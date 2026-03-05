# app.py - Versión definitiva con Earthaccess y pagos separados
# Requiere: streamlit, geopandas, pandas, numpy, matplotlib, shapely, folium, streamlit-folium, branca, plotly, scipy, pillow, opencv-python, ultralytics, mercadopago, earthaccess, xarray, rioxarray, rasterio, pyhdf

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
import base64
import time
import shutil
import sqlite3
import hashlib
import mercadopago

# ===== MANEJO CONDICIONAL DE OPENCV Y YOLO =====
try:
    import cv2
    CV2_AVAILABLE = True
except:
    CV2_AVAILABLE = False
    cv2 = None

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

# ===== LIBRERÍAS SATELITALES =====
try:
    import earthaccess
    import xarray as xr
    import rioxarray
    EARTHDATA_OK = True
except ImportError:
    EARTHDATA_OK = False

try:
    import rasterio
    from rasterio.mask import mask
    RASTERIO_OK = True
except ImportError:
    RASTERIO_OK = False

try:
    from pyhdf.SD import SD, SDC
    PYHDF_OK = True
except ImportError:
    PYHDF_OK = False

# ===== CONFIGURACIÓN DE MERCADO PAGO =====
MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
if not MERCADOPAGO_ACCESS_TOKEN:
    st.error("❌ Variable MERCADOPAGO_ACCESS_TOKEN no configurada.")
    st.stop()

sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)

EARTHDATA_USERNAME = os.environ.get("EARTHDATA_USERNAME")
EARTHDATA_PASSWORD = os.environ.get("EARTHDATA_PASSWORD")

# ===== BASE DE DATOS DE USUARIOS =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hash):
    return hash_password(password) == hash

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Crear tabla base
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT UNIQUE,
                  password_hash TEXT,
                  subscription_expires TIMESTAMP,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    # Agregar columna subscription_plan si no existe
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if 'subscription_plan' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN subscription_plan TEXT DEFAULT 'combo'")
    # Usuario administrador
    admin_email = "mawucano@gmail.com"
    far_future = "2100-01-01 00:00:00"
    c.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE users SET subscription_expires = ?, subscription_plan = 'combo' WHERE email = ?", (far_future, admin_email))
    else:
        default_password = "admin123"
        password_hash = hash_password(default_password)
        c.execute("INSERT INTO users (email, password_hash, subscription_expires, subscription_plan) VALUES (?, ?, ?, ?)",
                  (admin_email, password_hash, far_future, 'combo'))
    conn.commit()
    conn.close()

init_db()

def register_user(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        password_hash = hash_password(password)
        c.execute("INSERT INTO users (email, password_hash, subscription_expires, subscription_plan) VALUES (?, ?, ?, ?)",
                  (email, password_hash, None, None))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, password_hash, subscription_expires, subscription_plan FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row and verify_password(password, row[1]):
        return {'id': row[0], 'email': email, 'subscription_expires': row[2], 'subscription_plan': row[3]}
    return None

def update_subscription(email, days=30, plan='combo'):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    new_expiry = (datetime.now() + timedelta(days=days)).isoformat()
    c.execute("UPDATE users SET subscription_expires = ?, subscription_plan = ? WHERE email = ?", (new_expiry, plan, email))
    conn.commit()
    conn.close()
    return new_expiry

def get_user_by_email(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, email, subscription_expires, subscription_plan FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'email': row[1], 'subscription_expires': row[2], 'subscription_plan': row[3]}
    return None

# ===== FUNCIONES DE MERCADO PAGO =====
def create_preference(email, amount, description):
    try:
        base_url = os.environ.get("APP_BASE_URL", "https://tuapp.streamlit.app")
        preference_data = {
            "items": [{
                "title": description,
                "quantity": 1,
                "currency_id": "USD",
                "unit_price": amount
            }],
            "payer": {"email": email},
            "back_urls": {
                "success": f"{base_url}?payment=success",
                "failure": f"{base_url}?payment=failure",
                "pending": f"{base_url}?payment=pending"
            },
            "auto_return": "approved",
            "external_reference": email,
        }
        preference_response = sdk.preference().create(preference_data)
        if preference_response["status"] in [200, 201]:
            preference = preference_response["response"]
            return preference["init_point"], preference["id"]
        else:
            st.error("Error al crear preferencia")
            return None, None
    except Exception as e:
        st.error(f"Error conectando con Mercado Pago: {e}")
        return None, None

def check_payment_status(payment_id):
    try:
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] == 200 and payment_info["response"]["status"] == "approved":
            email = payment_info["response"].get("external_reference")
            if email:
                update_subscription(email, days=30, plan='combo')
                return True
    except:
        pass
    return False

# ===== AUTENTICACIÓN EN STREAMLIT =====
def show_login_signup():
    with st.sidebar:
        st.markdown("## 🔐 Acceso")
        menu = st.radio("", ["Iniciar sesión", "Registrarse"], key="auth_menu")
        email = st.text_input("Email", key="auth_email")
        password = st.text_input("Contraseña", type="password", key="auth_password")
        if menu == "Registrarse":
            if st.button("Registrar"):
                if register_user(email, password):
                    st.success("Registro exitoso. Inicia sesión.")
                else:
                    st.error("Email ya registrado.")
        else:
            if st.button("Ingresar"):
                user = login_user(email, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")

def logout():
    if st.sidebar.button("Cerrar sesión"):
        del st.session_state.user
        st.rerun()

# ===== VERIFICACIÓN DE SUSCRIPCIÓN Y PLAN =====
def check_subscription():
    gdf_temp = st.session_state.get('gdf_original', None)
    if 'user' not in st.session_state:
        show_login_signup()
        if gdf_temp is not None:
            st.session_state.gdf_original = gdf_temp
        st.stop()

    user = st.session_state.user
    crop_type = st.session_state.get('crop_type', 'Vid')

    if st.session_state.get('demo_mode', False):
        with st.sidebar:
            st.markdown(f"👤 Usuario: {user['email']} (Modo DEMO)")
            if st.button("💳 Actualizar a Premium"):
                st.session_state.demo_mode = False
                st.session_state.payment_intent = True
                st.rerun()
            logout()
        return

    with st.sidebar:
        st.markdown(f"👤 Usuario: {user['email']}")
        logout()

    expiry = user.get('subscription_expires')
    plan = user.get('subscription_plan', 'combo')

    if expiry:
        try:
            expiry_date = datetime.fromisoformat(expiry)
            if expiry_date > datetime.now():
                dias = (expiry_date - datetime.now()).days
                st.sidebar.info(f"✅ Suscripción activa ({dias} días) - Plan: {plan}")
                st.session_state.demo_mode = False
                # Validar plan contra cultivo
                if crop_type == 'Vid' and plan not in ['vid', 'combo']:
                    st.warning("Tu plan no incluye Vid. Debes adquirir el plan Vid o Combo.")
                    st.session_state.payment_intent = True
                    st.rerun()
                elif crop_type == 'Olivo' and plan not in ['olivo', 'combo']:
                    st.warning("Tu plan no incluye Olivo. Debes adquirir el plan Olivo o Combo.")
                    st.session_state.payment_intent = True
                    st.rerun()
                return True
        except:
            pass

    st.warning("🔒 Suscripción expirada o no activa.")
    st.markdown("### ¿Cómo deseas continuar?")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 💳 Pagar ahora")
        plan_opcion = st.radio("Plan:", ["Vid ($80/mes)", "Olivo ($80/mes)", "Combo ($150/mes)"], key="plan_selection")
        amount = 80.0 if "Vid" in plan_opcion or "Olivo" in plan_opcion else 150.0
        plan_desc = "Vid" if "Vid" in plan_opcion else "Olivo" if "Olivo" in plan_opcion else "Combo"
        if st.button("💵 Ir a pagar"):
            st.session_state.payment_intent = True
            st.session_state.selected_plan = plan_desc
            st.session_state.selected_amount = amount
            st.rerun()
    with col2:
        st.markdown("#### 🆓 Modo DEMO")
        if st.button("🎮 Continuar con DEMO"):
            st.session_state.demo_mode = True
            st.rerun()

    if st.session_state.get('payment_intent', False):
        st.markdown("### 💳 Pago con Mercado Pago")
        plan_desc = st.session_state.get('selected_plan', 'Combo')
        amount = st.session_state.get('selected_amount', 150.0)
        st.write(f"Plan **{plan_desc}** por **${amount} USD**.")
        if st.button("💵 Pagar ahora", key="pay_mp"):
            init_point, pref_id = create_preference(user['email'], amount, f"Suscripción {plan_desc}")
            if init_point:
                st.session_state.pref_id = pref_id
                st.markdown(f"[Haz clic aquí para pagar]({init_point})")
                st.info("Luego de pagar, regresa a esta página.")
            else:
                st.error("No se pudo generar el link de pago.")

        st.markdown("### 🏦 Transferencia bancaria")
        st.code("CBU: 3220001888034378480018\nAlias: inflar.pacu.inaudita")
        st.write("Envía comprobante a **mawucano@gmail.com**")

        query_params = st.query_params
        if 'payment' in query_params and query_params['payment'] == 'success' and 'collection_id' in query_params:
            payment_id = query_params['collection_id']
            if check_payment_status(payment_id):
                st.success("✅ Pago aprobado. Suscripción activada.")
                updated_user = get_user_by_email(user['email'])
                if updated_user:
                    st.session_state.user = updated_user
                st.session_state.demo_mode = False
                st.session_state.payment_intent = False
                st.rerun()
            else:
                st.error("No se pudo verificar el pago.")
        st.stop()

    st.stop()

# ===== FUNCIONES DE SIMULACIÓN (solo para DEMO) =====
def generar_datos_simulados_completos(gdf_original, n_divisiones):
    gdf_dividido = dividir_plantacion_en_bloques(gdf_original, n_divisiones)
    areas_ha = []
    for idx, row in gdf_dividido.iterrows():
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
    edades = 5 + 10 * np.random.rand(len(lons))
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
            'maxima': round(max(wind_diaria), 1),
            'diaria': [round(w, 1) for w in wind_diaria]
        },
        'periodo': 'Últimos 60 días (simulado)',
        'fuente': 'Datos simulados (DEMO)'
    }

# ===== CONFIGURACIÓN DE PÁGINA =====
st.set_page_config(page_title="Analizador de Vid y Olivo", page_icon="🍇", layout="wide", initial_sidebar_state="expanded")

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
        'variedad_seleccionada': 'Malbec',
        'textura_suelo': {},
        'textura_por_bloque': [],
        'datos_fertilidad': [],
        'analisis_suelo': True,
        'curvas_nivel': None,
        'demo_mode': False,
        'payment_intent': False,
        'selected_plan': 'Combo',
        'selected_amount': 150.0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()
check_subscription()

# ===== VARIEDADES =====
VARIEDADES_VID = ['Malbec', 'Cabernet Sauvignon', 'Merlot', 'Syrah', 'Chardonnay', 'Torrontés', 'Bonarda', 'Tempranillo', 'Garnacha', 'Moscatel', 'Pinot Noir', 'Sauvignon Blanc', 'Albariño', 'Verdejo', 'Chenin Blanc']
VARIEDADES_OLIVO = ['Arbequina', 'Picual', 'Hojiblanca', 'Manzanilla', 'Frantoio', 'Coratina', 'Leccino', 'Empeltre', 'Cornicabra', 'Changlot Real', 'Arauco', 'Nevadillo', 'Farga', 'Morisca', 'Verdial']

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
        st.warning(f"Error corrigiendo CRS: {e}")
        return gdf

def calcular_superficie(gdf):
    try:
        if gdf is None or len(gdf) == 0:
            return 0.0
        gdf = validar_y_corregir_crs(gdf)
        gdf_projected = gdf.to_crs('EPSG:3857')
        area_m2 = gdf_projected.geometry.area.sum()
        return area_m2 / 10000
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
            cell_maxx = minx + (j+1) * width
            cell_miny = miny + i * height
            cell_maxy = miny + (i+1) * height
            cell_poly = Polygon([(cell_minx, cell_miny), (cell_maxx, cell_miny), (cell_maxx, cell_maxy), (cell_minx, cell_maxy)])
            intersection = plantacion_principal.intersection(cell_poly)
            if not intersection.is_empty and intersection.area > 0:
                sub_poligonos.append(intersection)
    if sub_poligonos:
        nuevo_gdf = gpd.GeoDataFrame({'id_bloque': range(1, len(sub_poligonos)+1), 'geometry': sub_poligonos}, crs='EPSG:4326')
        return nuevo_gdf
    return gdf

# ===== PARSER KML =====
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
            coord_list = []
            coords = re.split(r'[\s\n\t]+', coord_text)
            for coord in coords:
                coord = coord.strip()
                if not coord or ',' not in coord:
                    continue
                try:
                    parts = coord.split(',')
                    if len(parts) >= 2:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        if -180 <= lon <= 180 and -90 <= lat <= 90:
                            coord_list.append((lon, lat))
                except:
                    continue
            if len(coord_list) >= 3:
                if coord_list[0] != coord_list[-1]:
                    coord_list.append(coord_list[0])
                try:
                    polygon = Polygon(coord_list)
                    if polygon.is_valid and polygon.area > 0:
                        polygons.append(polygon)
                except:
                    continue
        if polygons:
            return gpd.GeoDataFrame(geometry=polygons, crs='EPSG:4326')
        placemarks = re.findall(r'<Placemark[^>]*>([\s\S]*?)</Placemark>', content, re.IGNORECASE | re.DOTALL)
        for placemark in placemarks:
            coord_match = re.search(r'<coordinates[^>]*>([\s\S]*?)</coordinates>', placemark, re.IGNORECASE)
            if coord_match:
                coord_text = coord_match.group(1).strip()
                if coord_text:
                    coord_list = []
                    coords = re.split(r'[\s\n\t]+', coord_text)
                    for coord in coords:
                        coord = coord.strip()
                        if coord and ',' in coord:
                            try:
                                parts = coord.split(',')
                                if len(parts) >= 2:
                                    lon = float(parts[0])
                                    lat = float(parts[1])
                                    if -180 <= lon <= 180 and -90 <= lat <= 90:
                                        coord_list.append((lon, lat))
                            except:
                                continue
                    if len(coord_list) >= 3:
                        if coord_list[0] != coord_list[-1]:
                            coord_list.append(coord_list[0])
                        try:
                            polygon = Polygon(coord_list)
                            if polygon.is_valid and polygon.area > 0:
                                polygons.append(polygon)
                        except:
                            continue
        if polygons:
            return gpd.GeoDataFrame(geometry=polygons, crs='EPSG:4326')
        return None
    except Exception as e:
        st.error(f"Error en KML: {e}")
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
                    st.error("No se encontró .shp dentro del ZIP")
                    return None
                gdf = gpd.read_file(os.path.join(tmp_dir, shp_files[0]))
            elif ext == '.geojson':
                gdf = gpd.read_file(io.BytesIO(file_content))
            elif ext == '.kml':
                gdf = procesar_kml_robusto(file_content)
                if gdf is None:
                    st.error("No se pudieron extraer polígonos del KML")
                    return None
            elif ext == '.kmz':
                kmz_path = os.path.join(tmp_dir, 'temp.kmz')
                with open(kmz_path, 'wb') as f:
                    f.write(file_content)
                with zipfile.ZipFile(kmz_path, 'r') as kmz:
                    kml_files = [f for f in kmz.namelist() if f.endswith('.kml')]
                    if not kml_files:
                        st.error("No se encontró KML dentro del KMZ")
                        return None
                    kmz.extract(kml_files[0], tmp_dir)
                    with open(os.path.join(tmp_dir, kml_files[0]), 'rb') as f:
                        gdf = procesar_kml_robusto(f.read())
                if gdf is None:
                    st.error("No se pudieron extraer polígonos del KMZ")
                    return None
            else:
                st.error(f"Formato no soportado: {ext}")
                return None
        if gdf is None or len(gdf) == 0:
            st.error("No se encontraron geometrías")
            return None
        gdf = validar_y_corregir_crs(gdf)
        gdf = gdf.explode(ignore_index=True)
        gdf = gdf[gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
        if len(gdf) == 0:
            st.error("No hay polígonos válidos")
            return None
        union = gdf.unary_union
        if union.geom_type == 'MultiPolygon':
            areas = [p.area for p in union.geoms]
            main_poly = union.geoms[np.argmax(areas)]
        else:
            main_poly = union
        if not main_poly.is_valid:
            try:
                main_poly = make_valid(main_poly)
                if main_poly.geom_type == 'MultiPolygon':
                    areas = [p.area for p in main_poly.geoms]
                    main_poly = main_poly.geoms[np.argmax(areas)]
            except:
                pass
        gdf_unido = gpd.GeoDataFrame([{'geometry': main_poly, 'id_bloque': 1}], crs='EPSG:4326')
        area = calcular_superficie(gdf_unido)
        if area <= 0:
            st.error("El polígono tiene área cero o inválida")
            return None
        st.session_state.gdf_original = gdf_unido
        st.session_state.archivo_cargado = True
        st.session_state.analisis_completado = False
        st.session_state.deteccion_ejecutada = False
        st.success(f"✅ Plantación cargada: {area:.2f} ha")
        return gdf_unido
    except Exception as e:
        st.error(f"Error cargando archivo: {e}")
        return None

# ===== FUNCIONES SATELITALES (solo datos reales, sin simulación) =====
def obtener_ndvi_earthdata(gdf_dividido, fecha_inicio, fecha_fin):
    if not EARTHDATA_OK:
        st.error("Librerías earthaccess no instaladas.")
        st.stop()
    if not EARTHDATA_USERNAME or not EARTHDATA_PASSWORD:
        st.error("Credenciales Earthdata no configuradas.")
        st.stop()
    try:
        auth = earthaccess.login()
        if not auth.authenticated:
            st.error("No se pudo autenticar con Earthdata.")
            st.stop()
        bounds = gdf_dividido.total_bounds
        bbox = (bounds[0], bounds[1], bounds[2], bounds[3])
        results = earthaccess.search_data(
            short_name='MOD13Q1', version='061',
            bounding_box=bbox,
            temporal=(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')),
            count=5
        )
        if not results:
            st.error("No se encontraron escenas MOD13Q1 en el período.")
            st.stop()
        granule = results[0]
        st.info(f"Procesando NDVI: {granule['umm']['GranuleUR']}")
        temp_dir = tempfile.mkdtemp()
        try:
            downloaded = earthaccess.download(granule, local_path=temp_dir)
            if not downloaded:
                st.error("No se pudo descargar el archivo.")
                st.stop()
            hdf_files = [f for f in downloaded if f.suffix == '.hdf']
            if not hdf_files:
                st.error("No se encontró archivo HDF.")
                st.stop()
            download_path = str(hdf_files[0])
            # Verificar HTML
            if os.path.getsize(download_path) < 10240:
                with open(download_path, 'r', errors='ignore') as f:
                    if '<html' in f.read(500).lower():
                        st.error("El archivo descargado es una página HTML de error.")
                        st.stop()
            ndvi_values = []
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
                                progress_bar = st.progress(0, text="Procesando bloques NDVI...")
                                for idx, row in gdf_proj.iterrows():
                                    geom = [mapping(row.geometry)]
                                    try:
                                        out_image, _ = mask(src_ndvi, geom, crop=True, nodata=nodata)
                                        data = out_image[0]
                                        data_scaled = data.astype(np.float32) * 0.0001
                                        mask_valid = (data != nodata) & (data_scaled >= -0.2) & (data_scaled <= 1.0)
                                        data_clean = np.ma.masked_where(~mask_valid, data_scaled)
                                        mean_val = data_clean.mean()
                                        if np.ma.is_masked(mean_val) or np.isnan(mean_val):
                                            ndvi_values.append(np.nan)
                                        else:
                                            ndvi_values.append(round(float(mean_val), 3))
                                    except:
                                        ndvi_values.append(np.nan)
                                    progress_bar.progress((idx+1)/len(gdf_proj))
                                progress_bar.empty()
                                gdf_dividido['ndvi_modis'] = ndvi_values
                                st.success("✅ NDVI calculado con rasterio.")
                                return gdf_dividido
                except Exception as e:
                    st.warning(f"rasterio falló: {e}. Intentando con pyhdf...")
            if PYHDF_OK:
                try:
                    hdf = SD(download_path, SDC.READ)
                    ndvi_dataset = None
                    for name in hdf.datasets().keys():
                        if 'NDVI' in name:
                            ndvi_dataset = name
                            break
                    if ndvi_dataset is None:
                        st.error("No se encontró dataset NDVI con pyhdf.")
                        st.stop()
                    ndvi_data = hdf.select(ndvi_dataset).get()
                    ndvi_scaled = ndvi_data.astype(np.float32) * 0.0001
                    metadata = hdf.attributes().get('StructMetadata.0', '')
                    if not metadata:
                        st.error("No se encontró metadata en el HDF.")
                        st.stop()
                    import re
                    xdim_match = re.search(r'XDim\s*=\s*(\d+)', metadata, re.I)
                    ydim_match = re.search(r'YDim\s*=\s*(\d+)', metadata, re.I)
                    ul_match = re.search(r'UpperLeftPointMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)', metadata, re.I)
                    lr_match = re.search(r'LowerRightMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)', metadata, re.I)
                    if not (xdim_match and ydim_match and ul_match and lr_match):
                        st.error("No se pudo extraer geolocalización completa del HDF.")
                        st.stop()
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
                        with memfile.open(driver='GTiff', height=ydim, width=xdim, count=1,
                                          dtype=ndvi_scaled.dtype, crs=crs, transform=transform, nodata=-32768) as dst:
                            dst.write(ndvi_scaled, 1)
                        with memfile.open() as src_ndvi:
                            gdf_proj = gdf_dividido.to_crs(crs)
                            progress_bar = st.progress(0, text="Procesando bloques NDVI con pyhdf...")
                            for idx, row in gdf_proj.iterrows():
                                geom = [mapping(row.geometry)]
                                try:
                                    out_image, _ = mask(src_ndvi, geom, crop=True, nodata=-32768)
                                    data = out_image[0]
                                    mask_valid = (data != -32768) & (data >= -0.2) & (data <= 1.0)
                                    data_clean = np.ma.masked_where(~mask_valid, data)
                                    mean_val = data_clean.mean()
                                    if np.ma.is_masked(mean_val) or np.isnan(mean_val):
                                        ndvi_values.append(np.nan)
                                    else:
                                        ndvi_values.append(round(float(mean_val), 3))
                                except:
                                    ndvi_values.append(np.nan)
                                progress_bar.progress((idx+1)/len(gdf_proj))
                            progress_bar.empty()
                            gdf_dividido['ndvi_modis'] = ndvi_values
                            st.success("✅ NDVI calculado con pyhdf.")
                            return gdf_dividido
                except Exception as e:
                    st.error(f"pyhdf falló: {e}")
                    st.stop()
            else:
                st.error("No se pudo leer el archivo HDF.")
                st.stop()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        st.error(f"Error en obtención de NDVI: {e}")
        st.stop()

def obtener_ndwi_earthdata(gdf_dividido, fecha_inicio, fecha_fin):
    if not EARTHDATA_OK:
        st.error("Librerías earthaccess no instaladas.")
        st.stop()
    if not EARTHDATA_USERNAME or not EARTHDATA_PASSWORD:
        st.error("Credenciales Earthdata no configuradas.")
        st.stop()
    try:
        auth = earthaccess.login()
        if not auth.authenticated:
            st.error("No se pudo autenticar con Earthdata.")
            st.stop()
        bounds = gdf_dividido.total_bounds
        bbox = (bounds[0], bounds[1], bounds[2], bounds[3])
        results = earthaccess.search_data(
            short_name='MOD09GA', version='061',
            bounding_box=bbox,
            temporal=(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')),
            count=5
        )
        if not results:
            st.error("No se encontraron escenas MOD09GA en el período.")
            st.stop()
        granule = results[0]
        st.info(f"Procesando NDWI: {granule['umm']['GranuleUR']}")
        temp_dir = tempfile.mkdtemp()
        try:
            downloaded = earthaccess.download(granule, local_path=temp_dir)
            if not downloaded:
                st.error("No se pudo descargar el archivo.")
                st.stop()
            hdf_files = [f for f in downloaded if f.suffix == '.hdf']
            if not hdf_files:
                st.error("No se encontró archivo HDF.")
                st.stop()
            download_path = str(hdf_files[0])
            if os.path.getsize(download_path) < 10240:
                with open(download_path, 'r', errors='ignore') as f:
                    if '<html' in f.read(500).lower():
                        st.error("El archivo descargado es una página HTML de error.")
                        st.stop()
            ndwi_values = []
            if RASTERIO_OK:
                try:
                    with rasterio.open(download_path) as src:
                        subdatasets = src.subdatasets
                        nir_sub = None
                        swir_sub = None
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
                                progress_bar = st.progress(0, text="Procesando bloques NDWI...")
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
                                    except:
                                        ndwi_values.append(np.nan)
                                    progress_bar.progress((idx+1)/len(gdf_proj))
                                progress_bar.empty()
                                gdf_dividido['ndwi_modis'] = ndwi_values
                                st.success("✅ NDWI calculado con rasterio.")
                                return gdf_dividido
                except Exception as e:
                    st.warning(f"rasterio falló: {e}. Intentando con pyhdf...")
            if PYHDF_OK:
                try:
                    hdf = SD(download_path, SDC.READ)
                    nir_data = None
                    swir_data = None
                    for name in hdf.datasets().keys():
                        if 'sur_refl_b02' in name:
                            nir_data = hdf.select(name).get()
                        elif 'sur_refl_b06' in name:
                            swir_data = hdf.select(name).get()
                    if nir_data is None or swir_data is None:
                        st.error("No se encontraron bandas NIR o SWIR con pyhdf.")
                        st.stop()
                    nir = nir_data.astype(np.float32) * 0.0001
                    swir = swir_data.astype(np.float32) * 0.0001
                    metadata = hdf.attributes().get('StructMetadata.0', '')
                    if not metadata:
                        st.error("No se encontró metadata en el HDF.")
                        st.stop()
                    import re
                    xdim_match = re.search(r'XDim\s*=\s*(\d+)', metadata, re.I)
                    ydim_match = re.search(r'YDim\s*=\s*(\d+)', metadata, re.I)
                    ul_match = re.search(r'UpperLeftPointMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)', metadata, re.I)
                    lr_match = re.search(r'LowerRightMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)', metadata, re.I)
                    if not (xdim_match and ydim_match and ul_match and lr_match):
                        st.error("No se pudo extraer geolocalización completa del HDF.")
                        st.stop()
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
                            progress_bar = st.progress(0, text="Procesando bloques NDWI con pyhdf...")
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
                                except Exception as e:
                                    st.error(f"Error procesando bloque {idx+1}: {e}")
                                    st.stop()
                                progress_bar.progress((idx+1)/len(gdf_proj))
                            progress_bar.empty()
                            gdf_dividido['ndwi_modis'] = ndwi_values
                            st.success("✅ NDWI calculado con pyhdf.")
                            return gdf_dividido
                except Exception as e:
                    st.error(f"pyhdf falló: {e}")
                    st.stop()
            else:
                st.error("No se pudo leer el archivo HDF.")
                st.stop()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        st.error(f"Error en obtención de NDWI: {e}")
        st.stop()

# ===== FUNCIONES CLIMÁTICAS (se mantienen con fallback simulado) =====
def obtener_clima_openmeteo(gdf, fecha_inicio, fecha_fin):
    try:
        centroide = gdf.geometry.unary_union.centroid
        lat, lon = centroide.y, centroide.x
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": fecha_inicio.strftime("%Y-%m-%d"),
            "end_date": fecha_fin.strftime("%Y-%m-%d"),
            "daily": ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean", "precipitation_sum"],
            "timezone": "auto"
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "daily" not in data:
            raise ValueError
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
        st.warning(f"Error en Open-Meteo: {e}. Usando datos simulados.")
        return generar_datos_climaticos_simulados(gdf, fecha_inicio, fecha_fin)

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
            "start": start, "end": end,
            "format": "JSON"
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        props = data['properties']['parameter']
        radiacion = props.get('ALLSKY_SFC_SW_DWN', {})
        viento = props.get('WS2M', {})
        fechas = sorted(radiacion.keys())
        rad_diaria = [radiacion[f] for f in fechas]
        wind_diaria = [viento[f] for f in fechas]
        rad_diaria = [np.nan if r == -999 else r for r in rad_diaria]
        wind_diaria = [np.nan if w == -999 else w for w in wind_diaria]
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
        st.warning(f"Error en NASA POWER: {e}. Usando datos simulados.")
        return generar_datos_climaticos_simulados(gdf, fecha_inicio, fecha_fin)

def generar_datos_climaticos_simulados(gdf, fecha_inicio, fecha_fin):
    try:
        dias = (fecha_fin - fecha_inicio).days
        if dias <= 0:
            dias = 30
        rad_diaria = [np.random.uniform(15, 25) for _ in range(dias)]
        precip_diaria = [max(0, np.random.exponential(3) if np.random.random() > 0.7 else 0) for _ in range(dias)]
        wind_diaria = [np.random.uniform(2, 6) for _ in range(dias)]
        temp_diaria = [np.random.uniform(22, 28) for _ in range(dias)]
        return {
            'radiacion': {'promedio': round(np.mean(rad_diaria),1), 'maxima': round(max(rad_diaria),1), 'minima': round(min(rad_diaria),1), 'diaria': rad_diaria},
            'precipitacion': {'total': round(sum(precip_diaria),1), 'maxima_diaria': round(max(precip_diaria),1), 'dias_con_lluvia': sum(1 for p in precip_diaria if p>0.1), 'diaria': precip_diaria},
            'viento': {'promedio': round(np.mean(wind_diaria),1), 'maxima': round(max(wind_diaria),1), 'diaria': wind_diaria},
            'temperatura': {'promedio': round(np.mean(temp_diaria),1), 'maxima': round(max(temp_diaria),1), 'minima': round(min(temp_diaria),1), 'diaria': temp_diaria},
            'periodo': f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}",
            'fuente': 'Simulado (fallback)'
        }
    except:
        return {
            'radiacion': {'promedio': 18.0, 'maxima': 25.0, 'minima': 12.0, 'diaria': [18]*30},
            'precipitacion': {'total': 90.0, 'maxima_diaria': 15.0, 'dias_con_lluvia': 10, 'diaria': [3]*30},
            'viento': {'promedio': 3.0, 'maxima': 6.0, 'diaria': [3]*30},
            'temperatura': {'promedio': 25.0, 'maxima': 30.0, 'minima': 20.0, 'diaria': [25]*30},
            'periodo': 'Últimos 30 días',
            'fuente': 'Simulado (fallback)'
        }

def analizar_edad_plantacion(gdf_dividido):
    edades = []
    for idx, row in gdf_dividido.iterrows():
        try:
            centroid = row.geometry.centroid
            lat_norm = (centroid.y + 90) / 180
            lon_norm = (centroid.x + 180) / 360
            edad = 2 + (lat_norm * lon_norm * 18)
            edades.append(round(edad, 1))
        except:
            edades.append(10.0)
    return edades

# ===== DETECCIÓN DE PLANTAS =====
def verificar_puntos_en_poligono(puntos, gdf):
    puntos_dentro = []
    plantacion_union = gdf.unary_union
    for punto in puntos:
        if 'centroide' in punto:
            lon, lat = punto['centroide']
            point = Point(lon, lat)
            if plantacion_union.contains(point):
                puntos_dentro.append(punto)
    return puntos_dentro

def mejorar_deteccion_plantas(gdf, densidad=130):
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
        x_coords = []
        y_coords = []
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
                plantas.append({
                    'centroide': (lon, lat),
                    'area_m2': np.random.uniform(18, 24),
                    'circularidad': np.random.uniform(0.85, 0.98),
                    'diametro_aprox': np.random.uniform(5, 7),
                    'simulado': True
                })
        return {'detectadas': plantas, 'total': len(plantas), 'patron': 'hexagonal adaptativo', 'densidad_calculada': len(plantas)/area_ha, 'area_ha': area_ha}
    except Exception as e:
        print(f"Error en detección: {e}")
        return {'detectadas': [], 'total': 0}

def ejecutar_deteccion_plantas():
    if st.session_state.gdf_original is None:
        st.error("Primero debe cargar un archivo")
        return
    with st.spinner("Detectando plantas..."):
        gdf = st.session_state.gdf_original
        densidad = st.session_state.get('densidad_personalizada', 130)
        resultados = mejorar_deteccion_plantas(gdf, densidad)
        plantas_verificadas = verificar_puntos_en_poligono(resultados['detectadas'], gdf)
        st.session_state.plantas_detectadas = plantas_verificadas
        st.session_state.deteccion_ejecutada = True
        st.success(f"✅ {len(plantas_verificadas)} plantas detectadas")

def crear_graficos_climaticos_completos(datos_climaticos):
    longitudes = []
    for key in ['precipitacion', 'temperatura', 'radiacion', 'viento']:
        if key in datos_climaticos and 'diaria' in datos_climaticos[key]:
            longitudes.append(len(datos_climaticos[key]['diaria']))
    if not longitudes:
        return None
    n_dias = min(longitudes)
    dias = list(range(1, n_dias+1))
    fig, axes = plt.subplots(2,2, figsize=(15,10))
    if 'radiacion' in datos_climaticos and datos_climaticos['radiacion'].get('diaria'):
        rad = np.array(datos_climaticos['radiacion']['diaria'][:n_dias], dtype=np.float64)
        rad_filled = np.where(np.isnan(rad), np.nanmean(rad), rad)
        ax = axes[0,0]
        ax.plot(dias, rad_filled, 'o-', color='orange')
        ax.fill_between(dias, rad_filled, alpha=0.3, color='orange')
        ax.axhline(y=datos_climaticos['radiacion']['promedio'], color='red', linestyle='--', label=f"Prom: {datos_climaticos['radiacion']['promedio']} MJ/m²")
        ax.set_xlabel('Día'); ax.set_ylabel('Radiación (MJ/m²/día)'); ax.set_title('Radiación Solar'); ax.legend(); ax.grid(True, alpha=0.3)
    else:
        axes[0,0].text(0.5,0.5,"No disponible", ha='center', va='center')
    if 'precipitacion' in datos_climaticos and datos_climaticos['precipitacion'].get('diaria'):
        precip = np.array(datos_climaticos['precipitacion']['diaria'][:n_dias], dtype=np.float64)
        ax = axes[0,1]
        ax.bar(dias, precip, color='blue', alpha=0.7)
        ax.set_xlabel('Día'); ax.set_ylabel('Precipitación (mm)'); ax.set_title(f"Precipitación (Total: {datos_climaticos['precipitacion']['total']:.1f} mm)"); ax.grid(True, alpha=0.3, axis='y')
    else:
        axes[0,1].text(0.5,0.5,"No disponible", ha='center', va='center')
    if 'viento' in datos_climaticos and datos_climaticos['viento'].get('diaria'):
        wind = np.array(datos_climaticos['viento']['diaria'][:n_dias], dtype=np.float64)
        wind_filled = np.where(np.isnan(wind), np.nanmean(wind), wind)
        ax = axes[1,0]
        ax.plot(dias, wind_filled, 's-', color='green')
        ax.fill_between(dias, wind_filled, alpha=0.3, color='green')
        ax.axhline(y=datos_climaticos['viento']['promedio'], color='red', linestyle='--', label=f"Prom: {datos_climaticos['viento']['promedio']} m/s")
        ax.set_xlabel('Día'); ax.set_ylabel('Viento (m/s)'); ax.set_title('Velocidad del Viento'); ax.legend(); ax.grid(True, alpha=0.3)
    else:
        axes[1,0].text(0.5,0.5,"No disponible", ha='center', va='center')
    if 'temperatura' in datos_climaticos and datos_climaticos['temperatura'].get('diaria'):
        temp = np.array(datos_climaticos['temperatura']['diaria'][:n_dias], dtype=np.float64)
        temp_filled = np.where(np.isnan(temp), np.nanmean(temp), temp)
        ax = axes[1,1]
        ax.plot(dias, temp_filled, '^-', color='red')
        ax.fill_between(dias, temp_filled, alpha=0.3, color='red')
        ax.axhline(y=datos_climaticos['temperatura']['promedio'], color='blue', linestyle='--', label=f"Prom: {datos_climaticos['temperatura']['promedio']}°C")
        ax.set_xlabel('Día'); ax.set_ylabel('Temperatura (°C)'); ax.set_title('Temperatura Diaria'); ax.legend(); ax.grid(True, alpha=0.3)
    else:
        axes[1,1].text(0.5,0.5,"No disponible", ha='center', va='center')
    plt.suptitle(f"Datos Climáticos - {datos_climaticos.get('fuente','Desconocido')}", fontsize=16, y=1.02)
    plt.tight_layout()
    return fig

# ===== ANÁLISIS DE TEXTURA DE SUELO =====
def analizar_textura_suelo_venezuela_por_bloque(gdf_dividido):
    resultados = []
    try:
        centroide_global = gdf_dividido.geometry.unary_union.centroid
        lat_base = centroide_global.y
        if lat_base > 10:
            base, alt_base = 'Franco Arcilloso', 'Arcilloso'
        elif lat_base > 7:
            base, alt_base = 'Franco Arcilloso Arenoso', 'Franco'
        elif lat_base > 4:
            base, alt_base = 'Arenoso Franco', 'Arenoso'
        else:
            base, alt_base = 'Franco Arcilloso', 'Arcilloso Pesado'
        caracteristicas = {
            'Franco Arcilloso': {'arena':35,'limo':25,'arcilla':30,'textura':'Media','drenaje':'Moderado','CIC':'Alto (15-25)','ret_agua':'Alta','recomendacion':'Ideal para vid/olivo'},
            'Franco Arcilloso Arenoso': {'arena':45,'limo':20,'arcilla':25,'textura':'Media-ligera','drenaje':'Bueno','CIC':'Medio (10-15)','ret_agua':'Moderada','recomendacion':'Requiere riego'},
            'Arenoso Franco': {'arena':55,'limo':15,'arcilla':20,'textura':'Ligera','drenaje':'Excelente','CIC':'Bajo (5-10)','ret_agua':'Baja','recomendacion':'Fertilización fraccionada'},
            'Arcilloso': {'arena':25,'limo':20,'arcilla':40,'textura':'Pesada','drenaje':'Limitado','CIC':'Muy alto (25-35)','ret_agua':'Muy alta','recomendacion':'Drenaje y labranza'},
            'Arcilloso Pesado': {'arena':20,'limo':15,'arcilla':50,'textura':'Muy pesada','drenaje':'Muy limitado','CIC':'Extremo (>35)','ret_agua':'Extrema','recomendacion':'Drenaje intensivo'},
            'Franco': {'arena':40,'limo':40,'arcilla':20,'textura':'Media','drenaje':'Bueno','CIC':'Medio (10-20)','ret_agua':'Media','recomendacion':'Manejo estándar'},
            'Arenoso': {'arena':70,'limo':15,'arcilla':15,'textura':'Ligera','drenaje':'Excelente','CIC':'Muy bajo (<5)','ret_agua':'Muy baja','recomendacion':'Riego frecuente'}
        }
        for idx, row in gdf_dividido.iterrows():
            centroid = row.geometry.centroid
            semilla = abs(int(centroid.x*1000 + centroid.y*1000)) % (2**32)
            np.random.seed(semilla)
            tipo = base if np.random.random() < 0.7 else alt_base
            carac = caracteristicas.get(tipo, caracteristicas['Franco Arcilloso'])
            arena = carac['arena'] + np.random.randint(-5,6)
            limo = carac['limo'] + np.random.randint(-5,6)
            arcilla = carac['arcilla'] + np.random.randint(-5,6)
            total = arena + limo + arcilla
            arena = int(arena/total*100)
            limo = int(limo/total*100)
            arcilla = 100 - arena - limo
            resultados.append({
                'id_bloque': row.get('id_bloque', idx+1),
                'tipo_suelo': tipo,
                'arena': arena, 'limo': limo, 'arcilla': arcilla,
                'textura': carac['textura'], 'drenaje': carac['drenaje'],
                'CIC': carac['CIC'], 'ret_agua': carac['ret_agua'],
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
                N, P, K, pH, MO = np.random.uniform(120,180), np.random.uniform(40,70), np.random.uniform(180,250), np.random.uniform(5.8,6.5), np.random.uniform(3.5,5.0)
            elif ndvi > 0.6:
                N, P, K, pH, MO = np.random.uniform(80,120), np.random.uniform(25,40), np.random.uniform(120,180), np.random.uniform(5.2,5.8), np.random.uniform(2.5,3.5)
            else:
                N, P, K, pH, MO = np.random.uniform(40,80), np.random.uniform(15,25), np.random.uniform(80,120), np.random.uniform(4.8,5.2), np.random.uniform(1.5,2.5)
            rec_N = f"Aplicar {max(0,120-N):.0f} kg/ha N (Urea: {max(0,(120-N)/0.46):.0f} kg/ha)" if N<100 else "Mantener dosis actual"
            rec_P = f"Aplicar {max(0,50-P):.0f} kg/ha P2O5 (DAP: {max(0,(50-P)/0.46):.0f} kg/ha)" if P<30 else "Mantener dosis actual"
            rec_K = f"Aplicar {max(0,200-K):.0f} kg/ha K2O (KCl: {max(0,(200-K)/0.6):.0f} kg/ha)" if K<150 else "Mantener dosis actual"
            fertilidad_data.append({
                'id_bloque': row.get('id_bloque', idx+1),
                'N_kg_ha': round(N,1), 'P_kg_ha': round(P,1), 'K_kg_ha': round(K,1),
                'pH': round(pH,2), 'MO_porcentaje': round(MO,2),
                'recomendacion_N': rec_N, 'recomendacion_P': rec_P, 'recomendacion_K': rec_K,
                'geometria': row.geometry
            })
        return fertilidad_data
    except:
        return []

# ===== FUNCIONES DE VISUALIZACIÓN SIMPLIFICADAS =====
def crear_mapa_interactivo_base(gdf, columna_color=None, colormap=None, tooltip_fields=None, tooltip_aliases=None):
    if gdf is None or len(gdf)==0:
        return None
    centroide = gdf.geometry.unary_union.centroid
    m = folium.Map(location=[centroide.y, centroide.x], zoom_start=16, tiles=None, control_scale=True)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite Esri').add_to(m)
    folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attr='OpenStreetMap', name='OpenStreetMap').add_to(m)
    if columna_color and colormap:
        def style_function(feature):
            valor = feature['properties'].get(columna_color, 0)
            if valor is None or (isinstance(valor, float) and np.isnan(valor)):
                valor = 0
            try:
                color = colormap(float(valor))
            except:
                color = '#3388ff'
            return {'fillColor': color, 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.7}
    else:
        def style_function(feature):
            return {'fillColor': '#3388ff', 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.4}
    tooltip = folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True) if tooltip_fields and tooltip_aliases else None
    folium.GeoJson(gdf.to_json(), name='Polígonos', style_function=style_function, tooltip=tooltip).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    Fullscreen().add_to(m)
    MeasureControl().add_to(m)
    MiniMap(toggle_display=True).add_to(m)
    return m

def mostrar_estadisticas_indice(gdf, columna, titulo, vmin, vmax, colormap_list):
    if columna not in gdf.columns:
        st.error(f"Columna {columna} no disponible")
        return
    valores = gdf[columna].dropna()
    if len(valores)==0:
        st.warning(f"No hay datos para {titulo}")
        return
    colormap = LinearColormap(colors=colormap_list, vmin=vmin, vmax=vmax, caption=titulo)
    mapa = crear_mapa_interactivo_base(gdf, columna_color=columna, colormap=colormap,
                                       tooltip_fields=['id_bloque', columna], tooltip_aliases=['Bloque', titulo])
    if mapa:
        colormap.add_to(mapa)
        folium_static(mapa, width=1000, height=600)
    else:
        fig, ax = plt.subplots(figsize=(10,4))
        ax.bar(range(len(gdf)), gdf[columna].values, color='steelblue')
        ax.set_xlabel('Bloque'); ax.set_ylabel(titulo); ax.set_title(f'{titulo} por bloque')
        st.pyplot(fig)
        plt.close(fig)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.metric("Media", f"{valores.mean():.3f}")
    with col2: st.metric("Mediana", f"{valores.median():.3f}")
    with col3: st.metric("Desv. estándar", f"{valores.std():.3f}")
    with col4: st.metric("Mínimo", f"{valores.min():.3f}")
    with col5: st.metric("Máximo", f"{valores.max():.3f}")
    df_tabla = gdf[['id_bloque', columna]].copy().rename(columns={'id_bloque':'Bloque', columna:titulo})
    st.dataframe(df_tabla.style.format({titulo:'{:.3f}'}), use_container_width=True)

def mostrar_comparacion_ndvi_ndwi(gdf):
    if gdf is None or len(gdf)==0:
        return
    df = gdf[['id_bloque','ndvi_modis','ndwi_modis','salud','area_ha']].dropna()
    if len(df)==0:
        return
    try:
        import statsmodels.api as sm
        statsmodels_ok = True
    except:
        statsmodels_ok = False
    fig = px.scatter(df, x='ndvi_modis', y='ndwi_modis', color='salud', size='area_ha', hover_data=['id_bloque'],
                     labels={'ndvi_modis':'NDVI','ndwi_modis':'NDWI','salud':'Salud'},
                     title='Relación NDVI vs NDWI',
                     color_discrete_map={'Crítica':'#d73027','Baja':'#fee08b','Moderada':'#91cf60','Buena':'#1a9850'},
                     trendline='ols' if statsmodels_ok else None, trendline_color_override='gray')
    fig.update_traces(marker=dict(line=dict(width=1,color='DarkSlateGrey')))
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Top 5 NDVI")
        st.dataframe(df.nlargest(5,'ndvi_modis')[['id_bloque','ndvi_modis','salud']].rename(columns={'id_bloque':'Bloque','ndvi_modis':'NDVI'}).style.format({'NDVI':'{:.3f}'}), use_container_width=True)
        st.markdown("#### Bottom 5 NDVI")
        st.dataframe(df.nsmallest(5,'ndvi_modis')[['id_bloque','ndvi_modis','salud']].rename(columns={'id_bloque':'Bloque','ndvi_modis':'NDVI'}).style.format({'NDVI':'{:.3f}'}), use_container_width=True)
    with col2:
        st.markdown("#### Top 5 NDWI")
        st.dataframe(df.nlargest(5,'ndwi_modis')[['id_bloque','ndwi_modis','salud']].rename(columns={'id_bloque':'Bloque','ndwi_modis':'NDWI'}).style.format({'NDWI':'{:.3f}'}), use_container_width=True)
        st.markdown("#### Bottom 5 NDWI")
        st.dataframe(df.nsmallest(5,'ndwi_modis')[['id_bloque','ndwi_modis','salud']].rename(columns={'id_bloque':'Bloque','ndwi_modis':'NDWI'}).style.format({'NDWI':'{:.3f}'}), use_container_width=True)

def crear_mapa_fertilidad_interactivo(gdf_fertilidad, variable):
    info_var = {
        'N_kg_ha': {'titulo':'Nitrógeno (N)','unidad':'kg/ha','vmin':40,'vmax':180,'cmap':'YlGnBu'},
        'P_kg_ha': {'titulo':'Fósforo (P₂O₅)','unidad':'kg/ha','vmin':15,'vmax':70,'cmap':'YlOrRd'},
        'K_kg_ha': {'titulo':'Potasio (K₂O)','unidad':'kg/ha','vmin':80,'vmax':250,'cmap':'YlGn'},
        'pH': {'titulo':'pH del suelo','unidad':'','vmin':4.5,'vmax':6.5,'cmap':'RdYlGn_r'},
        'MO_porcentaje': {'titulo':'Materia Orgánica','unidad':'%','vmin':1.0,'vmax':5.0,'cmap':'BrBG'}
    }
    info = info_var.get(variable, {'titulo':variable,'unidad':'','vmin':None,'vmax':None,'cmap':'YlOrRd'})
    colormap = LinearColormap(
        colors=['#ffffb2','#fecc5c','#fd8d3c','#f03b20','#bd0026'] if info['cmap']=='YlOrRd' else
                ['#c7e9c0','#74c476','#31a354','#006d2c'] if info['cmap']=='YlGn' else
                ['#4575b4','#91bfdb','#e0f3f8','#fee090','#fc8d59','#d73027'] if info['cmap']=='RdYlGn_r' else
                ['#8c510a','#bf812d','#dfc27d','#f6e8c3','#c7eae5','#80cdc1','#35978f','#01665e'],
        vmin=info['vmin'] if info['vmin'] else gdf_fertilidad[variable].min(),
        vmax=info['vmax'] if info['vmax'] else gdf_fertilidad[variable].max(),
        caption=f"{info['titulo']} ({info['unidad']})"
    )
    m = crear_mapa_interactivo_base(gdf_fertilidad, columna_color=variable, colormap=colormap,
                                    tooltip_fields=['id_bloque', variable, 'recomendacion_N','recomendacion_P','recomendacion_K'],
                                    tooltip_aliases=['Bloque', f"{info['titulo']} ({info['unidad']})", 'Recom. N', 'Recom. P', 'Recom. K'])
    if m:
        colormap.add_to(m)
    return m

def crear_grafico_textural(arena, limo, arcilla, tipo_suelo):
    fig = go.Figure(go.Scatterternary(a=[arcilla], b=[limo], c=[arena], mode='markers+text',
                                      marker=dict(size=14, color='red'), text=[tipo_suelo], textposition='top center'))
    fig.update_layout(title='Triángulo Textural', ternary=dict(sum=100, aaxis=dict(title='% Arcilla'), baxis=dict(title='% Limo'), caxis=dict(title='% Arena')), height=500)
    return fig

# ===== FUNCIONES YOLO =====
def cargar_modelo_yolo(ruta_modelo):
    if not YOLO_AVAILABLE:
        st.error("Ultralytics no instalado")
        return None
    try:
        return YOLO(ruta_modelo)
    except Exception as e:
        st.error(f"Error cargando modelo: {e}")
        return None

def detectar_en_imagen(modelo, imagen_cv, conf_threshold=0.25):
    if modelo is None or not CV2_AVAILABLE:
        return None
    try:
        return modelo(imagen_cv, conf=conf_threshold)
    except Exception as e:
        st.error(f"Error en inferencia: {e}")
        return None

def dibujar_detecciones_con_leyenda(imagen_cv, resultados):
    if resultados is None or len(resultados)==0 or not CV2_AVAILABLE:
        return imagen_cv, []
    img_anotada = imagen_cv.copy()
    detecciones_info = []
    names = resultados[0].names
    for r in resultados:
        for box in r.boxes:
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = names[cls_id]
            color = tuple(np.random.randint(0,255,3).tolist())
            cv2.rectangle(img_anotada, (x1,y1), (x2,y2), color, 3)
            etiqueta = f"{label} {conf:.2f}"
            (w,h), _ = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img_anotada, (x1, y1-h-10), (x1+w, y1), color, -1)
            cv2.putText(img_anotada, etiqueta, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            detecciones_info.append({'clase':label, 'confianza':round(conf,3), 'bbox':[x1,y1,x2,y2], 'color':color})
    return img_anotada, detecciones_info

def crear_leyenda_html(detecciones_info):
    if not detecciones_info:
        return "<p>No se detectaron objetos.</p>"
    from collections import Counter
    clases_vistas = {d['clase']: d['color'] for d in detecciones_info}
    conteo = Counter([d['clase'] for d in detecciones_info])
    html = "<div style='background:rgba(30,30,30,0.9); padding:15px; border-radius:10px; margin-top:20px;'>"
    html += "<h4 style='color:white; margin-bottom:10px;'>📋 Leyenda</h4><table style='width:100%; color:white; border-collapse:collapse;'><tr><th>Color</th><th>Clase</th><th>Conteo</th></tr>"
    for clase, color in clases_vistas.items():
        color_hex = '#{:02x}{:02x}{:02x}'.format(color[0],color[1],color[2])
        html += f"<tr><td style='padding:8px;'><span style='display:inline-block; width:20px; height:20px; background-color:{color_hex}; border-radius:4px;'></span></td><td>{clase}</td><td style='text-align:center;'>{conteo[clase]}</td></tr>"
    html += "</table></div>"
    return html

# ===== CURVAS DE NIVEL =====
def obtener_dem_opentopography(gdf, api_key=None):
    try:
        import rasterio
        from rasterio.mask import mask
    except:
        st.warning("Para curvas reales instala rasterio y scikit-image")
        return None, None, None
    if api_key is None:
        api_key = os.environ.get("OPENTOPOGRAPHY_API_KEY")
    if not api_key:
        return None, None, None
    try:
        bounds = gdf.total_bounds
        west, south, east, north = bounds
        lon_span = east - west
        lat_span = north - south
        west -= lon_span*0.05
        east += lon_span*0.05
        south -= lat_span*0.05
        north += lat_span*0.05
        url = "https://portal.opentopography.org/API/globaldem"
        params = {"demtype":"SRTMGL1", "south":south, "north":north, "west":west, "east":east, "outputFormat":"GTiff", "API_Key":api_key}
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        dem_bytes = BytesIO(response.content)
        with rasterio.open(dem_bytes) as src:
            geom = [mapping(gdf.unary_union)]
            out_image, out_transform = mask(src, geom, crop=True, nodata=-32768)
            return out_image.squeeze(), src.meta, out_transform
    except Exception as e:
        st.error(f"Error descargando DEM: {e}")
        return None, None, None

def generar_curvas_nivel_simuladas(gdf):
    try:
        from skimage import measure
    except:
        return []
    bounds = gdf.total_bounds
    minx, miny, maxx, maxy = bounds
    n = 100
    x = np.linspace(minx, maxx, n)
    y = np.linspace(miny, maxy, n)
    X, Y = np.meshgrid(x, y)
    np.random.seed(42)
    Z = np.random.randn(n,n)*20
    from scipy.ndimage import gaussian_filter
    Z = gaussian_filter(Z, sigma=5)
    Z = 50 + (Z-Z.min())/(Z.max()-Z.min())*150
    contours = []
    niveles = np.arange(50,200,10)
    for nivel in niveles:
        try:
            for contour in measure.find_contours(Z, nivel):
                coords = [(minx + col/n*(maxx-minx), miny + row/n*(maxy-miny)) for row,col in contour]
                if len(coords)>2:
                    line = LineString(coords)
                    if line.length>0.01:
                        contours.append((line, nivel))
        except:
            continue
    return contours

def generar_curvas_nivel_reales(dem_array, transform, intervalo=10):
    try:
        from skimage import measure
    except:
        return []
    if dem_array is None:
        return []
    dem_array = np.ma.masked_where(dem_array <= -999, dem_array)
    vmin, vmax = dem_array.min(), dem_array.max()
    if vmin is np.ma.masked or vmax is np.ma.masked:
        return []
    niveles = np.arange(np.floor(vmin/intervalo)*intervalo, np.ceil(vmax/intervalo)*intervalo+intervalo, intervalo)
    contours = []
    for nivel in niveles:
        try:
            for contour in measure.find_contours(dem_array.filled(-999), nivel):
                coords = [transform*(col,row) for row,col in contour]
                if len(coords)>2:
                    line = LineString(coords)
                    if line.length>0.01:
                        contours.append((line, nivel))
        except:
            continue
    return contours

def mapa_curvas_coloreadas(gdf_original, curvas_con_elevacion):
    centroide = gdf_original.geometry.unary_union.centroid
    m = folium.Map(location=[centroide.y, centroide.x], zoom_start=15, tiles=None)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
    folium.TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attr='OSM', name='OpenStreetMap').add_to(m)
    folium.GeoJson(gdf_original.to_json(), name='Plantación', style_function=lambda x: {'color':'blue','fillOpacity':0.1,'weight':2}).add_to(m)
    elevaciones = [e for _,e in curvas_con_elevacion]
    if elevaciones:
        colormap = LinearColormap(colors=['green','yellow','orange','brown'], vmin=min(elevaciones), vmax=max(elevaciones), caption='Elevación (m)')
        colormap.add_to(m)
        for line, elev in curvas_con_elevacion:
            folium.GeoJson(gpd.GeoSeries(line).to_json(), style_function=lambda x, e=elev: {'color':colormap(e), 'weight':1.5, 'opacity':0.9},
                           tooltip=f'Elevación: {elev:.0f} m').add_to(m)
    folium.LayerControl().add_to(m)
    Fullscreen().add_to(m)
    return m

# ===== FUNCIÓN PRINCIPAL DE ANÁLISIS =====
def ejecutar_analisis_completo():
    if st.session_state.gdf_original is None:
        st.error("Primero debe cargar un archivo")
        return
    with st.spinner("Ejecutando análisis..."):
        n_divisiones = st.session_state.n_divisiones
        fecha_inicio = st.session_state.fecha_inicio
        fecha_fin = st.session_state.fecha_fin
        gdf = st.session_state.gdf_original.copy()

        if st.session_state.demo_mode:
            st.info("🎮 Modo DEMO activo: usando datos simulados.")
            gdf_dividido = generar_datos_simulados_completos(gdf, n_divisiones)
            st.session_state.datos_climaticos = generar_clima_simulado()
            st.session_state.datos_modis = {
                'ndvi': gdf_dividido['ndvi_modis'].mean(),
                'ndwi': gdf_dividido['ndwi_modis'].mean(),
                'fecha': fecha_inicio.strftime('%Y-%m-%d'),
                'fuente': 'Datos simulados (DEMO)'
            }
        else:
            # Modo PREMIUM: datos reales
            gdf_dividido = dividir_plantacion_en_bloques(gdf, n_divisiones)
            areas_ha = []
            for idx, row in gdf_dividido.iterrows():
                area_gdf = gpd.GeoDataFrame({'geometry':[row.geometry]}, crs=gdf_dividido.crs)
                areas_ha.append(float(calcular_superficie(area_gdf)))
            gdf_dividido['area_ha'] = areas_ha

            # NDVI real
            st.info("🛰️ Obteniendo NDVI desde Earthdata (MOD13Q1)...")
            gdf_dividido = obtener_ndvi_earthdata(gdf_dividido, fecha_inicio, fecha_fin)
            fuente_ndvi = "Earthdata MOD13Q1"

            # NDWI real
            st.info("💧 Obteniendo NDWI desde Earthdata (MOD09GA)...")
            gdf_dividido = obtener_ndwi_earthdata(gdf_dividido, fecha_inicio, fecha_fin)
            fuente_ndwi = "Earthdata MOD09GA"

            # Clima
            st.info("🌦️ Obteniendo datos climáticos...")
            datos_clima = obtener_clima_openmeteo(gdf, fecha_inicio, fecha_fin) or {}
            datos_power = obtener_radiacion_viento_power(gdf, fecha_inicio, fecha_fin) or {}
            st.session_state.datos_climaticos = {**datos_clima, **datos_power}

            # Edad simulada
            edades = analizar_edad_plantacion(gdf_dividido)
            gdf_dividido['edad_anios'] = edades

            st.session_state.datos_modis = {
                'ndvi': gdf_dividido['ndvi_modis'].mean(),
                'ndwi': gdf_dividido['ndwi_modis'].mean(),
                'fecha': fecha_inicio.strftime('%Y-%m-%d'),
                'fuente': f"NDVI: {fuente_ndvi}, NDWI: {fuente_ndwi}"
            }

        # Clasificar salud
        def clasificar_salud(ndvi):
            if ndvi < 0.4: return 'Crítica'
            if ndvi < 0.6: return 'Baja'
            if ndvi < 0.75: return 'Moderada'
            return 'Buena'
        gdf_dividido['salud'] = gdf_dividido['ndvi_modis'].apply(clasificar_salud)

        # Análisis de suelo
        if st.session_state.get('analisis_suelo', True):
            st.session_state.textura_por_bloque = analizar_textura_suelo_venezuela_por_bloque(gdf_dividido)
            if st.session_state.textura_por_bloque:
                st.session_state.textura_suelo = st.session_state.textura_por_bloque[0]

        st.session_state.datos_fertilidad = generar_mapa_fertilidad(gdf_dividido)

        st.session_state.resultados_todos = {
            'exitoso': True,
            'gdf_completo': gdf_dividido,
            'area_total': calcular_superficie(gdf)
        }
        st.session_state.analisis_completado = True
        st.success("✅ Análisis completado!")

# ===== ADVERTENCIAS DE LIBRERÍAS =====
if not EARTHDATA_OK:
    st.warning("⚠️ Para datos satelitales reales instala: pip install earthaccess xarray rioxarray")
if not RASTERIO_OK and not PYHDF_OK:
    st.warning("⚠️ rasterio y pyhdf no instalados. No se podrán leer archivos HDF4.")

# ===== ESTILOS Y CABECERA =====
st.markdown("""
<style>
/* Ocultar elementos de Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp [data-testid="stToolbar"] {display: none;}
.stAppDeployButton {display: none;}
.hero-banner { background: linear-gradient(145deg, rgba(15,23,42,0.95), rgba(30,41,59,0.98)); padding:1.5em; border-radius:15px; margin-bottom:1em; border:1px solid rgba(76,175,80,0.3); text-align:center; }
.hero-title { color:#fff; font-size:2em; font-weight:800; background: linear-gradient(135deg, #fff 0%, #81c784 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.stButton > button { background: linear-gradient(135deg, #4caf50 0%, #2e7d32 100%) !important; color:white !important; border:none !important; padding:0.8em 1.5em !important; border-radius:12px !important; font-weight:700 !important; }
.stTabs [data-baseweb="tab-list"] { background:rgba(30,41,59,0.7); backdrop-filter:blur(10px); padding:8px 16px; border-radius:16px; border:1px solid rgba(76,175,80,0.3); margin-top:1.5em; }
div[data-testid="metric-container"] { background:linear-gradient(135deg,rgba(30,41,59,0.9),rgba(15,23,42,0.95)); backdrop-filter:blur(10px); border-radius:18px; padding:22px; box-shadow:0 6px 20px rgba(0,0,0,0.35); border:1px solid rgba(76,175,80,0.25); }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-banner">
    <h1 class="hero-title">🍇 ANALIZADOR DE VID Y OLIVO SATELITAL</h1>
    <p style="color:#cbd5e1; font-size:1.2em;">Monitoreo biológico con datos reales NASA Earthdata · Open-Meteo · NASA POWER</p>
</div>
""", unsafe_allow_html=True)

# ===== SIDEBAR =====
with st.sidebar:
    st.markdown("## 🍇 CONFIGURACIÓN")
    crop_type = st.radio("Cultivo", ["Vid", "Olivo"], horizontal=True, key="crop_selector")
    st.session_state.crop_type = crop_type
    if crop_type == "Vid":
        variedad = st.selectbox("Variedad de Vid:", VARIEDADES_VID, index=0)
    else:
        variedad = st.selectbox("Variedad de Olivo:", VARIEDADES_OLIVO, index=0)
    st.session_state.variedad_seleccionada = f"{crop_type} - {variedad}"
    st.markdown("---")
    st.markdown("### 📅 Rango Temporal")
    fecha_fin = st.date_input("Fecha fin", datetime.now())
    fecha_inicio = st.date_input("Fecha inicio", datetime.now() - timedelta(days=60))
    if hasattr(fecha_inicio,'year'): fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
    if hasattr(fecha_fin,'year'): fecha_fin = datetime.combine(fecha_fin, datetime.min.time())
    st.session_state.fecha_inicio = fecha_inicio
    st.session_state.fecha_fin = fecha_fin
    st.markdown("---")
    st.markdown("### 🎯 División de Plantación")
    n_divisiones = st.slider("Número de bloques:", 8, 32, 16)
    st.session_state.n_divisiones = n_divisiones
    st.markdown("---")
    st.markdown("### 🌱 Detección de Plantas")
    deteccion_habilitada = st.checkbox("Activar detección", value=True)
    if deteccion_habilitada:
        densidad = st.slider("Densidad (plantas/ha):", 50, 200, 130)
        st.session_state.densidad_personalizada = densidad
    st.markdown("---")
    st.markdown("### 🧪 Análisis de Suelo")
    analisis_suelo = st.checkbox("Activar análisis de suelo", value=True)
    st.session_state.analisis_suelo = analisis_suelo
    st.markdown("---")
    st.markdown("### 📤 Subir Polígono")
    uploaded_file = st.file_uploader("Subir archivo", type=['zip','kml','kmz','geojson'], key="polygon_uploader")
    if uploaded_file is not None:
        st.info(f"📄 {uploaded_file.name} ({uploaded_file.size/1024:.1f} KB)")
        if st.button("🔄 Cargar Polígono"):
            with st.spinner("Procesando..."):
                gdf = cargar_archivo_plantacion(uploaded_file)
                if gdf is not None:
                    st.rerun()
    if st.session_state.get('archivo_cargado', False):
        st.success("✅ Polígono cargado")
        if st.session_state.gdf_original is not None:
            area = calcular_superficie(st.session_state.gdf_original)
            st.metric("Área", f"{area:.2f} ha")
    with st.expander("🔧 Debug"):
        st.write("Keys:", list(st.session_state.keys()))
        if st.session_state.gdf_original is not None:
            st.write("CRS:", st.session_state.gdf_original.crs)

# ===== ÁREA PRINCIPAL =====
if st.session_state.archivo_cargado and st.session_state.gdf_original is not None:
    gdf = st.session_state.gdf_original
    area_total = calcular_superficie(gdf)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 INFORMACIÓN")
        st.write(f"- **Área total:** {area_total:.1f} ha")
        st.write(f"- **Cultivo:** {st.session_state.crop_type}")
        st.write(f"- **Variedad:** {st.session_state.variedad_seleccionada.split(' - ')[1]}")
        st.write(f"- **Bloques:** {st.session_state.n_divisiones}")
        try:
            m_preview = folium.Map(location=[gdf.geometry.centroid.y.iloc[0], gdf.geometry.centroid.x.iloc[0]], zoom_start=15)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m_preview)
            folium.GeoJson(gdf.to_json(), style_function=lambda x: {'fillColor':'#3388ff','color':'black','weight':2,'fillOpacity':0.4}).add_to(m_preview)
            folium.LayerControl().add_to(m_preview)
            folium_static(m_preview, width=500, height=300)
        except Exception as e:
            st.warning(f"Error en mapa: {e}")
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
    st.info("👆 Sube un archivo de plantación en la barra lateral para comenzar.")
    if st.session_state.demo_mode:
        st.info("🎮 Modo DEMO: sube tu propio archivo para análisis con datos simulados.")

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
            pct_buena = (salud_counts.get('Buena',0)/total_bloques*100) if total_bloques>0 else 0
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
                    colors_pie = {'Crítica':'#d73027','Baja':'#fee08b','Moderada':'#91cf60','Buena':'#1a9850'}
                    pie_colors = [colors_pie.get(c,'#ccc') for c in salud_counts.index]
                    ax_pie.pie(salud_counts.values, labels=salud_counts.index, autopct='%1.1f%%', colors=pie_colors, startangle=90)
                    ax_pie.set_title("Clasificación de salud")
                    st.pyplot(fig_pie)
                    plt.close(fig_pie)
                else:
                    st.info("Sin datos")
            with col_g2:
                st.markdown("#### 📊 Histograma NDVI y Edad")
                if 'ndvi_modis' in gdf_completo.columns and 'edad_anios' in gdf_completo.columns:
                    fig_hist, ax_hist = plt.subplots(figsize=(5,3))
                    ax_hist.hist(gdf_completo['ndvi_modis'].dropna(), bins=15, alpha=0.7, label='NDVI', color='green')
                    ax_hist.set_xlabel('NDVI')
                    ax_hist.set_ylabel('Frecuencia', color='green')
                    ax2 = ax_hist.twinx()
                    ax2.hist(gdf_completo['edad_anios'].dropna(), bins=15, alpha=0.5, label='Edad', color='orange')
                    ax2.set_ylabel('Frecuencia (Edad)', color='orange')
                    ax_hist.set_title('Distribución NDVI y Edad')
                    fig_hist.tight_layout()
                    st.pyplot(fig_hist)
                    plt.close(fig_hist)
                else:
                    st.info("Datos insuficientes")
            st.markdown("---")
            st.markdown("#### 🗺️ Mapa de Salud por Bloque")
            try:
                fig_map, ax_map = plt.subplots(figsize=(10,5))
                gdf_completo.plot(column='salud', ax=ax_map, legend=True, categorical=True, cmap='RdYlGn',
                                  edgecolor='black', linewidth=0.3, legend_kwds={'title':'Salud','loc':'lower right'})
                ax_map.set_title("Distribución espacial de la salud")
                ax_map.set_xlabel("Longitud"); ax_map.set_ylabel("Latitud")
                st.pyplot(fig_map)
                plt.close(fig_map)
            except Exception as e:
                st.warning(f"Error en mapa: {e}")
            st.markdown("---")
            st.markdown("#### 📋 Resumen detallado por bloque")
            try:
                tabla = gdf_completo[['id_bloque','area_ha','edad_anios','ndvi_modis','ndwi_modis','salud']].copy()
                tabla.columns = ['Bloque','Área (ha)','Edad (años)','NDVI','NDWI','Salud']
                def color_salud(val):
                    if val=='Crítica': return 'background-color:#d73027; color:white'
                    if val=='Baja': return 'background-color:#fee08b'
                    if val=='Moderada': return 'background-color:#91cf60'
                    if val=='Buena': return 'background-color:#1a9850; color:white'
                    return ''
                styled = tabla.style.format({'Área (ha)':'{:.2f}','Edad (años)':'{:.1f}','NDVI':'{:.3f}','NDWI':'{:.3f}'}).applymap(color_salud, subset=['Salud'])
                st.dataframe(styled, use_container_width=True, height=400)
                csv_tabla = tabla.to_csv(index=False)
                st.download_button("📥 Exportar CSV", csv_tabla, f"resumen_{datetime.now():%Y%m%d}.csv", "text/csv")
            except Exception as e:
                st.warning(f"Error en tabla: {e}")
        with tab2:
            st.subheader("🗺️ MAPAS INTERACTIVOS")
            st.markdown("### 🌍 Mapa Interactivo con Plantas Detectadas")
            try:
                colormap_ndvi = LinearColormap(colors=['red','yellow','green'], vmin=0.3, vmax=0.9)
                mapa = crear_mapa_interactivo_base(gdf_completo, columna_color='ndvi_modis', colormap=colormap_ndvi,
                                                   tooltip_fields=['id_bloque','ndvi_modis','salud'], tooltip_aliases=['Bloque','NDVI','Salud'])
                if st.session_state.plantas_detectadas:
                    plantas_group = folium.FeatureGroup(name="Plantas")
                    for p in st.session_state.plantas_detectadas[:2000]:
                        if 'centroide' in p:
                            lon, lat = p['centroide']
                            folium.CircleMarker([lat, lon], radius=2, color='red', fill=True, fill_color='red').add_to(plantas_group)
                    plantas_group.add_to(mapa)
                folium.LayerControl().add_to(mapa)
                folium_static(mapa, width=1000, height=600)
            except Exception as e:
                st.error(f"Error en mapa: {e}")
        with tab3:
            st.subheader("🛰️ ÍNDICES DE VEGETACIÓN")
            st.caption(f"Fuente: {st.session_state.datos_modis.get('fuente','Earthdata')}")
            st.markdown("### 🌿 NDVI")
            if 'ndvi_modis' in gdf_completo.columns:
                mostrar_estadisticas_indice(gdf_completo, 'ndvi_modis', 'NDVI', 0.3, 0.9, ['red','yellow','green'])
            else:
                st.error("No hay datos de NDVI")
            st.markdown("---")
            st.markdown("### 💧 NDWI")
            st.info("NDWI = (NIR - SWIR)/(NIR + SWIR) con MOD09GA")
            if 'ndwi_modis' in gdf_completo.columns:
                mostrar_estadisticas_indice(gdf_completo, 'ndwi_modis', 'NDWI', 0.1, 0.7, ['brown','yellow','blue'])
            else:
                st.error("No hay datos de NDWI")
            st.markdown("---")
            mostrar_comparacion_ndvi_ndwi(gdf_completo)
            st.markdown("### 📥 EXPORTAR")
            try:
                gdf_indices = gdf_completo[['id_bloque','ndvi_modis','ndwi_modis','salud','geometry']].copy()
                gdf_indices.columns = ['id_bloque','NDVI','NDWI','Salud','geometry']
                geojson = gdf_indices.to_json()
                csv = gdf_indices.drop(columns='geometry').to_csv(index=False)
                col1, col2 = st.columns(2)
                with col1: st.download_button("🗺️ GeoJSON", geojson, f"indices_{datetime.now():%Y%m%d}.geojson", "application/geo+json")
                with col2: st.download_button("📊 CSV", csv, f"indices_{datetime.now():%Y%m%d}.csv", "text/csv")
            except Exception as e:
                st.info(f"Error exportando: {e}")
        with tab4:
            st.subheader("🌤️ DATOS CLIMÁTICOS")
            datos = st.session_state.datos_climaticos
            if datos:
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Precipitación total", f"{datos['precipitacion']['total']} mm")
                with col2: st.metric("Días con lluvia", f"{datos['precipitacion']['dias_con_lluvia']} días")
                with col3: st.metric("Temperatura promedio", f"{datos['temperatura']['promedio']}°C")
                with col4: st.metric("Radiación promedio", f"{datos.get('radiacion',{}).get('promedio','N/A')} MJ/m²")
                st.markdown("### 📈 GRÁFICOS")
                fig_clima = crear_graficos_climaticos_completos(datos)
                if fig_clima:
                    st.pyplot(fig_clima)
                    plt.close(fig_clima)
                st.markdown("### 📋 INFORMACIÓN")
                st.write(f"- **Fuente:** {datos.get('fuente','N/A')}")
                st.write(f"- **Período:** {datos['periodo']}")
            else:
                st.info("No hay datos climáticos")
        with tab5:
            st.subheader("🌱 DETECCIÓN DE PLANTAS")
            if st.session_state.deteccion_ejecutada and st.session_state.plantas_detectadas:
                plantas = st.session_state.plantas_detectadas
                total = len(plantas)
                area_total_val = resultados.get('area_total',0)
                densidad = total/area_total_val if area_total_val>0 else 0
                st.success(f"✅ {total} plantas detectadas")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Plantas", f"{total:,}")
                with col2: st.metric("Densidad", f"{densidad:.0f} plantas/ha")
                with col3: st.metric("Área prom.", f"{np.mean([p.get('area_m2',0) for p in plantas]):.1f} m²")
                with col4: st.metric("Diámetro prom.", f"{np.mean([p.get('diametro_aprox',0) for p in plantas]):.1f} m")
                st.markdown("### 🗺️ Mapa de Distribución")
                try:
                    centroide = gdf_completo.geometry.unary_union.centroid
                    m = folium.Map(location=[centroide.y, centroide.x], zoom_start=16)
                    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)
                    folium.GeoJson(gdf_completo.to_json(), style_function=lambda x: {'color':'blue','fillOpacity':0.1}).add_to(m)
                    for i, p in enumerate(plantas[:2000]):
                        if 'centroide' in p:
                            lon, lat = p['centroide']
                            folium.CircleMarker([lat, lon], radius=2, color='red', fill=True, fill_color='red', tooltip=f"Planta #{i+1}").add_to(m)
                    folium.LayerControl().add_to(m)
                    folium_static(m, width=1000, height=600)
                except Exception as e:
                    st.error(f"Error en mapa: {e}")
                if plantas:
                    df_plantas = pd.DataFrame([{
                        'id':i+1, 'longitud':p.get('centroide',(0,0))[0], 'latitud':p.get('centroide',(0,0))[1],
                        'area_m2':p.get('area_m2',0), 'diametro_m':p.get('diametro_aprox',0)
                    } for i,p in enumerate(plantas)])
                    geojson = gpd.GeoDataFrame(df_plantas, geometry=gpd.points_from_xy(df_plantas.longitud, df_plantas.latitud), crs='EPSG:4326').to_json()
                    csv = df_plantas.to_csv(index=False)
                    col1, col2 = st.columns(2)
                    with col1: st.download_button("🗺️ GeoJSON", geojson, f"plantas_{datetime.now():%Y%m%d}.geojson", "application/geo+json")
                    with col2: st.download_button("📊 CSV", csv, f"coordenadas_{datetime.now():%Y%m%d}.csv", "text/csv")
            else:
                st.info("Detección no ejecutada")
                if st.button("🔍 EJECUTAR DETECCIÓN", key="detectar_tab5"):
                    ejecutar_deteccion_plantas()
                    st.rerun()
        with tab6:
            st.subheader("🧪 FERTILIDAD NPK")
            datos_fertilidad = st.session_state.datos_fertilidad
            if datos_fertilidad:
                df_fertilidad = pd.DataFrame(datos_fertilidad)
                gdf_fertilidad = gpd.GeoDataFrame(df_fertilidad, geometry='geometria', crs='EPSG:4326')
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1: st.metric("N", f"{df_fertilidad['N_kg_ha'].mean():.0f} kg/ha")
                with col2: st.metric("P₂O₅", f"{df_fertilidad['P_kg_ha'].mean():.0f} kg/ha")
                with col3: st.metric("K₂O", f"{df_fertilidad['K_kg_ha'].mean():.0f} kg/ha")
                with col4: st.metric("pH", f"{df_fertilidad['pH'].mean():.2f}")
                with col5: st.metric("MO", f"{df_fertilidad['MO_porcentaje'].mean():.1f}%")
                st.markdown("### 🗺️ MAPA INTERACTIVO")
                variable = st.selectbox("Variable", ['N_kg_ha','P_kg_ha','K_kg_ha','pH','MO_porcentaje'],
                                        format_func=lambda x: {'N_kg_ha':'N (kg/ha)','P_kg_ha':'P₂O₅ (kg/ha)','K_kg_ha':'K₂O (kg/ha)','pH':'pH','MO_porcentaje':'MO (%)'}[x])
                mapa_fert = crear_mapa_fertilidad_interactivo(gdf_fertilidad, variable)
                if mapa_fert:
                    folium_static(mapa_fert, width=1000, height=600)
                st.markdown("### 📋 RECOMENDACIONES")
                df_recom = df_fertilidad[['id_bloque','N_kg_ha','P_kg_ha','K_kg_ha','pH','recomendacion_N','recomendacion_P','recomendacion_K']].rename(columns={
                    'id_bloque':'Bloque','N_kg_ha':'N','P_kg_ha':'P₂O₅','K_kg_ha':'K₂O','pH':'pH',
                    'recomendacion_N':'Recom. N','recomendacion_P':'Recom. P','recomendacion_K':'Recom. K'
                })
                st.dataframe(df_recom, use_container_width=True)
                csv_fert = df_fertilidad.drop(columns='geometria').to_csv(index=False)
                st.download_button("📊 CSV Fertilidad", csv_fert, f"fertilidad_{datetime.now():%Y%m%d}.csv", "text/csv")
            else:
                st.info("Ejecuta el análisis para ver datos de fertilidad")
        with tab7:
            st.subheader("🌱 TEXTURA DE SUELO")
            textura_por_bloque = st.session_state.get('textura_por_bloque', [])
            if textura_por_bloque:
                df_textura = pd.DataFrame(textura_por_bloque)
                st.success("Análisis de textura completado")
                st.markdown("### 🗺️ Mapa de Tipos de Suelo")
                try:
                    gdf_textura = gpd.GeoDataFrame(df_textura, geometry='geometria', crs='EPSG:4326')
                    tipos = gdf_textura['tipo_suelo'].unique()
                    colores = ['#8B4513','#D2691E','#F4A460','#DEB887','#BC8F8F','#CD853F']
                    color_dict = {t: colores[i%len(colores)] for i,t in enumerate(tipos)}
                    m = folium.Map(location=[gdf_completo.geometry.centroid.y.mean(), gdf_completo.geometry.centroid.x.mean()], zoom_start=15)
                    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri').add_to(m)
                    def style_func(feature):
                        return {'fillColor': color_dict.get(feature['properties']['tipo_suelo'], '#888'), 'color':'black','weight':1,'fillOpacity':0.6}
                    folium.GeoJson(gdf_textura.to_json(), style_function=style_func,
                                   tooltip=folium.GeoJsonTooltip(fields=['id_bloque','tipo_suelo','arena','limo','arcilla','drenaje'],
                                                                 aliases=['Bloque','Tipo','Arena %','Limo %','Arcilla %','Drenaje'])).add_to(m)
                    folium.LayerControl().add_to(m)
                    folium_static(m, width=1000, height=600)
                except Exception as e:
                    st.error(f"Error en mapa: {e}")
                st.markdown("### 📊 Composición Textural")
                fig, ax = plt.subplots(figsize=(12,6))
                df_plot = df_textura.head(20)
                ax.bar(df_plot['id_bloque'].astype(str), df_plot['arena'], label='Arena', color='#F4A460')
                ax.bar(df_plot['id_bloque'].astype(str), df_plot['limo'], bottom=df_plot['arena'], label='Limo', color='#DEB887')
                ax.bar(df_plot['id_bloque'].astype(str), df_plot['arcilla'], bottom=df_plot['arena']+df_plot['limo'], label='Arcilla', color='#8B4513')
                ax.set_xlabel('Bloque'); ax.set_ylabel('Porcentaje'); ax.set_title('Composición Textural'); ax.legend()
                plt.xticks(rotation=45); plt.tight_layout()
                st.pyplot(fig); plt.close(fig)
                st.markdown("### 🔺 Triángulo Textural (primer bloque)")
                if len(df_textura)>0:
                    row = df_textura.iloc[0]
                    fig_tri = crear_grafico_textural(row['arena'], row['limo'], row['arcilla'], row['tipo_suelo'])
                    st.plotly_chart(fig_tri, use_container_width=True)
                csv_textura = df_textura.drop(columns='geometria').to_csv(index=False)
                st.download_button("📊 CSV Textura", csv_textura, f"textura_{datetime.now():%Y%m%d}.csv", "text/csv")
            else:
                st.info("Ejecuta el análisis para ver textura")
        with tab8:
            st.subheader("🗺️ CURVAS DE NIVEL")
            if st.session_state.demo_mode:
                st.info("ℹ️ En DEMO se muestran curvas simuladas. Para curvas reales, suscríbete a Premium.")
            api_key = st.text_input("🔑 API Key OpenTopography (opcional)", type="password")
            intervalo = st.slider("Intervalo (m)", 5, 50, 10)
            if st.button("🔄 Generar curvas"):
                with st.spinner("Generando..."):
                    gdf_original = st.session_state.gdf_original
                    if gdf_original is None:
                        st.error("Primero carga una plantación")
                    else:
                        if not st.session_state.demo_mode and api_key:
                            dem, meta, transform = obtener_dem_opentopography(gdf_original, api_key)
                            if dem is not None:
                                curvas = generar_curvas_nivel_reales(dem, transform, intervalo)
                                st.success(f"✅ {len(curvas)} curvas reales generadas")
                            else:
                                st.warning("No se pudo obtener DEM real, usando simulado")
                                curvas = generar_curvas_nivel_simuladas(gdf_original)
                        else:
                            curvas = generar_curvas_nivel_simuladas(gdf_original)
                            st.info(f"ℹ️ {len(curvas)} curvas simuladas")
                        if curvas:
                            st.session_state.curvas_nivel = curvas
                            m = mapa_curvas_coloreadas(gdf_original, curvas)
                            folium_static(m, width=1000, height=600)
                            gdf_curvas = gpd.GeoDataFrame({'elevacion':[e for _,e in curvas], 'geometry':[l for l,_ in curvas]}, crs='EPSG:4326')
                            geojson = gdf_curvas.to_json()
                            csv = gdf_curvas.drop(columns='geometry').to_csv(index=False)
                            col1, col2 = st.columns(2)
                            with col1: st.download_button("🗺️ GeoJSON", geojson, f"curvas_{datetime.now():%Y%m%d}.geojson", "application/geo+json")
                            with col2: st.download_button("📊 CSV", csv, f"curvas_{datetime.now():%Y%m%d}.csv", "text/csv")
                        else:
                            st.warning("No se encontraron curvas")
        with tab9:
            st.subheader("🐛 Detección YOLO")
            if st.session_state.demo_mode:
                st.warning("⚠️ YOLO solo en Premium")
            elif not YOLO_AVAILABLE:
                st.error("Ultralytics no instalado")
            elif not CV2_AVAILABLE:
                st.error("OpenCV no disponible")
            else:
                st.markdown("Sube una imagen y un modelo YOLO (.pt)")
                col1, col2 = st.columns(2)
                with col1:
                    img_file = st.file_uploader("📸 Imagen", type=['jpg','jpeg','png'], key="yolo_img")
                with col2:
                    model_file = st.file_uploader("🤖 Modelo YOLO", type=['pt','onnx'], key="yolo_model")
                conf = st.slider("Umbral de confianza", 0.1, 0.9, 0.25, 0.05)
                if img_file and model_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(model_file.name)[1]) as tmp:
                        tmp.write(model_file.read())
                        model_path = tmp.name
                    img = Image.open(io.BytesIO(img_file.read()))
                    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    modelo = cargar_modelo_yolo(model_path)
                    if modelo:
                        st.info("Ejecutando inferencia...")
                        resultados = detectar_en_imagen(modelo, img_cv, conf)
                        if resultados and len(resultados)>0:
                            img_anotada, detecciones = dibujar_detecciones_con_leyenda(img_cv, resultados)
                            st.success(f"✅ {len(detecciones)} objetos detectados")
                            st.image(cv2.cvtColor(img_anotada, cv2.COLOR_BGR2RGB), use_container_width=True)
                            st.markdown(crear_leyenda_html(detecciones), unsafe_allow_html=True)
                            # Exportar
                            img_pil = Image.fromarray(cv2.cvtColor(img_anotada, cv2.COLOR_BGR2RGB))
                            buf = io.BytesIO()
                            img_pil.save(buf, format='PNG')
                            img_bytes = buf.getvalue()
                            df_det = pd.DataFrame(detecciones).drop(columns=['color'], errors='ignore')
                            csv_det = df_det.to_csv(index=False)
                            col_d1, col_d2 = st.columns(2)
                            with col_d1: st.download_button("📸 Imagen anotada", img_bytes, f"yolo_{datetime.now():%Y%m%d_%H%M%S}.png", "image/png")
                            with col_d2: st.download_button("📊 CSV", csv_det, f"detecciones_{datetime.now():%Y%m%d_%H%M%S}.csv", "text/csv")
                        else:
                            st.warning("No se detectaron objetos")
                    os.unlink(model_path)

# ===== PIE DE PÁGINA =====
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#94a3b8; padding:20px;">
    <p><strong>© 2026 Analizador de Vid y Olivo Satelital</strong></p>
    <p>Datos: NASA Earthdata · Open-Meteo · NASA POWER · OpenTopography</p>
    <p>Contacto: mawucano@gmail.com | +5493525 532313</p>
</div>
""", unsafe_allow_html=True)
