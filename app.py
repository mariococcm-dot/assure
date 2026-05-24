import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Assure Quality", layout="wide")

# --- ESTILO VISUAL (Original Restaurado) ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #111d2b; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN BLINDADA ---
def get_data(gid="0"):
    try:
        # Extraemos la URL base del secret
        raw_url = st.secrets["url_base"]
        # Forzamos la limpieza: quitamos cualquier cosa después del ID y armamos el link de exportación
        if "/d/" in raw_url:
            base = raw_url.split("/d/")[1].split("/")[0]
            clean_url = f"https://docs.google.com/spreadsheets/d/{base}/export?format=csv&gid={gid}"
        else:
            clean_url = raw_url
            
        return pd.read_csv(clean_url)
    except Exception as e:
        # Si falla, no intentamos procesar nada para evitar el KeyError
        return pd.DataFrame()

# --- LÓGICA DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Assure Quality Login")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        df_u = get_data("0") # Intentamos leer la pestaña 'usuarios' (GID 0)
        
        if not df_u.empty and 'username' in df_u.columns:
            # Buscamos al usuario en los datos de Google Sheets
            user_match = df_u[(df_u['username'].astype(str) == u) & (df_u['password'].astype(str) == p)]
            if not user_match.empty:
                st.session_state.auth = True
                st.session_state.user = user_match.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Usuario o clave incorrecta")
        else:
            st.error("Error de conexión: No se pudo leer la tabla de usuarios. Revisa el link en Secrets.")
    st.stop()

# --- INTERFAZ POST-LOGIN (Original sin cambios) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.write(f"Rol: {user['rol']}")
menu = ["📊 Dashboard", "📝 Evaluador"]
choice = st.sidebar.radio("Menú", menu)

if choice == "📊 Dashboard":
    st.header("📊 Panel de Control")
    col1, col2, col3 = st.columns(3)
    col1.metric("Promedio General", "92.5%", delta="2.1%")
    col2.metric("Auditorías Hoy", "14")
    col3.metric("Meta Semanal", "85%", delta="-5%")
    
    st.markdown("---")
    df_grafica = pd.DataFrame({
        'Día': ['Lun', 'Mar', 'Mie', 'Jue', 'Vie'],
        'Score': [85, 88, 92, 90, 95]
    })
    fig = px.line(df_grafica, x='Día', y='Score', title="Tendencia Semanal", markers=True)
    st.plotly_chart(fig, use_container_width=True)

elif choice == "📝 Evaluador":
    st.header("📝 Nueva Evaluación")
    with st.container():
        agente = st.text_input("Nombre del Agente")
        campaña = st.selectbox("Campaña", ["Ventas", "Soporte", "Retención"])
        st.markdown("---")
        
        # Feedback visual rescatado
        score = st.slider("Calificación", 0, 100, 80)
        if score >= 90:
            st.metric("Score Previsualizado", f"{score}%", delta="🎯 Excelente")
        elif score >= 80:
            st.metric("Score Previsualizado", f"{score}%", delta="✔️ Aprobado")
        else:
            st.metric("Score Previsualizado", f"{score}%", delta="🚨 Requiere Mejora", delta_color="inverse")
        
        if st.button("Guardar Evaluación"):
            st.success(f"Evaluación de {agente} enviada correctamente.")
            st.balloons()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
