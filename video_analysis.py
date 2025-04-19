"""
Funciones para analizar videos (calidad, subtítulos, OCR)
"""

import os
import subprocess
import logging
import re
from utils import log_print

# Verificar disponibilidad de módulos opcionales
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    log_print("OpenCV no disponible. Algunas funcionalidades estarán limitadas.", logging.WARNING)

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    log_print("pytesseract no disponible. Reconocimiento de texto en imágenes desactivado.", logging.WARNING)

def get_video_quality(filepath):
    """
    Determina la calidad del video basado en su resolución
    
    Args:
        filepath: Ruta al archivo de video
        
    Returns:
        String con la calidad (2160p, 1080p, 720p, 480p, Unknown)
    """
    if not CV2_AVAILABLE:
        return "Unknown"
    
    try:
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            log_print(f"No se pudo abrir el archivo {filepath}", logging.WARNING)
            return "Unknown"
        
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cap.release()
        
        if height >= 2160:
            return "2160p"
        elif height >= 1080:
            return "1080p"
        elif height >= 720:
            return "720p"
        return "480p"
    except Exception as e:
        log_print(f"Error obteniendo calidad de {filepath}: {e}", logging.ERROR)
        return "Unknown"

def get_video_duration(filepath):
    """
    Obtiene la duración del video en segundos
    
    Args:
        filepath: Ruta al archivo de video
        
    Returns:
        Duración en segundos (float) o None si hay error
    """
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
              "-of", "default=noprint_wrappers=1:nokey=1", filepath]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return duration
        else:
            log_print(f"Error obteniendo duración: {result.stderr}", logging.ERROR)
            return None
    except Exception as e:
        log_print(f"Error en get_video_duration: {e}", logging.ERROR)
        return None

def extract_subtitles(filepath, temp_dir):
    """
    Extrae subtítulos incrustados del video
    
    Args:
        filepath: Ruta al archivo de video
        temp_dir: Directorio para archivos temporales
        
    Returns:
        Texto de los subtítulos o cadena vacía si no hay subtítulos
    """
    subtitles_file = os.path.join(temp_dir, "subtitles.srt")
    
    try:
        subprocess.run([
            "ffmpeg", "-i", filepath, "-map", "s:0", subtitles_file
        ], capture_output=True)
        
        if not os.path.exists(subtitles_file):
            log_print(f"No se encontraron subtítulos en {filepath}", logging.DEBUG)
            return ""
            
        with open(subtitles_file, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        log_print(f"Error extrayendo subtítulos de {filepath}: {e}", logging.ERROR)
        return ""
    finally:
        if os.path.exists(subtitles_file):
            try:
                os.remove(subtitles_file)
            except Exception:
                pass

def extract_frames(filepath, temp_dir, timestamps=None):
    """
    Extrae fotogramas específicos del video
    
    Args:
        filepath: Ruta al archivo de video
        temp_dir: Directorio para guardar los fotogramas
        timestamps: Lista de tiempos (en segundos) para extraer fotogramas. 
                   Si es None, se usan tiempos predeterminados
    
    Returns:
        Lista de rutas a los fotogramas extraídos
    """
    if not os.path.exists(filepath):
        log_print(f"El archivo {filepath} no existe", logging.ERROR)
        return []
    
    os.makedirs(temp_dir, exist_ok=True)
    
    # Si no se especifican tiempos, calcular automáticamente
    if timestamps is None:
        duration = get_video_duration(filepath)
        if not duration:
            return []
        
        # Para videos cortos (menos de 5 min)
        if duration < 300:
            timestamps = [
                30,                 # Inicio (posible título)
                duration * 0.25,    # 25%
                duration * 0.5,     # Mitad
                duration * 0.75,    # 75%
                max(0, duration - 60)  # Final (posibles créditos)
            ]
        else:
            timestamps = [
                30,                  # Inicio
                120,                 # 2 minutos
                300,                 # 5 minutos
                600,                 # 10 minutos
                duration * 0.25,     # 25%
                duration * 0.5,      # Mitad
                duration * 0.75,     # 75%
                max(0, duration - 300),  # 5 min antes del final
                max(0, duration - 60)    # 1 min antes del final
            ]
        
        # Filtrar tiempos válidos y eliminar duplicados
        timestamps = sorted(list(set([int(t) for t in timestamps if t < duration])))
    
    # Extraer cada fotograma
    frame_files = []
    for t in timestamps:
        frame_file = os.path.join(temp_dir, f"frame_{t}.png")
        
        try:
            result = subprocess.run([
                "ffmpeg", "-i", filepath, "-ss", str(t), "-vframes", "1", frame_file
            ], capture_output=True)
            
            if os.path.exists(frame_file) and os.path.getsize(frame_file) > 0:
                frame_files.append(frame_file)
            else:
                log_print(f"No se pudo extraer fotograma en {t}s", logging.WARNING)
        except Exception as e:
            log_print(f"Error extrayendo fotograma en {t}s: {e}", logging.ERROR)
    
    return frame_files

def extract_audio_sample(filepath, temp_dir, start_time=30, duration=10):
    """
    Extrae una muestra de audio del video
    
    Args:
        filepath: Ruta al archivo de video
        temp_dir: Directorio para archivos temporales
        start_time: Tiempo de inicio en segundos
        duration: Duración de la muestra en segundos
        
    Returns:
        Ruta al archivo de audio extraído o None si hay error
    """
    audio_file = os.path.join(temp_dir, "audio_sample.wav")
    
    try:
        subprocess.run([
            "ffmpeg", "-i", filepath, "-ss", str(start_time), "-t", str(duration),
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", audio_file
        ], capture_output=True)
        
        if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
            return audio_file
        else:
            log_print(f"No se pudo extraer audio de {filepath}", logging.WARNING)
            return None
    except Exception as e:
        log_print(f"Error extrayendo audio: {e}", logging.ERROR)
        return None

def perform_ocr_on_frames(frame_files):
    """
    Realiza OCR en los fotogramas extraídos
    
    Args:
        frame_files: Lista de rutas a los fotogramas
        
    Returns:
        Texto extraído de los fotogramas
    """
    if not PYTESSERACT_AVAILABLE or not CV2_AVAILABLE:
        return ""
    
    extracted_text = []
    
    for frame_file in frame_files:
        try:
            # Cargar imagen
            img = cv2.imread(frame_file)
            if img is None:
                continue
            
            # 1. Procesar imagen original
            text1 = pytesseract.image_to_string(img, lang="spa+eng")
            
            # 2. Procesar versión en escala de grises
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            text2 = pytesseract.image_to_string(gray, lang="spa+eng")
            
            # 3. Procesar con umbral adaptativo
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY, 11, 2)
            text3 = pytesseract.image_to_string(thresh, lang="spa+eng")
            
            # Combinar resultados
            combined_text = text1 + " " + text2 + " " + text3
            
            # Filtrar líneas útiles (eliminar líneas muy cortas o con pocas letras)
            useful_lines = []
            for line in combined_text.split('\n'):
                # Contar letras/números (no solo espacios o símbolos)
                letters = sum(1 for c in line if c.isalnum())
                if len(line) > 5 and letters > 3:
                    useful_lines.append(line)
            
            if useful_lines:
                extracted_text.append(' '.join(useful_lines))
        
        except Exception as e:
            log_print(f"Error en OCR para {frame_file}: {e}", logging.ERROR)
    
    return " ".join(extracted_text)

def analyze_video_content(filepath, temp_dir, config):
    """
    Analiza el contenido de un video (subtítulos, fotogramas, etc.)
    
    Args:
        filepath: Ruta al archivo de video
        temp_dir: Directorio para archivos temporales
        config: Configuración del sistema
        
    Returns:
        Diccionario con los resultados del análisis
    """
    results = {
        "subtitles_text": "",
        "ocr_text": "",
        "audio_text": "",
        "duration": 0,
        "quality": "Unknown"
    }
    
    try:
        # Crear directorio temporal si no existe
        os.makedirs(temp_dir, exist_ok=True)
        
        # Obtener calidad y duración
        results["quality"] = get_video_quality(filepath)
        results["duration"] = get_video_duration(filepath) or 0
        
        # Extraer subtítulos
        results["subtitles_text"] = extract_subtitles(filepath, temp_dir)
        
        # Extraer y analizar fotogramas
        if config["processing"]["capture_frames"] and CV2_AVAILABLE and PYTESSERACT_AVAILABLE:
            frame_files = extract_frames(filepath, temp_dir)
            results["ocr_text"] = perform_ocr_on_frames(frame_files)
            
            # Limpiar fotogramas después de procesar
            if not config["processing"]["debug"]:
                for frame_file in frame_files:
                    try:
                        os.remove(frame_file)
                    except:
                        pass
        
        # Extraer y analizar audio (sería necesario un módulo para reconocimiento de voz)
        # Esta parte requeriría integración con un servicio como Whisper de OpenAI
        
        return results
    
    except Exception as e:
        log_print(f"Error analizando contenido de {filepath}: {e}", logging.ERROR)
        return results

def extract_season_episode_from_filename(filename):
    """
    Extrae información de temporada y episodio del nombre del archivo
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        Tupla (temporada, episodio) o (None, None) si no se puede extraer
    """
    # Patrones comunes de temporada/episodio
    patterns = [
        r'S(\d+)E(\d+)',            # S01E01
        r'(\d+)x(\d+)',             # 1x01
        r'[^0-9](\d{1,2})(\d{2})[^0-9]',  # 102 = temporada 1, episodio 2
        r'Season[^0-9]*(\d+)[^0-9]*Episode[^0-9]*(\d+)',  # Season 1 Episode 1
        r'Temporada[^0-9]*(\d+)[^0-9]*Capitulo[^0-9]*(\d+)',  # Temporada 1 Capitulo 1
        r'T(\d+)[^0-9]*C(\d+)',     # T1C01
        r'Temp(\d+)[^0-9]*Cap(\d+)' # Temp1Cap01
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            season, episode = match.groups()
            return int(season), int(episode)
    
    return None, None

def extract_year_from_filename(filename):
    """
    Extrae el año de un nombre de archivo
    
    Args:
        filename: Nombre del archivo
        
    Returns:
        Año como string o None si no se encuentra
    """
    # Buscar patrón de año (4 dígitos entre paréntesis o corchetes)
    patterns = [
        r'\((\d{4})\)',  # (2021)
        r'\[(\d{4})\]',  # [2021]
        r'[^0-9](\d{4})[^0-9]'  # cualquier año aislado
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            year = match.group(1)
            # Validar que sea un año razonable (1900-2099)
            if 1900 <= int(year) <= 2099:
                return year
    
    return None