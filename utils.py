"""
Funciones de utilidad para el sistema VideoSort
"""

import os
import logging
import subprocess
from datetime import datetime
import re

def setup_logging():
    """Configura el sistema de logging"""
    from config import LOGS_DIR
    
    # Crear directorio de logs si no existe
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Nombre de archivo con fecha
    log_file = os.path.join(LOGS_DIR, f"videosort_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configuración de logging
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # También enviar logs a consola
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
    return logging.getLogger('videosort')

def log_print(message, level=logging.INFO):
    """Imprime un mensaje y lo registra en el log"""
    if level == logging.DEBUG:
        logging.debug(message)
    elif level == logging.WARNING:
        logging.warning(message)
        print(f"ADVERTENCIA: {message}")
    elif level == logging.ERROR:
        logging.error(message)
        print(f"ERROR: {message}")
    else:
        logging.info(message)
        print(message)

def connect_network_drive(config):
    """Conecta a unidad de red usando configuración"""
    drive_letter = config["network"]["drive_letter"].rstrip(":\\")
    network_path = config["network"]["path"].replace("/", "\\")
    user = config["network"]["user"]
    password = config["network"]["password"]
    
    try:
        # Verificar si ya está mapeado
        result = subprocess.run("net use", capture_output=True, text=True, shell=True)
        if f"{drive_letter}:" in result.stdout and network_path in result.stdout:
            log_print(f"Unidad {drive_letter}: ya mapeada a {network_path}.")
            return f"{drive_letter}:\\"
        
        # Intentar eliminar mapeo previo
        subprocess.run(f"net use {drive_letter}: /delete", capture_output=True, text=True, shell=True)
        
        # Crear nuevo mapeo
        cmd = f"net use {drive_letter}: {network_path} /user:{user} \"{password}\""
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            log_print(f"Unidad {drive_letter}: mapeada correctamente a {network_path}.")
            return f"{drive_letter}:\\"
        else:
            log_print(f"Error al mapear {drive_letter}: {result.stderr}", logging.ERROR)
            return None
    except Exception as e:
        log_print(f"Excepción al mapear {drive_letter}: {e}", logging.ERROR)
        return None

def clean_filename(filename):
    """Limpia el nombre de archivo para búsqueda"""
    # Eliminar extensión
    name = os.path.splitext(filename)[0]
    
    # Eliminar etiquetas comunes
    name = re.sub(r'\[[^\]]*\]', '', name)
    name = re.sub(r'\([^)]*\)', '', name)
    
    # Reemplazar caracteres especiales con espacios
    name = re.sub(r'[._-]', ' ', name)
    
    # Términos comunes a eliminar
    common_terms = [
        # Español
        'Latino', 'Castellano', 'Español', 'ESP', 'LAT', 'Subtitulado', 'Subs',
        'Temporada', 'Capitulo', 'Cap', 'Temp', 'T', 'E', 'S', 'Serie',
        'Completa', 'Saga', 'Trilogia', 'Duologia',
        # Inglés
        'Season', 'Episode', 'Complete', 'Trilogy', 'Duology',
        # Técnicos
        'HDTV', 'BluRay', 'BRRip', 'DVDRip', 'WEB-DL', 'WEBRip',
        'XviD', 'MP4', 'x264', 'x265', 'HEVC', 'AAC', 'AC3', 
        'Rip', 'Screener', 'CAM', 'TS', 'HD', 'FHD', 'UHD', '4K'
    ]
    
    pattern = r'\b(' + '|'.join(common_terms) + r')\b'
    name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # Eliminar múltiples espacios
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Eliminar artículos al inicio
    name = re.sub(r'^(El|La|Los|Las|Un|Una|Unos|Unas|The|A|An) ', '', name, flags=re.IGNORECASE)
    
    return name

def sanitize_filename(filename):
    """Sanitiza un nombre de archivo para que sea válido en el sistema de archivos"""
    # Eliminar caracteres inválidos en nombres de archivo
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Limitar longitud (Windows tiene un límite de 255 caracteres)
    if len(filename) > 240:
        base, ext = os.path.splitext(filename)
        filename = base[:236] + ext
    
    return filename

def format_size(size_bytes):
    """Formatea un tamaño en bytes a formato legible"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.1f} MB"
    else:
        return f"{size_bytes/1024**3:.1f} GB"

def is_valid_video(filepath, config):
    """Verifica si un archivo es un video válido"""
    ext = os.path.splitext(filepath)[1].lower()
    return (ext in config["processing"]["video_extensions"] and 
            os.path.isfile(filepath) and 
            os.access(filepath, os.R_OK))

def check_dependencies():
    """Verifica dependencias del sistema y módulos opcionales"""
    dependencies = {
        "ffmpeg": False,
        "ffprobe": False,
        "cv2": False,
        "pytesseract": False,
        "face_recognition": False
    }
    
    # Verificar ffmpeg y ffprobe
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True)
        dependencies["ffmpeg"] = True
    except:
        pass
    
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True)
        dependencies["ffprobe"] = True
    except:
        pass
    
    # Verificar módulos Python
    try:
        import cv2
        dependencies["cv2"] = True
    except ImportError:
        pass
    
    try:
        import pytesseract
        dependencies["pytesseract"] = True
    except ImportError:
        pass
    
    try:
        import face_recognition
        dependencies["face_recognition"] = True
    except ImportError:
        pass
    
    return dependencies

# Inicializar logging al importar
logger = setup_logging()