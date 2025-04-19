"""
Operaciones con archivos (mover, renombrar, etc.)
"""

import os
import shutil
import csv
import re
import logging
from datetime import datetime
from utils import log_print, sanitize_filename

def create_backup_csv(backup_file, fieldnames=None):
    """
    Crea un archivo CSV para registrar operaciones de archivo
    
    Args:
        backup_file: Ruta al archivo CSV de respaldo
        fieldnames: Lista de nombres de campo (columnas)
        
    Returns:
        True si se crea correctamente, False si hay error
    """
    if fieldnames is None:
        fieldnames = ["nombre_original", "ruta_original", "nombre_nuevo", 
                     "ruta_nueva", "status", "timestamp"]
    
    try:
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        
        with open(backup_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        
        log_print(f"Archivo de respaldo creado: {backup_file}")
        return True
    except Exception as e:
        log_print(f"Error creando archivo de respaldo: {e}", logging.ERROR)
        return False

def append_to_backup(backup_file, data):
    """
    Añade una entrada al archivo CSV de respaldo
    
    Args:
        backup_file: Ruta al archivo CSV de respaldo
        data: Diccionario con datos para añadir
        
    Returns:
        True si se añade correctamente, False si hay error
    """
    try:
        # Verificar si existe el archivo
        if not os.path.exists(backup_file):
            fieldnames = list(data.keys())
            if "timestamp" not in fieldnames:
                fieldnames.append("timestamp")
            create_backup_csv(backup_file, fieldnames)
        
        # Añadir timestamp si no existe
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Abrir en modo append
        with open(backup_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            writer.writerow(data)
        
        return True
    except Exception as e:
        log_print(f"Error añadiendo a archivo de respaldo: {e}", logging.ERROR)
        return False

def safe_move_file(source_path, dest_path, create_dirs=True):
    """
    Mueve un archivo de forma segura, creando directorios si es necesario
    
    Args:
        source_path: Ruta origen
        dest_path: Ruta destino
        create_dirs: Si debe crear directorios destino automáticamente
        
    Returns:
        True si se mueve correctamente, False si hay error
    """
    try:
        # Verificar si existe el archivo origen
        if not os.path.exists(source_path):
            log_print(f"El archivo origen no existe: {source_path}", logging.ERROR)
            return False
        
        # Crear directorio destino si no existe
        if create_dirs:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        # Verificar si el archivo destino ya existe
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(dest_path)
            dest_path = f"{base}_duplicado{ext}"
            log_print(f"El archivo destino ya existe. Usando nuevo nombre: {dest_path}", logging.WARNING)
        
        # Mover archivo
        shutil.move(source_path, dest_path)
        log_print(f"Archivo movido: {source_path} -> {dest_path}")
        return True
    except Exception as e:
        log_print(f"Error moviendo archivo: {e}", logging.ERROR)
        return False

def create_movie_path(base_dir, title, year, quality, extension):
    """
    Crea la ruta para una película siguiendo una estructura estándar
    
    Args:
        base_dir: Directorio base
        title: Título de la película
        year: Año de lanzamiento
        quality: Calidad del video (1080p, etc.)
        extension: Extensión del archivo (.mp4, etc.)
        
    Returns:
        Tupla (ruta_directorio, ruta_archivo)
    """
    # Sanitizar título para nombre de carpeta y archivo
    safe_title = sanitize_filename(title)
    
    # Crear nombre de carpeta y archivo
    folder_name = f"{safe_title} ({year})"
    file_name = f"{safe_title} ({year}) [{quality}]{extension}"
    
    # Rutas completas
    movie_dir = os.path.join(base_dir, "Movies", folder_name)
    movie_file = os.path.join(movie_dir, file_name)
    
    return movie_dir, movie_file

def create_tv_path(base_dir, title, year, season, episode, quality, extension):
    """
    Crea la ruta para un episodio de serie siguiendo una estructura estándar
    
    Args:
        base_dir: Directorio base
        title: Título de la serie
        year: Año de lanzamiento
        season: Número de temporada
        episode: Número de episodio
        quality: Calidad del video (1080p, etc.)
        extension: Extensión del archivo (.mp4, etc.)
        
    Returns:
        Tupla (ruta_directorio, ruta_archivo)
    """
    # Sanitizar título para nombre de carpeta y archivo
    safe_title = sanitize_filename(title)
    
    # Formatear temporada y episodio como 2 dígitos
    season_str = f"{int(season):02d}"
    episode_str = f"{int(episode):02d}"
    
    # Crear nombres de carpetas y archivo
    series_folder = f"{safe_title} ({year})"
    season_folder = f"Season {season_str}"
    file_name = f"{safe_title} S{season_str}E{episode_str} [{quality}]{extension}"
    
    # Rutas completas
    season_dir = os.path.join(base_dir, "Shows", series_folder, season_folder)
    episode_file = os.path.join(season_dir, file_name)
    
    return season_dir, episode_file

def create_studio_path(base_dir, studio_name, original_filename):
    """
    Crea la ruta para un archivo no identificado organizado por estudio
    
    Args:
        base_dir: Directorio base
        studio_name: Nombre del estudio/cadena detectado
        original_filename: Nombre original del archivo
        
    Returns:
        Tupla (ruta_directorio, ruta_archivo)
    """
    # Si no hay estudio, usar carpeta genérica
    if not studio_name:
        studio_folder = "SinCadenaTelevisiva"
    else:
        # Sanitizar nombre del estudio
        studio_folder = sanitize_filename(studio_name)
    
    # Rutas completas
    studio_dir = os.path.join(base_dir, "ByStudio", studio_folder)
    file_path = os.path.join(studio_dir, original_filename)
    
    return studio_dir, file_path

def process_file_operation(source_path, result_info, output_dir, backup_file):
    """
    Procesa una operación de archivo completa (mover y registrar)
    
    Args:
        source_path: Ruta al archivo original
        result_info: Diccionario con información de identificación y destino
        output_dir: Directorio base para la salida
        backup_file: Archivo CSV para respaldo
        
    Returns:
        Diccionario con resultado de la operación
    """
    if not os.path.exists(source_path):
        log_print(f"El archivo {source_path} no existe", logging.ERROR)
        result = {
            "nombre_original": os.path.basename(source_path),
            "ruta_original": source_path,
            "nombre_nuevo": "",
            "ruta_nueva": "",
            "status": "error_origen"
        }
        append_to_backup(backup_file, result)
        return result
    
    original_filename = os.path.basename(source_path)
    extension = os.path.splitext(original_filename)[1].lower()
    
    try:
        # Determinar destino según el tipo de contenido
        if result_info.get("identificado"):
            if result_info.get("es_pelicula"):
                # Película
                info = result_info["info"]
                title = info.get('title', 'Unknown')
                year = info.get('release_date', '')[:4] if info.get('release_date') else 'Unknown'
                quality = result_info.get("quality", "Unknown")
                
                dest_dir, dest_file = create_movie_path(output_dir, title, year, quality, extension)
            else:
                # Serie
                info = result_info["info"]
                title = info.get('name', 'Unknown')
                year = info.get('first_air_date', '')[:4] if info.get('first_air_date') else 'Unknown'
                quality = result_info.get("quality", "Unknown")
                
                # Obtener temporada/episodio del resultado o usar valores predeterminados
                season = result_info.get("season", 1)
                episode = result_info.get("episode", 1)
                
                dest_dir, dest_file = create_tv_path(output_dir, title, year, season, episode, quality, extension)
        else:
            # No identificado, organizar por estudio
            studio = result_info.get("detected_studios", ["Unknown"])[0] if result_info.get("detected_studios") else None
            dest_dir, dest_file = create_studio_path(output_dir, studio, original_filename)
        
        # Mover archivo
        if safe_move_file(source_path, dest_file, create_dirs=True):
            result = {
                "nombre_original": original_filename,
                "ruta_original": source_path,
                "nombre_nuevo": os.path.basename(dest_file),
                "ruta_nueva": dest_file,
                "status": "success"
            }
        else:
            result = {
                "nombre_original": original_filename,
                "ruta_original": source_path,
                "nombre_nuevo": os.path.basename(dest_file),
                "ruta_nueva": dest_file,
                "status": "error_mover"
            }
        
        # Registrar en archivo de respaldo
        append_to_backup(backup_file, result)
        return result
    
    except Exception as e:
        log_print(f"Error procesando operación de archivo: {e}", logging.ERROR)
        result = {
            "nombre_original": original_filename,
            "ruta_original": source_path,
            "nombre_nuevo": "",
            "ruta_nueva": "",
            "status": f"error: {str(e)}"
        }
        append_to_backup(backup_file, result)
        return result

def restore_from_backup(backup_file):
    """
    Restaura archivos a sus ubicaciones originales según el archivo de respaldo
    
    Args:
        backup_file: Archivo CSV de respaldo
        
    Returns:
        Número de archivos restaurados
    """
    if not os.path.exists(backup_file):
        log_print(f"El archivo de respaldo {backup_file} no existe", logging.ERROR)
        return 0
    
    restored = 0
    errors = 0
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["status"] == "success" and os.path.exists(row["ruta_nueva"]):
                    # Crear directorio original si no existe
                    os.makedirs(os.path.dirname(row["ruta_original"]), exist_ok=True)
                    
                    try:
                        log_print(f"Restaurando: {row['ruta_nueva']} -> {row['ruta_original']}")
                        shutil.move(row["ruta_nueva"], row["ruta_original"])
                        restored += 1
                    except Exception as e:
                        log_print(f"Error restaurando {row['nombre_original']}: {e}", logging.ERROR)
                        errors += 1
    except Exception as e:
        log_print(f"Error procesando archivo de respaldo: {e}", logging.ERROR)
    
    log_print(f"Restauración completada. Restaurados: {restored}, Errores: {errors}")
    return restored