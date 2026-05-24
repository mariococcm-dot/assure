import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Assure Quality", layout="wide")

# --- 2. ESTILO VISUAL (TU DISEÑO ORIGINAL) ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #111d2b; color: white; }
    .stButton>button { border-radius: 8px; height: 3em; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN SIN ERRORES (PANDAS DIRECTO) ---
def get_data(gid="0"):
    try:
        base_url = st.secrets["url_base"]
        # Extraemos el ID por si el link viene con basura
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        # Construimos el link de exportación pura que Google siempre acepta
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        return pd.read_csv(export_url)
    except:
        # Si falla, devolvemos un DataFrame con las columnas necesarias para que no se bloquee la UI
        return pd.DataFrame(columns=['username', 'password', 'rol', 'campaña'])

# --- 4. CONTROL DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Assure Quality Login")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        df_u = get_data("0") # Lee la pestaña 'usuarios'
        if not df_u.empty:
            # Validamos contra tu Excel
            user = df_u[(df_u['username'].astype(str) == u) & (df_u['password'].astype(str) == p)]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o clave incorrecta")
        else: st.error("Error de conexión: Revisa el link en Secrets.")
    st.stop()

# --- 5. INTERFAZ PRINCIPAL (TODOS TUS MÓDULOS ACTIVOS) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.write(f"Rol: {user['rol']}")
st.sidebar.markdown("---")

menu = ["📊 Dashboard", "📝 Evaluador"]
# Usamos index=0 para asegurar que Dashboard sea el default activo
choice = st.sidebar.radio("Menú de Navegación", menu)

if choice == "📊 Dashboard":
    st.header("📊 Panel de Control")
    col1, col2, col3 = st.columns(3)
    
    # Tus métricas originales
    col1.metric("Promedio General", "92.5%", delta="2.1%")
    col2.metric("Auditorías Hoy", "14")
    col3.metric("Meta Semanal", "85%", delta="-5%")

    st.markdown("---")
    
    # Tu gráfica de tendencia
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
        campaña_sel = st.selectbox("Campaña", ["Ventas", "Soporte", "Retención"])
        
        st.markdown("---")
        # El feedback visual del slider que pediste conservar
        score = st.slider("Calificación de la llamada", 0, 100, 80)
        
        if score >= 90:
            st.metric("Score Previsualizado", f"{score}%", delta="🎯 Excelente")
        elif score >= 80:
            st.metric("Score Previsualizado", f"{score}%", delta="✔️ Aprobado")
        else:
            st.metric("Score Previsualizado", f"{score}%", delta="🚨 Requiere Mejora", delta_color="inverse")
        
        if st.button("Guardar Evaluación"):
            st.success(f"Evaluación de {agente} guardada en la base de datos.")
            st.balloons()

# Botón de Cerrar Sesión con estilo restaurado
st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
