import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
from urllib.parse import quote # Esto permite traducir la "ñ" a código web

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# URL DE TU GOOGLE APPS SCRIPT
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

# --- 2. CONEXIÓN A GOOGLE SHEET (LECTURA) ---
def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        nombre_hoja_web = quote(nombre_hoja)
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={nombre_hoja_web}&cache={datetime.now().timestamp()}"
        
        df = pd.read_csv(url_final)
        
        # Si el dataframe no está vacío, limpiamos columnas
        if not df.empty:
            # Convertimos todo a minúsculas y quitamos espacios
            df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al leer hoja {nombre_hoja}: {e}")
        return pd.DataFrame()        

# --- 3. LÓGICA DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario")
    p_log = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        df_db = get_data("usuarios")
        
        if not df_db.empty:
            if 'username' in df_db.columns and 'password' in df_db.columns:
                user_row = df_db[(df_db['username'].astype(str) == u_log) & 
                                 (df_db['password'].astype(str) == p_log)]
                
                if not user_row.empty:
                    user = user_row.iloc[0]
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {
                        "user": user['username'], 
                        "rol": user['rol'], 
                        "campaña": user['campaña']
                    }
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.error(f"❌ Error de estructura. Columnas detectadas: {list(df_db.columns)}")
        else:
            st.error("❌ No se pudo leer la base de datos de usuarios.")
    st.stop()


# --- 4. BARRA LATERAL ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Usuario: **{user_data['user']}**")
st.sidebar.write(f"Rol: **{user_data['rol']}**")

if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"]
elif user_data['rol'] == 'Evaluador':
    menu = ["Dashboard", "Evaluador"]
else:
    menu = ["Mis Calificaciones"]

choice = st.sidebar.selectbox("Menú", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- MÓDULOS DE NAVEGACIÓN ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_dash = get_data()
    if not df_dash.empty:
        camps_dash = ["Ver Todas"] + df_dash['campaña'].unique().tolist()
        sel_camp = st.selectbox("Filtrar por Campaña:", camps_dash)
        st.info(f"Mostrando datos reales para: {sel_camp}")

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_base = get_data()
    camps_reales = df_base['campaña'].unique().tolist() if not df_base.empty else []
    
    if not camps_reales:
        st.warning("No hay campañas configuradas.")
    else:
        with st.form("form_eval"):
            c1, c2 = st.columns(2)
            a_sel = c1.selectbox("Campaña", camps_reales)
            ags = df_base[(df_base['rol'] == 'Agente') & (df_base['campaña'] == a_sel)]['username'].tolist()
            ag_sel = c2.selectbox("Agente", ags) if ags else c2.text_input("Nombre Agente (Manual)")
            
            f_ev = st.date_input("Fecha de Evento", datetime.now())
            t_eval = st.selectbox("Evaluado por:", ["Calidad", "Operaciones"])
            score_val = st.slider("Calidad de Proceso (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar Evaluación"):
                payload = {
                    "target_sheet": "evaluaciones",
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fecha_evento": str(f_ev),
                    "area": a_sel,
                    "evaluador": user_data['user'],
                    "agente": ag_sel,
                    "pregunta": "Evaluación General",
                    "puntos_obtenidos": score_val,
                    "puntos_maximos": 100,
                    "observaciones": obs,
                    "tipo_evaluador": t_eval
                }
                res = requests.post(URL_SCRIPT, json=payload)
                if res.text == "Éxito":
                    st.success("✅ Evaluación guardada")
                    st.balloons()

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Acciones")
        modo_c = st.radio("Operación:", ["Nueva", "Editar / Acción"])
        
        if modo_c == "Nueva":
            nc = st.text_input("Nombre de Campaña")
            if st.button("🚀 Crear Campaña"):
                res = requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "create", "nombre": nc})
                if res.text == "Éxito": 
                    st.success("Creada"); st.rerun()
        else:
            camp_list = df_c['campaña'].unique().tolist() if not df_c.empty else []
            sel_c = st.selectbox("Seleccionar Campaña:", camp_list)
            nuevo_n = st.text_input("Renombrar a:")
            
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("📝 Modificar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "update", "old": sel_c, "new": nuevo_n})
                st.rerun()
            if b2.button("✅ Hab."):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "status", "nombre": sel_c, "val": "Activo"})
                st.rerun()
            if b3.button("🚫 Desh."):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "status", "nombre": sel_c, "val": "Inactivo"})
                st.rerun()
            if b4.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "delete", "nombre": sel_c})
                st.rerun()

    with col2:
        st.subheader("Campañas en Sistema")
        if not df_c.empty:
            st.dataframe(df_c[['campaña', 'estado']].drop_duplicates(), use_container_width=True, hide_index=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    col_u1, col_u2 = st.columns([1, 2])
    
    with col_u1:
        modo_u = st.radio("Acción", ["Nuevo", "Editar/Borrar"])
        if modo_u == "Nuevo":
            nu = st.text_input("Username")
            np = st.text_input("Password", type="password")
            nr = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            df_camps_aux = get_data("campañas")
            lista_c = df_camps_aux[df_camps_aux['estado'] == 'Activo']['campaña'].unique().tolist() if not df_camps_aux.empty else ["Todas"]
            nc_u = st.selectbox("Asignar a Campaña", lista_c)
            if st.button("🚀 Registrar"):
