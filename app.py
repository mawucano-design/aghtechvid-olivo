# app.py — Versión FINAL CORREGIDA con exportaciones GeoJSON funcionales y sin PDF
# Autor: Martin Ernesto Cano | Enero 2026
# Correcciones: CRS EPSG:4326 garantizado en GeoJSON, eliminación de PDF, preservación total de funcionalidades

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
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
import math
import warnings
import xml.etree.ElementTree as ET
import json
from io import BytesIO
from docx import Document  # MANTIENE DOCX (PDF ELIMINADO)
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import geojson
import requests
import contextily as ctx
from pyproj import CRS
import scipy
from scipy.interpolate import griddata as scipy_griddata
warnings.filterwarnings('ignore')

# ===== USAR TODO EL ANCHO DE LA PANTALLA =====
st.set_page_config(layout="wide", page_title="Analizador Agrícola Satelital - Mendoza", page_icon="🍇")

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
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
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
        <h1 class="hero-title">🍇 ANALIZADOR PARA VID, OLIVO Y HORTALIZAS EN MENDOZA</h1>
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
        
        if arcilla_pct >= 40:
            if limo_pct >= 40:
                return "Arcilla limosa"
            elif arena_pct <= 45:
                return "Arcilla"
            else:
                return "Arcilla arenosa"
        elif arcilla_pct >= 27 and arcilla_pct < 40:
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

# ===== CLASIFICACIÓN DE PENDIENTES PARA ANÁLISIS DE EROSIÓN =====
CLASIFICACION_PENDIENTES = {
    'PLANA (0-2%)': {'min': 0, 'max': 2, 'color': '#4daf4a', 'factor_erosivo': 0.1},
    'SUAVE (2-5%)': {'min': 2, 'max': 5, 'color': '#a6d96a', 'factor_erosivo': 0.3},
    'MODERADA (5-10%)': {'min': 5, 'max': 10, 'color': '#ffffbf', 'factor_erosivo': 0.6},
    'FUERTE (10-15%)': {'min': 10, 'max': 15, 'color': '#fdae61', 'factor_erosivo': 0.8},
    'MUY FUERTE (15-25%)': {'min': 15, 'max': 25, 'color': '#f46d43', 'factor_erosivo': 0.9},
    'EXTREMA (>25%)': {'min': 25, 'max': 100, 'color': '#d73027', 'factor_erosivo': 1.0}
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
if 'usar_inta' not in st.session_state:
    st.session_state['usar_inta'] = True
if 'mostrar_mapa_inta' not in st.session_state:
    st.session_state['mostrar_mapa_inta'] = False

# Valores por defecto para variables críticas
nutriente = "NITRÓGENO"
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
    """Garantiza CRS EPSG:4326 para todas las operaciones"""
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
    """Calcula área en hectáreas con precisión geodésica"""
    try:
        if gdf is None or len(gdf) == 0:
            return 0.0
        
        gdf = validar_y_corregir_crs(gdf)
        centroid = gdf.geometry.unary_union.centroid
        lon, lat = centroid.x, centroid.y
        
        # Calcular zona UTM
        utm_zone = int((lon + 180) / 6) + 1
        hemisphere = 'north' if lat >= 0 else 'south'
        epsg_utm = f"326{utm_zone:02d}" if hemisphere == 'north' else f"327{utm_zone:02d}"
        
        try:
            gdf_utm = gdf.to_crs(epsg=epsg_utm)
            area_m2 = gdf_utm.geometry.area.sum()
        except Exception:
            # Fallback a CRS de área igual
            gdf_eq = gdf.to_crs("EPSG:6933")
            area_m2 = gdf_eq.geometry.area.sum()
        
        return area_m2 / 10000
    except Exception as e:
        st.warning(f"⚠️ Error al calcular área precisa: {str(e)}. Usando cálculo aproximado.")
        area_grados2 = gdf.geometry.area.sum()
        area_m2 = area_grados2 * (111000 ** 2)
        return area_m2 / 10000

def dividir_parcela_en_zonas(gdf, n_zonas):
    """Divide parcela en zonas de manejo homogéneas"""
    if len(gdf) == 0:
        return gdf
    
    gdf = validar_y_corregir_crs(gdf)
    parcela_principal = gdf.iloc[0].geometry
    
    # Manejar MultiPolygon
    if parcela_principal.geom_type == 'MultiPolygon':
        parcela_principal = max(parcela_principal.geoms, key=lambda p: p.area)
    
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
            
            cell_poly = Polygon([(cell_minx, cell_miny), (cell_maxx, cell_miny), 
                                (cell_maxx, cell_maxy), (cell_minx, cell_maxy)])
            
            if not cell_poly.is_valid:
                cell_poly = cell_poly.buffer(0)
            
            intersection = parcela_principal.intersection(cell_poly)
            
            if not intersection.is_empty and intersection.area > 0:
                # Manejar geometrías múltiples
                if intersection.geom_type in ['Polygon', 'MultiPolygon']:
                    if intersection.geom_type == 'MultiPolygon':
                        for geom in intersection.geoms:
                            if geom.area > 0:
                                sub_poligonos.append(geom)
                    else:
                        sub_poligonos.append(intersection)
    
    if sub_poligonos:
        nuevo_gdf = gpd.GeoDataFrame({'id_zona': range(1, len(sub_poligonos) + 1), 
                                     'geometry': sub_poligonos}, 
                                     crs='EPSG:4326')
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
        
        # Buscar polígonos en el KML
        for placemark in root.findall('.//kml:Placemark', namespaces):
            # Buscar Polygon
            polygon_elem = placemark.find('.//kml:Polygon', namespaces)
            if polygon_elem is not None:
                coords_elem = polygon_elem.find('.//kml:coordinates', namespaces)
                if coords_elem is not None and coords_elem.text:
                    coord_text = coords_elem.text.strip()
                    coord_list = []
                    for coord_pair in coord_text.split():
                        parts = coord_pair.split(',')
                        if len(parts) >= 2:
                            try:
                                lon = float(parts[0])
                                lat = float(parts[1])
                                coord_list.append((lon, lat))
                            except:
                                continue
                    
                    if len(coord_list) >= 3:
                        # Cerrar el polígono si no está cerrado
                        if coord_list[0] != coord_list[-1]:
                            coord_list.append(coord_list[0])
                        polygons.append(Polygon(coord_list))
        
        if polygons:
            gdf = gpd.GeoDataFrame({'geometry': polygons}, crs='EPSG:4326')
            return gdf
        else:
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
            
            # Convertir MultiPolygon a Polygon si es necesario
            gdf = gdf.explode(index_parts=False)
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
            
            # Ajustar por condiciones del cultivo
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
        
        else:  # DATOS_SIMULADOS
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
        
        # Nitrógeno
        n_actual = row['nitrogeno_actual']
        n_optimo = params['NITROGENO']['optimo']
        if n_actual < n_optimo * 0.9:
            deficiencia_n = max(0, n_optimo - n_actual)
            eficiencia_n = params['RESPUESTA_N'] * 0.7
            incremento_n = deficiencia_n * eficiencia_n
            incremento_total += min(incremento_n, deficiencia_n * params['RESPUESTA_N'])
        
        # Fósforo
        p_actual = row['fosforo_actual']
        p_optimo = params['FOSFORO']['optimo']
        if p_actual < p_optimo * 0.85:
            deficiencia_p = max(0, p_optimo - p_actual)
            eficiencia_p = params['RESPUESTA_P'] * 0.5
            incremento_p = deficiencia_p * eficiencia_p
            incremento_total += incremento_p
        
        # Potasio
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
def realizar_analisis_economico(gdf_analizado, cultivo, variedad_params, area_total):
    precios_cultivo = PARAMETROS_ECONOMICOS['PRECIOS_CULTIVOS'][cultivo]
    precios_fert = PARAMETROS_ECONOMICOS['PRECIOS_FERTILIZANTES']
    conversion = PARAMETROS_ECONOMICOS['CONVERSION_NUTRIENTES']
    financieros = PARAMETROS_ECONOMICOS['PARAMETROS_FINANCIEROS']
    
    rend_actual_prom = gdf_analizado['rendimiento_actual'].mean()
    rend_proy_prom = gdf_analizado['rendimiento_proyectado'].mean()
    incremento_prom = gdf_analizado['incremento_rendimiento'].mean()
    
    # Obtener parámetros del cultivo
    if cultivo in ['VID', 'OLIVO']:
        params_cultivo = PARAMETROS_CULTIVOS[cultivo]
    else:
        params_cultivo = PARAMETROS_HORTALIZAS[cultivo]
    
    # Ajustar por variedad si se proporcionan parámetros
    if variedad_params:
        n_optimo = variedad_params.get('NITROGENO_OPTIMO', params_cultivo['NITROGENO']['optimo'])
        p_optimo = variedad_params.get('FOSFORO_OPTIMO', params_cultivo['FOSFORO']['optimo'])
        k_optimo = variedad_params.get('POTASIO_OPTIMO', params_cultivo['POTASIO']['optimo'])
    else:
        n_optimo = params_cultivo['NITROGENO']['optimo']
        p_optimo = params_cultivo['FOSFORO']['optimo']
        k_optimo = params_cultivo['POTASIO']['optimo']
    
    # Calcular deficiencias totales en todo el campo
    fertilizante_necesario = {'NITRÓGENO': 0, 'FÓSFORO': 0, 'POTASIO': 0}
    
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
    
    # Calcular costos
    costos = {
        'semilla': precios_cultivo['costo_semilla'],
        'herbicidas': precios_cultivo['costo_herbicidas'],
        'insecticidas': precios_cultivo['costo_insecticidas'],
        'labores': precios_cultivo['costo_labores'],
        'cosecha': precios_cultivo['costo_cosecha'],
        'otros': precios_cultivo['costo_otros']
    }
    
    costos_fertilizacion = 0
    
    # Costo de nitrógeno
    if fertilizante_necesario['NITRÓGENO'] > 0:
        fuente_n = conversion['NITRÓGENO']['fuente_principal']
        contenido_n = conversion['NITRÓGENO']['contenido_nutriente']
        eficiencia_n = conversion['NITRÓGENO']['eficiencia']
        kg_fertilizante_n = (fertilizante_necesario['NITRÓGENO'] / contenido_n) / eficiencia_n
        costo_n = (kg_fertilizante_n / 1000) * precios_fert[fuente_n]
        costos_fertilizacion += costo_n
    
    # Costo de fósforo
    if fertilizante_necesario['FÓSFORO'] > 0:
        fuente_p = conversion['FÓSFORO']['fuente_principal']
        contenido_p = conversion['FÓSFORO']['contenido_nutriente']
        eficiencia_p = conversion['FÓSFORO']['eficiencia']
        kg_fertilizante_p = (fertilizante_necesario['FÓSFORO'] / contenido_p) / eficiencia_p
        costo_p = (kg_fertilizante_p / 1000) * precios_fert[fuente_p]
        costos_fertilizacion += costo_p
    
    # Costo de potasio
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
    
    # Calcular ROI
    if costos_fertilizacion > 0:
        roi_fertilizacion = (incremento_margen_ha / costos_fertilizacion) * 100
    else:
        roi_fertilizacion = 0
    
    # Calcular relación B/C
    if costo_total_ha > 0:
        relacion_bc_actual = margen_actual_ha / costo_total_ha if margen_actual_ha > 0 else 0
        relacion_bc_proy = margen_proy_ha / costo_total_ha if margen_proy_ha > 0 else 0
    else:
        relacion_bc_actual = 0
        relacion_bc_proy = 0
    
    # Calcular VAN y TIR
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
    
    # Calcular punto de equilibrio
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

# ===== FUNCIONES DE EXPORTACIÓN CORREGIDAS (SIN PDF) =====
def exportar_a_geojson(gdf, nombre_base="parcela"):
    """Exporta GeoDataFrame a GeoJSON con CRS EPSG:4326 garantizado"""
    try:
        gdf = validar_y_corregir_crs(gdf)
        geojson_data = gdf.to_json()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"{nombre_base}_{timestamp}.geojson"
        return geojson_data, nombre_archivo
    except Exception as e:
        st.error(f"❌ Error exportando a GeoJSON: {str(e)}")
        return None, None

def exportar_a_geojson_completo(gdf, cultivo, analisis_tipo, metadata=None):
    """Exporta GeoDataFrame a GeoJSON con metadatos completos en EPSG:4326"""
    try:
        gdf = validar_y_corregir_crs(gdf.copy())
        gdf = gdf[gdf.geometry.notnull() & gdf.geometry.is_valid]
        
        if 'area_ha' not in gdf.columns:
            gdf['area_ha'] = gdf.geometry.area * (111000**2) / 10000
        
        gdf['cultivo'] = cultivo
        gdf['tipo_analisis'] = analisis_tipo
        gdf['fecha_analisis'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for col in gdf.select_dtypes(include=[np.number]).columns:
            if col != 'id_zona':
                gdf[col] = gdf[col].round(2)
        
        geojson_dict = json.loads(gdf.to_json())
        geojson_dict['metadata'] = {
            'sistema': 'Analizador Agrícola Satelital v2.0',
            'desarrollador': 'Martin Ernesto Cano',
            'cultivo': cultivo,
            'tipo_analisis': analisis_tipo,
            'numero_zonas': len(gdf),
            'area_total_ha': round(gdf['area_ha'].sum(), 2),
            'fecha_generacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'coordenadas_sistema': 'WGS84 (EPSG:4326)'
        }
        
        geojson_final = json.dumps(geojson_dict, indent=2, ensure_ascii=False)
        nombre_archivo = f"analisis_{cultivo.lower()}_{analisis_tipo.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"
        return geojson_final, nombre_archivo
        
    except Exception as e:
        st.error(f"❌ Error exportando GeoJSON: {str(e)}")
        return None, None

def exportar_imagen(fig, nombre_base, formato='png', dpi=300):
    """Exporta figura matplotlib a imagen de alta calidad"""
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format=formato, dpi=dpi, bbox_inches='tight', 
                   facecolor=fig.get_facecolor(), edgecolor='none')
        buf.seek(0)
        nombre_archivo = f"{nombre_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{formato}"
        return buf, nombre_archivo
    except Exception as e:
        st.error(f"❌ Error exportando imagen: {str(e)}")
        return None, None

def crear_paquete_completo(resultados_dict):
    """Crea ZIP con todos los resultados del análisis (SIN PDF)"""
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # 1. GeoJSON
            if 'gdf_analizado' in resultados_dict:
                geojson_data, geojson_name = exportar_a_geojson_completo(
                    resultados_dict['gdf_analizado'],
                    resultados_dict.get('cultivo', 'desconocido'),
                    resultados_dict.get('analisis_tipo', 'completo')
                )
                if geojson_data:
                    zip_file.writestr(geojson_name, geojson_data.encode('utf-8'))
            
            # 2. CSV
            if 'gdf_analizado' in resultados_dict:
                df_csv = resultados_dict['gdf_analizado'].drop(columns=['geometry'], errors='ignore')
                csv_buffer = io.BytesIO()
                df_csv.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                csv_buffer.seek(0)
                zip_file.writestr(f"datos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", csv_buffer.getvalue())
            
            # 3. Mapas (si existen en resultados_dict)
            for key, nombre_base in [('mapa_fertilidad', 'fertilidad'), ('mapa_rendimiento', 'rendimiento')]:
                if key in resultados_dict and resultados_dict[key]:
                    try:
                        img_data = resultados_dict[key].getvalue() if isinstance(resultados_dict[key], io.BytesIO) else resultados_dict[key]
                        zip_file.writestr(f"mapa_{nombre_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png", img_data)
                    except:
                        pass
            
            # 4. README
            readme = f"""
PAQUETE DE RESULTADOS AGRÍCOLAS
===============================
Cultivo: {resultados_dict.get('cultivo', 'N/A')}
Área total: {resultados_dict.get('area_total', 0):.2f} ha
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CONTENIDO:
- Archivo GeoJSON: Datos espaciales en EPSG:4326
- CSV: Datos tabulares por zona de manejo
- Mapas PNG: Visualización de fertilidad y rendimiento
- Sistema compatible con QGIS, ArcGIS y Google Earth Pro

METODOLOGÍA:
- Estimación NPK mediante teledetección satelital
- Zonificación de manejo variable
- Integración con parámetros agronómicos locales

Desarrollado por: Martin Ernesto Cano (mawucano@gmail.com)
"""
            zip_file.writestr("INSTRUCCIONES.txt", readme.encode('utf-8'))
        
        zip_buffer.seek(0)
        nombre_zip = f"resultados_agricolas_{resultados_dict.get('cultivo', 'analisis')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        return zip_buffer, nombre_zip
        
    except Exception as e:
        st.error(f"❌ Error creando paquete ZIP: {str(e)}")
        return None, None

# ===== FUNCIONES PARA GENERAR MAPAS DE CALOR DE RENDIMIENTO =====
# ===== FUNCIONES PARA MAPAS DE CALOR DE RENDIMIENTO =====
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
                          alpha=0.9))
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
        zi_incremento = griddata((x, y), incrementos, (xi, yi), method='linear', fill_value=np.nan)
        im1 = ax1.contourf(xi, yi, zi_actual, levels=40, cmap='RdYlGn', alpha=0.8, vmin=vmin, vmax=vmax)
        contour1 = ax1.contour(xi, yi, zi_actual, levels=6, colors='white', linewidths=1, alpha=0.5)
        ax1.clabel(contour1, inline=True, fontsize=8, colors='white', fmt='%1.1f t')
        for centroid, valor in zip(centroids, z_actual):
            ax1.plot(centroid.x, centroid.y, 'o', markersize=6,
                     markeredgecolor='white', markerfacecolor=plt.cm.RdYlGn((valor - vmin)/(vmax - vmin)))
        im2 = ax2.contourf(xi, yi, zi_proyectado, levels=40, cmap='RdYlGn', alpha=0.8, vmin=vmin, vmax=vmax)
        contour2 = ax2.contour(xi, yi, zi_proyectado, levels=6, colors='white', linewidths=1, alpha=0.5)
        ax2.clabel(contour2, inline=True, fontsize=8, colors='white', fmt='%1.1f t')
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

# ===== FUNCIONES PARA GENERAR MAPAS DE CALOR DE RENDIMIENTO =====
def crear_mapa_calor_rendimiento_actual(gdf_analizado, cultivo):
    try:
        if 'rendimiento_actual' not in gdf_analizado.columns:
            return None
        
        # Convertir a Web Mercator para mapas base
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        # Obtener centroides y valores
        centroids = gdf_plot.geometry.centroid
        x = np.array([c.x for c in centroids])
        y = np.array([c.y for c in centroids])
        z = gdf_plot['rendimiento_actual'].values
        
        # Definir límites para la interpolación
        x_min, y_min, x_max, y_max = gdf_plot.total_bounds
        xi = np.linspace(x_min, x_max, 200)
        yi = np.linspace(y_min, y_max, 200)
        xi, yi = np.meshgrid(xi, yi)
        
        # Interpolación
        try:
            zi = scipy_griddata((x, y), z, (xi, yi), method='cubic', fill_value=np.nan)
        except:
            zi = scipy_griddata((x, y), z, (xi, yi), method='linear', fill_value=np.nan)
        
        # Crear mapa de calor
        im = ax.contourf(xi, yi, zi, levels=50, cmap='RdYlGn', alpha=0.8,
                        vmin=z.min()*0.9, vmax=z.max()*1.1)
        
        # Contornos
        contour = ax.contour(xi, yi, zi, levels=10, colors='white', linewidths=0.5, alpha=0.5)
        
        # Etiquetas en centroides
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
        
        # Añadir mapa base Esri
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.4)
        except:
            pass
        
        # Título y etiquetas
        ax.set_title(f'🌾 MAPA DE CALOR - RENDIMIENTO ACTUAL\n{cultivo} (ton/ha)',
                    fontsize=16, fontweight='bold', pad=20, color='white')
        ax.set_xlabel('Longitud', color='white')
        ax.set_ylabel('Latitud', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.1, color='#475569', linestyle='--')
        
        # Colorbar
        cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label('Rendimiento (ton/ha)', fontsize=12, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        cbar.outline.set_edgecolor('white')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
        
        # Estadísticas
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
            zi_proyectado = scipy_griddata((x, y), z_proyectado, (xi, yi), method='cubic', fill_value=np.nan)
            zi_incremento = scipy_griddata((x, y), incrementos, (xi, yi), method='cubic', fill_value=np.nan)
        except:
            zi_proyectado = scipy_griddata((x, y), z_proyectado, (xi, yi), method='linear', fill_value=np.nan)
            zi_incremento = scipy_griddata((x, y), incrementos, (xi, yi), method='linear', fill_value=np.nan)
        
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
• Aumento: +{(incrementos.mean()/z_actual.mean()*100 if z_actual.mean() > 0 else 0):.1f}%
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
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        fig.patch.set_facecolor('#0f172a')
        
        for ax in [ax1, ax2]:
            ax.set_facecolor('#0f172a')
        
        # Mapa 1: Rendimiento Actual
        centroids = gdf_plot.geometry.centroid
        x = np.array([c.x for c in centroids])
        y = np.array([c.y for c in centroids])
        z_actual = gdf_plot['rendimiento_actual'].values
        
        x_min, y_min, x_max, y_max = gdf_plot.total_bounds
        xi = np.linspace(x_min, x_max, 150)
        yi = np.linspace(y_min, y_max, 150)
        xi, yi = np.meshgrid(xi, yi)
        
        try:
            zi_actual = scipy_griddata((x, y), z_actual, (xi, yi), method='cubic', fill_value=np.nan)
        except:
            zi_actual = scipy_griddata((x, y), z_actual, (xi, yi), method='linear', fill_value=np.nan)
        
        im1 = ax1.contourf(xi, yi, zi_actual, levels=40, cmap='YlOrRd', alpha=0.85,
                          vmin=z_actual.min()*0.9, vmax=z_actual.max()*1.1)
        
        for idx, (centroid, valor) in enumerate(zip(centroids, z_actual)):
            ax1.plot(centroid.x, centroid.y, 'o', markersize=6,
                    markeredgecolor='white', markerfacecolor=plt.cm.YlOrRd((valor - z_actual.min())/(z_actual.max() - z_actual.min())),
                    alpha=0.9)
            
            if idx % 3 == 0:
                ax1.annotate(f"{valor:.1f}",
                           (centroid.x, centroid.y),
                           xytext=(0, 8), textcoords="offset points",
                           fontsize=7, color='white', weight='bold',
                           ha='center', va='center',
                           bbox=dict(boxstyle="circle,pad=0.2",
                                    facecolor=(0, 0, 0, 0.6),
                                    alpha=0.8))
        
        try:
            ctx.add_basemap(ax1, source=ctx.providers.Esri.WorldImagery, alpha=0.3)
        except:
            pass
        
        ax1.set_title(f'🌾 RENDIMIENTO ACTUAL\n{cultivo}', fontsize=14, fontweight='bold', color='white', pad=15)
        ax1.set_xlabel('Longitud', color='white')
        ax1.set_ylabel('Latitud', color='white')
        ax1.tick_params(colors='white')
        ax1.grid(True, alpha=0.15, color='#475569')
        
        cbar1 = plt.colorbar(im1, ax=ax1, shrink=0.8, pad=0.03)
        cbar1.set_label('ton/ha', fontsize=10, color='white', weight='bold')
        cbar1.ax.yaxis.set_tick_params(color='white')
        cbar1.outline.set_edgecolor('white')
        plt.setp(cbar1.ax.get_yticklabels(), color='white')
        
        # Mapa 2: Rendimiento Proyectado
        z_proyectado = gdf_plot['rendimiento_proyectado'].values
        incrementos = z_proyectado - z_actual
        
        try:
            zi_proyectado = scipy_griddata((x, y), z_proyectado, (xi, yi), method='cubic', fill_value=np.nan)
        except:
            zi_proyectado = scipy_griddata((x, y), z_proyectado, (xi, yi), method='linear', fill_value=np.nan)
        
        im2 = ax2.contourf(xi, yi, zi_proyectado, levels=40, cmap='RdYlGn', alpha=0.85,
                          vmin=z_proyectado.min()*0.9, vmax=z_proyectado.max()*1.1)
        
        for idx, (centroid, valor, inc) in enumerate(zip(centroids, z_proyectado, incrementos)):
            size = 5 + (inc / incrementos.max() * 8) if incrementos.max() > 0 else 6
            ax2.plot(centroid.x, centroid.y, 'o', markersize=size,
                    markeredgecolor='cyan', markerfacecolor=plt.cm.RdYlGn((valor - z_proyectado.min())/(z_proyectado.max() - z_proyectado.min())),
                    alpha=0.9, markeredgewidth=1.5)
            
            if idx % 3 == 0:
                ax2.annotate(f"+{inc:.1f}",
                           (centroid.x, centroid.y),
                           xytext=(0, 8), textcoords="offset points",
                           fontsize=7, color='cyan', weight='bold',
                           ha='center', va='center',
                           bbox=dict(boxstyle="round,pad=0.2",
                                    facecolor=(0, 0, 0, 0.7),
                                    alpha=0.8, edgecolor='cyan'))
        
        try:
            ctx.add_basemap(ax2, source=ctx.providers.Esri.WorldImagery, alpha=0.3)
        except:
            pass
        
        ax2.set_title(f'🚀 RENDIMIENTO PROYECTADO\n(+{incrementos.mean():.1f} ton/ha)', 
                     fontsize=14, fontweight='bold', color='white', pad=15)
        ax2.set_xlabel('Longitud', color='white')
        ax2.set_ylabel('Latitud', color='white')
        ax2.tick_params(colors='white')
        ax2.grid(True, alpha=0.15, color='#475569')
        
        cbar2 = plt.colorbar(im2, ax=ax2, shrink=0.8, pad=0.03)
        cbar2.set_label('ton/ha', fontsize=10, color='white', weight='bold')
        cbar2.ax.yaxis.set_tick_params(color='white')
        cbar2.outline.set_edgecolor('white')
        plt.setp(cbar2.ax.get_yticklabels(), color='white')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                   facecolor='#0f172a', transparent=False)
        buf.seek(0)
        plt.close()
        return buf
        
    except Exception as e:
        st.error(f"Error creando mapa comparativo: {str(e)}")
        return None

# ===== FUNCIONES PARA MAPAS DE FERTILIDAD Y TEXTURA =====
def crear_mapa_fertilidad_integrada(gdf_analizado, cultivo, satelite, mostrar_capa_inta=False):
    try:
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, ax = plt.subplots(1, 1, figsize=(14, 9))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        valores = gdf_plot['npk_integrado']
        vmin, vmax = max(0.3, valores.min()*0.9), min(1.2, valores.max()*1.1)
        
        cmap = LinearSegmentedColormap.from_list('fertilidad_gee', PALETAS_GEE['FERTILIDAD'])
        
        for idx, row in gdf_plot.iterrows():
            valor_norm = (row['npk_integrado'] - vmin) / (vmax - vmin) if vmax > vmin else 0.5
            valor_norm = max(0, min(1, valor_norm))
            color = cmap(valor_norm)
            
            gdf_plot.iloc[[idx]].plot(ax=ax, color=color, edgecolor='white', 
                                    linewidth=2.0, alpha=0.85, zorder=3)
            
            centroid = row.geometry.centroid
            ax.annotate(f"Z{row['id_zona']}\n{row['npk_integrado']:.2f}", 
                       (centroid.x, centroid.y),
                       xytext=(5, 5), textcoords="offset points",
                       fontsize=9, color='white', weight='bold',
                       bbox=dict(boxstyle="round,pad=0.4", 
                               facecolor=(30/255, 41/255, 59/255, 0.92), 
                               edgecolor='white', linewidth=1.5))
        
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.4, zorder=1)
        except Exception as e:
            st.warning(f"No se pudo cargar mapa base Esri: {str(e)}")
        
        if mostrar_capa_inta:
            st.info("ℹ️ Capa INTA: Disponible como referencia en sistemas GIS (QGIS/ArcGIS)")
        
        satelite_info = SATELITES_DISPONIBLES.get(satelite, SATELITES_DISPONIBLES['DATOS_SIMULADOS'])
        ax.set_title(f'{ICONOS_CULTIVOS.get(cultivo, "🌱")} MAPA DE FERTILIDAD INTEGRADA NPK\n'
                    f'{cultivo} • {satelite_info.get("icono", "🛰️")} {satelite_info.get("nombre", "Datos")}',
                    fontsize=17, fontweight='bold', pad=22, color='white')
        
        ax.set_xlabel('Longitud', color='white', fontsize=12)
        ax.set_ylabel('Latitud', color='white', fontsize=12)
        ax.tick_params(colors='white', labelsize=10)
        ax.grid(True, alpha=0.25, color='#475569', linestyle='--', zorder=0)
        
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.85, pad=0.02)
        cbar.set_label('Índice NPK Integrado (0-1)', fontsize=13, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white', labelsize=11)
        cbar.outline.set_edgecolor('white')
        plt.setp(cbar.ax.get_yticklabels(), color='white')
        
        stats_text = f"""
📊 ESTADÍSTICAS:
• Promedio NPK: {valores.mean():.2f}
• Mínimo: {valores.min():.2f}
• Máximo: {valores.max():.2f}
• Zonas: {len(gdf_analizado)}
"""
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', color='white', fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.4",
                        facecolor=(30/255, 41/255, 59/255, 0.95),
                        edgecolor='white', linewidth=1.5))
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                   facecolor='#0f172a', edgecolor='none')
        buf.seek(0)
        plt.close()
        return buf
        
    except Exception as e:
        st.error(f"Error creando mapa de fertilidad: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def crear_mapa_npk_con_esri(gdf_analizado, nutriente, cultivo, satelite, mostrar_capa_inta=False):
    try:
        if gdf_analizado.empty or 'id_zona' not in gdf_analizado.columns:
            return None
        
        gdf_plot = gdf_analizado.copy()
        
        if gdf_plot.crs is None:
            gdf_plot = gdf_plot.set_crs('EPSG:4326')
        
        try:
            gdf_plot = gdf_plot.to_crs('EPSG:3857')
        except:
            pass
        
        fig, ax = plt.subplots(1, 1, figsize=(14, 9))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        mapeo_nutriente = {
            'NITRÓGENO': ('nitrogeno_actual', 'NITROGENO', 'NITRÓGENO (kg/ha)'),
            'FÓSFORO': ('fosforo_actual', 'FOSFORO', 'FÓSFORO (kg/ha)'),
            'POTASIO': ('potasio_actual', 'POTASIO', 'POTASIO (kg/ha)')
        }
        
        if nutriente not in mapeo_nutriente:
            st.warning(f"Nutriente no reconocido: {nutriente}")
            return None
        
        columna, clave_param, titulo_nutriente = mapeo_nutriente[nutriente]
        
        if columna not in gdf_analizado.columns:
            st.warning(f"Columna {columna} no encontrada en los datos")
            return None
        
        params = obtener_parametros_cultivo(cultivo)
        vmin, vmax = 0, 100
        
        try:
            if clave_param in params and isinstance(params[clave_param], dict):
                vmin = params[clave_param].get('min', 0) * 0.7
                vmax = params[clave_param].get('max', 100) * 1.2
            elif clave_param in params and isinstance(params[clave_param], (int, float)):
                vmin = params[clave_param] * 0.5
                vmax = params[clave_param] * 1.5
        except Exception as e:
            st.warning(f"Usando valores por defecto para {nutriente}: {e}")
        
        valores = gdf_analizado[columna].fillna(0).values
        vmin_actual = max(vmin, valores.min() * 0.8) if len(valores) > 0 else vmin
        vmax_actual = min(vmax, valores.max() * 1.2) if len(valores) > 0 else vmax
        
        if vmin_actual >= vmax_actual:
            vmin_actual = 0
            vmax_actual = max(100, valores.max() * 1.2) if len(valores) > 0 else 100
        
        colors = PALETAS_GEE.get(clave_param, ['#00ff00', '#ffff00', '#ff0000'])
        cmap = LinearSegmentedColormap.from_list('nutriente_gee', colors)
        
        for idx, row in gdf_plot.iterrows():
            try:
                valor = gdf_analizado.iloc[idx][columna] if columna in gdf_analizado.columns else 0
                valor_norm = max(0, min(1, (valor - vmin_actual) / (vmax_actual - vmin_actual))) if vmax_actual > vmin_actual else 0.5
                color = cmap(valor_norm)
                
                gdf_plot.iloc[[idx]].plot(ax=ax, color=color, edgecolor='white', linewidth=2.0, alpha=0.85, zorder=3)
                
                if hasattr(row.geometry, 'centroid'):
                    centroid = row.geometry.centroid
                else:
                    centroid = row.geometry.representative_point()
                
                ax.annotate(f"Z{row['id_zona']}\n{valor:.0f}", 
                           (centroid.x, centroid.y),
                           xytext=(5, 5), textcoords="offset points",
                           fontsize=9, color='white', weight='bold',
                           bbox=dict(boxstyle="round,pad=0.4", 
                                   facecolor=(30/255, 41/255, 59/255, 0.92), 
                                   edgecolor='white', linewidth=1.5))
            except Exception as e:
                st.warning(f"Error plotando zona {idx}: {str(e)}")
                continue
        
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.4, zorder=1)
        except Exception as e:
            st.warning(f"No se pudo cargar mapa base Esri: {str(e)}")
        
        if mostrar_capa_inta:
            st.info("ℹ️ Capa INTA: Disponible como referencia en sistemas GIS (QGIS/ArcGIS)")
        
        info_satelite = SATELITES_DISPONIBLES.get(satelite, SATELITES_DISPONIBLES['DATOS_SIMULADOS'])
        ax.set_title(f'{ICONOS_CULTIVOS.get(cultivo, "🌱")} ANÁLISIS DE {nutriente} - {cultivo}\n'
                    f'{info_satelite.get("icono", "🛰️")} {info_satelite.get("nombre", "Datos")} - {titulo_nutriente}',
                    fontsize=17, fontweight='bold', pad=22, color='white')
        
        ax.set_xlabel('Longitud', color='white', fontsize=12)
        ax.set_ylabel('Latitud', color='white', fontsize=12)
        ax.tick_params(colors='white', labelsize=10)
        ax.grid(True, alpha=0.25, color='#475569', linestyle='--', zorder=0)
        
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin_actual, vmax=vmax_actual))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, shrink=0.85, pad=0.02)
        cbar.set_label(titulo_nutriente, fontsize=13, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white', labelsize=11)
        cbar.outline.set_edgecolor('white')
        plt.setp(cbar.ax.get_yticklabels(), color='white')
        
        stats_text = f"""
📊 ESTADÍSTICAS {nutriente}:
• Promedio: {valores.mean():.1f} kg/ha
• Mínimo: {valores.min():.1f} kg/ha
• Máximo: {valores.max():.1f} kg/ha
• Óptimo: {params.get(clave_param, {}).get('optimo', 'N/A')} kg/ha
"""
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', color='white', fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.4",
                        facecolor=(30/255, 41/255, 59/255, 0.95),
                        edgecolor='white', linewidth=1.5))
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                   facecolor='#0f172a', edgecolor='none')
        buf.seek(0)
        plt.close()
        return buf
        
    except Exception as e:
        st.error(f"Error detallado creando mapa NPK: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def crear_mapa_texturas_con_esri(gdf_analizado, cultivo, mostrar_capa_inta=False):
    try:
        gdf_plot = gdf_analizado.to_crs(epsg=3857)
        fig, ax = plt.subplots(1, 1, figsize=(14, 9))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        texturas_unicas = gdf_plot['textura_usda'].unique()
        n_texturas = len(texturas_unicas)
        colors = PALETAS_GEE['TEXTURA'][:n_texturas] if n_texturas <= len(PALETAS_GEE['TEXTURA']) else plt.cm.tab20(np.linspace(0, 1, n_texturas))
        color_map = {textura: colors[i] for i, textura in enumerate(texturas_unicas)}
        
        for idx, row in gdf_plot.iterrows():
            textura = row['textura_usda']
            color = color_map.get(textura, '#808080')
            gdf_plot.iloc[[idx]].plot(ax=ax, color=color, edgecolor='white', 
                                    linewidth=2.0, alpha=0.85, zorder=3)
            
            centroid = row.geometry.centroid
            ax.annotate(f"Z{row['id_zona']}\n{textura[:15]}", 
                       (centroid.x, centroid.y),
                       xytext=(5, 5), textcoords="offset points",
                       fontsize=8, color='white', weight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", 
                               facecolor=(30/255, 41/255, 59/255, 0.9), 
                               edgecolor='white'))
        
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldImagery, alpha=0.4, zorder=1)
        except:
            pass
        
        if mostrar_capa_inta:
            st.info("ℹ️ Capa INTA: Disponible como referencia en sistemas GIS (QGIS/ArcGIS)")
        
        ax.set_title(f'{ICONOS_CULTIVOS.get(cultivo, "🌱")} MAPA DE TEXTURAS DEL SUELO (USDA)\n'
                    f'{cultivo} • Clasificación según sistema USDA',
                    fontsize=17, fontweight='bold', pad=22, color='white')
        
        ax.set_xlabel('Longitud', color='white', fontsize=12)
        ax.set_ylabel('Latitud', color='white', fontsize=12)
        ax.tick_params(colors='white', labelsize=10)
        ax.grid(True, alpha=0.25, color='#475569', linestyle='--', zorder=0)
        
        legend_elements = [mpatches.Patch(facecolor=color_map[t], edgecolor='white', label=t) 
                          for t in texturas_unicas if t != 'Sin datos']
        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper left', fontsize=9, 
                     facecolor=(30/255, 41/255, 59/255, 0.95), edgecolor='white',
                     labelcolor='white')
        
        stats_text = f"""
📊 ESTADÍSTICAS TEXTURALES:
• Texturas identificadas: {len([t for t in texturas_unicas if t != 'Sin datos'])}
• Textura predominante: {gdf_analizado['textura_usda'].mode()[0] if not gdf_analizado.empty else 'N/A'}
• Zonas analizadas: {len(gdf_analizado)}
"""
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', color='white', fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.4",
                        facecolor=(30/255, 41/255, 59/255, 0.95),
                        edgecolor='white', linewidth=1.5))
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                   facecolor='#0f172a', edgecolor='none')
        buf.seek(0)
        plt.close()
        return buf
        
    except Exception as e:
        st.error(f"Error creando mapa de texturas: {str(e)}")
        return None

# ===== FUNCIONES PARA CURVAS DE NIVEL =====
def generar_dem_sintetico(gdf, resolucion=10):
    try:
        gdf_4326 = validar_y_corregir_crs(gdf)
        bounds = gdf_4326.total_bounds
        minx, miny, maxx, maxy = bounds
        
        nx = int((maxx - minx) * 111000 / resolucion)
        ny = int((maxy - miny) * 111000 / resolucion)
        
        nx = max(50, min(300, nx))
        ny = max(50, min(300, ny))
        
        x = np.linspace(minx, maxx, nx)
        y = np.linspace(miny, maxy, ny)
        X, Y = np.meshgrid(x, y)
        
        centroid = gdf_4326.geometry.unary_union.centroid
        cx, cy = centroid.x, centroid.y
        
        Z_base = 500 + 200 * np.exp(-0.5 * ((X - cx)**2 + (Y - cy)**2) / 0.001)
        Z_ruido = np.random.uniform(-15, 15, Z_base.shape)
        Z = Z_base + Z_ruido
        
        mask = np.zeros_like(Z, dtype=bool)
        for i in range(Z.shape[0]):
            for j in range(Z.shape[1]):
                point = Point(X[i, j], Y[i, j])
                if not gdf_4326.geometry.contains(point).any():
                    mask[i, j] = True
        
        Z = np.ma.masked_array(Z, mask)
        
        return X, Y, Z, bounds
    except Exception as e:
        st.error(f"Error generando DEM sintético: {str(e)}")
        return None, None, None, None

def calcular_pendiente_simple(X, Y, Z, resolucion_m=10):
    try:
        if Z is None or isinstance(Z, np.ma.MaskedArray) and Z.mask.all():
            return None
        
        dx, dy = np.gradient(Z.filled(0) if isinstance(Z, np.ma.MaskedArray) else Z, 
                            (Y[1,0] - Y[0,0]) * 111000, 
                            (X[0,1] - X[0,0]) * 111000)
        pendiente = np.sqrt(dx**2 + dy**2)
        pendiente_grados = np.arctan(pendiente) * (180 / np.pi)
        
        if isinstance(Z, np.ma.MaskedArray):
            pendiente_grados = np.ma.masked_array(pendiente_grados, mask=Z.mask)
        
        return pendiente_grados
    except Exception as e:
        st.error(f"Error calculando pendiente: {str(e)}")
        return None

def generar_curvas_nivel_simple(X, Y, Z, intervalo=5, gdf=None):
    try:
        if Z is None:
            return [], []
        
        Z_plot = Z.filled(np.nan) if isinstance(Z, np.ma.MaskedArray) else Z
        min_z = np.nanmin(Z_plot)
        max_z = np.nanmax(Z_plot)
        
        niveles = np.arange(np.floor(min_z / intervalo) * intervalo, 
                           np.ceil(max_z / intervalo) * intervalo + intervalo, 
                           intervalo)
        
        curvas = []
        for nivel in niveles:
            cs = plt.contour(X, Y, Z_plot, levels=[nivel])
            for path in cs.collections[0].get_paths():
                if len(path.vertices) > 1:
                    coords = path.vertices
                    line = LineString(coords)
                    if gdf is not None:
                        line = line.intersection(gdf.geometry.unary_union)
                    if not line.is_empty and line.geom_type in ['LineString', 'MultiLineString']:
                        curvas.append((line, nivel))
        
        plt.close()
        return curvas, niveles
    except Exception as e:
        st.error(f"Error generando curvas de nivel: {str(e)}")
        return [], []

def crear_mapa_curvas_nivel(X, Y, Z, curvas, elevaciones, gdf, cultivo):
    try:
        fig, ax = plt.subplots(1, 1, figsize=(14, 9))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        Z_plot = Z.filled(np.nan) if isinstance(Z, np.ma.MaskedArray) else Z
        im = ax.contourf(X, Y, Z_plot, levels=30, cmap='terrain', alpha=0.75)
        
        for curva, elevacion in curvas:
            if curva.geom_type == 'LineString':
                x, y = curva.xy
                ax.plot(x, y, color='white', linewidth=1.2, alpha=0.85, zorder=3)
                if len(x) > 0:
                    mid_idx = len(x) // 2
                    ax.text(x[mid_idx], y[mid_idx], f'{elevacion:.0f}m', 
                           fontsize=8, color='white', weight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7),
                           zorder=4)
            elif curva.geom_type == 'MultiLineString':
                for line in curva.geoms:
                    x, y = line.xy
                    ax.plot(x, y, color='white', linewidth=1.2, alpha=0.85, zorder=3)
        
        gdf_4326 = validar_y_corregir_crs(gdf)
        gdf_3857 = gdf_4326.to_crs(epsg=3857)
        gdf_3857.boundary.plot(ax=ax, color='red', linewidth=2.5, zorder=5)
        
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldShadedRelief, alpha=0.5, zorder=1)
        except:
            pass
        
        ax.set_title(f'⛰️ MAPA DE CURVAS DE NIVEL Y ELEVACIÓN\n{cultivo} • Intervalo: {elevaciones[1]-elevaciones[0]:.0f}m',
                    fontsize=17, fontweight='bold', pad=22, color='white')
        ax.set_xlabel('Longitud', color='white', fontsize=12)
        ax.set_ylabel('Latitud', color='white', fontsize=12)
        ax.tick_params(colors='white', labelsize=10)
        ax.grid(True, alpha=0.2, color='#475569', linestyle='--')
        
        cbar = plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
        cbar.set_label('Elevación (m.s.n.m.)', fontsize=13, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white', labelsize=11)
        cbar.outline.set_edgecolor('white')
        plt.setp(cbar.ax.get_yticklabels(), color='white')
        
        stats_text = f"""
📊 ESTADÍSTICAS TOPOGRÁFICAS:
• Elevación mínima: {np.nanmin(Z_plot):.1f} m
• Elevación máxima: {np.nanmax(Z_plot):.1f} m
• Desnivel total: {np.nanmax(Z_plot) - np.nanmin(Z_plot):.1f} m
• Área: {calcular_superficie(gdf):.1f} ha
"""
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', color='white', fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.4",
                        facecolor=(30/255, 41/255, 59/255, 0.95),
                        edgecolor='white', linewidth=1.5))
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                   facecolor='#0f172a', edgecolor='none')
        buf.seek(0)
        plt.close()
        return buf
        
    except Exception as e:
        st.error(f"Error creando mapa de curvas: {str(e)}")
        return None

def crear_mapa_pendientes(X, Y, pendiente_grid, gdf, cultivo):
    try:
        if pendiente_grid is None:
            return None
        
        fig, ax = plt.subplots(1, 1, figsize=(14, 9))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        pend_plot = pendiente_grid.filled(np.nan) if isinstance(pendiente_grid, np.ma.MaskedArray) else pendiente_grid
        im = ax.contourf(X, Y, pend_plot, levels=25, cmap='RdYlGn_r', alpha=0.8)
        
        gdf_4326 = validar_y_corregir_crs(gdf)
        gdf_3857 = gdf_4326.to_crs(epsg=3857)
        gdf_3857.boundary.plot(ax=ax, color='black', linewidth=2.5, zorder=5)
        
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldShadedRelief, alpha=0.4, zorder=1)
        except:
            pass
        
        ax.set_title(f'📉 MAPA DE PENDIENTES Y RIESGO DE EROSIÓN\n{cultivo} • Clasificación según USDA',
                    fontsize=17, fontweight='bold', pad=22, color='white')
        ax.set_xlabel('Longitud', color='white', fontsize=12)
        ax.set_ylabel('Latitud', color='white', fontsize=12)
        ax.tick_params(colors='white', labelsize=10)
        ax.grid(True, alpha=0.2, color='#475569', linestyle='--')
        
        cbar = plt.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
        cbar.set_label('Pendiente (%)', fontsize=13, fontweight='bold', color='white')
        cbar.ax.yaxis.set_tick_params(color='white', labelsize=11)
        cbar.outline.set_edgecolor('white')
        plt.setp(cbar.ax.get_yticklabels(), color='white')
        
        # Leyenda de clasificación
        legend_y = 0.75
        for clase, datos in sorted(CLASIFICACION_PENDIENTES.items(), key=lambda x: x[1]['min']):
            ax.text(0.03, legend_y, f"■ {clase}", transform=ax.transAxes, fontsize=9,
                   color=datos['color'], weight='bold')
            legend_y -= 0.04
        
        stats_text = f"""
📊 ESTADÍSTICAS DE PENDIENTE:
• Pendiente promedio: {np.nanmean(pend_plot):.1f}%
• Pendiente máxima: {np.nanmax(pend_plot):.1f}%
• Área crítica (>15%): {np.sum(pend_plot > 15) / pend_plot.size * 100:.1f}%
• Riesgo erosión: {'ALTO' if np.nanmean(pend_plot) > 10 else 'MODERADO' if np.nanmean(pend_plot) > 5 else 'BAJO'}
"""
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', color='white', fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.4",
                        facecolor=(30/255, 41/255, 59/255, 0.95),
                        edgecolor='white', linewidth=1.5))
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                   facecolor='#0f172a', edgecolor='none')
        buf.seek(0)
        plt.close()
        return buf
        
    except Exception as e:
        st.error(f"Error creando mapa de pendientes: {str(e)}")
        return None

# ===== FUNCIONES DE VISUALIZACIÓN DE RESULTADOS =====
def mostrar_resultados_fertilidad(gdf_analizado, cultivo, area_total, satelite, mostrar_capa_inta=False):
    st.subheader(f"🌱 RESULTADOS DE FERTILIDAD INTEGRADA - {cultivo}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Área Total", f"{area_total:.1f} ha")
    with col2:
        st.metric("NPK Integrado", f"{gdf_analizado['npk_integrado'].mean():.2f}")
    with col3:
        st.metric("Nitrógeno Promedio", f"{gdf_analizado['nitrogeno_actual'].mean():.1f} kg/ha")
    with col4:
        st.metric("Fósforo Promedio", f"{gdf_analizado['fosforo_actual'].mean():.1f} kg/ha")
    
    st.markdown("### 🗺️ MAPA DE FERTILIDAD INTEGRADA NPK")
    mapa_buffer = crear_mapa_fertilidad_integrada(gdf_analizado, cultivo, satelite, mostrar_capa_inta)
    if mapa_buffer:
        st.image(mapa_buffer, use_container_width=True)
        
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            st.markdown("#### 📥 Descargar Mapa")
        with col_d2:
            st.download_button(
                "📥 PNG (Alta Resolución)",
                mapa_buffer,
                f"mapa_fertilidad_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                "image/png",
                key="descargar_mapa_fertilidad"
            )
    
    st.markdown("### 📊 VALORES POR ZONA DE MANEJO")
    columnas_mostrar = ['id_zona', 'area_ha', 'nitrogeno_actual', 'fosforo_actual', 'potasio_actual', 
                       'npk_integrado', 'ndvi', 'materia_organica']
    columnas_disponibles = [c for c in columnas_mostrar if c in gdf_analizado.columns]
    
    if 'area_ha' not in gdf_analizado.columns:
        gdf_analizado['area_ha'] = gdf_analizado.geometry.area * (111000**2) / 10000
    
    df_display = gdf_analizado[columnas_disponibles].copy()
    for col in df_display.select_dtypes(include=[np.number]).columns:
        df_display[col] = df_display[col].round(2)
    
    st.dataframe(df_display.style.background_gradient(cmap='RdYlGn', subset=['npk_integrado']),
                use_container_width=True)
    
    st.markdown("### 📈 ANÁLISIS ESTADÍSTICO")
    col_e1, col_e2, col_e3 = st.columns(3)
    
    with col_e1:
        st.markdown("**Nitrógeno (N)**")
        st.write(f"- Promedio: {gdf_analizado['nitrogeno_actual'].mean():.1f} kg/ha")
        st.write(f"- Rango: {gdf_analizado['nitrogeno_actual'].min():.1f} - {gdf_analizado['nitrogeno_actual'].max():.1f} kg/ha")
        st.write(f"- CV: {gdf_analizado['nitrogeno_actual'].std() / gdf_analizado['nitrogeno_actual'].mean() * 100:.1f}%")
    
    with col_e2:
        st.markdown("**Fósforo (P)**")
        st.write(f"- Promedio: {gdf_analizado['fosforo_actual'].mean():.1f} kg/ha")
        st.write(f"- Rango: {gdf_analizado['fosforo_actual'].min():.1f} - {gdf_analizado['fosforo_actual'].max():.1f} kg/ha")
        st.write(f"- CV: {gdf_analizado['fosforo_actual'].std() / gdf_analizado['fosforo_actual'].mean() * 100:.1f}%")
    
    with col_e3:
        st.markdown("**Potasio (K)**")
        st.write(f"- Promedio: {gdf_analizado['potasio_actual'].mean():.1f} kg/ha")
        st.write(f"- Rango: {gdf_analizado['potasio_actual'].min():.1f} - {gdf_analizado['potasio_actual'].max():.1f} kg/ha")
        st.write(f"- CV: {gdf_analizado['potasio_actual'].std() / gdf_analizado['potasio_actual'].mean() * 100:.1f}%")
    
    st.markdown("### 💡 INTERPRETACIÓN")
    npk_prom = gdf_analizado['npk_integrado'].mean()
    if npk_prom >= 0.9:
        st.success(f"✅ EXCELENTE FERTILIDAD: El suelo presenta niveles óptimos de nutrientes (NPK={npk_prom:.2f})")
    elif npk_prom >= 0.7:
        st.info(f"⚠️ BUENA FERTILIDAD: El suelo tiene buenos niveles pero requiere ajustes menores (NPK={npk_prom:.2f})")
    elif npk_prom >= 0.5:
        st.warning(f"⚠️ FERTILIDAD MODERADA: El suelo requiere fertilización balanceada (NPK={npk_prom:.2f})")
    else:
        st.error(f"❌ BAJA FERTILIDAD: El suelo presenta deficiencias nutricionales significativas (NPK={npk_prom:.2f})")

def mostrar_resultados_recomendaciones(gdf_analizado, cultivo, nutriente, area_total, satelite, mostrar_capa_inta=False):
    st.subheader(f"💡 RECOMENDACIONES DE FERTILIZACIÓN - {nutriente} ({cultivo})")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Área Total", f"{area_total:.1f} ha")
    with col2:
        st.metric(f"{nutriente} Actual", f"{gdf_analizado[f'{nutriente.lower().replace('ó','o')}_actual'].mean():.1f} kg/ha")
    with col3:
        st.metric(f"{nutriente} Óptimo", f"{obtener_parametros_cultivo(cultivo).get(nutriente, {}).get('optimo', 'N/A')} kg/ha")
    
    st.markdown(f"### 🗺️ MAPA DE RECOMENDACIONES DE {nutriente}")
    mapa_buffer = crear_mapa_npk_con_esri(gdf_analizado, nutriente, cultivo, satelite, mostrar_capa_inta)
    if mapa_buffer:
        st.image(mapa_buffer, use_container_width=True)
        
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            st.markdown("#### 📥 Descargar Mapa")
        with col_d2:
            st.download_button(
                "📥 PNG (Alta Resolución)",
                mapa_buffer,
                f"mapa_{nutriente.replace('Ó','O').replace(' ','_').lower()}_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                "image/png",
                key=f"descargar_mapa_{nutriente}"
            )
    
    st.markdown("### 📊 RECOMENDACIONES POR ZONA")
    columnas_base = ['id_zona', 'area_ha', f'{nutriente.lower().replace("ó","o")}_actual']
    if f'{nutriente.lower().replace("ó","o")}_recomendado' in gdf_analizado.columns:
        columnas_base.append(f'{nutriente.lower().replace("ó","o")}_recomendado')
    if f'{nutriente.lower().replace("ó","o")}_deficiencia' in gdf_analizado.columns:
        columnas_base.append(f'{nutriente.lower().replace("ó","o")}_deficiencia')
    
    columnas_disponibles = [c for c in columnas_base if c in gdf_analizado.columns]
    
    if 'area_ha' not in gdf_analizado.columns:
        gdf_analizado['area_ha'] = gdf_analizado.geometry.area * (111000**2) / 10000
    
    df_display = gdf_analizado[columnas_disponibles].copy()
    for col in df_display.select_dtypes(include=[np.number]).columns:
        df_display[col] = df_display[col].round(2)
    
    st.dataframe(df_display.style.background_gradient(
        cmap='RdYlGn_r' if f'{nutriente.lower().replace("ó","o")}_deficiencia' in df_display.columns else 'RdYlGn',
        subset=[c for c in df_display.columns if 'deficiencia' in c.lower() or 'recomendado' in c.lower()]
    ), use_container_width=True)
    
    st.markdown("### 💰 ESTIMACIÓN DE INSUMOS")
    params = obtener_parametros_cultivo(cultivo)
    nutriente_key = nutriente.replace('Ó', 'O').upper()
    
    if nutriente_key in ['NITROGENO', 'NITRÓGENO']:
        fuente = 'UREA'
        contenido = 0.46
        eficiencia = 0.6
        precio = PARAMETROS_ECONOMICOS['PRECIOS_FERTILIZANTES']['UREA']
    elif nutriente_key in ['FOSFORO', 'FÓSFORO']:
        fuente = 'FOSFATO DIAMÓNICO'
        contenido = 0.18
        eficiencia = 0.3
        precio = PARAMETROS_ECONOMICOS['PRECIOS_FERTILIZANTES']['FOSFATO_DIAMONICO']
    else:
        fuente = 'CLORURO DE POTASIO'
        contenido = 0.60
        eficiencia = 0.5
        precio = PARAMETROS_ECONOMICOS['PRECIOS_FERTILIZANTES']['CLORURO_POTASIO']
    
    deficiencia_prom = gdf_analizado[f'{nutriente.lower().replace("ó","o")}_deficiencia'].mean()
    kg_nutriente_ha = deficiencia_prom
    kg_fertilizante_ha = (kg_nutriente_ha / contenido) / eficiencia
    costo_ha = (kg_fertilizante_ha / 1000) * precio
    costo_total = costo_ha * area_total
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.metric("Deficiencia Promedio", f"{deficiencia_prom:.1f} kg/ha")
    with col_f2:
        st.metric(f"Fertilizante ({fuente})", f"{kg_fertilizante_ha:.1f} kg/ha")
    with col_f3:
        st.metric("Costo Estimado", f"USD ${costo_total:,.0f} total")
    
    st.markdown("### 💡 RECOMENDACIONES AGRONÓMICAS")
    if deficiencia_prom > 0:
        st.warning(f"⚠️ **DEFICIENCIA DETECTADA**: Se recomienda aplicación de {fuente} a razón de {kg_fertilizante_ha:.1f} kg/ha")
        st.info(f"📌 **Método de aplicación**: {METODOLOGIAS_NPK.get(satelite, {}).get(nutriente_key, {}).get('metodo', 'Aplicación convencional')}")
        st.info(f"🔬 **Fórmula**: {METODOLOGIAS_NPK.get(satelite, {}).get(nutriente_key, {}).get('formula', 'N/A')}")
    else:
        st.success(f"✅ **NIVELES ADECUADOS**: No se requiere aplicación adicional de {nutriente}")

def mostrar_resultados_textura(gdf_analizado, cultivo, area_total, mostrar_capa_inta=False):
    st.subheader(f"🏗️ ANÁLISIS DE TEXTURA DEL SUELO (USDA) - {cultivo}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Área Total", f"{area_total:.1f} ha")
    with col2:
        textura_pred = gdf_analizado['textura_usda'].mode()[0] if not gdf_analizado.empty else "N/A"
        st.metric("Textura Predominante", textura_pred)
    with col3:
        if 'arena' in gdf_analizado.columns:
            arena_prom = gdf_analizado['arena'].mean()
            limo_prom = gdf_analizado['limo'].mean()
            arcilla_prom = gdf_analizado['arcilla'].mean()
            st.metric("Arena/Limo/Arcilla", f"{arena_prom:.0f}%/{limo_prom:.0f}%/{arcilla_prom:.0f}%")
    
    st.markdown("### 🗺️ MAPA DE TEXTURAS USDA")
    mapa_buffer = crear_mapa_texturas_con_esri(gdf_analizado, cultivo, mostrar_capa_inta)
    if mapa_buffer:
        st.image(mapa_buffer, use_container_width=True)
        
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            st.markdown("#### 📥 Descargar Mapa")
        with col_d2:
            st.download_button(
                "📥 PNG (Alta Resolución)",
                mapa_buffer,
                f"mapa_texturas_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                "image/png",
                key="descargar_mapa_texturas"
            )
    
    st.markdown("### 📊 DISTRIBUCIÓN TEXTURAL")
    if not gdf_analizado.empty:
        texturas_count = gdf_analizado['textura_usda'].value_counts()
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#0f172a')
        
        colors = [PALETAS_GEE['TEXTURA'][i % len(PALETAS_GEE['TEXTURA'])] for i in range(len(texturas_count))]
        bars = ax.bar(texturas_count.index, texturas_count.values, color=colors, edgecolor='white', linewidth=1.5)
        
        ax.set_title('Distribución de Texturas por Zona', color='white', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Clase Textural (USDA)', color='white', fontsize=12)
        ax.set_ylabel('Número de Zonas', color='white', fontsize=12)
        ax.tick_params(colors='white')
        ax.grid(True, alpha=0.3, color='#475569', linestyle='--', axis='y')
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{int(height)}',
                   ha='center', va='bottom', color='white', fontweight='bold', fontsize=11)
        
        plt.xticks(rotation=15, ha='right')
        plt.tight_layout()
        st.pyplot(fig)
    
    st.markdown("### 💡 INTERPRETACIÓN Y MANEJO")
    textura_principal = gdf_analizado['textura_usda'].mode()[0] if not gdf_analizado.empty else "Sin datos"
    
    if textura_principal in RECOMENDACIONES_TEXTURA:
        rec = RECOMENDACIONES_TEXTURA[textura_principal]
        
        st.markdown(f"#### 🌱 **{textura_principal.upper()}**")
        
        col_t1, col_t2, col_t3 = st.columns(3)
        
        with col_t1:
            st.markdown("**✅ Propiedades Favorables**")
            for prop in rec['propiedades']:
                st.markdown(f"- {prop}")
        
        with col_t2:
            st.markdown("**⚠️ Limitantes**")
            for lim in rec['limitantes']:
                st.markdown(f"- {lim}")
        
        with col_t3:
            st.markdown("**🔧 Recomendaciones de Manejo**")
            for man in rec['manejo']:
                st.markdown(f"- {man}")
    else:
        st.info("ℹ️ Textura no identificada en base de datos USDA. Consulte con especialista.")

def mostrar_resultados_curvas_nivel(X, Y, Z, pendiente_grid, curvas, elevaciones, gdf, cultivo, area_total):
    st.subheader(f"⛰️ ANÁLISIS TOPOGRÁFICO - {cultivo}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Área Total", f"{area_total:.1f} ha")
    with col2:
        if Z is not None:
            Z_plot = Z.filled(np.nan) if isinstance(Z, np.ma.MaskedArray) else Z
            st.metric("Elev. Mínima", f"{np.nanmin(Z_plot):.0f} m")
    with col3:
        if Z is not None:
            st.metric("Elev. Máxima", f"{np.nanmax(Z_plot):.0f} m")
    with col4:
        if pendiente_grid is not None:
            pend_plot = pendiente_grid.filled(np.nan) if isinstance(pendiente_grid, np.ma.MaskedArray) else pendiente_grid
            st.metric("Pend. Promedio", f"{np.nanmean(pend_plot):.1f}%")
    
    tab1, tab2 = st.tabs(["🗺️ Curvas de Nivel", "📉 Pendientes y Erosión"])
    
    with tab1:
        st.markdown("### 🗺️ MAPA DE CURVAS DE NIVEL")
        mapa_curvas = crear_mapa_curvas_nivel(X, Y, Z, curvas, elevaciones, gdf, cultivo)
        if mapa_curvas:
            st.image(mapa_curvas, use_container_width=True)
            
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                st.markdown("#### 📥 Descargar Mapa")
            with col_d2:
                st.download_button(
                    "📥 PNG (Alta Resolución)",
                    mapa_curvas,
                    f"curvas_nivel_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                    "image/png",
                    key="descargar_curvas_nivel"
                )
    
    with tab2:
        st.markdown("### 📉 MAPA DE PENDIENTES Y RIESGO DE EROSIÓN")
        mapa_pendientes = crear_mapa_pendientes(X, Y, pendiente_grid, gdf, cultivo)
        if mapa_pendientes:
            st.image(mapa_pendientes, use_container_width=True)
            
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                st.markdown("#### 📥 Descargar Mapa")
            with col_d2:
                st.download_button(
                    "📥 PNG (Alta Resolución)",
                    mapa_pendientes,
                    f"pendientes_{cultivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.png",
                    "image/png",
                    key="descargar_pendientes"
                )
    
    st.markdown("### 💡 INTERPRETACIÓN TOPOGRÁFICA")
    if pendiente_grid is not None:
        pend_plot = pendiente_grid.filled(np.nan) if isinstance(pendiente_grid, np.ma.MaskedArray) else pendiente_grid
        pend_prom = np.nanmean(pend_plot)
        
        if pend_prom > 15:
            st.error(f"⚠️ **ALTO RIESGO DE EROSIÓN**: Pendiente promedio de {pend_prom:.1f}% requiere medidas conservacionistas urgentes")
            st.markdown("""
            - Implementar terrazas de contención
            - Siembra en contorno
            - Cobertura vegetal permanente
            - Evitar laboreo en épocas de lluvias intensas
            """)
        elif pend_prom > 8:
            st.warning(f"⚠️ **RIESGO MODERADO DE EROSIÓN**: Pendiente promedio de {pend_prom:.1f}% requiere manejo conservacionista")
            st.markdown("""
            - Rotación de cultivos con cobertura
            - Siembra en contorno
            - Franjas cortavientos
            - Manejo adecuado de residuos
            """)
        else:
            st.success(f"✅ **BAJO RIESGO DE EROSIÓN**: Pendiente promedio de {pend_prom:.1f}% favorable para el cultivo")
            st.markdown("""
            - Manejo convencional permitido
            - Optimizar drenaje superficial
            - Monitorear compactación
            """)

# ===== FUNCIÓN PRINCIPAL DE EJECUCIÓN =====
def ejecutar_analisis(gdf, nutriente, analisis_tipo, n_zonas, cultivo, satelite=None, 
                     indice=None, fecha_inicio=None, fecha_fin=None,
                     intervalo_curvas=5.0, resolucion_dem=10.0,
                     usar_inta=True, mostrar_capa_inta=False):
    try:
        gdf = validar_y_corregir_crs(gdf)
        area_total = calcular_superficie(gdf)
        
        if analisis_tipo in ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK"]:
            gdf_zonas = dividir_parcela_en_zonas(gdf, n_zonas)
            resultados_npk = calcular_indices_npk_avanzados(gdf_zonas, cultivo, satelite, usar_inta=usar_inta)
            
            for idx, row in gdf_zonas.iterrows():
                for key, value in resultados_npk[idx].items():
                    gdf_zonas.at[idx, key] = value
            
            if 'area_ha' not in gdf_zonas.columns:
                gdf_zonas['area_ha'] = gdf_zonas.geometry.area * (111000**2) / 10000
            
            if analisis_tipo == "RECOMENDACIONES NPK":
                params = obtener_parametros_cultivo(cultivo)
                nutriente_key = nutriente.replace('Ó', 'O').upper()
                
                if nutriente_key in ['NITROGENO', 'NITRÓGENO']:
                    opt = params['NITROGENO']['optimo']
                    col_actual = 'nitrogeno_actual'
                elif nutriente_key in ['FOSFORO', 'FÓSFORO']:
                    opt = params['FOSFORO']['optimo']
                    col_actual = 'fosforo_actual'
                else:
                    opt = params['POTASIO']['optimo']
                    col_actual = 'potasio_actual'
                
                gdf_zonas[f'{nutriente_key.lower()}_recomendado'] = opt
                gdf_zonas[f'{nutriente_key.lower()}_deficiencia'] = (opt - gdf_zonas[col_actual]).clip(lower=0)
            
            rend_actual = calcular_rendimiento_potencial(gdf_zonas, cultivo)
            gdf_zonas['rendimiento_actual'] = rend_actual
            
            if analisis_tipo == "RECOMENDACIONES NPK":
                rend_proyectado = calcular_rendimiento_con_recomendaciones(gdf_zonas, cultivo)
                gdf_zonas['rendimiento_proyectado'] = rend_proyectado
                gdf_zonas['incremento_rendimiento'] = gdf_zonas['rendimiento_proyectado'] - gdf_zonas['rendimiento_actual']
            
            return {
                'exitoso': True,
                'gdf_analizado': gdf_zonas,
                'area_total': area_total,
                'df_power': None  # En versión completa se integraría NASA POWER
            }
        
        elif analisis_tipo == "ANÁLISIS DE TEXTURA":
            gdf_zonas = dividir_parcela_en_zonas(gdf, n_zonas)
            
            for idx, row in gdf_zonas.iterrows():
                centroid = row.geometry.centroid
                seed_value = abs(hash(f"{centroid.x:.4f}_{centroid.y:.4f}_textura_{cultivo}")) % (2**32)
                rng = np.random.RandomState(seed_value)
                
                textura_optima = TEXTURA_SUELO_OPTIMA.get(cultivo, TEXTURA_SUELO_OPTIMA['VID'])
                arena_base = textura_optima['arena_optima']
                limo_base = textura_optima['limo_optima']
                arcilla_base = textura_optima['arcilla_optima']
                
                arena = max(5, min(90, arena_base + rng.normal(0, 8)))
                limo = max(5, min(90, limo_base + rng.normal(0, 6)))
                arcilla = 100 - arena - limo
                arcilla = max(5, min(90, arcilla))
                arena = arena * 100 / (arena + limo + arcilla)
                limo = limo * 100 / (arena + limo + arcilla)
                
                textura = clasificar_textura_usda(arena, limo, arcilla)
                
                gdf_zonas.at[idx, 'arena'] = round(arena, 1)
                gdf_zonas.at[idx, 'limo'] = round(limo, 1)
                gdf_zonas.at[idx, 'arcilla'] = round(arcilla, 1)
                gdf_zonas.at[idx, 'textura_usda'] = textura
                gdf_zonas.at[idx, 'densidad_aparente'] = round(textura_optima['densidad_aparente_optima'] + rng.normal(0, 0.1), 2)
                gdf_zonas.at[idx, 'porosidad'] = round(textura_optima['porosidad_optima'] + rng.normal(0, 0.05), 2)
            
            if 'area_ha' not in gdf_zonas.columns:
                gdf_zonas['area_ha'] = gdf_zonas.geometry.area * (111000**2) / 10000
            
            return {
                'exitoso': True,
                'gdf_analizado': gdf_zonas,
                'area_total': area_total
            }
        
        elif analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL":
            X, Y, Z, bounds = generar_dem_sintetico(gdf, resolucion_dem)
            if Z is None:
                return {'exitoso': False, 'error': 'Error generando DEM'}
            
            pendiente_grid = calcular_pendiente_simple(X, Y, Z, resolucion_dem)
            curvas, elevaciones = generar_curvas_nivel_simple(X, Y, Z, intervalo_curvas, gdf)
            
            return {
                'exitoso': True,
                'gdf_analizado': gdf,
                'area_total': area_total,
                'X': X,
                'Y': Y,
                'Z': Z,
                'pendiente_grid': pendiente_grid,
                'curvas': curvas,
                'elevaciones': elevaciones,
                'bounds': bounds
            }
        
        else:
            return {'exitoso': False, 'error': f'Análisis no reconocido: {analisis_tipo}'}
    
    except Exception as e:
        st.error(f"Error ejecutando análisis: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return {'exitoso': False, 'error': str(e)}

# ===== INTERFAZ DE USUARIO PRINCIPAL =====
def main():
    # Sidebar - Configuración
    with st.sidebar:
        st.markdown('<div class="sidebar-title">🍇 CONFIGURACIÓN DE ANÁLISIS</div>', unsafe_allow_html=True)
        
        st.subheader("1. Cargar Parcela")
        uploaded_file = st.file_uploader("Subir Shapefile (.zip) o KML/KMZ", 
                                       type=['zip', 'kml', 'kmz'],
                                       key="uploader_parcela")
        
        st.subheader("2. Parámetros del Cultivo")
        cultivo = st.selectbox("Cultivo", CULTIVOS, key="select_cultivo")
        
        if cultivo in ["VID", "OLIVO"]:
            variedades = list(VARIEDADES_VID.keys()) if cultivo == "VID" else list(VARIEDADES_OLIVO.keys())
            variedad = st.selectbox("Variedad", variedades, key="select_variedad")
            if cultivo == "VID":
                st.session_state['variedad_params'] = VARIEDADES_VID[variedad]
            else:
                st.session_state['variedad_params'] = VARIEDADES_OLIVO[variedad]
            st.session_state['variedad'] = variedad
        
        st.subheader("3. Tipo de Análisis")
        analisis_tipo = st.selectbox(
            "Seleccione análisis",
            ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK", "ANÁLISIS DE TEXTURA", "ANÁLISIS DE CURVAS DE NIVEL"],
            key="select_analisis"
        )
        
        if analisis_tipo == "RECOMENDACIONES NPK":
            nutriente = st.selectbox(
                "Nutriente a analizar",
                ["NITRÓGENO", "FÓSFORO", "POTASIO"],
                key="select_nutriente"
            )
            st.session_state['nutriente_seleccionado'] = nutriente
        else:
            st.session_state['nutriente_seleccionado'] = None
        
        st.subheader("4. Configuración Avanzada")
        n_divisiones = st.slider("Número de zonas de manejo", 2, 20, 5, key="slider_zonas")
        
        if analisis_tipo in ["FERTILIDAD ACTUAL", "RECOMENDACIONES NPK"]:
            satelite_seleccionado = st.selectbox(
                "Fuente satelital",
                list(SATELITES_DISPONIBLES.keys()),
                format_func=lambda x: f"{SATELITES_DISPONIBLES[x]['icono']} {SATELITES_DISPONIBLES[x]['nombre']} ({SATELITES_DISPONIBLES[x]['resolucion']})",
                key="select_satelite"
            )
            st.session_state['satelite_seleccionado'] = satelite_seleccionado
            
            indice_seleccionado = st.selectbox(
                "Índice de vegetación",
                SATELITES_DISPONIBLES[satelite_seleccionado]['indices'],
                key="select_indice"
            )
            st.session_state['indice_seleccionado'] = indice_seleccionado
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                fecha_inicio = st.date_input("Fecha inicio", 
                                           value=datetime.now() - timedelta(days=30),
                                           key="date_inicio")
            with col_f2:
                fecha_fin = st.date_input("Fecha fin", 
                                         value=datetime.now(),
                                         key="date_fin")
            
            st.session_state['fecha_inicio'] = fecha_inicio
            st.session_state['fecha_fin'] = fecha_fin
        
        elif analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL":
            intervalo_curvas = st.slider("Intervalo entre curvas (m)", 1.0, 20.0, 5.0, 0.5, key="slider_intervalo")
            resolucion_dem = st.slider("Resolución DEM (m)", 5.0, 30.0, 10.0, 1.0, key="slider_resolucion")
            st.session_state['intervalo_curvas'] = intervalo_curvas
            st.session_state['resolucion_dem'] = resolucion_dem
        
        st.subheader("5. Integración INTA")
        usar_inta = st.checkbox("Usar datos del INTA para materia orgánica", 
                               value=True, key="check_inta")
        mostrar_mapa_inta = st.checkbox("Mostrar capa de referencia INTA en mapas", 
                                       value=False, key="check_mapa_inta")
        st.session_state['usar_inta'] = usar_inta
        st.session_state['mostrar_mapa_inta'] = mostrar_mapa_inta
        
        st.markdown("---")
        if st.button("🚀 EJECUTAR ANÁLISIS", type="primary", use_container_width=True, key="btn_ejecutar"):
            st.session_state['ejecutar_analisis'] = True
        else:
            st.session_state['ejecutar_analisis'] = False
    
    # Contenido principal
    st.markdown("## 🌾 ANALIZADOR AGRÍCOLA SATELITAL - MENDOZA")
    
    if uploaded_file:
        gdf = cargar_archivo_parcela(uploaded_file)
        if gdf is not None:
            area_total = calcular_superficie(gdf)
            
            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                st.metric("📊 Polígonos", len(gdf))
            with col_res2:
                st.metric("📍 Área Total", f"{area_total:.1f} ha")
            with col_res3:
                st.metric("🗺️ CRS", str(gdf.crs).upper() if gdf.crs else "No definido")
            
            if st.session_state.get('ejecutar_analisis', False):
                with st.spinner("Ejecutando análisis..."):
                    resultados = ejecutar_analisis(
                        gdf, 
                        st.session_state.get('nutriente_seleccionado'),
                        analisis_tipo,
                        n_divisiones,
                        cultivo,
                        st.session_state.get('satelite_seleccionado'),
                        st.session_state.get('indice_seleccionado'),
                        st.session_state.get('fecha_inicio'),
                        st.session_state.get('fecha_fin'),
                        st.session_state.get('intervalo_curvas', 5.0),
                        st.session_state.get('resolucion_dem', 10.0),
                        usar_inta=st.session_state.get('usar_inta', True),
                        mostrar_capa_inta=st.session_state.get('mostrar_mapa_inta', False)
                    )
                    
                    if resultados['exitoso']:
                        st.session_state['resultados_guardados'] = {
                            'gdf_analizado': resultados['gdf_analizado'],
                            'analisis_tipo': analisis_tipo,
                            'cultivo': cultivo,
                            'area_total': resultados['area_total'],
                            'nutriente': st.session_state.get('nutriente_seleccionado'),
                            'satelite_seleccionado': st.session_state.get('satelite_seleccionado'),
                            'indice_seleccionado': st.session_state.get('indice_seleccionado'),
                            'X': resultados.get('X'),
                            'Y': resultados.get('Y'),
                            'Z': resultados.get('Z'),
                            'pendiente_grid': resultados.get('pendiente_grid'),
                            'curvas': resultados.get('curvas'),
                            'elevaciones': resultados.get('elevaciones'),
                            'usar_inta': st.session_state.get('usar_inta', True),
                            'mostrar_mapa_inta': st.session_state.get('mostrar_mapa_inta', False)
                        }
                        
                        st.success("✅ Análisis completado exitosamente")
                        
                        if analisis_tipo == "FERTILIDAD ACTUAL":
                            mostrar_resultados_fertilidad(
                                resultados['gdf_analizado'],
                                cultivo,
                                resultados['area_total'],
                                st.session_state.get('satelite_seleccionado'),
                                st.session_state.get('mostrar_mapa_inta', False)
                            )
                        elif analisis_tipo == "RECOMENDACIONES NPK":
                            mostrar_resultados_recomendaciones(
                                resultados['gdf_analizado'],
                                cultivo,
                                st.session_state.get('nutriente_seleccionado'),
                                resultados['area_total'],
                                st.session_state.get('satelite_seleccionado'),
                                st.session_state.get('mostrar_mapa_inta', False)
                            )
                            
                            # Análisis económico solo para recomendaciones NPK
                            if 'rendimiento_actual' in resultados['gdf_analizado'].columns:
                                st.markdown("---")
                                st.subheader("💰 ANÁLISIS ECONÓMICO DE FERTILIZACIÓN")
                                
                                variedad_params = st.session_state.get('variedad_params')
                                resultados_economicos = realizar_analisis_economico(
                                    resultados['gdf_analizado'],
                                    cultivo,
                                    variedad_params,
                                    resultados['area_total']
                                )
                                mostrar_analisis_economico(resultados_economicos)
                                
                                st.markdown("---")
                                st.subheader("🔥 MAPAS DE CALOR DE RENDIMIENTO")
                                
                                col_m1, col_m2, col_m3 = st.columns(3)
                                with col_m1:
                                    mapa_actual = crear_mapa_calor_rendimiento_actual(resultados['gdf_analizado'], cultivo)
                                    if mapa_actual:
                                        st.image(mapa_actual, use_container_width=True, caption="Rendimiento Actual")
                                with col_m2:
                                    mapa_proy = crear_mapa_calor_rendimiento_proyectado(resultados['gdf_analizado'], cultivo)
                                    if mapa_proy:
                                        st.image(mapa_proy, use_container_width=True, caption="Rendimiento Proyectado")
                                with col_m3:
                                    mapa_comp = crear_mapa_comparativo_calor(resultados['gdf_analizado'], cultivo)
                                    if mapa_comp:
                                        st.image(mapa_comp, use_container_width=True, caption="Comparativo")
                        
                        elif analisis_tipo == "ANÁLISIS DE TEXTURA":
                            mostrar_resultados_textura(
                                resultados['gdf_analizado'],
                                cultivo,
                                resultados['area_total'],
                                st.session_state.get('mostrar_mapa_inta', False)
                            )
                        
                        elif analisis_tipo == "ANÁLISIS DE CURVAS DE NIVEL":
                            mostrar_resultados_curvas_nivel(
                                resultados.get('X'),
                                resultados.get('Y'),
                                resultados.get('Z'),
                                resultados.get('pendiente_grid'),
                                resultados.get('curvas', []),
                                resultados.get('elevaciones', []),
                                gdf,
                                cultivo,
                                resultados['area_total']
                            )
                    else:
                        st.error(f"❌ Error en el análisis: {resultados.get('error', 'Error desconocido')}")
            else:
                st.info("👆 Configure los parámetros en el panel izquierdo y haga clic en 'EJECUTAR ANÁLISIS'")
        else:
            st.error("❌ No se pudo cargar la parcela. Verifique el formato del archivo.")
    else:
        st.info("👈 Suba un archivo de parcela en el panel izquierdo para comenzar el análisis")
        
        st.markdown("---")
        st.subheader("ℹ️ FORMATOS DE ARCHIVO ACEPTADOS")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown("""
            **Shapefile (.zip)**
            - Debe contener todos los archivos: .shp, .shx, .dbf, .prj
            - Sistema de coordenadas recomendado: WGS84 (EPSG:4326)
            - Polígonos simples o multipolígonos
            """)
        with col_f2:
            st.markdown("""
            **KML/KMZ**
            - Archivos de Google Earth (.kml)
            - Archivos comprimidos de Google Earth (.kmz)
            - Compatible con trazados de parcelas
            """)
    
    # ===== SECCIÓN DE EXPORTACIÓN GEOJSON (CORREGIDA Y FUNCIONAL) =====
    if 'resultados_guardados' in st.session_state:
        st.markdown("---")
        st.subheader("📤 EXPORTAR RESULTADOS EN FORMATO GEOJSON (EPSG:4326)")
        
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            st.markdown("### 🌍 Fertilidad Actual")
            if st.button("🌍 Exportar Fertilidad a GeoJSON", key="geo_fert_btn", use_container_width=True):
                with st.spinner("Generando GeoJSON de Fertilidad..."):
                    gdf_fert = st.session_state['resultados_guardados']['gdf_analizado']
                    geojson_data, nombre_archivo = exportar_a_geojson_completo(
                        gdf_fert,
                        st.session_state['resultados_guardados']['cultivo'],
                        "FERTILIDAD_ACTUAL",
                        metadata={
                            'satelite': st.session_state['resultados_guardados'].get('satelite_seleccionado', 'N/A'),
                            'area_total_ha': st.session_state['resultados_guardados']['area_total']
                        }
                    )
                    if geojson_data:
                        st.download_button(
                            label="📥 Descargar GeoJSON Fertilidad",
                            data=geojson_data.encode('utf-8'),
                            file_name=nombre_archivo,
                            mime="application/geo+json",
                            key="download_geojson_fert_btn"
                        )
                        st.success(f"✅ Archivo listo: {nombre_archivo}")
                        st.info("ℹ️ Formato: EPSG:4326 (WGS84) - Compatible con QGIS, ArcGIS, Google Earth Pro")
        
        with col_exp2:
            st.markdown("### 💡 Recomendaciones NPK")
            if st.session_state['resultados_guardados']['analisis_tipo'] == "RECOMENDACIONES NPK":
                nutriente_exp = st.session_state['resultados_guardados'].get('nutriente', 'NPK')
                if st.button(f"🌍 Exportar {nutriente_exp} a GeoJSON", key="geo_npk_btn", use_container_width=True):
                    with st.spinner(f"Generando GeoJSON de {nutriente_exp}..."):
                        gdf_npk = st.session_state['resultados_guardados']['gdf_analizado']
                        geojson_data, nombre_archivo = exportar_a_geojson_completo(
                            gdf_npk,
                            st.session_state['resultados_guardados']['cultivo'],
                            f"RECOMENDACIONES_{nutriente_exp.upper().replace('Ó','O')}",
                            metadata={
                                'nutriente': nutriente_exp,
                                'satelite': st.session_state['resultados_guardados'].get('satelite_seleccionado', 'N/A'),
                                'area_total_ha': st.session_state['resultados_guardados']['area_total']
                            }
                        )
                        if geojson_
                            st.download_button(
                                label=f"📥 Descargar GeoJSON {nutriente_exp}",
                                data=geojson_data.encode('utf-8'),
                                file_name=nombre_archivo,
                                mime="application/geo+json",
                                key="download_geojson_npk_btn"
                            )
                            st.success(f"✅ Archivo listo: {nombre_archivo}")
                            st.info("ℹ️ Formato: EPSG:4326 (WGS84) - Incluye recomendaciones por zona")
            else:
                st.info("⚠️ Ejecute análisis de 'RECOMENDACIONES NPK' para exportar")
        
        with col_exp3:
            st.markdown("### 🏗️ Textura USDA")
            if st.session_state['resultados_guardados']['analisis_tipo'] == "ANÁLISIS DE TEXTURA":
                if st.button("🌍 Exportar Textura a GeoJSON", key="geo_textura_btn", use_container_width=True):
                    with st.spinner("Generando GeoJSON de Textura..."):
                        gdf_textura = st.session_state['resultados_guardados']['gdf_analizado']
                        geojson_data, nombre_archivo = exportar_a_geojson_completo(
                            gdf_textura,
                            st.session_state['resultados_guardados']['cultivo'],
                            "TEXTURA_USDA",
                            metadata={
                                'clasificacion': 'USDA',
                                'area_total_ha': st.session_state['resultados_guardados']['area_total']
                            }
                        )
                        if geojson_
                            st.download_button(
                                label="📥 Descargar GeoJSON Textura",
                                data=geojson_data.encode('utf-8'),
                                file_name=nombre_archivo,
                                mime="application/geo+json",
                                key="download_geojson_textura_btn"
                            )
                            st.success(f"✅ Archivo listo: {nombre_archivo}")
                            st.info("ℹ️ Formato: EPSG:4326 (WGS84) - Clasificación textural USDA completa")
            else:
                st.info("⚠️ Ejecute análisis de 'ANÁLISIS DE TEXTURA' para exportar")
        
        st.markdown("---")
        st.subheader("📦 PAQUETE COMPLETO (GeoJSON + CSV + Mapas PNG)")
        
        if st.button("🎁 Generar Paquete Completo ZIP", type="primary", use_container_width=True, key="btn_zip_completo"):
            with st.spinner("Creando paquete ZIP con todos los resultados..."):
                resultados_completos = st.session_state['resultados_guardados'].copy()
                
                # Agregar mapas según tipo de análisis
                if resultados_completos['analisis_tipo'] == "FERTILIDAD ACTUAL":
                    resultados_completos['mapa_fertilidad'] = crear_mapa_fertilidad_integrada(
                        resultados_completos['gdf_analizado'],
                        resultados_completos['cultivo'],
                        resultados_completos.get('satelite_seleccionado', 'DATOS_SIMULADOS'),
                        resultados_completos.get('mostrar_mapa_inta', False)
                    )
                elif resultados_completos['analisis_tipo'] == "RECOMENDACIONES NPK":
                    resultados_completos['mapa_recomendaciones'] = crear_mapa_npk_con_esri(
                        resultados_completos['gdf_analizado'],
                        resultados_completos.get('nutriente', 'NITRÓGENO'),
                        resultados_completos['cultivo'],
                        resultados_completos.get('satelite_seleccionado', 'DATOS_SIMULADOS'),
                        resultados_completos.get('mostrar_mapa_inta', False)
                    )
                elif resultados_completos['analisis_tipo'] == "ANÁLISIS DE TEXTURA":
                    resultados_completos['mapa_texturas'] = crear_mapa_texturas_con_esri(
                        resultados_completos['gdf_analizado'],
                        resultados_completos['cultivo'],
                        resultados_completos.get('mostrar_mapa_inta', False)
                    )
                elif resultados_completos['analisis_tipo'] == "ANÁLISIS DE CURVAS DE NIVEL":
                    if resultados_completos.get('X') is not None:
                        resultados_completos['mapa_curvas'] = crear_mapa_curvas_nivel(
                            resultados_completos['X'],
                            resultados_completos['Y'],
                            resultados_completos['Z'],
                            resultados_completos.get('curvas', []),
                            resultados_completos.get('elevaciones', []),
                            gdf,
                            resultados_completos['cultivo']
                        )
                        resultados_completos['mapa_pendientes'] = crear_mapa_pendientes(
                            resultados_completos['X'],
                            resultados_completos['Y'],
                            resultados_completos['pendiente_grid'],
                            gdf,
                            resultados_completos['cultivo']
                        )
                
                # Generar paquete ZIP
                zip_buffer, nombre_zip = crear_paquete_completo(resultados_completos)
                
                if zip_buffer:
                    st.download_button(
                        label="📥 Descargar Paquete Completo ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=nombre_zip,
                        mime="application/zip",
                        key="download_zip_btn"
                    )
                    st.success(f"✅ Paquete generado: {nombre_zip}")
                    st.info("""
                    ℹ️ El paquete incluye:
                    - Archivo GeoJSON con datos espaciales (EPSG:4326 garantizado)
                    - CSV con datos tabulares por zona de manejo
                    - Mapas PNG de alta resolución (fertilidad/recomendaciones/textura/curvas)
                    - Archivo README con metodología y metadatos
                    - Sistema 100% compatible con QGIS, ArcGIS y Google Earth Pro
                    """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #cbd5e1; padding: 20px;'>
        <h3 style='color: #3b82f6; margin-bottom: 10px;'>🔬 Analizador Multi-Cultivo Satellital v2.0</h3>
        <p>Desarrollado por Martin Ernesto Cano • Enero 2026</p>
        <p>Integra datos de NASA POWER, Google Earth Engine, INTA y metodologías científicas para vid, olivo y hortalizas</p>
        <p style='background: rgba(59, 130, 246, 0.2); padding: 10px; border-radius: 10px; margin-top: 15px;'>
            ✅ TODAS LAS EXPORTACIONES GEOJSON GARANTIZAN CRS EPSG:4326 (WGS84) • ❌ SIN EXPORTACIONES PDF
        </p>
        <p style='font-style: italic; margin-top: 10px;'>
            ⚠️ Este es un sistema de apoyo a decisiones. Los resultados deben validarse con análisis de laboratorio.
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
