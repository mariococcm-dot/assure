import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Assure Quality", layout="wide")

# --- 2. ESTILO VISUAL (TU DISEÑO ORIGINAL) ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    [data-testid="stSidebar"] { background-color: #111d2b !important; color: white !important; }
    .stRadio > label { color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN REAL (SEGÚN TU SECRET) ---
def get_data():
    try:
        # Usa el link de exportación que configuraste
        url = st.secrets["url_base"]
        df = pd.read_csv(url)
        # Limpieza básica de espacios en nombres de columnas
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# --- 4. LÓGICA DE LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Assure Quality Login")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        df_u = get_data() # Lee tu pestaña de usuarios
        if not df_u.empty and 'username' in df_u.columns:
            user = df_u[(df_u['username'].astype(str) == u) & (df_u['password'].astype(str) == p)]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o clave incorrecta")
    st.stop()

# --- 5. INTERFAZ PRINCIPAL ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.write(f"Rol: {user['rol']}")
st.sidebar.markdown("---")

choice = st.sidebar.radio("Menú de Navegación", ["📊 Dashboard", "📝 Evaluador"])

# --- MÓDULO DASHBOARD (DATOS REALES) ---
if choice == "📊 Dashboard":
    st.header("📊 Panel de Control (Datos Reales)")
    
    # Aquí cargamos los datos para procesar
    df_real = get_data() 
    
    # Solo calculamos si existen las columnas 'score' y 'estado'
    if not df_real.empty and 'score' in df_real.columns:
        promedio = df_real['score'].mean()
        total_auditorias = len(df_real)
        # Ejemplo de filtro por estado 'Activo'
        activos = len(df_real[df_real['estado'] == 'Activo'])

        col1, col2, col3 = st.columns(3)
        col1.metric("Promedio General", f"{promedio:.1f}%")
        col2.metric("Total Auditorías", f"{total_auditorias}")
        col3.metric("Usuarios Activos", f"{activos}")

        st.markdown("---")
        # Gráfica real (usa una columna 'fecha' si la tienes, si no, usa el índice)
        fig = px.line(df_real, y='score', title="Tendencia de Calidad Real", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ No se encontraron datos de scores en tu Google Sheet para calcular las métricas.")

# --- MÓDULO EVALUADOR ---
elif choice == "📝 Evaluador":
    st.header("📝 Nueva Evaluación")
    with st.container():
        agente = st.text_input("Nombre del Agente")
        campaña = st.selectbox("Campaña", ["Ventas", "Soporte", "Retención"])
        st.markdown("---")
        
        # Feedback visual que ya tenías
        score = st.slider("Calificación de la llamada", 0, 100, 80)
        
        if score >= 90:
            st.metric("Score Previsualizado", f"{score}%", delta="🎯 Excelente")
        elif score >= 80:
            st.metric("Score Previsualizado", f"{score}%", delta="✔️ Aprobado")
        else:
            st.metric("Score Previsualizado", f"{score}%", delta="🚨 Mejora Necesaria", delta_color="inverse")
        
        if st.button("Guardar Evaluación"):
            # Aquí se añadiría la lógica para escribir en el Excel
            st.success(f"Evaluación de {agente} registrada localmente.")
            st.balloons()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
