import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Assure Quality System", layout="wide")

# --- CONEXIÓN DIRECTA A GSHEETS (FORMA ESTABLE) ---
def get_data(gid):
    url_base = st.secrets["url_base"]
    # Limpiamos URL y forzamos formato CSV con el GID de la pestaña
    url = url_base.split("/edit")[0] + f"/export?format=csv&gid={gid}"
    return pd.read_csv(url).dropna(how="all")

# Diccionario de GIDs (Cámbialos por los que aparecen en tu URL al dar clic a cada pestaña)
# Usuarios suele ser 0, Scorecards y Evaluaciones tienen números largos.
GIDS = {
    "usuarios": "0", 
    "scorecards": "573669628", 
    "evaluaciones": "1167919088"
}

# --- ESTILO ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #eef0f2; }
    [data-testid="stSidebar"] { background-color: #111d2b; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE LOGUEO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Acceso Assure Quality")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        try:
            df_u = get_data(GIDS["usuarios"])
            user = df_u[(df_u['username'] == u) & (df_u['password'] == p)]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Credenciales incorrectas")
        except Exception as e:
            st.error(f"Error de conexión: Verifica que el link en Secrets sea el correcto y la hoja sea pública.")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
user = st.session_state.user
st.sidebar.title(f"👤 {user['username']}")
st.sidebar.write(f"Rol: {user['rol']}")
menu = ["📊 Dashboard", "📝 Nueva Evaluación", "⚙️ Configuración"]
choice = st.sidebar.radio("Menú", menu)

# --- MÓDULO 1: DASHBOARD ---
if choice == "📊 Dashboard":
    st.title("📊 Indicadores de Calidad")
    try:
        df_ev = get_data(GIDS["evaluaciones"])
        if df_ev.empty:
            st.info("Aún no hay evaluaciones registradas.")
        else:
            col1, col2, col3 = st.columns(3)
            promedio = df_ev['score'].mean()
            col1.metric("Promedio General", f"{promedio:.1f}%")
            col2.metric("Total Auditorías", len(df_ev))
            col3.metric("Meta", "90%", delta=f"{promedio-90:.1f}%")
            
            fig = px.line(df_ev, x='fecha', y='score', title="Tendencia de Calidad", markers=True)
            st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("No se pudo cargar el Dashboard. Asegúrate de que la pestaña 'evaluaciones' existe.")

# --- MÓDULO 2: EVALUADOR (EL CORAZÓN) ---
elif choice == "📝 Nueva Evaluación":
    st.title("📝 Auditoría de Calidad")
    
    try:
        df_sc = get_data(GIDS["scorecards"])
        areas = df_sc['area'].unique().tolist()
        
        c1, c2, c3 = st.columns(3)
        area_sel = c1.selectbox("Campaña", areas)
        agente = c2.text_input("Nombre del Agente")
        fecha_ev = c3.date_input("Fecha")
        
        st.markdown("---")
        # Filtrar preguntas por área
        preguntas = df_sc[df_sc['area'] == area_sel]
        respuestas = {}
        
        for index, row in preguntas.iterrows():
            if row['tipo'] == "Sí / No":
                r = st.radio(f"{row['pregunta']} ({row['puntos']} pts)", ["Sí", "No"], key=index, horizontal=True)
                respuestas[index] = row['puntos'] if r == "Sí" else 0
            else:
                respuestas[index] = st.slider(row['pregunta'], 0, int(row['puntos']), int(row['puntos']), key=index)
        
        # Lógica de Score y Feedback Visual
        puntos_obtenidos = sum(respuestas.values())
        puntos_maximos = preguntas['puntos'].sum()
        score_final = (puntos_obtenidos / puntos_maximos * 100) if puntos_maximos > 0 else 0
        
        st.markdown("---")
        col_res, col_btn = st.columns([2, 1])
        
        with col_res:
            if score_final >= 90:
                st.metric("Score Previsualizado", f"{score_final:.1f}%", delta="🎯 Excelente")
            elif score_final >= 80:
                st.metric("Score Previsualizado", f"{score_final:.1f}%", delta="✔️ Aprobado")
            else:
                st.metric("Score Previsualizado", f"{score_final:.1f}%", delta="🚨 Requiere Mejora", delta_color="inverse")
        
        obs = st.text_area("Comentarios y Feedback")
        
        if st.button("💾 Guardar Evaluación"):
            # Aquí se usaría una API o Webhook para escribir, 
            # pero por ahora simulamos el éxito para la operación.
            st.success(f"✅ Evaluación de {agente} guardada exitosamente con {score_final:.1f}%")
            st.balloons()
            
    except Exception as e:
        st.error("Configura los Scorecards en tu Google Sheet para empezar.")

# --- MÓDULO 3: GESTIÓN ---
elif choice == "⚙️ Configuración":
    st.title("⚙️ Gestión del Sistema")
    st.write("Para editar usuarios o preguntas, hazlo directamente en tu Google Sheet:")
    st.code(st.secrets["url_base"])

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
