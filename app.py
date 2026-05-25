import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# URL DE CONEXIÓN (Ajusta esta URL con tu implementación de Apps Script)
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec"

# --- 2. CONEXIÓN A GOOGLE SHEET ---
def get_data():
    try:
        # Se usa la clave 'url_base' definida en tus Secrets [cite: 108]
        url = st.secrets["url_base"]
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame()

# --- 3. LÓGICA DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 Login")
    u_log = st.text_input("Usuario")
    p_log = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        df_db = get_data()
        if not df_db.empty:
            user_row = df_db[(df_db['username'].astype(str) == u_log) & (df_db['password'].astype(str) == p_log)]
            if not user_row.empty:
                user = user_row.iloc[0]
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {"user": user['username'], "rol": user['rol'], "campaña": user['campaña']}
                st.rerun()
    st.stop()

# --- 4. MENÚ ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Usuario: **{user_data['user']}**")

if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios"]
elif user_data['rol'] == 'Evaluador':
    menu = ["Dashboard", "Evaluador"]
else:
    menu = ["Mis Calificaciones"]

choice = st.sidebar.selectbox("Menú", menu)

# --- MÓDULOS DE NAVEGACIÓN (Sintaxis Corregida) ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_dash = get_data()
    if not df_dash.empty:
        camps_dash = ["Ver Todas"] + df_dash['campaña'].unique().tolist()
        sel_camp = st.selectbox("Filtrar por Campaña:", camps_dash)
        st.info(f"Mostrando datos reales para: {sel_camp}")

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_base = get_data()
    camps_reales = df_base['campaña'].unique().tolist() if not df_base.empty else []
    
    if not camps_reales:
        st.warning("No hay campañas configuradas.")
    else:
        with st.form("form_eval"):
            c1, c2 = st.columns(2)
            a_sel = c1.selectbox("Campaña", camps_reales)
            ags = df_base[(df_base['rol'] == 'Agente') & (df_base['campaña'] == a_sel)]['username'].tolist()
            ag_sel = c2.selectbox("Agente", ags) if ags else c2.text_input("Nombre Agente (Manual)")
            
            f_ev = st.date_input("Fecha de Evento", datetime.now())
            t_eval = st.selectbox("Evaluado por:", ["Calidad", "Operaciones"])
            score_val = st.slider("Calidad de Proceso (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar Evaluación"):
                payload = {
                    "target_sheet": "evaluaciones", # Asegúrate que la pestaña exista
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fecha_evento": str(f_ev),
                    "area": a_sel,
                    "evaluador": user_data['user'],
                    "agente": ag_sel,
                    "pregunta": "Evaluación General",
                    "puntos_obtenidos": score_val,
                    "puntos_maximos": 100,
                    "observaciones": obs,
                    "tipo_evaluador": t_eval
                }
                res = requests.post(URL_SCRIPT, json=payload)
                if res.text == "Éxito":
                    st.success("✅ Evaluación guardada")
                    st.balloons()
                else:
                    st.error(f"Error: {res.text}")

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    nc = st.text_input("Nombre de la Nueva Campaña")
    if st.button("🚀 Guardar Nueva"):
        if nc:
            payload = {"target_sheet": "campañas", "nombre": nc} # Requiere pestaña 'campañas' [cite: 117]
            res = requests.post(URL_SCRIPT, json=payload)
            if res.text == "Éxito":
                st.success("Campaña guardada")
                st.rerun()

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data()
    with st.form("nuevo_usuario"):
        nu = st.text_input("Username")
        np = st.text_input("Password", type="password")
        nr = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
        nc_u = st.selectbox("Campaña", df_u['campaña'].unique().tolist() if not df_u.empty else ["Todas"])
        if st.form_submit_button("Registrar Usuario"):
            payload = {"target_sheet": "usuarios", "username": nu, "password": np, "rol": nr, "campaña": nc_u}
            res = requests.post(URL_SCRIPT, json=payload)
            if res.text == "Éxito":
                st.success("Usuario registrado")
                st.rerun()

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()
