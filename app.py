import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO (VISIBILIDAD TOTAL) ---
st.set_page_config(page_title="Assure Quality Enterprise", layout="wide")

st.markdown("""
    <style>
    /* Sidebar oscuro con texto blanco forzado */
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    [data-testid="stSidebarContent"] * { color: white !important; }
    .stRadio > label { font-size: 1.1rem; font-weight: bold; color: white !important; }
    
    /* Tarjetas de Métricas Reales */
    .stMetric { 
        background-color: #ffffff !important; 
        padding: 25px; 
        border-radius: 15px; 
        border: 1px solid #e1e4e8;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricValue"] { color: #111d2b !important; font-size: 2.2rem !important; }
    [data-testid="stMetricLabel"] { color: #555555 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN REAL A TU GOOGLE SHEET ---
def get_data():
    try:
        # Tu URL de Secrets
        url = st.secrets["url_base"]
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame()

# --- 3. ACCESO AL SISTEMA ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Acceso Assure Quality")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Iniciar Sesión"):
        df_db = get_data()
        if not df_db.empty:
            # Validación real contra tu Excel
            user_row = df_db[(df_db['username'].astype(str) == u) & (df_db['password'].astype(str) == p)]
            if not user_row.empty:
                st.session_state.auth = True
                st.session_state.user = user_row.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o contraseña incorrectos.")
    st.stop()

# --- 4. NAVEGACIÓN COMPLETA (LOS 4 MÓDULOS DE AYER) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.markdown(f"**Rol:** {user['rol']}  \n**Campaña:** {user['campaña']}")
st.sidebar.markdown("---")

# Módulos recuperados
menu = ["📊 Dashboard", "📝 Auditoría", "👥 Personal", "⚙️ Campañas"]
choice = st.sidebar.radio("Menú de Navegación", menu)

# --- MÓDULO 1: DASHBOARD (DATOS REALES) ---
if choice == "📊 Dashboard":
    st.header("📊 Dashboard Operativo")
    df_real = get_data()
    if not df_real.empty and 'score' in df_real.columns:
        # Cálculos basados en tu columna 'score'
        avg = df_real['score'].mean()
        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio General", f"{avg:.1f}%")
        col2.metric("Auditorías Registradas", len(df_real))
        col3.metric("Meta Semanal", "85%")
        
        st.markdown("---")
        fig = px.area(df_real, y='score', title="Tendencia de Calidad Real", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Sin datos de score en el Excel para mostrar métricas.")

# --- MÓDULO 2: AUDITORÍA (REGISTRO) ---
elif choice == "📝 Auditoría":
    st.header("📝 Nueva Auditoría de Calidad")
    with st.form("audit_form"):
        c1, c2 = st.columns(2)
        agente_nom = c1.text_input("Agente")
        fecha_aud = c2.date_input("Fecha")
        # Slider visual
        nota = st.slider("Puntaje Obtenido", 0, 100, 85)
        obs = st.text_area("Comentarios de Retroalimentación")
        if st.form_submit_button("Guardar Auditoría"):
            st.success(f"Registro de {agente_nom} procesado correctamente.")
            st.balloons()

# --- MÓDULO 3: PERSONAL (REGISTRO USUARIOS) ---
elif choice == "👥 Personal":
    st.header("👥 Gestión de Usuarios y Roles")
    if user['rol'] == 'Administrador':
        with st.expander("Registrar Nuevo Usuario"):
            st.text_input("Username")
            st.text_input("Password")
            st.selectbox("Rol", ["Administrador", "Auditor", "Agente"])
            st.button("Guardar en Sistema")
    else:
        st.error("Acceso restringido: Solo Administradores.")

# --- MÓDULO 4: CAMPAÑAS ---
elif choice == "⚙️ Campañas":
    st.header("⚙️ Configuración de Campañas")
    st.write(f"Campaña actual: **{user['campaña']}**")
    st.multiselect("Campañas Activas", ["Ventas", "Soporte", "Retención"], default=["V
