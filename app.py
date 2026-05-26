import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# URL de tu Apps Script
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final)
        if not df.empty:
            # Limpiamos nombres de columnas: minúsculas y sin espacios
            df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except:
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
            # Intentar encontrar columnas de login dinámicamente
            col_user = 'username' if 'username' in df_db.columns else df_db.columns[0]
            col_pass = 'password' if 'password' in df_db.columns else df_db.columns[2]
            
            df_db[col_user] = df_db[col_user].astype(str).str.strip()
            df_db[col_pass] = df_db[col_pass].astype(str).str.strip()
            
            user_row = df_db[(df_db[col_user] == str(u_log).strip()) & (df_db[col_pass] == str(p_log).strip())]
            if not user_row.empty:
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = user_row.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 3. BARRA LATERAL ---
user_data = st.session_state["user_data"]
# Manejo de nombres de columnas dinámicos para el saludo
nombre_display = user_data.get('nombre', user_data.get('username', 'Usuario'))
rol_display = user_data.get('rol', 'Agente')

st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{nombre_display}**")

menu_options = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if rol_display == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú Principal", menu_options)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_evals = get_data("evaluaciones")
    if not df_evals.empty:
        c1, c2 = st.columns(2)
        c1.metric("Total Evaluaciones", len(df_evals))
        st.divider()
        st.subheader("Historial Reciente")
        st.dataframe(df_evals.tail(10), use_container_width=True, hide_index=True)
    else:
        st.info("Esperando datos de evaluaciones...")

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    if not df_c.empty:
        c_list = df_c['campaña'].tolist() if 'campaña' in df_c.columns else df_c.iloc[:,0].tolist()
        with st.form("form_eval"):
            col1, col2 = st.columns(2)
            c_s = col1.selectbox("Campaña", c_list)
            
            # Filtro de agentes dinámico
            col_u = 'username' if 'username' in df_u.columns else df_u.columns[0]
            col_n = 'nombre' if 'nombre' in df_u.columns else df_u.columns[1]
            ags = df_u[df_u.get('rol', '') == 'Agente'] 
            ag_list = (ags[col_u].astype(str) + " - " + ags[col_n].astype(str)).tolist()
            
            ag_s = col2.selectbox("Seleccionar Agente", ag_list) if ag_list else col2.text_input("ID Agente")
            score = st.slider("Calidad (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            if st.form_submit_button("Guardar Evaluación"):
                id_agente = ag_s.split(" - ")[0] if " - " in ag_s else ag_s
                p = {"target_sheet": "evaluaciones", "action": "create", "agente": id_agente, "puntos": score, "evaluador": user_data.get('username'), "fecha": datetime.now().strftime("%Y-%m-%d"), "observaciones": obs}
                requests.post(URL_SCRIPT, json=p)
                st.success("✅ Evaluación guardada")

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        with st.container(border=True):
            nc = st.text_input("Nombre de la Campaña")
            if st.button("🚀 Crear"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "create", "nombre": nc})
                st.rerun()
        if not df_c.empty:
            st.divider()
            col_camp = 'campaña' if 'campaña' in df_c.columns else df_c.columns[0]
            c_sel = st.selectbox("Acciones para:", df_c[col_camp].tolist())
            if st.button("🗑️ Eliminar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "delete", "nombre": c_sel})
                st.rerun()
    with col_r:
        st.dataframe(df_c, use_container_width=True, hide_index=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    col_l, col_r = st.columns([1.2, 2])
    
    with col_l:
        with st.container(border=True):
            st.subheader("Datos de Usuario")
            id_u = st.text_input("ID Empleado")
            nom_u = st.text_input("Nombre Completo")
            pass_u = st.text_input("Password", type="password")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            df_c_list = get_data("campañas")
            col_camp_ref = 'campaña' if 'campaña' in df_c_list.columns else (df_c_list.columns[0] if not df_c_list.empty else "Ninguna")
            list_c = df_c_list[col_camp_ref].unique().tolist() if not df_c_list.empty else ["General"]
            camp_u = st.selectbox("Campaña", list_c)
            
            b1, b2 = st.columns(2)
            if b1.button("🚀 Registrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u})
                st.rerun()
            if b2.button("📝 Modificar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u})
                st.rerun()
        
        if not df_u.empty:
            st.divider()
            # SELECCIÓN SEGURA DE COLUMNA PARA EL SELECTBOX
            col_id = 'username' if 'username' in df_u.columns else df_u.columns[0]
            u_sel = st.selectbox("Afectar a:", df_u[col_id].tolist())
            c1, c2 = st.columns(2)
            if c1.button("🚫 Inh."):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"status","user":u_sel,"val":"Inactivo"}); st.rerun()
            if c2.button("🗑️ Del."):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel}); st.rerun()
    with col_r:
        st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_sc = get_data("scorecards")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        with st.container(border=True):
            df_c_sc = get_data("campañas")
            col_camp_sc = 'campaña' if 'campaña' in df_c_sc.columns else (df_c_sc.columns[0] if not df_c_sc.empty else "N/A")
            c_sel_sc = st.selectbox("Campaña", df_c_sc[col_camp_sc].tolist() if not df_c_sc.empty else [])
            f_p = st.text_input("Criterio")
            f_pts = st.number_input("Puntos", 1, 100, 10)
            f_t = st.selectbox("Tipo", ["Escala", "Si/No"])
            if st.button("➕ Añadir"):
                requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_sel_sc,"pregunta":f_p,"puntos":f_pts,"tipo":f_t})
                st.rerun()
    with col_r:
        st.dataframe(df_sc, use_container_width=True, hide_index=True)
