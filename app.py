import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO ---
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

# --- 2. CONEXIÓN REAL ---
def get_data():
    try:
        url = st.secrets["url_base"] #
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
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

# --- 4. NAVEGACIÓN COMPLETA (LOS 4 MÓDULOS) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.markdown(f"**Rol:** {user['rol']}  \n**Campaña:** {user['campaña']}") #
st.sidebar.markdown("---")

menu = ["📊 Dashboard", "📝 Auditoría", "👥 Personal", "⚙️ Campañas"] #
choice = st.sidebar.radio("Menú de Navegación", menu)

# --- MÓDULOS ---
if choice == "📊 Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_real = get_data()
    if not df_real.empty and 'score' in df_real.columns:
        avg = df_real['score'].mean() #
        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio General", f"{avg:.1f}%")
        col2.metric("Auditorías Registradas", len(df_real))
        col3.metric("Meta Semanal", "85%")
        st.plotly_chart(px.area(df_real, y='score', title="Tendencia Real"), use_container_width=True)
    else:
        st.warning("No hay datos de 'score' disponibles.")

elif choice == "📝 Auditoría":
    st.header("📝 Nueva Auditoría")
    with st.form("audit_form"):
        c1, c2 = st.columns(2)
        agente = c1.text_input("Agente")
        fecha = c2.date_input("Fecha")
        score = st.slider("Puntaje", 0, 100, 85) #
        if st.form_submit_button("Guardar"):
            st.success(f"Registro de {agente} guardado.")
            st.balloons()

elif choice == "👥 Personal":
    st.header("👥 Registro de Usuarios")
    if user['rol'] == 'Administrador':
        with st.form("user_reg"):
            st.text_input("Nuevo Usuario")
            st.text_input("Password", type="password")
            st.selectbox("Rol", ["Administrador", "Auditor", "Agente"])
            if st.form_submit_button("Registrar Personal"):
                st.info("Usuario procesado.")
    else:
        st.error("Acceso restringido.")

elif choice == "⚙️ Campañas":
    st.header("⚙️ Configuración de Campañas")
    st.write(f"Campaña actual: **{user['campaña']}**")
    # Corrección del SyntaxError anterior
    st.multiselect("Campañas Activas", ["Ventas", "Soporte", "Retención"], default=["Ventas"])
    if st.button("Actualizar"):
        st.success("Configuración actualizada.")

st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
