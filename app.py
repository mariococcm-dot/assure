import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# ⚠️ PEGA AQUÍ TU URL DE GOOGLE APPS SCRIPT
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final)
        if not df.empty:
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
            df_db['username'] = df_db['username'].astype(str).str.strip()
            df_db['password'] = df_db['password'].astype(str).str.strip()
            user_row = df_db[(df_db['username'] == str(u_log).strip()) & (df_db['password'] == str(p_log).strip())]
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

menu_options = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user_data['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú Principal", menu_options)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_evals = get_data("evaluaciones")
    if not df_evals.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Evaluaciones", len(df_evals))
        # Ajusta 'puntos' según el nombre exacto de tu columna en evaluaciones
        col_pts = 'puntos' if 'puntos' in df_evals.columns else df_evals.columns[-1]
        c2.metric("Promedio General", f"{round(df_evals[col_pts].mean(), 2)}%")
        st.divider()
        st.subheader("Historial Reciente")
        st.dataframe(df_evals.tail(10), use_container_width=True, hide_index=True)
    else:
        st.info("Dashboard listo. Esperando datos de evaluaciones...")

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
            ag_s = col2.selectbox("Seleccionar Agente", ag_list) if ag_list else col2.text_input("ID Agente")
            score = st.slider("Calidad (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            if st.form_submit_button("Guardar Evaluación"):
                id_agente = ag_s.split(" - ")[0] if " - " in ag_s else ag_s
                p = {"target_sheet": "evaluaciones", "action": "create", "agente": id_agente, "puntos": score, "evaluador": user_data['username'], "fecha": datetime.now().strftime("%Y-%m-%d"), "observaciones": obs}
                requests.post(URL_SCRIPT, json=p)
                st.success(f"✅ Evaluación guardada para {id_agente}")

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        with st.container(border=True):
            st.subheader("Nueva Campaña")
            nc = st.text_input("Nombre")
            if st.button("🚀 Crear"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "create", "nombre": nc})
                st.rerun()
        if not df_c.empty:
            st.divider()
            c_sel = st.selectbox("Acciones para:", df_c['campaña'].tolist())
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
            list_c = df_c_list['campaña'].unique().tolist() if not df_c_list.empty else ["General"]
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
            u_sel = st.selectbox("Afectar a:", df_u['username'].tolist())
            c1, c2 = st.columns(2)
            if c1.button("🚫 Inh."):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"status","user":u_sel,"val":"Inactivo"}); st.rerun()
            if c2.button("🗑️ Del."):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel}); st.rerun()
    with col_r:
        st.dataframe(df_u[['username', 'nombre', 'rol', 'campaña', 'estado']], use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_sc = get_data("scorecards")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        with st.container(border=True):
            df_c_sc = get_data("campañas")
            c_sel_sc = st.selectbox("Campaña", df_c_sc['campaña'].tolist() if not df_c_sc.empty else [])
            f_p = st.text_input("Criterio")
            f_pts = st.number_input("Puntos", 1, 100, 10)
            f_t = st.selectbox("Tipo", ["Escala", "Si/No"])
            if st.button("➕ Añadir"):
                requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_sel_sc,"pregunta":f_p,"puntos":f_pts,"tipo":f_t})
                st.rerun()
    with col_r:
        st.dataframe(df_sc, use_container_width=True, hide_index=True)
