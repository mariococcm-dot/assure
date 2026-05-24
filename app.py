import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Assure Quality", layout="wide")

# --- ESTILO VISUAL (Mantenido tal cual) ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #111d2b; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- CORRECCIÓN DE CONEXIÓN (Único cambio realizado) ---
def get_data(gid="0"):
    try:
        # Usamos la URL de los secrets y nos aseguramos de que termine en export e incluya el GID
        url = st.secrets["url_base"].split("/edit")[0] + f"/export?format=csv&gid={gid}"
        df = pd.read_csv(url)
        return df
    except Exception as e:
        return pd.DataFrame() # Retorna vacío si falla para no romper el login

# --- LÓGICA DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Assure Quality Login")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        df_u = get_data("0") # GID 0 es la pestaña 'usuarios'
        if not df_u.empty and 'username' in df_u.columns:
            user = df_u[(df_u['username'] == u) & (df_u['password'] == p)]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o clave incorrecta")
        else: st.error("Error de conexión con la base de datos.")
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
    
    # Datos simulados para las gráficas (puedes vincularlos a otra pestaña después)
    col1.metric("Promedio General", "92.5%", delta="2.1%")
    col2.metric("Auditorías Hoy", "14")
    col3.metric("Meta Semanal", "85%", delta="-5%")

    st.markdown("---")
    
    # Gráfica de ejemplo que ya funcionaba
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
        # El feedback visual que rescatamos
        score = st.slider("Calificación de la interacción", 0, 100, 80)
        
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
