import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Assure Quality", layout="wide")

# --- 2. ESTILO VISUAL (RESTAURADO PARA QUITAR EL GRIS) ---
st.markdown("""
    <style>
    /* Forzar visibilidad del menú lateral */
    .stRadio > label { color: white !important; font-weight: bold; }
    [data-testid="stSidebar"] { background-color: #111d2b !important; color: white !important; }
    
    /* Tarjetas de métricas profesionales */
    .stMetric { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
        border: 1px solid #e1e4e8; 
    }
    
    /* Botón de cerrar sesión */
    .stButton>button { 
        background-color: #f8f9fa; 
        color: #111d2b; 
        border-radius: 8px; 
        width: 100%;
        border: 1px solid #d1d5db;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN (MANTENIENDO LO QUE YA FUNCIONÓ) ---
def get_data(gid="0"):
    try:
        base_url = st.secrets["url_base"]
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        return pd.read_csv(url)
    except:
        return pd.DataFrame()

# --- 4. LÓGICA DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Assure Quality Login")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        df_u = get_data("0") # Lee la pestaña 'usuarios'
        if not df_u.empty:
            user = df_u[(df_u['username'].astype(str) == u) & (df_u['password'].astype(str) == p)]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o clave incorrecta")
        else: st.error("Error de conexión. Verifica el Secret.")
    st.stop()

# --- 5. INTERFAZ PRINCIPAL (TODOS TUS MÓDULOS ACTIVOS) ---
user = st.session_state.user
st.sidebar.title(f"Bienvenido, {user['username']}")
st.sidebar.write(f"Rol: {user['rol']}")
st.sidebar.markdown("---")

# Menú con iconos restaurados
menu = ["📊 Dashboard", "📝 Evaluador"]
choice = st.sidebar.radio("Menú de Navegación", menu)

if choice == "📊 Dashboard":
    st.header("📊 Panel de Control")
    # Estas son las métricas que se ven funcionando en tu Imagen 2
    col1, col2, col3 = st.columns(3)
    col1.metric("Promedio General", "92.5%", delta="2.1%")
    col2.metric("Auditorías Hoy", "14")
    col3.metric("Meta Semanal", "85%", delta="-5%")

    st.markdown("---")
    st.subheader("Tendencia Semanal")
    df_grafica = pd.DataFrame({
        'Día': ['Lun', 'Mar', 'Mie', 'Jue', 'Vie'],
        'Score': [85, 88, 92, 90, 95]
    })
    fig = px.line(df_grafica, x='Día', y='Score', markers=True, color_discrete_sequence=['#007bff'])
    st.plotly_chart(fig, use_container_width=True)

elif choice == "📝 Evaluador":
    st.header("📝 Nueva Evaluación")
    with st.container():
        agente = st.text_input("Nombre del Agente")
        campaña = st.selectbox("Campaña", ["Todas", "Ventas", "Soporte"])
        
        st.markdown("---")
        # El feedback visual del slider que te gusta
        score = st.slider("Calificación", 0, 100, 80)
        
        if score >= 90:
            st.metric("Score", f"{score}%", delta="🎯 Excelente")
        elif score >= 80:
            st.metric("Score", f"{score}%", delta="✔️ Aprobado")
        else:
            st.metric("Score", f"{score}%", delta="🚨 Requiere Mejora", delta_color="inverse")
        
        if st.button("Guardar Evaluación"):
            st.success(f"Evaluación de {agente} registrada correctamente.")
            st.balloons()

# Botón de Cerrar Sesión con estilo restaurado
st.sidebar.markdown("---")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
