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
            user_row = df_db[(df_db['username'].astype(str) == str(u_log)) & 
                             (df_db['password'].astype(str) == str(p_log))]
            
            if not user_row.empty:
                user = user_row.iloc[0]
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {
                    "id": user['username'], 
                    "nombre": user['nombre'] if 'nombre' in df_db.columns else user['username'],
                    "rol": user['rol'], 
                    "campaña": user['campaña']
                }
                st.rerun()
            else:
                st.error("❌ ID o contraseña incorrectos")
        else:
            st.error("❌ No se pudo conectar con la base de datos.")
    st.stop()

# --- 4. BARRA LATERAL (MENÚ CORREGIDO) ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user_data['nombre']}**")
st.sidebar.write(f"ID: `{user_data['id']}`")

# RESTAURAMOS "Config Scorecards" EN EL MENÚ DEL ADMINISTRADOR
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

# --- 5. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    st.info("Visualización de resultados generales.")

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_base = get_data("usuarios")
    df_camps = get_data("campañas")
    
    if df_camps.empty:
        st.warning("Debe configurar campañas primero.")
    else:
        camps_reales = df_camps[df_camps['estado'] == 'Activo']['campaña'].tolist()
        with st.form("eval_form"):
            c1, c2 = st.columns(2)
            a_sel = c1.selectbox("Campaña", camps_reales)
            agentes_df = df_base[(df_base['rol'] == 'Agente') & (df_base['campaña'] == a_sel)]
            lista_agentes = (agentes_df['username'].astype(str) + " - " + agentes_df['nombre'].astype(str)).tolist()
            ag_sel = c2.selectbox("Seleccionar Agente", lista_agentes) if lista_agentes else c2.text_input("ID Agente (Manual)")
            
            score = st.slider("Calidad (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar"):
                id_real = ag_sel.split(" - ")[0] if " - " in ag_sel else ag_sel
                payload = {
                    "target_sheet": "evaluaciones",
                    "agente_id": id_real,
                    "evaluador": user_data['id'],
                    "puntos": score,
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                    "observaciones": obs
                }
                requests.post(URL_SCRIPT, json=payload)
                st.success(f"✅ Guardado para ID: {id_real}")

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    col1, col2 = st.columns([1, 2])
    with col1:
        nc = st.text_input("Nombre Nueva Campaña")
        if st.button("🚀 Crear"):
            requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "create", "nombre": nc})
            st.rerun()
    with col2:
        st.dataframe(df_c, use_container_width=True, hide_index=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data("usuarios")
    col_u1, col_u2 = st.columns([1, 2])
    with col_u1:
        with st.form("nuevo_u"):
            new_id = st.text_input("ID Empleado")
            new_name = st.text_input("Nombre Completo")
            new_pass = st.text_input("Password", type="password")
            new_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            df_c = get_data("campañas")
            lista_c = df_c['campaña'].unique().tolist() if not df_c.empty else ["Todas"]
            new_camp = st.selectbox("Campaña", lista_c)
            if st.form_submit_button("Registrar"):
                payload = {"target_sheet": "usuarios", "action": "create", "username": new_id, "nombre": new_name, "password": new_pass, "rol": new_rol, "campaña": new_camp}
                requests.post(URL_SCRIPT, json=payload)
                st.success("Usuario creado"); st.rerun()
    with col_u2:
        st.dataframe(df_u[['username', 'nombre', 'rol', 'campaña']], use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    # Este bloque renderiza la configuración de preguntas
    df_camps = get_data("campañas")
    if not df_camps.empty:
        c_act = df_camps[df_camps['estado'] == 'Activo']['campaña'].tolist()
        with st.form("config_sc"):
            f_c = st.selectbox("Campaña", c_act)
            f_p = st.text_input("Criterio / Pregunta")
            f_t = st.selectbox("Tipo", ["Escala (Slider)", "Sí / No"])
            f_pts = st.number_input("Puntos Máximos", 1, 100, 10)
            if st.form_submit_button("Añadir Criterio"):
                payload = {"target_sheet": "scorecards", "action": "create", "area": f_c, "pregunta": f_p, "puntos": f_pts, "tipo": f_t}
                requests.post(URL_SCRIPT, json=payload)
                st.success("Criterio añadido"); st.rerun()
    
    st.markdown("---")
    df_sc = get_data("scorecards")
    if not df_sc.empty:
        st.subheader("Criterios Actuales")
        st.dataframe(df_sc, use_container_width=True, hide_index=True)
