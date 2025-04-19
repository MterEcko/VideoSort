"""
Funciones para reconocimiento facial de actores
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
    log_print("OpenCV no disponible. Reconocimiento facial desactivado.", logging.WARNING)

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    log_print("face_recognition no disponible. Reconocimiento facial desactivado.", logging.WARNING)

def load_actors_db(db_file):
    """
    Carga la base de datos de encodings faciales de actores
    
    Args:
        db_file: Ruta al archivo de base de datos
        
    Returns:
        Diccionario con el formato {nombre_actor: [lista_de_encodings]}
    """
    if not os.path.exists(db_file):
        log_print(f"Base de datos de actores {db_file} no encontrada", logging.WARNING)
        return {}
    
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_print(f"Error cargando base de datos de actores: {e}", logging.ERROR)
        return {}

def detect_faces(image):
    """
    Detecta rostros en una imagen
    
    Args:
        image: Imagen (matriz numpy) donde buscar rostros
        
    Returns:
        Lista de ubicaciones de rostros (top, right, bottom, left)
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return []
    
    try:
        # Convertir imagen de OpenCV a formato face_recognition
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detectar ubicaciones de rostros
        face_locations = face_recognition.face_locations(rgb_image)
        return face_locations
    
    except Exception as e:
        log_print(f"Error en detección de rostros: {e}", logging.ERROR)
        return []

def recognize_actors(image, actors_db, min_confidence=0.6):
    """
    Detecta rostros en la imagen y los compara con base de datos de actores
    
    Args:
        image: Imagen (matriz numpy) donde buscar rostros
        actors_db: Diccionario con encodings de actores
        min_confidence: Umbral mínimo de confianza (0.0-1.0)
        
    Returns:
        Lista de nombres de actores reconocidos
    """
    if not FACE_RECOGNITION_AVAILABLE or not actors_db:
        return []
    
    try:
        # Convertir imagen de OpenCV a formato face_recognition
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detectar ubicaciones de rostros
        face_locations = face_recognition.face_locations(rgb_image)
        
        if not face_locations:
            return []
        
        # Extraer encodings de los rostros
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        # Lista para almacenar actores reconocidos
        recognized_actors = []
        
        # Para cada rostro detectado
        for face_encoding in face_encodings:
            # Comparar con cada actor en la base de datos
            for actor_name, actor_encodings in actors_db.items():
                for actor_encoding in actor_encodings:
                    # Convertir de lista a numpy array
                    actor_encoding_array = np.array(actor_encoding)
                    
                    # Comparar rostros
                    matches = face_recognition.compare_faces(
                        [actor_encoding_array], face_encoding, tolerance=min_confidence
                    )
                    
                    if matches[0]:
                        if actor_name not in recognized_actors:
                            recognized_actors.append(actor_name)
                            break
        
        return recognized_actors
    
    except Exception as e:
        log_print(f"Error en reconocimiento facial: {e}", logging.ERROR)
        return []

def detect_actors_in_frames(frame_files, actors_db, min_confidence=0.6):
    """
    Detecta actores en múltiples fotogramas
    
    Args:
        frame_files: Lista de rutas a fotogramas
        actors_db: Diccionario con encodings de actores
        min_confidence: Umbral mínimo de confianza (0.0-1.0)
        
    Returns:
        Lista de actores detectados
    """
    all_detected_actors = []
    
    for frame_file in frame_files:
        try:
            frame = cv2.imread(frame_file)
            if frame is None:
                continue
                
            detected = recognize_actors(frame, actors_db, min_confidence)
            
            for actor in detected:
                if actor not in all_detected_actors:
                    all_detected_actors.append(actor)
                    
        except Exception as e:
            log_print(f"Error procesando {frame_file}: {e}", logging.ERROR)
    
    return all_detected_actors

def mark_faces_in_image(image, face_locations, recognized_names=None):
    """
    Marca los rostros detectados en una imagen
    
    Args:
        image: Imagen (matriz numpy) donde marcar los rostros
        face_locations: Lista de ubicaciones de rostros (top, right, bottom, left)
        recognized_names: Lista de nombres para cada rostro (opcional)
        
    Returns:
        Imagen con los rostros marcados
    """
    if not CV2_AVAILABLE:
        return image
    
    # Crear copia para no modificar la original
    image_copy = image.copy()
    
    for i, (top, right, bottom, left) in enumerate(face_locations):
        # Dibujar rectángulo alrededor del rostro
        cv2.rectangle(image_copy, (left, top), (right, bottom), (0, 0, 255), 2)
        
        # Si hay nombres reconocidos, mostrarlos
        if recognized_names and i < len(recognized_names):
            name = recognized_names[i]
            # Colocar texto debajo del rostro
            cv2.putText(image_copy, name, (left, bottom + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
    
    return image_copy

def save_actor_recognition_results(frame_file, actors, output_dir):
    """
    Guarda imagen con actores marcados y registra resultados
    
    Args:
        frame_file: Ruta al fotograma analizado
        actors: Lista de actores detectados
        output_dir: Directorio para guardar resultados
        
    Returns:
        Ruta al archivo generado o None si hay error
    """
    if not CV2_AVAILABLE or not FACE_RECOGNITION_AVAILABLE:
        return None
    
    try:
        # Crear directorio si no existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Cargar imagen
        frame = cv2.imread(frame_file)
        if frame is None:
            return None
        
        # Detectar rostros
        face_locations = detect_faces(frame)
        
        # Marcar rostros con nombres de actores
        marked_frame = mark_faces_in_image(frame, face_locations, actors)
        
        # Generar nombre de archivo
        base_name = os.path.basename(frame_file)
        output_file = os.path.join(output_dir, f"detected_{base_name}")
        
        # Guardar imagen
        cv2.imwrite(output_file, marked_frame)
        
        return output_file
        
    except Exception as e:
        log_print(f"Error guardando resultados de reconocimiento: {e}", logging.ERROR)
        return None