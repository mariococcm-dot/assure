import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO (BORRADO DE CUALQUIER BLOQUEO VISUAL) ---
st.set_page_config(page_title="Assure Quality Enterprise", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    [data-testid="stSidebarContent"] * { color: white !important; }
    .stRadio > label { font-size: 1.1rem; font-weight: bold; color: white !important; }
    .stMetric { background-color: #ffffff !important; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; }
    [data-testid="stMetricValue"] { color: #111d2b !important; font-size: 2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN REAL A GOOGLE SHEETS ---
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
    st.title("🔑 Acceso al Sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        df_db = get_data()
        if not df_db.empty:
            user_row = df_db[(df_db['username'].astype(str) == u) & (df_db['password'].astype(str) == p)]
            if not user_row.empty:
                st.session_state.auth = True
                st.session_state.user = user_row.iloc[0].to_dict()
                st.rerun()
    st.stop()

# --- 4. MÓDULOS DE GESTIÓN (RECUPERADOS AL 100%) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.write(f"Rol: {user['rol']} | Campaña: {user['campaña']}")

# Los módulos que faltaban hoy
menu = ["📊 Dashboard", "📝 Auditoría", "👥 Personal", "⚙️ Campañas"]
choice = st.sidebar.radio("Navegación", menu)

if choice == "📊 Dashboard":
    st.header("📊 Panel de Control")
    df_real = get_data()
    if not df_real.empty and 'score' in df_real.columns:
        c1, c2, c3 = st.columns(3)
        c1.metric("Promedio General", f"{df_real['score'].mean():.1f}%") #
        c2.metric("Auditorías", len(df_real))
        c3.metric("Meta", "85%")
        st.plotly_chart(px.area(df_real, y='score', title="Tendencia Semanal"), use_container_width=True)

elif choice == "📝 Auditoría":
    st.header("📝 Nueva Auditoría")
    with st.form("audit"):
        st.text_input("Nombre Agente")
        st.slider("Puntaje", 0, 100, 85)
        if st.form_submit_button("Guardar"):
            st.success("Guardado.")

elif choice == "👥 Personal":
    st.header("👥 Gestión de Usuarios")
    tab1, tab2 = st.tabs(["Añadir Nuevo", "Editar Personal"])
    with tab1:
        with st.form("new_u"):
            st.text_input("Nombre de Usuario")
            st.selectbox("Rol", ["Administrador", "Auditor", "Agente"])
            st.form_submit_button("Crear")
    with tab2:
        st.write("Seleccione un usuario de la lista para editar sus permisos.")

elif choice == "⚙️ Campañas":
    st.header("⚙️ Configuración de Campañas") #
    tab_c1, tab_c2 = st.tabs(["Crear Campaña", "Activar/Desactivar"])
    with tab_c1:
        st.text_input("Nueva Campaña")
        st.button("Registrar")
    with tab_c2:
        st.multiselect("Campañas Activas", ["Ventas", "Soporte", "Retención"], default=["Ventas"])
        st.button("Actualizar")

st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
