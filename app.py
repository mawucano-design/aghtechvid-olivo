# app.py - Analizador de Vid y Olivo Satelital (sin autenticación ni pagos)
# 
# - Carga de polígono de plantación.
# - División en bloques y análisis NDVI/NDWI con datos reales NASA Earthdata (MOD13Q1, MOD09GA) o simulación.
# - Datos climáticos de Open-Meteo y NASA POWER.
# - Detección de plantas individuales, fertilidad NPK, textura de suelo, curvas de nivel y YOLO.
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
def obtener_ndvi_earthdata(gdf_dividido, fecha_inicio, fecha_fin):
    if not EARTHDATA_OK:
        st.warning("Earthaccess no instalado. Usando datos simulados.")
        return None
    if not EARTHDATA_USERNAME or not EARTHDATA_PASSWORD:
        st.warning("Credenciales de Earthdata no configuradas. Usando datos simulados.")
        return None

    try:
        auth = earthaccess.login()
        if not auth.authenticated:
            st.warning("No se pudo autenticar con Earthdata. Usando datos simulados.")
            return None

        bounds = gdf_dividido.total_bounds
        bbox = (bounds[0], bounds[1], bounds[2], bounds[3])

        results = earthaccess.search_data(
            short_name='MOD13Q1',
            version='061',
            bounding_box=bbox,
            temporal=(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')),
            count=5
        )

        if not results:
            st.warning("No se encontraron escenas MOD13Q1 en el período. Usando datos simulados.")
            return None

        granule = results[0]
        st.info(f"Procesando escena NDVI: {granule['umm']['GranuleUR']}")

        temp_dir = tempfile.mkdtemp()
        try:
            downloaded_files = earthaccess.download(granule, local_path=temp_dir)
        except Exception as e:
            st.warning(f"Error en descarga con earthaccess: {str(e)}. Usando datos simulados.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        if not downloaded_files:
            st.warning("No se pudo descargar el archivo. Usando datos simulados.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        # Convertir a string para evitar problemas con objetos Path
        downloaded_files = [str(f) for f in downloaded_files]

        hdf_files = [f for f in downloaded_files if f.endswith('.hdf')]
        if not hdf_files:
            st.warning("No se encontró archivo HDF en la descarga. Usando datos simulados.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        download_path = hdf_files[0]

        # Verificar que no sea HTML
        if os.path.getsize(download_path) < 10240:
            with open(download_path, 'r', errors='ignore') as f:
                head = f.read(500).lower()
                if '<html' in head:
                    st.warning("El archivo descargado es HTML de error. Usando datos simulados.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

        # Intento con rasterio
        rasterio_success = False
        if RASTERIO_OK:
            try:
                with rasterio.open(download_path) as src:
                    subdatasets = src.subdatasets
                    ndvi_sub = None
                    for sd in subdatasets:
                        if 'NDVI' in sd or 'ndvi' in sd.lower():
                            ndvi_sub = sd
                            break
                    if ndvi_sub:
                        with rasterio.open(ndvi_sub) as src_ndvi:
                            raster_crs = src_ndvi.crs
                            nodata = src_ndvi.nodata
                            gdf_proj = gdf_dividido.to_crs(raster_crs)
                            ndvi_values = []
                            progress_bar = st.progress(0, text="Procesando bloques para NDVI...")
                            for idx, row in gdf_proj.iterrows():
                                geom = [mapping(row.geometry)]
                                try:
                                    out_image, _ = mask(src_ndvi, geom, crop=True, nodata=nodata)
                                    data = out_image[0]
                                    data_scaled = data.astype(np.float32) * 0.0001
                                    mask_invalid = (data == nodata) | (data_scaled < -1) | (data_scaled > 1)
                                    data_clean = np.ma.masked_where(mask_invalid, data_scaled)
                                    mean_val = data_clean.mean()
                                    if np.ma.is_masked(mean_val) or np.isnan(mean_val):
                                        ndvi_values.append(np.nan)
                                    else:
                                        ndvi_values.append(round(float(mean_val), 3))
                                except Exception:
                                    ndvi_values.append(np.nan)
                                progress_bar.progress((idx + 1) / len(gdf_proj))
                            progress_bar.empty()
                            gdf_dividido['ndvi_modis'] = ndvi_values
                            st.success("✅ NDVI calculado con rasterio.")
                            rasterio_success = True
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return gdf_dividido
            except Exception:
                pass

        # Fallback con pyhdf
        if not rasterio_success and PYHDF_OK:
            try:
                hdf = SD(download_path, SDC.READ)
                ndvi_dataset = None
                for name in hdf.datasets().keys():
                    if 'NDVI' in name:
                        ndvi_dataset = name
                        break
                if ndvi_dataset is None:
                    st.warning("No se encontró dataset NDVI. Usando datos simulados.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

                ndvi_data = hdf.select(ndvi_dataset).get()
                ndvi_scaled = ndvi_data.astype(np.float32) * 0.0001

                # Extraer geolocalización con regex mejorada
                try:
                    metadata = hdf.attributes()['StructMetadata.0']
                    xdim_match = re.search(r'XDim\s*=\s*(\d+)', metadata, re.IGNORECASE)
                    ydim_match = re.search(r'YDim\s*=\s*(\d+)', metadata, re.IGNORECASE)
                    ul_match = re.search(
                        r'UpperLeftPointMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*[,]?\s*([+-]?\d+\.?\d*)\s*\)',
                        metadata, re.IGNORECASE
                    )
                    lr_match = re.search(
                        r'LowerRightMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*[,]?\s*([+-]?\d+\.?\d*)\s*\)',
                        metadata, re.IGNORECASE
                    )

                    if not (xdim_match and ydim_match and ul_match and lr_match):
                        st.warning("No se pudo extraer la geolocalización completa del HDF. Usando datos simulados.")
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return None
                    if len(ul_match.groups()) < 2 or len(lr_match.groups()) < 2:
                        st.warning("Formato inesperado en coordenadas de geolocalización. Usando datos simulados.")
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return None

                    xdim = int(xdim_match.group(1))
                    ydim = int(ydim_match.group(1))
                    ulx = float(ul_match.group(1))
                    uly = float(ul_match.group(2))
                    lrx = float(lr_match.group(1))
                    lry = float(lr_match.group(2))

                    if ndvi_scaled.shape != (ydim, xdim):
                        ydim, xdim = ndvi_scaled.shape

                    res_x = (lrx - ulx) / xdim
                    res_y = (uly - lry) / ydim
                    transform = rasterio.Affine(res_x, 0, ulx, 0, -res_y, uly)
                    crs = rasterio.crs.CRS.from_proj4("+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181 +units=m +no_defs")

                    with rasterio.io.MemoryFile() as memfile:
                        with memfile.open(
                            driver='GTiff',
                            height=ydim,
                            width=xdim,
                            count=1,
                            dtype=ndvi_scaled.dtype,
                            crs=crs,
                            transform=transform,
                            nodata=-32768
                        ) as dst:
                            dst.write(ndvi_scaled, 1)

                        with memfile.open() as src_ndvi:
                            gdf_proj = gdf_dividido.to_crs(crs)
                            ndvi_values = []
                            progress_bar = st.progress(0, text="Procesando bloques para NDVI con pyhdf...")
                            for idx, row in gdf_proj.iterrows():
                                geom = [mapping(row.geometry)]
                                try:
                                    out_image, _ = mask(src_ndvi, geom, crop=True, nodata=-32768)
                                    data = out_image[0]
                                    mask_invalid = (data == -32768) | (data < -1) | (data > 1)
                                    data_clean = np.ma.masked_where(mask_invalid, data)
                                    mean_val = data_clean.mean()
                                    if np.ma.is_masked(mean_val) or np.isnan(mean_val):
                                        ndvi_values.append(np.nan)
                                    else:
                                        ndvi_values.append(round(float(mean_val), 3))
                                except Exception:
                                    ndvi_values.append(np.nan)
                                progress_bar.progress((idx + 1) / len(gdf_proj))
                            progress_bar.empty()
                            gdf_dividido['ndvi_modis'] = ndvi_values
                            st.success("✅ NDVI calculado con pyhdf.")
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return gdf_dividido

                except Exception as e_meta:
                    st.warning(f"No se pudo extraer la geolocalización del archivo HDF: {str(e_meta)}. Usando datos simulados.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

            except Exception as e_pyhdf:
                st.warning(f"Error al procesar con pyhdf: {str(e_pyhdf)}. Usando datos simulados.")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None
        else:
            st.warning("No se pudo leer el archivo HDF (ni rasterio ni pyhdf disponibles). Usando datos simulados.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    except Exception as e:
        st.warning(f"Error en obtención de NDVI: {str(e)}. Usando datos simulados.")
        return None

def obtener_ndwi_earthdata(gdf_dividido, fecha_inicio, fecha_fin):
    if not EARTHDATA_OK:
        st.warning("Earthaccess no instalado. Usando datos simulados.")
        return None
    if not EARTHDATA_USERNAME or not EARTHDATA_PASSWORD:
        st.warning("Credenciales de Earthdata no configuradas. Usando datos simulados.")
        return None

    try:
        auth = earthaccess.login()
        if not auth.authenticated:
            st.warning("No se pudo autenticar con Earthdata. Usando datos simulados.")
            return None

        bounds = gdf_dividido.total_bounds
        bbox = (bounds[0], bounds[1], bounds[2], bounds[3])

        results = earthaccess.search_data(
            short_name='MOD09GA',
            version='061',
            bounding_box=bbox,
            temporal=(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')),
            count=5
        )

        if not results:
            st.warning("No se encontraron escenas MOD09GA. Usando datos simulados.")
            return None

        granule = results[0]
        st.info(f"Procesando escena NDWI: {granule['umm']['GranuleUR']}")

        temp_dir = tempfile.mkdtemp()
        try:
            downloaded_files = earthaccess.download(granule, local_path=temp_dir)
        except Exception as e:
            st.warning(f"Error en descarga: {str(e)}. Usando datos simulados.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        if not downloaded_files:
            st.warning("No se pudo descargar el archivo. Usando datos simulados.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        downloaded_files = [str(f) for f in downloaded_files]

        hdf_files = [f for f in downloaded_files if f.endswith('.hdf')]
        if not hdf_files:
            st.warning("No se encontró archivo HDF. Usando datos simulados.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        download_path = hdf_files[0]

        if os.path.getsize(download_path) < 10240:
            with open(download_path, 'r', errors='ignore') as f:
                head = f.read(500).lower()
                if '<html' in head:
                    st.warning("El archivo descargado es HTML de error. Usando datos simulados.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

        rasterio_success = False
        if RASTERIO_OK:
            try:
                with rasterio.open(download_path) as src:
                    subdatasets = src.subdatasets
                    nir_sub = swir_sub = None
                    for sd in subdatasets:
                        if 'sur_refl_b02' in sd:
                            nir_sub = sd
                        elif 'sur_refl_b06' in sd:
                            swir_sub = sd
                    if nir_sub and swir_sub:
                        with rasterio.open(nir_sub) as src_nir, rasterio.open(swir_sub) as src_swir:
                            raster_crs = src_nir.crs
                            nodata_nir = src_nir.nodata
                            nodata_swir = src_swir.nodata
                            gdf_proj = gdf_dividido.to_crs(raster_crs)
                            ndwi_values = []
                            progress_bar = st.progress(0, text="Procesando bloques para NDWI...")
                            for idx, row in gdf_proj.iterrows():
                                geom = [mapping(row.geometry)]
                                try:
                                    out_nir, _ = mask(src_nir, geom, crop=True, nodata=nodata_nir)
                                    nir_band = out_nir[0].astype(np.float32) * 0.0001
                                    out_swir, _ = mask(src_swir, geom, crop=True, nodata=nodata_swir)
                                    swir_band = out_swir[0].astype(np.float32) * 0.0001
                                    valid = (nir_band != nodata_nir * 0.0001) & (swir_band != nodata_swir * 0.0001) & (nir_band + swir_band != 0)
                                    nir_valid = np.ma.masked_where(~valid, nir_band)
                                    swir_valid = np.ma.masked_where(~valid, swir_band)
                                    with np.errstate(divide='ignore', invalid='ignore'):
                                        ndwi = (nir_valid - swir_valid) / (nir_valid + swir_valid)
                                    mean_val = ndwi.mean()
                                    if np.ma.is_masked(mean_val) or np.isnan(mean_val):
                                        ndwi_values.append(np.nan)
                                    else:
                                        ndwi_values.append(round(float(mean_val), 3))
                                except Exception:
                                    ndwi_values.append(np.nan)
                                progress_bar.progress((idx + 1) / len(gdf_proj))
                            progress_bar.empty()
                            gdf_dividido['ndwi_modis'] = ndwi_values
                            st.success("✅ NDWI calculado con rasterio.")
                            rasterio_success = True
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return gdf_dividido
            except Exception:
                pass

        if not rasterio_success and PYHDF_OK:
            try:
                hdf = SD(download_path, SDC.READ)
                nir_data = swir_data = None
                for name in hdf.datasets().keys():
                    if 'sur_refl_b02' in name:
                        nir_data = hdf.select(name).get()
                    elif 'sur_refl_b06' in name:
                        swir_data = hdf.select(name).get()
                if nir_data is None or swir_data is None:
                    st.warning("No se encontraron bandas NIR/SWIR. Usando datos simulados.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

                nir = nir_data.astype(np.float32) * 0.0001
                swir = swir_data.astype(np.float32) * 0.0001

                metadata = hdf.attributes()['StructMetadata.0']
                xdim_match = re.search(r'XDim\s*=\s*(\d+)', metadata, re.IGNORECASE)
                ydim_match = re.search(r'YDim\s*=\s*(\d+)', metadata, re.IGNORECASE)
                ul_match = re.search(
                    r'UpperLeftPointMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*[,]?\s*([+-]?\d+\.?\d*)\s*\)',
                    metadata, re.IGNORECASE
                )
                lr_match = re.search(
                    r'LowerRightMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*[,]?\s*([+-]?\d+\.?\d*)\s*\)',
                    metadata, re.IGNORECASE
                )

                if not (xdim_match and ydim_match and ul_match and lr_match):
                    st.warning("No se pudo extraer la geolocalización completa del HDF. Usando datos simulados.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None
                if len(ul_match.groups()) < 2 or len(lr_match.groups()) < 2:
                    st.warning("Formato inesperado en coordenadas de geolocalización. Usando datos simulados.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

                xdim = int(xdim_match.group(1))
                ydim = int(ydim_match.group(1))
                ulx = float(ul_match.group(1))
                uly = float(ul_match.group(2))
                lrx = float(lr_match.group(1))
                lry = float(lr_match.group(2))

                if nir.shape != (ydim, xdim):
                    ydim, xdim = nir.shape

                res_x = (lrx - ulx) / xdim
                res_y = (uly - lry) / ydim
                transform = rasterio.Affine(res_x, 0, ulx, 0, -res_y, uly)
                crs = rasterio.crs.CRS.from_proj4("+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181 +units=m +no_defs")

                with rasterio.io.MemoryFile() as memfile_nir, rasterio.io.MemoryFile() as memfile_swir:
                    with memfile_nir.open(driver='GTiff', height=ydim, width=xdim, count=1,
                                          dtype=nir.dtype, crs=crs, transform=transform, nodata=-32768) as dst_nir:
                        dst_nir.write(nir, 1)
                    with memfile_swir.open(driver='GTiff', height=ydim, width=xdim, count=1,
                                          dtype=swir.dtype, crs=crs, transform=transform, nodata=-32768) as dst_swir:
                        dst_swir.write(swir, 1)

                    with memfile_nir.open() as src_nir, memfile_swir.open() as src_swir:
                        gdf_proj = gdf_dividido.to_crs(crs)
                        ndwi_values = []
                        progress_bar = st.progress(0, text="Procesando bloques para NDWI con pyhdf...")
                        for idx, row in gdf_proj.iterrows():
                            geom = [mapping(row.geometry)]
                            try:
                                out_nir, _ = mask(src_nir, geom, crop=True, nodata=-32768)
                                nir_band = out_nir[0]
                                out_swir, _ = mask(src_swir, geom, crop=True, nodata=-32768)
                                swir_band = out_swir[0]
                                valid = (nir_band != -32768) & (swir_band != -32768) & (nir_band + swir_band != 0)
                                nir_valid = np.ma.masked_where(~valid, nir_band)
                                swir_valid = np.ma.masked_where(~valid, swir_band)
                                with np.errstate(divide='ignore', invalid='ignore'):
                                    ndwi = (nir_valid - swir_valid) / (nir_valid + swir_valid)
                                mean_val = ndwi.mean()
                                if np.ma.is_masked(mean_val) or np.isnan(mean_val):
                                    ndwi_values.append(np.nan)
                                else:
                                    ndwi_values.append(round(float(mean_val), 3))
                            except Exception:
                                ndwi_values.append(np.nan)
                            progress_bar.progress((idx + 1) / len(gdf_proj))
                        progress_bar.empty()
                        gdf_dividido['ndwi_modis'] = ndwi_values
                        st.success("✅ NDWI calculado con pyhdf.")
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return gdf_dividido

            except Exception as e_pyhdf:
                st.warning(f"Error con pyhdf: {str(e_pyhdf)}. Usando datos simulados.")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return None
        else:
            st.warning("No se pudo leer el archivo HDF. Usando datos simulados.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    except Exception as e:
        st.warning(f"Error en obtención de NDWI: {str(e)}. Usando datos simulados.")
        return None

# ===== FUNCIONES CLIMÁTICAS =====
def obtener_clima_openmeteo(gdf, fecha_inicio, fecha_fin):
    try:
        centroide = gdf.geometry.unary_union.centroid
        lat, lon = centroide.y, centroide.x
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": fecha_inicio.strftime("%Y-%m-%d"),
            "end_date": fecha_fin.strftime("%Y-%m-%d"),
            "daily": ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean", "precipitation_sum"],
            "timezone": "auto"
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "daily" not in data:
            raise ValueError("No se recibieron datos diarios")
        tmax = [t if t is not None else np.nan for t in data["daily"]["temperature_2m_max"]]
        tmin = [t if t is not None else np.nan for t in data["daily"]["temperature_2m_min"]]
        tmean = [t if t is not None else np.nan for t in data["daily"]["temperature_2m_mean"]]
        precip = [p if p is not None else 0.0 for p in data["daily"]["precipitation_sum"]]
        return {
            'precipitacion': {
                'total': round(sum(precip), 1),
                'maxima_diaria': round(max(precip) if precip else 0, 1),
                'dias_con_lluvia': sum(1 for p in precip if p > 0.1),
                'diaria': [round(p, 1) for p in precip]
            },
            'temperatura': {
                'promedio': round(np.nanmean(tmean), 1),
                'maxima': round(np.nanmax(tmax), 1),
                'minima': round(np.nanmin(tmin), 1),
                'diaria': [round(t, 1) if not np.isnan(t) else np.nan for t in tmean]
            },
            'periodo': f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}",
            'fuente': 'Open-Meteo ERA5'
        }
    except Exception as e:
        st.warning(f"Error en Open-Meteo: {str(e)[:100]}. Usando datos simulados.")
        return generar_clima_simulado()

def obtener_radiacion_viento_power(gdf, fecha_inicio, fecha_fin):
    try:
        centroide = gdf.geometry.unary_union.centroid
        lat, lon = centroide.y, centroide.x
        start = fecha_inicio.strftime("%Y%m%d")
        end = fecha_fin.strftime("%Y%m%d")
        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        params = {
            "parameters": "ALLSKY_SFC_SW_DWN,WS2M",
            "community": "RE",
            "longitude": lon,
            "latitude": lat,
            "start": start,
            "end": end,
            "format": "JSON"
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        props = data['properties']['parameter']
        radiacion = props.get('ALLSKY_SFC_SW_DWN', {})
        viento = props.get('WS2M', {})
        fechas = sorted(radiacion.keys())
        rad_diaria = [radiacion[f] if radiacion[f] != -999 else np.nan for f in fechas]
        wind_diaria = [viento[f] if viento[f] != -999 else np.nan for f in fechas]
        return {
            'radiacion': {
                'promedio': round(np.nanmean(rad_diaria), 1),
                'maxima': round(np.nanmax(rad_diaria), 1),
                'minima': round(np.nanmin(rad_diaria), 1),
                'diaria': [round(r, 1) if not np.isnan(r) else np.nan for r in rad_diaria]
            },
            'viento': {
                'promedio': round(np.nanmean(wind_diaria), 1),
                'maxima': round(np.nanmax(wind_diaria), 1),
                'diaria': [round(w, 1) if not np.isnan(w) else np.nan for w in wind_diaria]
            },
            'fuente': 'NASA POWER'
        }
    except Exception as e:
        st.warning(f"Error en NASA POWER: {str(e)[:100]}. Usando datos simulados.")
        clima_sim = generar_clima_simulado()
        return {
            'radiacion': clima_sim['radiacion'],
            'viento': clima_sim['viento'],
            'fuente': 'Simulado (fallback)'
        }

# ===== DETECCIÓN DE PLANTAS =====
def mejorar_deteccion_plantas(gdf, densidad=130, crop_type='Vid'):
    try:
        bounds = gdf.total_bounds
        min_lon, min_lat, max_lon, max_lat = bounds
        gdf_proj = gdf.to_crs('EPSG:3857')
        area_m2 = gdf_proj.geometry.area.sum()
        area_ha = area_m2 / 10000
        if area_ha <= 0:
            return {'detectadas': [], 'total': 0}
        num_plantas_objetivo = int(area_ha * densidad)
        espaciado_grados = 9 / 111000
        x_coords, y_coords = [], []
        x = min_lon
        while x <= max_lon:
            y = min_lat
            while y <= max_lat:
                x_coords.append(x)
                y_coords.append(y)
                y += espaciado_grados
            x += espaciado_grados
        for i in range(len(x_coords)):
            if i % 2 == 1:
                x_coords[i] += espaciado_grados / 2
        plantacion_union = gdf.unary_union
        plantas = []
        for i in range(len(x_coords)):
            if len(plantas) >= num_plantas_objetivo:
                break
            point = Point(x_coords[i], y_coords[i])
            if plantacion_union.contains(point):
                lon = x_coords[i] + np.random.normal(0, espaciado_grados * 0.1)
                lat = y_coords[i] + np.random.normal(0, espaciado_grados * 0.1)
                if crop_type == 'Vid':
                    area_m2 = np.random.uniform(1, 4)
                    diametro = np.random.uniform(1.0, 2.5)
                else:
                    area_m2 = np.random.uniform(4, 12)
                    diametro = np.random.uniform(2.0, 4.0)
                plantas.append({
                    'centroide': (lon, lat),
                    'area_m2': area_m2,
                    'circularidad': np.random.uniform(0.7, 0.95),
                    'diametro_aprox': diametro,
                    'simulado': True
                })
        return {
            'detectadas': plantas,
            'total': len(plantas),
            'densidad_calculada': len(plantas) / area_ha,
            'area_ha': area_ha
        }
    except Exception as e:
        print(f"Error en detección: {e}")
        return {'detectadas': [], 'total': 0}

def ejecutar_deteccion_plantas():
    if st.session_state.gdf_original is None:
        st.error("Primero debe cargar un archivo de plantación")
        return
    with st.spinner("Ejecutando detección de plantas..."):
        gdf = st.session_state.gdf_original
        densidad = st.session_state.densidad_personalizada
        crop_type = st.session_state.crop_type
        resultados = mejorar_deteccion_plantas(gdf, densidad, crop_type)
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
def analizar_textura_suelo_venezuela_por_bloque(gdf_dividido):
    resultados = []
    try:
        centroide_global = gdf_dividido.geometry.unary_union.centroid
        lat_base = centroide_global.y
        if lat_base > 10:
            base = 'Franco Arcilloso'
            alt_base = 'Arcilloso'
        elif lat_base > 7:
            base = 'Franco Arcilloso Arenoso'
            alt_base = 'Franco'
        elif lat_base > 4:
            base = 'Arenoso Franco'
            alt_base = 'Arenoso'
        else:
            base = 'Franco Arcilloso'
            alt_base = 'Arcilloso Pesado'
        caracteristicas = {
            'Franco Arcilloso': {'arena': 35, 'limo': 25, 'arcilla': 30, 'textura': 'Media', 'drenaje': 'Moderado', 'CIC': 'Alto (15-25)', 'ret_agua': 'Alta', 'recomendacion': 'Ideal para vid y olivo'},
            'Franco Arcilloso Arenoso': {'arena': 45, 'limo': 20, 'arcilla': 25, 'textura': 'Media-ligera', 'drenaje': 'Bueno', 'CIC': 'Medio (10-15)', 'ret_agua': 'Moderada', 'recomendacion': 'Requiere riego'},
            'Arenoso Franco': {'arena': 55, 'limo': 15, 'arcilla': 20, 'textura': 'Ligera', 'drenaje': 'Excelente', 'CIC': 'Bajo (5-10)', 'ret_agua': 'Baja', 'recomendacion': 'Fertilización fraccionada'},
            'Arcilloso': {'arena': 25, 'limo': 20, 'arcilla': 40, 'textura': 'Pesada', 'drenaje': 'Limitado', 'CIC': 'Muy alto (25-35)', 'ret_agua': 'Muy alta', 'recomendacion': 'Drenaje y labranza'},
            'Arcilloso Pesado': {'arena': 20, 'limo': 15, 'arcilla': 50, 'textura': 'Muy pesada', 'drenaje': 'Muy limitado', 'CIC': 'Extremo (>35)', 'ret_agua': 'Extrema', 'recomendacion': 'Drenaje intensivo'},
            'Franco': {'arena': 40, 'limo': 40, 'arcilla': 20, 'textura': 'Media', 'drenaje': 'Bueno', 'CIC': 'Medio (10-20)', 'ret_agua': 'Media', 'recomendacion': 'Manejo estándar'},
            'Arenoso': {'arena': 70, 'limo': 15, 'arcilla': 15, 'textura': 'Ligera', 'drenaje': 'Excelente', 'CIC': 'Muy bajo (<5)', 'ret_agua': 'Muy baja', 'recomendacion': 'Riego frecuente'}
        }
        for idx, row in gdf_dividido.iterrows():
            centroid = row.geometry.centroid
            semilla = abs(int(centroid.x * 1000 + centroid.y * 1000)) % (2**32)
            np.random.seed(semilla)
            r = np.random.random()
            tipo = base if r < 0.7 else alt_base
            carac = caracteristicas.get(tipo, caracteristicas['Franco Arcilloso'])
            arena = carac['arena'] + np.random.randint(-5, 6)
            limo = carac['limo'] + np.random.randint(-5, 6)
            arcilla = carac['arcilla'] + np.random.randint(-5, 6)
            total = arena + limo + arcilla
            arena = int(arena / total * 100)
            limo = int(limo / total * 100)
            arcilla = 100 - arena - limo
            resultados.append({
                'id_bloque': row.get('id_bloque', idx+1),
                'tipo_suelo': tipo,
                'arena': arena,
                'limo': limo,
                'arcilla': arcilla,
                'textura': carac['textura'],
                'drenaje': carac['drenaje'],
                'CIC': carac['CIC'],
                'ret_agua': carac['ret_agua'],
                'recomendacion': carac['recomendacion'],
                'geometria': row.geometry
            })
        return resultados
    except Exception as e:
        st.error(f"Error en análisis de textura: {e}")
        return []

# ===== FERTILIDAD NPK =====
def generar_mapa_fertilidad(gdf):
    try:
        fertilidad_data = []
        for idx, row in gdf.iterrows():
            ndvi = row.get('ndvi_modis', 0.65)
            if ndvi > 0.75:
                N = np.random.uniform(120, 180)
                P = np.random.uniform(40, 70)
                K = np.random.uniform(180, 250)
                pH = np.random.uniform(5.8, 6.5)
                MO = np.random.uniform(3.5, 5.0)
            elif ndvi > 0.6:
                N = np.random.uniform(80, 120)
                P = np.random.uniform(25, 40)
                K = np.random.uniform(120, 180)
                pH = np.random.uniform(5.2, 5.8)
                MO = np.random.uniform(2.5, 3.5)
            else:
                N = np.random.uniform(40, 80)
                P = np.random.uniform(15, 25)
                K = np.random.uniform(80, 120)
                pH = np.random.uniform(4.8, 5.2)
                MO = np.random.uniform(1.5, 2.5)
            rec_N = f"Aplicar {max(0, 120-N):.0f} kg/ha N" if N < 100 else "Mantener dosis actual"
            rec_P = f"Aplicar {max(0, 50-P):.0f} kg/ha P2O5" if P < 30 else "Mantener dosis actual"
            rec_K = f"Aplicar {max(0, 200-K):.0f} kg/ha K2O" if K < 150 else "Mantener dosis actual"
            fertilidad_data.append({
                'id_bloque': row.get('id_bloque', idx+1),
                'N_kg_ha': round(N, 1),
                'P_kg_ha': round(P, 1),
                'K_kg_ha': round(K, 1),
                'pH': round(pH, 2),
                'MO_porcentaje': round(MO, 2),
                'recomendacion_N': rec_N,
                'recomendacion_P': rec_P,
                'recomendacion_K': rec_K,
                'geometria': row.geometry
            })
        return fertilidad_data
    except Exception:
        return []

# ===== FUNCIONES DE VISUALIZACIÓN =====
def crear_mapa_interactivo_base(gdf, columna_color=None, colormap=None, tooltip_fields=None, tooltip_aliases=None):
    if gdf is None or len(gdf) == 0:
        return None
    centroide = gdf.geometry.unary_union.centroid
    m = folium.Map(location=[centroide.y, centroide.x], zoom_start=16, tiles=None, control_scale=True)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri, Maxar, Earthstar Geographics',
        name='Satélite Esri',
        overlay=False,
        control=True
    ).add_to(m)
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='OpenStreetMap',
        name='OpenStreetMap',
        overlay=False,
        control=True
    ).add_to(m)
    if columna_color and colormap:
        def style_function(feature):
            valor = feature['properties'].get(columna_color, 0)
            if isinstance(valor, (int, float)):
                if np.isnan(valor):
                    valor = 0
            else:
                try:
                    valor = float(valor) if valor is not None else 0
                except:
                    valor = 0
            color = colormap(valor) if hasattr(colormap, '__call__') else '#3388ff'
            return {'fillColor': color, 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.7}
    else:
        def style_function(feature):
            return {'fillColor': '#3388ff', 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.4}
    if tooltip_fields and tooltip_aliases:
        tooltip = folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True)
    else:
        tooltip = None
    folium.GeoJson(gdf.to_json(), name='Polígonos', style_function=style_function, tooltip=tooltip).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    Fullscreen(position='topright').add_to(m)
    MeasureControl(position='topright').add_to(m)
    MiniMap(toggle_display=True).add_to(m)
    return m

def mostrar_estadisticas_indice(gdf, columna, titulo, vmin, vmax, colormap_list):
    if columna not in gdf.columns:
        st.error(f"La columna {columna} no está disponible.")
        return
    valores = gdf[columna].dropna()
    if len(valores) == 0:
        st.warning(f"No hay datos válidos para {titulo}.")
        return
    colormap = LinearColormap(colors=colormap_list, vmin=vmin, vmax=vmax, caption=titulo)
    mapa = crear_mapa_interactivo_base(
        gdf,
        columna_color=columna,
        colormap=colormap,
        tooltip_fields=['id_bloque', columna],
        tooltip_aliases=['Bloque', titulo]
    )
    if mapa:
        colormap.add_to(mapa)
        folium_static(mapa, width=1000, height=600)
    else:
        st.warning("No se pudo generar el mapa. Mostrando gráfico de barras.")
        fig, ax = plt.subplots(figsize=(10,4))
        ax.bar(range(len(gdf)), gdf[columna].values, color='steelblue')
        ax.set_xlabel('Bloque')
        ax.set_ylabel(titulo)
        ax.set_title(f'Valores de {titulo} por bloque')
        st.pyplot(fig)
        plt.close(fig)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("Media", f"{valores.mean():.3f}")
    with col2: st.metric("Mediana", f"{valores.median():.3f}")
    with col3: st.metric("Desv. estándar", f"{valores.std():.3f}")
    with col4: st.metric("Mínimo", f"{valores.min():.3f}")
    with col5: st.metric("Máximo", f"{valores.max():.3f}")
    st.markdown("#### Valores por bloque")
    df_tabla = gdf[['id_bloque', columna]].copy()
    df_tabla.columns = ['Bloque', titulo]
    st.dataframe(df_tabla.style.format({titulo: '{:.3f}'}), use_container_width=True)

def mostrar_comparacion_ndvi_ndwi(gdf):
    if gdf is None or len(gdf) == 0:
        st.warning("No hay datos para la comparación.")
        return
    df = gdf[['id_bloque', 'ndvi_modis', 'ndwi_modis', 'salud', 'area_ha']].copy()
    df = df.dropna()
    if len(df) == 0:
        st.warning("Datos insuficientes para la comparación.")
        return
    st.markdown("### 🔍 Comparación NDVI vs NDWI")
    try:
        import statsmodels.api as sm
        statsmodels_ok = True
    except ImportError:
        statsmodels_ok = False
        st.info("ℹ️ Para ver la línea de tendencia, instala 'statsmodels' con: pip install statsmodels")
    fig = px.scatter(
        df, x='ndvi_modis', y='ndwi_modis', color='salud',
        size='area_ha', hover_data=['id_bloque'],
        labels={'ndvi_modis': 'NDVI', 'ndwi_modis': 'NDWI', 'salud': 'Salud'},
        title='Relación entre NDVI y NDWI por bloque',
        color_discrete_map={'Crítica': '#d73027', 'Baja': '#fee08b', 'Moderada': '#91cf60', 'Buena': '#1a9850'},
        trendline='ols' if statsmodels_ok else None,
        trendline_color_override='gray'
    )
    fig.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey')))
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Top 5 NDVI")
        top_ndvi = df.nlargest(5, 'ndvi_modis')[['id_bloque', 'ndvi_modis', 'salud']]
        top_ndvi.columns = ['Bloque', 'NDVI', 'Salud']
        st.dataframe(top_ndvi.style.format({'NDVI': '{:.3f}'}), use_container_width=True)
        st.markdown("#### Bottom 5 NDVI")
        bottom_ndvi = df.nsmallest(5, 'ndvi_modis')[['id_bloque', 'ndvi_modis', 'salud']]
        bottom_ndvi.columns = ['Bloque', 'NDVI', 'Salud']
        st.dataframe(bottom_ndvi.style.format({'NDVI': '{:.3f}'}), use_container_width=True)
    with col2:
        st.markdown("#### Top 5 NDWI")
        top_ndwi = df.nlargest(5, 'ndwi_modis')[['id_bloque', 'ndwi_modis', 'salud']]
        top_ndwi.columns = ['Bloque', 'NDWI', 'Salud']
        st.dataframe(top_ndwi.style.format({'NDWI': '{:.3f}'}), use_container_width=True)
        st.markdown("#### Bottom 5 NDWI")
        bottom_ndwi = df.nsmallest(5, 'ndwi_modis')[['id_bloque', 'ndwi_modis', 'salud']]
        bottom_ndwi.columns = ['Bloque', 'NDWI', 'Salud']
        st.dataframe(bottom_ndwi.style.format({'NDWI': '{:.3f}'}), use_container_width=True)

def crear_mapa_fertilidad_interactivo(gdf_fertilidad, variable):
    info_var = {
        'N_kg_ha': {'titulo': 'Nitrógeno (N)', 'unidad': 'kg/ha', 'vmin': 40, 'vmax': 180, 'cmap': 'YlGnBu'},
        'P_kg_ha': {'titulo': 'Fósforo (P₂O₅)', 'unidad': 'kg/ha', 'vmin': 15, 'vmax': 70, 'cmap': 'YlOrRd'},
        'K_kg_ha': {'titulo': 'Potasio (K₂O)', 'unidad': 'kg/ha', 'vmin': 80, 'vmax': 250, 'cmap': 'YlGn'},
        'pH': {'titulo': 'pH del suelo', 'unidad': '', 'vmin': 4.5, 'vmax': 6.5, 'cmap': 'RdYlGn_r'},
        'MO_porcentaje': {'titulo': 'Materia Orgánica', 'unidad': '%', 'vmin': 1.0, 'vmax': 5.0, 'cmap': 'BrBG'}
    }
    info = info_var.get(variable, {'titulo': variable, 'unidad': '', 'vmin': None, 'vmax': None, 'cmap': 'YlOrRd'})
    colormap = LinearColormap(
        colors=['#ffffb2','#fecc5c','#fd8d3c','#f03b20','#bd0026'] if info['cmap'] == 'YlOrRd' else
                ['#c7e9c0','#74c476','#31a354','#006d2c'] if info['cmap'] == 'YlGn' else
                ['#4575b4','#91bfdb','#e0f3f8','#fee090','#fc8d59','#d73027'] if info['cmap'] == 'RdYlGn_r' else
                ['#8c510a','#bf812d','#dfc27d','#f6e8c3','#c7eae5','#80cdc1','#35978f','#01665e'],
        vmin=info['vmin'] if info['vmin'] else gdf_fertilidad[variable].min(),
        vmax=info['vmax'] if info['vmax'] else gdf_fertilidad[variable].max(),
        caption=f"{info['titulo']} ({info['unidad']})"
    )
    m = crear_mapa_interactivo_base(
        gdf_fertilidad,
        columna_color=variable,
        colormap=colormap,
        tooltip_fields=['id_bloque', variable, 'recomendacion_N', 'recomendacion_P', 'recomendacion_K'],
        tooltip_aliases=['Bloque', f'{info["titulo"]} ({info["unidad"]})', 'Recom. N', 'Recom. P', 'Recom. K']
    )
    if m:
        colormap.add_to(m)
    return m

def crear_grafico_textural(arena, limo, arcilla, tipo_suelo):
    fig = go.Figure()
    fig.add_trace(go.Scatterternary(
        a=[arcilla], b=[limo], c=[arena],
        mode='markers+text',
        marker=dict(size=14, color='red'),
        text=[tipo_suelo],
        textposition='top center',
        name='Suelo actual'
    ))
    fig.update_layout(
        title='Triángulo Textural',
        ternary=dict(
            sum=100,
            aaxis=dict(title='% Arcilla', min=0, linewidth=2),
            baxis=dict(title='% Limo', min=0, linewidth=2),
            caxis=dict(title='% Arena', min=0, linewidth=2)
        ),
        height=500, width=600
    )
    return fig

# ===== FUNCIONES YOLO (protegidas) =====
def cargar_modelo_yolo(ruta_modelo):
    if not YOLO_AVAILABLE or not CV2_AVAILABLE:
        st.error("Las librerías ultralytics u opencv-python no están instaladas.")
        return None
    try:
        modelo = YOLO(ruta_modelo)
        return modelo
    except Exception as e:
        st.error(f"Error al cargar el modelo YOLO: {str(e)}")
        return None

def detectar_en_imagen(modelo, imagen_cv, conf_threshold=0.25):
    if modelo is None:
        return None
    try:
        resultados = modelo(imagen_cv, conf=conf_threshold)
        return resultados
    except Exception as e:
        st.error(f"Error en la inferencia YOLO: {str(e)}")
        return None

def dibujar_detecciones_con_leyenda(imagen_cv, resultados, colores_aleatorios=True):
    if not CV2_AVAILABLE:
        return imagen_cv, []
    if resultados is None or len(resultados) == 0:
        return imagen_cv, []
    img_anotada = imagen_cv.copy()
    detecciones_info = []
    names = resultados[0].names
    for r in resultados:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = names[cls_id]
            if colores_aleatorios:
                color = tuple(np.random.randint(0, 255, 3).tolist())
            else:
                np.random.seed(cls_id)
                color = tuple(np.random.randint(0, 255, 3).tolist())
                np.random.seed(None)
            cv2.rectangle(img_anotada, (x1, y1), (x2, y2), color, 3)
            etiqueta = f"{label} {conf:.2f}"
            (w, h), _ = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img_anotada, (x1, y1 - h - 10), (x1 + w, y1), color, -1)
            cv2.putText(img_anotada, etiqueta, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            detecciones_info.append({
                'clase': label,
                'confianza': round(conf, 3),
                'bbox': [x1, y1, x2, y2],
                'color': color
            })
    return img_anotada, detecciones_info

def crear_leyenda_html(detecciones_info):
    if not detecciones_info:
        return "<p>No se detectaron objetos.</p>"
    clases_vistas = {}
    for d in detecciones_info:
        if d['clase'] not in clases_vistas:
            clases_vistas[d['clase']] = d['color']
    from collections import Counter
    conteo_clases = Counter([d['clase'] for d in detecciones_info])
    html = "<div style='background: rgba(30, 30, 30, 0.9); padding: 15px; border-radius: 10px; margin-top: 20px;'>"
    html += "<h4 style='color: white; margin-bottom: 10px;'>📋 Leyenda de detecciones</h4>"
    html += "<table style='width: 100%; color: white; border-collapse: collapse;'>"
    html += "<tr><th>Color</th><th>Clase</th><th>Conteo</th></tr>"
    for clase, color in clases_vistas.items():
        color_hex = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
        html += f"<tr style='border-bottom: 1px solid #444;'>"
        html += f"<td style='padding: 8px;'><span style='display: inline-block; width: 20px; height: 20px; background-color: {color_hex}; border-radius: 4px;'></span></td>"
        html += f"<td style='padding: 8px;'>{clase}</td>"
        html += f"<td style='padding: 8px; text-align: center;'>{conteo_clases[clase]}</td>"
        html += f"</tr>"
    html += "</table></div>"
    return html

# ===== CURVAS DE NIVEL =====
def obtener_dem_opentopography(gdf, api_key=None):
    try:
        import rasterio
        from rasterio.mask import mask
    except ImportError:
        st.warning("Para curvas de nivel reales instala rasterio y scikit-image")
        return None, None, None
    if api_key is None:
        api_key = os.environ.get("OPENTOPOGRAPHY_API_KEY", None)
    if not api_key:
        return None, None, None
    try:
        bounds = gdf.total_bounds
        west, south, east, north = bounds
        lon_span = east - west
        lat_span = north - south
        west -= lon_span * 0.05
        east += lon_span * 0.05
        south -= lat_span * 0.05
        north += lat_span * 0.05
        url = "https://portal.opentopography.org/API/globaldem"
        params = {
            "demtype": "SRTMGL1",
            "south": south,
            "north": north,
            "west": west,
            "east": east,
            "outputFormat": "GTiff",
            "API_Key": api_key
        }
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        dem_bytes = BytesIO(response.content)
        with rasterio.open(dem_bytes) as src:
            geom = [mapping(gdf.unary_union)]
            out_image, out_transform = mask(src, geom, crop=True, nodata=-32768)
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "nodata": -32768
            })
        return out_image.squeeze(), out_meta, out_transform
    except Exception as e:
        st.error(f"Error descargando DEM: {str(e)[:200]}")
        return None, None, None

def generar_curvas_nivel_simuladas(gdf):
    try:
        from skimage import measure
    except ImportError:
        return []
    bounds = gdf.total_bounds
    minx, miny, maxx, maxy = bounds
    n = 100
    x = np.linspace(minx, maxx, n)
    y = np.linspace(miny, maxy, n)
    X, Y = np.meshgrid(x, y)
    np.random.seed(42)
    Z = np.random.randn(n, n) * 20
    from scipy.ndimage import gaussian_filter
    Z = gaussian_filter(Z, sigma=5)
    Z = 50 + (Z - Z.min()) / (Z.max() - Z.min()) * 150
    contours = []
    niveles = np.arange(50, 200, 10)
    for nivel in niveles:
        try:
            for contour in measure.find_contours(Z, nivel):
                coords = []
                for row, col in contour:
                    lat = miny + (row / n) * (maxy - miny)
                    lon = minx + (col / n) * (maxx - minx)
                    coords.append((lon, lat))
                if len(coords) > 2:
                    line = LineString(coords)
                    if line.length > 0.01:
                        contours.append((line, nivel))
        except:
            continue
    return contours

def generar_curvas_nivel_reales(dem_array, transform, intervalo=10):
    try:
        from skimage import measure
    except ImportError:
        return []
    if dem_array is None:
        return []
    dem_array = np.ma.masked_where(dem_array <= -999, dem_array)
    vmin = dem_array.min()
    vmax = dem_array.max()
    if vmin is np.ma.masked or vmax is np.ma.masked:
        return []
    niveles = np.arange(np.floor(vmin / intervalo) * intervalo,
                        np.ceil(vmax / intervalo) * intervalo + intervalo,
                        intervalo)
    contours = []
    for nivel in niveles:
        try:
            for contour in measure.find_contours(dem_array.filled(fill_value=-999), nivel):
                coords = []
                for row, col in contour:
                    x, y = transform * (col, row)
                    coords.append((x, y))
                if len(coords) > 2:
                    line = LineString(coords)
                    if line.length > 0.01:
                        contours.append((line, nivel))
        except:
            continue
    return contours

def mapa_curvas_coloreadas(gdf_original, curvas_con_elevacion):
    centroide = gdf_original.geometry.unary_union.centroid
    m = folium.Map(location=[centroide.y, centroide.x], zoom_start=15, tiles=None, control_scale=True)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                     attr='Esri', name='Satélite Esri', overlay=False, control=True).add_to(m)
    folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                     attr='OpenStreetMap', name='OpenStreetMap', overlay=False, control=True).add_to(m)
    folium.GeoJson(gdf_original.to_json(), name='Plantación',
                   style_function=lambda x: {'color': 'blue', 'fillOpacity': 0.1, 'weight': 2}).add_to(m)
    elevaciones = [e for _, e in curvas_con_elevacion]
    if elevaciones:
        vmin = min(elevaciones); vmax = max(elevaciones)
        colormap = LinearColormap(colors=['green','yellow','orange','brown'], vmin=vmin, vmax=vmax, caption='Elevación (m.s.n.m)')
        colormap.add_to(m)
        for line, elev in curvas_con_elevacion:
            folium.GeoJson(gpd.GeoSeries(line).to_json(), name='Curvas',
                           style_function=lambda x, e=elev: {'color': colormap(e), 'weight': 1.5, 'opacity': 0.9},
                           tooltip=f'Elevación: {elev:.0f} m').add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    Fullscreen().add_to(m)
    return m

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
    crop_type = st.radio(
        "Cultivo",
        ["Vid", "Olivo"],
        horizontal=True,
        index=0 if st.session_state.crop_type == "Vid" else 1,
        key="crop_selector"
    )
    st.session_state.crop_type = crop_type

    # Selección de variedad según cultivo
    if crop_type == "Vid":
        default_vid = 0
        if st.session_state.variedad_seleccionada in VARIEDADES_VID:
            default_vid = VARIEDADES_VID.index(st.session_state.variedad_seleccionada)
        variedad = st.selectbox(
            "Variedad de Vid:",
            VARIEDADES_VID,
            index=default_vid,
            key="variedad_vid"
        )
    else:
        default_olivo = 0
        if st.session_state.variedad_seleccionada in VARIEDADES_OLIVO:
            default_olivo = VARIEDADES_OLIVO.index(st.session_state.variedad_seleccionada)
        variedad = st.selectbox(
            "Variedad de Olivo:",
            VARIEDADES_OLIVO,
            index=default_olivo,
            key="variedad_olivo"
        )
    st.session_state.variedad_seleccionada = variedad

    st.markdown("---")
    st.markdown("### 📅 Rango Temporal")
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio_widget = st.date_input(
            "Inicio",
            value=st.session_state.fecha_inicio.date(),
            key="fecha_inicio_widget"
        )
    with col2:
        fecha_fin_widget = st.date_input(
            "Fin",
            value=st.session_state.fecha_fin.date(),
            key="fecha_fin_widget"
        )
    if fecha_inicio_widget is not None:
        st.session_state.fecha_inicio = datetime.combine(fecha_inicio_widget, datetime.min.time())
    if fecha_fin_widget is not None:
        st.session_state.fecha_fin = datetime.combine(fecha_fin_widget, datetime.min.time())

    st.markdown("---")
    st.markdown("### 🎯 División")
    n_divisiones_val = st.slider(
        "Número de bloques:",
        min_value=8,
        max_value=32,
        value=st.session_state.n_divisiones,
        key="n_divisiones"
    )
    st.session_state.n_divisiones = n_divisiones_val

    st.markdown("---")
    st.markdown("### 🌱 Detección de Plantas")
    deteccion_habilitada = st.checkbox("Activar detección de plantas", value=True, key="deteccion_checkbox")
    if deteccion_habilitada:
        densidad_val = st.slider(
            "Densidad objetivo (plantas/ha):",
            min_value=50,
            max_value=200,
            value=st.session_state.densidad_personalizada,
            key="densidad_slider"
        )
        st.session_state.densidad_personalizada = densidad_val

    st.markdown("---")
    st.markdown("### 🧪 Análisis de Suelo")
    analisis_suelo_val = st.checkbox(
        "Activar análisis de suelo",
        value=st.session_state.analisis_suelo,
        key="suelo_checkbox"
    )
    st.session_state.analisis_suelo = analisis_suelo_val
    if st.session_state.analisis_suelo:
        st.info("Incluye: Textura por bloque, fertilidad NPK, recomendaciones")

    st.markdown("---")
    st.markdown("### 📤 Subir Polígono")
    uploaded_file = st.file_uploader(
        "Subir archivo de plantación", 
        type=['zip', 'kml', 'kmz', 'geojson'],
        help="Formatos: Shapefile (.zip), KML (.kmz), GeoJSON (.geojson)",
        key="polygon_uploader"
    )
    if uploaded_file is not None:
        st.info(f"📄 Archivo: {uploaded_file.name}")
        st.info(f"📊 Tamaño: {uploaded_file.size / 1024:.1f} KB")
        if st.button("🔄 Cargar Polígono", key="load_polygon_btn"):
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
                if st.button("🚀 EJECUTAR ANÁLISIS", use_container_width=True, key="ejecutar_analisis"):
                    ejecutar_analisis_completo()
                    st.rerun()
            else:
                if st.button("🔄 RE-EJECUTAR", use_container_width=True, key="reejecutar_analisis"):
                    st.session_state.analisis_completado = False
                    ejecutar_analisis_completo()
                    st.rerun()
        with col_btn2:
            if deteccion_habilitada:
                if st.button("🔍 DETECTAR PLANTAS", use_container_width=True, key="detectar_plantas"):
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
                    mime="text/csv",
                    key="download_resumen"
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
                with col_dl1: st.download_button("🗺️ GeoJSON", geojson_indices, f"indices_{datetime.now():%Y%m%d}.geojson", "application/geo+json", key="download_geojson")
                with col_dl2: st.download_button("📊 CSV", csv_indices, f"indices_{datetime.now():%Y%m%d}.csv", "text/csv", key="download_csv_indices")
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
                        with col_p1: st.download_button("🗺️ GeoJSON", geojson_plantas, f"plantas_{datetime.now():%Y%m%d}.geojson", "application/geo+json", key="download_plantas_geojson")
                        with col_p2: st.download_button("📊 CSV", csv_plantas, f"coordenadas_{datetime.now():%Y%m%d}.csv", "text/csv", key="download_plantas_csv")
                    except: st.info("No se pudieron exportar los datos")
            else:
                st.info("La detección de plantas no se ha ejecutado aún.")
                if st.button("🔍 EJECUTAR DETECCIÓN DE PLANTAS", key="detectar_plantas_tab5", use_container_width=True):
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
                    }[x],
                    key="fertilidad_var"
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
                st.download_button("📊 CSV completo", csv_data, f"fertilidad_{datetime.now():%Y%m%d}.csv", "text/csv", key="download_fertilidad")
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
                st.download_button("📊 Descargar CSV de textura", csv_textura, f"textura_suelo_{datetime.now():%Y%m%d}.csv", "text/csv", key="download_textura")
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
                                    help="Regístrate gratis en opentopography.org", key="api_key")
            intervalo = st.slider("Intervalo entre curvas (metros)", 5, 50, 10, key="intervalo")
            if st.button("🔄 Generar curvas de nivel", use_container_width=True, key="gen_curvas"):
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
                            with col_exp1: st.download_button("🗺️ GeoJSON", geojson_curvas, f"curvas_nivel_{datetime.now():%Y%m%d}.geojson", "application/geo+json", key="download_curvas_geojson")
                            with col_exp2: st.download_button("📊 CSV", csv_curvas, f"curvas_nivel_{datetime.now():%Y%m%d}.csv", "text/csv", key="download_curvas_csv")
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
                    archivo_imagen = st.file_uploader("📸 Subir imagen (RGB)", type=['jpg', 'jpeg', 'png'], key="yolo_img")
                with col2:
                    archivo_modelo = st.file_uploader("🤖 Cargar modelo YOLO (.pt o .onnx)", type=['pt', 'onnx'], key="yolo_model")
                umbral_confianza = st.slider("Umbral de confianza", min_value=0.1, max_value=0.9, value=0.25, step=0.05, key="yolo_conf")
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
                                                   "image/png", key="download_yolo_png")
                            with col_dl2:
                                st.download_button("📊 CSV detecciones", csv_detecciones,
                                                   f"detecciones_{datetime.now():%Y%m%d_%H%M%S}.csv",
                                                   "text/csv", key="download_yolo_csv")
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
