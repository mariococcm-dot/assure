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
        return df
    except:
        return pd.DataFrame()

# --- 2. LÓGICA DE SESIÓN (LOGIN CORREGIDO) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("ID de Empleado").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        # --- LOGIN ADMINISTRADOR FIJO (BACKDOOR DE SEGURIDAD) ---
        if u_log == "admin" and p_log == "admin123": # Cambia admin123 por tu clave fija
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {
                "username": "admin",
                "nombre": "Administrador Sistema",
                "rol": "Administrador",
                "campaña": "Todas"
            }
            st.rerun()
        
        # --- LOGIN DESDE EXCEL ---
        df_db = get_data("usuarios")
        if not df_db.empty:
            encontrado = False
            for _, row in df_db.iterrows():
                # Col 0: ID, Col 2: Password
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
            
            if encontrado:
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 3. INTERFAZ PRINCIPAL ---
user = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user['nombre']}**")

menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Seleccione Módulo", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        col1, col2 = st.columns(2)
        col1.metric("Total Evaluaciones", len(df_ev))
        st.subheader("Historial de Evaluaciones")
        st.dataframe(df_ev, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos registrados aún.")

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    
    with st.form("form_eval"):
        c_list = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
        c_sel = st.selectbox("Campaña", c_list)
        
        # Filtro de agentes (Rol en columna 3)
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente'] if not df_u.empty else pd.DataFrame()
        ag_nombres = (ags.iloc[:,0].astype(str) + " - " + ags.iloc[:,1].astype(str)).tolist() if not ags.empty else []
        
        ag_sel = st.selectbox("Agente", ag_nombres if ag_nombres else ["Sin agentes"])
        score = st.slider("Calificación", 0, 100, 90)
        obs = st.text_area("Observaciones")
        
        if st.form_submit_button("Guardar Evaluación"):
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "agente": ag_sel.split(" - ")[0], "puntos": score,
                "evaluador": user['username'], "fecha": datetime.now().strftime("%d/%m/%Y"),
                "observaciones": obs
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success("✅ Evaluación guardada")

elif choice == "Gestión Campañas":
    st.header("📁 Gestión de Campañas")
    df_c = get_data("campañas")
    c1, c2 = st.columns([1, 2])
    with c1:
        nc = st.text_input("Nombre de Campaña")
        if st.button("🚀 Crear"):
            requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
            st.rerun()
    with c2:
        st.dataframe(df_c, use_container_width=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    col_l, col_r = st.columns([1.2, 2])
    
    with col_l:
        with st.container(border=True):
            st.subheader("Formulario")
            id_u = st.text_input("ID Usuario")
            nom_u = st.text_input("Nombre Completo")
            pass_u = st.text_input("Password")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            camp_u = st.text_input("Campaña")
            
            b1, b2 = st.columns(2)
            if b1.button("🚀 Registrar"):
                p = {"target_sheet":"usuarios","action":"create","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u}
                requests.post(URL_SCRIPT, json=p); st.rerun()
            if b2.button("📝 Modificar"):
                p = {"target_sheet":"usuarios","action":"update","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u}
                requests.post(URL_SCRIPT, json=p); st.rerun()
        
        st.divider()
        if not df_u.empty:
            u_sel = st.selectbox("Seleccionar para acción:", df_u.iloc[:,0].tolist())
            a1, a2 = st.columns(2)
            if a1.button("🚫 Inhabilitar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"status","user":u_sel,"val":"Inactivo"}); st.rerun()
            if a2.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel}); st.rerun()

    with col_r:
        st.subheader("Base de Datos")
        st.dataframe(df_u, use_container_width=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_sc = get_data("scorecards")
    with st.container(border=True):
        preg = st.text_input("Criterio de Evaluación")
        if st.button("➕ Añadir"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","pregunta":preg})
            st.rerun()
    st.dataframe(df_sc, use_container_width=True)
