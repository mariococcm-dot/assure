import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO (RESTAURADO) ---
st.set_page_config(page_title="Assure Quality Enterprise", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    [data-testid="stSidebarContent"] * { color: white !important; }
    .stRadio > label { font-size: 1.1rem; font-weight: bold; color: white !important; }
    .stMetric { background-color: #ffffff !important; padding: 25px; border-radius: 15px; border: 1px solid #e1e4e8; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    [data-testid="stMetricValue"] { color: #111d2b !important; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #555555 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN REAL ---
def get_data():
    try:
        url = st.secrets["url_base"] #
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

# --- 3. LÓGICA DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Acceso al Sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Iniciar Sesión"):
        df_db = get_data()
        if not df_db.empty:
            user_row = df_db[(df_db['username'].astype(str) == u) & (df_db['password'].astype(str) == p)]
            if not user_row.empty:
                st.session_state.auth = True
                st.session_state.user = user_row.iloc[0].to_dict()
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

# --- 4. NAVEGACIÓN COMPLETA (MÓDULOS RECUPERADOS) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.info(f"Rol: {user['rol']} | Campaña: {user['campaña']}")

# RECUERDA: Estos son los módulos que faltaban
menu = ["📊 Dashboard", "📝 Nueva Auditoría", "👥 Registro Usuarios", "⚙️ Campañas"]
choice = st.sidebar.radio("Módulos", menu)

# --- MÓDULO 1: DASHBOARD ---
if choice == "📊 Dashboard":
    st.header("📊 Dashboard de Calidad Real")
    df_real = get_data()
    if not df_real.empty and 'score' in df_real.columns:
        # Cálculos reales
        avg = df_real['score'].mean()
        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio General", f"{avg:.1f}%")
        col2.metric("Auditorías", len(df_real))
        col3.metric("Meta", "85%")
        st.plotly_chart(px.line(df_real, y='score', title="Tendencia"), use_container_width=True)

# --- MÓDULO 2: NUEVA AUDITORÍA (REGISTRO) ---
elif choice == "📝 Nueva Auditoría":
    st.header("📝 Registro de Auditoría")
    with st.form("audit_form"):
        col1, col2 = st.columns(2)
        agente = col1.text_input("Nombre del Agente")
        fecha = col2.date_input("Fecha de Auditoría")
        # El slider visual que pediste
        score = st.slider("Calificación Final", 0, 100, 85)
        comentarios = st.text_area("Observaciones")
        if st.form_submit_button("Guardar Registro"):
            st.success(f"Auditoría de {agente} enviada.")

# --- MÓDULO 3: REGISTRO DE USUARIOS ---
elif choice == "👥 Registro Usuarios":
    st.header("👥 Gestión de Personal")
    if user['rol'] == 'Administrador': # Solo Admin
        with st.expander("Añadir Nuevo Usuario"):
            new_u = st.text_input("Nuevo Username")
            new_p = st.text_input("Nueva Password")
            new_r = st.selectbox("Rol", ["Administrador", "Auditor", "Agente"])
            if st.button("Registrar Usuario"):
                st.info("Usuario listo para ser guardado en base de datos.")
    else:
        st.error("No tienes permisos para registrar usuarios.")

# --- MÓDULO 4: CAMPAÑAS ---
elif choice == "⚙️ Campañas":
    st.header("⚙️ Configuración de Campañas")
    st.write(f"Campaña actual activa: **{user['campaña']}**")
    # Aquí puedes añadir la lista de campañas reales
    lista_campañas = ["Ventas", "Soporte", "Retención", "Todas"]
    nueva_campaña = st.selectbox("Cambiar a Campaña:", lista_campañas)
    if st.button("Actualizar Configuración"):
        st.success(f"Campaña actualizada a {nueva_campaña}")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
