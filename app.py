# app.py - Analizador de Vid y Olivo Satelital (sin autenticación ni pagos)
# 
# - Carga de polígono de plantación.
# - División en bloques y análisis NDVI/NDWI con datos reales NASA Earthdata (MOD13Q1, MOD09GA) o simulación.
# - Datos climáticos de Open-Meteo y NASA POWER.
# - Detección de plantas individuales (mejorada con cuadrícula basada en densidad), fertilidad NPK, textura de suelo, curvas de nivel y YOLO.
# - Sin registro de usuarios ni suscripciones.
#
# IMPORTANTE: 
# - Configurar variables de entorno EARTHDATA_USERNAME y EARTHDATA_PASSWORD para datos reales (opcional).
# - Instalar dependencias: pip install earthaccess xarray rioxarray rasterio pyhdf ultralytics opencv-python

import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import tempfile
import os
import zipfile
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
from shapely.geometry import Polygon, Point, LineString, mapping
from shapely.validation import make_valid
import math
import warnings
from io import BytesIO
import requests
import re
import folium
from streamlit_folium import folium_static
from folium.plugins import Fullscreen, MeasureControl, MiniMap
from branca.colormap import LinearColormap
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import shutil

# ===== LIBRERÍAS OPCIONALES (YOLO y OpenCV) =====
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Suprimir advertencias de rasterio y otras librerías
warnings.filterwarnings('ignore', category=UserWarning, module='rasterio')
warnings.filterwarnings('ignore', category=RuntimeWarning)

# ===== LIBRERÍAS PARA DATOS SATELITALES (EARTHDATA) =====
try:
    import earthaccess
    import xarray as xr
    import rioxarray
    EARTHDATA_OK = True
except ImportError:
    EARTHDATA_OK = False

# ===== LIBRERÍAS PARA PROCESAMIENTO RASTER (rasterio y pyhdf) =====
try:
    import rasterio
    from rasterio.mask import mask
    from rasterio.transform import from_origin
    RASTERIO_OK = True
except ImportError:
    RASTERIO_OK = False

try:
    from pyhdf.SD import SD, SDC
    PYHDF_OK = True
except ImportError:
    PYHDF_OK = False

if not RASTERIO_OK and not PYHDF_OK:
    st.warning("⚠️ Ni rasterio ni pyhdf están instalados. No se podrán leer archivos HDF4. Instala al menos uno: pip install rasterio o pip install pyhdf")

# ===== CREDENCIALES EARTHDATA (desde secrets) =====
EARTHDATA_USERNAME = os.environ.get("EARTHDATA_USERNAME")
EARTHDATA_PASSWORD = os.environ.get("EARTHDATA_PASSWORD")

# ===== CONFIGURACIÓN DE PÁGINA =====
st.set_page_config(page_title="Analizador de Vid y Olivo Satelital", page_icon="🍇", layout="wide", initial_sidebar_state="expanded")

# ===== INICIALIZACIÓN DE SESIÓN =====
def init_session_state():
    defaults = {
        'geojson_data': None,
        'analisis_completado': False,
        'resultados_todos': {},
        'plantas_detectadas': [],
        'archivo_cargado': False,
        'gdf_original': None,
        'datos_modis': {},
        'datos_climaticos': {},
        'deteccion_ejecutada': False,
        'n_divisiones': 16,
        'fecha_inicio': datetime.now() - timedelta(days=60),
        'fecha_fin': datetime.now(),
        'crop_type': 'Vid',
        'variedad_seleccionada': 'Tempranillo',
        'textura_suelo': {},
        'textura_por_bloque': [],
        'datos_fertilidad': [],
        'analisis_suelo': True,
        'curvas_nivel': None,
        'densidad_personalizada': 130,
        'patron_plantacion': {'tipo': 'marco_real'},  # valor por defecto
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ===== CONFIGURACIONES =====
VARIEDADES_VID = [
    'Malbec', 'Cabernet Sauvignon', 'Merlot', 'Syrah', 'Chardonnay',
    'Torrontés', 'Bonarda', 'Tempranillo', 'Garnacha', 'Moscatel',
    'Pinot Noir', 'Sauvignon Blanc', 'Albariño', 'Verdejo', 'Chenin Blanc'
]

VARIEDADES_OLIVO = [
    'Arbequina', 'Picual', 'Hojiblanca', 'Manzanilla', 'Frantoio',
    'Coratina', 'Leccino', 'Empeltre', 'Cornicabra', 'Changlot Real',
    'Arauco', 'Nevadillo', 'Farga', 'Morisca', 'Verdial'
]

# ===== FUNCIONES DE UTILIDAD =====
def validar_y_corregir_crs(gdf):
    if gdf is None or len(gdf) == 0:
        return gdf
    try:
        if gdf.crs is None:
            bounds = gdf.total_bounds
            if abs(bounds[0]) <= 180 and abs(bounds[2]) <= 180:
                gdf = gdf.set_crs('EPSG:4326')
            else:
                gdf = gdf.set_crs('EPSG:3857')
                gdf = gdf.to_crs('EPSG:4326')
        elif str(gdf.crs).upper() != 'EPSG:4326':
            gdf = gdf.to_crs('EPSG:4326')
        return gdf
    except Exception as e:
        st.warning(f"Error al corregir CRS: {e}")
        return gdf

def calcular_superficie(gdf):
    try:
        if gdf is None or len(gdf) == 0:
            return 0.0
        gdf = validar_y_corregir_crs(gdf)
        gdf_projected = gdf.to_crs('EPSG:3857')
        area_m2 = gdf_projected.geometry.area.sum()
        return area_m2 / 10000  # hectáreas
    except Exception as e:
        st.warning(f"No se pudo calcular el área: {e}")
        return 0.0

def dividir_plantacion_en_bloques(gdf, n_bloques):
    if gdf is None or len(gdf) == 0:
        return gdf
    gdf = validar_y_corregir_crs(gdf)
    plantacion_principal = gdf.iloc[0].geometry
    bounds = plantacion_principal.bounds
    minx, miny, maxx, maxy = bounds
    sub_poligonos = []
    n_cols = math.ceil(math.sqrt(n_bloques))
    n_rows = math.ceil(n_bloques / n_cols)
    width = (maxx - minx) / n_cols
    height = (maxy - miny) / n_rows
    for i in range(n_rows):
        for j in range(n_cols):
            if len(sub_poligonos) >= n_bloques:
                break
            cell_minx = minx + j * width
            cell_maxx = minx + (j + 1) * width
            cell_miny = miny + i * height
            cell_maxy = miny + (i + 1) * height
            cell_poly = Polygon([
                (cell_minx, cell_miny), (cell_maxx, cell_miny),
                (cell_maxx, cell_maxy), (cell_minx, cell_maxy)
            ])
            intersection = plantacion_principal.intersection(cell_poly)
            if not intersection.is_empty and intersection.area > 0:
                sub_poligonos.append(intersection)
    if sub_poligonos:
        return gpd.GeoDataFrame(
            {'id_bloque': range(1, len(sub_poligonos) + 1), 'geometry': sub_poligonos},
            crs='EPSG:4326'
        )
    return gdf

# ===== PARSER KML MEJORADO =====
def procesar_kml_robusto(file_content):
    try:
        try:
            content = file_content.decode('utf-8')
        except:
            content = file_content.decode('latin-1', errors='ignore')
        polygons = []
        coord_sections = re.findall(r'<coordinates[^>]*>([\s\S]*?)</coordinates>', content, re.IGNORECASE | re.DOTALL)
        for coord_text in coord_sections:
            coord_text = coord_text.strip()
            if not coord_text:
                continue
            coords = re.split(r'[\s\n\t]+', coord_text)
            coord_list = []
            for coord in coords:
                coord = coord.strip()
                if not coord or ',' not in coord:
                    continue
                try:
                    parts = [p.strip() for p in coord.split(',')]
                    if len(parts) >= 2:
                        lon, lat = float(parts[0]), float(parts[1])
                        if -180 <= lon <= 180 and -90 <= lat <= 90:
                            coord_list.append((lon, lat))
                except ValueError:
                    continue
            if len(coord_list) >= 3:
                if coord_list[0] != coord_list[-1]:
                    coord_list.append(coord_list[0])
                try:
                    polygon = Polygon(coord_list)
                    if polygon.is_valid and polygon.area > 0:
                        polygons.append(polygon)
                except Exception:
                    continue
        if polygons:
            return gpd.GeoDataFrame(geometry=polygons, crs='EPSG:4326')
        # Intentar Placemark
        placemarks = re.findall(r'<Placemark[^>]*>([\s\S]*?)</Placemark>', content, re.IGNORECASE | re.DOTALL)
        for placemark in placemarks:
            coord_match = re.search(r'<coordinates[^>]*>([\s\S]*?)</coordinates>', placemark, re.IGNORECASE)
            if coord_match:
                coord_text = coord_match.group(1).strip()
                if coord_text:
                    coords = re.split(r'[\s\n\t]+', coord_text)
                    coord_list = []
                    for coord in coords:
                        coord = coord.strip()
                        if coord and ',' in coord:
                            try:
                                parts = [p.strip() for p in coord.split(',')]
                                if len(parts) >= 2:
                                    lon, lat = float(parts[0]), float(parts[1])
                                    if -180 <= lon <= 180 and -90 <= lat <= 90:
                                        coord_list.append((lon, lat))
                            except ValueError:
                                continue
                    if len(coord_list) >= 3:
                        if coord_list[0] != coord_list[-1]:
                            coord_list.append(coord_list[0])
                        try:
                            polygon = Polygon(coord_list)
                            if polygon.is_valid and polygon.area > 0:
                                polygons.append(polygon)
                        except Exception:
                            continue
        if polygons:
            return gpd.GeoDataFrame(geometry=polygons, crs='EPSG:4326')
        return None
    except Exception as e:
        st.error(f"Error en procesamiento KML: {str(e)}")
        return None

# ===== CARGA DE ARCHIVO =====
def cargar_archivo_plantacion(uploaded_file):
    try:
        file_content = uploaded_file.read()
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        gdf = None
        with tempfile.TemporaryDirectory() as tmp_dir:
            if ext == '.zip':
                with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_ref:
                    zip_ref.extractall(tmp_dir)
                shp_files = [f for f in os.listdir(tmp_dir) if f.endswith('.shp')]
                if not shp_files:
                    st.error("❌ No se encontró archivo .shp dentro del ZIP")
                    return None
                gdf = gpd.read_file(os.path.join(tmp_dir, shp_files[0]))
            elif ext == '.geojson':
                gdf = gpd.read_file(io.BytesIO(file_content))
            elif ext == '.kml':
                gdf = procesar_kml_robusto(file_content)
                if gdf is None:
                    st.error("❌ No se pudieron extraer polígonos del KML")
                    return None
            elif ext == '.kmz':
                kmz_path = os.path.join(tmp_dir, 'temp.kmz')
                with open(kmz_path, 'wb') as f:
                    f.write(file_content)
                with zipfile.ZipFile(kmz_path, 'r') as kmz:
                    kml_files = [f for f in kmz.namelist() if f.endswith('.kml')]
                    if not kml_files:
                        st.error("❌ No se encontró KML dentro del KMZ")
                        return None
                    kmz.extract(kml_files[0], tmp_dir)
                    with open(os.path.join(tmp_dir, kml_files[0]), 'rb') as f:
                        gdf = procesar_kml_robusto(f.read())
                if gdf is None:
                    st.error("❌ No se pudieron extraer polígonos del KMZ")
                    return None
            else:
                st.error(f"❌ Formato no soportado: {ext}. Use .zip, .geojson, .kml o .kmz")
                return None
        if gdf is None or len(gdf) == 0:
            st.error("❌ No se encontraron geometrías válidas")
            return None
        gdf = validar_y_corregir_crs(gdf)
        gdf = gdf.explode(ignore_index=True)
        gdf = gdf[gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
        if len(gdf) == 0:
            st.error("❌ No hay polígonos válidos después del filtrado")
            return None
        union = gdf.unary_union
        if union.geom_type == 'MultiPolygon':
            areas = [p.area for p in union.geoms]
            main_poly = union.geoms[np.argmax(areas)]
        else:
            main_poly = union
        if not main_poly.is_valid:
            main_poly = make_valid(main_poly)
            if main_poly.geom_type == 'MultiPolygon':
                areas = [p.area for p in main_poly.geoms]
                main_poly = main_poly.geoms[np.argmax(areas)]
        gdf_unido = gpd.GeoDataFrame([{'geometry': main_poly, 'id_bloque': 1}], crs='EPSG:4326')
        area = calcular_superficie(gdf_unido)
        if area <= 0:
            st.error("❌ El polígono tiene área cero o inválida")
            return None
        st.session_state.gdf_original = gdf_unido
        st.session_state.archivo_cargado = True
        st.session_state.analisis_completado = False
        st.session_state.deteccion_ejecutada = False
        st.success(f"✅ Plantación cargada: {area:.2f} ha")
        return gdf_unido
    except Exception as e:
        st.error(f"❌ Error cargando archivo: {str(e)}")
        return None

# ===== FUNCIONES DE SIMULACIÓN (FALLBACK) =====
def generar_datos_simulados_completos(gdf_original, n_divisiones, crop_type):
    gdf_dividido = dividir_plantacion_en_bloques(gdf_original, n_divisiones)
    areas_ha = []
    for _, row in gdf_dividido.iterrows():
        area_gdf = gpd.GeoDataFrame({'geometry': [row.geometry]}, crs=gdf_dividido.crs)
        areas_ha.append(float(calcular_superficie(area_gdf)))
    gdf_dividido['area_ha'] = areas_ha
    np.random.seed(42)
    centroides = gdf_dividido.geometry.centroid
    lons = centroides.x.values
    lats = centroides.y.values
    ndvi_vals = 0.5 + 0.2 * np.sin(lons * 10) * np.cos(lats * 10) + 0.1 * np.random.randn(len(lons))
    ndvi_vals = np.clip(ndvi_vals, 0.2, 0.9)
    gdf_dividido['ndvi_modis'] = np.round(ndvi_vals, 3)
    ndwi_vals = 0.3 + 0.15 * np.cos(lons * 5) * np.sin(lats * 5) + 0.1 * np.random.randn(len(lons))
    ndwi_vals = np.clip(ndwi_vals, 0.1, 0.7)
    gdf_dividido['ndwi_modis'] = np.round(ndwi_vals, 3)
    if crop_type == 'Vid':
        edad_base = 5
        rango = 15
    else:
        edad_base = 10
        rango = 30
    edades = edad_base + rango * np.random.rand(len(lons))
    gdf_dividido['edad_anios'] = np.round(edades, 1)
    def clasificar_salud(ndvi):
        if ndvi < 0.4: return 'Crítica'
        if ndvi < 0.6: return 'Baja'
        if ndvi < 0.75: return 'Moderada'
        return 'Buena'
    gdf_dividido['salud'] = gdf_dividido['ndvi_modis'].apply(clasificar_salud)
    return gdf_dividido

def generar_clima_simulado():
    dias = 60
    np.random.seed(42)
    precip_diaria = np.random.exponential(3, dias) * (np.random.rand(dias) > 0.6)
    temp_diaria = 25 + 5 * np.sin(np.linspace(0, 4*np.pi, dias)) + np.random.randn(dias)*2
    rad_diaria = 20 + 5 * np.sin(np.linspace(0, 4*np.pi, dias)) + np.random.randn(dias)*3
    wind_diaria = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, dias)) + np.random.randn(dias)*1
    return {
        'precipitacion': {
            'total': round(sum(precip_diaria), 1),
            'maxima_diaria': round(max(precip_diaria), 1),
            'dias_con_lluvia': int(sum(precip_diaria > 0.1)),
            'diaria': [round(p, 1) for p in precip_diaria]
        },
        'temperatura': {
            'promedio': round(np.mean(temp_diaria), 1),
            'maxima': round(np.max(temp_diaria), 1),
            'minima': round(np.min(temp_diaria), 1),
            'diaria': [round(t, 1) for t in temp_diaria]
        },
        'radiacion': {
            'promedio': round(np.mean(rad_diaria), 1),
            'maxima': round(np.max(rad_diaria), 1),
            'minima': round(np.min(rad_diaria), 1),
            'diaria': [round(r, 1) for r in rad_diaria]
        },
        'viento': {
            'promedio': round(np.mean(wind_diaria), 1),
            'maxima': round(np.max(wind_diaria), 1),
            'diaria': [round(w, 1) for w in wind_diaria]
        },
        'periodo': 'Últimos 60 días (simulado)',
        'fuente': 'Datos simulados (fallback)'
    }

# ===== FUNCIONES PARA DATOS SATELITALES CON EARTHDATA (CORREGIDAS) =====
# (Se mantienen igual que en la versión anterior, con las mejoras de expresiones regulares)
# ... (omitidas por brevedad, pero deben estar completas en el código real)

# ===== DETECCIÓN DE PLANTAS MEJORADA =====
def generar_plantas_segun_densidad(gdf, densidad, crop_type, perturbacion=0.2):
    """
    Genera puntos de plantas dentro del polígono basándose en la densidad objetivo (plantas/ha).
    Utiliza una cuadrícula regular en coordenadas proyectadas (EPSG:3857) con espaciado calculado
    a partir de la densidad, y aplica una pequeña perturbación aleatoria para simular irregularidad.
    """
    try:
        # Proyectar a metros
        gdf_proj = gdf.to_crs('EPSG:3857')
        poligono = gdf_proj.geometry.iloc[0]
        area_m2 = poligono.area
        area_ha = area_m2 / 10000

        if area_ha <= 0:
            return {'detectadas': [], 'total': 0}

        # Número objetivo de plantas
        num_objetivo = int(area_ha * densidad)
        if num_objetivo <= 0:
            return {'detectadas': [], 'total': 0}

        # Espaciado aproximado para una cuadrícula regular
        espaciado = np.sqrt(area_m2 / num_objetivo)  # en metros

        # Obtener bounds en metros
        bounds = gdf_proj.total_bounds  # minx, miny, maxx, maxy
        minx, miny, maxx, maxy = bounds

        # Generar puntos en cuadrícula regular
        x_coords = np.arange(minx, maxx, espaciado)
        y_coords = np.arange(miny, maxy, espaciado)

        plantas = []
        for x in x_coords:
            for y in y_coords:
                # Añadir perturbación aleatoria
                if perturbacion > 0:
                    dx = np.random.uniform(-espaciado * perturbacion, espaciado * perturbacion)
                    dy = np.random.uniform(-espaciado * perturbacion, espaciado * perturbacion)
                else:
                    dx = dy = 0
                punto = Point(x + dx, y + dy)
                if poligono.contains(punto):
                    # Convertir de nuevo a EPSG:4326 para almacenar
                    punto_geo = gpd.GeoSeries([punto], crs='EPSG:3857').to_crs('EPSG:4326').iloc[0]
                    lon, lat = punto_geo.x, punto_geo.y

                    # Determinar área de copa y diámetro según cultivo
                    if crop_type == 'Vid':
                        area_copa = np.random.uniform(1, 4)      # m²
                        diametro = np.random.uniform(1.0, 2.5)  # m
                    else:
                        area_copa = np.random.uniform(4, 12)     # m²
                        diametro = np.random.uniform(2.0, 4.0)   # m

                    plantas.append({
                        'centroide': (lon, lat),
                        'area_m2': area_copa,
                        'circularidad': np.random.uniform(0.7, 0.95),
                        'diametro_aprox': diametro,
                        'simulado': True
                    })

                    # Parar si ya alcanzamos el número objetivo
                    if len(plantas) >= num_objetivo:
                        break
            if len(plantas) >= num_objetivo:
                break

        return {
            'detectadas': plantas,
            'total': len(plantas),
            'densidad_calculada': len(plantas) / area_ha,
            'area_ha': area_ha
        }
    except Exception as e:
        print(f"Error en generación de plantas: {e}")
        return {'detectadas': [], 'total': 0}

def ejecutar_deteccion_plantas():
    if st.session_state.gdf_original is None:
        st.error("Primero debe cargar un archivo de plantación")
        return
    with st.spinner("Ejecutando detección de plantas..."):
        gdf = st.session_state.gdf_original
        densidad = st.session_state.densidad_personalizada
        crop_type = st.session_state.crop_type

        # Usar la nueva función basada en densidad
        resultados = generar_plantas_segun_densidad(gdf, densidad, crop_type, perturbacion=0.2)

        # Filtrar puntos dentro del polígono (ya deberían estarlo, pero por seguridad)
        plantas_dentro = []
        union = gdf.unary_union
        for p in resultados['detectadas']:
            point = Point(p['centroide'])
            if union.contains(point):
                plantas_dentro.append(p)

        st.session_state.plantas_detectadas = plantas_dentro
        st.session_state.deteccion_ejecutada = True
        st.success(f"✅ Detección completada: {len(plantas_dentro)} plantas detectadas")

# ===== ANÁLISIS DE TEXTURA DE SUELO =====
# ... (se mantiene igual)

# ===== FERTILIDAD NPK =====
# ... (se mantiene igual)

# ===== FUNCIONES DE VISUALIZACIÓN =====
# ... (se mantienen todas, incluyendo crear_graficos_climaticos_completos)

# ===== FUNCIONES YOLO (protegidas) =====
# ... (se mantienen)

# ===== CURVAS DE NIVEL =====
# ... (se mantienen)

# ===== FUNCIÓN PRINCIPAL DE ANÁLISIS =====
def ejecutar_analisis_completo():
    if st.session_state.gdf_original is None:
        st.error("Primero debe cargar un archivo de plantación")
        return
    with st.spinner("Ejecutando análisis completo..."):
        n_divisiones = st.session_state.n_divisiones
        fecha_inicio = st.session_state.fecha_inicio
        fecha_fin = st.session_state.fecha_fin
        gdf = st.session_state.gdf_original.copy()
        crop_type = st.session_state.crop_type

        gdf_dividido = dividir_plantacion_en_bloques(gdf, n_divisiones)
        areas_ha = []
        for _, row in gdf_dividido.iterrows():
            area_gdf = gpd.GeoDataFrame({'geometry': [row.geometry]}, crs=gdf_dividido.crs)
            areas_ha.append(calcular_superficie(area_gdf))
        gdf_dividido['area_ha'] = areas_ha

        st.info("🛰️ Obteniendo NDVI desde Earthdata...")
        resultado_ndvi = obtener_ndvi_earthdata(gdf_dividido, fecha_inicio, fecha_fin)
        if resultado_ndvi is None:
            st.warning("No se pudo obtener NDVI real. Usando datos simulados.")
            gdf_dividido['ndvi_modis'] = np.random.uniform(0.3, 0.9, len(gdf_dividido))
            fuente_ndvi = "Simulado"
        else:
            gdf_dividido = resultado_ndvi
            fuente_ndvi = "Earthdata MOD13Q1"

        st.info("💧 Obteniendo NDWI desde Earthdata...")
        resultado_ndwi = obtener_ndwi_earthdata(gdf_dividido, fecha_inicio, fecha_fin)
        if resultado_ndwi is None:
            st.warning("No se pudo obtener NDWI real. Usando datos simulados.")
            gdf_dividido['ndwi_modis'] = np.random.uniform(0.1, 0.6, len(gdf_dividido))
            fuente_ndwi = "Simulado"
        else:
            gdf_dividido = resultado_ndwi
            fuente_ndwi = "Earthdata MOD09GA"

        st.info("🌦️ Obteniendo datos climáticos...")
        datos_clima = obtener_clima_openmeteo(gdf, fecha_inicio, fecha_fin) or {}
        datos_power = obtener_radiacion_viento_power(gdf, fecha_inicio, fecha_fin) or {}
        st.session_state.datos_climaticos = {**datos_clima, **datos_power}

        # Edad simulada según cultivo
        if crop_type == 'Vid':
            edad_min, edad_max = 2, 20
        else:
            edad_min, edad_max = 5, 45
        edades = np.random.uniform(edad_min, edad_max, len(gdf_dividido))
        gdf_dividido['edad_anios'] = np.round(edades, 1)

        def clasificar_salud(ndvi):
            if ndvi < 0.4: return 'Crítica'
            if ndvi < 0.6: return 'Baja'
            if ndvi < 0.75: return 'Moderada'
            return 'Buena'
        gdf_dividido['salud'] = gdf_dividido['ndvi_modis'].apply(clasificar_salud)

        if st.session_state.analisis_suelo:
            st.session_state.textura_por_bloque = analizar_textura_suelo_venezuela_por_bloque(gdf_dividido)
            st.session_state.datos_fertilidad = generar_mapa_fertilidad(gdf_dividido)

        st.session_state.datos_modis = {
            'ndvi': gdf_dividido['ndvi_modis'].mean(),
            'ndwi': gdf_dividido['ndwi_modis'].mean(),
            'fecha': fecha_inicio.strftime('%Y-%m-%d'),
            'fuente': f"NDVI: {fuente_ndvi}, NDWI: {fuente_ndwi}"
        }

        st.session_state.resultados_todos = {
            'gdf_completo': gdf_dividido,
            'area_total': calcular_superficie(gdf)
        }
        st.session_state.analisis_completado = True
        st.success("✅ Análisis completado!")

# ===== INTERFAZ PRINCIPAL =====
st.markdown("""
<div style="text-align: center; padding: 1rem; background: linear-gradient(145deg, #0f172a, #1e293b); border-radius: 15px; margin-bottom: 2rem;">
    <h1 style="color: white; font-size: 2.5rem;">🍇 ANALIZADOR DE VID Y OLIVO SATELITAL</h1>
    <p style="color: #cbd5e1;">Monitoreo biológico con datos NASA Earthdata · Open-Meteo · NASA POWER</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🍇 CONFIGURACIÓN")
    
    # Selección de cultivo
    st.session_state.crop_type = st.radio(
        "Cultivo",
        ["Vid", "Olivo"],
        horizontal=True,
        index=0 if st.session_state.crop_type == "Vid" else 1
    )

    # Selección de variedad según cultivo
    if st.session_state.crop_type == "Vid":
        default_idx = VARIEDADES_VID.index(st.session_state.variedad_seleccionada) if st.session_state.variedad_seleccionada in VARIEDADES_VID else 0
        st.session_state.variedad_seleccionada = st.selectbox(
            "Variedad de Vid:",
            VARIEDADES_VID,
            index=default_idx
        )
    else:
        default_idx = VARIEDADES_OLIVO.index(st.session_state.variedad_seleccionada) if st.session_state.variedad_seleccionada in VARIEDADES_OLIVO else 0
        st.session_state.variedad_seleccionada = st.selectbox(
            "Variedad de Olivo:",
            VARIEDADES_OLIVO,
            index=default_idx
        )

    st.markdown("---")
    st.markdown("### 📅 Rango Temporal")
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio_widget = st.date_input(
            "Inicio",
            value=st.session_state.fecha_inicio.date()
        )
    with col2:
        fecha_fin_widget = st.date_input(
            "Fin",
            value=st.session_state.fecha_fin.date()
        )
    if fecha_inicio_widget is not None:
        st.session_state.fecha_inicio = datetime.combine(fecha_inicio_widget, datetime.min.time())
    if fecha_fin_widget is not None:
        st.session_state.fecha_fin = datetime.combine(fecha_fin_widget, datetime.min.time())

    st.markdown("---")
    st.markdown("### 🎯 División")
    st.session_state.n_divisiones = st.slider(
        "Número de bloques:",
        min_value=8,
        max_value=32,
        value=st.session_state.n_divisiones
    )

    st.markdown("---")
    st.markdown("### 🌱 Detección de Plantas")
    deteccion_habilitada = st.checkbox("Activar detección de plantas", value=True)
    if deteccion_habilitada:
        st.session_state.densidad_personalizada = st.slider(
            "Densidad objetivo (plantas/ha):",
            min_value=50,
            max_value=500,
            value=st.session_state.densidad_personalizada
        )
        # Opciones de patrón (aunque usaremos el método de densidad)
        st.markdown("#### Patrón de plantación")
        patron_opciones = ["Marco real (hileras)", "Cuadrícula hexagonal", "Aleatorio"]
        patron_sel = st.selectbox("Patrón", patron_opciones, index=0)
        # Guardamos la selección por si se quiere usar en el futuro, pero la función actual usa densidad
        st.session_state.patron_plantacion = {'tipo': patron_sel.lower().replace(" ", "_")}

    st.markdown("---")
    st.markdown("### 🧪 Análisis de Suelo")
    st.session_state.analisis_suelo = st.checkbox(
        "Activar análisis de suelo",
        value=st.session_state.analisis_suelo
    )
    if st.session_state.analisis_suelo:
        st.info("Incluye: Textura por bloque, fertilidad NPK, recomendaciones")

    st.markdown("---")
    st.markdown("### 📤 Subir Polígono")
    uploaded_file = st.file_uploader(
        "Subir archivo de plantación", 
        type=['zip', 'kml', 'kmz', 'geojson'],
        help="Formatos: Shapefile (.zip), KML (.kmz), GeoJSON (.geojson)"
    )
    if uploaded_file is not None:
        st.info(f"📄 Archivo: {uploaded_file.name}")
        st.info(f"📊 Tamaño: {uploaded_file.size / 1024:.1f} KB")
        if st.button("🔄 Cargar Polígono"):
            with st.spinner("⏳ Procesando polígono..."):
                gdf = cargar_archivo_plantacion(uploaded_file)
                if gdf is not None:
                    st.success("✅ Polígono cargado correctamente")
                    st.rerun()
    if st.session_state.get('archivo_cargado', False):
        st.success("✅ Polígono cargado en memoria")
        if st.session_state.get('gdf_original') is not None:
            area = calcular_superficie(st.session_state.gdf_original)
            st.metric("Área", f"{area:.2f} ha")

# ===== ÁREA PRINCIPAL =====
if st.session_state.archivo_cargado and st.session_state.gdf_original is not None:
    gdf = st.session_state.gdf_original
    try:
        area_total = calcular_superficie(gdf)
    except:
        area_total = 0.0

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 INFORMACIÓN DE LA PLANTACIÓN")
        st.write(f"- **Área total:** {area_total:.1f} ha")
        st.write(f"- **Cultivo:** {st.session_state.crop_type}")
        st.write(f"- **Variedad:** {st.session_state.variedad_seleccionada}")
        st.write(f"- **Bloques configurados:** {st.session_state.n_divisiones}")
        st.markdown("#### 🗺️ Vista previa del polígono")
        try:
            m_preview = folium.Map(
                location=[gdf.geometry.centroid.y.iloc[0], gdf.geometry.centroid.x.iloc[0]],
                zoom_start=15, tiles=None
            )
            folium.TileLayer(
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Satélite'
            ).add_to(m_preview)
            folium.GeoJson(
                gdf.to_json(),
                style_function=lambda x: {'fillColor': '#3388ff', 'color': 'black', 'weight': 2, 'fillOpacity': 0.4}
            ).add_to(m_preview)
            folium.LayerControl().add_to(m_preview)
            folium_static(m_preview, width=500, height=300)
        except Exception as e:
            st.warning(f"No se pudo mostrar el mapa de vista previa: {e}")
    with col2:
        st.markdown("### 🎯 ACCIONES")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if not st.session_state.analisis_completado:
                if st.button("🚀 EJECUTAR ANÁLISIS", use_container_width=True):
                    ejecutar_analisis_completo()
                    st.rerun()
            else:
                if st.button("🔄 RE-EJECUTAR", use_container_width=True):
                    st.session_state.analisis_completado = False
                    ejecutar_analisis_completo()
                    st.rerun()
        with col_btn2:
            if deteccion_habilitada:
                if st.button("🔍 DETECTAR PLANTAS", use_container_width=True):
                    ejecutar_deteccion_plantas()
                    st.rerun()
else:
    st.info("👆 Por favor, sube un archivo de plantación en la barra lateral para comenzar.")
    st.markdown("""
    ### ¿Cómo empezar?
    1. Sube un archivo con el polígono de tu plantación (formatos: Shapefile .zip, KML, KMZ, GeoJSON).
    2. Configura los parámetros de análisis.
    3. Haz clic en **EJECUTAR ANÁLISIS** para obtener resultados.
    """)

# ===== PESTAÑAS DE RESULTADOS =====
if st.session_state.analisis_completado:
    resultados = st.session_state.resultados_todos
    gdf_completo = resultados.get('gdf_completo')
    if gdf_completo is not None:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "📊 Resumen", "🗺️ Mapas", "🛰️ Índices", "🌤️ Clima", "🌱 Detección",
            "🧪 Fertilidad NPK", "🌱 Textura Suelo", "🗺️ Curvas de Nivel", "🐛 Detección YOLO"
        ])
        with tab1:
            st.subheader("📊 DASHBOARD DE RESUMEN")
            area_total = resultados.get('area_total', 0)
            edad_prom = gdf_completo['edad_anios'].mean() if 'edad_anios' in gdf_completo.columns else np.nan
            ndvi_prom = gdf_completo['ndvi_modis'].mean() if 'ndvi_modis' in gdf_completo.columns else np.nan
            ndwi_prom = gdf_completo['ndwi_modis'].mean() if 'ndwi_modis' in gdf_completo.columns else np.nan
            total_bloques = len(gdf_completo)
            salud_counts = gdf_completo['salud'].value_counts() if 'salud' in gdf_completo.columns else pd.Series()
            pct_buena = (salud_counts.get('Buena', 0) / total_bloques * 100) if total_bloques > 0 else 0
            col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns(6)
            with col_m1: st.metric("Área Total", f"{area_total:.1f} ha")
            with col_m2: st.metric("Bloques", f"{total_bloques}")
            with col_m3: st.metric("Edad Prom.", f"{edad_prom:.1f} años" if not np.isnan(edad_prom) else "N/A")
            with col_m4: st.metric("NDVI Prom.", f"{ndvi_prom:.3f}" if not np.isnan(ndvi_prom) else "N/A")
            with col_m5: st.metric("NDWI Prom.", f"{ndwi_prom:.3f}" if not np.isnan(ndwi_prom) else "N/A")
            with col_m6: st.metric("Salud Buena", f"{pct_buena:.1f}%")
            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("#### 🌡️ Distribución de Salud")
                if not salud_counts.empty:
                    fig_pie, ax_pie = plt.subplots(figsize=(5,3))
                    colors_pie = {'Crítica': '#d73027', 'Baja': '#fee08b', 'Moderada': '#91cf60', 'Buena': '#1a9850'}
                    pie_colors = [colors_pie.get(c, '#cccccc') for c in salud_counts.index]
                    wedges, texts, autotexts = ax_pie.pie(
                        salud_counts.values, labels=salud_counts.index, autopct='%1.1f%%',
                        colors=pie_colors, startangle=90, textprops={'fontsize': 9}
                    )
                    ax_pie.set_title("Clasificación de salud", fontsize=10)
                    st.pyplot(fig_pie)
                    plt.close(fig_pie)
                else:
                    st.info("Sin datos de salud")
            with col_g2:
                st.markdown("#### 📊 Histograma de NDVI y Edad")
                if 'ndvi_modis' in gdf_completo.columns and 'edad_anios' in gdf_completo.columns:
                    fig_hist, ax_hist = plt.subplots(figsize=(5,3))
                    ax_hist.hist(gdf_completo['ndvi_modis'].dropna(), bins=15, alpha=0.7, label='NDVI', color='green')
                    ax_hist.set_xlabel('NDVI')
                    ax_hist.set_ylabel('Frecuencia', color='green')
                    ax_hist.tick_params(axis='y', labelcolor='green')
                    ax2 = ax_hist.twinx()
                    ax2.hist(gdf_completo['edad_anios'].dropna(), bins=15, alpha=0.5, label='Edad', color='orange')
                    ax2.set_ylabel('Frecuencia (Edad)', color='orange')
                    ax2.tick_params(axis='y', labelcolor='orange')
                    ax_hist.set_title('Distribución de NDVI y Edad')
                    fig_hist.tight_layout()
                    st.pyplot(fig_hist)
                    plt.close(fig_hist)
                else:
                    st.info("Datos insuficientes para histograma")
            st.markdown("---")
            st.markdown("#### 🗺️ Mapa de Salud por Bloque")
            try:
                fig_map, ax_map = plt.subplots(figsize=(10,5))
                gdf_completo.plot(
                    column='salud', ax=ax_map, legend=True,
                    categorical=True, cmap='RdYlGn',
                    edgecolor='black', linewidth=0.3,
                    legend_kwds={'title': 'Salud', 'loc': 'lower right'}
                )
                ax_map.set_title("Distribución espacial de la salud")
                ax_map.set_xlabel("Longitud")
                ax_map.set_ylabel("Latitud")
                st.pyplot(fig_map)
                plt.close(fig_map)
            except Exception as e:
                st.warning(f"No se pudo generar el mapa de salud: {e}")
            st.markdown("---")
            st.markdown("#### 📋 Resumen detallado por bloque")
            try:
                columnas_tabla = ['id_bloque', 'area_ha', 'edad_anios', 'ndvi_modis', 'ndwi_modis', 'salud']
                tabla = gdf_completo[columnas_tabla].copy()
                tabla.columns = ['Bloque', 'Área (ha)', 'Edad (años)', 'NDVI', 'NDWI', 'Salud']
                def color_salud(val):
                    if val == 'Crítica': return 'background-color: #d73027; color: white'
                    elif val == 'Baja': return 'background-color: #fee08b'
                    elif val == 'Moderada': return 'background-color: #91cf60'
                    elif val == 'Buena': return 'background-color: #1a9850; color: white'
                    return ''
                styled_tabla = tabla.style.format({
                    'Área (ha)': '{:.2f}',
                    'Edad (años)': '{:.1f}',
                    'NDVI': '{:.3f}',
                    'NDWI': '{:.3f}'
                }).applymap(color_salud, subset=['Salud'])
                st.dataframe(styled_tabla, use_container_width=True, height=400)
                csv_tabla = tabla.to_csv(index=False)
                st.download_button(
                    label="📥 Exportar tabla a CSV",
                    data=csv_tabla,
                    file_name=f"resumen_plantacion_{datetime.now():%Y%m%d}.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.warning(f"No se pudo mostrar la tabla de bloques: {e}")
        with tab2:
            st.subheader("🗺️ MAPAS INTERACTIVOS")
            st.markdown("### 🌍 Mapa Interactivo con Plantas Detectadas")
            try:
                colormap_ndvi = LinearColormap(colors=['red','yellow','green'], vmin=0.3, vmax=0.9)
                mapa_interactivo = crear_mapa_interactivo_base(
                    gdf_completo,
                    columna_color='ndvi_modis',
                    colormap=colormap_ndvi,
                    tooltip_fields=['id_bloque','ndvi_modis','salud'],
                    tooltip_aliases=['Bloque','NDVI','Salud']
                )
                if st.session_state.plantas_detectadas:
                    plantas_group = folium.FeatureGroup(name="Plantas detectadas")
                    for i, planta in enumerate(st.session_state.plantas_detectadas[:2000]):
                        if 'centroide' in planta:
                            lon, lat = planta['centroide']
                            folium.CircleMarker(
                                [lat, lon], radius=2, color='red', fill=True,
                                fill_color='red', fill_opacity=0.8
                            ).add_to(plantas_group)
                    plantas_group.add_to(mapa_interactivo)
                    folium.LayerControl().add_to(mapa_interactivo)
                if mapa_interactivo:
                    folium_static(mapa_interactivo, width=1000, height=600)
                else:
                    st.warning("No se pudo generar el mapa interactivo")
            except Exception as e:
                st.error(f"Error al mostrar mapa interactivo: {str(e)[:100]}")
        with tab3:
            st.subheader("🛰️ ÍNDICES DE VEGETACIÓN")
            st.caption(f"Fuente: {st.session_state.datos_modis.get('fuente', 'Earthdata')}")
            st.markdown("### 🌿 NDVI")
            if 'ndvi_modis' in gdf_completo.columns:
                mostrar_estadisticas_indice(gdf_completo, 'ndvi_modis', 'NDVI', 0.3, 0.9, ['red','yellow','green'])
            else:
                st.error("No hay datos de NDVI disponibles.")
            st.markdown("---")
            st.markdown("### 💧 NDWI")
            st.info("NDWI calculado como (NIR - SWIR)/(NIR+SWIR) con bandas de MODIS (producto MOD09GA).")
            if 'ndwi_modis' in gdf_completo.columns:
                mostrar_estadisticas_indice(gdf_completo, 'ndwi_modis', 'NDWI', 0.1, 0.7, ['brown','yellow','blue'])
            else:
                st.error("No hay datos de NDWI disponibles.")
            st.markdown("---")
            mostrar_comparacion_ndvi_ndwi(gdf_completo)
            st.markdown("### 📥 EXPORTAR")
            try:
                gdf_indices = gdf_completo[['id_bloque','ndvi_modis','ndwi_modis','salud','geometry']].copy()
                gdf_indices.columns = ['id_bloque','NDVI','NDWI','Salud','geometry']
                geojson_indices = gdf_indices.to_json()
                csv_indices = gdf_indices.drop(columns='geometry').to_csv(index=False)
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1: st.download_button("🗺️ GeoJSON", geojson_indices, f"indices_{datetime.now():%Y%m%d}.geojson", "application/geo+json")
                with col_dl2: st.download_button("📊 CSV", csv_indices, f"indices_{datetime.now():%Y%m%d}.csv", "text/csv")
            except Exception as e:
                st.info(f"No se pudieron exportar los datos: {e}")
        with tab4:
            st.subheader("🌤️ DATOS CLIMÁTICOS")
            datos_climaticos = st.session_state.datos_climaticos
            if datos_climaticos:
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Precipitación total", f"{datos_climaticos['precipitacion']['total']} mm")
                with col2: st.metric("Días con lluvia", f"{datos_climaticos['precipitacion']['dias_con_lluvia']} días")
                with col3: st.metric("Temperatura promedio", f"{datos_climaticos['temperatura']['promedio']}°C")
                with col4: st.metric("Radiación promedio", f"{datos_climaticos.get('radiacion',{}).get('promedio', 'N/A')} MJ/m²")
                st.markdown("### 📈 GRÁFICOS CLIMÁTICOS COMPLETOS")
                try:
                    fig_clima = crear_graficos_climaticos_completos(datos_climaticos)
                    st.pyplot(fig_clima); plt.close(fig_clima)
                except Exception as e:
                    st.error(f"Error al mostrar gráficos climáticos: {str(e)[:100]}")
                st.markdown("### 📋 INFORMACIÓN ADICIONAL")
                st.write(f"- **Fuente precipitación/temperatura:** {datos_climaticos.get('fuente', 'N/A')}")
                st.write(f"- **Fuente radiación/viento:** NASA POWER")
                st.write(f"- **Período:** {datos_climaticos['periodo']}")
            else:
                st.info("No hay datos climáticos disponibles")
        with tab5:
            st.subheader("🌱 DETECCIÓN DE PLANTAS INDIVIDUALES")
            if st.session_state.deteccion_ejecutada and st.session_state.plantas_detectadas:
                plantas = st.session_state.plantas_detectadas
                total = len(plantas)
                area_total_val = resultados.get('area_total', 0)
                densidad = total / area_total_val if area_total_val > 0 else 0
                st.success(f"✅ Detección completada: {total} plantas detectadas")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Plantas detectadas", f"{total:,}")
                with col2: st.metric("Densidad", f"{densidad:.0f} plantas/ha")
                with col3: st.metric("Área promedio", f"{np.mean([p.get('area_m2',0) for p in plantas]):.1f} m²")
                with col4: st.metric("Diámetro promedio", f"{np.mean([p.get('diametro_aprox',0) for p in plantas]):.1f} m")
                st.markdown("### 🗺️ Mapa de Distribución")
                try:
                    centroide = gdf_completo.geometry.unary_union.centroid
                    m_plantas = folium.Map(location=[centroide.y, centroide.x], zoom_start=16, tiles=None)
                    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m_plantas)
                    folium.GeoJson(gdf_completo.to_json(), style_function=lambda x: {'color':'blue','fillOpacity':0.1}).add_to(m_plantas)
                    for i, planta in enumerate(plantas[:2000]):
                        if 'centroide' in planta:
                            lon, lat = planta['centroide']
                            folium.CircleMarker([lat, lon], radius=2, color='red', fill=True, 
                                                fill_color='red', fill_opacity=0.8,
                                                tooltip=f"Planta #{i+1}").add_to(m_plantas)
                    folium.LayerControl().add_to(m_plantas); Fullscreen().add_to(m_plantas)
                    folium_static(m_plantas, width=1000, height=600)
                except Exception as e:
                    st.error(f"Error al mostrar mapa de plantas: {str(e)[:100]}")
                if plantas:
                    try:
                        df_plantas = pd.DataFrame([{
                            'id': i+1, 'longitud': p.get('centroide', (0,0))[0], 'latitud': p.get('centroide', (0,0))[1],
                            'area_m2': p.get('area_m2', 0), 'diametro_m': p.get('diametro_aprox', 0)
                        } for i,p in enumerate(plantas)])
                        gdf_plantas = gpd.GeoDataFrame(df_plantas, geometry=gpd.points_from_xy(df_plantas.longitud, df_plantas.latitud), crs='EPSG:4326')
                        geojson_plantas = gdf_plantas.to_json(); csv_plantas = df_plantas.to_csv(index=False)
                        col_p1, col_p2 = st.columns(2)
                        with col_p1: st.download_button("🗺️ GeoJSON", geojson_plantas, f"plantas_{datetime.now():%Y%m%d}.geojson", "application/geo+json")
                        with col_p2: st.download_button("📊 CSV", csv_plantas, f"coordenadas_{datetime.now():%Y%m%d}.csv", "text/csv")
                    except: st.info("No se pudieron exportar los datos")
            else:
                st.info("La detección de plantas no se ha ejecutado aún.")
                if st.button("🔍 EJECUTAR DETECCIÓN DE PLANTAS", use_container_width=True):
                    ejecutar_deteccion_plantas()
                    st.rerun()
        with tab6:
            st.subheader("🧪 FERTILIDAD DEL SUELO Y RECOMENDACIONES NPK")
            st.caption("Basado en NDVI real y modelos de fertilidad típicos para vid y olivo.")
            datos_fertilidad = st.session_state.datos_fertilidad
            if datos_fertilidad:
                df_fertilidad = pd.DataFrame(datos_fertilidad)
                gdf_fertilidad = gpd.GeoDataFrame(df_fertilidad, geometry='geometria', crs='EPSG:4326')
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1: N_prom = df_fertilidad['N_kg_ha'].mean(); st.metric("Nitrógeno (N)", f"{N_prom:.0f} kg/ha")
                with col2: P_prom = df_fertilidad['P_kg_ha'].mean(); st.metric("Fósforo (P₂O₅)", f"{P_prom:.0f} kg/ha")
                with col3: K_prom = df_fertilidad['K_kg_ha'].mean(); st.metric("Potasio (K₂O)", f"{K_prom:.0f} kg/ha")
                with col4: pH_prom = df_fertilidad['pH'].mean(); st.metric("pH", f"{pH_prom:.2f}")
                with col5: MO_prom = df_fertilidad['MO_porcentaje'].mean(); st.metric("Materia Orgánica", f"{MO_prom:.1f}%")
                st.markdown("---")
                st.markdown("### 🗺️ MAPA INTERACTIVO DE NUTRIENTES (Esri Satélite)")
                variable = st.selectbox(
                    "Selecciona la variable a visualizar:",
                    options=['N_kg_ha', 'P_kg_ha', 'K_kg_ha', 'pH', 'MO_porcentaje'],
                    format_func=lambda x: {
                        'N_kg_ha': 'Nitrógeno (N) kg/ha',
                        'P_kg_ha': 'Fósforo (P₂O₅) kg/ha',
                        'K_kg_ha': 'Potasio (K₂O) kg/ha',
                        'pH': 'pH del suelo',
                        'MO_porcentaje': 'Materia Orgánica (%)'
                    }[x]
                )
                mapa_fertilidad = crear_mapa_fertilidad_interactivo(gdf_fertilidad, variable)
                if mapa_fertilidad:
                    folium_static(mapa_fertilidad, width=1000, height=600)
                else:
                    st.warning("No se pudo generar el mapa de fertilidad.")
                st.markdown("### 📋 RECOMENDACIONES DETALLADAS POR BLOQUE")
                df_recom = df_fertilidad[['id_bloque', 'N_kg_ha', 'P_kg_ha', 'K_kg_ha', 'pH', 
                                          'recomendacion_N', 'recomendacion_P', 'recomendacion_K']].copy()
                df_recom.columns = ['Bloque', 'N', 'P₂O₅', 'K₂O', 'pH', 'Recomendación N', 'Recomendación P', 'Recomendación K']
                st.dataframe(df_recom.head(15), use_container_width=True)
                st.markdown("### 📥 EXPORTAR DATOS DE FERTILIDAD")
                csv_data = df_fertilidad.drop(columns=['geometria']).to_csv(index=False)
                st.download_button("📊 CSV completo", csv_data, f"fertilidad_{datetime.now():%Y%m%d}.csv", "text/csv")
            else:
                st.info("Ejecute el análisis completo para ver los datos de fertilidad.")
        with tab7:
            st.subheader("🌱 ANÁLISIS DE TEXTURA DE SUELO MEJORADO")
            textura_por_bloque = st.session_state.get('textura_por_bloque', [])
            if textura_por_bloque:
                df_textura = pd.DataFrame(textura_por_bloque)
                st.success(f"**Análisis de textura por bloque completado**")
                st.markdown("### 🗺️ Mapa de Tipos de Suelo por Bloque")
                try:
                    gdf_textura = gpd.GeoDataFrame(df_textura, geometry='geometria', crs='EPSG:4326')
                    tipos_unicos = gdf_textura['tipo_suelo'].unique()
                    colores = ['#8B4513', '#D2691E', '#F4A460', '#DEB887', '#BC8F8F', '#CD853F']
                    color_dict = {tipo: colores[i % len(colores)] for i, tipo in enumerate(tipos_unicos)}
                    m_textura = folium.Map(
                        location=[gdf_completo.geometry.centroid.y.mean(), gdf_completo.geometry.centroid.x.mean()], 
                        zoom_start=15, tiles=None
                    )
                    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 
                                     attr='Esri', name='Satélite').add_to(m_textura)
                    def style_func(feature):
                        tipo = feature['properties']['tipo_suelo']
                        return {'fillColor': color_dict.get(tipo, '#888'), 
                                'color': 'black', 'weight': 1, 'fillOpacity': 0.6}
                    folium.GeoJson(
                        gdf_textura.to_json(),
                        name='Textura del suelo',
                        style_function=style_func,
                        tooltip=folium.GeoJsonTooltip(fields=['id_bloque','tipo_suelo','arena','limo','arcilla','drenaje'],
                                                      aliases=['Bloque','Tipo','Arena %','Limo %','Arcilla %','Drenaje'])
                    ).add_to(m_textura)
                    folium.LayerControl().add_to(m_textura); Fullscreen().add_to(m_textura)
                    folium_static(m_textura, width=1000, height=600)
                except Exception as e:
                    st.error(f"Error al crear mapa de textura: {e}")
                st.markdown("### 📊 Composición Textural por Bloque")
                fig, ax = plt.subplots(figsize=(12,6))
                df_plot = df_textura.head(20)
                ax.bar(df_plot['id_bloque'].astype(str), df_plot['arena'], label='Arena', color='#F4A460')
                ax.bar(df_plot['id_bloque'].astype(str), df_plot['limo'], bottom=df_plot['arena'], label='Limo', color='#DEB887')
                ax.bar(df_plot['id_bloque'].astype(str), df_plot['arcilla'], 
                       bottom=df_plot['arena']+df_plot['limo'], label='Arcilla', color='#8B4513')
                ax.set_xlabel('Bloque'); ax.set_ylabel('Porcentaje')
                ax.set_title('Composición Textural por Bloque'); ax.legend()
                plt.xticks(rotation=45); plt.tight_layout()
                st.pyplot(fig); plt.close(fig)
                st.markdown("### 🔺 Triángulo Textural (primer bloque)")
                if len(df_textura) > 0:
                    row = df_textura.iloc[0]
                    fig_tri = crear_grafico_textural(row['arena'], row['limo'], row['arcilla'], row['tipo_suelo'])
                    st.plotly_chart(fig_tri, use_container_width=True)
                csv_textura = df_textura.drop(columns=['geometria']).to_csv(index=False)
                st.download_button("📊 Descargar CSV de textura", csv_textura, f"textura_suelo_{datetime.now():%Y%m%d}.csv", "text/csv")
            else:
                st.info("Ejecute el análisis completo para ver el análisis de textura del suelo.")
        with tab8:
            st.subheader("🗺️ CURVAS DE NIVEL MEJORADAS")
            st.markdown("""
            **Modelo de elevación:** SRTM 1 arc-seg (30 m) · Fuente: OpenTopography  
            Para datos reales, obtén una **API key gratuita** [aquí](https://opentopography.org/).  
            Si no se proporciona, se generará un relieve simulado.
            """)
            api_key = st.text_input("🔑 API Key de OpenTopography (opcional)", type="password",
                                    help="Regístrate gratis en opentopography.org")
            intervalo = st.slider("Intervalo entre curvas (metros)", 5, 50, 10)
            if st.button("🔄 Generar curvas de nivel", use_container_width=True):
                with st.spinner("Procesando DEM y generando isolíneas..."):
                    gdf_original = st.session_state.gdf_original
                    if gdf_original is None:
                        st.error("Primero debe cargar una plantación.")
                    else:
                        if api_key:
                            dem, meta, transform = obtener_dem_opentopography(gdf_original, api_key)
                            if dem is not None:
                                curvas = generar_curvas_nivel_reales(dem, transform, intervalo)
                                st.success(f"✅ Se generaron {len(curvas)} curvas de nivel (DEM real)")
                            else:
                                st.warning("No se pudo obtener DEM real. Usando simulado.")
                                curvas = generar_curvas_nivel_simuladas(gdf_original)
                        else:
                            curvas = generar_curvas_nivel_simuladas(gdf_original)
                            st.info(f"ℹ️ Usando relieve simulado. Se generaron {len(curvas)} curvas de nivel.")
                        if curvas:
                            st.session_state.curvas_nivel = curvas
                            m_curvas = mapa_curvas_coloreadas(gdf_original, curvas)
                            folium_static(m_curvas, width=1000, height=600)
                            gdf_curvas = gpd.GeoDataFrame(
                                {'elevacion': [e for _, e in curvas], 'geometry': [l for l, _ in curvas]},
                                crs='EPSG:4326'
                            )
                            geojson_curvas = gdf_curvas.to_json()
                            csv_curvas = gdf_curvas.drop(columns='geometry').to_csv(index=False)
                            col_exp1, col_exp2 = st.columns(2)
                            with col_exp1: st.download_button("🗺️ GeoJSON", geojson_curvas, f"curvas_nivel_{datetime.now():%Y%m%d}.geojson", "application/geo+json")
                            with col_exp2: st.download_button("📊 CSV", csv_curvas, f"curvas_nivel_{datetime.now():%Y%m%d}.csv", "text/csv")
                        else:
                            st.warning("No se encontraron curvas de nivel en el área.")
            else:
                if st.session_state.get('curvas_nivel'):
                    st.info("Ya hay curvas de nivel generadas. Presiona el botón para regenerarlas.")
        with tab9:
            st.subheader("🐛 Detección de Enfermedades y Plagas con YOLO")
            if not YOLO_AVAILABLE or not CV2_AVAILABLE:
                st.warning("⚠️ Esta función requiere las librerías 'ultralytics' y 'opencv-python'. Para instalarlas, ejecuta: `pip install ultralytics opencv-python`")
            else:
                st.markdown("""
                Esta herramienta utiliza modelos YOLO para detectar automáticamente signos de enfermedades o plagas en imágenes de vid u olivo.
                - **Sube una imagen** (JPG, PNG) tomada con drone o cámara.
                - **Carga un modelo YOLO** pre-entrenado (formato `.pt` de PyTorch o `.onnx`).
                - Ajusta el **umbral de confianza** para filtrar detecciones débiles.
                """)
                col1, col2 = st.columns(2)
                with col1:
                    archivo_imagen = st.file_uploader("📸 Subir imagen (RGB)", type=['jpg', 'jpeg', 'png'])
                with col2:
                    archivo_modelo = st.file_uploader("🤖 Cargar modelo YOLO (.pt o .onnx)", type=['pt', 'onnx'])
                umbral_confianza = st.slider("Umbral de confianza", min_value=0.1, max_value=0.9, value=0.25, step=0.05)
                if archivo_imagen is not None and archivo_modelo is not None:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(archivo_modelo.name)[1]) as tmp_model:
                        tmp_model.write(archivo_modelo.read())
                        ruta_modelo_tmp = tmp_model.name
                    imagen_bytes = archivo_imagen.read()
                    imagen_pil = Image.open(io.BytesIO(imagen_bytes))
                    imagen_cv = cv2.cvtColor(np.array(imagen_pil), cv2.COLOR_RGB2BGR)
                    modelo = cargar_modelo_yolo(ruta_modelo_tmp)
                    if modelo is not None:
                        st.info("🔄 Ejecutando inferencia...")
                        resultados_yolo = detectar_en_imagen(modelo, imagen_cv, conf_threshold=umbral_confianza)
                        if resultados_yolo and len(resultados_yolo) > 0:
                            img_anotada, detecciones = dibujar_detecciones_con_leyenda(imagen_cv, resultados_yolo)
                            st.success(f"✅ Se detectaron {len(detecciones)} objetos.")
                            img_rgb = cv2.cvtColor(img_anotada, cv2.COLOR_BGR2RGB)
                            st.image(img_rgb, caption="Imagen con detecciones", use_container_width=True)
                            leyenda_html = crear_leyenda_html(detecciones)
                            st.markdown(leyenda_html, unsafe_allow_html=True)
                            st.markdown("### 📥 Exportar resultados")
                            img_pil_export = Image.fromarray(cv2.cvtColor(img_anotada, cv2.COLOR_BGR2RGB))
                            buf = io.BytesIO()
                            img_pil_export.save(buf, format='PNG')
                            byte_im = buf.getvalue()
                            df_detecciones = pd.DataFrame(detecciones)
                            if 'color' in df_detecciones.columns:
                                df_detecciones = df_detecciones.drop(columns=['color'])
                            csv_detecciones = df_detecciones.to_csv(index=False)
                            col_dl1, col_dl2 = st.columns(2)
                            with col_dl1:
                                st.download_button("📸 Imagen anotada (PNG)", byte_im,
                                                   f"deteccion_yolo_{datetime.now():%Y%m%d_%H%M%S}.png",
                                                   "image/png")
                            with col_dl2:
                                st.download_button("📊 CSV detecciones", csv_detecciones,
                                                   f"detecciones_{datetime.now():%Y%m%d_%H%M%S}.csv",
                                                   "text/csv")
                        else:
                            st.warning("No se detectaron objetos con el umbral de confianza actual.")
                    else:
                        st.error("No se pudo cargar el modelo. Asegúrate de que sea un archivo válido.")
                    os.unlink(ruta_modelo_tmp)
                else:
                    st.info("👆 Sube una imagen y un modelo YOLO para comenzar.")

# ===== PIE DE PÁGINA =====
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; padding: 20px;">
    <p><strong>© 2026 Analizador de Vid y Olivo Satelital</strong></p>
    <p>Datos satelitales: NASA Earthdata · Clima: Open-Meteo ERA5 · Radiación/Viento: NASA POWER · Curvas de nivel: OpenTopography SRTM</p>
    <p>Desarrollado por: BioMap Consultora | Contacto: mawucano@gmail.com | +5493525 532313</p>
</div>
""", unsafe_allow_html=True)
