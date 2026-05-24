import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Assure Quality", layout="wide", initial_sidebar_state="expanded")

# --- ESTILO PROFESIONAL (Restaurado) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #edf2f7; }
    [data-testid="stSidebar"] { background-color: #111d2b; color: white; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE LECTURA ROBUSTA ---
def get_data(gid="0"):
    try:
        base_url = st.secrets["url_base"]
        # Limpiamos la URL y forzamos el GID de la pestaña
        url = base_url.split("/export")[0] + f"/export?format=csv&gid={gid}"
        return pd.read_csv(url).dropna(how="all")
    except Exception as e:
        st.error(f"Error de conexión: Verifica el link en Secrets. Detalle: {e}")
        return pd.DataFrame()

# --- LÓGICA DE AUTENTICACIÓN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Assure Quality Login")
    with st.container():
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            df_u = get_data("0") # La pestaña 'usuarios' es el GID 0
            if not df_u.empty:
                user = df_u[(df_u['username'] == u) & (df_u['password'] == p)]
                if not user.empty:
                    st.session_state.auth = True
                    st.session_state.user = user.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Usuario o clave incorrecta")
    st.stop()

# --- APP PRINCIPAL (Interfaz Mejorada) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.markdown(f"**Rol:** {user['rol']}")
menu = ["📊 Dashboard", "📝 Evaluador"]
choice = st.sidebar.radio("Menú de Navegación", menu)

if choice == "📊 Dashboard":
    st.header("📊 Panel de Control en Tiempo Real")
    col1, col2, col3 = st.columns(3)
    # Aquí puedes agregar métricas reales leyendo la pestaña de evaluaciones
    col1.metric("Promedio General", "92.5%", delta="2.1%")
    col2.metric("Auditorías Hoy", "14")
    col3.metric("Meta Semanal", "85%", delta="-5%")

elif choice == "📝 Evaluador":
    st.header("📝 Nueva Evaluación de Calidad")
    
    with st.expander("Información del Agente", expanded=True):
        c1, c2 = st.columns(2)
        agente = c1.text_input("Nombre del Agente")
        campaña = c2.selectbox("Campaña", ["Ventas", "Soporte", "Retención"])

    st.markdown("---")
    # Ejemplo de Scorecard
    score = st.slider("Calificación de la llamada", 0, 100, 85)
    
    # Feedback visual (El que te gustaba)
    if score >= 90:
        st.metric("Score Previsualizado", f"{score}.0%", delta="🎯 Excelente")
    elif score >= 80:
        st.metric("Score Previsualizado", f"{score}.0%", delta="✔️ Aprobado")
    else:
        st.metric("Score Previsualizado", f"{score}.0%", delta="🚨 Requiere Mejora", delta_color="inverse")

    comentarios = st.text_area("Observaciones de la evaluación")
    
    if st.button("Guardar Evaluación"):
        st.success(f"Evaluación de {agente} guardada con éxito.")
        st.balloons()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
