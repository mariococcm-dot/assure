import streamlit as st
import pandas as pd
import plotly.express as px
import requests # Necesitas añadir esta importación al inicio de tu app.py
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# --- 2. CONEXIÓN EXCLUSIVA A TU GOOGLE SHEET ---
def get_data():
    try:
        url = st.secrets["url_base"] # Usa tu URL real de st.secrets
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame()

# --- 3. LÓGICA DE SESIÓN (ARCHIVO 22052026.txt) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 Login")
    u_log = st.text_input("Usuario")
    p_log = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        df_db = get_data()
        if not df_db.empty:
            # Validación real contra tu tabla [cite: 5]
            user_row = df_db[(df_db['username'].astype(str) == u_log) & (df_db['password'].astype(str) == p_log)]
            if not user_row.empty:
                user = user_row.iloc[0]
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {"user": user['username'], "rol": user['rol'], "campaña": user['campaña']}
                st.rerun()
    st.stop()

# --- 4. MENÚ Y NAVEGACIÓN (ORIGINAL) ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Usuario: **{user_data['user']}**")

# Roles y Menú según tu archivo original [cite: 6]
if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Config Scorecards", "Gestión Campañas", "Gestión Usuarios"]
elif user_data['rol'] == 'Evaluador':
    menu = ["Dashboard", "Evaluador"]
else:
    menu = ["Mis Calificaciones"]

choice = st.sidebar.selectbox("Menú", menu)

# --- BLOQUE: GESTIÓN USUARIOS ---
elif choice == "Gestión Usuarios":
    # ... (interfaz de nuevo usuario) [cite: 78]
    if st.button("🚀 Registrar"):
        # Enviamos a la hoja 'usuarios' que sí existe
        payload = {
            "target_sheet": "usuarios",
            "username": nu,
            "password": np,
            "rol": nr,
            "campaña": nc_u
        }
        res = requests.post(URL_SCRIPT, json=payload)
        if res.text == "Éxito":
            st.success("Usuario registrado")
            st.rerun()
            
# URL de tu nueva implementación de Apps Script
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwk5v7mPhLnfRuNCs5K6HCnXbggpbBVlrFktOb4F5vWwAL5Na5j2_3JFGh0Dde7Tk4q/exec"

# --- BLOQUE: GESTIÓN CAMPAÑAS ---
if choice == "Gestión Campañas":
    # ... (resto del código de interfaz)
    if st.button("🚀 Guardar Nueva"):
        if nc:
            # Enviamos el nombre de la hoja 'campañas' (créala en tu Excel)
            payload = {"target_sheet": "campañas", "nombre": nc}
            res = requests.post(URL_SCRIPT, json=payload)
            if res.text == "Éxito":
                st.success("Campaña guardada")
                st.rerun()
            else:
                st.error(f"Error: {res.text}")     
                
# --- MÓDULO: EVALUADOR (SOLO CAMPAÑAS EXISTENTES) ---
elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_eval = get_data()
    # CORRECCIÓN: Tomar campañas solo del Excel [cite: 17]
    camps_reales = df_eval['campaña'].unique().tolist() if not df_eval.empty else []
    
    if not camps_reales:
        st.warning("No hay campañas registradas en el Excel.")
    else:
        # Aquí ya no aparecerá "Ventas" o "Soporte" a menos que estén en tu archivo
        a_sel = st.selectbox("Seleccionar Campaña Real", camps_reales)
        st.text_input("Nombre del Agente")
        st.button("Guardar Evaluación")

# --- MÓDULO: DASHBOARD ---
elif choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_dash = get_data()
    if not df_dash.empty:
        # Filtro dinámico basado en los datos [cite: 9]
        camps_dash = ["Ver Todas"] + df_dash['campaña'].unique().tolist()
        sel_camp = st.selectbox("Filtrar por Campaña:", camps_dash)
        st.info(f"Mostrando datos reales para: {sel_camp}")

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()
