import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Assure Quality", layout="wide")

# --- ESTILO VISUAL (TU DISEÑO) ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #111d2b !important; color: white !important; }
    .stRadio > label { color: white !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN DIRECTA ---
def get_data():
    try:
        # Lee directamente la URL del secret sin modificarle nada
        return pd.read_csv(st.secrets["url_base"])
    except:
        return pd.DataFrame()

# --- LÓGICA DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Assure Quality Login")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        df_u = get_data()
        if not df_u.empty and 'username' in df_u.columns:
            # Validación exacta según tu hoja
            user = df_u[(df_u['username'].astype(str) == u) & (df_u['password'].astype(str) == p)]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o clave incorrecta")
        else: st.error("Error: No se pudo conectar con Google Sheets.")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.write(f"Rol: {user['rol']}")
st.sidebar.markdown("---")

choice = st.sidebar.radio("Menú de Navegación", ["📊 Dashboard", "📝 Evaluador"])

if choice == "📊 Dashboard":
    st.header("📊 Panel de Control")
    col1, col2, col3 = st.columns(3)
    col1.metric("Promedio General", "92.5%", delta="2.1%")
    col2.metric("Auditorías Hoy", "14")
    col3.metric("Meta Semanal", "85%", delta="-5%")

    st.markdown("---")
    df_grafica = pd.DataFrame({'Día': ['Lun', 'Mar', 'Mie', 'Jue', 'Vie'], 'Score': [85, 88, 92, 90, 95]})
    fig = px.line(df_grafica, x='Día', y='Score', markers=True, title="Tendencia Semanal")
    st.plotly_chart(fig, use_container_width=True)

elif choice == "📝 Evaluador":
    st.header("📝 Nueva Evaluación")
    agente = st.text_input("Nombre del Agente")
    score = st.slider("Calificación", 0, 100, 80)
    
    if score >= 90: st.metric("Score", f"{score}%", delta="🎯 Excelente")
    elif score >= 80: st.metric("Score", f"{score}%", delta="✔️ Aprobado")
    else: st.metric("Score", f"{score}%", delta="🚨 Mejora", delta_color="inverse")
    
    if st.button("Guardar"):
        st.success(f"Evaluación de {agente} guardada.")
        st.balloons()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
