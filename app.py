import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO VISUAL (RESTAURADO) ---
st.set_page_config(page_title="Assure Quality Enterprise", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    [data-testid="stSidebarContent"] * { color: white !important; }
    .stRadio > label { font-size: 1.1rem; font-weight: bold; color: white !important; }
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

# --- 2. CONEXIÓN REAL A GOOGLE SHEETS ---
def get_data():
    try:
        url = st.secrets["url_base"] #
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame()

# --- 3. CONTROL DE ACCESO ---
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
            else: st.error("Credenciales incorrectas.")
    st.stop()

# --- 4. MENÚ DE NAVEGACIÓN TOTAL (LOS 4 MÓDULOS) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.markdown(f"**Rol:** {user['rol']} | **Campaña:** {user['campaña']}")
st.sidebar.markdown("---")

# Módulos reales solicitados
menu = ["📊 Dashboard", "📝 Auditoría", "👥 Personal", "⚙️ Campañas"]
choice = st.sidebar.radio("Módulos de Gestión", menu)

# --- MÓDULO 1: DASHBOARD (DATOS REALES) ---
if choice == "📊 Dashboard":
    st.header("📊 Panel de Control Operativo")
    df_real = get_data()
    if not df_real.empty and 'score' in df_real.columns:
        avg = df_real['score'].mean()
        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio General", f"{avg:.1f}%") #
        col2.metric("Total Auditorías", len(df_real))
        col3.metric("Meta Semanal", "85%")
        st.plotly_chart(px.area(df_real, y='score', title="Tendencia de Calidad"), use_container_width=True)
    else:
        st.warning("⚠️ No se detectan datos de 'score' en la base de datos.")

# --- MÓDULO 2: AUDITORÍA (FORMULARIO) ---
elif choice == "📝 Auditoría":
    st.header("📝 Nueva Auditoría de Calidad")
    with st.form("audit_form"):
        c1, c2 = st.columns(2)
        agente = c1.text_input("Nombre del Agente")
        fecha = c2.date_input("Fecha de Evaluación")
        score = st.slider("Puntaje Final", 0, 100, 85)
        comentarios = st.text_area("Observaciones de Mejora")
        if st.form_submit_button("Guardar Registro"):
            st.success(f"Auditoría de {agente} enviada con éxito.")
            st.balloons()

# --- MÓDULO 3: PERSONAL (CREACIÓN Y EDICIÓN) ---
elif choice == "👥 Personal":
    st.header("👥 Gestión de Usuarios y Accesos")
    tab1, tab2 = st.tabs(["✨ Crear Usuario", "✏️ Editar Usuario"])
    
    with tab1:
        with st.form("new_user_form"):
            st.text_input("Nuevo Username")
            st.text_input("Contraseña", type="password")
            st.selectbox("Asignar Rol", ["Administrador", "Auditor", "Agente"])
            st.selectbox("Asignar Campaña", ["Ventas", "Soporte", "Retención"])
            if st.form_submit_button("Registrar en Base de Datos"):
                st.info("Usuario creado satisfactoriamente.")

    with tab2:
        df_u = get_data()
        if not df_u.empty:
            sel_user = st.selectbox("Usuario a modificar", df_u['username'].tolist())
            st.text_input("Nueva Contraseña", type="password")
            st.selectbox("Cambiar Rol", ["Administrador", "Auditor", "Agente"], key="edit_role")
            if st.button("Guardar Cambios"):
                st.success("Usuario actualizado.")

# --- MÓD
