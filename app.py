import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Assure Quality", layout="wide")

# --- 2. ESTILO PARA FORZAR VISIBILIDAD DE MÓDULOS ---
st.markdown("""
    <style>
    /* Forzar que el menú de navegación sea blanco y no gris */
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    [data-testid="stSidebarContent"] * { color: white !important; }
    .stRadio > label { font-size: 1.2rem; font-weight: bold; }
    
    /* Estilo de las métricas en blanco para que resalten */
    .stMetric { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #d1d5db;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricValue"] { color: #111d2b !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN (Manejando el Error 400) ---
def get_data():
    try:
        # Tu link de Google Sheets configurado en Secrets
        url = st.secrets["url_base"]
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip() # Limpia nombres de columnas
        return df
    except Exception as e:
        # Si falla, no bloqueamos la app, devolvemos un aviso
        return None

# --- 4. LÓGICA DE LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Assure Quality Login")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        df_u = get_data()
        if df_u is not None:
            # Validación con tu Excel real
            user = df_u[(df_u['username'].astype(str) == u) & (df_u['password'].astype(str) == p)]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o clave incorrecta")
        else: st.error("Error de conexión: Revisa el link en Secrets.")
    st.stop()

# --- 5. MENÚ DE NAVEGACIÓN (SIEMPRE ACTIVO) ---
user = st.session_state.user
st.sidebar.title(f"Hola, {user['username']}")
st.sidebar.write(f"**Rol:** {user['rol']}")
st.sidebar.write(f"**Campaña:** {user['campaña']}")
st.sidebar.markdown("---")

# Aquí están los módulos que pediste
choice = st.sidebar.radio("IR A:", ["📊 Dashboard", "📝 Evaluador"])

if choice == "📊 Dashboard":
    st.header("📊 Panel de Control Operativo")
    df_real = get_data()
    
    if df_real is not None and 'score' in df_real.columns:
        # CÁLCULOS REALES
        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio General", f"{df_real['score'].mean():.1f}%")
        col2.metric("Auditorías Totales", len(df_real))
        col3.metric("Meta", "85%")
        
        st.markdown("---")
        fig = px.bar(df_real, x='username', y='score', title="Desempeño por Usuario")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Los módulos están activos, pero no hay datos en la columna 'score' de tu Excel.")

elif choice == "📝 Evaluador":
    st.header("📝 Módulo Evaluador")
    st.info(f"Campaña actual: {user['campaña']}")
    
    with st.container():
        agente = st.text_input("Nombre del Agente")
        # Slider visual restaurado
        nota = st.slider("Calificación", 0, 100, 80)
        
        if nota >= 90: st.success(f"Excelente: {nota}%")
        elif nota >= 80: st.info(f"Aprobado: {nota}%")
        else: st.error(f"Reprobado: {nota}%")
        
        if st.button("Guardar Evaluación"):
            st.balloons()
            st.success("Guardado (Simulación)")

# BOTÓN CERRAR SESIÓN
st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
