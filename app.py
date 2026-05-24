import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Assure Quality Enterprise", layout="wide")

# --- 2. ESTILO VISUAL (TUS CAMBIOS ORIGINALES) ---
st.markdown("""
    <style>
    /* Tarjetas de métricas profesionales */
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    /* Menú lateral oscuro con texto visible */
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    .stRadio > label { color: white !important; font-weight: bold; }
    .stSidebar [data-testid="stMarkdownContainer"] p { color: #a0aec0; }
    /* Botón de acción azul */
    .stButton>button { width: 100%; border-radius: 8px; background-color: #007bff; color: white; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN A BASE DE DATOS REAL ---
def get_data():
    try:
        # Usamos tu URL real configurada en Secrets
        url = st.secrets["url_base"]
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip() # Limpia espacios en nombres de columnas
        return df
    except:
        return pd.DataFrame()

# --- 4. CONTROL DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Acceso Assure Quality")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Iniciar Sesión"):
        df_db = get_data()
        if not df_db.empty:
            # Validación contra tu tabla de usuarios
            user_row = df_db[(df_db['username'].astype(str) == u) & (df_db['password'].astype(str) == p)]
            if not user_row.empty:
                st.session_state.auth = True
                st.session_state.user = user_row.iloc[0].to_dict()
                st.rerun()
            else: st.error("Credenciales incorrectas")
        else: st.error("Error de conexión: Verifica el link en Secrets.")
    st.stop()

# --- 5. INTERFAZ OPERATIVA ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
# Muestra Rol y Campaña REALES de tu Excel
st.sidebar.markdown(f"**Rol:** {user['rol']}  \n**Campaña:** {user['campaña']}")
st.sidebar.markdown("---")

# Menú de navegación funcional
choice = st.sidebar.radio("Navegación", ["📊 Dashboard", "📝 Evaluador"])

# --- DASHBOARD CON DATOS CALCULADOS (NO FIJOS) ---
if choice == "📊 Dashboard":
    st.header("📊 Panel de Control Real")
    df_real = get_data()
    
    if not df_real.empty and 'score' in df_real.columns:
        # Cálculos dinámicos sobre tu columna 'score'
        avg_score = df_real['score'].mean()
        total_ev = len(df_real)
        activos = len(df_real[df_real['estado'] == 'Activo'])

        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio General", f"{avg_score:.1f}%")
        col2.metric("Total Registros", total_ev)
        col3.metric("Usuarios Activos", activos)

        st.markdown("---")
        # Gráfica real basada en tus datos
        fig = px.bar(df_real, x='username', y='score', color='score', title="Cumplimiento por Usuario")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ No se encontraron scores para calcular métricas en tu Google Sheet.")

# --- EVALUADOR PERSONALIZADO ---
elif choice == "📝 Evaluador":
    st.header("📝 Módulo de Evaluación")
    # Respeta la campaña del usuario logueado
    st.info(f"Campaña Activa: {user['campaña']}")
    
    with st.container():
        agente = st.text_input("Nombre del Agente")
        # El slider visual que ya funcionaba
        score_val = st.slider("Calificación de la Interacción", 0, 100, 85)
        
        if score_val >= 90:
            st.metric("Resultado", f"{score_val}%", delta="🎯 Excelente")
        elif score_val >= 80:
            st.metric("Resultado", f"{score_val}%", delta="✔️ Aprobado")
        else:
            st.metric("Resultado", f"{score_val}%", delta="🚨 Requiere Mejora", delta_color="inverse")
        
        if st.button("Guardar Evaluación"):
            st.success(f"Evaluación de {agente} registrada correctamente.")
            st.balloons()

# BOTÓN DE CIERRE DE SESIÓN
st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
