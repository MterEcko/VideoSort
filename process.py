"""
Funciones principales de procesamiento para el sistema VideoSort
"""

import os
import csv
import time
import logging
import subprocess
from pathlib import Path
from multiprocessing import Pool
from functools import partial
from tqdm import tqdm
from datetime import datetime

# Importar módulos del sistema
from config import load_config, TEMP_DIR, ACTORS_DB_FILE, LOGOS_DIR, STUDIOS_MAPPING_FILE, PROCESSED_CSV_FILE, ACTORS_CSV_FILE
from utils import log_print, clean_filename, is_valid_video
from video_analysis import get_video_quality, analyze_video_content, extract_season_episode_from_filename, extract_year_from_filename
from tmdb_api import search_tmdb_multilang, search_by_actors
from studio_detect import load_studios_mapping, detect_studios_in_frames
from actor_detect import load_actors_db, detect_actors_in_frames
from actor_db import register_actors_for_video
from files_ops import process_file_operation, append_to_backup

def process_single_video(filepath, config, temp_dir=None):
    """
    Procesa un video completo: analiza contenido, identifica y prepara para renombrar
    
    Args:
        filepath: Ruta al archivo de video
        config: Configuración del sistema
        temp_dir: Directorio temporal específico (si None, se genera automáticamente)
        
    Returns:
        Diccionario con resultados del procesamiento
    """
    # Verificar que el archivo existe y es un video válido
    if not os.path.exists(filepath) or not is_valid_video(filepath, config):
        log_print(f"Archivo inválido o no existe: {filepath}", logging.ERROR)
        return {
            "identificado": False,
            "info": None,
            "mensaje": "Archivo inválido o no existe"
        }
    
    original_filename = os.path.basename(filepath)
    log_print(f"Procesando video: {original_filename}")
    
    # Crear directorio temporal
    if temp_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = os.path.join(TEMP_DIR, f"{clean_filename(original_filename)}_{timestamp}")
    
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 1. Analizar contenido del video
        log_print("Analizando contenido del video...")
        content_results = analyze_video_content(filepath, temp_dir, config)
        
        # 2. Obtener calidad
        quality = content_results.get("quality", "Unknown")
        
        # 3. Intentar identificar por nombre de archivo
        cleaned_name = clean_filename(original_filename)
        log_print(f"Buscando por nombre: '{cleaned_name}'")
        
        result = None
        is_movie = None
        
        # Intentar primero como película
        result, is_movie = search_tmdb_multilang(cleaned_name, config, is_series=False)
        
        # Si no hay resultado, intentar como serie
        if not result:
            result, is_movie = search_tmdb_multilang(cleaned_name, config, is_series=True)
        
        # 4. Si no hay resultado, intentar con texto extraído
        if not result and content_results.get("ocr_text"):
            log_print("Buscando por texto OCR...")
            ocr_text = content_results["ocr_text"]
            
            # Dividir en fragmentos significativos (líneas o bloques)
            fragments = []
            for line in ocr_text.split('\n'):
                if len(line.strip()) > 15:  # Solo líneas con suficiente texto
                    fragments.append(line.strip())
            
            # Buscar con fragmentos
            for fragment in fragments[:5]:  # Limitar a los primeros 5
                result, is_movie = search_tmdb_multilang(fragment, config, is_series=False)
                if result:
                    break
                
                result, is_movie = search_tmdb_multilang(fragment, config, is_series=True)
                if result:
                    break
        
        # 5. Si no hay resultado, intentar con subtítulos
        if not result and content_results.get("subtitles_text"):
            log_print("Buscando por subtítulos...")
            subtitle_text = content_results["subtitles_text"]
            
            # Dividir en bloques
            blocks = subtitle_text.split('\n\n')
            for block in blocks[:5]:  # Limitar a los primeros 5
                # Eliminar líneas de tiempo
                lines = [l for l in block.split('\n') if not l.strip().startswith('-->')]
                if lines:
                    search_text = ' '.join(lines)
                    
                    result, is_movie = search_tmdb_multilang(search_text, config, is_series=False)
                    if result:
                        break
                    
                    result, is_movie = search_tmdb_multilang(search_text, config, is_series=True)
                    if result:
                        break
        
        # 6. Extraer fotogramas para análisis de actores y estudios
        frame_files = []
        if config["processing"]["capture_frames"] and (
            config["processing"]["detect_actors"] or config["processing"]["detect_studios"]):
            # Ya tenemos fotogramas extraídos durante el análisis
            frame_files = [f for f in os.listdir(temp_dir) if f.startswith('frame_') and f.endswith('.png')]
            frame_files = [os.path.join(temp_dir, f) for f in frame_files]
        
        # 7. Detectar estudios
        detected_studios = []
        if config["processing"]["detect_studios"] and frame_files:
            log_print("Detectando estudios/cadenas...")
            studios_mapping = load_studios_mapping(STUDIOS_MAPPING_FILE)
            detected_studios = detect_studios_in_frames(frame_files, studios_mapping, LOGOS_DIR)
        
        # 8. Detectar actores
        detected_actors = []
        if config["processing"]["detect_actors"] and frame_files:
            log_print("Detectando actores...")
            actors_db = load_actors_db(ACTORS_DB_FILE)
            detected_actors = detect_actors_in_frames(
                frame_files, actors_db, config["processing"]["min_confidence"]
            )
        
        # 9. Si aún no hay resultado y hay actores detectados, buscar por actores
        if not result and detected_actors:
            log_print(f"Buscando por actores: {detected_actors}")
            result, is_movie = search_by_actors(detected_actors, config, is_series=False)
            
            if not result:
                result, is_movie = search_by_actors(detected_actors, config, is_series=True)
        
        # 10. Preparar resultado
        if result:
            # Obtener información de temporada/episodio para series
            season = None
            episode = None
            
            if not is_movie:
                # Intentar extraer de nombre de archivo
                season, episode = extract_season_episode_from_filename(original_filename)
                
                # Si no se pudo extraer, usar valores predeterminados
                if season is None:
                    season = 1
                if episode is None:
                    episode = 1
            
            # Registrar actores detectados (si hay)
            if detected_actors:
                studio_name = detected_studios[0] if detected_studios else ""
                register_actors_for_video(
                    ACTORS_CSV_FILE, filepath, original_filename, detected_actors, studio_name
                )
            
            # Resultado exitoso
            return {
                "identificado": True,
                "es_pelicula": is_movie,
                "info": result,
                "quality": quality,
                "season": season,
                "episode": episode,
                "detected_studios": detected_studios,
                "detected_actors": detected_actors
            }
        else:
            # No identificado
            return {
                "identificado": False,
                "info": None,
                "quality": quality,
                "detected_studios": detected_studios,
                "detected_actors": detected_actors,
                "mensaje": "No se pudo identificar"
            }
    
    except Exception as e:
        log_print(f"Error procesando {filepath}: {e}", logging.ERROR)
        return {
            "identificado": False,
            "info": None,
            "mensaje": f"Error: {str(e)}"
        }
    finally:
        # Limpiar directorio temporal si no está en modo debug
        if not config["processing"]["debug"] and os.path.exists(temp_dir):
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                log_print(f"Error eliminando directorio temporal: {e}", logging.ERROR)

def process_batch(video_files, config, output_dir, batch_num=1):
    """
    Procesa un lote de videos
    
    Args:
        video_files: Lista de rutas a archivos de video
        config: Configuración del sistema
        output_dir: Directorio base para la salida
        batch_num: Número de lote para registro
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    log_print(f"Iniciando procesamiento del lote {batch_num} con {len(video_files)} videos")
    
    # Archivo de respaldo para este lote
    batch_backup_file = f"{PROCESSED_CSV_FILE}.{batch_num}"
    
    # Estadísticas
    stats = {
        "total": len(video_files),
        "procesados": 0,
        "identificados": 0,
        "no_identificados": 0,
        "errores": 0
    }
    
    # Decidir entre procesamiento en paralelo o secuencial
    if config["processing"]["debug"]:
        # En modo debug, procesar secuencialmente
        results = []
        for video in tqdm(video_files, desc=f"Procesando lote {batch_num}", unit="video"):
            result = process_single_video(video, config)
            stats["procesados"] += 1
            
            if result["identificado"]:
                stats["identificados"] += 1
            elif "mensaje" in result and result["mensaje"].startswith("Error"):
                stats["errores"] += 1
            else:
                stats["no_identificados"] += 1
            
            # Procesar operación de archivo
            if config["processing"]["rename_files"]:
                file_op_result = process_file_operation(video, result, output_dir, batch_backup_file)
            else:
                # Solo registrar sin mover
                file_op_result = {
                    "nombre_original": os.path.basename(video),
                    "ruta_original": video,
                    "nombre_nuevo": "",
                    "ruta_nueva": "",
                    "status": "no_action"
                }
                append_to_backup(batch_backup_file, file_op_result)
            
            results.append((result, file_op_result))
    else:
        # En modo normal, usar multiprocesamiento
        with Pool(processes=config["processing"]["max_processes"]) as pool:
            # Procesar videos
            process_func = partial(process_single_video, config=config)
            results_iter = pool.imap_unordered(process_func, video_files)
            
            # Crear barra de progreso
            results = []
            for result in tqdm(results_iter, total=len(video_files), desc=f"Procesando lote {batch_num}", unit="video"):
                stats["procesados"] += 1
                
                if result["identificado"]:
                    stats["identificados"] += 1
                elif "mensaje" in result and result["mensaje"].startswith("Error"):
                    stats["errores"] += 1
                else:
                    stats["no_identificados"] += 1
                
                # Obtener ruta del video original (necesitamos buscarla ya que imap_unordered no mantiene orden)
                video_idx = stats["procesados"] - 1  # Índice en la lista original
                if video_idx < len(video_files):
                    video = video_files[video_idx]
                    
                    # Procesar operación de archivo
                    if config["processing"]["rename_files"]:
                        file_op_result = process_file_operation(video, result, output_dir, batch_backup_file)
                    else:
                        # Solo registrar sin mover
                        file_op_result = {
                            "nombre_original": os.path.basename(video),
                            "ruta_original": video,
                            "nombre_nuevo": "",
                            "ruta_nueva": "",
                            "status": "no_action"
                        }
                        append_to_backup(batch_backup_file, file_op_result)
                    
                    results.append((result, file_op_result))
    
    # Mostrar estadísticas
    log_print(f"Estadísticas del lote {batch_num}:")
    log_print(f"  - Total procesados: {stats['procesados']}")
    log_print(f"  - Identificados: {stats['identificados']}")
    log_print(f"  - No identificados: {stats['no_identificados']}")
    log_print(f"  - Errores: {stats['errores']}")
    
    return stats

def process_directory(directory, config, recursive=True, mode="default"):
    """
    Procesa todos los videos en un directorio
    
    Args:
        directory: Directorio a procesar
        config: Configuración del sistema
        recursive: Si debe procesar subdirectorios
        mode: Modo de procesamiento ('default', 'direct', 'batch')
        
    Returns:
        Diccionario con estadísticas del procesamiento
    """
    if not os.path.exists(directory):
        log_print(f"El directorio {directory} no existe", logging.ERROR)
        return {"error": "Directorio no existe"}
    
    log_print(f"Procesando directorio: {directory} (modo: {mode})")
    
    # Estadísticas globales
    global_stats = {
        "total": 0,
        "procesados": 0,
        "identificados": 0,
        "no_identificados": 0,
        "errores": 0,
        "tiempo_inicio": datetime.now(),
        "tiempo_fin": None
    }
    
    # Recopilar archivos de video
    video_files = []
    
    if mode == "direct":
        # Modo directo: solo archivos en el directorio actual
        for file in os.listdir(directory):
            filepath = os.path.join(directory, file)
            if is_valid_video(filepath, config):
                video_files.append(filepath)
    else:
        # Modo predeterminado o por lotes
        if mode == "batch":
            # Buscar subdirectorios como lotes
            batches = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d)) and 
                     not d.startswith('.') and 
                     d not in [config["output"]["movies_dir"], config["output"]["shows_dir"], 
                              config["output"]["unknown_dir"], config["output"]["studios_dir"]]]
            
            if not batches:
                log_print("No se encontraron subdirectorios para procesar como lotes", logging.WARNING)
                return global_stats
            
            # Procesar cada lote
            for batch_num, batch in enumerate(batches, 1):
                batch_path = os.path.join(directory, batch)
                batch_files = []
                
                # Recopilar archivos en el lote
                for root, _, files in os.walk(batch_path):
                    for file in files:
                        filepath = os.path.join(root, file)
                        if is_valid_video(filepath, config):
                            batch_files.append(filepath)
                
                if not batch_files:
                    log_print(f"No se encontraron videos en el lote {batch}", logging.WARNING)
                    continue
                
                # Procesar lote
                batch_stats = process_batch(batch_files, config, directory, batch_num)
                
                # Actualizar estadísticas globales
                global_stats["total"] += batch_stats["total"]
                global_stats["procesados"] += batch_stats["procesados"]
                global_stats["identificados"] += batch_stats["identificados"]
                global_stats["no_identificados"] += batch_stats["no_identificados"]
                global_stats["errores"] += batch_stats["errores"]
        else:
            # Modo predeterminado: buscar recursivamente
            for root, _, files in os.walk(directory):
                for file in files:
                    filepath = os.path.join(root, file)
                    if is_valid_video(filepath, config):
                        video_files.append(filepath)
                
                # Si no es recursivo, salir después del primer nivel
                if not recursive:
                    break
            
            # Procesar como un solo lote
            if video_files:
                batch_stats = process_batch(video_files, config, directory)
                
                # Actualizar estadísticas globales
                global_stats["total"] = batch_stats["total"]
                global_stats["procesados"] = batch_stats["procesados"]
                global_stats["identificados"] = batch_stats["identificados"]
                global_stats["no_identificados"] = batch_stats["no_identificados"]
                global_stats["errores"] = batch_stats["errores"]
    
    # Registrar tiempo de finalización
    global_stats["tiempo_fin"] = datetime.now()
    tiempo_total = (global_stats["tiempo_fin"] - global_stats["tiempo_inicio"]).total_seconds()
    
    # Mostrar estadísticas finales
    log_print("\nEstadísticas finales:")
    log_print(f"  - Total archivos: {global_stats['total']}")
    log_print(f"  - Procesados: {global_stats['procesados']}")
    log_print(f"  - Identificados: {global_stats['identificados']}")
    log_print(f"  - No identificados: {global_stats['no_identificados']}")
    log_print(f"  - Errores: {global_stats['errores']}")
    log_print(f"  - Tiempo total: {tiempo_total:.2f} segundos")
    
    if global_stats["total"] > 0:
        velocidad = tiempo_total / global_stats["total"]
        log_print(f"  - Velocidad promedio: {velocidad:.2f} segundos por archivo")
    
    return global_stats