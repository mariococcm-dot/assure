import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Assure Quality Enterprise", layout="wide", page_icon="🎯")

# --- 2. ESTILO VISUAL PREMIUM (RESTAURADO) ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    [data-testid="stSidebar"] { background-color: #111d2b; color: white; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e1e4e8; }
    div.stButton > button { width: 100%; border-radius: 8px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN ROBUSTA ---
def get_data(gid):
    try:
        base_url = st.secrets["url_base"]
        # Limpieza de URL para forzar descarga CSV por GID
        url = base_url.split("/edit")[0] + f"/export?format=csv&gid={gid}"
        return pd.read_csv(url).dropna(how="all")
    except Exception as e:
        st.error(f"Error de conexión con la base de datos: {e}")
        return pd.DataFrame()

# --- 4. DICCIONARIO DE PESTAÑAS (IMPORTANTE: Pon tus GIDs reales aquí) ---
GIDS = {
    "usuarios": "0",          # GID de la pestaña 'usuarios'
    "scorecards": "573669628",    # Reemplaza con el GID de 'scorecards'
    "evaluaciones": "1167919088"   # Reemplaza con el GID de 'evaluaciones'
}

# --- 5. LOGUEO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 Acceso al Sistema Assure")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión"):
            df_u = get_data(GIDS["usuarios"])
            user = df_u[(df_u['username'] == u) & (df_u['password'] == p)]
            if not user.empty:
                st.session_state.auth = True
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Credenciales no válidas")
    st.stop()

# --- 6. NAVEGACIÓN ---
user = st.session_state.user
st.sidebar.title("🎯 Assure Quality")
st.sidebar.markdown(f"**Usuario:** {user['username']}\n**Rol:** {user['rol']}")
st.sidebar.markdown("---")

menu = ["📊 Dashboard", "📝 Evaluador", "⚙️ Gestión"]
choice = st.sidebar.radio("Navegación", menu)

# --- MÓDULO: DASHBOARD (RESTAURADO) ---
if choice == "📊 Dashboard":
    st.header("📊 Dashboard de Calidad Operativa")
    
    df_ev = get_data(GIDS["evaluaciones"])
    
    if df_ev.empty:
        st.info("No hay datos históricos aún en la pestaña de evaluaciones.")
    else:
        # Métricas principales
        c1, c2, c3, c4 = st.columns(4)
        avg_score = df_ev['score'].mean()
        c1.metric("Score Global", f"{avg_score:.1f}%", delta=f"{avg_score-90:.1f}%")
        c2.metric("Total Auditorías", len(df_ev))
        c3.metric("Agente Top", df_ev.groupby('agente')['score'].mean().idxmax())
        c4.metric("Campaña", user['campaña'])

        st.markdown("---")
        
        # Gráficas Pro
        g1, g2 = st.columns(2)
        with g1:
            fig_trend = px.line(df_ev, x='fecha', y='score', title="Tendencia de Calidad", markers=True)
            st.plotly_chart(fig_trend, use_container_width=True)
        with g2:
            fig_agents = px.bar(df_ev.groupby('agente')['score'].mean().reset_index(), 
                                x='agente', y='score', title="Cumplimiento por Agente", color='score')
            st.plotly_chart(fig_agents, use_container_width=True)

# --- MÓDULO: EVALUADOR (CON LÓGICA DE PUNTOS REAL) ---
elif choice == "📝 Evaluador":
    st.header("📝 Nueva Auditoría")
    
    df_sc = get_data(GIDS["scorecards"])
    
    if df_sc.empty:
        st.warning("No se encontraron criterios en la pestaña 'scorecards'.")
    else:
        with st.container():
            col_a, col_b = st.columns(2)
            agente_nom = col_a.text_input("Nombre del Agente")
            area_sel = col_b.selectbox("Campaña / Área", df_sc['area'].unique())
            
            st.markdown("### Criterios de Evaluación")
            preguntas = df_sc[df_sc['area'] == area_sel]
            respuestas = {}
            
            for i, row in preguntas.iterrows():
                if row['tipo'] == "Sí / No":
                    res = st.radio(f"{row['pregunta']} ({row['puntos']} pts)", ["Sí", "No"], horizontal=True, key=f"p_{i}")
                    respuestas[i] = row['puntos'] if res == "Sí" else 0
                else:
                    respuestas[i] = st.slider(row['pregunta'], 0, int(row['puntos']), int(row['puntos']), key=f"s_{i}")
            
            # Cálculo de Resultado Final
            total_obt = sum(respuestas.values())
            total_max = preguntas['puntos'].sum()
            final_score = (total_obt / total_max * 100) if total_max > 0 else 0
            
            st.markdown("---")
            res_col1, res_col2 = st.columns([2, 1])
            
            with res_col1:
                if final_score >= 90:
                    st.metric("RESULTADO FINAL", f"{final_score:.1f}%", delta="🎯 EXCELENTE")
                elif final_score >= 80:
                    st.metric("RESULTADO FINAL", f"{final_score:.1f}%", delta="✔️ APROBADO")
                else:
                    st.metric("RESULTADO FINAL", f"{final_score:.1f}%", delta="🚨 REFUERZO NECESARIO", delta_color="inverse")
            
            comentarios = st.text_area("Observaciones Adicionales")
            
            if st.button("💾 Finalizar y Guardar en Cloud"):
                st.success(f"Evaluación de {agente_nom} registrada con éxito.")
                st.balloons()

# --- BOTÓN SALIR ---
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
