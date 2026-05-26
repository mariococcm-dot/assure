import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote 

st.set_page_config(page_title="QualityScore Enterprise", layout="wide")
URL_SCRIPT = "TU_URL_DE_APPS_SCRIPT_AQUI" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final)
        if not df.empty: df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except: return pd.DataFrame()

# --- LOGIN ---
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario (ID)")
    p_log = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        df = get_data("usuarios")
        if not df.empty:
            df['username'] = df['username'].astype(str).str.strip()
            df['password'] = df['password'].astype(str).str.strip()
            user = df[(df['username'] == u_log) & (df['password'] == p_log)]
            if not user.empty:
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("❌ Datos incorrectos")
    st.stop()

# --- MENÚ ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Hola, **{user_data['nombre']}**")
menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user_data['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Ir a:", menu)

# --- MÓDULO USUARIOS ---
if choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    col1, col2 = st.columns([1.2, 2])
    
    with col1:
        with st.container(border=True):
            st.markdown("### Datos del Usuario")
            id_u = st.text_input("ID Empleado (No editable para Modificar)")
            nom_u = st.text_input("Nombre Completo")
            pass_u = st.text_input("Password", type="password")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            camps = get_data("campañas")
            camp_u = st.selectbox("Campaña", camps['campaña'].tolist() if not camps.empty else ["Todas"])
            
            btn1, btn2 = st.columns(2)
            if btn1.button("🚀 Registrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u})
                st.rerun()
            if btn2.button("📝 Modificar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u})
                st.rerun()
        
        st.markdown("---")
        if not df_u.empty:
            u_sel = st.selectbox("Seleccionar Usuario:", df_u['username'].tolist())
            act1, act2 = st.columns(2)
            if act1.button("🚫 Inhabilitar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"status","user":u_sel,"val":"Inactivo"})
                st.rerun()
            if act2.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel})
                st.rerun()

    with col2:
        st.dataframe(df_u, use_container_width=True, hide_index=True)

# --- MÓDULO CAMPAÑAS ---
elif choice == "Gestión Campañas":
    st.header("📁 Gestión de Campañas")
    df_c = get_data("campañas")
    c_l, c_r = st.columns([1, 2])
    with c_l:
        nc = st.text_input("Nombre de Campaña")
        if st.button("Crear"):
            requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc}); st.rerun()
        st.markdown("---")
        if not df_c.empty:
            sel_c = st.selectbox("Campaña:", df_c['campaña'].tolist())
            if st.button("🗑️ Eliminar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"delete","nombre":sel_c}); st.rerun()
    with c_r:
        st.dataframe(df_c, use_container_width=True, hide_index=True)

# (Otros módulos como Evaluador y Dashboard irían aquí siguiendo la misma lógica)
