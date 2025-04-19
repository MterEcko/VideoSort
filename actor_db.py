"""
Gestión de base de datos de actores
"""

import os
import csv
import json
import requests
import shutil
import logging
from utils import log_print

# Verificar dependencias opcionales
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False

# Configuración para TMDb
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def download_image(url, destination_path):
    """
    Descarga una imagen desde URL y la guarda en la ruta especificada
    
    Args:
        url: URL de la imagen
        destination_path: Ruta donde guardar la imagen
        
    Returns:
        True si se descarga correctamente, False si hay error
    """
    try:
        response = requests.get(url, stream=True, timeout=15)
        if response.status_code == 200:
            with open(destination_path, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            return True
        else:
            log_print(f"Error descargando imagen: {response.status_code}", logging.WARNING)
            return False
    except Exception as e:
        log_print(f"Error en download_image: {e}", logging.ERROR)
        return False

def search_actor_tmdb(actor_name, config):
    """
    Busca información de un actor en TMDb
    
    Args:
        actor_name: Nombre del actor a buscar
        config: Configuración con API key
        
    Returns:
        Diccionario con información del actor o None si no se encuentra
    """
    try:
        api_key = config["api_keys"]["tmdb"]
        url = f"https://api.themoviedb.org/3/search/person?api_key={api_key}&query={actor_name}&language=en-US"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and len(data["results"]) > 0:
                # Retornar el primer resultado
                return data["results"][0]
        
        log_print(f"No se encontró información para {actor_name}", logging.WARNING)
        return None
    except Exception as e:
        log_print(f"Error buscando actor en TMDb: {e}", logging.ERROR)
        return None

def get_actor_images(actor_id, config, max_images=5):
    """
    Obtiene URLs de imágenes de un actor desde TMDb
    
    Args:
        actor_id: ID del actor en TMDb
        config: Configuración con API key
        max_images: Número máximo de imágenes a obtener
        
    Returns:
        Lista de URLs de imágenes
    """
    try:
        api_key = config["api_keys"]["tmdb"]
        url = f"https://api.themoviedb.org/3/person/{actor_id}/images?api_key={api_key}"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if "profiles" in data and data["profiles"]:
                # Tomar las primeras max_images o todas si hay menos
                images = data["profiles"][:max_images]
                return [f"{TMDB_IMAGE_BASE_URL}{img['file_path']}" for img in images]
        
        log_print(f"No se encontraron imágenes para actor ID {actor_id}", logging.WARNING)
        return []
    except Exception as e:
        log_print(f"Error obteniendo imágenes: {e}", logging.ERROR)
        return []

def create_actor_entry(actor_name, actors_dir, config, max_images=5):
    """
    Crea entrada en la base de datos para un actor
    
    Args:
        actor_name: Nombre del actor
        actors_dir: Directorio base para actores
        config: Configuración con API key
        max_images: Número máximo de imágenes a descargar
        
    Returns:
        True si se crea correctamente, False si hay error
    """
    # Buscar actor en TMDb
    actor_info = search_actor_tmdb(actor_name, config)
    if not actor_info:
        return False
    
    actor_id = actor_info["id"]
    professional_name = actor_info.get("name", actor_name)
    
    # Crear directorio para el actor si no existe
    actor_dir = os.path.join(actors_dir, professional_name.replace(" ", "_"))
    os.makedirs(actor_dir, exist_ok=True)
    
    # Obtener URLs de imágenes
    image_urls = get_actor_images(actor_id, config, max_images)
    if not image_urls:
        log_print(f"No se pudieron obtener imágenes para {actor_name}", logging.WARNING)
        return False
    
    # Descargar imágenes
    saved_images = 0
    for i, url in enumerate(image_urls):
        extension = os.path.splitext(url)[1] if "." in url else ".jpg"
        image_path = os.path.join(actor_dir, f"{i+1}{extension}")
        
        if download_image(url, image_path):
            saved_images += 1
    
    if saved_images == 0:
        log_print(f"No se pudieron guardar imágenes para {actor_name}", logging.WARNING)
        return False
    
    log_print(f"Se guardaron {saved_images} imágenes para {professional_name}")
    return True

def create_actors_db_from_list(actor_list, actors_dir, config):
    """
    Crea base de datos de actores a partir de una lista
    
    Args:
        actor_list: Lista de nombres de actores
        actors_dir: Directorio base para actores
        config: Configuración con API key
        
    Returns:
        Número de actores procesados correctamente
    """
    # Crear directorio principal si no existe
    os.makedirs(actors_dir, exist_ok=True)
    
    processed_actors = 0
    for actor in actor_list:
        log_print(f"Procesando actor: {actor}")
        if create_actor_entry(actor, actors_dir, config):
            processed_actors += 1
    
    log_print(f"Base de datos creada con {processed_actors} de {len(actor_list)} actores")
    return processed_actors

def generate_encodings_db(actors_dir, db_file):
    """
    Genera archivo JSON con encodings faciales de actores
    
    Args:
        actors_dir: Directorio con imágenes de actores
        db_file: Ruta donde guardar la base de datos
        
    Returns:
        True si se genera correctamente, False si hay error
    """
    if not FACE_RECOGNITION_AVAILABLE:
        log_print("face_recognition no disponible. No se pueden generar encodings.", logging.ERROR)
        return False
    
    if not os.path.exists(actors_dir):
        log_print(f"No se encontró el directorio {actors_dir}", logging.ERROR)
        return False
    
    db_actors = {}
    
    # Recorrer directorio de actores
    for actor_dir in os.listdir(actors_dir):
        actor_path = os.path.join(actors_dir, actor_dir)
        
        if os.path.isdir(actor_path):
            actor_name = actor_dir.replace("_", " ")
            db_actors[actor_name] = []
            
            # Procesar cada imagen del actor
            processed_images = 0
            for img_file in os.listdir(actor_path):
                if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(actor_path, img_file)
                    
                    try:
                        # Cargar imagen
                        image = face_recognition.load_image_file(img_path)
                        
                        # Extraer encoding
                        face_encodings = face_recognition.face_encodings(image)
                        
                        if face_encodings:
                            # Guardar el primer encoding (asumiendo una sola cara por imagen)
                            db_actors[actor_name].append(face_encodings[0].tolist())
                            processed_images += 1
                    except Exception as e:
                        log_print(f"Error procesando {img_path}: {e}", logging.ERROR)
            
            log_print(f"Procesadas {processed_images} imágenes para {actor_name}")
            
            # Si no se pudo procesar ninguna imagen, eliminar entrada
            if processed_images == 0:
                del db_actors[actor_name]
    
    # Guardar base de datos en archivo JSON
    try:
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(db_actors, f)
        
        log_print(f"Base de datos de encodings creada con {len(db_actors)} actores")
        return True
    except Exception as e:
        log_print(f"Error guardando base de datos: {e}", logging.ERROR)
        return False

def create_actors_csv(csv_file):
    """
    Crea archivo CSV para registrar actores por video
    
    Args:
        csv_file: Ruta al archivo CSV
        
    Returns:
        True si se crea correctamente, False si ya existe
    """
    if os.path.exists(csv_file):
        log_print(f"El archivo {csv_file} ya existe", logging.INFO)
        return False
    
    try:
        os.makedirs(os.path.dirname(csv_file), exist_ok=True)
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ruta_video', 'nombre_video', 'actores', 'estudio'])
        
        log_print(f"Archivo CSV {csv_file} creado")
        return True
    except Exception as e:
        log_print(f"Error creando CSV: {e}", logging.ERROR)
        return False

def register_actors_for_video(csv_file, video_path, video_name, actors, studio=""):
    """
    Registra actores detectados en un video en el CSV
    
    Args:
        csv_file: Ruta al archivo CSV
        video_path: Ruta del video
        video_name: Nombre del video
        actors: Lista de actores detectados
        studio: Estudio/cadena detectado (opcional)
        
    Returns:
        True si se registra correctamente, False si hay error
    """
    # Convertir lista de actores a string separado por comas
    actors_str = ", ".join(actors) if actors else ""
    
    try:
        # Crear archivo si no existe
        if not os.path.exists(csv_file):
            create_actors_csv(csv_file)
            
        # Abrir archivo en modo append
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([video_path, video_name, actors_str, studio])
        
        return True
    except Exception as e:
        log_print(f"Error registrando actores en CSV: {e}", logging.ERROR)
        return False

def import_actors_from_file(file_path):
    """
    Importa lista de actores desde un archivo de texto
    
    Args:
        file_path: Ruta al archivo de texto
        
    Returns:
        Lista de nombres de actores
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            actors = [line.strip() for line in f if line.strip()]
        
        log_print(f"Se importaron {len(actors)} actores desde {file_path}")
        return actors
    except Exception as e:
        log_print(f"Error importando actores desde archivo: {e}", logging.ERROR)
        return []

def get_popular_actors(config, count=50):
    """
    Obtiene lista de actores populares desde TMDb
    
    Args:
        config: Configuración con API key
        count: Cantidad de actores a obtener
        
    Returns:
        Lista de nombres de actores
    """
    try:
        api_key = config["api_keys"]["tmdb"]
        actors = []
        pages = (count // 20) + 1  # TMDb devuelve 20 por página
        
        for page in range(1, pages+1):
            url = f"https://api.themoviedb.org/3/person/popular?api_key={api_key}&language=en-US&page={page}"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    for actor in data["results"]:
                        if len(actors) < count:
                            actors.append(actor["name"])
                        else:
                            break
        
        log_print(f"Se obtuvieron {len(actors)} actores populares")
        return actors
    except Exception as e:
        log_print(f"Error obteniendo actores populares: {e}", logging.ERROR)
        return []