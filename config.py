"""
Configuración global y funciones de carga/guardado para el sistema VideoSort
"""

import os
import json
import logging
from pathlib import Path

# Directorios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Subdirectorios específicos
ACTORS_DIR = os.path.join(DATA_DIR, "actors")
LOGOS_DIR = os.path.join(DATA_DIR, "logos")
TEMP_FRAMES_DIR = os.path.join(TEMP_DIR, "frames")
TEMP_AUDIO_DIR = os.path.join(TEMP_DIR, "audio")

# Archivos de configuración
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ACTORS_DB_FILE = os.path.join(DATA_DIR, "actors_db.json")
LOGOS_DB_FILE = os.path.join(DATA_DIR, "logos_db.json")
STUDIOS_MAPPING_FILE = os.path.join(DATA_DIR, "studios_mapping.json")
PROCESSED_CSV_FILE = os.path.join(OUTPUT_DIR, "processed_videos.csv")
ACTORS_CSV_FILE = os.path.join(OUTPUT_DIR, "actors_videos.csv")

# Configuración predeterminada
DEFAULT_CONFIG = {
    "api_keys": {
        "tmdb": "f98a4a1f467421762760132e1b91df58",
        "thetvdb": "21ee6d29-bc04-4dd0-98d4-649dc302a138"
    },
    "network": {
        "path": r"\\10.10.1.111\compartida\mp4",
        "user": "POLUX",
        "password": "Supermetroid1.",
        "drive_letter": "Z:"
    },
    "processing": {
        "video_extensions": [".mp4", ".mkv", ".mov", ".avi"],
        "max_processes": 4,
        "batch_size": 100,
        "debug": True,
        "capture_frames": True,
        "analyze_audio": False,
        "detect_actors": True,
        "detect_studios": True,
        "rename_files": True,
        "output_language": "en",
        "min_confidence": 0.6
    },
    "output": {
        "movies_dir": "Movies",
        "shows_dir": "Shows",
        "unknown_dir": "Unknown",
        "studios_dir": "ByStudio"
    }
}

def create_directories():
    """Crea todos los directorios necesarios para el sistema"""
    dirs = [
        CONFIG_DIR, DATA_DIR, LOGS_DIR, TEMP_DIR, OUTPUT_DIR,
        ACTORS_DIR, LOGOS_DIR, TEMP_FRAMES_DIR, TEMP_AUDIO_DIR
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        logging.debug(f"Directorio creado o verificado: {directory}")

def load_config():
    """Carga la configuración desde archivo o crea una nueva si no existe"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logging.debug("Configuración cargada correctamente")
            return config
        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
    
    # Si no existe o hay error, crear archivo con configuración predeterminada
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG

def save_config(config):
    """Guarda la configuración en archivo"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        logging.debug("Configuración guardada correctamente")
        return True
    except Exception as e:
        logging.error(f"Error guardando configuración: {e}")
        return False

def update_config(key, value):
    """Actualiza un valor específico en la configuración"""
    config = load_config()
    
    # Manejar rutas anidadas tipo "processing.debug"
    if "." in key:
        parts = key.split(".")
        current = config
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    else:
        config[key] = value
    
    return save_config(config)

def get_config_value(key, default=None):
    """Obtiene un valor específico de la configuración"""
    config = load_config()
    
    # Manejar rutas anidadas tipo "processing.debug"
    if "." in key:
        parts = key.split(".")
        current = config
        for part in parts:
            if part not in current:
                return default
            current = current[part]
        return current
    else:
        return config.get(key, default)

# Inicializar sistema al importar
create_directories()