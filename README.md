VideoSort

VideoSort es un sistema automatizado para organizar archivos de video (películas y series) mediante análisis de contenido, reconocimiento facial de actores, detección de logos de estudios, y consultas a APIs como The Movie Database (TMDb) y TheTVDB. Clasifica videos en carpetas estructuradas como Movies/Título (Año)/ para películas y Shows/Serie (Año)/Season XX/ para series, optimizado para sistemas como Jellyfin.

Características





Identifica películas y series usando TMDb y TheTVDB.



Detecta actores mediante reconocimiento facial con face_recognition.



Reconoce estudios/cadenas con OCR (pytesseract) y análisis de logos.



Analiza fotogramas para extraer texto (títulos, créditos) y metadatos.



Organiza archivos con nombres como Título (Año) [Calidad].ext o Serie SXXEXX [Calidad].ext.



Soporta procesamiento en lotes y acceso a unidades de red (Z:\).



Registra actores detectados en un CSV (actors_videos.csv).

Instalación





Clona el repositorio:

git clone https://github.com/MterEcko/VideoSort.git
cd VideoSort



Instala las dependencias:

pip install opencv-python pytesseract face_recognition requests beautifulsoup4 tqdm



Instala herramientas externas:





FFmpeg y FFprobe:





Windows: Descarga desde ffmpeg.org y añade al PATH.



Linux: sudo apt-get install ffmpeg



macOS: brew install ffmpeg



Tesseract OCR:





Windows: Descarga desde GitHub.



Linux: sudo apt-get install tesseract-ocr



macOS: brew install tesseract



Configura la unidad de red:





Asegúrate de que \\10.10.1.111\compartida\mp4 esté mapeada como Z:\ con las credenciales en config/config.json.

Uso





Ejecuta el script principal:

python run.py



Usa el menú interactivo para:





Opción 1: Verificar configuración y dependencias.



Opción 2: Gestionar actores (importar lista, descargar populares, generar base de datos).



Opción 3: Gestionar logos de estudios.



Opción 5: Procesar videos (individual o en lotes).



Los videos procesados se mueven a:





Movies/Título (Año)/ para películas.



Shows/Serie (Año)/Season XX/ para series.



Unknown/ para archivos no identificados.



Revisa el CSV C:\Scripts\output\actors_videos.csv para actores detectados.



Consulta los logs en logs/ para diagnósticos (videosort_YYYYMMDD_HHMMSS.log).

Configuración

El archivo config/config.json define:





Claves de API: TMDb y TheTVDB (advertencia: están expuestas, considera protegerlas).



Unidad de red: \\10.10.1.111\compartida\mp4 mapeada como Z:\.



Procesamiento:





"video_extensions": .mp4, .mkv, .mov, .avi.



"max_processes": 4 procesos paralelos.



"capture_frames": Extrae 30 fotogramas por video.



"detect_actors": Activa reconocimiento facial.



"detect_studios": Activa detección de logos.



"min_confidence": 0.6 (sugiero 0.7 para mejor precisión).



Salida: Directorios Movies, Shows, Unknown, ByStudio.

Para mejorar el nombrado:





Cambia "min_confidence": 0.7 para reducir falsos positivos en actores.



Opcionalmente, activa "analyze_audio": true para extraer subtítulos.

Estructura del Proyecto





run.py: Menú interactivo principal.



config.py y config/config.json: Gestión de configuración.



video_analysis.py: Extracción de fotogramas y OCR.



actor_detect.py y actor_db.py: Reconocimiento y gestión de actores.



studio_detect.py y logo_db.py: Detección y gestión de estudios.



tmdb_api.py: Consultas a TMDb para metadatos.



files_ops.py: Movimiento y renombrado de archivos.



utils.py: Funciones auxiliares (logging, limpieza de nombres).



videosort.py: Lógica principal de clasificación.

Requisitos





Python: 3.8+



Bibliotecas: opencv-python, pytesseract, face_recognition, requests, beautifulsoup4, tqdm



Herramientas: ffmpeg, ffprobe, Tesseract OCR



APIs: Claves válidas para TMDb y TheTVDB



Red: Acceso a Z:\ (\\10.10.1.111\compartida\mp4)

Solución de Problemas





Actores detectados incorrectamente (ej. Jean-Claude Van Damme y Jackie Chan juntos):





Regenera la base de datos de actores:





Usa run.py (opción 2, submenú 2) para descargar actores populares, incluyendo a Eddie Murphy.



Verifica que data/actors/ tenga imágenes claras.



Aumenta "min_confidence": 0.7 en config.json.



Revisa logs/ para errores en face_recognition.



Títulos incorrectos (ej. Candy Cane Lane identificado como Rock & Roll Hall of Fame):





Asegúrate de que data/actors_db.json incluya actores relevantes (ej. Eddie Murphy).



Habilita "analyze_audio": true para extraer subtítulos.



Verifica los fotogramas en temp/ (modo debug activado) para confirmar qué texto OCR se extrae.



Revisa logs/ para errores en consultas a TMDb.



Errores de red: Confirma que Z:\ esté accesible con las credenciales en config.json.



Dependencias: Instala face_recognition y dlib si faltan:

pip install face_recognition

Advertencia de Seguridad

Las claves de API y credenciales en config/config.json están expuestas en un repositorio público. Esto puede permitir acceso no autorizado a las APIs o la unidad de red. Considera:





Invalidar las claves actuales en TMDb/TheTVDB y generar nuevas.



Mover claves a un archivo .env (requiere instalar python-dotenv).

Licencia

MIT

Contacto

MterEcko para soporte o contribuciones.
