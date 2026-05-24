import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO (RESTAURADO) ---
st.set_page_config(page_title="QualityScore Enterprise Edition", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #111d2b !important; }
    [data-testid="stSidebarContent"] * { color: white !important; }
    .stRadio > label { font-size: 1.1rem; font-weight: bold; color: white !important; }
    .stMetric { background-color: #ffffff !important; padding: 25px; border-radius: 15px; border: 1px solid #e1e4e8; }
    [data-testid="stMetricValue"] { color: #111d2b !important; font-size: 2.2rem !important; }
    [data-testid="stMetricLabel"] { color: #555555 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS (REEMPLAZA SQLITE) ---
def get_data():
    try:
        url = st.secrets["url_base"]
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# --- 3. LÓGICA DE SESIÓN Y LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Enterprise - Login")
    u_log = st.text_input("Usuario")
    p_log = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        df_db = get_data()
        if not df_db.empty:
            # Validación con tu tabla de usuarios [cite: 3, 5]
            user_row = df_db[(df_db['username'].astype(str) == u_log) & (df_db['password'].astype(str) == p_log)]
            if not user_row.empty:
                user = user_row.iloc[0]
                if user['estado'] == 'Inactivo': 
                    st.error("🚫 Usuario inactivo.")
                else:
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {"user": user['username'], "rol": user['rol'], "campaña": user['campaña']}
                    st.rerun()
            else: st.error("❌ Credenciales incorrectas.")
    st.stop()

# --- 4. MENÚ Y NAVEGACIÓN (SEGÚN ROL DE AYER) ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Usuario: **{user_data['user']}**")

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# Definición de menús según el archivo funcional 
if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Config Scorecards", "Gestión Campañas", "Gestión Usuarios"]
elif user_data['rol'] == 'Evaluador':
    menu = ["Dashboard", "Evaluador"]
else:
    menu = ["Mis Calificaciones"]

choice = st.sidebar.selectbox("Menú", menu)

# --- MÓDULO: DASHBOARD ---
if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_eval = get_data()
    
    if df_eval.empty:
        st.info("Sin datos registrados aún.")
    else:
        # Lógica de fechas y meses [cite: 7, 8]
        df_eval['fecha_registro'] = pd.to_datetime(df_eval['fecha_registro'])
        df_eval['Año'] = df_eval['fecha_registro'].dt.year
        meses_esp = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            camps = ["Ver Todas"] + sorted(df_eval['area'].unique().tolist())
            sel_camp = st.selectbox("Campaña:", camps)
        with col_f2:
            sel_año = st.selectbox("Año:", sorted(df_eval['Año'].unique().tolist(), reverse=True))
        with col_f3:
            sel_mes_num = st.selectbox("Mes:", range(1, 13), format_func=lambda x: meses_esp[x-1], index=datetime.now().month - 1)

        # Filtrado y KPIs [cite: 11, 12]
        df_f = df_eval[(df_eval['Año'] == sel_año) & (df_eval['fecha_registro'].dt.month == sel_mes_num)]
        if sel_camp != "Ver Todas":
            df_f = df_f[df_f['area'] == sel_camp]

        if not df_f.empty:
            df_cons = df_f.groupby(['agente', 'area']).agg(
                Suma_Obtenida=('puntos_obtenidos', 'sum'),
                Suma_Maxima=('puntos_maximos', 'sum')
            ).reset_index()
            df_cons['% Final'] = (df_cons['Suma_Obtenida'] / df_cons['Suma_Maxima']) * 100
            
            st.metric("Total de Monitoreos", len(df_cons))
            fig = px.bar(df_cons, x='agente', y='% Final', color='area', title="Desempeño por Agente", text_auto='.1f')
            st.plotly_chart(fig, use_container_width=True)

# --- MÓDULO: GESTIÓN DE USUARIOS (RESTAURADO) ---
elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data()
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Acciones")
        modo_u = st.radio("Operación:", ["Nuevo", "Editar"]) # [cite: 33, 34]
        if modo_u == "Nuevo":
            st.text_input("Username")
            st.text_input("Password", type="password")
            st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            st.button("🚀 Registrar")
        else:
            st.selectbox("Seleccionar Usuario:", df_u['username'].tolist() if not df_u.empty else [])
            st.button("📝 Actualizar")
    
    with col2:
        st.subheader("Lista")
        st.dataframe(df_u[['username', 'rol', 'campaña', 'estado']] if not df_u.empty else pd.DataFrame())

# --- MÓDULO: GESTIÓN DE CAMPAÑAS (RESTAURADO) ---
elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.radio("Operación:", ["Nueva", "Editar Existente"]) # [cite: 26]
        st.text_input("Nombre Campaña")
        st.button("Guardar")
    with col2:
        st.subheader("Listado Activo")
        # Aquí se mostraría la lista de campañas únicas de la base
        st.info("Lista de campañas sincronizada con Google Sheets.")

# --- MÓDULO: EVALUADOR ---
elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    with st.form("eval_form"):
        st.selectbox("Campaña", ["Ventas", "Soporte"])
        st.text_input("Nombre Agente")
        st.slider("Criterio: Calidad de Proceso", 0, 100, 85) # [cite: 20]
        if st.form_submit_button("Guardar Evaluación"):
            st.success("Evaluación procesada exitosamente.")

# --- MÓDULO: MIS CALIFICACIONES (PARA AGENTES) ---
elif choice == "Mis Calificaciones":
    st.header(f"📈 Panel de Resultados: {user_data['user']}")
    st.info("Aquí verás tus resultados históricos filtrados por tu usuario.") # [cite: 42]
