import streamlit as st
import pandas as pd
import plotly.express as px
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

# --- MÓDULO: GESTIÓN USUARIOS (LEER DE TU EXCEL) ---
if choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data() # Obtener usuarios reales
    
    col1, col2 = st.columns([1, 2])
    with col1:
        modo = st.radio("Operación:", ["Nuevo", "Editar"])
        if modo == "Nuevo":
            st.text_input("Username")
            # Lista de campañas dinámica desde el Excel, no manual [cite: 34]
            camps_avail = df_u['campaña'].unique().tolist() if not df_u.empty else []
            st.selectbox("Campaña", ["Todas"] + camps_avail)
            st.button("🚀 Registrar")
    with col2:
        st.dataframe(df_u[['username', 'rol', 'campaña', 'estado']] if not df_u.empty else pd.DataFrame())

# --- MÓDULO: GESTIÓN CAMPAÑAS (LEER DE TU EXCEL) ---
elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data()
    # Extraer nombres de campañas reales que existan en la columna 'area' o 'campaña' [cite: 26]
    campañas_reales = df_c['campaña'].unique().tolist() if 'campaña' in df_c.columns else []
    
    st.subheader("Campañas Activas en el Sistema")
    st.write(campañas_reales) # Solo muestra lo que existe en el Excel

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
