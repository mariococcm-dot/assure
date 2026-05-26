import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# ⚠️ ASEGÚRATE DE QUE ESTA URL SEA LA CORRECTA DE TU APPS SCRIPT
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final)
        return df
    except:
        return pd.DataFrame()

# --- 2. LÓGICA DE LOGIN (SEGURA POR POSICIÓN DE COLUMNA) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("ID de Empleado").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        df_db = get_data("usuarios")
        if not df_db.empty:
            encontrado = False
            for _, row in df_db.iterrows():
                # Comparamos Columna A (0) y Columna C (2) sin importar el nombre del encabezado
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

# --- 3. BARRA LATERAL ---
user = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user['nombre']}**")
menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú", menu)
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        st.metric("Total Evaluaciones", len(df_ev))
        st.dataframe(df_ev.tail(10), use_container_width=True)
    else: st.info("No hay datos para mostrar.")

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    with st.form("eval_form"):
        c_sel = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        ag_list = df_u[df_u.iloc[:,3] == 'Agente'] # Filtrar por columna Rol (índice 3)
        ag_sel = st.selectbox("Agente", (ag_list.iloc[:,0] + " - " + ag_list.iloc[:,1]).tolist() if not ag_list.empty else ["No hay agentes"])
        score = st.slider("Calidad (%)", 0, 100, 85)
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Guardar"):
            id_ag = ag_sel.split(" - ")[0]
            requests.post(URL_SCRIPT, json={"target_sheet":"evaluaciones","action":"create","agente":id_ag,"puntos":score,"evaluador":user['username'],"fecha":datetime.now().strftime("%Y-%m-%d"),"observaciones":obs})
            st.success("Guardado correctamente")

elif choice == "Gestión Campañas":
    st.header("📁 Gestión de Campañas")
    df_c = get_data("campañas")
    col1, col2 = st.columns([1, 2])
    with col1:
        nc = st.text_input("Nombre Campaña")
        if st.button("🚀 Crear"):
            requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc}); st.rerun()
        if not df_c.empty:
            sel_c = st.selectbox("Campaña a borrar:", df_c.iloc[:,0].tolist())
            if st.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"delete","nombre":sel_c}); st.rerun()
    with col2: st.dataframe(df_c, use_container_width=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    col_l, col_r = st.columns([1.2, 2])
    with col_l:
        with st.container(border=True):
            id_u = st.text_input("ID")
            nom_u = st.text_input("Nombre")
            pass_u = st.text_input("Pass")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            camp_u = st.text_input("Campaña")
            b1, b2 = st.columns(2)
            if b1.button("🚀 Registrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u}); st.rerun()
            if b2.button("📝 Modificar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u}); st.rerun()
        if not df_u.empty:
            st.divider()
            u_sel = st.selectbox("Acción para:", df_u.iloc[:,0].tolist())
            c1, c2 = st.columns(2)
            if c1.button("🚫 Inh."):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"status","user":u_sel,"val":"Inactivo"}); st.rerun()
            if c2.button("🗑️ Del."):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel}); st.rerun()
    with col_r: st.dataframe(df_u, use_container_width=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Scorecards")
    df_sc = get_data("scorecards")
    with st.container(border=True):
        f_p = st.text_input("Pregunta")
        if st.button("Añadir"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","pregunta":f_p})
            st.rerun()
    st.dataframe(df_sc, use_container_width=True)
