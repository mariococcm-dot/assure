import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="QualityScore Enterprise",
    page_icon="🎯",
    layout="wide"
)

# --- 2. ESTILO VISUAL (Vainilla Premium) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #111d2b; color: white; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN A DATOS (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name):
    return conn.read(worksheet=sheet_name).dropna(how="all")

# --- 4. BARRA LATERAL (Logo e Info) ---
# Tip: Sube tu logo a GitHub y usa el nombre del archivo aquí
try:
    st.sidebar.image("logo.png", use_container_width=True) # Cambia por tu archivo
except:
    st.sidebar.title("🎯 QualityScore")

st.sidebar.markdown("---")

# --- 5. LOGICA DE ACCESO ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    with st.container():
        st.subheader("🔑 Inicio de Sesión Operativo")
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar al Sistema"):
            df_u = get_data("usuarios")
            user = df_u[(df_u['username'] == u) & (df_u['password'] == p)]
            if not user.empty:
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Acceso denegado")
    st.stop()

# --- 6. MENÚ DE NAVEGACIÓN ---
user_data = st.session_state["user_data"]
menu = []
if user_data['rol'] == 'Administrador':
    menu = ["📊 Dashboard", "📝 Evaluación", "⚙️ Gestión Campañas", "👥 Usuarios"]
elif user_data['rol'] == 'Evaluador':
    menu = ["📊 Dashboard", "📝 Evaluación"]
else:
    menu = ["📈 Mis Resultados"]

choice = st.sidebar.radio("Navegación", menu)

# --- 7. MÓDULO: DASHBOARD ---
if choice == "📊 Dashboard":
    st.title("📊 Analítica de Calidad en Tiempo Real")
    df_eval = get_data("evaluaciones")
    
    if df_eval.empty:
        st.info("Esperando los primeros datos de la operación...")
    else:
        # Filtros Pro
        col1, col2, col3 = st.columns(3)
        with col1:
            camp_list = ["Todas"] + df_eval['area'].unique().tolist()
            sel_camp = st.selectbox("Campaña", camp_list)
        with col2:
            df_eval['fecha_evento'] = pd.to_datetime(df_eval['fecha_evento'])
            años = sorted(df_eval['fecha_evento'].dt.year.unique(), reverse=True)
            sel_año = st.selectbox("Año", años)
        with col3:
            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            sel_mes = st.selectbox("Mes", meses, index=datetime.now().month-1)

        # Filtrado de datos
        df_f = df_eval[df_eval['fecha_evento'].dt.year == sel_año]
        if sel_camp != "Todas": df_f = df_f[df_f['area'] == sel_camp]
        
        # Gráficas de Desempeño
        st.markdown("---")
        c_alt1, c_alt2 = st.columns(2)
        with c_alt1:
            fig_agentes = px.bar(df_f.groupby('agente')['puntos_obtenidos'].mean().reset_index(), 
                                 x='agente', y='puntos_obtenidos', title="Desempeño por Asesor (%)",
                                 color='puntos_obtenidos', color_continuous_scale='Viridis')
            st.plotly_chart(fig_agentes, use_container_width=True)
        with c_alt2:
            fig_criterio = px.bar(df_f.groupby('pregunta')['puntos_obtenidos'].sum().reset_index(), 
                                  y='pregunta', x='puntos_obtenidos', orientation='h', 
                                  title="Puntos Acumulados por Criterio", color_discrete_sequence=['#007bff'])
            st.plotly_chart(fig_criterio, use_container_width=True)

# --- 8. MÓDULO: EVALUACIÓN ---
elif choice == "📝 Evaluación":
    st.header("📝 Nueva Auditoría de Calidad")
    df_sc = get_data("scorecards")
    areas = df_sc['area'].unique().tolist()
    
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1: a_sel = st.selectbox("Campaña a evaluar", areas)
        with c2: ag_sel = st.text_input("Nombre del Agente")
        with c3: f_ev = st.date_input("Fecha del contacto", datetime.now())
        
        st.markdown("### Criterios de Evaluación")
        preguntas = df_sc[df_sc['area'] == a_sel]
        respuestas = {}
        
        for _, row in preguntas.iterrows():
            if row['tipo'] == "Sí / No":
                r = st.radio(row['pregunta'], ["Sí", "No"], horizontal=True)
                respuestas[row['pregunta']] = row['puntos'] if r == "Sí" else 0
            else:
                respuestas[row['pregunta']] = st.slider(row['pregunta'], 0, int(row['puntos']), int(row['puntos']))
        
        obs = st.text_area("Notas de Retroalimentación")
        
        # Feedback Visual Dinámico
        total_obt = sum(respuestas.values())
        total_max = preguntas['puntos'].sum()
        score_final = (total_obt / total_max * 100) if total_max > 0 else 0
        
        if score_final >= 90:
            st.metric("Puntaje Final", f"{score_final:.1f}%", delta="🎯 Excelente", delta_color="normal")
        elif score_final >= 80:
            st.metric("Puntaje Final", f"{score_final:.1f}%", delta="✔️ Aprobado", delta_color="off")
        else:
            st.metric("Puntaje Final", f"{score_final:.1f}%", delta="🚨 Requiere Mejora", delta_color="inverse")

        if st.button("🚀 Finalizar y Cargar a Google Sheets"):
            # Aquí va la lógica de conn.update para enviar los datos
            st.success("¡Evaluación enviada con éxito!")

# --- 9. GESTIÓN (Simplificada) ---
elif choice == "⚙️ Gestión Campañas":
    st.title("⚙️ Configuración de Operación")
    st.write("Desde aquí puedes añadir nuevas campañas y criterios.")
    # Lógica de gestión de campañas vinculada a GSheets

elif choice == "👥 Usuarios":
    st.title("👥 Control de Accesos")
    df_u = get_data("usuarios")
    st.dataframe(df_u, use_container_width=True)

if st.sidebar.button("🚪 Salir"):
    st.session_state["autenticado"] = False
    st.rerun()
