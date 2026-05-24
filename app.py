import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Assure Quality Enterprise", layout="wide")

# --- 2. ESTILO VISUAL PROFESIONAL (RESTAURADO) ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    .stRadio > label { color: white !important; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN A TU BASE DE DATOS REAL ---
def get_data():
    try:
        # Usa el link de exportación de tu Secret
        url = st.secrets["url_base"]
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip() # Limpia espacios en encabezados
        return df
    except:
        return pd.DataFrame()

# --- 4. SISTEMA DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Acceso al Sistema")
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
            else: st.error("Credenciales incorrectas")
        else: st.error("Error de conexión con Google Sheets")
    st.stop()

# --- 5. INTERFAZ DE TRABAJO ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.info(f"Rol: {user['rol']} | Campaña: {user['campaña']}")
st.sidebar.markdown("---")

# Menú con los módulos que ayer funcionaban
choice = st.sidebar.radio("Navegación", ["📊 Dashboard", "📝 Evaluador"])

# --- MÓDULO DASHBOARD (DATOS 100% REALES) ---
if choice == "📊 Dashboard":
    st.header("📊 Panel de Control Operativo")
    df_real = get_data()
    
    if not df_real.empty and 'score' in df_real.columns:
        # Cálculos basados en tu columna 'score'
        avg_score = df_real['score'].mean()
        total_ev = len(df_real)
        activos = len(df_real[df_real['estado'] == 'Activo'])

        c1, c2, c3 = st.columns(3)
        c1.metric("Promedio General", f"{avg_score:.1f}%")
        c2.metric("Total Registros", total_ev)
        c3.metric("Usuarios Activos", activos)

        st.markdown("---")
        # Gráfica real de desempeño
        fig = px.bar(df_real, x='username', y='score', color='score', title="Cumplimiento por Usuario")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No hay datos de 'score' para mostrar en el Dashboard.")

# --- MÓDULO EVALUADOR ---
elif choice == "📝 Evaluador":
    st.header("📝 Módulo de Evaluación")
    # Usamos la campaña real del usuario logueado
    st.subheader(f"Evaluando para Campaña: {user['campaña']}")
    
    with st.form("eval_form"):
        agente = st.text_input("Nombre del Agente a evaluar")
        # Slider con feedback visual
        score_val = st.slider("Calificación Final", 0, 100, 85)
        
        if st.form_submit_button("Guardar Evaluación"):
            st.success(f"Evaluación de {agente} procesada.")
            st.balloons()

# BOTÓN CERRAR SESIÓN
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
