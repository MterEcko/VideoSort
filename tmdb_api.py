"""
Funciones para búsqueda en TMDb (The Movie Database)
"""

import requests
import time
import logging
from utils import log_print

def search_tmdb_multilang(query, config, is_series=False, attempts=3):
    """
    Busca en TMDb con soporte para múltiples idiomas
    
    Args:
        query: Texto de búsqueda
        config: Configuración con la API key
        is_series: True para buscar series, False para películas
        attempts: Número de intentos si hay errores
        
    Returns:
        (resultado, tipo) donde tipo es True para película, False para serie
    """
    api_key = config["api_keys"]["tmdb"]
    languages = ["es", "en"]  # Primero español, luego inglés
    
    best_result = None
    result_type = None
    
    for lang in languages:
        try:
            if is_series:
                url = f"https://api.themoviedb.org/3/search/tv?api_key={api_key}&query={query}&language={lang}"
            else:
                url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={query}&language={lang}"
                
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results") and len(data["results"]) > 0:
                    result = data["results"][0]
                    name_key = 'title' if not is_series else 'name'
                    log_print(f"Encontrado en {lang}: {result.get(name_key, 'Sin título')}")
                    
                    # Si es la primera vez o tiene mejor puntuación
                    if best_result is None or result.get('popularity', 0) > best_result.get('popularity', 0):
                        # Si idioma no es inglés y estamos pidiendo salida en inglés
                        if lang != "en" and config["processing"]["output_language"] == "en":
                            # Buscar detalles en inglés
                            id_result = result['id']
                            detail_url = f"https://api.themoviedb.org/3/{'tv' if is_series else 'movie'}/{id_result}?api_key={api_key}&language=en"
                            detail_response = requests.get(detail_url, timeout=15)
                            
                            if detail_response.status_code == 200:
                                result = detail_response.json()
                        
                        best_result = result
                        result_type = not is_series  # True si es película, False si es serie
        except Exception as e:
            log_print(f"Error buscando en TMDb para '{query}' en {lang}: {e}", logging.ERROR)
            if attempts > 1:
                time.sleep(2)  # Esperar antes de reintentar
                return search_tmdb_multilang(query, config, is_series, attempts-1)
    
    return best_result, result_type

def search_by_actors(actors, config, is_series=False):
    """
    Busca películas o series que incluyan a los actores especificados
    
    Args:
        actors: Lista de nombres de actores
        config: Configuración con la API key
        is_series: True para buscar series, False para películas
        
    Returns:
        (resultado, tipo) donde tipo es True para película, False para serie
    """
    if not actors or len(actors) == 0:
        return None, None
    
    api_key = config["api_keys"]["tmdb"]
    
    try:
        # Primero, buscar IDs de los actores
        actor_ids = []
        
        for actor in actors:
            # Buscar actor en TMDb
            url = f"https://api.themoviedb.org/3/search/person?api_key={api_key}&query={actor}&language=en-US"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results") and len(data["results"]) > 0:
                    # Tomar el primer resultado
                    actor_ids.append(data["results"][0]["id"])
        
        if not actor_ids:
            return None, None
        
        # Ahora, buscar películas o series con estos actores
        all_results = []
        
        for actor_id in actor_ids:
            # Buscar créditos del actor
            url = f"https://api.themoviedb.org/3/person/{actor_id}/{'tv_credits' if is_series else 'movie_credits'}?api_key={api_key}&language=en-US"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                # Añadir a resultados
                if "cast" in data:
                    for item in data["cast"]:
                        all_results.append(item)
        
        # Contar frecuencia de cada película/serie
        from collections import Counter
        counter = Counter()
        id_to_info = {}
        
        for item in all_results:
            if "id" in item:
                counter[item["id"]] += 1
                id_to_info[item["id"]] = item
        
        # Obtener los que aparecen más veces (compartidos por más actores)
        most_common = counter.most_common()
        
        # Si hay resultados, devolver el más común
        if most_common:
            best_id, frequency = most_common[0]
            best_result = id_to_info[best_id]
            
            # Verificar si la frecuencia indica una buena coincidencia
            # (aparece en los créditos de múltiples actores buscados)
            if frequency >= min(2, len(actor_ids)):
                return best_result, not is_series
        
        return None, None
        
    except Exception as e:
        log_print(f"Error buscando por actores: {e}", logging.ERROR)
        return None, None

def get_movie_details(movie_id, config):
    """
    Obtiene detalles completos de una película
    
    Args:
        movie_id: ID de la película en TMDb
        config: Configuración con la API key
        
    Returns:
        Diccionario con detalles completos
    """
    api_key = config["api_keys"]["tmdb"]
    
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&append_to_response=credits,images,videos,release_dates&language={config['processing']['output_language']}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        else:
            log_print(f"Error obteniendo detalles de película {movie_id}: {response.status_code}", logging.ERROR)
            return None
    except Exception as e:
        log_print(f"Error en get_movie_details: {e}", logging.ERROR)
        return None

def get_tv_details(tv_id, config):
    """
    Obtiene detalles completos de una serie
    
    Args:
        tv_id: ID de la serie en TMDb
        config: Configuración con la API key
        
    Returns:
        Diccionario con detalles completos
    """
    api_key = config["api_keys"]["tmdb"]
    
    try:
        url = f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={api_key}&append_to_response=credits,images,videos,content_ratings&language={config['processing']['output_language']}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        else:
            log_print(f"Error obteniendo detalles de serie {tv_id}: {response.status_code}", logging.ERROR)
            return None
    except Exception as e:
        log_print(f"Error en get_tv_details: {e}", logging.ERROR)
        return None

def get_season_details(tv_id, season_number, config):
    """
    Obtiene detalles de una temporada específica
    
    Args:
        tv_id: ID de la serie en TMDb
        season_number: Número de temporada
        config: Configuración con la API key
        
    Returns:
        Diccionario con detalles de la temporada
    """
    api_key = config["api_keys"]["tmdb"]
    
    try:
        url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_number}?api_key={api_key}&language={config['processing']['output_language']}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        else:
            log_print(f"Error obteniendo detalles de temporada {season_number}: {response.status_code}", logging.ERROR)
            return None
    except Exception as e:
        log_print(f"Error en get_season_details: {e}", logging.ERROR)
        return None

def get_episode_details(tv_id, season_number, episode_number, config):
    """
    Obtiene detalles de un episodio específico
    
    Args:
        tv_id: ID de la serie en TMDb
        season_number: Número de temporada
        episode_number: Número de episodio
        config: Configuración con la API key
        
    Returns:
        Diccionario con detalles del episodio
    """
    api_key = config["api_keys"]["tmdb"]
    
    try:
        url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_number}/episode/{episode_number}?api_key={api_key}&language={config['processing']['output_language']}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        else:
            log_print(f"Error obteniendo detalles de episodio {season_number}x{episode_number}: {response.status_code}", logging.ERROR)
            return None
    except Exception as e:
        log_print(f"Error en get_episode_details: {e}", logging.ERROR)
        return None