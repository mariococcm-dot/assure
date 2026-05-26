import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# SUSTITUYE CON TU URL DE DESPLIEGUE (Deployment ID)
URL_SCRIPT = "TU_URL_DE_APPS_SCRIPT_AQUI" 

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

if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"]
else:
    menu = ["Dashboard", "Evaluador"]

choice = st.sidebar.selectbox("Menú Principal", menu)
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

# --- MÓDULO: DASHBOARD ---
if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    st.info("Visualización de KPIs y desempeño por campaña.")
    
    df_evals = get_data("evaluaciones")
    if not df_evals.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Evaluaciones", len(df_evals))
        col2.metric("Promedio General", f"{round(df_evals['puntos_obtenidos'].mean(), 2)}%")
        st.divider()
        st.subheader("Últimas Evaluaciones")
        st.dataframe(df_evals.tail(10), use_container_width=True)
    else:
        st.warning("Aún no hay datos de evaluaciones para mostrar.")

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
            
            # Filtro de agentes
            ags = df_u[(df_u['rol'] == 'Agente') & (df_u['campaña'] == c_s)]
            ag_list = (ags['username'].astype(str) + " - " + ags['nombre'].astype(str)).tolist()
            ag_s = col2.selectbox("Seleccionar Agente", ag_list) if ag_list else col2.text_input("ID Agente (Manual)")
            
            score = st.slider("Calidad (%)", 0, 100, 85)
            obs = st.text_area("Observaciones de la llamada / interacción")
            
            if st.form_submit_button("Guardar Evaluación"):
                id_agente = ag_s.split(" - ")[0] if " - " in ag_s else ag_s
                payload = {
                    "target_sheet": "evaluaciones", 
                    "action": "create",
                    "agente": id_agente, 
                    "puntos_obtenidos": score, 
                    "evaluador": user_data['username'], 
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "observaciones": obs
                }
                requests.post(URL_SCRIPT, json=payload)
                st.success(f"✅ Evaluación registrada para {id_agente}")

# --- MÓDULO: GESTIÓN CAMPAÑAS ---
elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        with st.container(border=True):
            st.subheader("Nueva Campaña")
            nc = st.text_input("Nombre de la Campaña")
            if st.button("🚀 Crear"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "create", "nombre": nc})
                st.rerun()
        
        st.divider()
        if not df_c.empty:
            c_sel = st.selectbox("Seleccionar Campaña:", df_c['campaña'].tolist())
            if st.button("🗑️ Eliminar Campaña"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "delete", "nombre": c_sel})
                st.rerun()
    with col_r:
        st.subheader("Campañas Activas")
        st.dataframe(df_c, use_container_width=True, hide_index=True)

# --- MÓDULO: GESTIÓN USUARIOS ---
elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    col_l, col_r = st.columns([1.2, 2])
    
    with col_l:
        st.subheader("Formulario de Usuario")
        with st.container(border=True):
            id_u = st.text_input("ID Empleado")
            nom_u = st.text_input("Nombre Completo")
            pass_u = st.text_input("Password", type="password")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            df_c_list = get_data("campañas")
            list_c = df_c_list['campaña'].unique().tolist() if not df_c_list.empty else ["Ninguna"]
            camp_u = st.selectbox("Campaña Asignada", list_c)
            
            b1, b2 = st.columns(2)
            if b1.button("🚀 Registrar"):
                p = {"target_sheet": "usuarios", "action": "create", "username": id_u, "nombre": nom_u, "password": pass_u, "rol": rol_u, "campaña": camp_u}
                requests.post(URL_SCRIPT, json=p); st.rerun()
            if b2.button("📝 Modificar"):
                p = {"target_sheet": "usuarios", "action": "update", "username": id_u, "nombre": nom_u, "password": pass_u, "rol": rol_u, "campaña": camp_u}
                requests.post(URL_SCRIPT, json=p); st.rerun()

        st.divider()
        st.subheader("Acciones Rápidas")
        if not df_u.empty:
            u_sel = st.selectbox("Usuario:", df_u['username'].tolist())
            c1, c2 = st.columns(2)
            if c1.button("🚫 Inhabilitar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "status", "user": u_sel, "val": "Inactivo"}); st.rerun()
            if c2.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "delete", "user": u_sel}); st.rerun()

    with col_r:
        st.subheader("Base de Usuarios")
        st.dataframe(df_u[['username', 'nombre', 'rol', 'campaña', 'estado']], use_container_width=True, hide_index=True)

# --- MÓDULO: CONFIG SCORECARDS ---
elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_sc = get_data("scorecards")
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        st.subheader("Nuevo Criterio")
        with st.container(border=True):
            df_c_sc = get_data("campañas")
            c_sel_sc = st.selectbox("Campaña vinculada", df_c_sc['campaña'].tolist() if not df_c_sc.empty else [])
            f_p = st.text_input("Pregunta de Evaluación")
            f_pts = st.number_input("Peso/Puntos", 1, 100, 10)
            f_t = st.selectbox("Tipo de respuesta", ["Escala (0-100)", "Binaria (Si/No)"])
            
            if st.button("➕ Añadir a Scorecard"):
                p = {"target_sheet": "scorecards", "action": "create", "area": c_sel_sc, "pregunta": f_p, "puntos": f_pts, "tipo": f_t}
                requests.post(URL_SCRIPT, json=p); st.rerun()
    
    with col_r:
        st.subheader("Criterios Registrados")
        st.dataframe(df_sc, use_container_width=True, hide_index=True)
