import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# URL de tu Apps Script (Asegúrate de que sea la última versión implementada)
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final)
        # Limpieza estándar de columnas
        if not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- 2. LÓGICA DE LOGIN (ADMIN FIJO + EXCEL) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        # Prioridad 1: Admin Fijo
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"username": "admin", "nombre": "Administrador", "rol": "Administrador", "campaña": "Todas"}
            st.rerun()
        
        # Prioridad 2: Base de datos Excel
        df_db = get_data("usuarios")
        if not df_db.empty:
            encontrado = False
            for _, row in df_db.iterrows():
                # Columna 0 (username) y Columna 2 (password)
                if str(row.iloc[0]).strip() == u_log and str(row.iloc[2]).strip() == p_log:
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {
                        "username": str(row.iloc[0]).strip(),
                        "nombre": str(row.iloc[1]).strip(),
                        "rol": str(row.iloc[3]).strip(),
                        "campaña": str(row.iloc[4]).strip()
                    }
                    encontrado = True
                    break
            if encontrado: st.rerun()
            else: st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# --- 3. BARRA LATERAL ---
user = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user['nombre']}**")
menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

# --- DASHBOARD ---
if choice == "Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        st.metric("Total Evaluaciones", len(df_ev))
        st.dataframe(df_ev, use_container_width=True, hide_index=True)
    else: st.info("No hay datos de evaluaciones aún.")

# --- EVALUADOR ---
elif choice == "Evaluador":
    st.header("📝 Módulo de Evaluación")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    
    with st.form("form_eval"):
        col1, col2 = st.columns(2)
        c_list = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
        c_sel = col1.selectbox("Campaña", c_list)
        
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente'] if not df_u.empty else pd.DataFrame()
        ag_list = (ags.iloc[:,0].astype(str) + " - " + ags.iloc[:,1].astype(str)).tolist()
        ag_sel = col2.selectbox("Agente", ag_list if ag_list else ["Sin agentes"])
        
        puntos = st.slider("Puntaje", 0, 100, 85)
        obs = st.text_area("Observaciones")
        
        if st.form_submit_button("Guardar Evaluación"):
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "agente": ag_sel.split(" - ")[0], "puntos_obtenidos": puntos,
                "evaluador": user['username'], "observaciones": obs
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success("✅ Evaluación registrada correctamente")

# --- GESTIÓN CAMPAÑAS ---
elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    c1, c2 = st.columns([1, 2])
    with c1:
        nc = st.text_input("Nombre de la Campaña")
        if st.button("🚀 Crear Campaña"):
            requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
            st.rerun()
    with c2: st.dataframe(df_c, use_container_width=True, hide_index=True)

# --- GESTIÓN USUARIOS ---
elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1.2, 2])
    
    with col_l:
        with st.container(border=True):
            st.subheader("Datos de Usuario")
            u_id = st.text_input("ID / Username")
            u_nom = st.text_input("Nombre Completo")
            u_pass = st.text_input("Password")
            u_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            u_camp = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["Todas"])
            
            b_reg, b_mod = st.columns(2)
            if b_reg.button("🚀 Registrar"):
                # ORDEN ESTRICTO: A=username, B=nombre, C=password, D=rol, E=campaña, F=estado
                p = {"target_sheet":"usuarios","action":"create","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp,"estado":"Activo"}
                requests.post(URL_SCRIPT, json=p); st.rerun()
            if b_mod.button("📝 Modificar"):
                p = {"target_sheet":"usuarios","action":"update","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp}
                requests.post(URL_SCRIPT, json=p); st.rerun()
        
        st.divider()
        if not df_u.empty:
            st.subheader("Acciones Rápidas")
            u_sel = st.selectbox("Seleccionar ID:", df_u.iloc[:,0].tolist())
            a1, a2 = st.columns(2)
            if a1.button("🚫 Inhabilitar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"status","user":u_sel,"val":"Inactivo"}); st.rerun()
            if a2.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel}); st.rerun()

    with col_r:
        st.subheader("Lista de Usuarios")
        st.dataframe(df_u, use_container_width=True, hide_index=True)

# --- CONFIG SCORECARDS ---
elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_sc = get_data("scorecards")
    df_c = get_data("campañas")
    
    with st.container(border=True):
        c_sc = st.selectbox("Campaña vinculada", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        preg_sc = st.text_input("Pregunta / Criterio")
        pts_sc = st.number_input("Puntos", 1, 100, 10)
        if st.button("➕ Añadir Criterio"):
            p = {"target_sheet":"scorecards","action":"create","area":c_sc, "pregunta":preg_sc, "puntos":pts_sc}
            requests.post(URL_SCRIPT, json=p); st.rerun()
    
    st.subheader("Criterios Registrados")
    st.dataframe(df_sc, use_container_width=True, hide_index=True)
