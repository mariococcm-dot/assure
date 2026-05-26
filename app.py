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
        # Limpiar nombres de columnas para evitar errores de espacios
        if not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# --- 2. LÓGICA DE SESIÓN (LOGIN) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("ID de Empleado").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        # Login Administrativo Fijo
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"username": "admin", "nombre": "Admin Maestro", "rol": "Administrador"}
            st.rerun()
        
        # Login desde Excel
        df_db = get_data("usuarios")
        if not df_db.empty:
            encontrado = False
            for _, row in df_db.iterrows():
                if str(row.iloc[0]).strip() == u_log and str(row.iloc[2]).strip() == p_log:
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {
                        "username": str(row.iloc[0]),
                        "nombre": str(row.iloc[1]),
                        "rol": str(row.iloc[3]),
                        "campaña": str(row.iloc[4])
                    }
                    encontrado = True
                    break
            if encontrado: st.rerun()
            else: st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 3. INTERFAZ ---
user = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user['nombre']}**")

menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Módulo", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Dashboard")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        st.metric("Total Evaluaciones", len(df_ev))
        st.dataframe(df_ev, use_container_width=True)
    else: st.info("No hay datos.")

elif choice == "Evaluador":
    st.header("📝 Evaluación")
    df_c = get_data("campañas")
    df_u = get_data("usuarios")
    
    with st.form("f_eval"):
        # CARGA DINÁMICA DE CAMPAÑAS
        lista_campanas = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
        c_sel = st.selectbox("Campaña", lista_campanas)
        
        # Filtro de agentes
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente'] if not df_u.empty else pd.DataFrame()
        ag_nombres = (ags.iloc[:,0].astype(str) + " - " + ags.iloc[:,1].astype(str)).tolist() if not ags.empty else []
        ag_sel = st.selectbox("Agente", ag_nombres if ag_nombres else ["Sin agentes"])
        
        score = st.slider("Calidad", 0, 100, 90)
        if st.form_submit_button("Guardar"):
            p = {"target_sheet":"evaluaciones","action":"create","agente":ag_sel.split(" - ")[0],"puntos":score,"evaluador":user['username'],"fecha":datetime.now().strftime("%Y-%m-%d")}
            requests.post(URL_SCRIPT, json=p)
            st.success("Guardado")

elif choice == "Gestión Campañas":
    st.header("📁 Campañas")
    df_c = get_data("campañas")
    c1, c2 = st.columns([1, 2])
    with c1:
        nc = st.text_input("Nombre Campaña")
        if st.button("🚀 Crear"):
            requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc}); st.rerun()
    with c2: st.dataframe(df_c, use_container_width=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas") # Cargamos campañas para el selector
    col_l, col_r = st.columns([1.2, 2])
    
    with col_l:
        with st.container(border=True):
            id_u = st.text_input("ID")
            nom_u = st.text_input("Nombre")
            pass_u = st.text_input("Password")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            
            # CARGA DINÁMICA DE CAMPAÑAS PARA ASIGNAR
            lista_c = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
            camp_u = st.selectbox("Asignar Campaña", lista_c)
            
            b1, b2 = st.columns(2)
            if b1.button("🚀 Registrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u}); st.rerun()
            if b2.button("📝 Modificar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u}); st.rerun()
        
        if not df_u.empty:
            st.divider()
            u_sel = st.selectbox("ID a afectar:", df_u.iloc[:,0].tolist())
            if st.button("🗑️ Borrar Usuario"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel}); st.rerun()

    with col_r: st.dataframe(df_u, use_container_width=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Scorecards")
    df_c = get_data("campañas")
    with st.container(border=True):
        # CARGA DINÁMICA DE CAMPAÑAS PARA SCORECARDS
        lista_cs = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
        c_sc = st.selectbox("Campaña vinculada", lista_cs)
        preg = st.text_input("Pregunta")
        if st.button("➕ Añadir"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_sc,"pregunta":preg})
            st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)
