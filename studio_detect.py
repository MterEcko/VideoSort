"""
Funciones para detectar estudios y cadenas televisivas
"""

import os
import json
import logging
import numpy as np
from utils import log_print

# Verificar dependencias
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    log_print("OpenCV no disponible. Detección de logos desactivada.", logging.WARNING)

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    log_print("pytesseract no disponible. Detección de estudios por texto desactivada.", logging.WARNING)

def load_studios_mapping(mapping_file):
    """
    Carga el mapeo de patrones de texto a estudios
    
    Args:
        mapping_file: Ruta al archivo de mapeo
        
    Returns:
        Diccionario con el mapeo
    """
    # Mapeo predeterminado
    default_mapping = {
        "FOX": ["fox", "20th century fox", "fox searchlight", "fox studios"],
        "HBO": ["hbo", "home box office", "hbo original"],
        "Netflix": ["netflix", "netflix original", "netflix studios"],
        "Disney": ["disney", "walt disney", "disney pictures", "disney+"],
        "Warner": ["warner", "warner bros", "warnermedia", "warner brothers"],
        "Universal": ["universal", "universal pictures", "universal studios"],
        "Paramount": ["paramount", "paramount pictures"],
        "Sony": ["sony", "sony pictures", "columbia pictures"],
        "AMC": ["amc", "amc presents", "amc studios"],
        "CartoonNetwork": ["cartoon network", "adult swim", "cn"],
        "MGM": ["mgm", "metro goldwyn mayer"],
        "Lionsgate": ["lionsgate", "lions gate"],
        "DreamWorks": ["dreamworks", "dreamworks animation"],
        "Pixar": ["pixar", "pixar animation"],
        "BBC": ["bbc", "british broadcasting", "bbc films", "bbc studios"],
        "Showtime": ["showtime", "showtime presents"],
        "Starz": ["starz", "starz original"],
        "CBS": ["cbs", "cbs studios", "cbs films"],
        "NBC": ["nbc", "nbc universal", "nbc studios"],
        "Amazon": ["amazon", "amazon studios", "prime video"]
    }
    
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log_print(f"Error cargando mapeo de estudios: {e}", logging.ERROR)
    
    # Si no existe o hay error, crear archivo con mapeo predeterminado
    try:
        os.makedirs(os.path.dirname(mapping_file), exist_ok=True)
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(default_mapping, f, indent=4)
    except Exception as e:
        log_print(f"Error guardando mapeo de estudios: {e}", logging.ERROR)
    
    return default_mapping

def detect_studio_from_text(ocr_text, studios_mapping):
    """
    Detecta estudio/cadena basado en texto OCR
    
    Args:
        ocr_text: Texto extraído mediante OCR
        studios_mapping: Diccionario de mapeo de estudios
        
    Returns:
        Nombre del estudio o None si no se detecta
    """
    if not ocr_text:
        return None
        
    text_lower = ocr_text.lower()
    
    for studio, patterns in studios_mapping.items():
        for pattern in patterns:
            if pattern in text_lower:
                return studio
    
    return None

def get_logo_files(logos_dir):
    """
    Obtiene la lista de archivos de logos disponibles
    
    Args:
        logos_dir: Directorio donde se almacenan los logos
        
    Returns:
        Lista de tuplas (nombre_estudio, ruta_logo)
    """
    if not os.path.exists(logos_dir):
        log_print(f"Directorio de logos {logos_dir} no existe", logging.WARNING)
        return []
        
    logo_files = []
    
    for filename in os.listdir(logos_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            # El nombre del estudio es el nombre del archivo sin extensión
            studio = os.path.splitext(filename)[0]
            logo_path = os.path.join(logos_dir, filename)
            logo_files.append((studio, logo_path))
    
    return logo_files

def detect_studio_from_logo(image, logos_dir, threshold=0.7):
    """
    Detecta estudio/cadena basado en reconocimiento de logos
    
    Args:
        image: Imagen (matriz numpy) donde buscar logos
        logos_dir: Directorio con imágenes de logos
        threshold: Umbral de coincidencia (0.0-1.0)
        
    Returns:
        Nombre del estudio o None si no se detecta
    """
    if not CV2_AVAILABLE or not os.path.exists(logos_dir):
        return None
    
    try:
        logo_files = get_logo_files(logos_dir)
        
        if not logo_files:
            return None
        
        # Para cada logo, intentar reconocimiento
        matches = []
        
        for studio, logo_path in logo_files:
            # Cargar imagen del logo
            logo_img = cv2.imread(logo_path)
            
            if logo_img is None:
                continue
            
            # Verificar que la imagen del logo sea más pequeña que la imagen del video
            if (logo_img.shape[0] > image.shape[0] or 
                logo_img.shape[1] > image.shape[1]):
                # Redimensionar logo si es necesario
                scale = min(image.shape[0] / logo_img.shape[0], 
                           image.shape[1] / logo_img.shape[1])
                # Reducir un poco más para asegurar que entre
                scale = scale * 0.8
                new_height = int(logo_img.shape[0] * scale)
                new_width = int(logo_img.shape[1] * scale)
                logo_img = cv2.resize(logo_img, (new_width, new_height))
            
            # Si sigue siendo muy grande, continuar con el siguiente
            if (logo_img.shape[0] > image.shape[0] or 
                logo_img.shape[1] > image.shape[1]):
                continue
                
            # Hacer template matching
            result = cv2.matchTemplate(image, logo_img, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                # Agregar a coincidencias con su puntuación
                matches.append((studio, max_val))
        
        # Si hay coincidencias, devolver la mejor
        if matches:
            best_match = max(matches, key=lambda x: x[1])
            return best_match[0]
    
    except Exception as e:
        log_print(f"Error en detección de logo: {e}", logging.ERROR)
    
    return None

def analyze_frame_for_studios(frame, studios_mapping, logos_dir):
    """
    Analiza un fotograma para detectar estudios (por texto y logo)
    
    Args:
        frame: Imagen (matriz numpy) del fotograma
        studios_mapping: Diccionario de mapeo de patrones de texto a estudios
        logos_dir: Directorio con imágenes de logos
        
    Returns:
        Lista de estudios detectados
    """
    detected_studios = []
    
    try:
        # 1. Detectar por OCR
        if PYTESSERACT_AVAILABLE:
            ocr_text = pytesseract.image_to_string(frame, lang="spa+eng")
            studio = detect_studio_from_text(ocr_text, studios_mapping)
            if studio and studio not in detected_studios:
                detected_studios.append(studio)
        
        # 2. Detectar por comparación de logos
        if CV2_AVAILABLE:
            studio = detect_studio_from_logo(frame, logos_dir)
            if studio and studio not in detected_studios:
                detected_studios.append(studio)
                
    except Exception as e:
        log_print(f"Error analizando fotograma para estudios: {e}", logging.ERROR)
    
    return detected_studios

def detect_studios_in_frames(frame_files, studios_mapping, logos_dir):
    """
    Detecta estudios en múltiples fotogramas
    
    Args:
        frame_files: Lista de rutas a fotogramas
        studios_mapping: Diccionario de mapeo de patrones de texto a estudios
        logos_dir: Directorio con imágenes de logos
        
    Returns:
        Lista de estudios detectados
    """
    all_detected_studios = []
    
    for frame_file in frame_files:
        try:
            frame = cv2.imread(frame_file)
            if frame is None:
                continue
                
            detected = analyze_frame_for_studios(frame, studios_mapping, logos_dir)
            
            for studio in detected:
                if studio not in all_detected_studios:
                    all_detected_studios.append(studio)
                    
        except Exception as e:
            log_print(f"Error procesando {frame_file}: {e}", logging.ERROR)
    
    return all_detected_studios