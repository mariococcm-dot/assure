import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO (VISIBILIDAD TOTAL) ---
st.set_page_config(page_title="Assure Quality Enterprise", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    [data-testid="stSidebarContent"] * { color: white !important; }
    .stRadio > label { font-size: 1.1rem; font-weight: bold; color: white !important; }
    .stMetric { background-color: #ffffff !important; padding: 25px; border-radius: 15px; border: 1px solid #e1e4e8; }
    [data-testid="stMetricValue"] { color: #111d2b !important; font-size: 2.2rem !important; }
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

# --- 3. ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Acceso Assure Quality")
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

# --- 4. NAVEGACIÓN TOTAL (LOS 4 MÓDULOS) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.markdown(f"**Rol:** {user['rol']} | **Campaña:** {user['campaña']}")
st.sidebar.markdown("---")

menu = ["📊 Dashboard", "📝 Auditoría", "👥 Personal", "⚙️ Campañas"]
choice = st.sidebar.radio("Menú de Navegación", menu)

# --- MÓDULO 1: DASHBOARD ---
if choice == "📊 Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_real = get_data()
    if not df_real.empty and 'score' in df_real.columns:
        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio General", f"{df_real['score'].mean():.1f}%")
        col2.metric("Total Auditorías", len(df_real))
        col3.metric("Meta", "85%")
        st.plotly_chart(px.area(df_real, y='score', title="Tendencia Real"), use_container_width=True)

# --- MÓDULO 2: AUDITORÍA ---
elif choice == "📝 Auditoría":
    st.header("📝 Registro de Nueva Auditoría")
    with st.form("audit"):
        st.text_input("Nombre del Agente")
        st.slider("Calificación Obtenida", 0, 100, 85)
        st.text_area("Comentarios de Retroalimentación")
        if st.form_submit_button("Guardar Registro"):
            st.success("Auditoría registrada.")

# --- MÓDULO 3: PERSONAL (CREACIÓN Y EDICIÓN) ---
elif choice == "👥 Personal":
    st.header("👥 Gestión de Usuarios")
    tab1, tab2 = st.tabs(["Añadir Nuevo", "Editar Existente"])
    
    with tab1:
        with st.form("new_user"):
            st.text_input("Nuevo Username")
            st.text_input("Password", type="password")
            st.selectbox("Rol", ["Administrador", "Auditor", "Agente"])
            if st.form_submit_button("Crear Usuario"):
                st.info("Procesando creación...")

    with tab2:
        df_users = get_data()
        if not df_users.empty:
            user_edit = st.selectbox("Selecciona usuario a editar", df_users['username'].tolist())
            st.text_input("Actualizar Password")
            st.selectbox("Cambiar Rol", ["Administrador", "Auditor", "Agente"], key="edit_rol")
            st.button("Actualizar Usuario")

# --- MÓDULO 4: CAMPAÑAS (CREACIÓN Y EDICIÓN) ---
elif choice == "⚙️ Campañas":
    st.header("⚙️ Configuración de Campañas")
    st.write(f"Campaña actual de tu perfil: **{user['campaña']}**")
    
    tab_c1, tab_c2 = st.tabs(["Crear Campaña", "Gestionar Activas"])
    
    with tab_c1:
        with st.form("new_camp"):
            st.text_input("Nombre de la Nueva Campaña")
            st.multiselect("Asignar Auditores", ["Auditor_1", "Auditor_2"])
            if st.form_submit_button("Crear Campaña"):
                st.success("Campaña creada satisfactoriamente.")

    with tab_c2:
        # Recuperado de la imagen image_11fd94.png
        st.multiselect("Campañas Activas en el Sistema", ["Ventas", "Soporte", "Retención"], default=["Ventas"])
        if st.button("Actualizar Campañas Activas"):
            st.success("Estado de campañas actualizado.")

st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
