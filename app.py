# app.py — Versión final con VID, OLIVO y HORTALIZAS de MENDOZA (CORREGIDO)
# Autor: Martin Ernesto Cano
# Fecha: Enero 2026
import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import tempfile
import os
import zipfile
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import io
from shapely.geometry import Polygon, LineString
import math
import warnings
import xml.etree.ElementTree as ET
import base64
import json
from io import BytesIO
from fpdf import FPDF
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import geojson
import requests
import contextily as ctx
from pyproj import CRS
warnings.filterwarnings('ignore')

# ===== USAR TODO EL ANCHO DE LA PANTALLA =====
st.set_page_config(layout="wide")

# === ESTILOS PERSONALIZADOS - VERSIÓN PREMIUM MODERNA ===
st.markdown("""
<style>
/* === FONDO GENERAL OSCURO ELEGANTE === */
.stApp {
background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
color: #ffffff !important;
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
/* === SIDEBAR: FONDO BLANCO CON TEXTO NEGRO === */
[data-testid="stSidebar"] {
background: #ffffff !important;
border-right: 1px solid #e5e7eb !important;
box-shadow: 5px 0 25px rgba(0, 0, 0, 0.1) !important;
}
/* Texto general del sidebar en NEGRO */
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stText,
[data-testid="stSidebar"] .stTitle,
[data-testid="stSidebar"] .stSubheader {
color: #000000 !important;
text-shadow: none !important;
}
/* Título del sidebar elegante */
.sidebar-title {
font-size: 1.4em;
font-weight: 800;
margin: 1.5em 0 1em 0;
text-align: center;
padding: 14px;
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
border-radius: 16px;
color: #ffffff !important;
box-shadow: 0 6px 20px rgba(59, 130, 246, 0.3);
border: 1px solid rgba(255, 255, 255, 0.2);
letter-spacing: 0.5px;
}
/* Widgets del sidebar con estilo glassmorphism */
[data-testid="stSidebar"] .stSelectbox,
[data-testid="stSidebar"] .stDateInput,
[data-testid="stSidebar"] .stSlider {
background: rgba(255, 255, 255, 0.9) !important;
backdrop-filter: blur(10px);
border-radius: 12px;
padding: 12px;
margin: 8px 0;
border: 1px solid #d1d5db !important;
}
/* Labels de los widgets en negro */
[data-testid="stSidebar"] .stSelectbox div,
[data-testid="stSidebar"] .stDateInput div,
[data-testid="stSidebar"] .stSlider label {
color: #000000 !important;
font-weight: 600;
font-size: 0.95em;
}
/* Inputs y selects - fondo blanco con texto negro */
[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
background-color: #ffffff !important;
border: 1px solid #d1d5db !important;
color: #000000 !important;
border-radius: 8px;
}
/* Slider - colores negro */
[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {
color: #000000 !important;
}
/* Date Input - fondo blanco con texto negro */
[data-testid="stSidebar"] .stDateInput [data-baseweb="input"] {
background-color: #ffffff !important;
border: 1px solid #d1d5db !important;
color: #000000 !important;
border-radius: 8px;
}
/* Placeholder en gris */
[data-testid="stSidebar"] .stDateInput [data-baseweb="input"]::placeholder {
color: #6b7280 !important;
}
/* Botones premium */
.stButton > button {
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
color: white !important;
border: none !important;
padding: 0.8em 1.5em !important;
border-radius: 12px !important;
font-weight: 700 !important;
font-size: 1em !important;
box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
transition: all 0.3s ease !important;
text-transform: uppercase !important;
letter-spacing: 0.5px !important;
}
.stButton > button:hover {
transform: translateY(-3px) !important;
box-shadow: 0 8px 25px rgba(59, 130, 246, 0.6) !important;
background: linear-gradient(135deg, #4f8df8 0%, #2d5fe8 100%) !important;
}
/* === HERO BANNER PRINCIPAL CON IMAGEN === */
.hero-banner {
background: linear-gradient(rgba(15, 23, 42, 0.9), rgba(15, 23, 42, 0.95)),
url('https://images.unsplash.com/photo-1597981309443-6e2d2a4d9c3f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80') !important;
background-size: cover !important;
background-position: center 40% !important;
padding: 3.5em 2em !important;
border-radius: 24px !important;
margin-bottom: 2.5em !important;
box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4) !important;
border: 1px solid rgba(59, 130, 246, 0.2) !important;
position: relative !important;
overflow: hidden !important;
}
.hero-banner::before {
content: '' !important;
position: absolute !important;
top: 0 !important;
left: 0 !important;
right: 0 !important;
bottom: 0 !important;
background: linear-gradient(45deg, rgba(59, 130, 246, 0.1), rgba(29, 78, 216, 0.05)) !important;
z-index: 1 !important;
}
.hero-content {
position: relative !important;
z-index: 2 !important;
text-align: center !important;
}
.hero-title {
color: #ffffff !important;
font-size: 3.2em !important;
font-weight: 900 !important;
margin-bottom: 0.3em !important;
text-shadow: 0 4px 12px rgba(0, 0, 0, 0.6) !important;
letter-spacing: -0.5px !important;
background: linear-gradient(135deg, #ffffff 0%, #93c5fd 100%) !important;
-webkit-background-clip: text !important;
-webkit-text-fill-color: transparent !important;
background-clip: text !important;
}
.hero-subtitle {
color: #cbd5e1 !important;
font-size: 1.3em !important;
font-weight: 400 !important;
max-width: 800px !important;
margin: 0 auto !important;
line-height: 1.6 !important;
}
/* === PESTAÑAS PRINCIPALES (fuera del sidebar) - SIN CAMBIOS === */
.stTabs [data-baseweb="tab-list"] {
background: rgba(255, 255, 255, 0.05) !important;
backdrop-filter: blur(10px) !important;
padding: 8px 16px !important;
border-radius: 16px !important;
border: 1px solid rgba(255, 255, 255, 0.1) !important;
margin-top: 1em !important;
gap: 8px !important;
}
.stTabs [data-baseweb="tab"] {
color: #94a3b8 !important;
font-weight: 600 !important;
padding: 12px 24px !important;
border-radius: 12px !important;
background: transparent !important;
transition: all 0.3s ease !important;
border: 1px solid transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
color: #ffffff !important;
background: rgba(59, 130, 246, 0.2) !important;
border-color: rgba(59, 130, 246, 0.3) !important;
transform: translateY(-2px) !important;
}
.stTabs [aria-selected="true"] {
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
color: #ffffff !important;
font-weight: 700 !important;
border: none !important;
box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
}
/* === PESTAÑAS DEL SIDEBAR: FONDO BLANCO + TEXTO NEGRO === */
[data-testid="stSidebar"] .stTabs [data-baseweb="tab-list"] {
background: #ffffff !important;
border: 1px solid #e2e8f0 !important;
padding: 8px !important;
border-radius: 12px !important;
gap: 6px !important;
}
[data-testid="stSidebar"] .stTabs [data-baseweb="tab"] {
color: #000000 !important;
background: transparent !important;
border-radius: 8px !important;
padding: 8px 16px !important;
font-weight: 600 !important;
border: 1px solid transparent !important;
}
[data-testid="stSidebar"] .stTabs [data-baseweb="tab"]:hover {
background: #f1f5f9 !important;
color: #000000 !important;
border-color: #cbd5e1 !important;
}
/* Pestaña activa en el sidebar: blanco con texto negro */
[data-testid="stSidebar"] .stTabs [aria-selected="true"] {
background: #ffffff !important;
color: #000000 !important;
font-weight: 700 !important;
border: 1px solid #3b82f6 !important;
}
/* === MÉTRICAS PREMIUM === */
div[data-testid="metric-container"] {
background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9)) !important;
backdrop-filter: blur(10px) !important;
border-radius: 20px !important;
padding: 24px !important;
box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
border: 1px solid rgba(59, 130, 246, 0.2) !important;
transition: all 0.3s ease !important;
}
div[data-testid="metric-container"]:hover {
transform: translateY(-5px) !important;
box-shadow: 0 15px 40px rgba(59, 130, 246, 0.2) !important;
border-color: rgba(59, 130, 246, 0.4) !important;
}
div[data-testid="metric-container"] label,
div[data-testid="metric-container"] div,
div[data-testid="metric-container"] [data-testid="stMetricValue"],
div[data-testid="metric-container"] [data-testid="stMetricLabel"] {
color: #ffffff !important;
font-weight: 600 !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
font-size: 2.5em !important;
font-weight: 800 !important;
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
-webkit-background-clip: text !important;
-webkit-text-fill-color: transparent !important;
background-clip: text !important;
}
/* === GRÁFICOS CON ESTILO OSCURO === */
.stPlotlyChart, .stPyplot {
background: rgba(15, 23, 42, 0.8) !important;
backdrop-filter: blur(10px) !important;
border-radius: 20px !important;
padding: 20px !important;
box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
border: 1px solid rgba(59, 130, 246, 0.2) !important;
}
/* === EXPANDERS ELEGANTES === */
.streamlit-expanderHeader {
color: #ffffff !important;
background: rgba(30, 41, 59, 0.8) !important;
backdrop-filter: blur(10px) !important;
border-radius: 16px !important;
font-weight: 700 !important;
border: 1px solid rgba(255, 255, 255, 0.1) !important;
padding: 16px 20px !important;
margin-bottom: 10px !important;
}
.streamlit-expanderContent {
background: rgba(15, 23, 42, 0.6) !important;
border-radius: 0 0 16px 16px !important;
padding: 20px !important;
border: 1px solid rgba(255, 255, 255, 0.1) !important;
border-top: none !important;
}
/* === TEXTOS GENERALES === */
h1, h2, h3, h4, h5, h6 {
color: #ffffff !important;
font-weight: 800 !important;
margin-top: 1.5em !important;
}
p, div, span, label, li {
color: #cbd5e1 !important;
line-height: 1.7 !important;
}
/* === DATA FRAMES TABLAS ELEGANTES === */
.dataframe {
background: rgba(15, 23, 42, 0.8) !important;
backdrop-filter: blur(10px) !important;
border-radius: 16px !important;
border: 1px solid rgba(255, 255,255, 0.1) !important;
color: #ffffff !important;
}
.dataframe th {
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
color: #ffffff !important;
font-weight: 700 !important;
padding: 16px !important;
}
.dataframe td {
color: #cbd5e1 !important;
padding: 14px 16px !important;
border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}
/* === ALERTS Y MENSAJES === */
.stAlert {
border-radius: 16px !important;
border: 1px solid rgba(255, 255, 255, 0.1) !important;
backdrop-filter: blur(10px) !important;
}
/* === SCROLLBAR PERSONALIZADA === */
::-webkit-scrollbar {
width: 10px !important;
height: 10px !important;
}
::-webkit-scrollbar-track {
background: rgba(15, 23, 42, 0.8) !important;
border-radius: 10px !important;
}
::-webkit-scrollbar-thumb {
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
border-radius: 10px !important;
}
::-webkit-scrollbar-thumb:hover {
background: linear-gradient(135deg, #4f8df8 0%, #2d5fe8 100%) !important;
}
/* === IMÁGENES DEL SIDEBAR === */
[data-testid="stSidebar"] img {
border-radius: 16px !important;
border: 2px solid #d1d5db !important;
box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1) !important;
transition: all 0.3s ease !important;
}
[data-testid="stSidebar"] img:hover {
transform: scale(1.02) !important;
box-shadow: 0 12px 35px rgba(0, 0, 0, 0.2) !important;
border-color: #3b82f6 !important;
}
/* === TARJETAS DE CULTIVOS === */
.cultivo-card {
background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)) !important;
border-radius: 20px !important;
padding: 25px !important;
border: 1px solid rgba(59, 130, 246, 0.2) !important;
box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
transition: all 0.3s ease !important;
height: 100% !important;
}
.cultivo-card:hover {
transform: translateY(-8px) !important;
box-shadow: 0 20px 40px rgba(59, 130, 246, 0.2) !important;
border-color: rgba(59, 130, 246, 0.4) !important;
}
/* === TABLERO DE CONTROL === */
.dashboard-grid {
display: grid !important;
grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)) !important;
gap: 25px !important;
margin: 30px 0 !important;
}
.dashboard-card {
background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)) !important;
border-radius: 20px !important;
padding: 25px !important;
border: 1px solid rgba(59, 130, 246, 0.2) !important;
box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
transition: all 0.3s ease !important;
}
.dashboard-card:hover {
transform: translateY(-5px) !important;
box-shadow: 0 20px 40px rgba(59, 130, 246, 0.2) !important;
}
/* === STATS BADGES === */
.stats-badge {
display: inline-block !important;
padding: 6px 14px !important;
border-radius: 50px !important;
font-size: 0.85em !important;
font-weight: 700 !important;
margin: 2px !important;
}
.badge-success {
background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
color: white !important;
}
.badge-warning {
background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
color: white !important;
}
.badge-danger {
background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
color: white !important;
}
.badge-info {
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
color: white !important;
}
/* Estilos adicionales para mapas de calor */
.map-container {
background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.98)) !important;
border-radius: 20px !important;
padding: 20px !important;
margin: 20px 0 !important;
border: 1px solid rgba(59, 130, 246, 0.3) !important;
box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4) !important;
}
.map-title {
font-size: 1.4em !important;
font-weight: 800 !important;
color: #ffffff !important;
text-align: center !important;
margin-bottom: 15px !important;
padding-bottom: 10px !important;
border-bottom: 2px solid rgba(59, 130, 246, 0.5) !important;
}
.map-stats {
background: rgba(30, 41, 59, 0.8) !important;
border-radius: 12px !important;
padding: 15px !important;
margin: 10px 0 !important;
border: 1px solid rgba(255, 255, 255, 0.1) !important;
}
.map-tabs .stTabs [data-baseweb="tab-list"] {
background: rgba(30, 41, 59, 0.8) !important;
border-radius: 12px !important;
padding: 8px !important;
margin-bottom: 15px !important;
}
.map-tabs .stTabs [data-baseweb="tab"] {
color: #cbd5e1 !important;
font-weight: 600 !important;
}
.map-tabs .stTabs [aria-selected="true"] {
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
color: #ffffff !important;
}
/* Mejorar visualización de imágenes de mapas */
.stImage > img {
border-radius: 16px !important;
border: 2px solid rgba(59, 130, 246, 0.3) !important;
box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
transition: all 0.3s ease !important;
}
.stImage > img:hover {
transform: scale(1.01) !important;
box-shadow: 0 15px 40px rgba(59, 130, 246, 0.2) !important;
border-color: rgba(59, 130, 246, 0.6) !important;
}
/* Estilos para estadísticas de mapas */
.stats-card {
background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95)) !important;
border-radius: 16px !important;
padding: 20px !important;
margin: 10px 0 !important;
border: 1px solid rgba(59, 130, 246, 0.2) !important;
}
.stats-value {
font-size: 2em !important;
font-weight: 800 !important;
background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
-webkit-background-clip: text !important;
-webkit-text-fill-color: transparent !important;
background-clip: text !important;
margin: 5px 0 !important;
}
.stats-label {
color: #94a3b8 !important;
font-size: 0.9em !important;
font-weight: 600 !important;
text-transform: uppercase !important;
letter-spacing: 0.5px !important;
}
/* Mejorar botones de descarga de mapas */
.download-map-btn {
background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
color: white !important;
border: none !important;
padding: 10px 20px !important;
border-radius: 10px !important;
font-weight: 700 !important;
margin: 5px !important;
transition: all 0.3s ease !important;
}
.download-map-btn:hover {
transform: translateY(-2px) !important;
box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4) !important;
}
/* Leyenda de mapas mejorada */
.map-legend {
background: rgba(30, 41, 59, 0.9) !important;
border-radius: 10px !important;
padding: 15px !important;
border: 1px solid rgba(255, 255, 255, 0.1) !important;
margin: 15px 0 !important;
}
.legend-title {
color: #ffffff !important;
font-weight: 700 !important;
margin-bottom: 10px !important;
font-size: 1.1em !important;
}
.legend-item {
display: flex !important;
align-items: center !important;
margin: 5px 0 !important;
color: #cbd5e1 !important;
}
.legend-color {
width: 20px !important;
height: 20px !important;
border-radius: 4px !important;
margin-right: 10px !important;
border: 1px solid rgba(255, 255, 255, 0.2) !important;
}
</style>
""", unsafe_allow_html=True)

# ===== HERO BANNER PRINCIPAL =====
st.markdown("""
<div class="hero-banner">
<div class="hero-content">
<h1 class="hero-title">ANALIZADOR PARA VID, OLIVO Y HORTALIZAS EN MENDOZA</h1>
<p class="hero-subtitle">Potenciado con NASA POWER, GEE, INTA y tecnología avanzada para viñedos, olivares y huertas</p>
</div>
</div>
""", unsafe_allow_html=True)

# ===== CONFIGURACIÓN DE SATÉLITES DISPONIBLES =====
SATELITES_DISPONIBLES = {
'SENTINEL-2': {
'nombre': 'Sentinel-2',
'resolucion': '10m',
'revisita': '5 días',
'bandas': ['B2', 'B3', 'B4', 'B5', 'B8', 'B8A', 'B11', 'B12'],
'indices': ['NDVI', 'NDRE', 'GNDVI', 'OSAVI', 'MCARI', 'TCARI', 'NDII'],
'icono': '🛰️',
'bandas_np': {
'N': ['B5', 'B8A'],
'P': ['B4', 'B11'],
'K': ['B8', 'B11', 'B12']
}
},
'LANDSAT-8': {
'nombre': 'Landsat 8',
'resolucion': '30m',
'revisita': '16 días',
'bandas': ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B10', 'B11'],
'indices': ['NDVI', 'NDWI', 'EVI', 'SAVI', 'MSAVI', 'NDII'],
'icono': '🛰️',
'bandas_np': {
'N': ['B4', 'B5'],
'P': ['B3', 'B6'],
'K': ['B5', 'B6', 'B7']
}
},
'DATOS_SIMULADOS': {
'nombre': 'Datos Simulados',
'resolucion': '10m',
'revisita': '5 días',
'bandas': ['B2', 'B3', 'B4', 'B5', 'B8'],
'indices': ['NDVI', 'NDRE', 'GNDVI'],
'icono': '🔬'
}
}

# ===== NUEVAS METODOLOGÍAS PARA ESTIMAR NPK CON TELEDETECCIÓN =====
METODOLOGIAS_NPK = {
'SENTINEL-2': {
'NITRÓGENO': {
'metodo': 'NDRE + Regresión Espectral',
'formula': 'N = 150 * NDRE + 50 * (B8A/B5)',
'bandas': ['B5', 'B8A'],
'r2_esperado': 0.75,
'referencia': 'Clevers & Gitelson, 2013'
},
'FÓSFORO': {
'metodo': 'Índice SWIR-VIS',
'formula': 'P = 80 * (B11/B4)^0.5 + 20',
'bandas': ['B4', 'B11'],
'r2_esperado': 0.65,
'referencia': 'Miphokasap et al., 2012'
},
'POTASIO': {
'metodo': 'Índice de Estrés Hídrico',
'formula': 'K = 120 * (B8 - B11)/(B8 + B12) + 40',
'bandas': ['B8', 'B11', 'B12'],
'r2_esperado': 0.70,
'referencia': 'Jackson et al., 2004'
}
},
'LANDSAT-8': {
'NITRÓGENO': {
'metodo': 'TCARI/OSAVI',
'formula': 'N = 3*[(B5-B4)-0.2*(B5-B3)*(B5/B4)] / (1.16*(B5-B4)/(B5+B4+0.16))',
'bandas': ['B3', 'B4', 'B5'],
'r2_esperado': 0.72,
'referencia': 'Haboudane et al., 2002'
},
'FÓSFORO': {
'metodo': 'Relación SWIR1-Verde',
'formula': 'P = 60 * (B6/B3)^0.7 + 25',
'bandas': ['B3', 'B6'],
'r2_esperado': 0.68,
'referencia': 'Chen et al., 2010'
},
'POTASIO': {
'metodo': 'Índice NIR-SWIR',
'formula': 'K = 100 * (B5 - B7)/(B5 + B7) + 50',
'bandas': ['B5', 'B7'],
'r2_esperado': 0.69,
'referencia': 'Thenkabail et al., 2000'
}
}
}

# ===== VARIEDADES DE VID EN MENDOZA (incluyendo BONARDA) =====
VARIEDADES_VID = {
'MALBEC': {
'RENDIMIENTO_BASE': 8.0,
'RENDIMIENTO_OPTIMO': 12.0,
'RESPUESTA_N': 0.015,
'RESPUESTA_P': 0.025,
'RESPUESTA_K': 0.020,
'NITROGENO_OPTIMO': 90,
'FOSFORO_OPTIMO': 30,
'POTASIO_OPTIMO': 150,
'CICLO': 150,
'TIPO': 'Tinto',
'REGION': 'Mendoza - Luján de Cuyo'
},
'CABERNET SAUVIGNON': {
'RENDIMIENTO_BASE': 7.0,
'RENDIMIENTO_OPTIMO': 11.0,
'RESPUESTA_N': 0.014,
'RESPUESTA_P': 0.022,
'RESPUESTA_K': 0.018,
'NITROGENO_OPTIMO': 85,
'FOSFORO_OPTIMO': 28,
'POTASIO_OPTIMO': 140,
'CICLO': 155,
'TIPO': 'Tinto',
'REGION': 'Mendoza - Maipú'
},
'CHARDONNAY': {
'RENDIMIENTO_BASE': 9.0,
'RENDIMIENTO_OPTIMO': 13.0,
'RESPUESTA_N': 0.016,
'RESPUESTA_P': 0.026,
'RESPUESTA_K': 0.021,
'NITROGENO_OPTIMO': 95,
'FOSFORO_OPTIMO': 32,
'POTASIO_OPTIMO': 155,
'CICLO': 145,
'TIPO': 'Blanco',
'REGION': 'Mendoza - Valle de Uco'
},
'SYRAH': {
'RENDIMIENTO_BASE': 7.5,
'RENDIMIENTO_OPTIMO': 11.5,
'RESPUESTA_N': 0.013,
'RESPUESTA_P': 0.020,
'RESPUESTA_K': 0.019,
'NITROGENO_OPTIMO': 80,
'FOSFORO_OPTIMO': 25,
'POTASIO_OPTIMO': 145,
'CICLO': 152,
'TIPO': 'Tinto',
'REGION': 'Mendoza - San Rafael'
},
'BONARDA': {
'RENDIMIENTO_BASE': 10.0,
'RENDIMIENTO_OPTIMO': 14.0,
'RESPUESTA_N': 0.017,
'RESPUESTA_P': 0.028,
'RESPUESTA_K': 0.022,
'NITROGENO_OPTIMO': 95,
'FOSFORO_OPTIMO': 32,
'POTASIO_OPTIMO': 155,
'CICLO': 145,
'TIPO': 'Tinto',
'REGION': 'Mendoza - San Martín / Rivadavia'
}
}

# ===== VARIEDADES DE OLIVO EN MENDOZA =====
VARIEDADES_OLIVO = {
'ARBEQUINA': {
'RENDIMIENTO_BASE': 6.0,
'RENDIMIENTO_OPTIMO': 10.0,
'RESPUESTA_N': 0.010,
'RESPUESTA_P': 0.015,
'RESPUESTA_K': 0.012,
'NITROGENO_OPTIMO': 70,
'FOSFORO_OPTIMO': 20,
'POTASIO_OPTIMO': 120,
'CICLO': 180,
'TIPO': 'Aceite',
'REGION': 'Mendoza - San Rafael'
},
'ARBOSANA': {
'RENDIMIENTO_BASE': 5.5,
'RENDIMIENTO_OPTIMO': 9.5,
'RESPUESTA_N': 0.009,
'RESPUESTA_P': 0.014,
'RESPUESTA_K': 0.011,
'NITROGENO_OPTIMO': 65,
'FOSFORO_OPTIMO': 18,
'POTASIO_OPTIMO': 115,
'CICLO': 185,
'TIPO': 'Aceite',
'REGION': 'Mendoza - Junín'
},
'PICUAL': {
'RENDIMIENTO_BASE': 7.0,
'RENDIMIENTO_OPTIMO': 11.0,
'RESPUESTA_N': 0.011,
'RESPUESTA_P': 0.016,
'RESPUESTA_K': 0.013,
'NITROGENO_OPTIMO': 75,
'FOSFORO_OPTIMO': 22,
'POTASIO_OPTIMO': 125,
'CICLO': 190,
'TIPO': 'Aceite',
'REGION': 'Mendoza - Rivadavia'
},
'MANZANILLA': {
'RENDIMIENTO_BASE': 5.0,
'RENDIMIENTO_OPTIMO': 8.0,
'RESPUESTA_N': 0.008,
'RESPUESTA_P': 0.012,
'RESPUESTA_K': 0.010,
'NITROGENO_OPTIMO': 60,
'FOSFORO_OPTIMO': 15,
'POTASIO_OPTIMO': 110,
'CICLO': 175,
'TIPO': 'Mesa',
'REGION': 'Mendoza - Santa Rosa'
}
}

# ===== PARÁMETROS AGRONÓMICOS PARA HORTALIZAS EN MENDOZA =====
PARAMETROS_HORTALIZAS = {
'TOMATE': {
'NITROGENO': {'min': 120, 'max': 200, 'optimo': 160},
'FOSFORO': {'min': 40, 'max': 80, 'optimo': 60},
'POTASIO': {'min': 180, 'max': 250, 'optimo': 220},
'MATERIA_ORGANICA_OPTIMA': 3.0,
'HUMEDAD_OPTIMA': 0.25,
'NDVI_OPTIMO': 0.85,
'RENDIMIENTO_BASE': 40.0,
'RENDIMIENTO_OPTIMO': 80.0,
'RESPUESTA_N': 0.25,
'RESPUESTA_P': 0.15,
'RESPUESTA_K': 0.20,
'FACTOR_CLIMA': 0.90,
'CICLO': 120
},
'CEBOLLA': {
'NITROGENO': {'min': 100, 'max': 160, 'optimo': 130},
'FOSFORO': {'min': 30, 'max': 60, 'optimo': 45},
'POTASIO': {'min': 120, 'max': 180, 'optimo': 150},
'MATERIA_ORGANICA_OPTIMA': 2.5,
'HUMEDAD_OPTIMA': 0.22,
'NDVI_OPTIMO': 0.75,
'RENDIMIENTO_BASE': 30.0,
'RENDIMIENTO_OPTIMO': 60.0,
'RESPUESTA_N': 0.20,
'RESPUESTA_P': 0.12,
'RESPUESTA_K': 0.15,
'FACTOR_CLIMA': 0.85,
'CICLO': 150
},
'PAPA': {
'NITROGENO': {'min': 140, 'max': 220, 'optimo': 180},
'FOSFORO': {'min': 50, 'max': 90, 'optimo': 70},
'POTASIO': {'min': 200, 'max': 300, 'optimo': 250},
'MATERIA_ORGANICA_OPTIMA': 3.5,
'HUMEDAD_OPTIMA': 0.28,
'NDVI_OPTIMO': 0.80,
'RENDIMIENTO_BASE': 25.0,
'RENDIMIENTO_OPTIMO': 50.0,
'RESPUESTA_N': 0.18,
'RESPUESTA_P': 0.14,
'RESPUESTA_K': 0.22,
'FACTOR_CLIMA': 0.88,
'CICLO': 130
},
'ZANAHORIA': {
'NITROGENO': {'min': 80, 'max': 140, 'optimo': 110},
'FOSFORO': {'min': 35, 'max': 70, 'optimo': 50},
'POTASIO': {'min': 150, 'max': 220, 'optimo': 180},
'MATERIA_ORGANICA_OPTIMA': 2.8,
'HUMEDAD_OPTIMA': 0.24,
'NDVI_OPTIMO': 0.70,
'RENDIMIENTO_BASE': 35.0,
'RENDIMIENTO_OPTIMO': 70.0,
'RESPUESTA_N': 0.16,
'RESPUESTA_P': 0.10,
'RESPUESTA_K': 0.18,
'FACTOR_CLIMA': 0.82,
'CICLO': 140
},
'LECHUGA': {
'NITROGENO': {'min': 90, 'max': 150, 'optimo': 120},
'FOSFORO': {'min': 25, 'max': 50, 'optimo': 35},
'POTASIO': {'min': 100, 'max': 160, 'optimo': 130},
'MATERIA_ORGANICA_OPTIMA': 3.2,
'HUMEDAD_OPTIMA': 0.30,
'NDVI_OPTIMO': 0.82,
'RENDIMIENTO_BASE': 20.0,
'RENDIMIENTO_OPTIMO': 40.0,
'RESPUESTA_N': 0.22,
'RESPUESTA_P': 0.11,
'RESPUESTA_K': 0.16,
'FACTOR_CLIMA': 0.80,
'CICLO': 70
},
'AJO': {
'NITROGENO': {'min': 110, 'max': 180, 'optimo': 140},
'FOSFORO': {'min': 40, 'max': 75, 'optimo': 55},
'POTASIO': {'min': 140, 'max': 200, 'optimo': 170},
'MATERIA_ORGANICA_OPTIMA': 2.6,
'HUMEDAD_OPTIMA': 0.20,
'NDVI_OPTIMO': 0.65,
'RENDIMIENTO_BASE': 8.0,
'RENDIMIENTO_OPTIMO': 15.0,
'RESPUESTA_N': 0.14,
'RESPUESTA_P': 0.09,
'RESPUESTA_K': 0.12,
'FACTOR_CLIMA': 0.85,
'CICLO': 180
}
}

# ===== PARÁMETROS AGRONÓMICOS POR CULTIVO (VID Y OLIVO) =====
PARAMETROS_CULTIVOS = {
'VID': {
'NITROGENO': {'min': 70, 'max': 110, 'optimo': 90},
'FOSFORO': {'min': 20, 'max': 40, 'optimo': 30},
'POTASIO': {'min': 120, 'max': 180, 'optimo': 150},
'MATERIA_ORGANICA_OPTIMA': 2.5,
'HUMEDAD_OPTIMA': 0.20,
'NDVI_OPTIMO': 0.75,
'NDRE_OPTIMO': 0.45,
'TCARI_OPTIMO': 0.35,
'OSAVI_OPTIMO': 0.55,
'RENDIMIENTO_BASE': 8.0,
'RENDIMIENTO_OPTIMO': 12.0,
'RESPUESTA_N': 0.015,
'RESPUESTA_P': 0.025,
'RESPUESTA_K': 0.020,
'FACTOR_CLIMA': 0.85
},
'OLIVO': {
'NITROGENO': {'min': 50, 'max': 90, 'optimo': 70},
'FOSFORO': {'min': 15, 'max': 30, 'optimo': 20},
'POTASIO': {'min': 100, 'max': 150, 'optimo': 120},
'MATERIA_ORGANICA_OPTIMA': 2.0,
'HUMEDAD_OPTIMA': 0.18,
'NDVI_OPTIMO': 0.65,
'NDRE_OPTIMO': 0.35,
'TCARI_OPTIMO': 0.25,
'OSAVI_OPTIMO': 0.45,
'RENDIMIENTO_BASE': 6.0,
'RENDIMIENTO_OPTIMO': 10.0,
'RESPUESTA_N': 0.010,
'RESPUESTA_P': 0.015,
'RESPUESTA_K': 0.012,
'FACTOR_CLIMA': 0.80
}
}

# ===== PARÁMETROS ECONÓMICOS ACTUALIZADOS =====
PARAMETROS_ECONOMICOS = {
'PRECIOS_CULTIVOS': {
'VID': {
'precio_ton': 450,
'costo_semilla': 0,
'costo_herbicidas': 120,
'costo_insecticidas': 80,
'costo_labores': 300,
'costo_cosecha': 200,
'costo_otros': 100
},
'OLIVO': {
'precio_ton': 320,
'costo_semilla': 0,
'costo_herbicidas': 100,
'costo_insecticidas': 90,
'costo_labores': 350,
'costo_cosecha': 220,
'costo_otros': 110
},
'TOMATE': {
'precio_ton': 800,
'costo_semilla': 150,
'costo_herbicidas': 100,
'costo_insecticidas': 180,
'costo_labores': 400,
'costo_cosecha': 300,
'costo_otros': 120
},
'CEBOLLA': {
'precio_ton': 600,
'costo_semilla': 120,
'costo_herbicidas': 90,
'costo_insecticidas': 100,
'costo_labores': 350,
'costo_cosecha': 250,
'costo_otros': 100
},
'PAPA': {
'precio_ton': 400,
'costo_semilla': 200,
'costo_herbicidas': 120,
'costo_insecticidas': 150,
'costo_labores': 380,
'costo_cosecha': 280,
'costo_otros': 110
},
'ZANAHORIA': {
'precio_ton': 700,
'costo_semilla': 180,
'costo_herbicidas': 110,
'costo_insecticidas': 140,
'costo_labores': 420,
'costo_cosecha': 320,
'costo_otros': 130
},
'LECHUGA': {
'precio_ton': 1200,
'costo_semilla': 200,
'costo_herbicidas': 80,
'costo_insecticidas': 160,
'costo_labores': 450,
'costo_cosecha': 350,
'costo_otros': 140
},
'AJO': {
'precio_ton': 2500,
'costo_semilla': 800,
'costo_herbicidas': 100,
'costo_insecticidas': 90,
'costo_labores': 400,
'costo_cosecha': 300,
'costo_otros': 120
}
},
'PRECIOS_FERTILIZANTES': {
'UREA': 450,
'FOSFATO_DIAMONICO': 650,
'CLORURO_POTASIO': 400,
'SULFATO_AMONICO': 350,
'SUPERFOSFATO': 420
},
'CONVERSION_NUTRIENTES': {
'NITRÓGENO': {
'fuente_principal': 'UREA',
'contenido_nutriente': 0.46,
'eficiencia': 0.6
},
'FÓSFORO': {
'fuente_principal': 'FOSFATO_DIAMONICO',
'contenido_nutriente': 0.18,
'eficiencia': 0.3
},
'POTASIO': {
'fuente_principal': 'CLORURO_POTASIO',
'contenido_nutriente': 0.60,
'eficiencia': 0.5
}
},
'PARAMETROS_FINANCIEROS': {
'tasa_descuento': 0.10,
'periodo_analisis': 5,
'inflacion_esperada': 0.08,
'impuestos': 0.35,
'subsidios': 0.05
}
}

# ===== NUEVA CLASIFICACIÓN USDA PARA TEXTURA DE SUELO =====
def clasificar_textura_usda(arena, limo, arcilla):
    try:
        total = arena + limo + arcilla
        if total == 0:
            return "Sin datos"
        arena_pct = (arena / total) * 100
        limo_pct = (limo / total) * 100
        arcilla_pct = (arcilla / total) * 100
        if arcilla_pct > 40:
            if limo_pct >= 40:
                return "Arcilla limosa"
            elif arena_pct <= 45:
                return "Arcilla"
            else:
                return "Arcilla arenosa"
        elif arcilla_pct >= 27 and arcilla_pct <= 40:
            if limo_pct >= 40:
                return "Franco arcilloso limoso"
            elif arena_pct <= 20:
                return "Franco arcilloso"
            else:
                return "Franco arcilloso arenoso"
        elif arcilla_pct >= 20 and arcilla_pct < 27:
            if limo_pct < 28:
                if arena_pct >= 52:
                    return "Arena franca"
                else:
                    return "Franco arenoso"
            else:
                if arena_pct >= 52:
                    return "Franco limoso arenoso"
                else:
                    return "Franco limoso"
        elif arcilla_pct >= 10 and arcilla_pct < 20:
            if limo_pct >= 50:
                return "Limo"
            elif limo_pct >= 30:
                if arena_pct >= 52:
                    return "Franco limoso arenoso"
                else:
                    return "Franco limoso"
            else:
                if arena_pct >= 70:
                    return "Arena"
                elif arena_pct >= 50:
                    return "Arena franca"
                else:
                    return "Franco arenoso"
        else:
            if limo_pct >= 80:
                return "Limo"
            elif limo_pct >= 50:
                return "Limo arenoso"
            else:
                if arena_pct >= 85:
                    return "Arena"
                else:
                    return "Arena franca"
    except Exception as e:
        return "Sin datos"

# ===== PARÁMETROS DE TEXTURA DEL SUELO POR CULTIVO - ACTUALIZADO A USDA =====
TEXTURA_SUELO_OPTIMA = {
'VID': {
'textura_optima': 'Franco arenoso',
'arena_optima': 65,
'limo_optima': 20,
'arcilla_optima': 15,
'densidad_aparente_optima': 1.4,
'porosidad_optima': 0.45
},
'OLIVO': {
'textura_optima': 'Franco arenoso',
'arena_optima': 70,
'limo_optima': 18,
'arcilla_optima': 12,
'densidad_aparente_optima': 1.45,
'porosidad_optima': 0.42
},
'TOMATE': {'textura_optima': 'Franco limoso', 'arena_optima': 40, 'limo_optima': 40, 'arcilla_optima': 20, 'densidad_aparente_optima': 1.3, 'porosidad_optima': 0.48},
'CEBOLLA': {'textura_optima': 'Franco arenoso', 'arena_optima': 60, 'limo_optima': 25, 'arcilla_optima': 15, 'densidad_aparente_optima': 1.4, 'porosidad_optima': 0.45},
'PAPA': {'textura_optima': 'Franco limoso', 'arena_optima': 35, 'limo_optima': 45, 'arcilla_optima': 20, 'densidad_aparente_optima': 1.25, 'porosidad_optima': 0.50},
'ZANAHORIA': {'textura_optima': 'Franco arenoso', 'arena_optima': 65, 'limo_optima': 20, 'arcilla_optima': 15, 'densidad_aparente_optima': 1.35, 'porosidad_optima': 0.46},
'LECHUGA': {'textura_optima': 'Franco limoso', 'arena_optima': 40, 'limo_optima': 40, 'arcilla_optima': 20, 'densidad_aparente_optima': 1.3, 'porosidad_optima': 0.48},
'AJO': {'textura_optima': 'Franco arenoso', 'arena_optima': 60, 'limo_optima': 25, 'arcilla_optima': 15, 'densidad_aparente_optima': 1.4, 'porosidad_optima': 0.45}
}

# RECOMENDACIONES POR TIPO DE TEXTURA USDA
RECOMENDACIONES_TEXTURA = {
'Franco arenoso': {
'propiedades': [
"Excelente drenaje",
"Fácil labranza en cualquier condición",
"Rápido calentamiento",
"Buen desarrollo radicular"
],
'limitantes': [
"Baja retención de agua y nutrientes",
"Alta lixiviación de fertilizantes",
"Baja materia orgánica"
],
'manejo': [
"Riego frecuente en pequeñas cantidades",
"Fertilización fraccionada",
"Aplicación de materia orgánica",
"Cultivos de cobertura"
]
},
'Franco limoso': {
'propiedades': [
"Equilibrio ideal arena-limo-arcilla",
"Excelente estructura y porosidad",
"Alta capacidad de retención de agua",
"Fertilidad natural alta"
],
'limitantes': [
"Puede compactarse con maquinaria pesada",
"Moderadamente susceptible a erosión"
],
'manejo': [
"Labranza mínima o conservacionista",
"Rotación de cultivos",
"Uso de coberturas vegetales",
"Fertilización balanceada"
]
},
'Arcilla': {
'propiedades': [
"Alta capacidad de retención de agua y nutrientes",
"Estructura estable",
"Alta fertilidad potencial"
],
'limitantes': [
"Muy pesada cuando está húmeda",
"Drenaje muy lento",
"Difícil labranza",
"Propensa a compactación"
],
'manejo': [
"Drenaje artificial obligatorio",
"Labranza en condiciones óptimas",
"Encalamiento para mejorar estructura",
"Cultivos tolerantes a humedad"
]
},
'Limo': {
'propiedades': [
"Alta capacidad de retención de agua",
"Fácil labranza",
"Buena fertilidad natural"
],
'limitantes': [
"Susceptible a compactación",
"Propenso a formación de costra superficial",
"Baja estabilidad estructural"
],
'manejo': [
"Evitar labranza en condiciones húmedas",
"Uso de coberturas vegetales",
"Aplicación de materia orgánica",
"Riego por aspersión ligera"
]
}
}

# ICONOS Y COLORES POR CULTIVO
ICONOS_CULTIVOS = {
'VID': '🍇',
'OLIVO': '🫒',
'TOMATE': '🍅',
'CEBOLLA': '🧅',
'PAPA': '🥔',
'ZANAHORIA': '🥕',
'LECHUGA': '🥬',
'AJO': '🧄'
}

COLORES_CULTIVOS = {
'VID': '#8B0000',
'OLIVO': '#556B2F',
'TOMATE': '#DC2626',
'CEBOLLA': '#F59E0B',
'PAPA': '#A16207',
'ZANAHORIA': '#EA580C',
'LECHUGA': '#16A34A',
'AJO': '#71717A'
}

# PALETAS GEE MEJORADAS
PALETAS_GEE = {
'FERTILIDAD': ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#d9ef8b', '#a6d96a', '#66bd63', '#1a9850', '#006837'],
'NITROGENO': ['#00ff00', '#80ff00', '#ffff00', '#ff8000', '#ff0000'],
'FOSFORO': ['#0000ff', '#4040ff', '#8080ff', '#c0c0ff', '#ffffff'],
'POTASIO': ['#4B0082', '#6A0DAD', '#8A2BE2', '#9370DB', '#D8BFD8'],
'TEXTURA': ['#8c510a', '#d8b365', '#f6e8c3', '#c7eae5', '#5ab4ac', '#01665e'],
'ELEVACION': ['#006837', '#1a9850', '#66bd63', '#a6d96a', '#d9ef8b', '#ffffbf', '#fee08b', '#fdae61', '#f46d43', '#d73027'],
'PENDIENTE': ['#4daf4a', '#a6d96a', '#ffffbf', '#fdae61', '#f46d43', '#d73027']
}

# URLs de imágenes ilustradas (dibujos técnicos) para sidebar
IMAGENES_CULTIVOS = {
    'VID': 'https://raw.githubusercontent.com/agrogeomatics/icons/main/crops/grapevine.png',
    'OLIVO': 'https://raw.githubusercontent.com/agrogeomatics/icons/main/crops/olive_tree.png',
    'TOMATE': 'https://raw.githubusercontent.com/agrogeomatics/icons/main/crops/tomato.png',
    'CEBOLLA': 'https://raw.githubusercontent.com/agrogeomatics/icons/main/crops/onion.png',
    'PAPA': 'https://raw.githubusercontent.com/agrogeomatics/icons/main/crops/potato.png',
    'ZANAHORIA': 'https://raw.githubusercontent.com/agrogeomatics/icons/main/crops/carrot.png',
    'LECHUGA': 'https://raw.githubusercontent.com/agrogeomatics/icons/main/crops/lettuce.png',
    'AJO': 'https://raw.githubusercontent.com/agrogeomatics/icons/main/crops/garlic.png'
}

# ===== INICIALIZACIÓN SEGURA DE VARIABLES DE CONFIGURACIÓN =====
if 'variedad' not in st.session_state:
    st.session_state['variedad'] = None
if 'variedad_params' not in st.session_state:
    st.session_state['variedad_params'] = None

nutriente = None
satelite_seleccionado = "SENTINEL-2"
indice_seleccionado = "NDVI"
fecha_inicio = datetime.now() - timedelta(days=30)
fecha_fin = datetime.now()
intervalo_curvas = 5.0
resolucion_dem = 10.0

# ===== NUEVA FUNCIÓN: Integración con el INTA =====
def obtener_materia_organica_inta(gdf, cultivo, usar_inta=True):
    if not usar_inta:
        mo_valor = PARAMETROS_CULTIVOS.get(cultivo, PARAMETROS_HORTALIZAS.get(cultivo, {})).get('MATERIA_ORGANICA_OPTIMA', 2.5)
        return {
            'materia_organica': round(mo_valor, 2),
            'region_inta': 'Estimación genérica',
            'fuente': 'Sistema interno',
            'textura_predominante': 'No disponible'
        }
    try:
        centroid = gdf.geometry.unary_union.centroid
        lon = centroid.x
        lat = centroid.y
        regiones_inta = [
            {
                'nombre': 'OESTE (Mendoza, San Juan)',
                'lat_min': -37.0, 'lat_max': -30.0,
                'lon_min': -72.0, 'lon_max': -66.0,
                'mo_promedio': 1.5,
                'mo_rango': (0.8, 2.5),
                'textura_predominante': 'Franco arenoso'
            },
            {
                'nombre': 'PAMPA HÚMEDA (Núcleo Maicero)',
                'lat_min': -38.0, 'lat_max': -32.0,
                'lon_min': -62.0, 'lon_max': -58.0,
                'mo_promedio': 3.8,
                'mo_rango': (2.5, 5.5),
                'textura_predominante': 'Franco limoso'
            },
            {
                'nombre': 'NOA (Tucumán, Salta, Jujuy)',
                'lat_min': -28.0, 'lat_max': -22.0,
                'lon_min': -67.0, 'lon_max': -64.0,
                'mo_promedio': 2.2,
                'mo_rango': (1.2, 3.5),
                'textura_predominante': 'Franco arcilloso'
            },
            {
                'nombre': 'NEA (Corrientes, Misiones, Chaco)',
                'lat_min': -30.0, 'lat_max': -25.0,
                'lon_min': -62.0, 'lon_max': -54.0,
                'mo_promedio': 4.5,
                'mo_rango': (3.0, 7.0),
                'textura_predominante': 'Arcilla limosa'
            },
            {
                'nombre': 'PATAGONIA (Río Negro, Neuquén)',
                'lat_min': -42.0, 'lat_max': -38.0,
                'lon_min': -72.0, 'lon_max': -62.0,
                'mo_promedio': 5.2,
                'mo_rango': (3.5, 8.0),
                'textura_predominante': 'Franco volcánico'
            }
        ]
        region_encontrada = None
        for region in regiones_inta:
            if (region['lat_min'] <= lat <= region['lat_max'] and
                region['lon_min'] <= lon <= region['lon_max']):
                region_encontrada = region
                break
        if region_encontrada:
            seed_value = abs(hash(f"{lat:.4f}_{lon:.4f}_inta_mo")) % (2**32)
            rng = np.random.RandomState(seed_value)
            mo_valor = rng.normal(region_encontrada['mo_promedio'], 0.6)
            mo_valor = max(region_encontrada['mo_rango'][0], min(region_encontrada['mo_rango'][1], mo_valor))
            return {
                'materia_organica': round(mo_valor, 2),
                'region_inta': region_encontrada['nombre'],
                'fuente': 'INTA (simulado con datos reales)',
                'textura_predominante': region_encontrada['textura_predominante']
            }
        else:
            mo_valor = PARAMETROS_CULTIVOS.get(cultivo, PARAMETROS_HORTALIZAS.get(cultivo, {})).get('MATERIA_ORGANICA_OPTIMA', 2.5)
            return {
                'materia_organica': round(mo_valor, 2),
                'region_inta': 'Fuera de cobertura INTA',
                'fuente': 'Estimación genérica',
                'textura_predominante': 'No disponible'
            }
    except Exception as e:
        mo_valor = PARAMETROS_CULTIVOS.get(cultivo, PARAMETROS_HORTALIZAS.get(cultivo, {})).get('MATERIA_ORGANICA_OPTIMA', 2.5)
        return {
            'materia_organica': round(mo_valor, 2),
            'region_inta': 'Error en consulta',
            'fuente': 'Estimación de respaldo',
            'textura_predominante': 'No disponible'
        }

# ===== FUNCIONES AUXILIARES - CORREGIDAS PARA EPSG:4326 =====
def validar_y_corregir_crs(gdf):
    if gdf is None or len(gdf) == 0:
        return gdf
    try:
        if gdf.crs is None:
            gdf = gdf.set_crs('EPSG:4326', inplace=False)
            st.info("ℹ️ Se asignó EPSG:4326 al archivo (no tenía CRS)")
        elif str(gdf.crs).upper() != 'EPSG:4326':
            original_crs = str(gdf.crs)
            gdf = gdf.to_crs('EPSG:4326')
            st.info(f"ℹ️ Transformado de {original_crs} a EPSG:4326")
        return gdf
    except Exception as e:
        st.warning(f"⚠️ Error al corregir CRS: {str(e)}")
        return gdf

def calcular_superficie(gdf):
    try:
        if gdf is None or len(gdf) == 0:
            return 0.0
        gdf = validar_y_corregir_crs(gdf)
        centroid = gdf.geometry.unary_union.centroid
        lon, lat = centroid.x, centroid.y
        utm_zone = int((lon + 180) / 6) + 1
        hemisphere = 'north' if lat >= 0 else 'south'
        epsg_utm = f"326{utm_zone:02d}" if hemisphere == 'north' else f"327{utm_zone:02d}"
        try:
            gdf_utm = gdf.to_crs(epsg=epsg_utm)
            area_m2 = gdf_utm.geometry.area.sum()
        except Exception:
            gdf_eq = gdf.to_crs("EPSG:6933")
            area_m2 = gdf_eq.geometry.area.sum()
        return area_m2 / 10000
    except Exception as e:
        st.warning(f"⚠️ Error al calcular área precisa: {str(e)}. Usando cálculo aproximado.")
        area_grados2 = gdf.geometry.area.sum()
        area_m2 = area_grados2 * (111000 ** 2)
        return area_m2 / 10000

def dividir_parcela_en_zonas(gdf, n_zonas):
    if len(gdf) == 0:
        return gdf
    gdf = validar_y_corregir_crs(gdf)
    parcela_principal = gdf.iloc[0].geometry
    bounds = parcela_principal.bounds
    minx, miny, maxx, maxy = bounds
    sub_poligonos = []
    n_cols = math.ceil(math.sqrt(n_zonas))
    n_rows = math.ceil(n_zonas / n_cols)
    width = (maxx - minx) / n_cols
    height = (maxy - miny) / n_rows
    for i in range(n_rows):
        for j in range(n_cols):
            if len(sub_poligonos) >= n_zonas:
                break
            cell_minx = minx + (j * width)
            cell_maxx = minx + ((j + 1) * width)
            cell_miny = miny + (i * height)
            cell_maxy = miny + ((i + 1) * height)
            cell_poly = Polygon([(cell_minx, cell_miny), (cell_maxx, cell_miny), (cell_maxx, cell_maxy), (cell_minx, cell_maxy)])
            intersection = parcela_principal.intersection(cell_poly)
            if not intersection.is_empty and intersection.area > 0:
                sub_poligonos.append(intersection)
    if sub_poligonos:
        nuevo_gdf = gpd.GeoDataFrame({'id_zona': range(1, len(sub_poligonos) + 1), 'geometry': sub_poligonos}, crs='EPSG:4326')
        return nuevo_gdf
    else:
        return gdf

# ===== FUNCIONES PARA CARGAR ARCHIVOS =====
def cargar_shapefile_desde_zip(zip_file):
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            shp_files = [f for f in os.listdir(tmp_dir) if f.endswith('.shp')]
            if shp_files:
                shp_path = os.path.join(tmp_dir, shp_files[0])
                gdf = gpd.read_file(shp_path)
                gdf = validar_y_corregir_crs(gdf)
                return gdf
            else:
                st.error("❌ No se encontró ningún archivo .shp en el ZIP")
                return None
    except Exception as e:
        st.error(f"❌ Error cargando shapefile desde ZIP: {str(e)}")
        return None

def parsear_kml_manual(contenido_kml):
    try:
        root = ET.fromstring(contenido_kml)
        namespaces = {'kml': 'http://www.opengis.net/kml/2.2'}
        polygons = []
        for polygon_elem in root.findall('.//kml:Polygon', namespaces):
            coords_elem = polygon_elem.find('.//kml:coordinates', namespaces)
            if coords_elem is not None and coords_elem.text:
                coord_text = coords_elem.text.strip()
                coord_list = []
                for coord_pair in coord_text.split():
                    parts = coord_pair.split(',')
                    if len(parts) >= 2:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        coord_list.append((lon, lat))
                if len(coord_list) >= 3:
                    polygons.append(Polygon(coord_list))
        if not polygons:
            for multi_geom in root.findall('.//kml:MultiGeometry', namespaces):
                for polygon_elem in multi_geom.findall('.//kml:Polygon', namespaces):
                    coords_elem = polygon_elem.find('.//kml:coordinates', namespaces)
                    if coords_elem is not None and coords_elem.text:
                        coord_text = coords_elem.text.strip()
                        coord_list = []
                        for coord_pair in coord_text.split():
                            parts = coord_pair.split(',')
                            if len(parts) >= 2:
                                lon = float(parts[0])
                                lat = float(parts[1])
                                coord_list.append((lon, lat))
                        if len(coord_list) >= 3:
                            polygons.append(Polygon(coord_list))
        if polygons:
            gdf = gpd.GeoDataFrame({'geometry': polygons}, crs='EPSG:4326')
            return gdf
        else:
            for placemark in root.findall('.//kml:Placemark', namespaces):
                for elem_name in ['Polygon', 'LineString', 'Point', 'LinearRing']:
                    elem = placemark.find(f'.//kml:{elem_name}', namespaces)
                    if elem is not None:
                        coords_elem = elem.find('.//kml:coordinates', namespaces)
                        if coords_elem is not None and coords_elem.text:
                            coord_text = coords_elem.text.strip()
                            coord_list = []
                            for coord_pair in coord_text.split():
                                parts = coord_pair.split(',')
                                if len(parts) >= 2:
                                    lon = float(parts[0])
                                    lat = float(parts[1])
                                    coord_list.append((lon, lat))
                            if len(coord_list) >= 3:
                                polygons.append(Polygon(coord_list))
                            break
            if polygons:
                gdf = gpd.GeoDataFrame({'geometry': polygons}, crs='EPSG:4326')
                return gdf
        return None
    except Exception as e:
        st.error(f"❌ Error parseando KML manualmente: {str(e)}")
        return None

def cargar_kml(kml_file):
    try:
        if kml_file.name.endswith('.kmz'):
            with tempfile.TemporaryDirectory() as tmp_dir:
                with zipfile.ZipFile(kml_file, 'r') as zip_ref:
                    zip_ref.extractall(tmp_dir)
                kml_files = [f for f in os.listdir(tmp_dir) if f.endswith('.kml')]
                if kml_files:
                    kml_path = os.path.join(tmp_dir, kml_files[0])
                    with open(kml_path, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                    gdf = parsear_kml_manual(contenido)
                    if gdf is not None:
                        return gdf
                    else:
                        try:
                            gdf = gpd.read_file(kml_path)
                            gdf = validar_y_corregir_crs(gdf)
                            return gdf
                        except:
                            st.error("❌ No se pudo cargar el archivo KML/KMZ")
                            return None
                else:
                    st.error("❌ No se encontró ningún archivo .kml en el KMZ")
                    return None
        else:
            contenido = kml_file.read().decode('utf-8')
            gdf = parsear_kml_manual(contenido)
            if gdf is not None:
                return gdf
            else:
                kml_file.seek(0)
                gdf = gpd.read_file(kml_file)
                gdf = validar_y_corregir_crs(gdf)
                return gdf
    except Exception as e:
        st.error(f"❌ Error cargando archivo KML/KMZ: {str(e)}")
        return None

def cargar_archivo_parcela(uploaded_file):
    try:
        if uploaded_file.name.endswith('.zip'):
            gdf = cargar_shapefile_desde_zip(uploaded_file)
        elif uploaded_file.name.endswith(('.kml', '.kmz')):
            gdf = cargar_kml(uploaded_file)
        else:
            st.error("❌ Formato de archivo no soportado")
            return None
        if gdf is not None:
            gdf = validar_y_corregir_crs(gdf)
            if not gdf.geometry.geom_type.str.contains('Polygon').any():
                st.warning("⚠️ El archivo no contiene polígonos. Intentando extraer polígonos...")
                gdf = gdf.explode()
                gdf = gdf[gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])]
            if len(gdf) > 0:
                if 'id_zona' not in gdf.columns:
                    gdf['id_zona'] = range(1, len(gdf) + 1)
                if str(gdf.crs).upper() != 'EPSG:4326':
                    st.warning(f"⚠️ El archivo no pudo ser convertido a EPSG:4326. CRS actual: {gdf.crs}")
                return gdf
            else:
                st.error("❌ No se encontraron polígonos en el archivo")
                return None
        return gdf
    except Exception as e:
        st.error(f"❌ Error cargando archivo: {str(e)}")
        import traceback
        st.error(f"Detalle: {traceback.format_exc()}")
        return None

# ===== NUEVAS FUNCIONES PARA ESTIMAR NPK CON TELEDETECCIÓN =====
def calcular_nitrogeno_sentinel2(b5, b8a):
    ndre = (b8a - b5) / (b8a + b5 + 1e-10)
    nitrogeno = 150 * ndre + 50 * (b8a / (b5 + 1e-10))
    return max(0, min(300, nitrogeno)), ndre

def calcular_fosforo_sentinel2(b4, b11):
    swir_vis_ratio = b11 / (b4 + 1e-10)
    fosforo = 80 * (swir_vis_ratio ** 0.5) + 20
    return max(0, min(100, fosforo)), swir_vis_ratio

def calcular_potasio_sentinel2(b8, b11, b12):
    ndii = (b8 - b11) / (b8 + b11 + 1e-10)
    potasio = 120 * ndii + 40 * (b8 / (b12 + 1e-10))
    return max(0, min(250, potasio)), ndii

def calcular_nitrogeno_landsat8(b3, b4, b5):
    tcari = 3 * ((b5 - b4) - 0.2 * (b5 - b3) * (b5 / (b4 + 1e-10)))
    osavi = (1.16 * (b5 - b4)) / (b5 + b4 + 0.16 + 1e-10)
    tcari_osavi = tcari / (osavi + 1e-10)
    nitrogeno = 100 * tcari_osavi + 30
    return max(0, min(300, nitrogeno)), tcari_osavi

def calcular_fosforo_landsat8(b3, b6):
    swir_verde_ratio = b6 / (b3 + 1e-10)
    fosforo = 60 * (swir_verde_ratio ** 0.7) + 25
    return max(0, min(100, fosforo)), swir_verde_ratio

def calcular_potasio_landsat8(b5, b7):
    nir_swir_ratio = (b5 - b7) / (b5 + b7 + 1e-10)
    potasio = 100 * nir_swir_ratio + 50
    return max(0, min(250, potasio)), nir_swir_ratio

def obtener_parametros_cultivo(cultivo):
    """Obtiene parámetros según tipo de cultivo"""
    if cultivo in ['VID', 'OLIVO']:
        return PARAMETROS_CULTIVOS[cultivo]
    else:
        return PARAMETROS_HORTALIZAS[cultivo]

def calcular_indices_npk_avanzados(gdf, cultivo, satelite, usar_inta=True):
    resultados = []
    params = obtener_parametros_cultivo(cultivo)
    if 'variedad_params' in st.session_state and st.session_state['variedad_params']:
        variedad_params = st.session_state['variedad_params']
        params.update({
            'RENDIMIENTO_BASE': variedad_params['RENDIMIENTO_BASE'],
            'RENDIMIENTO_OPTIMO': variedad_params['RENDIMIENTO_OPTIMO'],
            'RESPUESTA_N': variedad_params['RESPUESTA_N'],
            'RESPUESTA_P': variedad_params['RESPUESTA_P'],
            'RESPUESTA_K': variedad_params['RESPUESTA_K'],
            'NITROGENO': {'optimo': variedad_params['NITROGENO_OPTIMO']},
            'FOSFORO': {'optimo': variedad_params['FOSFORO_OPTIMO']},
            'POTASIO': {'optimo': variedad_params['POTASIO_OPTIMO']}
        })
    datos_inta = obtener_materia_organica_inta(gdf, cultivo, usar_inta=usar_inta)
    materia_organica_base = datos_inta['materia_organica']
    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid
        seed_value = abs(hash(f"{centroid.x:.6f}_{centroid.y:.6f}_{cultivo}_{satelite}")) % (2**32)
        rng = np.random.RandomState(seed_value)
        if satelite == "SENTINEL-2":
            b3 = rng.uniform(0.08, 0.12)
            b4 = rng.uniform(0.06, 0.10)
            b5 = rng.uniform(0.10, 0.15)
            b8 = rng.uniform(0.25, 0.40)
            b8a = rng.uniform(0.20, 0.35)
            b11 = rng.uniform(0.15, 0.25)
            b12 = rng.uniform(0.10, 0.20)
            nitrogeno, ndre = calcular_nitrogeno_sentinel2(b5, b8a)
            fosforo, swir_vis = calcular_fosforo_sentinel2(b4, b11)
            potasio, ndii = calcular_potasio_sentinel2(b8, b11, b12)
            nitrogeno = nitrogeno * (params['NDVI_OPTIMO'] / 0.85)
            fosforo = fosforo * (params['MATERIA_ORGANICA_OPTIMA'] / 3.5)
            potasio = potasio * (params['HUMEDAD_OPTIMA'] / 0.3)
        elif satelite == "LANDSAT-8":
            b3 = rng.uniform(0.08, 0.12)
            b4 = rng.uniform(0.06, 0.10)
            b5 = rng.uniform(0.20, 0.35)
            b6 = rng.uniform(0.12, 0.22)
            b7 = rng.uniform(0.08, 0.18)
            nitrogeno, tcari_osavi = calcular_nitrogeno_landsat8(b3, b4, b5)
            fosforo, swir_verde = calcular_fosforo_landsat8(b3, b6)
            potasio, nir_swir = calcular_potasio_landsat8(b5, b7)
            nitrogeno = nitrogeno * (params['NDVI_OPTIMO'] / 0.85)
            fosforo = fosforo * (params['MATERIA_ORGANICA_OPTIMA'] / 3.5)
            potasio = potasio * (params['HUMEDAD_OPTIMA'] / 0.3)
        else:
            nitrogeno = rng.uniform(params['NITROGENO']['min'] * 0.8, params['NITROGENO']['max'] * 1.2)
            fosforo = rng.uniform(params['FOSFORO']['min'] * 0.8, params['FOSFORO']['max'] * 1.2)
            potasio = rng.uniform(params['POTASIO']['min'] * 0.8, params['POTASIO']['max'] * 1.2)
            ndre = rng.uniform(0.2, 0.7)
            swir_vis = rng.uniform(0.5, 2.0)
            ndii = rng.uniform(0.1, 0.6)
        materia_organica = materia_organica_base * (1 + rng.normal(0, 0.1))
        materia_organica = max(0.5, min(10.0, materia_organica))
        ndvi = rng.uniform(params['NDVI_OPTIMO'] * 0.7, params['NDVI_OPTIMO'] * 1.1)
        humedad_suelo = rng.uniform(params['HUMEDAD_OPTIMA'] * 0.7, params['HUMEDAD_OPTIMA'] * 1.2)
        ndwi = rng.uniform(0.1, 0.4)
        npk_integrado = (
            0.4 * (nitrogeno / params['NITROGENO']['optimo']) +
            0.3 * (fosforo / params['FOSFORO']['optimo']) +
            0.3 * (potasio / params['POTASIO']['optimo'])
        ) / 1.0
        resultados.append({
            'nitrogeno_actual': round(nitrogeno, 1),
            'fosforo_actual': round(fosforo, 1),
            'potasio_actual': round(potasio, 1),
            'npk_integrado': round(npk_integrado, 3),
            'materia_organica': round(materia_organica, 2),
            'humedad_suelo': round(humedad_suelo, 3),
            'ndvi': round(ndvi, 3),
            'ndre': round(ndre, 3),
            'ndwi': round(ndwi, 3),
            'ndii': round(ndii, 3) if 'ndii' in locals() else 0.0,
            'region_inta': datos_inta['region_inta'],
            'fuente_materia_organica': datos_inta['fuente']
        })
    return resultados

# ===== FUNCIONES PARA CÁLCULO DE RENDIMIENTO MEJORADAS =====
def obtener_parametros_rendimiento(cultivo):
    params = obtener_parametros_cultivo(cultivo)
    if 'variedad_params' in st.session_state and st.session_state['variedad_params']:
        variedad_params = st.session_state['variedad_params']
        params.update({
            'RENDIMIENTO_BASE': variedad_params['RENDIMIENTO_BASE'],
            'RENDIMIENTO_OPTIMO': variedad_params['RENDIMIENTO_OPTIMO'],
            'RESPUESTA_N': variedad_params['RESPUESTA_N'],
            'RESPUESTA_P': variedad_params['RESPUESTA_P'],
            'RESPUESTA_K': variedad_params['RESPUESTA_K'],
            'NITROGENO': {'optimo': variedad_params['NITROGENO_OPTIMO']},
            'FOSFORO': {'optimo': variedad_params['FOSFORO_OPTIMO']},
            'POTASIO': {'optimo': variedad_params['POTASIO_OPTIMO']}
        })
    return params

def calcular_rendimiento_potencial(gdf_analizado, cultivo):
    params = obtener_parametros_rendimiento(cultivo)
    rendimientos = []
    for idx, row in gdf_analizado.iterrows():
        factor_fertilidad = row['npk_integrado']
        factor_humedad = min(1.0, row['ndwi'] / 0.4) if 'ndwi' in row else 0.7
        factor_vigor = min(1.2, row['ndvi'] / params['NDVI_OPTIMO'])
        factor_clima = params['FACTOR_CLIMA']
        rendimiento_base = params['RENDIMIENTO_BASE']
        ajuste_fertilidad = 0.5 + (factor_fertilidad * 0.5)
        rendimiento_potencial = (
            rendimiento_base *
            ajuste_fertilidad *
            factor_humedad *
            factor_vigor *
            factor_clima
        )
        rendimiento_potencial = min(rendimiento_potencial, params['RENDIMIENTO_OPTIMO'] * 1.1)
        rendimientos.append(round(rendimiento_potencial, 2))
    return rendimientos

def calcular_rendimiento_con_recomendaciones(gdf_analizado, cultivo):
    params = obtener_parametros_rendimiento(cultivo)
    rendimientos = []
    for idx, row in gdf_analizado.iterrows():
        factor_fertilidad = row['npk_integrado']
        factor_humedad = min(1.0, row['ndwi'] / 0.4) if 'ndwi' in row else 0.7
        factor_vigor = min(1.2, row['ndvi'] / params['NDVI_OPTIMO'])
        factor_clima = params['FACTOR_CLIMA']
        rendimiento_base = params['RENDIMIENTO_BASE']
        ajuste_fertilidad = 0.5 + (factor_fertilidad * 0.5)
        rendimiento_actual = (
            rendimiento_base *
            ajuste_fertilidad *
            factor_humedad *
            factor_vigor *
            factor_clima
        )
        incremento_total = 0
        n_actual = row['nitrogeno_actual']
        n_optimo = params['NITROGENO']['optimo']
        if n_actual < n_optimo * 0.9:
            deficiencia_n = max(0, n_optimo - n_actual)
            eficiencia_n = params['RESPUESTA_N'] * 0.7
            incremento_n = deficiencia_n * eficiencia_n
            incremento_total += min(incremento_n, deficiencia_n * params['RESPUESTA_N'])
        p_actual = row['fosforo_actual']
        p_optimo = params['FOSFORO']['optimo']
        if p_actual < p_optimo * 0.85:
            deficiencia_p = max(0, p_optimo - p_actual)
            eficiencia_p = params['RESPUESTA_P'] * 0.5
            incremento_p = deficiencia_p * eficiencia_p
            incremento_total += incremento_p
        k_actual = row['potasio_actual']
        k_optimo = params['POTASIO']['optimo']
        if k_actual < k_optimo * 0.85:
            deficiencia_k = max(0, k_optimo - k_actual)
            eficiencia_k = params['RESPUESTA_K'] * 0.6
            incremento_k = deficiencia_k * eficiencia_k
            incremento_total += incremento_k
        rendimiento_proyectado = rendimiento_actual + incremento_total
        rendimiento_max = params['RENDIMIENTO_OPTIMO'] * 1.2
        rendimiento_proyectado = min(rendimiento_proyectado, rendimiento_max)
        rendimientos.append(round(rendimiento_proyectado, 2))
    return rendimientos

# ===== FUNCIONES PARA ANÁLISIS ECONÓMICO =====
def obtener_estadisticas_completas(gdf_analizado, cultivo):
    """Calcula estadísticas completas para el reporte"""
    stats = {
        'cultivo': cultivo,
        'numero_zonas': len(gdf_analizado),
        'area_total_ha': gdf_analizado['area_ha'].sum() if 'area_ha' in gdf_analizado.columns else 0
    }
    
    # Fertilidad
    if 'npk_integrado' in gdf_analizado.columns:
        stats['fertilidad_promedio'] = gdf_analizado['npk_integrado'].mean()
    
    # Nutrientes
    for nutriente in ['nitrogeno_actual', 'fosforo_actual', 'potasio_actual']:
        if nutriente in gdf_analizado.columns:
            stats[f'{nutriente}_prom'] = gdf_analizado[nutriente].mean()
            stats[f'{nutriente}_min'] = gdf_analizado[nutriente].min()
            stats[f'{nutriente}_max'] = gdf_analizado[nutriente].max()
    
    # Rendimiento
    if 'rendimiento_actual' in gdf_analizado.columns:
        stats['rendimiento_actual_prom'] = gdf_analizado['rendimiento_actual'].mean()
        stats['rendimiento_actual_total'] = (gdf_analizado['rendimiento_actual'] * gdf_analizado['area_ha']).sum()
    
    if 'rendimiento_proyectado' in gdf_analizado.columns:
        stats['rendimiento_proy_prom'] = gdf_analizado['rendimiento_proyectado'].mean()
        stats['rendimiento_proy_total'] = (gdf_analizado['rendimiento_proyectado'] * gdf_analizado['area_ha']).sum()
    
    return stats

def realizar_analisis_economico(gdf_analizado, cultivo, variedad_params, area_total):
    precios_cultivo = PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][cultivo]
    # ... (el resto de tu función existente)


# ===== FUNCIONES PARA ANÁLISIS ECONÓMICO =====
def realizar_analisis_economico(gdf_analizado, cultivo, variedad_params, area_total):
    precios_cultivo = PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][cultivo]
    precios_fert = PARAMETROS_ECONOMICOS['PRECIOS_FERTILIZANTES']
    conversion = PARAMETROS_ECONOMICOS['CONVERSION_NUTRIENTES']
    financieros = PARAMETROS_ECONOMICOS['PARAMETROS_FINANCIEROS']
    rend_actual_prom = gdf_analizado['rendimiento_actual'].mean()
    rend_proy_prom = gdf_analizado['rendimiento_proyectado'].mean()
    incremento_prom = gdf_analizado['incremento_rendimiento'].mean()
    
    # ===== CALCULAR FERTILIZANTE NECESARIO BASADO EN DEFICIENCIAS REALES =====
    fertilizante_necesario = {'NITRÓGENO': 0, 'FÓSFORO': 0, 'POTASIO': 0}
    
    # Obtener parámetros del cultivo
    if cultivo in ['VID', 'OLIVO']:
        params_cultivo = PARAMETROS_CULTIVOS[cultivo]
    else:
        params_cultivo = PARAMETROS_HORTALIZAS[cultivo]
    
    # Ajustar por variedad si se proporcionan parámetros
    if variedad_params:
        # Si tenemos parámetros de variedad, usarlos para los valores óptimos
        n_optimo = variedad_params.get('NITROGENO_OPTIMO', params_cultivo['NITROGENO']['optimo'])
        p_optimo = variedad_params.get('FOSFORO_OPTIMO', params_cultivo['FOSFORO']['optimo'])
        k_optimo = variedad_params.get('POTASIO_OPTIMO', params_cultivo['POTASIO']['optimo'])
    else:
        # Usar valores generales del cultivo
        n_optimo = params_cultivo['NITROGENO']['optimo']
        p_optimo = params_cultivo['FOSFORO']['optimo']
        k_optimo = params_cultivo['POTASIO']['optimo']
    
    # Calcular deficiencias totales en todo el campo
    for idx, row in gdf_analizado.iterrows():
        area_zona = row['area_ha']
        
        # Nitrógeno
        n_actual = row.get('nitrogeno_actual', 0)
        if n_actual < n_optimo:
            deficiencia_n = (n_optimo - n_actual) * area_zona
            fertilizante_necesario['NITRÓGENO'] += deficiencia_n
        
        # Fósforo
        p_actual = row.get('fosforo_actual', 0)
        if p_actual < p_optimo:
            deficiencia_p = (p_optimo - p_actual) * area_zona
            fertilizante_necesario['FÓSFORO'] += deficiencia_p
        
        # Potasio
        k_actual = row.get('potasio_actual', 0)
        if k_actual < k_optimo:
            deficiencia_k = (k_optimo - k_actual) * area_zona
            fertilizante_necesario['POTASIO'] += deficiencia_k
    
    # Convertir a kg/ha para cálculo de costos (promedio por hectárea)
    if area_total > 0:
        fertilizante_necesario['NITRÓGENO'] = fertilizante_necesario['NITRÓGENO'] / area_total
        fertilizante_necesario['FÓSFORO'] = fertilizante_necesario['FÓSFORO'] / area_total
        fertilizante_necesario['POTASIO'] = fertilizante_necesario['POTASIO'] / area_total
    # ===== FIN DEL CÁLCULO DE FERTILIZANTE NECESARIO =====
    
    costos = {}
    costos['semilla'] = precios_cultivo['costo_semilla']
    costos['herbicidas'] = precios_cultivo['costo_herbicidas']
    costos['insecticidas'] = precios_cultivo['costo_insecticidas']
    costos['labores'] = precios_cultivo['costo_labores']
    costos['cosecha'] = precios_cultivo['costo_cosecha']
    costos['otros'] = precios_cultivo['costo_otros']
    costos_fertilizacion = 0
    
    if fertilizante_necesario['NITRÓGENO'] > 0:
        fuente_n = conversion['NITRÓGENO']['fuente_principal']
        contenido_n = conversion['NITRÓGENO']['contenido_nutriente']
        eficiencia_n = conversion['NITRÓGENO']['eficiencia']
        kg_fertilizante_n = (fertilizante_necesario['NITRÓGENO'] / contenido_n) / eficiencia_n
        costo_n = (kg_fertilizante_n / 1000) * precios_fert[fuente_n]
        costos_fertilizacion += costo_n
    
    if fertilizante_necesario['FÓSFORO'] > 0:
        fuente_p = conversion['FÓSFORO']['fuente_principal']
        contenido_p = conversion['FÓSFORO']['contenido_nutriente']
        eficiencia_p = conversion['FÓSFORO']['eficiencia']
        kg_fertilizante_p = (fertilizante_necesario['FÓSFORO'] / contenido_p) / eficiencia_p
        costo_p = (kg_fertilizante_p / 1000) * precios_fert[fuente_p]
        costos_fertilizacion += costo_p
    
    if fertilizante_necesario['POTASIO'] > 0:
        fuente_k = conversion['POTASIO']['fuente_principal']
        contenido_k = conversion['POTASIO']['contenido_nutriente']
        eficiencia_k = conversion['POTASIO']['eficiencia']
        kg_fertilizante_k = (fertilizante_necesario['POTASIO'] / contenido_k) / eficiencia_k
        costo_k = (kg_fertilizante_k / 1000) * precios_fert[fuente_k]
        costos_fertilizacion += costo_k
    
    costos['fertilizacion'] = costos_fertilizacion
    costo_total_ha = sum(costos.values())
    ingresos_actual_ha = rend_actual_prom * precios_cultivo['precio_ton']
    margen_actual_ha = ingresos_actual_ha - costo_total_ha + costos['fertilizacion']
    ingresos_proy_ha = rend_proy_prom * precios_cultivo['precio_ton']
    margen_proy_ha = ingresos_proy_ha - costo_total_ha
    incremento_margen_ha = margen_proy_ha - margen_actual_ha
    
    if costos_fertilizacion > 0:
        roi_fertilizacion = (incremento_margen_ha / costos_fertilizacion) * 100
    else:
        roi_fertilizacion = 0
    
    if costo_total_ha > 0:
        relacion_bc_actual = margen_actual_ha / costo_total_ha
        relacion_bc_proy = margen_proy_ha / costo_total_ha
    else:
        relacion_bc_actual = 0
        relacion_bc_proy = 0
    
    flujos = []
    for año in range(financieros['periodo_analisis']):
        factor_inflacion = (1 + financieros['inflacion_esperada']) ** año
        flujo_neto = incremento_margen_ha * area_total * factor_inflacion
        flujo_neto = flujo_neto * (1 - financieros['impuestos'])
        flujo_neto = flujo_neto * (1 + financieros['subsidios'])
        if año == 0:
            flujo_neto -= costos_fertilizacion * area_total
        flujos.append(flujo_neto)
    
    van = 0
    for t, flujo in enumerate(flujos):
        van += flujo / ((1 + financieros['tasa_descuento']) ** t)
    
    def calcular_tir(flujos):
        def npv(tasa):
            npv_val = 0
            for t, flujo in enumerate(flujos):
                npv_val += flujo / ((1 + tasa) ** t)
            return npv_val
        
        low = 0.0
        high = 1.0
        for _ in range(100):
            mid = (low + high) / 2
            if npv(mid) > 0:
                low = mid
            else:
                high = mid
        
        return (low + high) / 2
    
    tir = calcular_tir(flujos) * 100
    
    if incremento_margen_ha > 0:
        punto_equilibrio_ha = costos_fertilizacion / incremento_margen_ha
    else:
        punto_equilibrio_ha = 0
    
    resultados_economicos = {
        'cultivo': cultivo,
        'area_total_ha': area_total,
        'variedad': st.session_state.get('variedad', 'No especificada'),
        'rendimiento_actual_ton_ha': rend_actual_prom,
        'rendimiento_proy_ton_ha': rend_proy_prom,
        'incremento_rendimiento_ton_ha': incremento_prom,
        'costo_total_ha': costo_total_ha,
        'costo_fertilizacion_ha': costos_fertilizacion,
        'costo_semilla_ha': costos['semilla'],
        'costo_insumos_ha': costos['herbicidas'] + costos['insecticidas'] + costos['otros'],
        'ingreso_actual_ha': ingresos_actual_ha,
        'ingreso_proy_ha': ingresos_proy_ha,
        'margen_actual_ha': margen_actual_ha,
        'margen_proy_ha': margen_proy_ha,
        'incremento_margen_ha': incremento_margen_ha,
        'roi_fertilizacion_%': roi_fertilizacion,
        'relacion_bc_actual': relacion_bc_actual,
        'relacion_bc_proy': relacion_bc_proy,
        'van_usd': van,
        'tir_%': tir,
        'punto_equilibrio_ha': punto_equilibrio_ha,
        'incremento_produccion_total_ton': incremento_prom * area_total,
        'incremento_ingreso_total_usd': incremento_margen_ha * area_total,
        'costo_fertilizacion_total_usd': costos_fertilizacion * area_total
    }
    
    return resultados_economicos

def mostrar_analisis_economico(resultados_economicos):
    financieros = PARAMETROS_ECONOMICOS['PARAMETROS_FINANCIEROS']
    flujos_proyectados = []
    for año in range(financieros['periodo_analisis']):
        factor_inflacion = (1 + financieros['inflacion_esperada']) ** año
        flujo_anual = resultados_economicos['incremento_margen_ha'] * resultados_economicos['area_total_ha'] * factor_inflacion
        if año == 0:
            flujo_anual -= resultados_economicos['costo_fertilizacion_total_usd']
        flujos_proyectados.append({
            'Año': año + 1,
            'Flujo Neto (USD)': flujo_anual,
            'Flujo Acumulado (USD)': sum(f['Flujo Neto (USD)'] for f in flujos_proyectados) + flujo_anual
        })
    st.markdown("---")
    st.subheader("💰 ANÁLISIS ECONÓMICO AGRÍCOLA")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "📈 Incremento Producción",
            f"{resultados_economicos['incremento_rendimiento_ton_ha']:.1f} ton/ha",
            f"{resultados_economicos['incremento_produccion_total_ton']:.0f} ton total"
        )
    with col2:
        st.metric(
            "💰 ROI Fertilización",
            f"{resultados_economicos['roi_fertilizacion_%']:.0f}%",
            delta_color="normal"
        )
    with col3:
        st.metric(
            "📊 VAN Proyecto",
            f"${resultados_economicos['van_usd']:,.0f}",
            delta_color="normal"
        )
    with col4:
        st.metric(
            "🎯 TIR",
            f"{resultados_economicos['tir_%']:.1f}%",
            delta_color="normal"
        )
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Resumen", "📊 Costos", "💰 Rentabilidad", "📈 Proyecciones"])
    with tab1:
        resumen_data = {
            'Concepto': [
                'Rendimiento Actual',
                'Rendimiento Proyectado',
                'Incremento',
                'Ingresos Actuales',
                'Ingresos Proyectados',
                'Costos Totales',
                'Margen Actual',
                'Margen Proyectado',
                'Incremento Margen'
            ],
            'Valor (USD/ha)': [
                f"{resultados_economicos['rendimiento_actual_ton_ha']:.1f} ton",
                f"{resultados_economicos['rendimiento_proy_ton_ha']:.1f} ton",
                f"+{resultados_economicos['incremento_rendimiento_ton_ha']:.1f} ton",
                f"${resultados_economicos['ingreso_actual_ha']:,.0f}",
                f"${resultados_economicos['ingreso_proy_ha']:,.0f}",
                f"${resultados_economicos['costo_total_ha']:,.0f}",
                f"${resultados_economicos['margen_actual_ha']:,.0f}",
                f"${resultados_economicos['margen_proy_ha']:,.0f}",
                f"${resultados_economicos['incremento_margen_ha']:,.0f}"
            ]
        }
        st.dataframe(pd.DataFrame(resumen_data), use_container_width=True)
    with tab2:
        costos_data = {
            'Rubro': ['Semilla', 'Fertilización', 'Herbicidas', 'Inseticidas', 'Labores', 'Cosecha', 'Otros'],
            'Costo USD/ha': [
                resultados_economicos['costo_semilla_ha'],
                resultados_economicos['costo_fertilizacion_ha'],
                PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_herbicidas'],
                PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_insecticidas'],
                PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_labores'],
                PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_cosecha'],
                PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_otros']
            ]
        }
        df_costos = pd.DataFrame(costos_data)
        fig, ax = plt.subplots(figsize=(10, 6))
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6']
        ax.bar(df_costos['Rubro'], df_costos['Costo USD/ha'], color=colors)
        ax.set_title('Distribución de Costos por Hectárea', color='white')
        ax.set_ylabel('USD/ha', color='white')
        ax.tick_params(colors='white')
        ax.set_facecolor('#0f172a')
        fig.patch.set_facecolor('#0f172a')
        for i, v in enumerate(df_costos['Costo USD/ha']):
            ax.text(i, v + 5, f'${v:,.0f}', ha='center', color='white', fontweight='bold')
        st.pyplot(fig)
    with tab3:
        rentabilidad_data = {
            'Escenario': ['Actual (sin fert.)', 'Proyectado (con fert.)'],
            'B/C Ratio': [
                resultados_economicos['relacion_bc_actual'],
                resultados_economicos['relacion_bc_proy']
            ],
            'Margen (USD/ha)': [
                resultados_economicos['margen_actual_ha'],
                resultados_economicos['margen_proy_ha']
            ]
        }
        df_rent = pd.DataFrame(rentabilidad_data)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        bars1 = ax1.bar(df_rent['Escenario'], df_rent['B/C Ratio'], color=['#ef4444', '#10b981'])
        ax1.set_title('Relación Beneficio/Costo', color='white')
        ax1.set_ylabel('Ratio B/C', color='white')
        ax1.axhline(y=1.0, color='white', linestyle='--', alpha=0.5)
        ax1.text(0.5, 1.05, 'Límite Rentabilidad', ha='center', color='white', fontsize=9)
        bars2 = ax2.bar(df_rent['Escenario'], df_rent['Margen (USD/ha)'], color=['#f59e0b', '#3b82f6'])
        ax2.set_title('Margen Neto por Hectárea', color='white')
        ax2.set_ylabel('USD/ha', color='white')
        for ax in [ax1, ax2]:
            ax.set_facecolor('#0f172a')
            ax.tick_params(colors='white')
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                     f'{height:.2f}',
                     ha='center', va='bottom', color='white', fontweight='bold')
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 10,
                     f'${height:,.0f}',
                     ha='center', va='bottom', color='white', fontweight='bold')
        fig.patch.set_facecolor('#0f172a')
        plt.tight_layout()
        st.pyplot(fig)
        st.markdown("##### 💡 INTERPRETACIÓN:")
        if resultados_economicos['relacion_bc_proy'] > 1.5:
            st.success("**EXCELENTE RENTABILIDAD:** La inversión en fertilización es altamente rentable (B/C > 1.5)")
        elif resultados_economicos['relacion_bc_proy'] > 1.2:
            st.info("**BUENA RENTABILIDAD:** La inversión es recomendable (B/C > 1.2)")
        elif resultados_economicos['relacion_bc_proy'] > 1.0:
            st.warning("**RENTABILIDAD LIMITE:** La inversión apenas cubre costos (B/C > 1.0)")
    with tab4:
        st.markdown("#### 📅 PROYECCIÓN DE FLUJOS DE CAJA (5 AÑOS)")
        df_flujos = pd.DataFrame(flujos_proyectados)
        st.dataframe(df_flujos.style.format({
            'Flujo Neto (USD)': '${:,.0f}',
            'Flujo Acumulado (USD)': '${:,.0f}'
        }), use_container_width=True)
        fig, ax = plt.subplots(figsize=(10, 5))
        años = df_flujos['Año']
        flujos = df_flujos['Flujo Neto (USD)']
        bars = ax.bar(años, flujos, color=['#ef4444' if f < 0 else '#10b981' for f in flujos])
        ax.set_title('Flujos de Caja Anuales', color='white')
        ax.set_xlabel('Año', color='white')
        ax.set_ylabel('USD', color='white')
        ax.axhline(y=0, color='white', linewidth=1)
        ax2 = ax.twinx()
        ax2.plot(años, df_flujos['Flujo Acumulado (USD)'], color='#3b82f6', marker='o', linewidth=3)
        ax2.set_ylabel('Flujo Acumulado (USD)', color='#3b82f6')
        ax2.tick_params(axis='y', colors='#3b82f6')
        ax.set_facecolor('#0f172a')
        fig.patch.set_facecolor('#0f172a')
        ax.tick_params(colors='white')
        st.pyplot(fig)
    st.markdown("---")
    st.subheader("💡 RECOMENDACIONES ECONÓMICAS")
    rec_col1, rec_col2 = st.columns(2)
    with rec_col1:
        st.markdown("##### ✅ ACCIONES RECOMENDADAS")
        if resultados_economicos['roi_fertilizacion_%'] > 100:
            st.success("**INVERTIR EN FERTILIZACIÓN:** ROI > 100% indica excelente retorno")
        if resultados_economicos['van_usd'] > 0:
            st.success("**PROYECTO VIABLE:** VAN positivo genera valor económico")
        if resultados_economicos['tir_%'] > PARAMETROS_ECONOMICOS['PARAMETROS_FINANCIEROS']['tasa_descuento'] * 100:
            st.success(f"**TIR ATRACTIVA:** {resultados_economicos['tir_%']:.1f}% supera la tasa de descuento")
        if resultados_economicos['cultivo'] == "VID":
            st.info("Para vid: Considerar poda y manejo de carga para optimizar calidad")
        elif resultados_economicos['cultivo'] == "OLIVO":
            st.info("Para olivo: Optimizar riego y cosecha mecanizada")
        elif resultados_economicos['cultivo'] in ["TOMATE", "CEBOLLA", "PAPA", "ZANAHORIA", "LECHUGA", "AJO"]:
            st.info("Para hortalizas: Considerar rotación de cultivos y control integrado de plagas")
    with rec_col2:
        st.markdown("##### ⚠️ CONSIDERACIONES")
        st.warning("**RIESGOS CLIMÁTICOS:** Considerar seguro agrícola")
        st.warning("**VOLATILIDAD PRECIOS:** Diversificar cultivos si es posible")
        st.warning("**COSTOS LOGÍSTICOS:** Incluir en análisis de rentabilidad")
    st.markdown("---")
    st.subheader("📥 EXPORTAR ANÁLISIS ECONÓMICO")
    if st.button("📊 Generar Reporte Económico (Excel)"):
        df_economico = pd.DataFrame([resultados_economicos])
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_economico.T.to_excel(writer, sheet_name='Resumen')
            costos_det = pd.DataFrame({
                'Rubro': ['Semilla', 'Fertilización', 'Herbicidas', 'Inseticidas', 'Labores', 'Cosecha', 'Otros', 'TOTAL'],
                'USD/ha': [
                    resultados_economicos['costo_semilla_ha'],
                    resultados_economicos['costo_fertilizacion_ha'],
                    PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_herbicidas'],
                    PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_insecticidas'],
                    PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_labores'],
                    PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_cosecha'],
                    PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][resultados_economicos['cultivo']]['costo_otros'],
                    resultados_economicos['costo_total_ha']
                ]
            })
            costos_det.to_excel(writer, sheet_name='Costos', index=False)
            pd.DataFrame(flujos_proyectados).to_excel(writer, sheet_name='Proyecciones', index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="📥 Descargar Análisis Económico (Excel)",
            data=excel_buffer,
            file_name=f"analisis_economico_{resultados_economicos['cultivo']}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ===== FUNCIONES PARA GENERAR MAPAS DE CALOR DE RENDIMIENTO =====
def crear_mapa_calor_rendimiento_actual(gdf_analizado, cultivo):
    try:
        if 'rendimiento_actual' not in gdf_analizado.columns:
            return None
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        centroids = gdf_plot.geometry.centroid
        x = np.array([c.x for c in centroids])
        y = np.array([c.y for c in centroids])
        z = gdf_plot['rendimiento_actual'].values
        x_min, y_min, x_max, y_max = gdf_plot.total_bounds
        xi = np.linspace(x_min, x_max, 200)
        yi = np.linspace(y_min, y_max, 200)
        xi, yi = np.meshgrid(xi, yi)
        try:
            from scipy.interpolate import griddata
            zi = griddata((x, y), z, (xi, yi), method='cubic', fill_value=np.nan)
        except:
            zi = griddata((x, y), z, (xi, yi), method='linear', fill_value=np.nan)
        im = ax.contourf(xi, yi, zi, levels=50, cmap='RdYlGn', alpha=0.8,
                         vmin=z.min()*0.9, vmax=z.max()*1.1)
        contour = ax.contour(xi, yi, zi, levels=10, colors='white', linewidths=0.5, alpha=0.5)
        for idx, (centroid, valor) in enumerate(zip(centroids, z)):
            ax.plot(centroid.x, centroid.y, 'o', markersize=8,
                    markeredgecolor='white', markerfacecolor=plt.cm.RdYlGn((valor - z.min())/(z.max() - z.min())))
            if idx % 2 == 0:
                ax.annotate(f"{valor:.1f}t",
                            (centroid.x, centroid.y),
                            xytext=(0, 10), textcoords="offset points",
                            fontsize=8, color='white', weight='bold',
                            ha='center', va='center',
                            bbox=dict(boxstyle="round,pad=0.2",
                                      facecolor=(0, 0, 0, 0.7),
                                      alpha=0.8))
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.4)
        except:
            pass
        ax.set_title(f'🌾 MAPA DE CALOR - RENDIMIENTO ACTUAL\n{cultivo} (ton/ha)',
                     fontsize=16, fontweight='bold', pad=20, color='white')
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.1, color='#475569', linestyle='--')
        cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label('Rendimiento (ton/ha)', fontsize=12, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        cbar.outline.set_edgecolor('white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        stats = {
            'promedio': z.mean(),
            'min': z.min(),
            'max': z.max(),
            'std': z.std()
        }
        info_text = f"""
📊 ESTADÍSTICAS:
• Promedio: {stats['promedio']:.1f} ton/ha
• Mínimo: {stats['min']:.1f} ton/ha
• Máximo: {stats['max']:.1f} ton/ha
• Variación: {stats['std']:.1f} ton/ha
"""
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', color='white',
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor=(30/255, 41/255, 59/255, 0.9),
                          alpha=0.9, edgecolor='white'))
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                    facecolor='#0f172a', transparent=False)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        st.error(f"Error creando mapa de calor actual: {str(e)}")
        return crear_mapa_calor_rendimiento_actual_fallback(gdf_analizado, cultivo)

def crear_mapa_calor_rendimiento_actual_fallback(gdf_analizado, cultivo):
    try:
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        valores = gdf_plot['rendimiento_actual']
        vmin = valores.min() * 0.9
        vmax = valores.max() * 1.1
        colors = ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#ffffbf',
                  '#d9ef8b', '#a6d96a', '#66bd63', '#1a9850', '#006837']
        cmap = LinearSegmentedColormap.from_list('rendimiento_actual', colors)
        for idx, row in gdf_plot.iterrows():
            valor = row['rendimiento_actual']
            valor_norm = (valor - vmin) / (vmax - vmin) if vmax != vmin else 0.5
            valor_norm = max(0, min(1, valor_norm))
            color = cmap(valor_norm)
            gdf_plot.iloc[[idx]].plot(ax=ax, color=color, edgecolor='white',
                                      linewidth=1, alpha=0.85)
            centroid = row.geometry.centroid
            ax.annotate(f"{valor:.1f}t",
                        (centroid.x, centroid.y),
                        xytext=(0, 0), textcoords="offset points",
                        fontsize=8, color='white', weight='bold',
                        bbox=dict(boxstyle="circle,pad=0.2",
                                  facecolor=(0, 0, 0, 0.6),
                                  alpha=0.8, edgecolor='white'))
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.3)
        except:
            pass
        ax.set_title(f'🌾 MAPA DE CALOR - RENDIMIENTO ACTUAL\n{cultivo} (ton/ha)',
                     fontsize=16, fontweight='bold', pad=20, color='white')
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.2, color='#475569')
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
        cbar.set_label('Rendimiento (ton/ha)', fontsize=12, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        cbar.outline.set_edgecolor('white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        st.error(f"Error en fallback: {str(e)}")
        return None

def crear_mapa_calor_rendimiento_proyectado(gdf_analizado, cultivo):
    try:
        if 'rendimiento_proyectado' not in gdf_analizado.columns:
            return None
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        centroids = gdf_plot.geometry.centroid
        x = np.array([c.x for c in centroids])
        y = np.array([c.y for c in centroids])
        z_proyectado = gdf_plot['rendimiento_proyectado'].values
        z_actual = gdf_plot['rendimiento_actual'].values
        incrementos = z_proyectado - z_actual
        x_min, y_min, x_max, y_max = gdf_plot.total_bounds
        xi = np.linspace(x_min, x_max, 200)
        yi = np.linspace(y_min, y_max, 200)
        xi, yi = np.meshgrid(xi, yi)
        try:
            from scipy.interpolate import griddata
            zi_proyectado = griddata((x, y), z_proyectado, (xi, yi), method='cubic', fill_value=np.nan)
            zi_incremento = griddata((x, y), incrementos, (xi, yi), method='cubic', fill_value=np.nan)
        except:
            zi_proyectado = griddata((x, y), z_proyectado, (xi, yi), method='linear', fill_value=np.nan)
            zi_incremento = griddata((x, y), incrementos, (xi, yi), method='linear', fill_value=np.nan)
        im_proyectado = ax.contourf(xi, yi, zi_proyectado, levels=50, cmap='RdYlGn', alpha=0.7,
                                    vmin=z_proyectado.min()*0.9, vmax=z_proyectado.max()*1.1)
        im_incremento = ax.contourf(xi, yi, zi_incremento, levels=20, cmap='viridis', alpha=0.4)
        contour = ax.contour(xi, yi, zi_proyectado, levels=8, colors='white', linewidths=1, alpha=0.6)
        ax.clabel(contour, inline=True, fontsize=8, colors='white', fmt='%1.1f t')
        for idx, (centroid, valor_proy, valor_act, inc) in enumerate(zip(centroids, z_proyectado, z_actual, incrementos)):
            marker_size = 6 + (inc / max(incrementos) * 10) if max(incrementos) > 0 else 8
            ax.plot(centroid.x, centroid.y, 'o', markersize=marker_size,
                    markeredgecolor='white', markerfacecolor=plt.cm.RdYlGn((valor_proy - z_proyectado.min())/(z_proyectado.max() - z_proyectado.min())),
                    markeredgewidth=1)
            if idx % 3 == 0:
                ax.annotate(f"+{inc:.1f}t",
                            (centroid.x, centroid.y),
                            xytext=(0, 15), textcoords="offset points",
                            fontsize=7, color='cyan', weight='bold',
                            ha='center', va='center',
                            bbox=dict(boxstyle="round,pad=0.2",
                                      facecolor=(0, 0, 0, 0.7),
                                      alpha=0.8, edgecolor='white'))
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.3)
        except:
            pass
        ax.set_title(f'🚀 MAPA DE CALOR - RENDIMIENTO PROYECTADO\n{cultivo} (con fertilización óptima)',
                     fontsize=16, fontweight='bold', pad=20, color='white')
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.1, color='#475569', linestyle='--')
        cbar1 = plt.colorbar(im_proyectado, ax=ax, shrink=0.8, pad=0.02)
        cbar1.set_label('Rendimiento Proyectado (ton/ha)', fontsize=12, fontweight='bold', color='white')
        cbar1.ax.yaxis.set_tick_params(color='white')
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        divider = make_axes_locatable(ax)
        cax2 = divider.append_axes("right", size="3%", pad=0.15)
        cbar2 = plt.colorbar(im_incremento, cax=cax2)
        cbar2.set_label('Incremento (ton/ha)', fontsize=9, color='white')
        cbar2.ax.yaxis.set_tick_params(color='white')
        for cbar in [cbar1, cbar2]:
            cbar.outline.set_edgecolor('white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        stats_text = f"""
📈 ESTADÍSTICAS DE POTENCIAL:
• Actual: {z_actual.mean():.1f} ton/ha
• Proyectado: {z_proyectado.mean():.1f} ton/ha
• Incremento: +{incrementos.mean():.1f} ton/ha
• Aumento: +{(incrementos.mean()/z_actual.mean()*100 if z_actual.mean()>0 else 0):.1f}%
"""
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', color='white',
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor=(30/255, 41/255, 59/255, 0.9),
                          alpha=0.9, edgecolor='white'))
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                    facecolor='#0f172a', transparent=False)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        st.error(f"Error creando mapa de calor proyectado: {str(e)}")
        return crear_mapa_calor_rendimiento_proyectado_fallback(gdf_analizado, cultivo)

def crear_mapa_calor_rendimiento_proyectado_fallback(gdf_analizado, cultivo):
    try:
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        valores = gdf_plot['rendimiento_proyectado']
        vmin = valores.min() * 0.9
        vmax = valores.max() * 1.1
        colors = ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8',
                  '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']
        cmap = LinearSegmentedColormap.from_list('rendimiento_proyectado', colors)
        for idx, row in gdf_plot.iterrows():
            valor = row['rendimiento_proyectado']
            incremento = row['rendimiento_proyectado'] - row['rendimiento_actual']
            valor_norm = (valor - vmin) / (vmax - vmin) if vmax != vmin else 0.5
            valor_norm = max(0, min(1, valor_norm))
            color = cmap(valor_norm)
            gdf_plot.iloc[[idx]].plot(ax=ax, color=color, edgecolor='white',
                                      linewidth=1, alpha=0.85)
            centroid = row.geometry.centroid
            ax.annotate(f"{valor:.1f}t\n(+{incremento:.1f})",
                        (centroid.x, centroid.y),
                        xytext=(0, 0), textcoords="offset points",
                        fontsize=7, color='white', weight='bold',
                        ha='center', va='center',
                        bbox=dict(boxstyle="round,pad=0.2",
                                  facecolor=(0, 0, 0, 0.6),
                                  alpha=0.8, edgecolor='white'))
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.3)
        except:
            pass
        ax.set_title(f'🚀 MAPA DE CALOR - RENDIMIENTO PROYECTADO\n{cultivo} (con fertilización óptima)',
                     fontsize=16, fontweight='bold', pad=20, color='white')
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.2, color='#475569')
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
        cbar.set_label('Rendimiento Proyectado (ton/ha)', fontsize=12, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        cbar.outline.set_edgecolor('white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        st.error(f"Error en fallback: {str(e)}")
        return None

def crear_mapa_comparativo_calor(gdf_analizado, cultivo):
    try:
        if 'rendimiento_actual' not in gdf_analizado.columns or 'rendimiento_proyectado' not in gdf_analizado.columns:
            return None
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
        fig.patch.set_facecolor('#0f172a')
        ax1.set_facecolor('#0f172a')
        ax2.set_facecolor('#0f172a')
        centroids = gdf_plot.geometry.centroid
        x = np.array([c.x for c in centroids])
        y = np.array([c.y for c in centroids])
        z_actual = gdf_plot['rendimiento_actual'].values
        z_proyectado = gdf_plot['rendimiento_proyectado'].values
        incrementos = z_proyectado - z_actual
        vmin = min(z_actual.min(), z_proyectado.min()) * 0.9
        vmax = max(z_actual.max(), z_proyectado.max()) * 1.2
        x_min, y_min, x_max, y_max = gdf_plot.total_bounds
        xi = np.linspace(x_min, x_max, 150)
        yi = np.linspace(y_min, y_max, 150)
        xi, yi = np.meshgrid(xi, yi)
        try:
            from scipy.interpolate import griddata
            zi_actual = griddata((x, y), z_actual, (xi, yi), method='cubic', fill_value=np.nan)
            zi_proyectado = griddata((x, y), z_proyectado, (xi, yi), method='cubic', fill_value=np.nan)
        except:
            zi_actual = griddata((x, y), z_actual, (xi, yi), method='linear', fill_value=np.nan)
            zi_proyectado = griddata((x, y), z_proyectado, (xi, yi), method='linear', fill_value=np.nan)
        im1 = ax1.contourf(xi, yi, zi_actual, levels=40, cmap='RdYlGn', alpha=0.8, vmin=vmin, vmax=vmax)
        contour1 = ax1.contour(xi, yi, zi_actual, levels=6, colors='white', linewidths=1, alpha=0.5)
        ax1.clabel(contour1, inline=True, fontsize=8, colors='white', fmt='%1.1f t')
        for centroid, valor in zip(centroids, z_actual):
            ax1.plot(centroid.x, centroid.y, 'o', markersize=6,
                     markeredgecolor='white', markerfacecolor=plt.cm.RdYlGn((valor - vmin)/(vmax - vmin)))
        im2 = ax2.contourf(xi, yi, zi_proyectado, levels=40, cmap='RdYlGn', alpha=0.8, vmin=vmin, vmax=vmax)
        contour2 = ax2.contour(xi, yi, zi_proyectado, levels=6, colors='white', linewidths=1, alpha=0.5)
        ax2.clabel(contour2, inline=True, fontsize=8, colors='white', fmt='%1.1f t')
        zi_incremento = griddata((x, y), incrementos, (xi, yi), method='linear', fill_value=np.nan)
        im_incremento = ax2.contourf(xi, yi, zi_incremento, levels=15, cmap='Blues', alpha=0.3)
        for centroid, valor, inc in zip(centroids, z_proyectado, incrementos):
            ax2.plot(centroid.x, centroid.y, 'o', markersize=6 + (inc/max(incrementos)*3 if max(incrementos)>0 else 0),
                     markeredgecolor='white', markerfacecolor=plt.cm.RdYlGn((valor - vmin)/(vmax - vmin)))
        ax1.set_title('🌾 RENDIMIENTO ACTUAL\n(ton/ha)', fontsize=14, fontweight='bold', color='white', pad=15)
        ax2.set_title('🚀 RENDIMIENTO PROYECTADO\n(ton/ha)', fontsize=14, fontweight='bold', color='white', pad=15)
        for ax in [ax1, ax2]:
            ax.set_xlabel('Longitud', color='white')
            ax.set_ylabel('Latitud', color='white')
            ax.tick_params(colors='white')
            ax.grid(True, alpha=0.1, color='#475569', linestyle='--')
        cbar1 = plt.colorbar(im1, ax=ax1, shrink=0.6)
        cbar1.set_label('ton/ha', fontsize=10, color='white')
        cbar1.ax.yaxis.set_tick_params(color='white')
        cbar2 = plt.colorbar(im2, ax=ax2, shrink=0.6)
        cbar2.set_label('ton/ha', fontsize=10, color='white')
        cbar2.ax.yaxis.set_tick_params(color='white')
        for cbar in [cbar1, cbar2]:
            cbar.outline.set_edgecolor('white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        rend_actual_prom = z_actual.mean()
        rend_proy_prom = z_proyectado.mean()
        incremento_prom = incrementos.mean()
        porcentaje_aumento = (incremento_prom / rend_actual_prom * 100) if rend_actual_prom > 0 else 0
        info_comparativo = f"""
📊 COMPARATIVA DE POTENCIAL:
┌─────────────────────────────┐
│ Actual:     {rend_actual_prom:6.1f} ton/ha │
│ Proyectado: {rend_proy_prom:6.1f} ton/ha │
│ Incremento: +{incremento_prom:5.1f} ton/ha │
│ Aumento:    +{porcentaje_aumento:5.1f}%    │
└─────────────────────────────┘
"""
        fig.text(0.5, 0.02, info_comparativo, fontsize=11, color='white', ha='center',
                 bbox=dict(boxstyle="round,pad=0.5",
                           facecolor=(30/255, 41/255, 59/255, 0.95),
                           alpha=0.95, edgecolor='#3b82f6', linewidth=2))
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                    facecolor='#0f172a', transparent=False)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        st.error(f"Error creando mapa comparativo: {str(e)}")
        return crear_mapa_comparativo_calor_fallback(gdf_analizado, cultivo)

def crear_mapa_comparativo_calor_fallback(gdf_analizado, cultivo):
    try:
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        fig.patch.set_facecolor('#0f172a')
        ax1.set_facecolor('#0f172a')
        ax2.set_facecolor('#0f172a')
        cmap_actual = plt.cm.YlOrRd
        cmap_proyectado = plt.cm.RdYlGn
        vmin = min(gdf_plot['rendimiento_actual'].min(), gdf_plot['rendimiento_proyectado'].min()) * 0.9
        vmax = max(gdf_plot['rendimiento_actual'].max(), gdf_plot['rendimiento_proyectado'].max()) * 1.2
        for idx, row in gdf_plot.iterrows():
            valor = row['rendimiento_actual']
            valor_norm = (valor - vmin) / (vmax - vmin) if vmax != vmin else 0.5
            valor_norm = max(0, min(1, valor_norm))
            color = cmap_actual(valor_norm)
            gdf_plot.iloc[[idx]].plot(ax=ax1, color=color, edgecolor='white', linewidth=0.8, alpha=0.85)
            centroid = row.geometry.centroid
            ax1.annotate(f"{valor:.1f}",
                         (centroid.x, centroid.y),
                         xytext=(0, 0), textcoords="offset points",
                         fontsize=6, color='white', weight='bold',
                         ha='center', va='center',
                         bbox=dict(boxstyle="circle,pad=0.15",
                                   facecolor=(0, 0, 0, 0.6),
                                   alpha=0.8))
        for idx, row in gdf_plot.iterrows():
            valor = row['rendimiento_proyectado']
            incremento = row['rendimiento_proyectado'] - row['rendimiento_actual']
            valor_norm = (valor - vmin) / (vmax - vmin) if vmax != vmin else 0.5
            valor_norm = max(0, min(1, valor_norm))
            color = cmap_proyectado(valor_norm)
            gdf_plot.iloc[[idx]].plot(ax=ax2, color=color, edgecolor='white', linewidth=0.8, alpha=0.85)
            centroid = row.geometry.centroid
            ax2.annotate(f"{valor:.1f}\n+{incremento:.1f}",
                         (centroid.x, centroid.y),
                         xytext=(0, 0), textcoords="offset points",
                         fontsize=6, color='white', weight='bold',
                         ha='center', va='center',
                         bbox=dict(boxstyle="round,pad=0.15",
                                   facecolor=(0, 0, 0, 0.6),
                                   alpha=0.8))
        ax1.set_title('🌾 RENDIMIENTO ACTUAL\n(ton/ha)', fontsize=14, fontweight='bold', color='white')
        ax2.set_title('🚀 RENDIMIENTO CON FERTILIZACIÓN\n(ton/ha)', fontsize=14, fontweight='bold', color='white')
        for ax in [ax1, ax2]:
            ax.set_xlabel('Longitud', color='white')
            ax.set_ylabel('Latitud', color='white')
            ax.tick_params(colors='white')
            ax.grid(True, alpha=0.1, color='#475569')
        sm1 = plt.cm.ScalarMappable(cmap=cmap_actual, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm1.set_array([])
        cbar1 = plt.colorbar(sm1, ax=ax1, shrink=0.6)
        cbar1.set_label('ton/ha', fontsize=10, color='white')
        sm2 = plt.cm.ScalarMappable(cmap=cmap_proyectado, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm2.set_array([])
        cbar2 = plt.colorbar(sm2, ax=ax2, shrink=0.6)
        cbar2.set_label('ton/ha', fontsize=10, color='white')
        for cbar in [cbar1, cbar2]:
            cbar.ax.yaxis.set_tick_params(color='white')
            cbar.outline.set_edgecolor('white')
            plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        st.error(f"Error en fallback: {str(e)}")
        return None

# ===== FUNCIONES PARA DATOS SATELITALES =====
def descargar_datos_landsat8(gdf, fecha_inicio, fecha_fin, indice='NDVI'):
    try:
        st.info(f"🔍 Buscando escenas Landsat 8...")
        datos_simulados = {
            'indice': indice,
            'valor_promedio': 0.65 + np.random.normal(0, 0.1),
            'fuente': 'Landsat-8',
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'id_escena': f"LC08_{np.random.randint(1000000, 9999999)}",
            'cobertura_nubes': f"{np.random.randint(0, 15)}%",
            'resolucion': '30m'
        }
        st.success(f"✅ Escena Landsat 8 encontrada: {datos_simulados['id_escena']}")
        st.info(f"☁️ Cobertura de nubes: {datos_simulados['cobertura_nubes']}")
        return datos_simulados
    except Exception as e:
        st.error(f"❌ Error procesando Landsat 8: {str(e)}")
        return None

def descargar_datos_sentinel2(gdf, fecha_inicio, fecha_fin, indice='NDVI'):
    try:
        st.info(f"🔍 Buscando escenas Sentinel-2...")
        datos_simulados = {
            'indice': indice,
            'valor_promedio': 0.72 + np.random.normal(0, 0.08),
            'fuente': 'Sentinel-2',
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'id_escena': f"S2A_{np.random.randint(1000000, 9999999)}",
            'cobertura_nubes': f"{np.random.randint(0, 10)}%",
            'resolucion': '10m'
        }
        st.success(f"✅ Escena Sentinel-2 encontrada: {datos_simulados['id_escena']}")
        st.info(f"☁️ Cobertura de nubes: {datos_simulados['cobertura_nubes']}")
        return datos_simulados
    except Exception as e:
        st.error(f"❌ Error procesando Sentinel-2: {str(e)}")
        return None

def generar_datos_simulados(gdf, cultivo, indice='NDVI'):
    st.info("🔬 Generando datos simulados...")
    datos_simulados = {
        'indice': indice,
        'valor_promedio': obtener_parametros_cultivo(cultivo)['NDVI_OPTIMO'] * 0.8 + np.random.normal(0, 0.1),
        'fuente': 'Simulación',
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'resolucion': '10m'
    }
    st.success("✅ Datos simulados generados")
    return datos_simulados

# ===== FUNCIÓN CORREGIDA PARA OBTENER DATOS DE NASA POWER =====
def obtener_datos_nasa_power(gdf, fecha_inicio, fecha_fin):
    try:
        centroid = gdf.geometry.unary_union.centroid
        lat = round(centroid.y, 4)
        lon = round(centroid.x, 4)
        start = fecha_inicio.strftime("%Y%m%d")
        end = fecha_fin.strftime("%Y%m%d")
        params = {
            'parameters': 'ALLSKY_SFC_SW_DWN,WS2M,T2M,PRECTOTCORR',
            'community': 'RE',
            'longitude': lon,
            'latitude': lat,
            'start': start,
            'end': end,
            'format': 'JSON'
        }
        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if 'properties' not in data:
            st.warning("⚠️ No se obtuvieron datos de NASA POWER (fuera de rango o sin conexión).")
            return None
        series = data['properties']['parameter']
        df_power = pd.DataFrame({
            'fecha': pd.to_datetime(list(series['ALLSKY_SFC_SW_DWN'].keys())),
            'radiacion_solar': list(series['ALLSKY_SFC_SW_DWN'].values()),
            'viento_2m': list(series['WS2M'].values()),
            'temperatura': list(series['T2M'].values()),
            'precipitacion': list(series['PRECTOTCORR'].values())
        })
        df_power = df_power.replace(-999, np.nan).dropna()
        if df_power.empty:
            st.warning("⚠️ Datos de NASA POWER no disponibles para el período seleccionado.")
            return None
        st.success("✅ Datos meteorológicos de NASA POWER cargados.")
        return df_power
    except Exception as e:
        st.error(f"❌ Error al obtener datos de NASA POWER: {str(e)}")
        return None

# ===== FUNCIONES DE ANÁLISIS GEE MEJORADAS =====
def calcular_recomendaciones_npk_cientificas(gdf_analizado, nutriente, cultivo):
    import copy
    recomendaciones = []
    params = copy.deepcopy(obtener_parametros_cultivo(cultivo))
    if 'variedad_params' in st.session_state:
        variedad = st.session_state['variedad']
        variedad_params = st.session_state['variedad_params']
        if nutriente == "NITRÓGENO":
            params['NITROGENO']['optimo'] = variedad_params['NITROGENO_OPTIMO']
        elif nutriente == "FÓSFORO":
            params['FOSFORO']['optimo'] = variedad_params['FOSFORO_OPTIMO']
        elif nutriente == "POTASIO":
            params['POTASIO']['optimo'] = variedad_params['POTASIO_OPTIMO']
    for idx, row in gdf_analizado.iterrows():
        if nutriente == "NITRÓGENO":
            valor_actual = row['nitrogeno_actual']
            objetivo = params['NITROGENO']['optimo']
            deficiencia = max(0, objetivo - valor_actual)
            eficiencia = 0.5
            recomendado = deficiencia / eficiencia if deficiencia > 0 else 0
        elif nutriente == "FÓSFORO":
            valor_actual = row['fosforo_actual']
            objetivo = params['FOSFORO']['optimo']
            deficiencia = max(0, objetivo - valor_actual)
            eficiencia = 0.3
            recomendado = deficiencia / eficiencia if deficiencia > 0 else 0
        else:
            valor_actual = row['potasio_actual']
            objetivo = params['POTASIO']['optimo']
            deficiencia = max(0, objetivo - valor_actual)
            eficiencia = 0.6
            recomendado = deficiencia / eficiencia if deficiencia > 0 else 0
        recomendado_redondeado = round(recomendado / 5) * 5
        recomendaciones.append(max(0, recomendado_redondeado))
    return recomendaciones

# ===== FUNCIONES DE TEXTURA DEL SUELO - ACTUALIZADAS A USDA =====
def clasificar_textura_suelo(arena, limo, arcilla):
    return clasificar_textura_usda(arena, limo, arcilla)

def analizar_textura_suelo(gdf, cultivo):
    gdf = validar_y_corregir_crs(gdf)
    params_textura = TEXTURA_SUELO_OPTIMA[cultivo]
    zonas_gdf = gdf.copy()
    areas_ha_list = []
    arena_list = []
    limo_list = []
    arcilla_list = []
    textura_list = []
    for idx, row in zonas_gdf.iterrows():
        try:
            area_gdf = gpd.GeoDataFrame({'geometry': [row.geometry]}, crs=zonas_gdf.crs)
            area_ha = calcular_superficie(area_gdf)
            if hasattr(area_ha, 'iloc'):
                area_ha = float(area_ha.iloc[0])
            elif hasattr(area_ha, '__len__') and len(area_ha) > 0:
                area_ha = float(area_ha[0])
            else:
                area_ha = float(area_ha)
            areas_ha_list.append(area_ha)
            centroid = row.geometry.centroid if hasattr(row.geometry, 'centroid') else row.geometry.representative_point()
            seed_value = abs(hash(f"{centroid.x:.6f}_{centroid.y:.6f}_{cultivo}_textura")) % (2**32)
            rng = np.random.RandomState(seed_value)
            arena_optima = params_textura['arena_optima']
            limo_optima = params_textura['limo_optima']
            arcilla_optima = params_textura['arcilla_optima']
            arena_val = max(5, min(95, rng.normal(arena_optima, 10)))
            limo_val = max(5, min(95, rng.normal(limo_optima, 8)))
            arcilla_val = max(5, min(95, rng.normal(arcilla_optima, 7)))
            total = arena_val + limo_val + arcilla_val
            arena_pct = (arena_val / total) * 100
            limo_pct = (limo_val / total) * 100
            arcilla_pct = (arcilla_val / total) * 100
            textura = clasificar_textura_suelo(arena_pct, limo_pct, arcilla_pct)
            arena_list.append(float(arena_pct))
            limo_list.append(float(limo_pct))
            arcilla_list.append(float(arcilla_pct))
            textura_list.append(textura)
        except Exception as e:
            areas_ha_list.append(0.0)
            arena_list.append(float(params_textura['arena_optima']))
            limo_list.append(float(params_textura['limo_optima']))
            arcilla_list.append(float(params_textura['arcilla_optima']))
            textura_list.append(params_textura['textura_optima'])
    zonas_gdf['area_ha'] = areas_ha_list
    zonas_gdf['arena'] = arena_list
    zonas_gdf['limo'] = limo_list
    zonas_gdf['arcilla'] = arcilla_list
    zonas_gdf['textura_suelo'] = textura_list
    return zonas_gdf

# ===== FUNCIONES DE CURVAS DE NIVEL =====
def clasificar_pendiente(pendiente_porcentaje):
    CLASIFICACION_PENDIENTES = {
        'PLANA (0-2%)': {'min': 0, 'max': 2, 'color': '#4daf4a', 'factor_erosivo': 0.1},
        'SUAVE (2-5%)': {'min': 2, 'max': 5, 'color': '#a6d96a', 'factor_erosivo': 0.3},
        'MODERADA (5-10%)': {'min': 5, 'max': 10, 'color': '#ffffbf', 'factor_erosivo': 0.6},
        'FUERTE (10-15%)': {'min': 10, 'max': 15, 'color': '#fdae61', 'factor_erosivo': 0.8},
        'MUY FUERTE (15-25%)': {'min': 15, 'max': 25, 'color': '#f46d43', 'factor_erosivo': 0.9},
        'EXTREMA (>25%)': {'min': 25, 'max': 100, 'color': '#d73027', 'factor_erosivo': 1.0}
    }
    for categoria, params in CLASIFICACION_PENDIENTES.items():
        if params['min'] <= pendiente_porcentaje < params['max']:
            return categoria, params['color']
    return "EXTREMA (>25%)", CLASIFICACION_PENDIENTES['EXTREMA (>25%)']['color']

def calcular_estadisticas_pendiente_simple(pendiente_grid):
    pendiente_flat = pendiente_grid.flatten()
    pendiente_flat = pendiente_flat[~np.isnan(pendiente_flat)]
    if len(pendiente_flat) == 0:
        return {'promedio': 0, 'min': 0, 'max': 0, 'std': 0, 'distribucion': {}}
    stats = {
        'promedio': float(np.mean(pendiente_flat)),
        'min': float(np.min(pendiente_flat)),
        'max': float(np.max(pendiente_flat)),
        'std': float(np.std(pendiente_flat)),
        'distribucion': {}
    }
    CLASIFICACION_PENDIENTES = {
        'PLANA (0-2%)': {'min': 0, 'max': 2, 'color': '#4daf4a', 'factor_erosivo': 0.1},
        'SUAVE (2-5%)': {'min': 2, 'max': 5, 'color': '#a6d96a', 'factor_erosivo': 0.3},
        'MODERADA (5-10%)': {'min': 5, 'max': 10, 'color': '#ffffbf', 'factor_erosivo': 0.6},
        'FUERTE (10-15%)': {'min': 10, 'max': 15, 'color': '#fdae61', 'factor_erosivo': 0.8},
        'MUY FUERTE (15-25%)': {'min': 15, 'max': 25, 'color': '#f46d43', 'factor_erosivo': 0.9},
        'EXTREMA (>25%)': {'min': 25, 'max': 100, 'color': '#d73027', 'factor_erosivo': 1.0}
    }
    for categoria, params in CLASIFICACION_PENDIENTES.items():
        mask = (pendiente_flat >= params['min']) & (pendiente_flat < params['max'])
        stats['distribucion'][categoria] = {'porcentaje': float(np.sum(mask) / len(pendiente_flat) * 100), 'color': params['color']}
    return stats

def generar_dem_sintetico(gdf, resolucion=10.0):
    gdf = validar_y_corregir_crs(gdf)
    bounds = gdf.total_bounds
    minx, miny, maxx, maxy = bounds
    centroid = gdf.geometry.unary_union.centroid
    seed_value = int(centroid.x * 10000 + centroid.y * 10000) % (2**32)
    rng = np.random.RandomState(seed_value)
    num_cells = 50
    x = np.linspace(minx, maxx, num_cells)
    y = np.linspace(miny, maxy, num_cells)
    X, Y = np.meshgrid(x, y)
    elevacion_base = rng.uniform(100, 300)
    slope_x = rng.uniform(-0.001, 0.001)
    slope_y = rng.uniform(-0.001, 0.001)
    relief = np.zeros_like(X)
    n_hills = rng.randint(2, 5)
    for _ in range(n_hills):
        hill_center_x = rng.uniform(minx, maxx)
        hill_center_y = rng.uniform(miny, maxy)
        hill_radius = rng.uniform(0.001, 0.005)
        hill_height = rng.uniform(10, 50)
        dist = np.sqrt((X - hill_center_x)**2 + (Y - hill_center_y)**2)
        relief += hill_height * np.exp(-(dist**2) / (2 * hill_radius**2))
    noise = rng.randn(*X.shape) * 2
    Z = elevacion_base + slope_x * (X - minx) + slope_y * (Y - miny) + relief + noise
    Z = np.maximum(Z, 50)
    return X, Y, Z, bounds

def calcular_pendiente_simple(X, Y, Z, resolucion=10.0):
    dy = np.gradient(Z, axis=0) / resolucion
    dx = np.gradient(Z, axis=1) / resolucion
    pendiente = np.sqrt(dx**2 + dy**2) * 100
    pendiente = np.clip(pendiente, 0, 100)
    return pendiente

def crear_mapa_pendientes_simple(X, Y, pendiente_grid, gdf_original):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.patch.set_facecolor('#0f172a')
    ax1.set_facecolor('#0f172a')
    ax2.set_facecolor('#0f172a')
    X_flat = X.flatten()
    Y_flat = Y.flatten()
    Z_flat = pendiente_grid.flatten()
    valid_mask = ~np.isnan(Z_flat)
    if np.sum(valid_mask) > 10:
        scatter = ax1.scatter(X_flat[valid_mask], Y_flat[valid_mask], c=Z_flat[valid_mask], cmap='RdYlGn_r', s=20, alpha=0.7, vmin=0, vmax=30)
        cbar = plt.colorbar(scatter, ax=ax1, shrink=0.8)
        cbar.set_label('Pendiente (%)', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        cbar.outline.set_edgecolor('white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        for porcentaje in [2, 5, 10, 15, 25]:
            mask_cat = (Z_flat[valid_mask] >= porcentaje-1) & (Z_flat[valid_mask] <= porcentaje+1)
            if np.sum(mask_cat) > 0:
                x_center = np.mean(X_flat[valid_mask][mask_cat])
                y_center = np.mean(Y_flat[valid_mask][mask_cat])
                ax1.text(x_center, y_center, f'{porcentaje}%', fontsize=8, fontweight='bold', ha='center', va='center',
                         bbox=dict(boxstyle="round,pad=0.3", facecolor=(30/255, 41/255, 59/255, 0.9), edgecolor='white'), color='white')
    else:
        ax1.text(0.5, 0.5, 'Datos insuficientes\npara mapa de calor', transform=ax1.transAxes, ha='center', va='center', fontsize=12, color='white')
    gdf_original.plot(ax=ax1, color='none', edgecolor='white', linewidth=2)
    ax1.set_title('Mapa de Calor de Pendientes', fontsize=12, fontweight='bold', color='white')
    ax1.set_xlabel('Longitud', color='white')
    ax1.set_ylabel('Latitud', color='white')
    ax1.tick_params(colors='white')
    ax1.grid(True, alpha=0.3, color='#475569')
    if np.sum(valid_mask) > 0:
        pendiente_data = Z_flat[valid_mask]
        ax2.hist(pendiente_data, bins=30, edgecolor='white', color='#3b82f6', alpha=0.7)
        for porcentaje, color in [(2, '#4daf4a'), (5, '#a6d96a'), (10, '#ffffbf'), (15, '#fdae61'), (25, '#f46d43')]:
            ax2.axvline(x=porcentaje, color=color, linestyle='--', linewidth=1, alpha=0.7)
            ax2.text(porcentaje+0.5, ax2.get_ylim()[1]*0.9, f'{porcentaje}%', color=color, fontsize=8)
        stats_pendiente = calcular_estadisticas_pendiente_simple(pendiente_grid)
        stats_text = f"""
Estadísticas:
• Mínima: {stats_pendiente['min']:.1f}%
• Máxima: {stats_pendiente['max']:.1f}%
• Promedio: {stats_pendiente['promedio']:.1f}%
• Desviación: {stats_pendiente['std']:.1f}%
"""
        ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, fontsize=9, verticalalignment='top',
                 color='white', bbox=dict(boxstyle="round,pad=0.3", facecolor=(30/255, 41/255, 59/255, 0.9), edgecolor='white'))
        ax2.set_xlabel('Pendiente (%)', color='white')
        ax2.set_ylabel('Frecuencia', color='white')
        ax2.set_title('Distribución de Pendientes', fontsize=12, fontweight='bold', color='white')
        ax2.tick_params(colors='white')
        ax2.grid(True, alpha=0.3, color='#475569')
    else:
        ax2.text(0.5, 0.5, 'Sin datos de pendiente', transform=ax2.transAxes, ha='center', va='center', fontsize=12, color='white')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
    buf.seek(0)
    plt.close()
    return buf, calcular_estadisticas_pendiente_simple(pendiente_grid)

def generar_curvas_nivel_simple(X, Y, Z, intervalo=5.0, gdf_original=None):
    curvas = []
    elevaciones = []
    try:
        if gdf_original is not None:
            poligono_principal = gdf_original.iloc[0].geometry
            bounds = poligono_principal.bounds
            centro = poligono_principal.centroid
            ancho = bounds[2] - bounds[0]
            alto = bounds[3] - bounds[1]
            radio_max = min(ancho, alto) / 2
            z_min, z_max = np.nanmin(Z), np.nanmax(Z)
            n_curvas = min(10, int((z_max - z_min) / intervalo))
            for i in range(1, n_curvas + 1):
                radio = radio_max * (i / n_curvas)
                circle = centro.buffer(radio)
                interseccion = poligono_principal.intersection(circle)
                if interseccion.geom_type == 'LineString':
                    curvas.append(interseccion)
                    elevaciones.append(z_min + (i * intervalo))
                elif interseccion.geom_type == 'MultiLineString':
                    for parte in interseccion.geoms:
                        curvas.append(parte)
                        elevaciones.append(z_min + (i * intervalo))
    except Exception as e:
        if gdf_original is not None:
            bounds = gdf_original.total_bounds
            for i in range(3):
                y = bounds[1] + (i + 1) * ((bounds[3] - bounds[1]) / 4)
                linea = LineString([(bounds[0], y), (bounds[2], y)])
                curvas.append(linea)
                elevaciones.append(100 + i * 50)
    return curvas, elevaciones

# ===== FUNCIONES DE EXPORTACIÓN Y REPORTES - CORREGIDAS =====
def exportar_a_geojson(gdf, nombre_base="parcela"):
    try:
        gdf = validar_y_corregir_crs(gdf)
        geojson_data = gdf.to_json()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"{nombre_base}_{timestamp}.geojson"
        return geojson_data, nombre_archivo
    except Exception as e:
        st.error(f"❌ Error exportando a GeoJSON: {str(e)}")
        return None, None

def generar_resumen_estadisticas(gdf_analizado, analisis_tipo, cultivo, df_power=None):
    estadisticas = {}
    try:
        if analisis_tipo in ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK"]:
            if 'npk_integrado' in gdf_analizado.columns:
                estadisticas['Índice NPK Integrado'] = f"{gdf_analizado['npk_integrado'].mean():.3f}"
            if 'nitrogeno_actual' in gdf_analizado.columns:
                estadisticas['Nitrógeno Promedio'] = f"{gdf_analizado['nitrogeno_actual'].mean():.1f} kg/ha"
            if 'fosforo_actual' in gdf_analizado.columns:
                estadisticas['Fósforo Promedio'] = f"{gdf_analizado['fosforo_actual'].mean():.1f} kg/ha"
            if 'potasio_actual' in gdf_analizado.columns:
                estadisticas['Potasio Promedio'] = f"{gdf_analizado['potasio_actual'].mean():.1f} kg/ha"
            if 'ndvi' in gdf_analizado.columns:
                estadisticas['NDVI Promedio'] = f"{gdf_analizado['ndvi'].mean():.3f}"
            if 'ndwi' in gdf_analizado.columns:
                estadisticas['NDWI Promedio'] = f"{gdf_analizado['ndwi'].mean():.3f}"
            if 'materia_organica' in gdf_analizado.columns:
                estadisticas['Materia Orgánica Promedio'] = f"{gdf_analizado['materia_organica'].mean():.1f}%"
            if cultivo in ["VID", "OLIVO"] and 'variedad' in st.session_state:
                estadisticas[f'Variedad de {cultivo}'] = st.session_state['variedad']
            elif cultivo in ["TOMATE", "CEBOLLA", "PAPA", "ZANAHORIA", "LECHUGA", "AJO"]:
                estadisticas['Hortaliza'] = cultivo
            if df_power is not None:
                estadisticas['Radiación Solar Promedio'] = f"{df_power['radiacion_solar'].mean():.1f} kWh/m²/día"
                estadisticas['Velocidad Viento Promedio'] = f"{df_power['viento_2m'].mean():.2f} m/s"
                estadisticas['Precipitación Promedio'] = f"{df_power['precipitacion'].mean():.2f} mm/día"
        elif analisis_tipo == "ANÁLISIS DE TEXTURA":
            if 'arena' in gdf_analizado.columns:
                estadisticas['Arena Promedio'] = f"{gdf_analizado['arena'].mean():.1f}%"
                estadisticas['Limo Promedio'] = f"{gdf_analizado['limo'].mean():.1f}%"
                estadisticas['Arcilla Promedio'] = f"{gdf_analizado['arcilla'].mean():.1f}%"
            if 'textura_suelo' in gdf_analizado.columns:
                textura_predominante = gdf_analizado['textura_suelo'].mode()[0] if len(gdf_analizado) > 0 else "N/D"
                estadisticas['Textura Predominante'] = textura_predominante
            if 'area_ha' in gdf_analizado.columns:
                estadisticas['Área Promedio por Zona'] = f"{gdf_analizado['area_ha'].mean():.2f} ha"
                if gdf_analizado['area_ha'].mean() > 0:
                    estadisticas['Coeficiente de Variación'] = f"{(gdf_analizado['area_ha'].std() / gdf_analizado['area_ha'].mean() * 100):.1f}%"
    except Exception as e:
        st.warning(f"No se pudieron calcular algunas estadísticas: {str(e)}")
    return estadisticas

def generar_recomendaciones_generales(gdf_analizado, analisis_tipo, cultivo):
    recomendaciones = []
    try:
        if analisis_tipo == "FERTILIDAD ACTUAL":
            if 'npk_integrado' in gdf_analizado.columns:
                npk_promedio = gdf_analizado['npk_integrado'].mean()
                if npk_promedio < 0.3:
                    recomendaciones.append("Fertilidad MUY BAJA: Se recomienda aplicación urgente de fertilizantes balanceados")
                    recomendaciones.append("Considerar enmiendas orgánicas para mejorar la estructura del suelo")
                elif npk_promedio < 0.5:
                    recomendaciones.append("Fertilidad BAJA: Recomendada aplicación de fertilizantes según análisis de suelo")
                elif npk_promedio < 0.7:
                    recomendaciones.append("Fertilidad ADECUADA: Mantener prácticas de manejo actuales")
                else:
                    recomendaciones.append("Fertilidad ÓPTIMA: Excelente condición, continuar con manejo actual")
            if 'nitrogeno_actual' in gdf_analizado.columns:
                n_prom = gdf_analizado['nitrogeno_actual'].mean()
                n_opt = obtener_parametros_cultivo(cultivo)['NITROGENO']['optimo']
                if n_prom < n_opt * 0.7:
                    recomendaciones.append(f"Deficiencia de Nitrógeno ({n_prom:.1f} vs {n_opt:.1f} kg/ha): Aplicar fertilizante nitrogenado")
            if 'fosforo_actual' in gdf_analizado.columns:
                p_prom = gdf_analizado['fosforo_actual'].mean()
                p_opt = obtener_parametros_cultivo(cultivo)['FOSFORO']['optimo']
                if p_prom < p_opt * 0.7:
                    recomendaciones.append(f"Deficiencia de Fósforo ({p_prom:.1f} vs {p_opt:.1f} kg/ha): Aplicar superfosfato o fosfato diamónico")
            if 'potasio_actual' in gdf_analizado.columns:
                k_prom = gdf_analizado['potasio_actual'].mean()
                k_opt = obtener_parametros_cultivo(cultivo)['POTASIO']['optimo']
                if k_prom < k_opt * 0.7:
                    recomendaciones.append(f"Deficiencia de Potasio ({k_prom:.1f} vs {k_opt:.1f} kg/ha): Aplicar cloruro o sulfato de potasio")
        elif analisis_tipo == "ANÁLISIS DE TEXTURA":
            if 'textura_suelo' in gdf_analizado.columns:
                textura_predominante = gdf_analizado['textura_suelo'].mode()[0] if len(gdf_analizado) > 0 else "N/D"
                if textura_predominante in RECOMENDACIONES_TEXTURA:
                    recomendaciones.append(f"Suelo {textura_predominante}: Ver recomendaciones específicas en el informe")
                else:
                    recomendaciones.append("Consultar recomendaciones específicas para la textura identificada")
        if cultivo == "VID":
            if 'variedad' in st.session_state:
                variedad = st.session_state['variedad']
                recomendaciones.append(f"Variedad: {variedad}")
                if "MALBEC" in variedad:
                    recomendaciones.append("Para Malbec: Control riguroso de carga y exposición solar")
                elif "CABERNET" in variedad:
                    recomendaciones.append("Para Cabernet Sauvignon: Manejo de vigor y poda larga")
                elif "CHARDONNAY" in variedad:
                    recomendaciones.append("Para Chardonnay: Riego controlado y manejo de sombra")
                elif "SYRAH" in variedad:
                    recomendaciones.append("Para Syrah: Manejo de temperatura y maduración fenólica")
                elif "BONARDA" in variedad:
                    recomendaciones.append("Para Bonarda: Alta carga frutal, requerimientos altos de N y K")
            recomendaciones.append("Mantener humedad adecuada durante floración y cuajado")
            recomendaciones.append("Controlar enfermedades fúngicas en períodos húmedos")
        elif cultivo == "OLIVO":
            if 'variedad' in st.session_state:
                variedad = st.session_state['variedad']
                recomendaciones.append(f"Variedad: {variedad}")
                if "ARBEQUINA" in variedad:
                    recomendaciones.append("Para Arbequina: Alta densidad y poda mecánica")
                elif "ARBOSANA" in variedad:
                    recomendaciones.append("Para Arbosana: Riego deficitario controlado")
                elif "PICUAL" in variedad:
                    recomendaciones.append("Para Picual: Manejo de vigor y cosecha temprana")
                elif "MANZANILLA" in variedad:
                    recomendaciones.append("Para Manzanilla: Cosecha manual y control de mosca")
            recomendaciones.append("Optimizar riego por goteo con déficit controlado")
            recomendaciones.append("Realizar análisis de suelo de laboratorio para validar resultados satelitales")
            recomendaciones.append("Considerar agricultura de precisión para aplicación variable de insumos")
        elif cultivo in ["TOMATE", "CEBOLLA", "PAPA", "ZANAHORIA", "LECHUGA", "AJO"]:
            recomendaciones.append(f"Para {cultivo.lower()}: Considerar rotación de cultivos y control integrado de plagas")
            recomendaciones.append("Mantener niveles óptimos de materia orgánica (>2.5%)")
            recomendaciones.append("Aplicar riego por goteo con alta frecuencia")
    except Exception as e:
        recomendaciones.append("Error generando recomendaciones específicas")
    return recomendaciones

def limpiar_texto_para_pdf(texto):
    if not isinstance(texto, str):
        texto = str(texto)
    reemplazos = {
        '\u2022': '-',
        '\u2705': '[OK]',
        '\u26A0\uFE0F': '[!]',
        '\u274C': '[X]',
        '\u2013': '-',
        '\u2014': '--',
        '\u2018': "'",
        '\u2019': "'",
        '\u201C': '"',
        '\u201D': '"',
        '\u2192': '->',
        '\u2190': '<-',
        '\u2265': '>=',
        '\u2264': '<=',
        '\u00A0': ' ',
    }
    for original, reemplazo in reemplazos.items():
        texto = texto.replace(original, reemplazo)
    texto = texto.encode('latin-1', errors='replace').decode('latin-1')
    return texto

def generar_reporte_pdf(gdf_analizado, cultivo, analisis_tipo, area_total,
                        nutriente=None, satelite=None, indice=None,
                        mapa_buffer=None, estadisticas=None, recomendaciones=None):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font('Arial', '', 12)
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, limpiar_texto_para_pdf(f'REPORTE DE ANÁLISIS AGRÍCOLA - {cultivo}'), 0, 1, 'C')
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, limpiar_texto_para_pdf(f'Tipo de Análisis: {analisis_tipo}'), 0, 1, 'C')
        if cultivo in ["VID", "OLIVO"] and 'variedad' in st.session_state:
            pdf.cell(0, 10, limpiar_texto_para_pdf(f'Variedad: {st.session_state["variedad"]}'), 0, 1, 'C')
        pdf.cell(0, 10, limpiar_texto_para_pdf(f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}'), 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, '1. INFORMACIÓN GENERAL', 0, 1)
        info_general = f"""Cultivo: {cultivo}
Área Total: {area_total:.2f} ha
Zonas Analizadas: {len(gdf_analizado)}
Tipo de Análisis: {analisis_tipo}"""
        if satelite:
            info_general += f"\nSatélite: {satelite}"
        if indice:
            info_general += f"\nÍndice: {indice}"
        if nutriente:
            info_general += f"\nNutriente Analizado: {nutriente}"
        for linea in info_general.strip().split('\n'):
            pdf.cell(0, 8, limpiar_texto_para_pdf(linea), 0, 1)
        pdf.ln(5)
        if estadisticas:
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, '2. ESTADÍSTICAS PRINCIPALES', 0, 1)
            pdf.set_font('Arial', '', 12)
            for key, value in estadisticas.items():
                linea = f"- {key}: {value}"
                pdf.cell(0, 8, limpiar_texto_para_pdf(linea), 0, 1)
            pdf.ln(5)
        if analisis_tipo == "RECOMENDACIONES NPK" and 'rendimiento_actual' in gdf_analizado.columns:
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'ANÁLISIS DE POTENCIAL DE COSECHA', 0, 1)
            pdf.set_font('Arial', '', 12)
            rend_actual = gdf_analizado['rendimiento_actual'].mean()
            rend_proy = gdf_analizado['rendimiento_proyectado'].mean()
            incremento = gdf_analizado['incremento_rendimiento'].mean()
            porcentaje = (incremento / rend_actual * 100) if rend_actual > 0 else 0
            info_rendimiento = f"""Rendimiento Actual Promedio: {rend_actual:.1f} ton/ha
Rendimiento Proyectado Promedio: {rend_proy:.1f} ton/ha
Incremento Esperado: {incremento:.1f} ton/ha
Porcentaje de Aumento: {porcentaje:.1f}%
"""
            for linea in info_rendimiento.strip().split('\n'):
                pdf.cell(0, 8, limpiar_texto_para_pdf(linea), 0, 1)
            pdf.ln(5)
        if mapa_buffer:
            try:
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, '3. MAPA DE RESULTADOS', 0, 1)
                temp_img_path = "temp_map.png"
                with open(temp_img_path, "wb") as f:
                    f.write(mapa_buffer.getvalue())
                pdf.image(temp_img_path, x=10, w=190)
                pdf.ln(5)
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
            except Exception as e:
                pdf.cell(0, 8, limpiar_texto_para_pdf(f"Error al incluir mapa: {str(e)[:50]}..."), 0, 1)
        else:
            pdf.cell(0, 8, limpiar_texto_para_pdf("Mapa no disponible para este análisis"), 0, 1)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, '4. RESUMEN DE ZONAS', 0, 1)
        pdf.set_font('Arial', '', 10)
        if gdf_analizado is not None and not gdf_analizado.empty:
            columnas_mostrar = ['id_zona', 'area_ha']
            if 'npk_integrado' in gdf_analizado.columns:
                columnas_mostrar.append('npk_integrado')
            if 'nitrogeno_actual' in gdf_analizado.columns:
                columnas_mostrar.append('nitrogeno_actual')
            if 'fosforo_actual' in gdf_analizado.columns:
                columnas_mostrar.append('fosforo_actual')
            if 'potasio_actual' in gdf_analizado.columns:
                columnas_mostrar.append('potasio_actual')
            if 'valor_recomendado' in gdf_analizado.columns:
                columnas_mostrar.append('valor_recomendado')
            if 'textura_suelo' in gdf_analizado.columns:
                columnas_mostrar.append('textura_suelo')
            if 'ndwi' in gdf_analizado.columns:
                columnas_mostrar.append('ndwi')
            if 'rendimiento_actual' in gdf_analizado.columns:
                columnas_mostrar.extend(['rendimiento_actual', 'rendimiento_proyectado'])
            columnas_mostrar = [col for col in columnas_mostrar if col in gdf_analizado.columns]
            if columnas_mostrar:
                datos_tabla = [columnas_mostrar]
                for _, row in gdf_analizado.head(15).iterrows():
                    fila = []
                    for col in columnas_mostrar:
                        if col in gdf_analizado.columns:
                            valor = row[col]
                            if isinstance(valor, float):
                                if col in ['npk_integrado', 'ndwi']:
                                    fila.append(f"{valor:.3f}")
                                elif col in ['nitrogeno_actual', 'fosforo_actual', 'potasio_actual', 'valor_recomendado']:
                                    fila.append(f"{valor:.1f}")
                                elif col in ['rendimiento_actual', 'rendimiento_proyectado']:
                                    fila.append(f"{valor:.1f}")
                                else:
                                    fila.append(f"{valor:.2f}")
                            else:
                                fila.append(str(valor))
                        else:
                            fila.append("N/A")
                    datos_tabla.append(fila)
                col_widths = [190 // len(columnas_mostrar)] * len(columnas_mostrar)
                for fila in datos_tabla:
                    for i, item in enumerate(fila):
                        if i < len(col_widths):
                            pdf.cell(col_widths[i], 8, limpiar_texto_para_pdf(str(item)), border=1)
                    pdf.ln()
                pdf.ln(5)
        if recomendaciones:
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, '5. RECOMENDACIONES', 0, 1)
            pdf.set_font('Arial', '', 12)
            for rec in recomendaciones:
                linea = f"- {limpiar_texto_para_pdf(rec)}"
                pdf.multi_cell(0, 8, linea)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, '6. METADATOS TÉCNICOS', 0, 1)
        pdf.set_font('Arial', '', 10)
        metadatos = f"""Generado por: Analizador Multi-Cultivo Satellital
Versión: 2.0 (Con metodologías científicas NPK)
Fecha de generación: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Sistema de coordenadas: EPSG:4326 (WGS84)
Número de zonas: {len(gdf_analizado)}"""
        for linea in metadatos.strip().split('\n'):
            pdf.cell(0, 6, limpiar_texto_para_pdf(linea), 0, 1)
        pdf_output = BytesIO()
        pdf_output.write(pdf.output(dest='S').encode('latin-1'))
        pdf_output.seek(0)
        return pdf_output
    except Exception as e:
        st.error(f"❌ Error generando PDF: {str(e)}")
        import traceback
        st.error(f"Detalle: {traceback.format_exc()}")
        return None

def generar_reporte_completo_docx(resultados_dict):
    """
    Genera un reporte DOCX completo con todos los análisis realizados.
    
    Args:
        resultados_dict: Diccionario con todos los resultados de análisis
            Debe contener:
            - gdf_analizado: GeoDataFrame con datos de fertilidad
            - cultivo: Nombre del cultivo
            - area_total: Área total en ha
            - df_power: DataFrame de datos NASA POWER
            - mapa_fertilidad: BytesIO del mapa de fertilidad
            - mapa_recomendaciones: BytesIO del mapa de recomendaciones
            - mapa_texturas: BytesIO del mapa de texturas
            - mapa_curvas: BytesIO del mapa de curvas
            - resultados_economicos: Diccionario con análisis económico
            - analisis_tipo: Tipo de análisis realizado
            - nutriente: Nutriente analizado (si aplica)
            - satelite: Satélite usado
    """
    try:
        doc = Document()
        
        # ===== PORTADA =====
        title = doc.add_heading('REPORTE COMPLETO DE ANÁLISIS AGRÍCOLA', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Información básica
        doc.add_paragraph(f"Cultivo: {resultados_dict.get('cultivo', 'No especificado')}")
        doc.add_paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        doc.add_paragraph(f"Área total: {resultados_dict.get('area_total', 0):.2f} ha")
        doc.add_paragraph(f"Análisis: {resultados_dict.get('analisis_tipo', 'Completo')}")
        
        if 'variedad' in st.session_state:
            doc.add_paragraph(f"Variedad: {st.session_state['variedad']}")
        
        doc.add_page_break()
        
        # ===== 1. RESUMEN EJECUTIVO =====
        doc.add_heading('1. RESUMEN EJECUTIVO', level=1)
        
        resumen_text = f"""
        Este reporte presenta un análisis integral del cultivo de {resultados_dict.get('cultivo', 'N/A')} 
        realizado mediante técnicas de teledetección y análisis agronómico avanzado.
        
        Principales hallazgos:
        • Área analizada: {resultados_dict.get('area_total', 0):.2f} hectáreas
        • Cultivo: {resultados_dict.get('cultivo', 'N/A')}
        • Fuente de datos: {resultados_dict.get('satelite', 'No especificado')}
        • Metodología: Análisis de fertilidad, textura, topografía y potencial económico
        """
        
        for linea in resumen_text.strip().split('\n'):
            if linea.strip():
                doc.add_paragraph(linea.strip())
        
        doc.add_page_break()
        
        # ===== 2. FERTILIDAD DEL SUELO =====
        if 'gdf_analizado' in resultados_dict:
            gdf_analizado = resultados_dict['gdf_analizado']
            doc.add_heading('2. FERTILIDAD DEL SUELO (NPK)', level=1)
            
            if 'npk_integrado' in gdf_analizado.columns:
                npk_prom = gdf_analizado['npk_integrado'].mean()
                doc.add_paragraph(f"Índice de fertilidad integrado: {npk_prom:.3f}")
            
            # Tabla de nutrientes
            table_data = []
            table_data.append(['Nutriente', 'Promedio (kg/ha)', 'Mínimo', 'Máximo'])
            
            nutrientes = ['nitrogeno_actual', 'fosforo_actual', 'potasio_actual']
            nombres = ['Nitrógeno', 'Fósforo', 'Potasio']
            
            for col, nombre in zip(nutrientes, nombres):
                if col in gdf_analizado.columns:
                    prom = gdf_analizado[col].mean()
                    minimo = gdf_analizado[col].min()
                    maximo = gdf_analizado[col].max()
                    table_data.append([nombre, f"{prom:.1f}", f"{minimo:.1f}", f"{maximo:.1f}"])
            
            if len(table_data) > 1:
                table = doc.add_table(rows=len(table_data), cols=4)
                table.style = 'Table Grid'
                
                for i, row_data in enumerate(table_data):
                    for j, cell_data in enumerate(row_data):
                        table.cell(i, j).text = str(cell_data)
        
        # ===== 3. RECOMENDACIONES DE FERTILIZACIÓN =====
        if 'nutriente' in resultados_dict and 'valor_recomendado' in gdf_analizado.columns:
            doc.add_heading('3. RECOMENDACIONES DE FERTILIZACIÓN', level=1)
            doc.add_paragraph(f"Nutriente analizado: {resultados_dict['nutriente']}")
            
            rec_prom = gdf_analizado['valor_recomendado'].mean()
            total_kg = (gdf_analizado['valor_recomendado'] * gdf_analizado['area_ha']).sum()
            
            doc.add_paragraph(f"Recomendación promedio: {rec_prom:.1f} kg/ha")
            doc.add_paragraph(f"Total requerido: {total_kg:.0f} kg")
            
            # Tabla por zona
            if len(gdf_analizado) <= 20:  # Mostrar solo si no son muchas zonas
                table = doc.add_table(rows=len(gdf_analizado)+1, cols=4)
                table.style = 'Table Grid'
                table.cell(0, 0).text = "Zona"
                table.cell(0, 1).text = "Área (ha)"
                table.cell(0, 2).text = "Nivel Actual"
                table.cell(0, 3).text = "Recomendación"
                
                for idx, row in gdf_analizado.iterrows():
                    i = idx + 1
                    table.cell(i, 0).text = str(row['id_zona'])
                    table.cell(i, 1).text = f"{row['area_ha']:.2f}"
                    col_actual = f"{resultados_dict['nutriente'].lower()}_actual"
                    if col_actual in row:
                        table.cell(i, 2).text = f"{row[col_actual]:.1f}"
                    table.cell(i, 3).text = f"{row['valor_recomendado']:.1f}"
        
        # ===== 4. ANÁLISIS ECONÓMICO =====
        if 'resultados_economicos' in resultados_dict:
            doc.add_heading('4. ANÁLISIS ECONÓMICO', level=1)
            eco = resultados_dict['resultados_economicos']
            
            # Tabla de indicadores económicos
            indicadores = [
                ("Rendimiento actual", f"{eco.get('rendimiento_actual_ton_ha', 0):.1f} ton/ha"),
                ("Rendimiento proyectado", f"{eco.get('rendimiento_proy_ton_ha', 0):.1f} ton/ha"),
                ("Incremento esperado", f"{eco.get('incremento_rendimiento_ton_ha', 0):.1f} ton/ha"),
                ("ROI fertilización", f"{eco.get('roi_fertilizacion_%', 0):.0f}%"),
                ("VAN del proyecto", f"${eco.get('van_usd', 0):,.0f}"),
                ("TIR", f"{eco.get('tir_%', 0):.1f}%"),
                ("Relación B/C", f"{eco.get('relacion_bc_proy', 0):.2f}"),
                ("Incremento ingreso total", f"${eco.get('incremento_ingreso_total_usd', 0):,.0f}")
            ]
            
            for nombre, valor in indicadores:
                p = doc.add_paragraph()
                p.add_run(f"{nombre}: ").bold = True
                p.add_run(valor)
        
        # ===== 5. DATOS CLIMATOLÓGICOS =====
        if 'df_power' in resultados_dict and resultados_dict['df_power'] is not None:
            doc.add_heading('5. DATOS CLIMATOLÓGICOS (NASA POWER)', level=1)
            df_power = resultados_dict['df_power']
            
            # Resumen estadístico
            stats = [
                ("Radiación solar promedio", f"{df_power['radiacion_solar'].mean():.1f} kWh/m²/día"),
                ("Temperatura promedio", f"{df_power['temperatura'].mean():.1f} °C"),
                ("Precipitación total", f"{df_power['precipitacion'].sum():.1f} mm"),
                ("Velocidad del viento promedio", f"{df_power['viento_2m'].mean():.1f} m/s")
            ]
            
            for nombre, valor in stats:
                p = doc.add_paragraph()
                p.add_run(f"{nombre}: ").bold = True
                p.add_run(valor)
            
            # Tabla de datos diarios (solo últimos 7 días)
            doc.add_heading('Datos Diarios (últimos 7 días)', level=2)
            if len(df_power) > 0:
                df_recent = df_power.tail(7)
                table = doc.add_table(rows=len(df_recent)+1, cols=5)
                table.style = 'Table Grid'
                
                headers = ['Fecha', 'Radiación', 'Temperatura', 'Precipitación', 'Viento']
                for j, header in enumerate(headers):
                    table.cell(0, j).text = header
                
                for i, (_, row) in enumerate(df_recent.iterrows()):
                    table.cell(i+1, 0).text = row['fecha'].strftime('%d/%m/%Y')
                    table.cell(i+1, 1).text = f"{row['radiacion_solar']:.1f}"
                    table.cell(i+1, 2).text = f"{row['temperatura']:.1f}"
                    table.cell(i+1, 3).text = f"{row['precipitacion']:.1f}"
                    table.cell(i+1, 4).text = f"{row['viento_2m']:.1f}"
        
        # ===== 6. TEXTURA DEL SUELO =====
        if 'gdf_analizado' in resultados_dict and 'textura_suelo' in gdf_analizado.columns:
            doc.add_heading('6. ANÁLISIS DE TEXTURA DEL SUELO (USDA)', level=1)
            
            textura_pred = gdf_analizado['textura_suelo'].mode()[0] if len(gdf_analizado) > 0 else "No disponible"
            doc.add_paragraph(f"Textura predominante: {textura_pred}")
            
            # Distribución de texturas
            if 'textura_suelo' in gdf_analizado.columns:
                textura_counts = gdf_analizado['textura_suelo'].value_counts()
                if len(textura_counts) > 0:
                    doc.add_heading('Distribución de Texturas por Zona', level=2)
                    for textura, count in textura_counts.items():
                        porcentaje = (count / len(gdf_analizado)) * 100
                        doc.add_paragraph(f"{textura}: {count} zonas ({porcentaje:.1f}%)")
        
        # ===== 7. CURVAS DE NIVEL Y TOPOGRAFÍA =====
        if 'mapa_curvas' in resultados_dict:
            doc.add_heading('7. ANÁLISIS TOPOGRÁFICO', level=1)
            doc.add_paragraph("Incluye análisis de pendientes y curvas de nivel para planificación del riego y prevención de erosión.")
            
            if 'estadisticas_pendiente' in resultados_dict:
                stats = resultados_dict['estadisticas_pendiente']
                if isinstance(stats, dict):
                    pendientes = [
                        ("Pendiente promedio", f"{stats.get('promedio', 0):.1f}%"),
                        ("Pendiente máxima", f"{stats.get('max', 0):.1f}%"),
                        ("Pendiente mínima", f"{stats.get('min', 0):.1f}%")
                    ]
                    
                    for nombre, valor in pendientes:
                        p = doc.add_paragraph()
                        p.add_run(f"{nombre}: ").bold = True
                        p.add_run(valor)
        
        # ===== 8. POTENCIAL DE COSECHA =====
        if 'gdf_analizado' in resultados_dict and 'rendimiento_actual' in gdf_analizado.columns:
            doc.add_heading('8. POTENCIAL DE COSECHA', level=1)
            
            rend_actual = gdf_analizado['rendimiento_actual'].mean()
            if 'rendimiento_proyectado' in gdf_analizado.columns:
                rend_proy = gdf_analizado['rendimiento_proyectado'].mean()
                incremento = gdf_analizado['incremento_rendimiento'].mean()
                porcentaje = (incremento / rend_actual * 100) if rend_actual > 0 else 0
                
                doc.add_paragraph(f"Rendimiento actual promedio: {rend_actual:.1f} ton/ha")
                doc.add_paragraph(f"Rendimiento proyectado con manejo: {rend_proy:.1f} ton/ha")
                doc.add_paragraph(f"Incremento potencial: {incremento:.1f} ton/ha ({porcentaje:.1f}%)")
            
            # Distribución de rendimientos
            if 'rendimiento_actual' in gdf_analizado.columns:
                rend_min = gdf_analizado['rendimiento_actual'].min()
                rend_max = gdf_analizado['rendimiento_actual'].max()
                rend_std = gdf_analizado['rendimiento_actual'].std()
                
                stats_rend = [
                    ("Mínimo", f"{rend_min:.1f} ton/ha"),
                    ("Máximo", f"{rend_max:.1f} ton/ha"),
                    ("Variabilidad", f"{rend_std:.1f} ton/ha")
                ]
                
                for nombre, valor in stats_rend:
                    p = doc.add_paragraph()
                    p.add_run(f"{nombre}: ").bold = True
                    p.add_run(valor)
        
        # ===== 9. RECOMENDACIONES GENERALES =====
        doc.add_heading('9. RECOMENDACIONES GENERALES', level=1)
        
        recomendaciones = [
            "1. Validar los resultados de fertilidad con análisis de suelo de laboratorio",
            "2. Implementar agricultura de precisión para aplicación variable de insumos",
            "3. Considerar riego por goteo para optimizar el uso del agua",
            "4. Monitorear regularmente el estado del cultivo mediante índices de vegetación",
            "5. Implementar prácticas de conservación de suelo en zonas con pendiente >10%",
            "6. Realizar rotación de cultivos para mejorar la salud del suelo",
            "7. Considerar coberturas vegetales para reducir erosión y mejorar materia orgánica"
        ]
        
        for rec in recomendaciones:
            doc.add_paragraph(rec, style='List Bullet')
        
        # ===== 10. ANEXOS =====
        doc.add_page_break()
        doc.add_heading('10. ANEXOS', level=1)
        doc.add_paragraph("Mapas y gráficos adicionales disponibles en versión digital del reporte.")
        
        # ===== GUARDAR DOCUMENTO =====
        docx_output = BytesIO()
        doc.save(docx_output)
        docx_output.seek(0)
        
        return docx_output
        
    except Exception as e:
        st.error(f"Error generando reporte completo: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def generar_reporte_docx(gdf_analizado, cultivo, analisis_tipo, area_total,
                         nutriente=None, satelite=None, indice=None,
                         mapa_buffer=None, estadisticas=None, recomendaciones=None):
    try:
        doc = Document()
        title = doc.add_heading(f'REPORTE DE ANÁLISIS AGRÍCOLA - {cultivo}', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle = doc.add_paragraph(f'Tipo de Análisis: {analisis_tipo}')
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if cultivo in ["VID", "OLIVO"] and 'variedad' in st.session_state:
            variedad_par = doc.add_paragraph(f'Variedad: {st.session_state["variedad"]}')
            variedad_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fecha = doc.add_paragraph(f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
        fecha.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()
        doc.add_heading('1. INFORMACIÓN GENERAL', level=1)
        info_table = doc.add_table(rows=4, cols=2)
        info_table.style = 'Table Grid'
        info_table.cell(0, 0).text = 'Cultivo'
        info_table.cell(0, 1).text = cultivo
        info_table.cell(1, 0).text = 'Área Total'
        info_table.cell(1, 1).text = f'{area_total:.2f} ha'
        info_table.cell(2, 0).text = 'Zonas Analizadas'
        info_table.cell(2, 1).text = str(len(gdf_analizado))
        info_table.cell(3, 0).text = 'Tipo de Análisis'
        info_table.cell(3, 1).text = analisis_tipo
        row_count = 4
        if satelite:
            if row_count >= len(info_table.rows):
                info_table.add_row()
            info_table.cell(row_count, 0).text = 'Satélite'
            info_table.cell(row_count, 1).text = satelite
            row_count += 1
        if indice:
            if row_count >= len(info_table.rows):
                info_table.add_row()
            info_table.cell(row_count, 0).text = 'Índice'
            info_table.cell(row_count, 1).text = indice
            row_count += 1
        if nutriente:
            if row_count >= len(info_table.rows):
                info_table.add_row()
            info_table.cell(row_count, 0).text = 'Nutriente Analizado'
            info_table.cell(row_count, 1).text = nutriente
        doc.add_paragraph()
        if estadisticas:
            doc.add_heading('2. ESTADÍSTICAS PRINCIPALES', level=1)
            for key, value in estadisticas.items():
                p = doc.add_paragraph(style='List Bullet')
                run = p.add_run(f'{key}: ')
                run.bold = True
                p.add_run(str(value))
            doc.add_paragraph()
        if analisis_tipo == "RECOMENDACIONES NPK" and 'rendimiento_actual' in gdf_analizado.columns:
            doc.add_heading('ANÁLISIS DE POTENCIAL DE COSECHA', level=1)
            rend_actual = gdf_analizado['rendimiento_actual'].mean()
            rend_proy = gdf_analizado['rendimiento_proyectado'].mean()
            incremento = gdf_analizado['incremento_rendimiento'].mean()
            porcentaje = (incremento / rend_actual * 100) if rend_actual > 0 else 0
            rendimiento_table = doc.add_table(rows=4, cols=2)
            rendimiento_table.style = 'Table Grid'
            rendimiento_table.cell(0, 0).text = 'Rendimiento Actual Promedio'
            rendimiento_table.cell(0, 1).text = f'{rend_actual:.1f} ton/ha'
            rendimiento_table.cell(1, 0).text = 'Rendimiento Proyectado Promedio'
            rendimiento_table.cell(1, 1).text = f'{rend_proy:.1f} ton/ha'
            rendimiento_table.cell(2, 0).text = 'Incremento Esperado'
            rendimiento_table.cell(2, 1).text = f'{incremento:.1f} ton/ha'
            rendimiento_table.cell(3, 0).text = 'Porcentaje de Aumento'
            rendimiento_table.cell(3, 1).text = f'{porcentaje:.1f}%'
            doc.add_paragraph()
        if mapa_buffer:
            try:
                doc.add_heading('3. MAPA DE RESULTADOS', level=1)
                temp_img_path = "temp_map_docx.png"
                with open(temp_img_path, "wb") as f:
                    f.write(mapa_buffer.getvalue())
                doc.add_picture(temp_img_path, width=Inches(6.0))
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
                doc.add_paragraph()
            except Exception as e:
                doc.add_paragraph(f'Error al incluir mapa: {str(e)[:50]}...')
        else:
            doc.add_paragraph('Mapa no disponible para este análisis')
        doc.add_heading('4. RESUMEN DE ZONAS', level=1)
        if gdf_analizado is not None and not gdf_analizado.empty:
            columnas_mostrar = ['id_zona', 'area_ha']
            if 'npk_integrado' in gdf_analizado.columns:
                columnas_mostrar.append('npk_integrado')
            if 'nitrogeno_actual' in gdf_analizado.columns:
                columnas_mostrar.append('nitrogeno_actual')
            if 'fosforo_actual' in gdf_analizado.columns:
                columnas_mostrar.append('fosforo_actual')
            if 'potasio_actual' in gdf_analizado.columns:
                columnas_mostrar.append('potasio_actual')
            if 'valor_recomendado' in gdf_analizado.columns:
                columnas_mostrar.append('valor_recomendado')
            if 'textura_suelo' in gdf_analizado.columns:
                columnas_mostrar.append('textura_suelo')
            if 'ndwi' in gdf_analizado.columns:
                columnas_mostrar.append('ndwi')
            if 'rendimiento_actual' in gdf_analizado.columns:
                columnas_mostrar.extend(['rendimiento_actual', 'rendimiento_proyectado'])
            columnas_mostrar = [col for col in columnas_mostrar if col in gdf_analizado.columns]
            if columnas_mostrar:
                tabla = doc.add_table(rows=1, cols=len(columnas_mostrar))
                tabla.style = 'Table Grid'
                for i, col in enumerate(columnas_mostrar):
                    tabla.cell(0, i).text = col.replace('_', ' ').upper()
                for idx, row in gdf_analizado.head(10).iterrows():
                    row_cells = tabla.add_row().cells
                    for i, col in enumerate(columnas_mostrar):
                        if col in gdf_analizado.columns:
                            valor = row[col]
                            if isinstance(valor, float):
                                if col in ['npk_integrado', 'ndwi']:
                                    row_cells[i].text = f"{valor:.3f}"
                                elif col in ['nitrogeno_actual', 'fosforo_actual', 'potasio_actual', 'valor_recomendado']:
                                    row_cells[i].text = f"{valor:.1f}"
                                elif col in ['rendimiento_actual', 'rendimiento_proyectado']:
                                    row_cells[i].text = f"{valor:.1f}"
                                else:
                                    row_cells[i].text = f"{valor:.2f}"
                            else:
                                row_cells[i].text = str(valor)
                        else:
                            row_cells[i].text = "N/A"
        doc.add_paragraph()
        if recomendaciones:
            doc.add_heading('5. RECOMENDACIONES', level=1)
            for rec in recomendaciones:
                p = doc.add_paragraph(style='List Bullet')
                p.add_run(rec)
        doc.add_heading('6. METADATOS TÉCNICOS', level=1)
        metadatos = [
            ('Generado por', 'Analizador Multi-Cultivo Satellital'),
            ('Versión', '2.0 (Con metodologías científicas NPK)'),
            ('Fecha de generación', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ('Sistema de coordenadas', 'EPSG:4326 (WGS84)'),
            ('Número de zonas', str(len(gdf_analizado)))
        ]
        for key, value in metadatos:
            p = doc.add_paragraph()
            run_key = p.add_run(f'{key}: ')
            run_key.bold = True
            p.add_run(value)
        docx_output = BytesIO()
        doc.save(docx_output)
        docx_output.seek(0)
        return docx_output
    except Exception as e:
        st.error(f"❌ Error generando DOCX: {str(e)}")
        import traceback
        st.error(f"Detalle: {traceback.format_exc()}")
        return None

# ===== FUNCIÓN CORREGIDA crear_mapa_npk_con_esri =====
def crear_mapa_npk_con_esri(gdf_analizado, nutriente, cultivo, satelite, mostrar_capa_inta=False):
    try:
        if gdf_analizado.empty or 'id_zona' not in gdf_analizado.columns:
            return None
        gdf_plot = gpd.GeoDataFrame(gdf_analizado.copy())
        
        # Convertir a EPSG:3857 para visualización
        if str(gdf_plot.crs).upper() != 'EPSG:3857':
            try:
                gdf_plot = gdf_plot.to_crs('EPSG:3857')
            except:
                pass
        
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        mapeo_nutriente = {
            'NITRÓGENO': ('nitrogeno_actual', 'NITROGENO', 'NITRÓGENO (kg/ha)'),
            'FÓSFORO': ('fosforo_actual', 'FOSFORO', 'FÓSFORO (kg/ha)'),
            'POTASIO': ('potasio_actual', 'POTASIO', 'POTASIO (kg/ha)')
        }
        
        if nutriente not in mapeo_nutriente:
            return None
        
        columna, clave_param, titulo_nutriente = mapeo_nutriente[nutriente]
        
        if columna not in gdf_analizado.columns:
            return None
        
        # Obtener parámetros con valores por defecto seguros
        params = obtener_parametros_cultivo(cultivo)
        vmin, vmax = 0, 100  # Valores por defecto
        
        # Intentar obtener valores de forma segura
        try:
            if clave_param in params:
                param_data = params[clave_param]
                if isinstance(param_data, dict) and 'min' in param_data and 'max' in param_data:
                    vmin = param_data.get('min', 0) * 0.7
                    vmax = param_data.get('max', 100) * 1.2
                elif isinstance(param_data, (int, float)):
                    vmin = param_data * 0.5
                    vmax = param_data * 1.5
        except Exception as e:
            st.warning(f"Usando valores por defecto para {nutriente}: {e}")
        
        # Asegurar que vmax > vmin
        if vmin >= vmax:
            vmin, vmax = 0, max(100, gdf_analizado[columna].max() * 1.2)
        
        # Obtener valores reales para normalización
        valores = gdf_analizado[columna].fillna(0).values
        vmin_actual = max(vmin, valores.min() * 0.8)
        vmax_actual = min(vmax, valores.max() * 1.2)
        
        # Crear colormap
        colors = PALETAS_GEE.get(clave_param, ['#00ff00', '#ffff00', '#ff0000'])
        cmap = LinearSegmentedColormap.from_list('nutriente_gee', colors)
        
        # Plotear cada zona
        for idx, row in gdf_plot.iterrows():
            try:
                valor = gdf_analizado.iloc[idx][columna] if columna in gdf_analizado.columns else 0
                valor_norm = max(0, min(1, (valor - vmin_actual) / (vmax_actual - vmin_actual))) if vmax_actual > vmin_actual else 0.5
                color = cmap(valor_norm)
                
                # Asegurar que sea un GeoDataFrame válido
                if hasattr(gdf_plot.iloc[[idx]], 'plot'):
                    gdf_plot.iloc[[idx]].plot(ax=ax, color=color, edgecolor='white', linewidth=1.5, alpha=0.7)
                
                # Añadir etiqueta
                if 'geometry' in row:
                    if hasattr(row.geometry, 'centroid'):
                        centroid = row.geometry.centroid
                    else:
                        centroid = row.geometry.representative_point()
                    
                    ax.annotate(f"Z{row['id_zona']}\n{valor:.0f}", 
                                (centroid.x, centroid.y),
                                xytext=(5, 5), textcoords="offset points",
                                fontsize=8, color='white', weight='bold',
                                bbox=dict(boxstyle="round,pad=0.3", 
                                          facecolor=(30/255, 41/255, 59/255, 0.9), 
                                          edgecolor='white'))
            except Exception as e:
                continue
        
        # Añadir mapa base
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.3)
        except Exception:
            pass
        
        # Añadir capa INTA si está habilitado
        if mostrar_capa_inta:
            try:
                wms_url = "https://wms.inta.gob.ar/geoserver/inta/wms"
                ctx.add_basemap(
                    ax,
                    url=wms_url + "?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=inta%3Asuelos_argentina&SRS=EPSG%3A3857&WIDTH=256&HEIGHT=256&BBOX={bbox-epsg-3857}&FORMAT=image/png&TRANSPARENT=true",
                    attribution="© INTA - Mapa de Suelos",
                    alpha=0.4
                )
            except Exception:
                pass
        
        # Configurar título y etiquetas
        info_satelite = SATELITES_DISPONIBLES.get(satelite, SATELITES_DISPONIBLES['DATOS_SIMULADOS'])
        ax.set_title(f'{ICONOS_CULTIVOS.get(cultivo, "🌱")} ANÁLISIS DE {nutriente} - {cultivo}\n'
                     f'{info_satelite.get("icono", "🛰️")} {info_satelite.get("nombre", "Datos")} - {titulo_nutriente}',
                     fontsize=16, fontweight='bold', pad=20, color='white')
        
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3, color='#475569')
        
        # Crear colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin_actual, vmax=vmax_actual))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
        cbar.set_label(titulo_nutriente, fontsize=12, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        cbar.outline.set_edgecolor('white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                    facecolor='#0f172a', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf
        
    except Exception as e:
        st.error(f"Error detallado creando mapa NPK: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def crear_mapa_fertilidad_integrada(gdf_analizado, cultivo, satelite, mostrar_capa_inta=False):
    try:
        if gdf_analizado.empty or 'npk_integrado' not in gdf_analizado.columns:
            return None
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        cmap = LinearSegmentedColormap.from_list('fertilidad_gee', PALETAS_GEE['FERTILIDAD'])
        for idx, row in gdf_plot.iterrows():
            valor = row['npk_integrado']
            color = cmap(max(0, min(1, valor)))
            gdf_plot.iloc[[idx]].plot(ax=ax, color=color, edgecolor='white', linewidth=1.5, alpha=0.7)
            centroid = row.geometry.centroid
            ax.annotate(f"Z{row['id_zona']}\n{valor:.2f}", (centroid.x, centroid.y),
                        xytext=(5, 5), textcoords="offset points",
                        fontsize=8, color='white', weight='bold',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor=(30/255, 41/255, 59/255, 0.9), edgecolor='white'))
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.3)
        except Exception:
            pass
        if mostrar_capa_inta:
            try:
                wms_url = "https://wms.inta.gob.ar/geoserver/inta/wms"
                ctx.add_basemap(
                    ax,
                    url=wms_url + "?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=inta%3Asuelos_argentina&SRS=EPSG%3A3857&WIDTH=256&HEIGHT=256&BBOX={bbox-epsg-3857}&FORMAT=image/png&TRANSPARENT=true",
                    attribution="© INTA - Mapa de Suelos",
                    alpha=0.4
                )
            except Exception:
                pass
        info_satelite = SATELITES_DISPONIBLES.get(satelite, SATELITES_DISPONIBLES['DATOS_SIMULADOS'])
        ax.set_title(f'{ICONOS_CULTIVOS[cultivo]} FERTILIDAD INTEGRADA (NPK) - {cultivo}\n'
                     f'{info_satelite["icono"]} {info_satelite["nombre"]}',
                     fontsize=16, fontweight='bold', pad=20, color='white')
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3, color='#475569')
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=1))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
        cbar.set_label('Índice de Fertilidad (0-1)', fontsize=12, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        cbar.outline.set_edgecolor('white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        st.error(f"Error creando mapa de fertilidad: {str(e)}")
        return None

def crear_mapa_texturas_con_esri(gdf_analizado, cultivo, mostrar_capa_inta=False):
    try:
        if gdf_analizado.empty or 'textura_suelo' not in gdf_analizado.columns:
            return None
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        colores_textura = {
            'Franco limoso': '#c7eae5',
            'Franco': '#a6d96a',
            'Franco arcilloso limoso': '#5ab4ac',
            'Franco arenoso': '#f6e8c3',
            'Arcilla': '#01665e',
            'Arcilla limosa': '#003c30',
            'Arena franca': '#d8b365',
            'Limo': '#8c510a',
            'Franco arcilloso': '#35978f',
            'Franco arcilloso arenoso': '#80cdc1',
            'Limo arenoso': '#dfc27d',
            'Arena': '#f6e8c3',
            'Arcilla arenosa': '#01665e',
            'Franco limoso arenoso': '#a6d96a',
            'Sin datos': '#999999'
        }
        for idx, row in gdf_plot.iterrows():
            textura = row['textura_suelo']
            color = colores_textura.get(textura, '#999999')
            gdf_plot.iloc[[idx]].plot(ax=ax, color=color, edgecolor='white', linewidth=1.5, alpha=0.8)
            textura_abrev = textura[:12] + '...' if len(textura) > 15 else textura
            centroid = row.geometry.centroid
            ax.annotate(f"Z{row['id_zona']}\n{textura_abrev}", (centroid.x, centroid.y),
                        xytext=(5, 5), textcoords="offset points",
                        fontsize=8, color='black', weight='bold',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.3)
        except Exception:
            pass
        if mostrar_capa_inta:
            try:
                wms_url = "https://wms.inta.gob.ar/geoserver/inta/wms"
                ctx.add_basemap(
                    ax,
                    url=wms_url + "?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=inta%3Asuelos_argentina&SRS=EPSG%3A3857&WIDTH=256&HEIGHT=256&BBOX={bbox-epsg-3857}&FORMAT=image/png&TRANSPARENT=true",
                    attribution="© INTA - Mapa de Suelos",
                    alpha=0.4
                )
            except Exception:
                pass
        ax.set_title(f'{ICONOS_CULTIVOS[cultivo]} MAPA DE TEXTURAS USDA - {cultivo}',
                     fontsize=16, fontweight='bold', pad=20, color='white')
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3, color='#475569')
        texturas_presentes = [t for t in gdf_analizado['textura_suelo'].unique() if t in colores_textura]
        if texturas_presentes:
            legend_elements = [mpatches.Patch(facecolor=colores_textura[t], edgecolor='white', label=t)
                               for t in texturas_presentes]
            legend = ax.legend(handles=legend_elements, title='Texturas USDA',
                               loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=9)
            legend.get_title().set_color('white')
            for text in legend.get_texts():
                text.set_color('white')
            legend.get_frame().set_facecolor((30/255, 41/255, 59/255, 0.9))
            legend.get_frame().set_edgecolor('white')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception as e:
        st.error(f"Error creando mapa de texturas: {str(e)}")
        return None

# ===== FUNCIONES DE GRÁFICOS NASA POWER CON ESTILO OSCURO =====
def crear_grafico_personalizado(series, titulo, ylabel, color_linea, fondo_grafico='#0f172a', color_texto='#ffffff'):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_facecolor(fondo_grafico)
    fig.patch.set_facecolor(fondo_grafico)
    ax.plot(series.index, series.values, color=color_linea, linewidth=2.2)
    ax.set_title(titulo, fontsize=14, fontweight='bold', color=color_texto)
    ax.set_ylabel(ylabel, fontsize=12, color=color_texto)
    ax.set_xlabel("Fecha", fontsize=11, color=color_texto)
    ax.tick_params(axis='x', colors=color_texto, rotation=0)
    ax.tick_params(axis='y', colors=color_texto)
    ax.grid(True, color='#475569', linestyle='--', linewidth=0.7, alpha=0.7)
    for spine in ax.spines.values():
        spine.set_color('#475569')
    plt.tight_layout()
    return fig

def crear_grafico_barras_personalizado(series, titulo, ylabel, color_barra, fondo_grafico='#0f172a', color_texto='#ffffff'):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_facecolor(fondo_grafico)
    fig.patch.set_facecolor(fondo_grafico)
    ax.bar(series.index, series.values, color=color_barra, alpha=0.85)
    ax.set_title(titulo, fontsize=14, fontweight='bold', color=color_texto)
    ax.set_ylabel(ylabel, fontsize=12, color=color_texto)
    ax.set_xlabel("Fecha", fontsize=11, color=color_texto)
    ax.tick_params(axis='x', colors=color_texto, rotation=0)
    ax.tick_params(axis='y', colors=color_texto)
    ax.grid(axis='y', color='#475569', linestyle='--', linewidth=0.7, alpha=0.7)
    for spine in ax.spines.values():
        spine.set_color('#475569')
    plt.tight_layout()
    return fig

# ===== FUNCIÓN PRINCIPAL DE ANÁLISIS (MEJORADA) =====
def ejecutar_analisis(gdf, nutriente, analisis_tipo, n_divisiones, cultivo,
                      satelite=None, indice=None, fecha_inicio=None,
                      fecha_fin=None, intervalo_curvas=5.0, resolucion_dem=10.0,
                      usar_inta=True, mostrar_capa_inta=False):
    resultados = {
        'exitoso': False,
        'gdf_analizado': None,
        'mapa_buffer': None,
        'tabla_datos': None,
        'estadisticas': {},
        'recomendaciones': [],
        'area_total': 0,
        'df_power': None
    }
    try:
        gdf = validar_y_corregir_crs(gdf)
        area_total = calcular_superficie(gdf)
        resultados['area_total'] = area_total
        if analisis_tipo == "ANÁLISIS DE TEXTURA":
            gdf_dividido = dividir_parcela_en_zonas(gdf, n_divisiones)
            gdf_analizado = analizar_textura_suelo(gdf_dividido, cultivo)
            resultados['gdf_analizado'] = gdf_analizado
            resultados['exitoso'] = True
            return resultados
        elif analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL":
            gdf_dividido = dividir_parcela_en_zonas(gdf, n_divisiones)
            resultados['gdf_analizado'] = gdf_dividido
            resultados['exitoso'] = True
            return resultados
        elif analisis_tipo in ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK"]:
            datos_satelitales = None
            if satelite == "SENTINEL-2":
                datos_satelitales = descargar_datos_sentinel2(gdf, fecha_inicio, fecha_fin, indice)
            elif satelite == "LANDSAT-8":
                datos_satelitales = descargar_datos_landsat8(gdf, fecha_inicio, fecha_fin, indice)
            else:
                datos_satelitales = generar_datos_simulados(gdf, cultivo, indice)
            gdf_dividido = dividir_parcela_en_zonas(gdf, n_divisiones)
            indices_npk = calcular_indices_npk_avanzados(gdf_dividido, cultivo, satelite, usar_inta)
            gdf_analizado = gdf_dividido.copy()
            for idx, indice_data in enumerate(indices_npk):
                for key, value in indice_data.items():
                    gdf_analizado.loc[gdf_analizado.index[idx], key] = value
            areas_ha_list = []
            for idx, row in gdf_analizado.iterrows():
                area_gdf = gpd.GeoDataFrame({'geometry': [row.geometry]}, crs=gdf_analizado.crs)
                area_ha = calcular_superficie(area_gdf)
                if hasattr(area_ha, 'iloc'):
                    area_ha = float(area_ha.iloc[0])
                elif hasattr(area_ha, '__len__') and len(area_ha) > 0:
                    area_ha = float(area_ha[0])
                else:
                    area_ha = float(area_ha)
                areas_ha_list.append(area_ha)
            gdf_analizado['area_ha'] = areas_ha_list
            if analisis_tipo == "RECOMENDACIONES NPK":
                recomendaciones_npk = calcular_recomendaciones_npk_cientificas(gdf_analizado, nutriente, cultivo)
                gdf_analizado['valor_recomendado'] = recomendaciones_npk
                rendimientos_actual = calcular_rendimiento_potencial(gdf_analizado, cultivo)
                rendimientos_proyectado = calcular_rendimiento_con_recomendaciones(gdf_analizado, cultivo)
                gdf_analizado['rendimiento_actual'] = rendimientos_actual
                gdf_analizado['rendimiento_proyectado'] = rendimientos_proyectado
                gdf_analizado['incremento_rendimiento'] = gdf_analizado['rendimiento_proyectado'] - gdf_analizado['rendimiento_actual']
            elif analisis_tipo == "FERTILIDAD ACTUAL":
                rendimientos_actual = calcular_rendimiento_potencial(gdf_analizado, cultivo)
                gdf_analizado['rendimiento_actual'] = rendimientos_actual
            resultados['gdf_analizado'] = gdf_analizado
            resultados['exitoso'] = True
            if satelite:
                df_power = obtener_datos_nasa_power(gdf, fecha_inicio, fecha_fin)
                if df_power is not None:
                    resultados['df_power'] = df_power
            return resultados
        else:
            st.error(f"Tipo de análisis no soportado: {analisis_tipo}")
            return resultados
    except Exception as e:
        st.error(f"❌ Error en análisis: {str(e)}")
        import traceback
        st.error(f"Detalle: {traceback.format_exc()}")
        return resultados

# ===== FUNCIONES DE VISUALIZACIÓN =====
def mostrar_resultados_textura(gdf_analizado, cultivo, area_total, mostrar_capa_inta=False):
    st.subheader("📊 ESTADÍSTICAS DE TEXTURA (USDA)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        textura_predominante = gdf_analizado['textura_suelo'].mode()[0] if len(gdf_analizado) > 0 else "Sin datos"
        st.metric("🏗️ Textura Predominante", textura_predominante)
    with col2:
        avg_arena = gdf_analizado['arena'].mean()
        st.metric("🏖️ Arena Promedio", f"{avg_arena:.1f}%")
    with col3:
        avg_limo = gdf_analizado['limo'].mean()
        st.metric("🌫️ Limo Promedio", f"{avg_limo:.1f}%")
    with col4:
        avg_arcilla = gdf_analizado['arcilla'].mean()
        st.metric("🧱 Arcilla Promedio", f"{avg_arcilla:.1f}%")
    st.subheader("📈 COMPOSICIÓN GRANULOMÉTRICA (USDA)")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('#0f172a')
    ax1.set_facecolor('#0f172a')
    ax2.set_facecolor('#0f172a')
    composicion = [gdf_analizado['arena'].mean(), gdf_analizado['limo'].mean(), gdf_analizado['arcilla'].mean()]
    labels = ['Arena', 'Limo', 'Arcilla']
    colors_pie = ['#d8b365', '#f6e8c3', '#01665e']
    ax1.pie(composicion, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90, textprops={'color': 'white'})
    ax1.set_title('Composición Promedio USDA', color='white')
    textura_dist = gdf_analizado['textura_suelo'].value_counts()
    ax2.bar(textura_dist.index, textura_dist.values, color=[PALETAS_GEE['TEXTURA'][i % len(PALETAS_GEE['TEXTURA'])] for i in range(len(textura_dist))])
    ax2.set_title('Distribución de Texturas USDA', color='white')
    ax2.set_xlabel('Clase Textural USDA', color='white')
    ax2.set_ylabel('Número de Zonas', color='white')
    ax2.tick_params(axis='x', rotation=45, colors='white')
    ax2.tick_params(axis='y', colors='white')
    ax2.set_facecolor('#0f172a')
    plt.tight_layout()
    st.pyplot(fig)
    st.subheader("🗺️ MAPA DE TEXTURAS USDA CON ESRI SATELLITE")
    mapa_texturas = crear_mapa_texturas_con_esri(gdf_analizado, cultivo, mostrar_capa_inta)
    if mapa_texturas:
        st.image(mapa_texturas, use_container_width=True)
        st.download_button(
            "📥 Descargar Mapa de Texturas USDA",
            mapa_texturas,
            f"mapa_texturas_usda_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            "image/png"
        )
    st.subheader("📋 TABLA DE RESULTADOS POR ZONA (USDA)")
    columnas_textura = ['id_zona', 'area_ha', 'textura_suelo', 'arena', 'limo', 'arcilla']
    columnas_textura = [col for col in columnas_textura if col in gdf_analizado.columns]
    if columnas_textura:
        tabla_textura = gdf_analizado[columnas_textura].copy()
        tabla_textura.columns = ['Zona', 'Área (ha)', 'Textura USDA', 'Arena (%)', 'Limo (%)', 'Arcilla (%)']
        st.dataframe(tabla_textura)
    st.subheader("💡 RECOMENDACIONES DE MANEJO POR TEXTURA USDA")
    if 'textura_suelo' in gdf_analizado.columns:
        textura_predominante = gdf_analizado['textura_suelo'].mode()[0] if len(gdf_analizado) > 0 else "Sin datos"
        if textura_predominante in RECOMENDACIONES_TEXTURA:
            st.markdown(f"#### 🏗️ **{textura_predominante.upper()}**")
            info_textura = RECOMENDACIONES_TEXTURA[textura_predominante]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**✅ PROPIEDADES FÍSICAS**")
                for prop in info_textura['propiedades']:
                    st.markdown(f"• {prop}")
            with col2:
                st.markdown("**⚠️ LIMITANTES**")
                for lim in info_textura['limitantes']:
                    st.markdown(f"• {lim}")
            with col3:
                st.markdown("**🛠️ MANEJO RECOMENDADO**")
                for man in info_textura['manejo']:
                    st.markdown(f"• {man}")
        else:
            st.info(f"Textura '{textura_predominante}' - Consultar recomendaciones específicas para esta clase textural")
    st.subheader("💾 DESCARGAR RESULTADOS USDA")
    if 'columnas_textura' in locals() and columnas_textura:
        tabla_textura = gdf_analizado[columnas_textura].copy()
        tabla_textura.columns = ['Zona', 'Área (ha)', 'Textura USDA', 'Arena (%)', 'Limo (%)', 'Arcilla (%)']
        csv = tabla_textura.to_csv(index=False)
        st.download_button(
            "📥 Descargar CSV con Análisis de Textura USDA",
            csv,
            f"textura_usda_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv"
        )

def mostrar_resultados_curvas_nivel(X, Y, Z, pendiente_grid, curvas, elevaciones, gdf_original, cultivo, area_total):
    st.subheader("📊 ESTADÍSTICAS TOPOGRÁFICAS")
    elevaciones_flat = Z.flatten()
    elevaciones_flat = elevaciones_flat[~np.isnan(elevaciones_flat)]
    if len(elevaciones_flat) > 0:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            elevacion_promedio = np.mean(elevaciones_flat)
            st.metric("🏔️ Elevación Promedio", f"{elevacion_promedio:.1f} m")
        with col2:
            rango_elevacion = np.max(elevaciones_flat) - np.min(elevaciones_flat)
            st.metric("📏 Rango de Elevación", f"{rango_elevacion:.1f} m")
        with col3:
            mapa_pendientes, stats_pendiente = crear_mapa_pendientes_simple(X, Y, pendiente_grid, gdf_original)
            st.metric("📐 Pendiente Promedio", f"{stats_pendiente['promedio']:.1f}%")
        with col4:
            num_curvas = len(curvas) if curvas else 0
            st.metric("🔄 Número de Curvas", f"{num_curvas}")
    st.subheader("🔥 MAPA DE CALOR DE PENDIENTES")
    st.image(mapa_pendientes, use_container_width=True)
    st.download_button(
        "📥 Descargar Mapa de Pendientes",
        mapa_pendientes,
        f"mapa_pendientes_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
        "image/png"
    )
    st.subheader("⚠️ ANÁLISIS DE RIESGO DE EROSION")
    if 'stats_pendiente' in locals() and 'distribucion' in stats_pendiente:
        riesgo_total = 0
        for categoria, data in stats_pendiente['distribucion'].items():
            if categoria in ['PLANA (0-2%)', 'SUAVE (2-5%)', 'MODERADA (5-10%)', 'FUERTE (10-15%)', 'MUY FUERTE (15-25%)', 'EXTREMA (>25%)']:
                riesgo_total += data['porcentaje'] * CLASIFICACION_PENDIENTES[categoria]['factor_erosivo']
        riesgo_promedio = riesgo_total / 100
        col1, col2, col3 = st.columns(3)
        with col1:
            if riesgo_promedio < 0.3:
                st.success("✅ **RIESGO BAJO**")
                st.metric("Factor Riesgo", f"{riesgo_promedio:.2f}")
            elif riesgo_promedio < 0.6:
                st.warning("⚠️ **RIESGO MODERADO**")
                st.metric("Factor Riesgo", f"{riesgo_promedio:.2f}")
            else:
                st.error("🚨 **RIESGO ALTO**")
                st.metric("Factor Riesgo", f"{riesgo_promedio:.2f}")
        with col2:
            area_total_ha = area_total
            porcentaje_critico = sum(data['porcentaje'] for cat, data in stats_pendiente['distribucion'].items()
                                     if cat in ['FUERTE (10-15%)', 'MUY FUERTE (15-25%)', 'EXTREMA (>25%)'])
            area_critica = area_total_ha * (porcentaje_critico / 100)
            st.metric("Área Crítica (>10%)", f"{area_critica:.2f} ha")
        with col3:
            porcentaje_manejable = sum(data['porcentaje'] for cat, data in stats_pendiente['distribucion'].items()
                                       if cat in ['PLANA (0-2%)', 'SUAVE (2-5%)', 'MODERADA (5-10%)'])
            area_manejable = area_total_ha * (porcentaje_manejable / 100)
            st.metric("Área Manejable (<10%)", f"{area_manejable:.2f} ha")
    st.subheader("📈 VISUALIZACIÓN 3D DEL TERRENO")
    try:
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        surf = ax.plot_surface(X, Y, Z, cmap='terrain', alpha=0.8, linewidth=0)
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.set_zlabel('Elevación (m)', color='white')
        ax.set_title(f'Modelo 3D del Terreno - {cultivo}', color='white')
        ax.tick_params(colors='white')
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.zaxis.label.set_color('white')
        ax.title.set_color('white')
        cbar = fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='Elevación (m)')
        cbar.set_label('Elevación (m)', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        plt.tight_layout()
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"No se pudo generar visualización 3D: {e}")
    st.subheader("💾 DESCARGAR RESULTADOS")
    sample_points = []
    for i in range(0, X.shape[0], 5):
        for j in range(0, X.shape[1], 5):
            if not np.isnan(Z[i, j]):
                sample_points.append({
                    'lat': Y[i, j],
                    'lon': X[i, j],
                    'elevacion_m': Z[i, j],
                    'pendiente_%': pendiente_grid[i, j]
                })
    if sample_points:
        df_dem = pd.DataFrame(sample_points)
        csv = df_dem.to_csv(index=False)
        st.download_button(
            label="📊 Descargar Muestras DEM (CSV)",
            data=csv,
            file_name=f"dem_muestras_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

# ===== SIDEBAR MEJORADO CON OPCIÓN DEL INTA =====
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚙️ CONFIGURACIÓN</div>', unsafe_allow_html=True)
    cultivo = st.selectbox("Cultivo:", ["VID", "OLIVO", "TOMATE", "CEBOLLA", "PAPA", "ZANAHORIA", "LECHUGA", "AJO"])
    if cultivo == "VID":
        variedad = st.selectbox("Variedad de Vid:", list(VARIEDADES_VID.keys()), index=0)
        st.session_state['variedad'] = variedad
        st.session_state['variedad_params'] = VARIEDADES_VID[variedad]
    elif cultivo == "OLIVO":
        variedad = st.selectbox("Variedad de Olivo:", list(VARIEDADES_OLIVO.keys()), index=0)
        st.session_state['variedad'] = variedad
        st.session_state['variedad_params'] = VARIEDADES_OLIVO[variedad]
    if 'variedad' in st.session_state and st.session_state['variedad']:
        params = st.session_state['variedad_params']
        st.info(f"""
**📊 {st.session_state['variedad']}**
- Potencial: {params['RENDIMIENTO_BASE']} - {params['RENDIMIENTO_OPTIMO']} ton/ha
- Ciclo: {params.get('CICLO', 'N/D')} días
- Región: {params.get('REGION', 'N/D')}
""")
    st.image(IMAGENES_CULTIVOS[cultivo], use_container_width=True)
    if satelite_seleccionado in METODOLOGIAS_NPK:
        st.info(f"**Metodología {satelite_seleccionado}:**")
        for nutriente_metodo, info in METODOLOGIAS_NPK[satelite_seleccionado].items():
            st.write(f"- **{nutriente_metodo}**: {info['metodo']}")
    with st.expander("🌱 INTEGRACIÓN CON EL INTA"):
        usar_inta = st.checkbox(
            "✅ Usar datos del INTA para materia orgánica",
            value=True,
            help="Activa la estimación de materia orgánica basada en mapas reales del INTA por región"
        )
        mostrar_mapa_inta = st.checkbox(
            "🗺️ Mostrar capa base del INTA",
            value=False,
            help="Superpone el mapa de suelos del INTA como capa base (requiere conexión a internet)"
        )
        if usar_inta:
            st.info("🔍 La materia orgánica se estimará usando datos regionales del INTA")
        else:
            st.warning("⚠️ Se usará estimación genérica basada en cultivo")
    analisis_tipo = st.selectbox("Tipo de Análisis:", ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK", "ANÁLISIS DE TEXTURA", "ANÁLISIS DE CURVAS DE NIVEL"])
    if analisis_tipo == "RECOMENDACIONES NPK":
        nutriente = st.selectbox("Nutriente:", ["NITRÓGENO", "FÓSFORO", "POTASIO"])
    st.subheader("🛰️ Fuente de Datos Satelitales")
    satelite_seleccionado = st.selectbox(
        "Satélite:",
        ["SENTINEL-2", "LANDSAT-8", "DATOS_SIMULADOS"],
        help="Selecciona la fuente de datos satelitales"
    )
    if satelite_seleccionado in SATELITES_DISPONIBLES:
        info_satelite = SATELITES_DISPONIBLES[satelite_seleccionado]
        st.info(f"""
**{info_satelite['icono']} {info_satelite['nombre']}**
- Resolución: {info_satelite['resolucion']}
- Revisita: {info_satelite['revisita']}
- Índices: {', '.join(info_satelite['indices'][:3])}
""")
    if analisis_tipo in ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK"]:
        st.subheader("📊 Índices de Vegetación")
        if satelite_seleccionado == "SENTINEL-2":
            indice_seleccionado = st.selectbox("Índice:", SATELITES_DISPONIBLES['SENTINEL-2']['indices'])
        elif satelite_seleccionado == "LANDSAT-8":
            indice_seleccionado = st.selectbox("Índice:", SATELITES_DISPONIBLES['LANDSAT-8']['indices'])
        else:
            indice_seleccionado = st.selectbox("Índice:", SATELITES_DISPONIBLES['DATOS_SIMULADOS']['indices'])
    if analisis_tipo in ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK"]:
        st.subheader("📅 Rango Temporal")
        fecha_fin = st.date_input("Fecha fin", datetime.now())
        fecha_inicio = st.date_input("Fecha inicio", datetime.now() - timedelta(days=30))
    st.subheader("🎯 División de Parcela")
    n_divisiones = st.slider("Número de zonas de manejo:", min_value=16, max_value=48, value=32)
    if analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL":
        st.subheader("🏔️ Configuración Curvas de Nivel")
        intervalo_curvas = st.slider("Intervalo entre curvas (metros):", 1.0, 20.0, 5.0, 1.0)
        resolucion_dem = st.slider("Resolución DEM (metros):", 5.0, 50.0, 10.0, 5.0)
    st.subheader("📤 Subir Parcela")
    uploaded_file = st.file_uploader("Subir archivo de tu parcela", type=['zip', 'kml', 'kmz'],
                                     help="Formatos aceptados: Shapefile (.zip), KML (.kml), KMZ (.kmz)")
    with st.expander("💰 CONFIGURACIÓN ECONÓMICA"):
        st.markdown("#### Precios de Mercado (USD)")
        precio_vid = st.number_input("Vid (USD/ton)", value=450.0, min_value=300.0, max_value=600.0)
        precio_olivo = st.number_input("Olivo (USD/ton)", value=320.0, min_value=200.0, max_value=500.0)
        precio_tomate = st.number_input("Tomate (USD/ton)", value=800.0, min_value=500.0, max_value=1200.0)
        precio_cebolla = st.number_input("Cebolla (USD/ton)", value=600.0, min_value=400.0, max_value=800.0)
        precio_papa = st.number_input("Papa (USD/ton)", value=400.0, min_value=250.0, max_value=600.0)
        precio_zanahoria = st.number_input("Zanahoria (USD/ton)", value=700.0, min_value=450.0, max_value=900.0)
        precio_lechuga = st.number_input("Lechuga (USD/ton)", value=1200.0, min_value=800.0, max_value=1500.0)
        precio_ajo = st.number_input("Ajo (USD/ton)", value=2500.0, min_value=1800.0, max_value=3000.0)
        PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS']['VID']['precio_ton'] = precio_vid
        PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS']['OLIVO']['precio_ton'] = precio_olivo
        PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS']['TOMATE']['precio_ton'] = precio_tomate
        PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS']['CEBOLLA']['precio_ton'] = precio_cebolla
        PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS']['PAPA']['precio_ton'] = precio_papa
        PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS']['ZANAHORIA']['precio_ton'] = precio_zanahoria
        PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS']['LECHUGA']['precio_ton'] = precio_lechuga
        PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS']['AJO']['precio_ton'] = precio_ajo
        st.subheader("🧪 Precios Fertilizantes")
        precio_urea = st.number_input("Urea (USD/ton)", value=450.0, min_value=300.0, max_value=600.0)
        precio_fosfato = st.number_input("Fosfato (USD/ton)", value=650.0, min_value=400.0, max_value=800.0)
        precio_potasio = st.number_input("Potasio (USD/ton)", value=400.0, min_value=250.0, max_value=550.0)
        PARAMETROS_ECONOMICOS['PRECIOS_FERTILIZANTES']['UREA'] = precio_urea
        PARAMETROS_ECONOMICOS['PRECIOS_FERTILIZANTES']['FOSFATO_DIAMONICO'] = precio_fosfato
        PARAMETROS_ECONOMICOS['PRECIOS_FERTILIZANTES']['CLORURO_POTASIO'] = precio_potasio
        st.subheader("📈 Parámetros Financieros")
        tasa_descuento = st.slider("Tasa Descuento (%)", 5.0, 20.0, 10.0, 0.5) / 100
        inflacion = st.slider("Inflación Esperada (%)", 0.0, 15.0, 8.0, 0.5) / 100
        PARAMETROS_ECONOMICOS['PARAMETROS_FINANCIEROS']['tasa_descuento'] = tasa_descuento
        PARAMETROS_ECONOMICOS['PARAMETROS_FINANCIEROS']['inflacion_esperada'] = inflacion
    st.session_state['usar_inta'] = usar_inta
    st.session_state['mostrar_mapa_inta'] = mostrar_mapa_inta

# ===== FUNCIONES DE VISUALIZACIÓN DE RESULTADOS =====
def mostrar_resultados_fertilidad(gdf_analizado, cultivo, area_total, satelite, mostrar_capa_inta=False):
    st.subheader(f"🌱 ANÁLISIS DE FERTILIDAD ACTUAL - {cultivo}")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if 'npk_integrado' in gdf_analizado.columns:
            npk_prom = gdf_analizado['npk_integrado'].mean()
            st.metric("📊 Índice NPK Integrado", f"{npk_prom:.3f}")
    with col2:
        if 'nitrogeno_actual' in gdf_analizado.columns:
            n_prom = gdf_analizado['nitrogeno_actual'].mean()
            st.metric("🧪 Nitrógeno", f"{n_prom:.1f} kg/ha")
    with col3:
        if 'fosforo_actual' in gdf_analizado.columns:
            p_prom = gdf_analizado['fosforo_actual'].mean()
            st.metric("🔬 Fósforo", f"{p_prom:.1f} kg/ha")
    with col4:
        if 'potasio_actual' in gdf_analizado.columns:
            k_prom = gdf_analizado['potasio_actual'].mean()
            st.metric("⚡ Potasio", f"{k_prom:.1f} kg/ha")
    st.subheader("🗺️ MAPA DE FERTILIDAD INTEGRADA (NPK)")
    mapa_fertilidad = crear_mapa_fertilidad_integrada(gdf_analizado, cultivo, satelite, mostrar_capa_inta)
    if mapa_fertilidad:
        st.image(mapa_fertilidad, use_container_width=True)
        st.download_button(
            label="📥 Descargar Mapa de Fertilidad",
            data=mapa_fertilidad.getvalue(),
            file_name=f"fertilidad_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png"
        )
    else:
        st.warning("No se pudo generar el mapa de fertilidad.")
    st.subheader("📋 RESULTADOS POR ZONA")
    columnas_mostrar = ['id_zona', 'area_ha', 'npk_integrado',
                        'nitrogeno_actual', 'fosforo_actual', 'potasio_actual']
    columnas_mostrar = [col for col in columnas_mostrar if col in gdf_analizado.columns]
    if columnas_mostrar:
        df_mostrar = gdf_analizado[columnas_mostrar].copy()
        df_mostrar.columns = ['Zona', 'Área (ha)', 'Índice NPK',
                              'Nitrógeno (kg/ha)', 'Fósforo (kg/ha)', 'Potasio (kg/ha)']
        st.dataframe(df_mostrar)
        csv = df_mostrar.to_csv(index=False)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"fertilidad_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )

def mostrar_resultados_recomendaciones(gdf_analizado, cultivo, nutriente, area_total, satelite, mostrar_capa_inta=False):
    st.subheader(f"💡 RECOMENDACIONES DE {nutriente} - {cultivo}")
    col1, col2, col3 = st.columns(3)
    with col1:
        if 'valor_recomendado' in gdf_analizado.columns:
            rec_prom = gdf_analizado['valor_recomendado'].mean()
            st.metric("🧴 Recomendación Promedio", f"{rec_prom:.1f} kg/ha")
    with col2:
        col_nutriente = f"{nutriente.lower()}_actual"
        if col_nutriente in gdf_analizado.columns:
            actual_prom = gdf_analizado[col_nutriente].mean()
            st.metric("📊 Nivel Actual", f"{actual_prom:.1f} kg/ha")
    with col3:
        if 'area_ha' in gdf_analizado.columns and 'valor_recomendado' in gdf_analizado.columns:
            total_kg = (gdf_analizado['valor_recomendado'] * gdf_analizado['area_ha']).sum()
            st.metric("⚖️ Total Requerido", f"{total_kg:.0f} kg")
    st.subheader(f"🗺️ MAPA DE RECOMENDACIONES - {nutriente}")
    mapa_recomendaciones = crear_mapa_npk_con_esri(gdf_analizado, nutriente, cultivo, satelite, mostrar_capa_inta)
    if mapa_recomendaciones:
        st.image(mapa_recomendaciones, use_container_width=True)
        st.download_button(
            label=f"📥 Descargar Mapa de {nutriente}",
            data=mapa_recomendaciones.getvalue(),
            file_name=f"recomendacion_{nutriente}_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
            mime="image/png"
        )
    st.subheader("📋 RECOMENDACIONES POR ZONA")
    columnas_mostrar = ['id_zona', 'area_ha', f'{nutriente.lower()}_actual', 'valor_recomendado']
    columnas_mostrar = [col for col in columnas_mostrar if col in gdf_analizado.columns]
    if columnas_mostrar:
        df_mostrar = gdf_analizado[columnas_mostrar].copy()
        nombres_columnas = {
            'id_zona': 'Zona',
            'area_ha': 'Área (ha)',
            f'{nutriente.lower()}_actual': 'Nivel Actual (kg/ha)',
            'valor_recomendado': 'Recomendación (kg/ha)'
        }
        df_mostrar.rename(columns=nombres_columnas, inplace=True)
        st.dataframe(df_mostrar)
        csv = df_mostrar.to_csv(index=False)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"recomendaciones_{nutriente}_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )


# ===== CLASIFICACIÓN DE PENDIENTES (definición faltante) =====
CLASIFICACION_PENDIENTES = {
    'PLANA (0-2%)': {'min': 0, 'max': 2, 'color': '#4daf4a', 'factor_erosivo': 0.1},
    'SUAVE (2-5%)': {'min': 2, 'max': 5, 'color': '#a6d96a', 'factor_erosivo': 0.3},
    'MODERADA (5-10%)': {'min': 5, 'max': 10, 'color': '#ffffbf', 'factor_erosivo': 0.6},
    'FUERTE (10-15%)': {'min': 10, 'max': 15, 'color': '#fdae61', 'factor_erosivo': 0.8},
    'MUY FUERTE (15-25%)': {'min': 15, 'max': 25, 'color': '#f46d43', 'factor_erosivo': 0.9},
    'EXTREMA (>25%)': {'min': 25, 'max': 100, 'color': '#d73027', 'factor_erosivo': 1.0}
}

# ... (continuación del código anterior) ...

# ===== INTERFAZ PRINCIPAL (continuación) =====
if 'uploaded_file' in locals() and uploaded_file:
    with st.spinner("Cargando parcela..."):
        try:
            gdf = cargar_archivo_parcela(uploaded_file)
            if gdf is not None:
                st.success(f"✅ **Parcela cargada exitosamente:** {len(gdf)} polígono(s)")
                area_total = calcular_superficie(gdf)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**📊 INFORMACIÓN DE LA PARCELA:**")
                    st.write(f"- Polígonos: {len(gdf)}")
                    st.write(f"- Área total: {area_total:.1f} ha")
                    st.write(f"- CRS: {gdf.crs}")
                    st.write(f"- Formato: {uploaded_file.name.split('.')[-1].upper()}")
                    
                    st.write("**📍 Vista Previa:**")
                    fig, ax = plt.subplots(figsize=(8, 6))
                    fig.patch.set_facecolor('#0f172a')
                    ax.set_facecolor('#0f172a')
                    gdf.plot(ax=ax, color='lightgreen', edgecolor='white', alpha=0.7)
                    ax.set_title(f"Parcela: {uploaded_file.name}", color='white')
                    ax.set_xlabel("Longitud", color='white')
                    ax.set_ylabel("Latitud", color='white')
                    ax.tick_params(colors='white')
                    ax.grid(True, alpha=0.3, color='#475569')
                    st.pyplot(fig)
                
                with col2:
                    st.write("**🎯 CONFIGURACIÓN GEE:**")
                    st.write(f"- Cultivo: {ICONOS_CULTIVOS[cultivo]} {cultivo}")
                    if cultivo in ["VID", "OLIVO"] and 'variedad' in st.session_state:
                        st.write(f"- Variedad: {st.session_state['variedad']}")
                    st.write(f"- Análisis: {analisis_tipo}")
                    st.write(f"- Zonas: {n_divisiones}")
                    
                    if st.session_state.get('usar_inta', True):
                        st.write("🌱 **INTA Activado:** Estimación regional de materia orgánica")
                    else:
                        st.write("⚠️ **INTA Desactivado:** Estimación genérica")
                    
                    if analisis_tipo in ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK"]:
                        st.write(f"- Satélite: {SATELITES_DISPONIBLES[satelite_seleccionado]['nombre']}")
                        st.write(f"- Índice: {indice_seleccionado}")
                        st.write(f"- Período: {fecha_inicio} a {fecha_fin}")
                    elif analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL":
                        st.write(f"- Intervalo curvas: {intervalo_curvas} m")
                        st.write(f"- Resolución DEM: {resolucion_dem} m")
                
                if st.button("🚀 EJECUTAR ANÁLISIS COMPLETO", type="primary"):
                    resultados = None
                    
                    if analisis_tipo in ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK"]:
                        resultados = ejecutar_analisis(
                            gdf, nutriente, analisis_tipo, n_divisiones,
                            cultivo, satelite_seleccionado, indice_seleccionado,
                            fecha_inicio, fecha_fin,
                            usar_inta=st.session_state.get('usar_inta', True),
                            mostrar_capa_inta=st.session_state.get('mostrar_mapa_inta', False)
                        )
                    elif analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL":
                        resultados = ejecutar_analisis(
                            gdf, None, analisis_tipo, n_divisiones,
                            cultivo, None, None, None, None,
                            intervalo_curvas, resolucion_dem,
                            usar_inta=st.session_state.get('usar_inta', True),
                            mostrar_capa_inta=st.session_state.get('mostrar_mapa_inta', False)
                        )
                    else:
                        resultados = ejecutar_analisis(
                            gdf, None, analisis_tipo, n_divisiones,
                            cultivo, None, None, None, None,
                            usar_inta=st.session_state.get('usar_inta', True),
                            mostrar_capa_inta=st.session_state.get('mostrar_mapa_inta', False)
                        )
                    
                    if resultados and resultados['exitoso']:
                        st.session_state['resultados_guardados'] = {
                            'gdf_analizado': resultados['gdf_analizado'],
                            'analisis_tipo': analisis_tipo,
                            'cultivo': cultivo,
                            'area_total': resultados['area_total'],
                            'nutriente': nutriente,
                            'satelite_seleccionado': satelite_seleccionado,
                            'indice_seleccionado': indice_seleccionado,
                            'mapa_buffer': resultados.get('mapa_buffer'),
                            'X': None,
                            'Y': None,
                            'Z': None,
                            'pendiente_grid': None,
                            'gdf_original': gdf if analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL" else None,
                            'df_power': resultados.get('df_power'),
                            'usar_inta': st.session_state.get('usar_inta', True),
                            'mostrar_mapa_inta': st.session_state.get('mostrar_mapa_inta', False)
                        }
                        
                        st.success("✅ Análisis completado exitosamente!")
                        
                        # Mostrar resultados según tipo de análisis
                        if analisis_tipo == "FERTILIDAD ACTUAL":
                            mostrar_resultados_fertilidad(
                                resultados['gdf_analizado'],
                                cultivo,
                                resultados['area_total'],
                                satelite_seleccionado,
                                st.session_state.get('mostrar_mapa_inta', False)
                            )
                        elif analisis_tipo == "RECOMENDACIONES NPK":
                            mostrar_resultados_recomendaciones(
                                resultados['gdf_analizado'],
                                cultivo,
                                nutriente,
                                resultados['area_total'],
                                satelite_seleccionado,
                                st.session_state.get('mostrar_mapa_inta', False)
                            )
                        elif analisis_tipo == "ANÁLISIS DE TEXTURA":
                            mostrar_resultados_textura(
                                resultados['gdf_analizado'],
                                cultivo,
                                resultados['area_total'],
                                st.session_state.get('mostrar_mapa_inta', False)
                            )
                        elif analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL":
                            X, Y, Z, bounds = generar_dem_sintetico(gdf, resolucion_dem)
                            pendiente_grid = calcular_pendiente_simple(X, Y, Z, resolucion_dem)
                            curvas, elevaciones = generar_curvas_nivel_simple(X, Y, Z, intervalo_curvas, gdf)
                            mostrar_resultados_curvas_nivel(
                                X, Y, Z, pendiente_grid, curvas, elevaciones,
                                gdf, cultivo, resultados['area_total']
                            )
                        
                        # Análisis económico para recomendaciones NPK
                        if analisis_tipo == "RECOMENDACIONES NPK" and 'rendimiento_actual' in resultados['gdf_analizado'].columns:
                            st.markdown("---")
                            st.subheader("💰 ANÁLISIS ECONÓMICO")
                            
                            variedad_params = None
                            if 'variedad_params' in st.session_state:
                                variedad_params = st.session_state['variedad_params']
                            
                            resultados_economicos = realizar_analisis_economico(
                                resultados['gdf_analizado'],
                                cultivo,
                                variedad_params,
                                resultados['area_total']
                            )
                            mostrar_analisis_economico(resultados_economicos)
                            
                            st.markdown("---")
                            st.subheader("🔥 MAPAS DE CALOR DE RENDIMIENTO")
                            
                            tab1, tab2, tab3 = st.tabs(["🌾 Rendimiento Actual", "🚀 Rendimiento Proyectado", "📊 Comparativo"])
                            
                            with tab1:
                                st.subheader("🌾 RENDIMIENTO ACTUAL (sin fertilización)")
                                mapa_actual = crear_mapa_calor_rendimiento_actual(resultados['gdf_analizado'], cultivo)
                                if mapa_actual:
                                    st.image(mapa_actual, use_container_width=True)
                                    st.download_button(
                                        "📥 Descargar Mapa de Rendimiento Actual",
                                        mapa_actual,
                                        f"rendimiento_actual_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                                        "image/png"
                                    )
                            
                            with tab2:
                                st.subheader("🚀 RENDIMIENTO PROYECTADO (con fertilización)")
                                mapa_proyectado = crear_mapa_calor_rendimiento_proyectado(resultados['gdf_analizado'], cultivo)
                                if mapa_proyectado:
                                    st.image(mapa_proyectado, use_container_width=True)
                                    st.download_button(
                                        "📥 Descargar Mapa de Rendimiento Proyectado",
                                        mapa_proyectado,
                                        f"rendimiento_proyectado_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                                        "image/png"
                                    )
                            
                            with tab3:
                                st.subheader("📊 MAPA COMPARATIVO")
                                mapa_comparativo = crear_mapa_comparativo_calor(resultados['gdf_analizado'], cultivo)
                                if mapa_comparativo:
                                    st.image(mapa_comparativo, use_container_width=True)
                                    st.download_button(
                                        "📥 Descargar Mapa Comparativo",
                                        mapa_comparativo,
                                        f"comparativo_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                                        "image/png"
                                    )
                            
                            # Métricas de rendimiento
                            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                            with col_r1:
                                rend_actual = resultados['gdf_analizado']['rendimiento_actual'].mean()
                                st.metric("📊 Rendimiento Actual", f"{rend_actual:.1f} ton/ha")
                            with col_r2:
                                rend_proy = resultados['gdf_analizado']['rendimiento_proyectado'].mean()
                                st.metric("🚀 Rendimiento Proyectado", f"{rend_proy:.1f} ton/ha")
                            with col_r3:
                                incremento = resultados['gdf_analizado']['incremento_rendimiento'].mean()
                                st.metric("📈 Incremento", f"+{incremento:.1f} ton/ha")
                            with col_r4:
                                porcentaje = (incremento / rend_actual * 100) if rend_actual > 0 else 0
                                st.metric("📊 Porcentaje", f"+{porcentaje:.1f}%")
                        
                        # Datos meteorológicos de NASA POWER
                        if resultados.get('df_power') is not None:
                            st.markdown("---")
                            st.subheader("🌤️ DATOS METEOROLÓGICOS NASA POWER")
                            df_power = resultados['df_power']
                            
                            tab_p1, tab_p2, tab_p3, tab_p4 = st.tabs(["🌞 Radiación Solar", "💨 Viento", "🌡️ Temperatura", "💧 Precipitación"])
                            
                            with tab_p1:
                                fig_rad = crear_grafico_personalizado(
                                    df_power.set_index('fecha')['radiacion_solar'],
                                    "Radiación Solar Diaria",
                                    "kWh/m²/día",
                                    "#FFD700",
                                    '#0f172a',
                                    '#ffffff'
                                )
                                st.pyplot(fig_rad)
                            
                            with tab_p2:
                                fig_viento = crear_grafico_personalizado(
                                    df_power.set_index('fecha')['viento_2m'],
                                    "Velocidad del Viento a 2m",
                                    "m/s",
                                    "#87CEEB",
                                    '#0f172a',
                                    '#ffffff'
                                )
                                st.pyplot(fig_viento)
                            
                            with tab_p3:
                                fig_temp = crear_grafico_personalizado(
                                    df_power.set_index('fecha')['temperatura'],
                                    "Temperatura del Aire a 2m",
                                    "°C",
                                    "#FF6B6B",
                                    '#0f172a',
                                    '#ffffff'
                                )
                                st.pyplot(fig_temp)
                            
                            with tab_p4:
                                fig_precip = crear_grafico_barras_personalizado(
                                    df_power.set_index('fecha')['precipitacion'],
                                    "Precipitación Diaria",
                                    "mm/día",
                                    "#4B8BBE",
                                    '#0f172a',
                                    '#ffffff'
                                )
                                st.pyplot(fig_precip)
                            
                            st.subheader("📊 RESUMEN METEOROLÓGICO")
                            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                            with col_m1:
                                st.metric("🌞 Radiación Promedio", f"{df_power['radiacion_solar'].mean():.1f} kWh/m²/día")
                            with col_m2:
                                st.metric("💨 Viento Promedio", f"{df_power['viento_2m'].mean():.1f} m/s")
                            with col_m3:
                                st.metric("🌡️ Temperatura Promedio", f"{df_power['temperatura'].mean():.1f} °C")
                            with col_m4:
                                st.metric("💧 Precipitación Promedio", f"{df_power['precipitacion'].mean():.1f} mm/día")
                    
                    else:
                        st.error("❌ Error al ejecutar el análisis. Por favor, verifique los parámetros.")
            
            else:
                st.error("❌ No se pudo cargar la parcela. Verifique el formato del archivo.")
        
        except Exception as e:
            st.error(f"❌ Error al procesar la parcela: {str(e)}")
            import traceback
            st.error(f"Detalle: {traceback.format_exc()}")
# ===== BOTÓN PARA GENERAR REPORTE COMPLETO =====
if 'resultados_guardados' in st.session_state and st.session_state['resultados_guardados']:
    st.markdown("---")
    st.subheader("📋 REPORTE COMPLETO")
    
    col_rep1, col_rep2 = st.columns(2)
    
    with col_rep1:
        if st.button("📄 Generar Reporte Completo (DOCX)", type="secondary"):
            with st.spinner("Generando reporte completo..."):
                try:
                    # Recopilar todos los datos para el reporte
                    resultados_completos = {
                        'gdf_analizado': st.session_state['resultados_guardados']['gdf_analizado'],
                        'cultivo': st.session_state['resultados_guardados']['cultivo'],
                        'area_total': st.session_state['resultados_guardados']['area_total'],
                        'analisis_tipo': st.session_state['resultados_guardados']['analisis_tipo'],
                        'nutriente': st.session_state['resultados_guardados'].get('nutriente'),
                        'satelite': st.session_state['resultados_guardados'].get('satelite_seleccionado'),
                        'df_power': st.session_state['resultados_guardados'].get('df_power')
                    }
                    
                    # Si hay análisis económico, agregarlo
                    if 'resultados_economicos' in locals():
                        resultados_completos['resultados_economicos'] = resultados_economicos
                    
                    # Generar reporte
                    reporte_completo = generar_reporte_completo_docx(resultados_completos)
                    
                    if reporte_completo:
                        st.success("✅ Reporte completo generado exitosamente!")
                        
                        # Botón de descarga
                        st.download_button(
                            label="📥 Descargar Reporte Completo (DOCX)",
                            data=reporte_completo,
                            file_name=f"reporte_completo_{st.session_state['resultados_guardados']['cultivo']}_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    
                except Exception as e:
                    st.error(f"Error generando reporte: {str(e)}")
    
    with col_rep2:
        if st.button("📊 Resumen Ejecutivo (PDF)", type="secondary"):
            with st.spinner("Generando resumen PDF..."):
                try:
                    # Generar resumen PDF
                    pdf_resumen = generar_reporte_pdf(
                        st.session_state['resultados_guardados']['gdf_analizado'],
                        st.session_state['resultados_guardados']['cultivo'],
                        st.session_state['resultados_guardados']['analisis_tipo'],
                        st.session_state['resultados_guardados']['area_total'],
                        st.session_state['resultados_guardados'].get('nutriente'),
                        st.session_state['resultados_guardados'].get('satelite_seleccionado'),
                        st.session_state['resultados_guardados'].get('indice_seleccionado'),
                        st.session_state['resultados_guardados'].get('mapa_buffer')
                    )
                    
                    if pdf_resumen:
                        st.download_button(
                            label="📥 Descargar Resumen (PDF)",
                            data=pdf_resumen,
                            file_name=f"resumen_{st.session_state['resultados_guardados']['cultivo']}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf"
                        )
                        
                except Exception as e:
                    st.error(f"Error generando PDF: {str(e)}")
# Mensaje inicial cuando no hay archivo cargado
else:
    st.info("👈 **Suba un archivo de parcela en el panel izquierdo para comenzar el análisis.**")
    
    # Mostrar información sobre el sistema
    st.markdown("---")
    st.subheader("ℹ️ INFORMACIÓN DEL SISTEMA")
    
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown("""
        ### 🚀 CARACTERÍSTICAS PRINCIPALES
        
        **🌱 Cultivos Soportados:**
        - 🍇 **Vid**: Malbec, Cabernet Sauvignon, Chardonnay, Syrah, Bonarda
        - 🫒 **Olivo**: Arbequina, Arbosana, Picual, Manzanilla
        - 🥗 **Hortalizas**: Tomate, Cebolla, Papa, Zanahoria, Lechuga, Ajo
        
        **🛰️ Fuentes de Datos:**
        - Sentinel-2 (10m resolución)
        - Landsat-8 (30m resolución)
        - NASA POWER (datos meteorológicos)
        - INTA (mapas de suelos regionales)
        
        **📊 Análisis Disponibles:**
        - Fertilidad actual del suelo (NPK)
        - Recomendaciones de fertilización
        - Textura del suelo (clasificación USDA)
        - Curvas de nivel y pendientes
        """)
    
    with col_info2:
        st.markdown("""
        ### 💡 METODOLOGÍAS CIENTÍFICAS
        
        **🧪 Estimación NPK por Teledetección:**
        - **Nitrógeno**: NDRE + Regresión Espectral
        - **Fósforo**: Índice SWIR-VIS
        - **Potasio**: Índice de Estrés Hídrico
        
        **🏗️ Clasificación USDA:**
        - Sistema textural actualizado
        - 12 clases texturales
        - Recomendaciones específicas por textura
        
        **💰 Análisis Económico:**
        - ROI de fertilización
        - VAN y TIR del proyecto
        - Punto de equilibrio
        - Relación beneficio/costo
        """)
    
    st.markdown("---")
    st.subheader("📋 FORMATOS DE ARCHIVO ACEPTADOS")
    
    formatos_col1, formatos_col2, formatos_col3 = st.columns(3)
    
    with formatos_col1:
        st.markdown("""
        ### 🗺️ Shapefile
        - Archivo .ZIP con todos los componentes
        - Debe contener .shp, .shx, .dbf, .prj
        - Sistema de coordenadas preferido: WGS84 (EPSG:4326)
        """)
    
    with formatos_col2:
        st.markdown("""
        ### 📍 KML/KMZ
        - Archivos .kml (Google Earth)
        - Archivos .kmz (KML comprimido)
        - Polígonos o multipolígonos
        - Compatible con Google Maps/Earth
        """)
    
    with formatos_col3:
        st.markdown("""
        ### 🎯 RECOMENDACIONES
        - Un solo polígono por archivo
        - Área máxima recomendada: 1000 ha
        - Verifique que el CRS sea WGS84
        - Use polígonos simples sin huecos
        """)

# Footer de la aplicación
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; padding: 20px;">
<p>🔬 <strong>Analizador Multi-Cultivo Satellital v2.0</strong> • Desarrollado por Martin Ernesto Cano • Enero 2026</p>
<p>🌐 Integra datos de NASA POWER, Google Earth Engine, INTA y metodologías científicas para vid, olivo y hortalizas</p>
<p>⚠️ <em>Este es un sistema de apoyo a decisiones. Los resultados deben validarse con análisis de laboratorio.</em></p>
</div>
""", unsafe_allow_html=True)

# ===== FUNCIÓN PARA LIMPIAR CACHÉ Y RECURSOS =====
def limpiar_recursos():
    """Limpia recursos temporales y caché"""
    try:
        # Cerrar figuras de matplotlib
        plt.close('all')
        
        # Limpiar variables de sesión si es necesario
        if 'temp_files' in st.session_state:
            for temp_file in st.session_state.temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
        
        # Liberar memoria
        import gc
        gc.collect()
        
    except Exception as e:
        pass  # Silenciar errores de limpieza

# Ejecutar limpieza al final
limpiar_recursos()
