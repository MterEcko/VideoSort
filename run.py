#!/usr/bin/env python
"""
VideoSort - Sistema de identificación y organización de videos
Punto de entrada principal con menús interactivos
"""

import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
import argparse
import logging
from datetime import datetime



# Importar módulos del sistema
from config import load_config, save_config, create_directories, DEFAULT_CONFIG
from config import ACTORS_DIR, LOGOS_DIR, ACTORS_DB_FILE, STUDIOS_MAPPING_FILE, LOGOS_DB_FILE, PROCESSED_CSV_FILE
from config import DATA_DIR, CONFIG_FILE
from utils import log_print, setup_logging, connect_network_drive, check_dependencies
from actor_db import create_actors_db_from_list, generate_encodings_db, get_popular_actors, import_actors_from_file
from logo_db import download_all_logos, create_logos_directory, organize_logos
from process import process_single_video, process_directory
from files_ops import restore_from_backup


def show_header():
    """Muestra cabecera del programa"""
    print("\n" + "="*60)
    print("               VideoSort v1.0")
    print("     Sistema de identificación y organización de videos")
    print("="*60)

def check_system():
    """Verifica el sistema y muestra información de diagnóstico"""
    print("\nVerificando sistema...")
    
    # Comprobar dependencias
    dependencies = check_dependencies()
    
    print("\nDependencias:")
    for dep, installed in dependencies.items():
        status = "✓ INSTALADO" if installed else "✗ NO INSTALADO"
        print(f"  - {dep}: {status}")
    
    # Comprobar directorios
    print("\nDirectorios:")
    dirs_to_check = [
        ("Config", os.path.dirname(CONFIG_FILE)),
        ("Datos", DATA_DIR),
        ("Actores", ACTORS_DIR),
        ("Logos", LOGOS_DIR)
    ]
    
    for name, path in dirs_to_check:
        exists = os.path.exists(path)
        status = "✓ EXISTE" if exists else "✗ NO EXISTE"
        print(f"  - {name}: {status} ({path})")
    
    # Comprobar bases de datos
    print("\nBases de datos:")
    dbs_to_check = [
        ("Actores", ACTORS_DB_FILE),
        ("Logos", LOGOS_DB_FILE)
    ]
    
    for name, path in dbs_to_check:
        exists = os.path.exists(path)
        status = "✓ EXISTE" if exists else "✗ NO EXISTE"
        if exists:
            size = os.path.getsize(path)
            size_str = f"{size/1024:.1f} KB"
            print(f"  - {name}: {status} ({size_str})")
        else:
            print(f"  - {name}: {status}")
    
    # Verificar acceso a red si está configurado
    config = load_config()
    if config["network"]["path"]:
        print("\nAcceso a red:")
        drive = connect_network_drive(config)
        if drive:
            print(f"  - Unidad de red: ✓ CONECTADA ({drive})")
        else:
            print(f"  - Unidad de red: ✗ NO CONECTADA ({config['network']['path']})")
    
    print("\nSistema verificado.")

def menu_configuracion():
    """Menú para configuración del sistema"""
    config = load_config()
    
    while True:
        print("\n===== CONFIGURACIÓN =====")
        print("1. Configurar API keys")
        print("2. Configurar acceso a red")
        print("3. Configurar procesamiento")
        print("4. Configurar organización")
        print("5. Restaurar configuración predeterminada")
        print("6. Volver al menú principal")
        
        opcion = input("\nSeleccione una opción (1-6): ")
        
        if opcion == "1":
            # Configurar API keys
            print("\n--- API Keys ---")
            print(f"TMDb actual: {config['api_keys']['tmdb']}")
            print(f"TheTVDB actual: {config['api_keys']['thetvdb']}")
            
            nueva_tmdb = input("Nueva API key para TMDb (dejar vacío para mantener): ")
            if nueva_tmdb:
                config["api_keys"]["tmdb"] = nueva_tmdb
            
            nueva_tvdb = input("Nueva API key para TheTVDB (dejar vacío para mantener): ")
            if nueva_tvdb:
                config["api_keys"]["thetvdb"] = nueva_tvdb
            
            save_config(config)
            print("API keys actualizadas.")
        
        elif opcion == "2":
            # Configurar acceso a red
            print("\n--- Acceso a Red ---")
            print(f"Ruta actual: {config['network']['path']}")
            print(f"Usuario actual: {config['network']['user']}")
            print(f"Letra de unidad actual: {config['network']['drive_letter']}")
            
            nueva_ruta = input("Nueva ruta de red (dejar vacío para mantener): ")
            if nueva_ruta:
                config["network"]["path"] = nueva_ruta
            
            nuevo_usuario = input("Nuevo usuario (dejar vacío para mantener): ")
            if nuevo_usuario:
                config["network"]["user"] = nuevo_usuario
                config["network"]["password"] = input("Nueva contraseña: ")
            
            nueva_letra = input("Nueva letra de unidad (dejar vacío para mantener): ")
            if nueva_letra:
                config["network"]["drive_letter"] = nueva_letra
            
            save_config(config)
            print("Configuración de red actualizada.")
        
        elif opcion == "3":
            # Configurar procesamiento
            print("\n--- Procesamiento ---")
            print(f"Procesos máximos: {config['processing']['max_processes']}")
            print(f"Modo debug: {'Activado' if config['processing']['debug'] else 'Desactivado'}")
            print(f"Captura de fotogramas: {'Activada' if config['processing']['capture_frames'] else 'Desactivada'}")
            print(f"Detección de actores: {'Activada' if config['processing']['detect_actors'] else 'Desactivada'}")
            print(f"Detección de estudios: {'Activada' if config['processing']['detect_studios'] else 'Desactivada'}")
            print(f"Renombrar archivos: {'Activado' if config['processing']['rename_files'] else 'Desactivado'}")
            
            try:
                nuevos_procesos = input("Número máximo de procesos (dejar vacío para mantener): ")
                if nuevos_procesos:
                    config["processing"]["max_processes"] = int(nuevos_procesos)
                
                nuevo_debug = input("Activar modo debug (s/n, dejar vacío para mantener): ").lower()
                if nuevo_debug in ['s', 'n']:
                    config["processing"]["debug"] = (nuevo_debug == 's')
                
                nueva_captura = input("Activar captura de fotogramas (s/n, dejar vacío para mantener): ").lower()
                if nueva_captura in ['s', 'n']:
                    config["processing"]["capture_frames"] = (nueva_captura == 's')
                
                nueva_deteccion_actores = input("Activar detección de actores (s/n, dejar vacío para mantener): ").lower()
                if nueva_deteccion_actores in ['s', 'n']:
                    config["processing"]["detect_actors"] = (nueva_deteccion_actores == 's')
                
                nueva_deteccion_estudios = input("Activar detección de estudios (s/n, dejar vacío para mantener): ").lower()
                if nueva_deteccion_estudios in ['s', 'n']:
                    config["processing"]["detect_studios"] = (nueva_deteccion_estudios == 's')
                
                nuevo_renombrar = input("Activar renombrado de archivos (s/n, dejar vacío para mantener): ").lower()
                if nuevo_renombrar in ['s', 'n']:
                    config["processing"]["rename_files"] = (nuevo_renombrar == 's')
                
                save_config(config)
                print("Configuración de procesamiento actualizada.")
            except ValueError:
                print("Error: Valor no válido.")
        
        elif opcion == "4":
            # Configurar organización
            print("\n--- Organización ---")
            print(f"Directorio de películas: {config['output']['movies_dir']}")
            print(f"Directorio de series: {config['output']['shows_dir']}")
            print(f"Directorio de desconocidos: {config['output']['unknown_dir']}")
            print(f"Directorio de estudios: {config['output']['studios_dir']}")
            
            nuevo_movies = input("Nuevo directorio de películas (dejar vacío para mantener): ")
            if nuevo_movies:
                config["output"]["movies_dir"] = nuevo_movies
            
            nuevo_shows = input("Nuevo directorio de series (dejar vacío para mantener): ")
            if nuevo_shows:
                config["output"]["shows_dir"] = nuevo_shows
            
            nuevo_unknown = input("Nuevo directorio de desconocidos (dejar vacío para mantener): ")
            if nuevo_unknown:
                config["output"]["unknown_dir"] = nuevo_unknown
            
            nuevo_studios = input("Nuevo directorio de estudios (dejar vacío para mantener): ")
            if nuevo_studios:
                config["output"]["studios_dir"] = nuevo_studios
            
            save_config(config)
            print("Configuración de organización actualizada.")
        
        elif opcion == "5":
            # Restaurar configuración predeterminada
            confirmacion = input("¿Está seguro de restaurar la configuración predeterminada? (s/n): ").lower()
            if confirmacion == 's':
                save_config(DEFAULT_CONFIG)
                config = load_config()
                print("Configuración restaurada a valores predeterminados.")
        
        elif opcion == "6":
            # Volver al menú principal
            break
        
        else:
            print("Opción no válida.")

def menu_actores():
    """Menú para gestión de base de datos de actores"""
    config = load_config()
    
    while True:
        print("\n===== GESTIÓN DE ACTORES =====")
        print("1. Crear base de datos con lista manual")
        print("2. Importar actores desde archivo de texto")
        print("3. Obtener actores populares automáticamente")
        print("4. Generar encodings faciales")
        print("5. Ver actores en base de datos")
        print("6. Volver al menú principal")
        
        opcion = input("\nSeleccione una opción (1-6): ")
        
        if opcion == "1":
            # Lista manual
            print("\nIngresa nombres de actores separados por comas:")
            input_actores = input()
            lista_actores = [a.strip() for a in input_actores.split(',') if a.strip()]
            
            if lista_actores:
                print(f"Se procesarán {len(lista_actores)} actores.")
                create_actors_db_from_list(lista_actores, ACTORS_DIR, config)
            else:
                print("No se ingresaron nombres válidos.")
        
        elif opcion == "2":
            # Importar desde archivo
            ruta_archivo = input("Ingresa la ruta del archivo de texto con nombres de actores: ")
            if os.path.exists(ruta_archivo):
                actores = import_actors_from_file(ruta_archivo)
                if actores:
                    create_actors_db_from_list(actores, ACTORS_DIR, config)
            else:
                print(f"El archivo {ruta_archivo} no existe")
        
        elif opcion == "3":
            # Obtener actores populares
            try:
                cantidad = int(input("¿Cuántos actores populares deseas obtener? (recomendado: 50-100): ") or "50")
                actores = get_popular_actors(config, cantidad)
                if actores:
                    print(f"Se obtuvieron {len(actores)} actores")
                    create_actors_db_from_list(actores, ACTORS_DIR, config)
            except ValueError:
                print("Por favor ingresa un número válido")
        
        elif opcion == "4":
            # Generar encodings
            print("Generando encodings faciales (puede tardar varios minutos)...")
            generate_encodings_db(ACTORS_DIR, ACTORS_DB_FILE)
        
        elif opcion == "5":
            # Ver actores en base de datos
            if os.path.exists(ACTORS_DB_FILE):
                import json
                try:
                    with open(ACTORS_DB_FILE, 'r', encoding='utf-8') as f:
                        db = json.load(f)
                    print(f"\nActores en base de datos ({len(db)} total):")
                    for i, actor in enumerate(sorted(db.keys()), 1):
                        if i % 5 == 0:  # 5 por línea
                            print(f"{actor}")
                        else:
                            print(f"{actor}", end=", ")
                    print()
                except Exception as e:
                    print(f"Error cargando base de datos: {e}")
            else:
                print("La base de datos de actores aún no existe.")
        
        elif opcion == "6":
            # Volver al menú principal
            break
        
        else:
            print("Opción no válida.")

def menu_logos():
    """Menú para gestión de logos de estudios"""
    while True:
        print("\n===== GESTIÓN DE LOGOS =====")
        print("1. Crear directorio de logos")
        print("2. Descargar logos de estudios predefinidos")
        print("3. Descargar logos de estudios específicos")
        print("4. Organizar logos descargados")
        print("5. Ver logos disponibles")
        print("6. Volver al menú principal")
        
        opcion = input("\nSeleccione una opción (1-6): ")
        
        if opcion == "1":
            # Crear directorio
            create_logos_directory(LOGOS_DIR)
            print(f"Directorio de logos creado en {LOGOS_DIR}")
        
        elif opcion == "2":
            # Descargar logos predefinidos
            max_logos = int(input("¿Cuántos logos intentar descargar por estudio? (1-5): ") or "2")
            max_logos = max(1, min(5, max_logos))  # Limitar entre 1 y 5
            print("Descargando logos (esto puede tardar varios minutos)...")
            download_all_logos(LOGOS_DIR)
        
        elif opcion == "3":
            # Descargar logos específicos
            print("Ingresa los nombres de estudios separados por comas:")
            estudios_input = input()
            estudios = [e.strip() for e in estudios_input.split(',') if e.strip()]
            
            if estudios:
                max_logos = int(input("¿Cuántos logos intentar descargar por estudio? (1-5): ") or "2")
                max_logos = max(1, min(5, max_logos))  # Limitar entre 1 y 5
                print("Descargando logos (esto puede tardar varios minutos)...")
                download_all_logos(LOGOS_DIR, estudios)
            else:
                print("No ingresaste ningún estudio válido")
        
        elif opcion == "4":
            # Organizar logos
            print("Organizando logos descargados...")
            organize_logos(LOGOS_DIR, STUDIOS_MAPPING_FILE)
        
        elif opcion == "5":
            # Ver logos disponibles
            if os.path.exists(LOGOS_DIR):
                logos = [f for f in os.listdir(LOGOS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if logos:
                    print(f"\nLogos disponibles ({len(logos)} total):")
                    for i, logo in enumerate(sorted(logos), 1):
                        nombre = os.path.splitext(logo)[0].replace('_', ' ')
                        if i % 3 == 0:  # 3 por línea
                            print(f"{nombre}")
                        else:
                            print(f"{nombre}", end=", ")
                    print()
                else:
                    print("No hay logos disponibles.")
            else:
                print(f"El directorio {LOGOS_DIR} no existe.")
        
        elif opcion == "6":
            # Volver al menú principal
            break
        
        else:
            print("Opción no válida.")

def menu_procesamiento():
    """Menú para procesamiento de videos"""
    config = load_config()
    
    while True:
        print("\n===== PROCESAMIENTO DE VIDEOS =====")
        print("1. Procesar un solo archivo")
        print("2. Procesar directorio (modo directo)")
        print("3. Procesar directorio (modo recursivo)")
        print("4. Procesar directorio con lotes")
        print("5. Restaurar archivos desde respaldo")
        print("6. Volver al menú principal")
        
        opcion = input("\nSeleccione una opción (1-6): ")
        
        if opcion == "1":
            # Procesar archivo individual
            ruta_archivo = input("Ingresa la ruta completa del archivo a procesar: ")
            if os.path.exists(ruta_archivo) and os.path.isfile(ruta_archivo):
                print(f"Procesando archivo: {ruta_archivo}")
                resultado = process_single_video(ruta_archivo, config)
                
                if resultado["identificado"]:
                    tipo = "Película" if resultado["es_pelicula"] else "Serie"
                    if resultado["es_pelicula"]:
                        titulo = resultado["info"].get("title", "Desconocido")
                        year = resultado["info"].get("release_date", "")[:4] if resultado["info"].get("release_date") else "Desconocido"
                    else:
                        titulo = resultado["info"].get("name", "Desconocido")
                        year = resultado["info"].get("first_air_date", "")[:4] if resultado["info"].get("first_air_date") else "Desconocido"
                    
                    print(f"\nResultado: ✓ IDENTIFICADO")
                    print(f"Tipo: {tipo}")
                    print(f"Título: {titulo} ({year})")
                    if "detected_actors" in resultado and resultado["detected_actors"]:
                        print(f"Actores detectados: {', '.join(resultado['detected_actors'])}")
                    if "detected_studios" in resultado and resultado["detected_studios"]:
                        print(f"Estudios detectados: {', '.join(resultado['detected_studios'])}")
                else:
                    print(f"\nResultado: ✗ NO IDENTIFICADO")
                    if "mensaje" in resultado:
                        print(f"Mensaje: {resultado['mensaje']}")
                    if "detected_studios" in resultado and resultado["detected_studios"]:
                        print(f"Estudios detectados: {', '.join(resultado['detected_studios'])}")
            else:
                print(f"El archivo {ruta_archivo} no existe o no es un archivo válido")
        
        elif opcion in ["2", "3", "4"]:
            # Procesar directorio
            ruta_dir = input("Ingresa la ruta del directorio a procesar: ")
            if os.path.exists(ruta_dir) and os.path.isdir(ruta_dir):
                # Conectar unidad de red si es necesario
                if config["network"]["path"]:
                    drive = connect_network_drive(config)
                    if not drive and ruta_dir.startswith(config["network"]["drive_letter"]):
                        print("Error: No se pudo conectar a la unidad de red.")
                        continue
                
                # Determinar modo
                if opcion == "2":
                    modo = "direct"
                    print(f"Procesando directorio en modo directo: {ruta_dir}")
                elif opcion == "3":
                    modo = "default"
                    print(f"Procesando directorio en modo recursivo: {ruta_dir}")
                else:
                    modo = "batch"
                    print(f"Procesando directorio con lotes: {ruta_dir}")
                
                # Procesar
                stats = process_directory(ruta_dir, config, recursive=(opcion == "3"), mode=modo)
                
                # Mostrar resultados
                if "error" in stats:
                    print(f"Error: {stats['error']}")
                else:
                    print("\nProcesamiento completado.")
            else:
                print(f"El directorio {ruta_dir} no existe")
        
        elif opcion == "5":
            # Restaurar desde respaldo
            if os.path.exists(PROCESSED_CSV_FILE):
                print(f"Usando archivo de respaldo principal: {PROCESSED_CSV_FILE}")
                restore_from_backup(PROCESSED_CSV_FILE)
            else:
                # Buscar archivos de respaldo por lotes
                respaldos = [f for f in os.listdir('.') if f.startswith(os.path.basename(PROCESSED_CSV_FILE) + ".")]
                
                if respaldos:
                    print("Se encontraron los siguientes archivos de respaldo:")
                    for i, respaldo in enumerate(respaldos, 1):
                        print(f"{i}. {respaldo}")
                    
                    try:
                        seleccion = int(input("Selecciona un archivo de respaldo (número) o 0 para todos: "))
                        if seleccion == 0:
                            for respaldo in respaldos:
                                print(f"Restaurando desde {respaldo}...")
                                restore_from_backup(respaldo)
                        elif 1 <= seleccion <= len(respaldos):
                            respaldo = respaldos[seleccion-1]
                            print(f"Restaurando desde {respaldo}...")
                            restore_from_backup(respaldo)
                        else:
                            print("Selección no válida")
                    except ValueError:
                        print("Por favor ingresa un número válido")
                else:
                    print("No se encontraron archivos de respaldo.")
        
        elif opcion == "6":
            # Volver al menú principal
            break
        
        else:
            print("Opción no válida.")

def menu_principal():
    """Menú principal del programa"""
    show_header()
    
    # Crear directorios necesarios
    create_directories()
    
    while True:
        print("\n===== MENÚ PRINCIPAL =====")
        print("1. Verificar sistema")
        print("2. Configuración")
        print("3. Gestión de actores")
        print("4. Gestión de logos")
        print("5. Procesamiento de videos")
        print("6. Salir")
        
        opcion = input("\nSeleccione una opción (1-6): ")
        
        if opcion == "1":
            check_system()
        elif opcion == "2":
            menu_configuracion()
        elif opcion == "3":
            menu_actores()
        elif opcion == "4":
            menu_logos()
        elif opcion == "5":
            menu_procesamiento()
        elif opcion == "6":
            print("\nSaliendo del programa...")
            sys.exit(0)
        else:
            print("Opción no válida.")

if __name__ == "__main__":
    # Configurar logging
    setup_logging()
    
    # Procesar argumentos de línea de comandos si existen
    parser = argparse.ArgumentParser(description="VideoSort - Sistema de identificación y organización de videos")
    parser.add_argument('-c', '--check', action='store_true', help="Verificar sistema")
    parser.add_argument('-f', '--file', help="Procesar un archivo específico")
    parser.add_argument('-d', '--directory', help="Procesar un directorio")
    parser.add_argument('-r', '--recursive', action='store_true', help="Procesar directorios recursivamente")
    parser.add_argument('-b', '--batch', action='store_true', help="Procesar por lotes")
    
    args = parser.parse_args()
    
    if args.check:
        show_header()
        check_system()
        sys.exit(0)
    
    if args.file:
        show_header()
        config = load_config()
        print(f"Procesando archivo: {args.file}")
        process_single_video(args.file, config)
        sys.exit(0)
    
    if args.directory:
        show_header()
        config = load_config()
        mode = "batch" if args.batch else ("default" if args.recursive else "direct")
        print(f"Procesando directorio: {args.directory} (modo: {mode})")
        process_directory(args.directory, config, recursive=args.recursive, mode=mode)
        sys.exit(0)
    
    # Si no hay argumentos, mostrar menú interactivo
    menu_principal()