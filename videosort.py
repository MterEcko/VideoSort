import os
import requests
import time
import shutil
import json
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

# Configuración
LOGOS_DIR = "logos_estudios"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
CONFIG_FILE = "logos_descargados.json"

# Lista de estudios y cadenas televisivas (amplía según necesites)
ESTUDIOS = [
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
    "IFC Films", "Miramax", "Orion Pictures",
    "Screen Gems", "STX Entertainment"
]

def setup_directory():
    """Crea el directorio para logos si no existe"""
    os.makedirs(LOGOS_DIR, exist_ok=True)
    print(f"Directorio '{LOGOS_DIR}' listo para almacenar logos")
    
    # Crear archivo de seguimiento si no existe
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"descargados": []}, f)

def cargar_estado():
    """Carga el estado de logos ya descargados"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"descargados": []}

def guardar_estado(estado):
    """Guarda el estado de logos descargados"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(estado, f)

def limpiar_nombre_archivo(nombre):
    """Convierte un nombre a un formato válido para nombre de archivo"""
    # Eliminar caracteres no válidos para nombre de archivo
    nombre = ''.join(c for c in nombre if c.isalnum() or c in ' ._-')
    # Reemplazar espacios por guiones bajos
    nombre = nombre.replace(' ', '_')
    return nombre

def buscar_logo_bing(query, max_resultados=3):
    """Busca logos usando Bing y devuelve URLs de imágenes"""
    search_url = f"https://www.bing.com/images/search?q={quote_plus(query)}+logo+transparent+png&form=HDRSC2&first=1"
    
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"Error en la búsqueda: {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Bing almacena las URLs en atributos 'src' o 'data-src' de las etiquetas img
        img_tags = soup.find_all('img', class_='mimg')
        
        urls = []
        for img in img_tags[:max_resultados]:
            url = img.get('src') or img.get('data-src')
            if url and not url.startswith('data:'):  # Ignorar data URIs
                urls.append(url)
        
        return urls
    
    except Exception as e:
        print(f"Error buscando imágenes para {query}: {e}")
        return []

def buscar_logo_duckduckgo(query, max_resultados=3):
    """Busca logos usando DuckDuckGo y devuelve URLs de imágenes"""
    search_url = f"https://duckduckgo.com/?q={quote_plus(query)}+logo+transparent+png&t=h_&iax=images&ia=images"
    
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"Error en la búsqueda: {response.status_code}")
            return []
        
        # DuckDuckGo carga las imágenes con JavaScript, así que no podemos extraerlas directamente
        # Buscamos patrones de vdata-src en el HTML
        pattern = r'vqd="([^"]+)"'
        import re
        matches = re.search(pattern, response.text)
        
        if not matches:
            return []
            
        vqd = matches.group(1)
        
        # Ahora hacemos la petición a la API de imágenes
        api_url = f"https://duckduckgo.com/i.js?q={quote_plus(query)}+logo+transparent+png&vqd={vqd}"
        api_response = requests.get(api_url, headers=HEADERS, timeout=10)
        
        if api_response.status_code != 200:
            return []
            
        results = api_response.json()
        
        urls = []
        for result in results.get('results', [])[:max_resultados]:
            image_url = result.get('image')
            if image_url:
                urls.append(image_url)
        
        return urls
        
    except Exception as e:
        print(f"Error buscando imágenes para {query} en DuckDuckGo: {e}")
        return []

def descargar_imagen(url, ruta_destino):
    """Descarga una imagen desde URL y la guarda en la ruta especificada"""
    try:
        response = requests.get(url, stream=True, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            with open(ruta_destino, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            return True
        else:
            print(f"Error descargando imagen: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error en descargar_imagen: {e}")
        return False

def descargar_logos_estudios(estudios=None, max_por_estudio=2):
    """Descarga logos para los estudios especificados"""
    if estudios is None:
        estudios = ESTUDIOS
    
    # Cargar estado
    estado = cargar_estado()
    ya_descargados = estado["descargados"]
    
    # Crear directorio
    setup_directory()
    
    # Para cada estudio
    for estudio in tqdm(estudios, desc="Descargando logos de estudios"):
        # Verificar si ya se ha descargado
        nombre_limpio = limpiar_nombre_archivo(estudio)
        if nombre_limpio in ya_descargados:
            print(f"Logo para {estudio} ya descargado anteriormente, omitiendo...")
            continue
        
        print(f"\nBuscando logo para: {estudio}")
        
        # Buscar con Bing
        urls = buscar_logo_bing(f"{estudio} logo", max_resultados=max_por_estudio)
        
        # Si no hay resultados, intentar con DuckDuckGo
        if not urls:
            print(f"No se encontraron resultados en Bing, intentando con DuckDuckGo...")
            urls = buscar_logo_duckduckgo(f"{estudio} logo", max_resultados=max_por_estudio)
        
        # Descargar imágenes encontradas
        descargada = False
        for i, url in enumerate(urls):
            ruta_destino = os.path.join(LOGOS_DIR, f"{nombre_limpio}_{i+1}.png")
            print(f"Descargando {url} a {ruta_destino}")
            
            if descargar_imagen(url, ruta_destino):
                print(f"Logo para {estudio} descargado como {ruta_destino}")
                descargada = True
                # Guardar estado
                ya_descargados.append(nombre_limpio)
                estado["descargados"] = ya_descargados
                guardar_estado(estado)
        
        if not descargada:
            print(f"No se pudo descargar ningún logo para {estudio}")
        
        # Pausa para evitar bloqueos
        time.sleep(2)
    
    print(f"\nProceso completado. Se descargaron logos para {len(estado['descargados'])} estudios")

def menu_descargar_logos():
    """Menú interactivo para descargar logos"""
    while True:
        print("\n===== DESCARGADOR DE LOGOS =====")
        print("1. Descargar logos de todos los estudios predefinidos")
        print("2. Descargar logos de estudios específicos")
        print("3. Agregar estudio a la lista y descargar su logo")
        print("4. Mostrar estudios disponibles")
        print("5. Salir")
        
        opcion = input("\nSelecciona una opción (1-5): ")
        
        if opcion == "1":
            max_logos = int(input("¿Cuántos logos intentar descargar por estudio? (1-5): ") or "2")
            max_logos = max(1, min(5, max_logos))  # Limitar entre 1 y 5
            descargar_logos_estudios(max_por_estudio=max_logos)
        
        elif opcion == "2":
            print("Ingresa los nombres de estudios separados por comas:")
            estudios_input = input()
            estudios = [e.strip() for e in estudios_input.split(',') if e.strip()]
            
            if estudios:
                max_logos = int(input("¿Cuántos logos intentar descargar por estudio? (1-5): ") or "2")
                max_logos = max(1, min(5, max_logos))  # Limitar entre 1 y 5
                descargar_logos_estudios(estudios, max_por_estudio=max_logos)
            else:
                print("No ingresaste ningún estudio válido")
        
        elif opcion == "3":
            nuevo_estudio = input("Ingresa el nombre del nuevo estudio: ")
            if nuevo_estudio.strip():
                ESTUDIOS.append(nuevo_estudio.strip())
                print(f"'{nuevo_estudio}' agregado a la lista")
                descargar_logos_estudios([nuevo_estudio.strip()], max_por_estudio=3)
            else:
                print("Nombre de estudio no válido")
        
        elif opcion == "4":
            print("\nESTUDIOS DISPONIBLES:")
            for i, estudio in enumerate(ESTUDIOS, 1):
                print(f"{i}. {estudio}")
        
        elif opcion == "5":
            print("Saliendo del programa...")
            break
        
        else:
            print("Opción no válida. Por favor, selecciona una opción del 1 al 5.")

# Función para verificar y renombrar logos
def organizar_logos():
    """Verifica los logos descargados y los reorganiza para facilitar su uso"""
    # Verificar que el directorio existe
    if not os.path.exists(LOGOS_DIR):
        print(f"El directorio {LOGOS_DIR} no existe")
        return
    
    # Listar todos los archivos en el directorio
    archivos = os.listdir(LOGOS_DIR)
    logos = [f for f in archivos if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    
    if not logos:
        print("No se encontraron archivos de imagen en el directorio")
        return
    
    print(f"Se encontraron {len(logos)} archivos de imagen")
    
    # Para cada estudio en la lista
    for estudio in ESTUDIOS:
        nombre_limpio = limpiar_nombre_archivo(estudio)
        
        # Buscar archivos que coincidan con el patrón del estudio
        coincidencias = [f for f in logos if f.startswith(f"{nombre_limpio}_")]
        
        if coincidencias:
            # Tomar el primer archivo y renombrarlo al formato estándar
            mejor_archivo = coincidencias[0]  # Podríamos implementar un algoritmo más sofisticado aquí
            nuevo_nombre = f"{nombre_limpio}.png"
            
            # Si ya existe un archivo con ese nombre, no sobrescribir
            if nuevo_nombre in logos:
                print(f"Ya existe un archivo {nuevo_nombre}, omitiendo...")
                continue
            
            # Renombrar
            ruta_origen = os.path.join(LOGOS_DIR, mejor_archivo)
            ruta_destino = os.path.join(LOGOS_DIR, nuevo_nombre)
            
            try:
                shutil.copy2(ruta_origen, ruta_destino)
                print(f"Renombrado: {mejor_archivo} -> {nuevo_nombre}")
            except Exception as e:
                print(f"Error renombrando {mejor_archivo}: {e}")
    
    print("Proceso de organización completado")

# Función principal
if __name__ == "__main__":
    menu_descargar_logos()
    
    # Preguntar si desea organizar los logos
    print("\n¿Deseas organizar los logos descargados? (s/n)")
    respuesta = input().lower()
    if respuesta == 's':
        organizar_logos()