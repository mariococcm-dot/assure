import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        nombre_hoja_web = quote(nombre_hoja)
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={nombre_hoja_web}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final)
        if not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 2. LÓGICA DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("ID de Empleado")
    p_log = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        df_db = get_data("usuarios")
        if not df_db.empty:
            df_db['username'] = df_db['username'].astype(str).str.strip()
            df_db['password'] = df_db['password'].astype(str).str.strip()
            user_row = df_db[(df_db['username'] == str(u_log).strip()) & 
                             (df_db['password'] == str(p_log).strip())]
            if not user_row.empty:
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = user_row.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 3. BARRA LATERAL ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user_data['nombre']}**")
st.sidebar.write(f"Rol: `{user_data['rol']}`")

if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"]
else:
    menu = ["Dashboard", "Evaluador"]

choice = st.sidebar.selectbox("Menú", menu)
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

# --- MÓDULO: GESTIÓN USUARIOS ---
if choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    col_l, col_r = st.columns([1.2, 2])
    
    with col_l:
        st.subheader("Datos de Usuario")
        with st.container(border=True):
            id_u = st.text_input("ID Empleado")
            nom_u = st.text_input("Nombre Completo")
            pass_u = st.text_input("Password", type="password")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            df_c = get_data("campañas")
            list_c = df_c['campaña'].unique().tolist() if not df_c.empty else ["Todas"]
            camp_u = st.selectbox("Campaña", list_c)
            
            b_reg, b_edit = st.columns(2)
            if b_reg.button("🚀 Registrar"):
                p = {"target_sheet": "usuarios", "action": "create", "username": id_u, "nombre": nom_u, "password": pass_u, "rol": rol_u, "campaña": camp_u, "estado": "Activo"}
                requests.post(URL_SCRIPT, json=p); st.rerun()
            if b_edit.button("📝 Modificar"):
                p = {"target_sheet": "usuarios", "action": "update", "username": id_u, "nombre": nom_u, "password": pass_u, "rol": rol_u, "campaña": camp_u}
                requests.post(URL_SCRIPT, json=p); st.rerun()

        st.markdown("---")
        st.subheader("Acciones Rápidas")
        if not df_u.empty:
            sel = st.selectbox("Seleccionar Usuario:", df_u['username'].tolist())
            c1, c2 = st.columns(2)
            if c1.button("🚫 Deshabilitar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "status", "user": sel, "val": "Inactivo"}); st.rerun()
            if c2.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "delete", "user": sel}); st.rerun()

    with col_r:
        st.subheader("Lista de Personal")
        if not df_u.empty:
            st.dataframe(df_u[['username', 'nombre', 'rol', 'campaña', 'estado']], use_container_width=True, hide_index=True)

# --- MÓDULO: GESTIÓN CAMPAÑAS ---
elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        with st.container(border=True):
            nc = st.text_input("Nombre de Campaña")
            if st.button("🚀 Crear"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "create", "nombre": nc}); st.rerun()
        
        st.markdown("---")
        if not df_c.empty:
            c_sel = st.selectbox("Campaña:", df_c['campaña'].tolist())
            nn = st.text_input("Nuevo nombre (para editar):")
            ca1, ca2, ca3 = st.columns(3)
            if ca1.button("📝 Edit"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "update", "old": c_sel, "new": nn}); st.rerun()
            if ca2.button("🚫 Des"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "status", "nombre": c_sel, "val": "Inactivo"}); st.rerun()
            if ca3.button("🗑️ Del"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "delete", "nombre": c_sel}); st.rerun()
    with col_r:
        st.dataframe(df_c, use_container_width=True, hide_index=True)

# --- MÓDULO: EVALUADOR ---
elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    if not df_c.empty:
        c_list = df_c[df_c['estado'] == 'Activo']['campaña'].tolist()
        with st.form("form_eval"):
            col1, col2 = st.columns(2)
            c_s = col1.selectbox("Campaña", c_list)
            ags = df_u[(df_u['rol'] == 'Agente') & (df_u['campaña'] == c_s)]
            ag_list = (ags['username'].astype(str) + " - " + ags['nombre'].astype(str)).tolist()
            ag_s = col2.selectbox("Agente", ag_list) if ag_list else col2.text_input("ID Agente (Manual)")
            
            sc = st.slider("Calidad (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            if st.form_submit_button("Guardar Evaluación"):
                id_agente = ag_s.split(" - ")[0] if " - " in ag_s else ag_s
                requests.post(URL_SCRIPT, json={"target_sheet": "evaluaciones", "agente": id_agente, "puntos": sc, "evaluador": user_data['username'], "fecha": datetime.now().strftime("%Y-%m-%d")})
                st.success("✅ Evaluación guardada")

# --- MÓDULO: SCORECARDS ---
elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        with st.container(border=True):
            f_c = st.selectbox("Campaña", get_data("campañas")['campaña'].tolist() if not get_data("campañas").empty else [])
            f_p = st.text_input("Criterio / Pregunta")
            if st.button("➕ Añadir Criterio"):
                requests.post(URL_SCRIPT, json={"target_sheet": "scorecards", "action": "create", "area": f_c, "pregunta": f_p})
                st.rerun()
    with col_r:
        df_sc = get_data("scorecards")
        st.dataframe(df_sc, use_container_width=True, hide_index=True)

# --- MÓDULO: DASHBOARD ---
else:
    st.header("📊 Dashboard de Calidad")
    st.info("Módulo de analítica en tiempo real.")
