app.py - Versión mejorada con análisis de NDVI/NDWI por bloque con estadísticas detalladas
- Registro e inicio de sesión de usuarios.
- Suscripción mensual (150 USD) con Mercado Pago.
- Modo DEMO con datos simulados y posibilidad de subir tu propio polígono.
- Modo PREMIUM con datos reales de NDVI y NDWI desde Earthdata (MOD13Q1 y MOD09GA).
- NUEVO: Estadísticas por bloque (media, mín, máx, desv. estándar, conteo de píxeles)
- NUEVO: Validación de calidad de datos satelitales
- NUEVO: Gráficos de variabilidad con barras de error

IMPORTANTE:
- Configurar variables de entorno en secrets: MERCADOPAGO_ACCESS_TOKEN,
EARTHDATA_USERNAME, EARTHDATA_PASSWORD, APP_BASE_URL.
- Instalar dependencias: pip install earthaccess xarray rioxarray rasterio pyhdf

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
from shapely.geometry import Polygon, Point, LineString, mapping, box
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
from plotly.subplots import make_subplots
import cv2
from PIL import Image
from scipy.spatial import KDTree
from scipy.interpolate import Rbf
import base64
import time
import shutil

# Suprimir advertencias de rasterio y otras librerías
warnings.filterwarnings('ignore', category=UserWarning, module='rasterio')
warnings.filterwarnings('ignore', category=RuntimeWarning)

# ===== AUTENTICACIÓN Y PAGOS =====
import sqlite3
import hashlib
import mercadopago

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

# Mostrar advertencias solo si ninguna está disponible
if not RASTERIO_OK and not PYHDF_OK:
    st.warning("⚠️ Ni rasterio ni pyhdf están instalados. No se podrán leer archivos HDF4. Instala al menos uno: pip install rasterio o pip install pyhdf")

# ===== CONFIGURACIÓN DE MERCADO PAGO =====
MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
if not MERCADOPAGO_ACCESS_TOKEN:
    st.error("❌ No se encontró la variable de entorno MERCADOPAGO_ACCESS_TOKEN. Configúrala para habilitar pagos.")
    st.stop()

sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)

# ===== CREDENCIALES EARTHDATA (desde secrets) =====
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
    c.execute('''CREATE TABLE IF NOT EXISTS users
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password_hash TEXT,
    subscription_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    admin_email = "mawucano@gmail.com"
    far_future = "2100-01-01 00:00:00"
    c.execute("SELECT id FROM users WHERE email = ?", (admin_email,))
    existing = c.fetchone()
    if existing:
        c.execute("UPDATE users SET subscription_expires = ? WHERE email = ?", (far_future, admin_email))
    else:
        default_password = "jocauru"
        password_hash = hash_password(default_password)
        c.execute("INSERT INTO users (email, password_hash, subscription_expires) VALUES (?, ?, ?)",
                 (admin_email, password_hash, far_future))
    conn.commit()
    conn.close()

init_db()

def register_user(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        password_hash = hash_password(password)
        c.execute("INSERT INTO users (email, password_hash, subscription_expires) VALUES (?, ?, ?)",
                 (email, password_hash, None))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, password_hash, subscription_expires FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row and verify_password(password, row[1]):
        return {'id': row[0], 'email': email, 'subscription_expires': row[2]}
    return None

def update_subscription(email, days=30):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    new_expiry = (datetime.now() + timedelta(days=days)).isoformat()
    c.execute("UPDATE users SET subscription_expires = ? WHERE email = ?", (new_expiry, email))
    conn.commit()
    conn.close()
    return new_expiry

def get_user_by_email(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT id, email, subscription_expires FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'email': row[1], 'subscription_expires': row[2]}
    return None

# ===== FUNCIONES DE MERCADO PAGO =====
def create_preference(email, amount=150.0, description="Suscripción mensual - Analizador de Palma Aceitera"):
    try:
        base_url = os.environ.get("APP_BASE_URL")
        if not base_url:
            try:
                base_url = st.secrets.get("APP_BASE_URL", "https://tuapp.streamlit.app")
            except:
                base_url = "https://tuapp.streamlit.app"
        
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
            error_msg = preference_response.get("response", {}).get("message", "Error desconocido")
            st.error(f"❌ Error al crear preferencia de pago: {error_msg}")
            return None, None
    except Exception as e:
        st.error(f"❌ Error al conectar con Mercado Pago: {str(e)}")
        return None, None

def check_payment_status(payment_id):
    try:
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] == 200:
            payment = payment_info["response"]
            if payment["status"] == "approved":
                email = payment.get("external_reference")
                if email:
                    new_expiry = update_subscription(email)
                    return True
    except Exception as e:
        st.error(f"Error verificando pago: {e}")
    return False

# ===== FUNCIONES DE AUTENTICACIÓN EN STREAMLIT =====
def show_login_signup():
    with st.sidebar:
        st.markdown("## 🔐 Acceso")
        menu = st.radio(" ", ["Iniciar sesión", "Registrarse"], key="auth_menu")
        email = st.text_input("Email", key="auth_email")
        password = st.text_input("Contraseña", type="password", key="auth_password")
        
        if menu == "Registrarse":
            if st.button("Registrar", key="register_btn"):
                if register_user(email, password):
                    st.success("Registro exitoso. Ahora inicia sesión.")
                else:
                    st.error("El email ya está registrado.")
        else:
            if st.button("Ingresar", key="login_btn"):
                user = login_user(email, password)
                if user:
                    st.session_state.user = user
                    st.success("Sesión iniciada")
                    st.rerun()
                else:
                    st.error("Email o contraseña incorrectos")

def logout():
    if st.sidebar.button("Cerrar sesión"):
        del st.session_state.user
        st.rerun()

# ===== FUNCIÓN DE SUSCRIPCIÓN =====
def check_subscription():
    gdf_temp = st.session_state.get('gdf_original', None)
    if 'user' not in st.session_state:
        show_login_signup()
        if gdf_temp is not None:
            st.session_state.gdf_original = gdf_temp
        st.stop()

    if st.session_state.get('demo_mode', False):
        with st.sidebar:
            st.markdown(f"👤 Usuario: {st.session_state.user['email']} (Modo DEMO)")
            if st.button("💳 Actualizar a Premium", key="upgrade_from_demo"):
                st.session_state.demo_mode = False
                st.session_state.payment_intent = True
                st.rerun()
            logout()
        return

    with st.sidebar:
        st.markdown(f"👤 Usuario: {st.session_state.user['email']}")
        logout()

    user = st.session_state.user
    expiry = user.get('subscription_expires')
    if expiry:
        try:
            expiry_date = datetime.fromisoformat(expiry)
            if expiry_date > datetime.now():
                dias_restantes = (expiry_date - datetime.now()).days
                st.sidebar.info(f"✅ Suscripción activa (vence en {dias_restantes} días)")
                st.session_state.demo_mode = False
                return True
        except:
            pass

    st.warning("🔒 Tu suscripción ha expirado o no tienes una activa.")
    st.markdown("### ¿Cómo deseas continuar?")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 💳 Pagar ahora")
        st.write("Obtén acceso completo a datos satelitales reales por **150 USD/mes**.")
        if st.button("💵 Ir a pagar", key="pay_now"):
            st.session_state.payment_intent = True
            st.rerun()
    with col2:
        st.markdown("#### 🆓 Modo DEMO")
        st.write("Continúa con datos simulados y funcionalidad limitada.")
        if st.button("🎮 Continuar con DEMO", key="demo_button"):
            st.session_state.demo_mode = True
            st.rerun()

    if st.session_state.get('payment_intent', False):
        st.markdown("### 💳 Pago con Mercado Pago")
        st.write("Paga con tarjeta de crédito, débito o efectivo (en USD).")
        if st.button("💵 Pagar ahora 150 USD", key="pay_mp"):
            init_point, pref_id = create_preference(user['email'])
            if init_point:
                st.session_state.pref_id = pref_id
                st.markdown(f"[Haz clic aquí para pagar]({init_point})")
                st.info("Serás redirigido a Mercado Pago. Luego de pagar, regresa a esta página.")
            else:
                st.error("No se pudo generar el link de pago.")
        
        st.markdown("### 🏦 Transferencia bancaria")
        st.write("También puedes pagar por transferencia (USD) a:")
        st.code("CBU: 3220001888034378480018\nAlias: inflar.pacu.inaudita")
        st.write("Luego envía el comprobante a **mawucano@gmail.com** para activar manualmente.")
        
        query_params = st.query_params
        if 'payment' in query_params and query_params['payment'] == 'success' and 'collection_id' in query_params:
            payment_id = query_params['collection_id']
            if check_payment_status(payment_id):
                st.success("✅ ¡Pago aprobado! Tu suscripción ha sido activada por 30 días.")
                updated_user = get_user_by_email(user['email'])
                if updated_user:
                    st.session_state.user = updated_user
                st.session_state.demo_mode = False
                st.session_state.payment_intent = False
                st.rerun()
            else:
                st.error("No se pudo verificar el pago. Contacta a soporte.")
        st.stop()

    st.stop()

# ===== FUNCIONES DE SIMULACIÓN PARA MODO DEMO =====
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

    # NDVI con variabilidad por bloque
    ndvi_vals = 0.5 + 0.2 * np.sin(lons * 10) * np.cos(lats * 10) + 0.1 * np.random.randn(len(lons))
    ndvi_vals = np.clip(ndvi_vals, 0.2, 0.9)
    gdf_dividido['ndvi_modis'] = np.round(ndvi_vals, 3)
    gdf_dividido['ndvi_std'] = np.round(np.abs(np.random.randn(len(lons)) * 0.05), 3)
    gdf_dividido['ndvi_min'] = np.round(ndvi_vals - gdf_dividido['ndvi_std'], 3)
    gdf_dividido['ndvi_max'] = np.round(ndvi_vals + gdf_dividido['ndvi_std'], 3)
    gdf_dividido['ndvi_pixels'] = np.random.randint(50, 200, len(lons))

    # NDWI con variabilidad por bloque
    ndwi_vals = 0.3 + 0.15 * np.cos(lons * 5) * np.sin(lats * 5) + 0.1 * np.random.randn(len(lons))
    ndwi_vals = np.clip(ndwi_vals, 0.1, 0.7)
    gdf_dividido['ndwi_modis'] = np.round(ndwi_vals, 3)
    gdf_dividido['ndwi_std'] = np.round(np.abs(np.random.randn(len(lons)) * 0.03), 3)
    gdf_dividido['ndwi_min'] = np.round(ndwi_vals - gdf_dividido['ndwi_std'], 3)
    gdf_dividido['ndwi_max'] = np.round(ndwi_vals + gdf_dividido['ndwi_std'], 3)
    gdf_dividido['ndwi_pixels'] = np.random.randint(50, 200, len(lons))

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
    temp_diaria = 25 + 5 * np.sin(np.linspace(0, 4*np.pi, dias)) + np.random.randn(dias)
    rad_diaria = 20 + 5 * np.sin(np.linspace(0, 4*np.pi, dias)) + np.random.randn(dias)
    wind_diaria = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, dias)) + np.random.randn(dias)
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
        'fuente': 'Datos simulados (DEMO)'
    }

# ===== CONFIGURACIÓN DE PÁGINA =====
st.set_page_config(page_title="Analizador de Vid y Olivo", page_icon="🍇", layout="wide", initial_sidebar_state="expanded")

# ===== INICIALIZACIÓN DE SESIÓN =====
def init_session_state():
    defaults = {
        'geojson_data': None,
        'analisis_completado': False,
        'resultados_todos': {},
        'palmas_detectadas': [],
        'archivo_cargado': False,
        'gdf_original': None,
        'datos_modis': {},
        'datos_climaticos': {},
        'deteccion_ejecutada': False,
        'n_divisiones': 16,
        'fecha_inicio': datetime.now() - timedelta(days=60),
        'fecha_fin': datetime.now(),
        'variedad_seleccionada': 'Tenera (DxP)',
        'textura_suelo': {},
        'textura_por_bloque': [],
        'datos_fertilidad': [],
        'analisis_suelo': True,
        'curvas_nivel': None,
        'demo_mode': False,
        'payment_intent': False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()
check_subscription()

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
            try:
                gdf = gdf.to_crs('EPSG:4326')
            except Exception as e:
                st.warning(f"⚠️ No se pudo convertir CRS: {e}")
        return gdf
    except Exception as e:
        st.warning(f"Error al corregir CRS: {e}")
        return gdf

def calcular_superficie(gdf):
    try:
        if gdf is None or len(gdf) == 0:
            return 0.0
        gdf = validar_y_corregir_crs(gdf)
        bounds = gdf.total_bounds
        if bounds[0] < -180 or bounds[2] > 180 or bounds[1] < -90 or bounds[3] > 90:
            area_grados2 = gdf.geometry.area.sum()
            area_m2 = area_grados2 * 111000 * 111000
            return area_m2 / 10000
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
            cell_minx = minx + (j * width)
            cell_maxx = minx + ((j + 1) * width)
            cell_miny = miny + (i * height)
            cell_maxy = miny + ((i + 1) * height)
            cell_poly = Polygon([
                (cell_minx, cell_miny), (cell_maxx, cell_miny),
                (cell_maxx, cell_maxy), (cell_minx, cell_maxy)
            ])
            intersection = plantacion_principal.intersection(cell_poly)
            if not intersection.is_empty and intersection.area > 0:
                sub_poligonos.append(intersection)

    if sub_poligonos:
        nuevo_gdf = gpd.GeoDataFrame(
            {'id_bloque': range(1, len(sub_poligonos) + 1), 'geometry': sub_poligonos},
            crs='EPSG:4326'
        )
        return nuevo_gdf
    return gdf

# ===== PARSER KML MEJORADO =====
def procesar_kml_robusto(file_content):
    try:
        try:
            content = file_content.decode('utf-8')
        except:
            content = file_content.decode('latin-1', errors='ignore')
        
        polygons = []
        coord_sections = re.findall(
            r'<coordinates[^>]*>([\s\S]*?)</coordinates>', 
            content, 
            re.IGNORECASE | re.DOTALL
        )
        
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
                    parts = [p.strip() for p in coord.split(',')]
                    if len(parts) >= 2:
                        lon = float(parts[0])
                        lat = float(parts[1])
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
                st.error(f"❌ Formato no soportado: {ext}")
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
            try:
                main_poly = make_valid(main_poly)
                if main_poly.geom_type == 'MultiPolygon':
                    areas = [p.area for p in main_poly.geoms]
                    main_poly = main_poly.geoms[np.argmax(areas)]
            except Exception as e:
                st.warning(f"⚠️ No se pudo reparar la geometría: {e}")
        
        gdf_unido = gpd.GeoDataFrame(
            [{'geometry': main_poly, 'id_bloque': 1}], 
            crs='EPSG:4326'
        )
        
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

# ===== FUNCIONES MEJORADAS PARA NDVI CON ESTADÍSTICAS POR BLOQUE =====
def obtener_ndvi_earthdata(gdf_dividido, fecha_inicio, fecha_fin):
    """
    Obtiene NDVI real para cada bloque con estadísticas detalladas (media, min, max, std, pixel count).
    """
    if not EARTHDATA_OK:
        st.error("Librerías earthaccess/xarray/rioxarray no instaladas.")
        return None
    if not EARTHDATA_USERNAME or not EARTHDATA_PASSWORD:
        st.error("Credenciales de Earthdata no configuradas.")
        return None
    
    try:
        auth = earthaccess.login()
        if not auth.authenticated:
            st.error("No se pudo autenticar con Earthdata.")
            return None

        bounds = gdf_dividido.total_bounds
        bbox = (bounds[0], bounds[1], bounds[2], bounds[3])

        # Buscar MÚLTIPLES escenas para mejor cobertura
        results = earthaccess.search_data(
            short_name='MOD13Q1',
            version='061',
            bounding_box=bbox,
            temporal=(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')),
            count=10
        )

        if not results:
            st.error("No se encontraron escenas MOD13Q1 en el período.")
            return None

        granule = results[0]
        st.info(f"🛰️ Procesando escena NDVI: {granule['umm']['GranuleUR']}")

        temp_dir = tempfile.mkdtemp()
        downloaded_files = earthaccess.download(granule, local_path=temp_dir)
        
        if not downloaded_files:
            st.error("No se pudo descargar el archivo.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        hdf_files = [f for f in downloaded_files if f.endswith('.hdf')]
        if not hdf_files:
            st.error("No se encontró archivo HDF en la descarga.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        download_path = hdf_files[0]

        # Verificar integridad del archivo
        file_size = os.path.getsize(download_path)
        if file_size < 10240:
            with open(download_path, 'r', errors='ignore') as f:
                head = f.read(500).lower()
                if '<html' in head:
                    st.error("El archivo descargado parece ser una página HTML de error.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

        # --- PROCESAMIENTO CON RASTERIO ---
        rasterio_success = False
        if RASTERIO_OK:
            try:
                with rasterio.open(download_path) as src:
                    subdatasets = src.subdatasets
                    ndvi_sub = None
                    for sd in subdatasets:
                        if 'NDVI' in sd.upper():
                            ndvi_sub = sd
                            break
                    
                    if ndvi_sub:
                        with rasterio.open(ndvi_sub) as src_ndvi:
                            raster_crs = src_ndvi.crs
                            nodata = src_ndvi.nodata
                            gdf_proj = gdf_dividido.to_crs(raster_crs)

                            ndvi_values = []
                            ndvi_std = []
                            ndvi_min = []
                            ndvi_max = []
                            pixel_count = []
                            
                            progress_bar = st.progress(0, text="Procesando bloques para NDVI...")

                            for idx, row in gdf_proj.iterrows():
                                geom = [mapping(row.geometry)]
                                try:
                                    out_image, _ = mask(src_ndvi, geom, crop=True, nodata=nodata)
                                    data = out_image[0].astype(np.float32)
                                    
                                    # Aplicar factor de escala MOD13Q1 (0.0001)
                                    data_scaled = data * 0.0001
                                    
                                    # Máscara de valores inválidos
                                    mask_invalid = (data == nodata) | (data_scaled < -1) | (data_scaled > 1)
                                    data_clean = np.ma.masked_where(mask_invalid, data_scaled)
                                    
                                    # Calcular estadísticas por bloque
                                    mean_val = data_clean.mean()
                                    std_val = data_clean.std()
                                    min_val = data_clean.min()
                                    max_val = data_clean.max()
                                    count_valid = np.count_nonzero(~data_clean.mask)
                                    
                                    ndvi_values.append(round(float(mean_val), 4) if not np.ma.is_masked(mean_val) else np.nan)
                                    ndvi_std.append(round(float(std_val), 4) if not np.ma.is_masked(std_val) else np.nan)
                                    ndvi_min.append(round(float(min_val), 4) if not np.ma.is_masked(min_val) else np.nan)
                                    ndvi_max.append(round(float(max_val), 4) if not np.ma.is_masked(max_val) else np.nan)
                                    pixel_count.append(int(count_valid))
                                    
                                except Exception:
                                    ndvi_values.append(np.nan)
                                    ndvi_std.append(np.nan)
                                    ndvi_min.append(np.nan)
                                    ndvi_max.append(np.nan)
                                    pixel_count.append(0)

                                progress_bar.progress((idx + 1) / len(gdf_proj),
                                                     text=f"Procesando bloque {idx+1}/{len(gdf_proj)}")

                            progress_bar.empty()

                            gdf_dividido['ndvi_modis'] = ndvi_values
                            gdf_dividido['ndvi_std'] = ndvi_std
                            gdf_dividido['ndvi_min'] = ndvi_min
                            gdf_dividido['ndvi_max'] = ndvi_max
                            gdf_dividido['ndvi_pixels'] = pixel_count
                            
                            st.success(f"✅ NDVI calculado por bloque: {len([v for v in ndvi_values if not np.isnan(v)])} bloques válidos")
                            rasterio_success = True
                            return gdf_dividido

            except Exception as e:
                st.warning(f"⚠️ Rasterio falló, intentando con pyhdf: {str(e)[:100]}")
                pass

        # --- FALLBACK CON PYHDF ---
        if not rasterio_success and PYHDF_OK:
            try:
                hdf = SD(download_path, SDC.READ)
                
                ndvi_dataset = None
                for name in hdf.datasets().keys():
                    if 'NDVI' in name.upper():
                        ndvi_dataset = name
                        break
                
                if ndvi_dataset is None:
                    st.error("No se encontró dataset NDVI en el archivo HDF.")
                    return None

                ndvi_data = hdf.select(ndvi_dataset).get()
                ndvi_scaled = ndvi_data.astype(np.float32) * 0.0001

                metadata = hdf.attributes()['StructMetadata.0']
                xdim_match = re.search(r'XDim\s*=\s*(\d+)', metadata, re.IGNORECASE)
                ydim_match = re.search(r'YDim\s*=\s*(\d+)', metadata, re.IGNORECASE)
                ul_match = re.search(r'UpperLeftPointMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)', metadata, re.IGNORECASE)
                lr_match = re.search(r'LowerRightMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)', metadata, re.IGNORECASE)

                if not (xdim_match and ydim_match and ul_match and lr_match):
                    raise ValueError("No se pudo extraer la geolocalización completa")

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
                        ndvi_std = []
                        ndvi_min = []
                        ndvi_max = []
                        pixel_count = []
                        
                        progress_bar = st.progress(0, text="Procesando bloques para NDVI con pyhdf...")

                        for idx, row in gdf_proj.iterrows():
                            geom = [mapping(row.geometry)]
                            try:
                                out_image, _ = mask(src_ndvi, geom, crop=True, nodata=-32768)
                                data = out_image[0]
                                mask_invalid = (data == -32768) | (data < -1) | (data > 1)
                                data_clean = np.ma.masked_where(mask_invalid, data)
                                
                                mean_val = data_clean.mean()
                                std_val = data_clean.std()
                                min_val = data_clean.min()
                                max_val = data_clean.max()
                                count_valid = np.count_nonzero(~data_clean.mask)
                                
                                ndvi_values.append(round(float(mean_val), 4) if not np.ma.is_masked(mean_val) else np.nan)
                                ndvi_std.append(round(float(std_val), 4) if not np.ma.is_masked(std_val) else np.nan)
                                ndvi_min.append(round(float(min_val), 4) if not np.ma.is_masked(min_val) else np.nan)
                                ndvi_max.append(round(float(max_val), 4) if not np.ma.is_masked(max_val) else np.nan)
                                pixel_count.append(int(count_valid))
                                
                            except Exception:
                                ndvi_values.append(np.nan)
                                ndvi_std.append(np.nan)
                                ndvi_min.append(np.nan)
                                ndvi_max.append(np.nan)
                                pixel_count.append(0)

                            progress_bar.progress((idx + 1) / len(gdf_proj),
                                                 text=f"Procesando bloque {idx+1}/{len(gdf_proj)}")

                        progress_bar.empty()

                        gdf_dividido['ndvi_modis'] = ndvi_values
                        gdf_dividido['ndvi_std'] = ndvi_std
                        gdf_dividido['ndvi_min'] = ndvi_min
                        gdf_dividido['ndvi_max'] = ndvi_max
                        gdf_dividido['ndvi_pixels'] = pixel_count
                        
                        st.success(f"✅ NDVI calculado por bloque con pyhdf: {len([v for v in ndvi_values if not np.isnan(v)])} bloques válidos")
                        return gdf_dividido

            except Exception as e_pyhdf:
                st.error(f"Error al procesar con pyhdf: {str(e_pyhdf)}")
                return None
        
        if not rasterio_success:
            st.error("No se pudo leer el archivo HDF.")
            return None

    except Exception as e:
        st.error(f"Error en obtención de NDVI: {str(e)}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ===== FUNCIONES MEJORADAS PARA NDWI CON ESTADÍSTICAS POR BLOQUE =====
def obtener_ndwi_earthdata(gdf_dividido, fecha_inicio, fecha_fin):
    """
    Obtiene NDWI real para cada bloque con estadísticas detalladas.
    """
    if not EARTHDATA_OK:
        st.error("Librerías earthaccess no instaladas.")
        return None
    if not EARTHDATA_USERNAME or not EARTHDATA_PASSWORD:
        st.error("Credenciales de Earthdata no configuradas.")
        return None
    
    try:
        auth = earthaccess.login()
        if not auth.authenticated:
            st.error("No se pudo autenticar con Earthdata.")
            return None

        bounds = gdf_dividido.total_bounds
        bbox = (bounds[0], bounds[1], bounds[2], bounds[3])

        results = earthaccess.search_data(
            short_name='MOD09GA',
            version='061',
            bounding_box=bbox,
            temporal=(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')),
            count=10
        )

        if not results:
            st.error("No se encontraron escenas MOD09GA en el período.")
            return None

        granule = results[0]
        st.info(f"💧 Procesando escena NDWI: {granule['umm']['GranuleUR']}")

        temp_dir = tempfile.mkdtemp()
        downloaded_files = earthaccess.download(granule, local_path=temp_dir)
        
        if not downloaded_files:
            st.error("No se pudo descargar el archivo.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        hdf_files = [f for f in downloaded_files if f.endswith('.hdf')]
        if not hdf_files:
            st.error("No se encontró archivo HDF.")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        download_path = hdf_files[0]

        file_size = os.path.getsize(download_path)
        if file_size < 10240:
            with open(download_path, 'r', errors='ignore') as f:
                head = f.read(500).lower()
                if '<html' in head:
                    st.error("El archivo descargado es una página HTML de error.")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

        rasterio_success = False
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

                            ndwi_values = []
                            ndwi_std = []
                            ndwi_min = []
                            ndwi_max = []
                            pixel_count = []
                            
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
                                    std_val = ndwi.std()
                                    min_val = ndwi.min()
                                    max_val = ndwi.max()
                                    count_valid = np.count_nonzero(~ndwi.mask) if hasattr(ndwi, 'mask') else len(ndwi.flatten())
                                    
                                    ndwi_values.append(round(float(mean_val), 4) if not np.ma.is_masked(mean_val) else np.nan)
                                    ndwi_std.append(round(float(std_val), 4) if not np.ma.is_masked(std_val) else np.nan)
                                    ndwi_min.append(round(float(min_val), 4) if not np.ma.is_masked(min_val) else np.nan)
                                    ndwi_max.append(round(float(max_val), 4) if not np.ma.is_masked(max_val) else np.nan)
                                    pixel_count.append(int(count_valid))
                                    
                                except Exception:
                                    ndwi_values.append(np.nan)
                                    ndwi_std.append(np.nan)
                                    ndwi_min.append(np.nan)
                                    ndwi_max.append(np.nan)
                                    pixel_count.append(0)

                                progress_bar.progress((idx + 1) / len(gdf_proj),
                                                     text=f"Procesando bloque {idx+1}/{len(gdf_proj)}")

                            progress_bar.empty()

                            gdf_dividido['ndwi_modis'] = ndwi_values
                            gdf_dividido['ndwi_std'] = ndwi_std
                            gdf_dividido['ndwi_min'] = ndwi_min
                            gdf_dividido['ndwi_max'] = ndwi_max
                            gdf_dividido['ndwi_pixels'] = pixel_count
                            
                            st.success(f"✅ NDWI calculado por bloque: {len([v for v in ndwi_values if not np.isnan(v)])} bloques válidos")
                            rasterio_success = True
                            return gdf_dividido

            except Exception:
                pass

        if not rasterio_success and PYHDF_OK:
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
                    st.error("No se encontraron las bandas NIR o SWIR con pyhdf.")
                    return None

                nir = nir_data.astype(np.float32) * 0.0001
                swir = swir_data.astype(np.float32) * 0.0001

                metadata = hdf.attributes()['StructMetadata.0']
                xdim_match = re.search(r'XDim\s*=\s*(\d+)', metadata, re.IGNORECASE)
                ydim_match = re.search(r'YDim\s*=\s*(\d+)', metadata, re.IGNORECASE)
                ul_match = re.search(r'UpperLeftPointMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)', metadata, re.IGNORECASE)
                lr_match = re.search(r'LowerRightMtrs\s*=\s*\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)', metadata, re.IGNORECASE)

                if not (xdim_match and ydim_match and ul_match and lr_match):
                    raise ValueError("No se pudo extraer la geolocalización completa")

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
                        ndwi_std = []
                        ndwi_min = []
                        ndwi_max = []
                        pixel_count = []
                        
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
                                std_val = ndwi.std()
                                min_val = ndwi.min()
                                max_val = ndwi.max()
                                count_valid = np.count_nonzero(~ndwi.mask) if hasattr(ndwi, 'mask') else len(ndwi.flatten())
                                
                                ndwi_values.append(round(float(mean_val), 4) if not np.ma.is_masked(mean_val) else np.nan)
                                ndwi_std.append(round(float(std_val), 4) if not np.ma.is_masked(std_val) else np.nan)
                                ndwi_min.append(round(float(min_val), 4) if not np.ma.is_masked(min_val) else np.nan)
                                ndwi_max.append(round(float(max_val), 4) if not np.ma.is_masked(max_val) else np.nan)
                                pixel_count.append(int(count_valid))
                                
                            except Exception:
                                ndwi_values.append(np.nan)
                                ndwi_std.append(np.nan)
                                ndwi_min.append(np.nan)
                                ndwi_max.append(np.nan)
                                pixel_count.append(0)

                            progress_bar.progress((idx + 1) / len(gdf_proj),
                                                 text=f"Procesando bloque {idx+1}/{len(gdf_proj)}")

                        progress_bar.empty()

                        gdf_dividido['ndwi_modis'] = ndwi_values
                        gdf_dividido['ndwi_std'] = ndwi_std
                        gdf_dividido['ndwi_min'] = ndwi_min
                        gdf_dividido['ndwi_max'] = ndwi_max
                        gdf_dividido['ndwi_pixels'] = pixel_count
                        
                        st.success(f"✅ NDWI calculado por bloque con pyhdf: {len([v for v in ndwi_values if not np.isnan(v)])} bloques válidos")
                        return gdf_dividido

            except Exception as e_pyhdf:
                st.error(f"Error al procesar con pyhdf: {str(e_pyhdf)}")
                return None
        
        if not rasterio_success:
            st.error("No se pudo leer el archivo HDF.")
            return None

    except Exception as e:
        st.error(f"Error en obtención de NDWI: {str(e)}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ===== VALIDACIÓN DE CALIDAD DE DATOS =====
def validar_calidad_ndvi(gdf_dividido):
    """Valida la calidad de los datos NDVI obtenidos."""
    problemas = []
    
    if 'ndvi_pixels' in gdf_dividido.columns:
        bloques_sin_datos = (gdf_dividido['ndvi_pixels'] == 0).sum()
        if bloques_sin_datos > 0:
            problemas.append(f"⚠️ {bloques_sin_datos} bloques sin datos válidos")
    
    if 'ndvi_modis' in gdf_dividido.columns:
        valores_nan = gdf_dividido['ndvi_modis'].isna().sum()
        if valores_nan > 0:
            problemas.append(f"⚠️ {valores_nan} valores NDVI inválidos")
        
        ndvi_min = gdf_dividido['ndvi_modis'].min()
        ndvi_max = gdf_dividido['ndvi_modis'].max()
        if not np.isnan(ndvi_min) and not np.isnan(ndvi_max):
            if ndvi_min < 0.1 or ndvi_max > 0.95:
                problemas.append("⚠️ Rango de NDVI fuera de lo esperado")
    
    return problemas

# ===== FUNCIONES CLIMÁTICAS =====
def obtener_clima_openmeteo(gdf, fecha_inicio, fecha_fin):
    try:
        centroide = gdf.geometry.unary_union.centroid
        lat = centroide.y
        lon = centroide.x
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": fecha_inicio.strftime("%Y-%m-%d"),
            "end_date": fecha_fin.strftime("%Y-%m-%d"),
            "daily": ["temperature_2m_max", "temperature_2m_min",
                     "temperature_2m_mean", "precipitation_sum"],
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
        return generar_datos_climaticos_simulados(gdf, fecha_inicio, fecha_fin)

def obtener_radiacion_viento_power(gdf, fecha_inicio, fecha_fin):
    try:
        centroide = gdf.geometry.unary_union.centroid
        lat = centroide.y
        lon = centroide.x
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
        st.warning(f"Error en NASA POWER: {str(e)[:100]}. Usando datos simulados.")
        dias = (fecha_fin - fecha_inicio).days
        if dias <= 0:
            dias = 30
        rad_diaria = [np.random.uniform(15, 25) for _ in range(dias)]
        wind_diaria = [np.random.uniform(2, 6) for _ in range(dias)]
        return {
            'radiacion': {
                'promedio': round(np.mean(rad_diaria), 1),
                'maxima': round(max(rad_diaria), 1),
                'minima': round(min(rad_diaria), 1),
                'diaria': rad_diaria
            },
            'viento': {
                'promedio': round(np.mean(wind_diaria), 1),
                'maxima': round(max(wind_diaria), 1),
                'diaria': wind_diaria
            },
            'fuente': 'Simulado (fallback)'
        }

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
            'radiacion': {
                'promedio': round(np.mean(rad_diaria), 1),
                'maxima': round(max(rad_diaria), 1),
                'minima': round(min(rad_diaria), 1),
                'diaria': rad_diaria
            },
            'precipitacion': {
                'total': round(sum(precip_diaria), 1),
                'maxima_diaria': round(max(precip_diaria), 1),
                'dias_con_lluvia': sum(1 for p in precip_diaria if p > 0.1),
                'diaria': precip_diaria
            },
            'viento': {
                'promedio': round(np.mean(wind_diaria), 1),
                'maxima': round(max(wind_diaria), 1),
                'diaria': wind_diaria
            },
            'temperatura': {
                'promedio': round(np.mean(temp_diaria), 1),
                'maxima': round(max(temp_diaria), 1),
                'minima': round(min(temp_diaria), 1),
                'diaria': temp_diaria
            },
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
        return {
            'detectadas': plantas,
            'total': len(plantas),
            'patron': 'hexagonal adaptativo',
            'densidad_calculada': len(plantas) / area_ha,
            'area_ha': area_ha
        }
    except Exception as e:
        print(f"Error en detección mejorada: {e}")
        return {'detectadas': [], 'total': 0}

def ejecutar_deteccion_plantas():
    if st.session_state.gdf_original is None:
        st.error("Primero debe cargar un archivo de plantación")
        return
    with st.spinner("Ejecutando detección MEJORADA de plantas..."):
        gdf = st.session_state.gdf_original
        densidad = st.session_state.get('densidad_personalizada', 130)
        resultados = mejorar_deteccion_plantas(gdf, densidad)
        plantas_verificadas = verificar_puntos_en_poligono(resultados['detectadas'], gdf)
        st.session_state.plantas_detectadas = plantas_verificadas
        st.session_state.deteccion_ejecutada = True
        st.success(f"✅ Detección MEJORADA completada: {len(plantas_verificadas)} plantas detectadas")

# ===== FUNCIONES DE VISUALIZACIÓN MEJORADAS =====
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
            return {
                'fillColor': color,
                'color': 'black',
                'weight': 0.5,
                'fillOpacity': 0.7
            }
    else:
        def style_function(feature):
            return {'fillColor': '#3388ff', 'color': 'black', 'weight': 0.5, 'fillOpacity': 0.4}

    if tooltip_fields and tooltip_aliases:
        tooltip = folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True)
    else:
        tooltip = None

    folium.GeoJson(
        gdf.to_json(),
        name='Polígonos',
        style_function=style_function,
        tooltip=tooltip
    ).add_to(m)

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
        st.warning("No se pudo generar el mapa.")
        fig, ax = plt.subplots(figsize=(10,4))
        ax.bar(range(len(gdf)), gdf[columna].values, color='steelblue')
        ax.set_xlabel('Bloque')
        ax.set_ylabel(titulo)
        ax.set_title(f'Valores de {titulo} por bloque')
        st.pyplot(fig)
        plt.close(fig)

    # Mostrar estadísticas COMPLETAS
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Media", f"{valores.mean():.3f}")
    with col2:
        st.metric("Mediana", f"{valores.median():.3f}")
    with col3:
        st.metric("Desv. estándar", f"{valores.std():.3f}")
    with col4:
        st.metric("Mínimo", f"{valores.min():.3f}")
    with col5:
        st.metric("Máximo", f"{valores.max():.3f}")

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
        st.info("ℹ️ Para ver la línea de tendencia, instala 'statsmodels'")

    fig = px.scatter(
        df, x='ndvi_modis', y='ndwi_modis', color='salud',
        size='area_ha', hover_data=['id_bloque'],
        labels={'ndvi_modis': 'NDVI', 'ndwi_modis': 'NDWI', 'salud': 'Salud'},
        title='Relación entre NDVI y NDWI por bloque',
        color_discrete_map={
            'Crítica': '#d73027',
            'Baja': '#fee08b',
            'Moderada': '#91cf60',
            'Buena': '#1a9850'
        },
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

# ===== FUNCIONES DE ANÁLISIS DE SUELO =====
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
            'Franco Arcilloso': {
                'arena': 35, 'limo': 25, 'arcilla': 30,
                'textura': 'Media', 'drenaje': 'Moderado',
                'CIC': 'Alto (15-25)', 'ret_agua': 'Alta',
                'recomendacion': 'Ideal para palma'
            },
            'Franco Arcilloso Arenoso': {
                'arena': 45, 'limo': 20, 'arcilla': 25,
                'textura': 'Media-ligera', 'drenaje': 'Bueno',
                'CIC': 'Medio (10-15)', 'ret_agua': 'Moderada',
                'recomendacion': 'Requiere riego'
            },
            'Arenoso Franco': {
                'arena': 55, 'limo': 15, 'arcilla': 20,
                'textura': 'Ligera', 'drenaje': 'Excelente',
                'CIC': 'Bajo (5-10)', 'ret_agua': 'Baja',
                'recomendacion': 'Fertilización fraccionada'
            },
            'Arcilloso': {
                'arena': 25, 'limo': 20, 'arcilla': 40,
                'textura': 'Pesada', 'drenaje': 'Limitado',
                'CIC': 'Muy alto (25-35)', 'ret_agua': 'Muy alta',
                'recomendacion': 'Drenaje y labranza'
            },
            'Arcilloso Pesado': {
                'arena': 20, 'limo': 15, 'arcilla': 50,
                'textura': 'Muy pesada', 'drenaje': 'Muy limitado',
                'CIC': 'Extremo (>35)', 'ret_agua': 'Extrema',
                'recomendacion': 'Drenaje intensivo'
            },
            'Franco': {
                'arena': 40, 'limo': 40, 'arcilla': 20,
                'textura': 'Media', 'drenaje': 'Bueno',
                'CIC': 'Medio (10-20)', 'ret_agua': 'Media',
                'recomendacion': 'Manejo estándar'
            },
            'Arenoso': {
                'arena': 70, 'limo': 15, 'arcilla': 15,
                'textura': 'Ligera', 'drenaje': 'Excelente',
                'CIC': 'Muy bajo (<5)', 'ret_agua': 'Muy baja',
                'recomendacion': 'Riego frecuente'
            }
        }
        
        for idx, row in gdf_dividido.iterrows():
            centroid = row.geometry.centroid
            semilla = abs(int(centroid.x * 1000 + centroid.y * 1000)) % (2**32)
            np.random.seed(semilla)
            r = np.random.random()
            if r < 0.7:
                tipo = base
            else:
                tipo = alt_base
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
            
            if N < 100:
                rec_N = f"Aplicar {max(0, 120-N):.0f} kg/ha N"
            else:
                rec_N = "Mantener dosis actual"
            if P < 30:
                rec_P = f"Aplicar {max(0, 50-P):.0f} kg/ha P2O5"
            else:
                rec_P = "Mantener dosis actual"
            if K < 150:
                rec_K = f"Aplicar {max(0, 200-K):.0f} kg/ha K2O"
            else:
                rec_K = "Mantener dosis actual"
            
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

# ===== FUNCIÓN PRINCIPAL DE ANÁLISIS MEJORADA =====
def ejecutar_analisis_completo():
    if st.session_state.gdf_original is None:
        st.error("Primero debe cargar un archivo de plantación")
        return
    with st.spinner("Ejecutando análisis completo..."):
        n_divisiones = st.session_state.get('n_divisiones', 16)
        fecha_inicio = st.session_state.get('fecha_inicio', datetime.now() - timedelta(days=60))
        fecha_fin = st.session_state.get('fecha_fin', datetime.now())
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
            gdf_dividido = dividir_plantacion_en_bloques(gdf, n_divisiones)
            areas_ha = []
            for idx, row in gdf_dividido.iterrows():
                area_gdf = gpd.GeoDataFrame({'geometry': [row.geometry]}, crs=gdf_dividido.crs)
                areas_ha.append(float(calcular_superficie(area_gdf)))
            gdf_dividido['area_ha'] = areas_ha

            st.info("🛰️ Obteniendo NDVI desde Earthdata (MOD13Q1)...")
            resultado_ndvi = obtener_ndvi_earthdata(gdf_dividido, fecha_inicio, fecha_fin)
            if resultado_ndvi is None:
                st.error("No se pudo obtener NDVI real.")
                st.stop()
            gdf_dividido = resultado_ndvi
            fuente_ndvi = "Earthdata MOD13Q1"

            st.info("💧 Obteniendo NDWI desde Earthdata (MOD09GA)...")
            resultado_ndwi = obtener_ndwi_earthdata(gdf_dividido, fecha_inicio, fecha_fin)
            if resultado_ndwi is None:
                st.error("No se pudo obtener NDWI real.")
                st.stop()
            gdf_dividido = resultado_ndwi
            fuente_ndwi = "Earthdata MOD09GA"

            st.info("🌦️ Obteniendo datos climáticos...")
            datos_clima = obtener_clima_openmeteo(gdf, fecha_inicio, fecha_fin) or {}
            st.info("☀️ Obteniendo radiación y viento...")
            datos_power = obtener_radiacion_viento_power(gdf, fecha_inicio, fecha_fin) or {}
            st.session_state.datos_climaticos = {**datos_clima, **datos_power}

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

        # Validar calidad de datos (solo modo PREMIUM)
        if not st.session_state.demo_mode:
            problemas_calidad = validar_calidad_ndvi(gdf_dividido)
            if problemas_calidad:
                st.warning("### ⚠️ Advertencias de Calidad de Datos")
                for problema in problemas_calidad:
                    st.warning(problema)

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

# ===== ESTILOS CSS =====
st.markdown("""
<style>
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}
header {visibility: hidden !important;}
.stApp header {display: none !important;}
.stApp [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
.stAppDeployButton {display: none !important;}
[data-testid="stAppDeployButton"] {display: none !important;}
.hero-banner { 
    background: linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.98)); 
    padding: 1.5em; 
    border-radius: 15px; 
    margin-bottom: 1em; 
    border: 1px solid rgba(76, 175, 80, 0.3); 
    text-align: center; 
}
.hero-title { 
    color: #ffffff; 
    font-size: 2em; 
    font-weight: 800; 
    margin-bottom: 0.5em; 
    background: linear-gradient(135deg, #ffffff 0%, #81c784 100%); 
    -webkit-background-clip: text; 
    -webkit-text-fill-color: transparent; 
}
.stButton > button { 
    background: linear-gradient(135deg, #4caf50 0%, #2e7d32 100%) !important; 
    color: white !important; 
    border: none !important; 
    padding: 0.8em 1.5em !important; 
    border-radius: 12px !important; 
    font-weight: 700 !important; 
}
div[data-testid="metric-container"] { 
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)) !important; 
    backdrop-filter: blur(10px) !important; 
    border-radius: 18px !important; 
    padding: 22px !important; 
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35) !important; 
    border: 1px solid rgba(76, 175, 80, 0.25) !important; 
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-banner">
<h1 class="hero-title">🍇 ANALIZADOR DE VID Y OLIVO SATELITAL</h1>
<p>Monitoreo biológico con datos reales NASA Earthdata · Open-Meteo · NASA POWER</p>
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
    fecha_fin_default = datetime.now()
    fecha_inicio_default = datetime.now() - timedelta(days=60)
    fecha_fin = st.date_input("Fecha fin", fecha_fin_default)
    fecha_inicio = st.date_input("Fecha inicio", fecha_inicio_default)
    try:
        if hasattr(fecha_inicio, 'year'): fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
        if hasattr(fecha_fin, 'year'): fecha_fin = datetime.combine(fecha_fin, datetime.min.time())
    except: pass
    st.session_state.fecha_inicio = fecha_inicio
    st.session_state.fecha_fin = fecha_fin
    
    st.markdown("---")
    st.markdown("### 🎯 División de Plantación")
    n_divisiones = st.slider("Número de bloques:", 8, 32, 16)
    st.session_state.n_divisiones = n_divisiones
    
    st.markdown("---")
    st.markdown("### 🌱 Detección de Plantas")
    deteccion_habilitada = st.checkbox("Activar detección de plantas", value=True)
    if deteccion_habilitada:
        densidad_personalizada = st.slider("Densidad objetivo (plantas/ha):", 50, 200, 130)
        st.session_state.densidad_personalizada = densidad_personalizada
    
    st.markdown("---")
    st.markdown("### 🧪 Análisis de Suelo")
    analisis_suelo = st.checkbox("Activar análisis de suelo", value=True)
    if analisis_suelo:
        st.info("Incluye: Textura por bloque, fertilidad NPK, recomendaciones")
    st.session_state.analisis_suelo = analisis_suelo
    
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
        st.write(f"- **Variedad:** {st.session_state.variedad_seleccionada}")
        st.write(f"- **Bloques configurados:** {st.session_state.n_divisiones}")
        st.markdown("#### 🗺️ Vista previa del polígono")
        try:
            m_preview = folium.Map(location=[gdf.geometry.centroid.y.iloc[0], gdf.geometry.centroid.x.iloc[0]], zoom_start=15, tiles=None)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                             attr='Esri', name='Satélite').add_to(m_preview)
            folium.GeoJson(gdf.to_json(), style_function=lambda x: {'fillColor': '#3388ff', 'color': 'black', 'weight': 2, 'fillOpacity': 0.4}).add_to(m_preview)
            folium.LayerControl().add_to(m_preview)
            folium_static(m_preview, width=500, height=300)
        except Exception as e:
            st.warning(f"No se pudo mostrar el mapa: {e}")
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
1. Inicia sesión o regístrate.
2. Sube un archivo con el polígono de tu plantación.
3. Configura los parámetros de análisis.
4. Haz clic en EJECUTAR ANÁLISIS para obtener resultados.
""")
    if st.session_state.demo_mode:
        st.info("🎮 Estás en modo DEMO. Sube tu propio archivo para ejecutar el análisis con datos simulados.")

# ===== PESTAÑAS DE RESULTADOS =====
if st.session_state.analisis_completado:
    resultados = st.session_state.resultados_todos
    gdf_completo = resultados.get('gdf_completo')
    if gdf_completo is not None:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📊 Resumen", "🗺️ Mapas", "🛰️ Índices", 
            "🌤️ Clima", "🌴 Detección", "🧪 Fertilidad NPK", 
            "🌱 Textura Suelo"
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
            with col_m1:
                st.metric("Área Total", f"{area_total:.1f} ha")
            with col_m2:
                st.metric("Bloques", f"{total_bloques}")
            with col_m3:
                st.metric("Edad Prom.", f"{edad_prom:.1f} años" if not np.isnan(edad_prom) else "N/A")
            with col_m4:
                st.metric("NDVI Prom.", f"{ndvi_prom:.3f}" if not np.isnan(ndvi_prom) else "N/A")
            with col_m5:
                st.metric("NDWI Prom.", f"{ndwi_prom:.3f}" if not np.isnan(ndwi_prom) else "N/A")
            with col_m6:
                st.metric("Salud Buena", f"{pct_buena:.1f}%")
            
            st.markdown("---")
            
            # NUEVO: Estadísticas detalladas de NDVI por bloque
            st.markdown("### 📊 Estadísticas de NDVI por Bloque")
            if 'ndvi_modis' in gdf_completo.columns:
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                with col_s1:
                    st.metric("NDVI Promedio", f"{gdf_completo['ndvi_modis'].mean():.3f}")
                with col_s2:
                    st.metric("NDVI Mínimo", f"{gdf_completo['ndvi_modis'].min():.3f}")
                with col_s3:
                    st.metric("NDVI Máximo", f"{gdf_completo['ndvi_modis'].max():.3f}")
                with col_s4:
                    st.metric("NDVI Desv. Est.", f"{gdf_completo['ndvi_modis'].std():.3f}")
            
            st.markdown("---")
            
            st.markdown("#### 📋 Resumen detallado por bloque")
            try:
                columnas_tabla = ['id_bloque', 'area_ha', 'edad_anios', 'ndvi_modis', 
                                 'ndvi_min', 'ndvi_max', 'ndvi_std', 'ndwi_modis', 'salud']
                tabla = gdf_completo[columnas_tabla].copy()
                tabla.columns = ['Bloque', 'Área (ha)', 'Edad', 'NDVI', 'NDVI Min', 
                                'NDVI Max', 'NDVI σ', 'NDWI', 'Salud']
                
                def color_salud(val):
                    if val == 'Crítica':
                        return 'background-color: #d73027; color: white'
                    elif val == 'Baja':
                        return 'background-color: #fee08b'
                    elif val == 'Moderada':
                        return 'background-color: #91cf60'
                    elif val == 'Buena':
                        return 'background-color: #1a9850; color: white'
                    return ''
                
                styled_tabla = tabla.style.format({
                    'Área (ha)': '{:.2f}',
                    'Edad': '{:.1f}',
                    'NDVI': '{:.3f}',
                    'NDVI Min': '{:.3f}',
                    'NDVI Max': '{:.3f}',
                    'NDVI σ': '{:.3f}',
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
                st.warning(f"No se pudo mostrar la tabla: {e}")
        
        with tab2:
            st.subheader("🗺️ MAPAS INTERACTIVOS")
            st.markdown("### 🌍 Mapa Interactivo")
            try:
                colormap_ndvi = LinearColormap(colors=['red','yellow','green'], vmin=0.3, vmax=0.9)
                mapa_interactivo = crear_mapa_interactivo_base(
                    gdf_completo,
                    columna_color='ndvi_modis',
                    colormap=colormap_ndvi,
                    tooltip_fields=['id_bloque','ndvi_modis','salud'],
                    tooltip_aliases=['Bloque','NDVI','Salud']
                )
                if mapa_interactivo:
                    folium_static(mapa_interactivo, width=1000, height=600)
                else:
                    st.warning("No se pudo generar el mapa interactivo")
            except Exception as e:
                st.error(f"Error al mostrar mapa: {str(e)[:100]}")
        
        with tab3:
            st.subheader("🛰️ ÍNDICES DE VEGETACIÓN")
            st.caption(f"Fuente: {st.session_state.datos_modis.get('fuente', 'Earthdata')}")
            
            st.markdown("### 🌿 NDVI")
            if 'ndvi_modis' in gdf_completo.columns:
                mostrar_estadisticas_indice(gdf_completo, 'ndvi_modis', 'NDVI', 0.3, 0.9, ['red','yellow','green'])
                
                # NUEVO: Gráfico de variabilidad con barras de error
                st.markdown("#### 📈 Variabilidad de NDVI por Bloque")
                if 'ndvi_std' in gdf_completo.columns:
                    fig_var = go.Figure()
                    fig_var.add_trace(go.Bar(
                        x=gdf_completo['id_bloque'].values,
                        y=gdf_completo['ndvi_modis'].values,
                        error_y=dict(
                            type='data',
                            array=gdf_completo['ndvi_std'].values,
                            visible=True
                        ),
                        name='NDVI por bloque'
                    ))
                    fig_var.update_layout(
                        title='NDVI por Bloque con Desviación Estándar',
                        xaxis_title='Bloque',
                        yaxis_title='NDVI',
                        height=400
                    )
                    st.plotly_chart(fig_var, use_container_width=True)
            else:
                st.error("No hay datos de NDVI disponibles.")
            
            st.markdown("---")
            st.markdown("### 💧 NDWI")
            st.info("NDWI calculado como (NIR - SWIR)/(NIR+SWIR) con bandas de MODIS.")
            if 'ndwi_modis' in gdf_completo.columns:
                mostrar_estadisticas_indice(gdf_completo, 'ndwi_modis', 'NDWI', 0.1, 0.7, ['brown','yellow','blue'])
                
                # NUEVO: Gráfico de variabilidad NDWI
                st.markdown("#### 📈 Variabilidad de NDWI por Bloque")
                if 'ndwi_std' in gdf_completo.columns:
                    fig_var_ndwi = go.Figure()
                    fig_var_ndwi.add_trace(go.Bar(
                        x=gdf_completo['id_bloque'].values,
                        y=gdf_completo['ndwi_modis'].values,
                        error_y=dict(
                            type='data',
                            array=gdf_completo['ndwi_std'].values,
                            visible=True
                        ),
                        name='NDWI por bloque'
                    ))
                    fig_var_ndwi.update_layout(
                        title='NDWI por Bloque con Desviación Estándar',
                        xaxis_title='Bloque',
                        yaxis_title='NDWI',
                        height=400
                    )
                    st.plotly_chart(fig_var_ndwi, use_container_width=True)
            else:
                st.error("No hay datos de NDWI disponibles.")
            
            st.markdown("---")
            mostrar_comparacion_ndvi_ndwi(gdf_completo)
        
        with tab4:
            st.subheader("🌤️ DATOS CLIMÁTICOS")
            datos_climaticos = st.session_state.datos_climaticos
            if datos_climaticos:
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Precipitación total", f"{datos_climaticos['precipitacion']['total']} mm")
                with col2: st.metric("Días con lluvia", f"{datos_climaticos['precipitacion']['dias_con_lluvia']} días")
                with col3: st.metric("Temperatura promedio", f"{datos_climaticos['temperatura']['promedio']}°C")
                with col4: st.metric("Radiación promedio", f"{datos_climaticos.get('radiacion',{}).get('promedio', 'N/A')} MJ/m²")
            else:
                st.info("No hay datos climáticos disponibles")
        
        with tab5:
            st.subheader("🌴 DETECCIÓN DE PLANTAS")
            if st.session_state.deteccion_ejecutada and st.session_state.palmas_detectadas:
                palmas = st.session_state.palmas_detectadas
                total = len(palmas)
                area_total_val = resultados.get('area_total', 0)
                densidad = total / area_total_val if area_total_val > 0 else 0
                st.success(f"✅ Detección completada: {total} plantas detectadas")
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Plantas detectadas", f"{total:,}")
                with col2: st.metric("Densidad", f"{densidad:.0f} plantas/ha")
                with col3: st.metric("Área promedio", f"{np.mean([p.get('area_m2',0) for p in palmas]):.1f} m²")
                with col4: st.metric("Diámetro promedio", f"{np.mean([p.get('diametro_aprox',0) for p in palmas]):.1f} m")
            else:
                st.info("La detección no se ha ejecutado aún.")
                if st.button("🔍 EJECUTAR DETECCIÓN", key="detectar_palmas_tab5", use_container_width=True):
                    ejecutar_deteccion_plantas()
                    st.rerun()
        
        with tab6:
            st.subheader("🧪 FERTILIDAD DEL SUELO")
            datos_fertilidad = st.session_state.datos_fertilidad
            if datos_fertilidad:
                df_fertilidad = pd.DataFrame(datos_fertilidad)
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1: st.metric("Nitrógeno (N)", f"{df_fertilidad['N_kg_ha'].mean():.0f} kg/ha")
                with col2: st.metric("Fósforo (P₂O₅)", f"{df_fertilidad['P_kg_ha'].mean():.0f} kg/ha")
                with col3: st.metric("Potasio (K₂O)", f"{df_fertilidad['K_kg_ha'].mean():.0f} kg/ha")
                with col4: st.metric("pH", f"{df_fertilidad['pH'].mean():.2f}")
                with col5: st.metric("Materia Orgánica", f"{df_fertilidad['MO_porcentaje'].mean():.1f}%")
            else:
                st.info("Ejecute el análisis completo para ver los datos de fertilidad.")
        
        with tab7:
            st.subheader("🌱 ANÁLISIS DE TEXTURA DE SUELO")
            textura_por_bloque = st.session_state.get('textura_por_bloque', [])
            if textura_por_bloque:
                df_textura = pd.DataFrame(textura_por_bloque)
                st.success(f"**Análisis de textura por bloque completado**")
                st.dataframe(df_textura[['id_bloque','tipo_suelo','arena','limo','arcilla','drenaje']].head(20))
            else:
                st.info("Ejecute el análisis completo para ver el análisis de textura.")

# ===== PIE DE PÁGINA =====
st.markdown("---")
st.markdown("""
© 2026 Analizador de Palma Aceitera Satelital
Datos satelitales: NASA Earthdata · Clima: Open-Meteo ERA5 · Radiación/Viento: NASA POWER
Desarrollado por: BioMap Consultora | Contacto: mawucano@gmail.com
""", unsafe_allow_html=True)
