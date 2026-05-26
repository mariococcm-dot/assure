import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

# --- 2. CONEXIÓN A GOOGLE SHEET ---
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
        st.error(f"Error al leer hoja {nombre_hoja}: {e}")
        return pd.DataFrame()

# --- 3. LÓGICA DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("ID de Empleado (Usuario)") 
    p_log = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        df_db = get_data("usuarios")
        if not df_db.empty:
            user_row = df_db[(df_db['username'].astype(str) == str(u_log)) & (df_db['password'].astype(str) == str(p_log))]
            if not user_row.empty:
                user = user_row.iloc[0]
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {
                    "id": user['username'], 
                    "nombre": user['nombre'] if 'nombre' in df_db.columns else user['username'],
                    "rol": user['rol'], "campaña": user['campaña']
                }
                st.rerun()
            else:
                st.error("❌ ID o contraseña incorrectos")
    st.stop()

# --- 4. BARRA LATERAL ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user_data['nombre']}**")
if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"]
else:
    menu = ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú", menu)
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 5. MÓDULOS ---

# --- GESTIÓN USUARIOS (ESTRUCTURA VISUAL SEGÚN IMAGEN) ---
if choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.markdown("### Datos de Usuario")
        with st.container(border=True):
            new_id = st.text_input("ID Empleado")
            new_name = st.text_input("Nombre Completo")
            new_pass = st.text_input("Password", type="password")
            new_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            df_c = get_data("campañas")
            lista_c = df_c['campaña'].unique().tolist() if not df_c.empty else ["Todas"]
            new_camp = st.selectbox("Campaña", lista_c)
            
            if st.button("Registrar"):
                payload = {"target_sheet": "usuarios", "action": "create", "username": new_id, "nombre": new_name, "password": new_pass, "rol": new_rol, "campaña": new_camp}
                requests.post(URL_SCRIPT, json=payload)
                st.success("Usuario Registrado"); st.rerun()
        
        st.markdown("---")
        st.markdown("### Acciones Rápidas")
        if not df_u.empty:
            u_sel = st.selectbox("Seleccionar para acción:", df_u['username'].tolist())
            c1, c2, c3 = st.columns(3)
            if c1.button("✅ Hab."):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "status", "user": u_sel, "val": "Activo"}); st.rerun()
            if c2.button("🚫 Des."):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "status", "user": u_sel, "val": "Inactivo"}); st.rerun()
            if c3.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "delete", "user": u_sel}); st.rerun()

    with col_right:
        st.markdown("### Lista de Personal")
        if not df_u.empty:
            st.dataframe(df_u[['username', 'nombre', 'rol', 'campaña']], use_container_width=True, hide_index=True)

# --- GESTIÓN CAMPAÑAS (ESTRUCTURA VISUAL SEGÚN IMAGEN) ---
elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.markdown("### Nueva Campaña")
        with st.container(border=True):
            nc = st.text_input("Nombre de Campaña")
            if st.button("Crear Campaña"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "create", "nombre": nc})
                st.success("Creada"); st.rerun()
        
        st.markdown("---")
        st.markdown("### Acciones")
        if not df_c.empty:
            c_sel = st.selectbox("Seleccionar Campaña:", df_c['campaña'].unique().tolist())
            nuevo_n = st.text_input("Nuevo nombre (opcional)")
            ca1, ca2, ca3 = st.columns(3)
            if ca1.button("📝 Renom."):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "update", "old": c_sel, "new": nuevo_n}); st.rerun()
            if ca2.button("🚫 Desh."):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "status", "nombre": c_sel, "val": "Inactivo"}); st.rerun()
            if ca3.button("🗑️ Elim."):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "delete", "nombre": c_sel}); st.rerun()

    with col_right:
        st.markdown("### Campañas en Sistema")
        if not df_c.empty:
            st.dataframe(df_c[['campaña', 'estado']], use_container_width=True, hide_index=True)

# --- EVALUADOR ---
elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_base = get_data("usuarios")
    df_camps = get_data("campañas")
    if not df_camps.empty:
        camps_reales = df_camps[df_camps['estado'] == 'Activo']['campaña'].tolist()
        col1, col2 = st.columns(2)
        with st.form("eval_form"):
            a_sel = col1.selectbox("Campaña", camps_reales)
            agentes_df = df_base[(df_base['rol'] == 'Agente') & (df_base['campaña'] == a_sel)]
            lista_agentes = (agentes_df['username'].astype(str) + " - " + agentes_df['nombre'].astype(str)).tolist()
            ag_sel = col2.selectbox("Seleccionar Agente", lista_agentes) if lista_agentes else col2.text_input("ID Agente (Manual)")
            score = st.slider("Calidad (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            if st.form_submit_button("Guardar Evaluación"):
                id_real = ag_sel.split(" - ")[0] if " - " in ag_sel else ag_sel
                payload = {"target_sheet": "evaluaciones", "agente_id": id_real, "evaluador": user_data['id'], "puntos": score, "fecha": datetime.now().strftime("%Y-%m-%d"), "observaciones": obs}
                requests.post(URL_SCRIPT, json=payload); st.success("✅ Guardado")

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_camps = get_data("campañas")
    if not df_camps.empty:
        c_act = df_camps[df_camps['estado'] == 'Activo']['campaña'].tolist()
        col_l, col_r = st.columns([1, 2])
        with col_l:
            with st.container(border=True):
                f_c = st.selectbox("Campaña", c_act)
                f_p = st.text_input("Criterio / Pregunta")
                f_t = st.selectbox("Tipo", ["Escala (Slider)", "Sí / No"])
                f_pts = st.number_input("Puntos Máximos", 1, 100, 10)
                if st.button("Añadir Criterio"):
                    payload = {"target_sheet": "scorecards", "action": "create", "area": f_c, "pregunta": f_p, "puntos": f_pts, "tipo": f_t}
                    requests.post(URL_SCRIPT, json=payload); st.rerun()
        with col_r:
            df_sc = get_data("scorecards")
            if not df_sc.empty:
                st.dataframe(df_sc, use_container_width=True, hide_index=True)

else:
    st.header("📊 Dashboard")
    st.info("Cargando analítica...")
