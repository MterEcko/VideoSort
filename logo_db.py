"""
Gestión de base de datos de logos de estudios y cadenas televisivas
"""

import os
import json
import requests
import shutil
import time
import logging
from urllib.parse import quote_plus
from utils import log_print

# Intenta importar BeautifulSoup para el scraping
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    log_print("BeautifulSoup no disponible. Algunas funciones de búsqueda de logos estarán limitadas.", logging.WARNING)

# Configuración para las peticiones HTTP
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Lista predefinida de estudios y cadenas televisivas
DEFAULT_STUDIOS = [
    "FOX", "20th Century Fox", "FOX Searchlight",
    "HBO", "HBO Max", 
    "Netflix", "Netflix Studios",
    "Disney", "Walt Disney Pictures", "Disney+",
    "Warner Bros", "Warner Brothers", "WarnerMedia",
    "Universal Pictures", "Universal Studios",
    "Paramount Pictures", "Paramount",
    "Sony Pictures", "Columbia Pictures",
    "AMC", "AMC Studios",
    "Cartoon Network", "Adult Swim", 
    "MGM", "Metro Goldwyn Mayer",
    "Lionsgate", "Lions Gate",
    "DreamWorks", "DreamWorks Animation",
    "Pixar", "Pixar Animation",
    "BBC", "BBC Films", "BBC Studios",
    "Showtime", 
    "Starz", "Starz Originals",
    "CBS", "CBS Studios", "CBS Films",
    "NBC", "NBC Universal",
    "Amazon", "Amazon Studios", "Prime Video",
    "A24", "Blumhouse", "Focus Features",
    "New Line Cinema", "Summit Entertainment",
    "The CW", "USA Network", "FX", "Syfy",
    "Apple TV+", "Hulu", "Comedy Central",
    "National Geographic", "History Channel",
    "PBS", "PBS Kids", "Nickelodeon", "MTV",
    "Discovery", "Discovery Channel", "TLC",
    "TNT", "TBS", "Cinemax", "EPIX",
    "IFC Films", "Miramax", "Orion Pictures"
]

def create_logos_directory(logos_dir):
    """
    Crea el directorio para logos si no existe y añade un README
    
    Args:
        logos_dir: Ruta al directorio para logos
        
    Returns:
        True si se crea o ya existe, False si hay error
    """
    try:
        os.makedirs(logos_dir, exist_ok=True)
        
        # Crear archivo README con instrucciones
        readme_path = os.path.join(logos_dir, "README.txt")
        
        if not os.path.exists(readme_path):
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write("Biblioteca de Logos de Estudios y Cadenas\n")
                f.write("=========================================\n\n")
                f.write("Instrucciones:\n")
                f.write("1. Guarda imágenes de logos de estudios y cadenas en este directorio\n")
                f.write("2. Nombra cada archivo con el nombre del estudio/cadena, por ejemplo: 'FOX.png', 'HBO.jpg'\n")
                f.write("3. Se recomiendan imágenes de tamaño mediano (aprox. 300x300 píxeles)\n\n")
                f.write("Estudios/cadenas sugeridos para incluir:\n")
                for studio in DEFAULT_STUDIOS[:20]:  # Mostrar solo los primeros 20 para no hacer el archivo muy largo
                    f.write(f"- {studio}\n")
                f.write("- ... y muchos más.\n")
        
        log_print(f"Directorio para logos configurado en {logos_dir}")
        return True
    
    except Exception as e:
        log_print(f"Error creando directorio de logos: {e}", logging.ERROR)
        return False

def clean_filename(name):
    """
    Convierte un nombre a un formato válido para nombre de archivo
    
    Args:
        name: Nombre a limpiar
        
    Returns:
        Nombre limpio para usar como nombre de archivo
    """
    # Eliminar caracteres no válidos para nombre de archivo
    name = ''.join(c for c in name if c.isalnum() or c in ' ._-')
    # Reemplazar espacios por guiones bajos
    name = name.replace(' ', '_')
    return name

def search_logo_bing(query, max_results=3):
    """
    Busca logos usando Bing y devuelve URLs de imágenes
    
    Args:
        query: Término de búsqueda (nombre del estudio + "logo")
        max_results: Número máximo de resultados a devolver
        
    Returns:
        Lista de URLs de imágenes
    """
    if not BS4_AVAILABLE:
        return []
        
    search_url = f"https://www.bing.com/images/search?q={quote_plus(query)}+logo+transparent+png&form=HDRSC2&first=1"
    
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            log_print(f"Error en la búsqueda Bing: {response.status_code}", logging.WARNING)
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Bing almacena las URLs en atributos 'src' o 'data-src' de las etiquetas img
        img_tags = soup.find_all('img', class_='mimg')
        
        urls = []
        for img in img_tags[:max_results]:
            url = img.get('src') or img.get('data-src')
            if url and not url.startswith('data:'):  # Ignorar data URIs
                urls.append(url)
        
        return urls
    
    except Exception as e:
        log_print(f"Error buscando imágenes para {query}: {e}", logging.ERROR)
        return []

def search_logo_google(query, max_results=3):
    """
    Busca logos usando Google y devuelve URLs de imágenes
    Nota: Esto es una implementación básica y puede ser bloqueada por Google
    
    Args:
        query: Término de búsqueda (nombre del estudio + "logo")
        max_results: Número máximo de resultados a devolver
        
    Returns:
        Lista de URLs de imágenes
    """
    if not BS4_AVAILABLE:
        return []
        
    search_url = f"https://www.google.com/search?q={quote_plus(query)}+logo+transparent&tbm=isch"
    
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            log_print(f"Error en la búsqueda Google: {response.status_code}", logging.WARNING)
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraer URLs de imágenes (esto puede cambiar si Google modifica su estructura)
        urls = []
        img_tags = soup.find_all('img')
        
        for img in img_tags[1:max_results+1]:  # Saltar la primera que suele ser el logo de Google
            url = img.get('src')
            if url and not url.startswith('data:'):  # Ignorar data URIs
                urls.append(url)
        
        return urls
    
    except Exception as e:
        log_print(f"Error buscando imágenes para {query} en Google: {e}", logging.ERROR)
        return []

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
        response = requests.get(url, stream=True, headers=HEADERS, timeout=10)
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

def download_logo(studio_name, logos_dir, max_tries=3):
    """
    Busca y descarga el logo de un estudio/cadena
    
    Args:
        studio_name: Nombre del estudio/cadena
        logos_dir: Directorio donde guardar el logo
        max_tries: Número máximo de intentos con diferentes motores de búsqueda
        
    Returns:
        Ruta al archivo descargado o None si hay error
    """
    # Limpiar nombre para usar como nombre de archivo
    clean_name = clean_filename(studio_name)
    
    # Verificar si ya existe el logo
    existing_files = [f for f in os.listdir(logos_dir) if f.startswith(clean_name) and 
                     f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if existing_files:
        log_print(f"Logo para {studio_name} ya existe: {existing_files[0]}")
        return os.path.join(logos_dir, existing_files[0])
    
    log_print(f"Buscando logo para: {studio_name}")
    
    # Términos de búsqueda
    search_terms = [
        f"{studio_name} logo",
        f"{studio_name} logo transparent",
        f"{studio_name} official logo"
    ]
    
    # Intentar con diferentes motores de búsqueda y términos
    for term in search_terms:
        # Intentar con Bing
        urls = search_logo_bing(term, max_results=3)
        
        # Si no hay resultados, intentar con Google
        if not urls:
            urls = search_logo_google(term, max_results=3)
        
        # Intentar descargar cada URL
        for i, url in enumerate(urls):
            destination = os.path.join(logos_dir, f"{clean_name}_{i+1}.png")
            log_print(f"Descargando {url} a {destination}")
            
            if download_image(url, destination):
                log_print(f"Logo para {studio_name} descargado como {destination}")
                return destination
        
        # Pausa para evitar bloqueos
        time.sleep(1)
    
    log_print(f"No se pudo descargar ningún logo para {studio_name}", logging.WARNING)
    return None

def download_all_logos(logos_dir, studios=None):
    """
    Descarga logos para todos los estudios/cadenas especificados
    
    Args:
        logos_dir: Directorio donde guardar los logos
        studios: Lista de estudios/cadenas (usa DEFAULT_STUDIOS si es None)
        
    Returns:
        Número de logos descargados correctamente
    """
    if studios is None:
        studios = DEFAULT_STUDIOS
    
    # Crear directorio
    create_logos_directory(logos_dir)
    
    # Estado de descarga
    downloaded = 0
    failed = 0
    
    for studio in studios:
        log_print(f"Procesando {studio} ({downloaded+failed+1}/{len(studios)})")
        
        if download_logo(studio, logos_dir):
            downloaded += 1
        else:
            failed += 1
        
        # Pausa entre descargas para evitar ser bloqueado
        time.sleep(2)
    
    log_print(f"Proceso completado. Descargados: {downloaded}, Fallidos: {failed}")
    return downloaded

def save_logo_db(logos_dir, db_file):
    """
    Guarda la base de datos de logos disponibles
    
    Args:
        logos_dir: Directorio con los logos
        db_file: Archivo donde guardar la base de datos
        
    Returns:
        True si se guarda correctamente, False si hay error
    """
    try:
        # Obtener lista de archivos de logos
        logo_files = {}
        
        if os.path.exists(logos_dir):
            for filename in os.listdir(logos_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    # Extraer nombre del estudio del nombre del archivo
                    parts = os.path.splitext(filename)[0].split('_')
                    studio = '_'.join(parts[:-1]) if len(parts) > 1 else parts[0]
                    studio = studio.replace('_', ' ')
                    
                    logo_files[studio] = filename
        
        # Guardar en archivo JSON
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(logo_files, f, indent=4)
        
        log_print(f"Base de datos de logos guardada con {len(logo_files)} entradas")
        return True
        
    except Exception as e:
        log_print(f"Error guardando base de datos de logos: {e}", logging.ERROR)
        return False

def load_logo_db(db_file):
    """
    Carga la base de datos de logos
    
    Args:
        db_file: Archivo de base de datos
        
    Returns:
        Diccionario con la base de datos de logos
    """
    if os.path.exists(db_file):
        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_print(f"Error cargando base de datos de logos: {e}", logging.ERROR)
    
    return {}

def organize_logos(logos_dir, studios_mapping_file):
    """
    Organiza los logos descargados, renombrando para consistencia
    
    Args:
        logos_dir: Directorio con logos
        studios_mapping_file: Archivo de mapeo de estudios
        
    Returns:
        Número de logos organizados
    """
    # Cargar mapeo de estudios
    studios_mapping = {}
    if os.path.exists(studios_mapping_file):
        try:
            with open(studios_mapping_file, 'r', encoding='utf-8') as f:
                studios_mapping = json.load(f)
        except Exception as e:
            log_print(f"Error cargando mapeo de estudios: {e}", logging.ERROR)
    
    if not studios_mapping:
        log_print("No se pudo cargar el mapeo de estudios", logging.WARNING)
        return 0
    
    # Verificar directorio de logos
    if not os.path.exists(logos_dir):
        log_print(f"El directorio {logos_dir} no existe", logging.ERROR)
        return 0
    
    # Obtener archivos
    logo_files = [f for f in os.listdir(logos_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    organized = 0
    
    # Para cada estudio en el mapeo
    for studio, patterns in studios_mapping.items():
        clean_studio = clean_filename(studio)
        
        # Verificar si ya existe un archivo limpio para este estudio
        clean_file = f"{clean_studio}.png"
        if clean_file in logo_files:
            continue
        
        # Buscar archivos que coincidan con el patrón del estudio
        matches = [f for f in logo_files if clean_studio in f.lower()]
        
        if matches:
            # Tomar el primer archivo y renombrarlo
            best_file = matches[0]
            src_path = os.path.join(logos_dir, best_file)
            dst_path = os.path.join(logos_dir, clean_file)
            
            try:
                # Copiar en lugar de mover para conservar el original
                shutil.copy2(src_path, dst_path)
                log_print(f"Logo organizado: {best_file} -> {clean_file}")
                organized += 1
            except Exception as e:
                log_print(f"Error organizando {best_file}: {e}", logging.ERROR)
    
    log_print(f"Organización completada. {organized} logos organizados")
    return organized