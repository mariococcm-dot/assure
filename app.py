import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

# --- 2. CONEXIÓN A GOOGLE SHEET (LECTURA) ---
def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        nombre_hoja_web = quote(nombre_hoja)
        # Agregamos tq? para asegurar que Google Sheets envíe los datos limpios
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={nombre_hoja_web}&cache={datetime.now().timestamp()}"
        
        # Cargamos el CSV
        df = pd.read_csv(url_final)
        
        # --- LIMPIEZA CRÍTICA ---
        if not df.empty:
            # 1. Eliminamos columnas sin nombre (Unamed)
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            # 2. Convertimos encabezados a minúsculas y quitamos espacios
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
    u_log = st.text_input("Usuario")
    p_log = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        df_db = get_data("usuarios")
        
        if not df_db.empty:
            # Buscamos si existe la columna que contenga 'user' o 'pass' por si hay variaciones
            col_user = [c for c in df_db.columns if 'user' in c]
            col_pass = [c for c in df_db.columns if 'pass' in c]
            
            if col_user and col_pass:
                u_col, p_col = col_user[0], col_pass[0]
                user_row = df_db[(df_db[u_col].astype(str) == u_log) & 
                                 (df_db[p_col].astype(str) == p_log)]
                
                if not user_row.empty:
                    user = user_row.iloc[0]
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {
                        "user": user[u_col], 
                        "rol": user['rol'] if 'rol' in df_db.columns else 'Agente', 
                        "campaña": user['campaña'] if 'campaña' in df_db.columns else 'Todas'
                    }
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.error(f"❌ Estructura incorrecta. Columnas: {list(df_db.columns)}")
        else:
            st.error("❌ No se pudo leer la base de datos.")
    st.stop()

# --- 4. BARRA LATERAL ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Usuario: **{user_data['user']}**")

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

# --- 5. MÓDULOS PRINCIPALES ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    st.info("Módulo de Dashboard activo")

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_base = get_data("usuarios")
    df_camp_list = get_data("campañas")
    
    if df_camp_list.empty:
        st.warning("No hay campañas configuradas.")
    else:
        camps_reales = df_camp_list[df_camp_list['estado'] == 'Activo']['campaña'].tolist()
        with st.form("form_eval"):
            c1, c2 = st.columns(2)
            a_sel = c1.selectbox("Campaña", camps_reales)
            ags = df_base[(df_base['rol'].str.contains('Agente', case=False, na=False)) & (df_base['campaña'] == a_sel)]['username'].tolist()
            ag_sel = c2.selectbox("Agente", ags) if ags else c2.text_input("Nombre Agente (Manual)")
            
            f_ev = st.date_input("Fecha de Evento", datetime.now())
            t_eval = st.selectbox("Evaluado por:", ["Calidad", "Operaciones"])
            score_val = st.slider("Calidad (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar"):
                payload = {
                    "target_sheet": "evaluaciones",
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fecha_evento": str(f_ev),
                    "area": a_sel,
                    "evaluador": user_data['user'],
                    "agente": ag_sel,
                    "puntos_obtenidos": score_val,
                    "observaciones": obs
                }
                res = requests.post(URL_SCRIPT, json=payload)
                st.success("✅ Enviado")

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
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    col_u1, col_u2 = st.columns([1, 2])
    
    with col_u1:
        modo_u = st.radio("Acción", ["Nuevo", "Editar/Borrar"])
        if modo_u == "Nuevo":
            nu = st.text_input("Username")
            np = st.text_input("Password", type="password")
            nr = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            df_camps_aux = get_data("campañas")
            lista_c = df_camps_aux[df_camps_aux['estado'] == 'Activo']['campaña'].unique().tolist() if not df_camps_aux.empty else ["Todas"]
            nc_u = st.selectbox("Asignar a Campaña", lista_c)
            if st.button("🚀 Registrar"):
                payload = {"target_sheet": "usuarios", "action": "create", "username": nu, "password": np, "rol": nr, "campaña": nc_u}
                requests.post(URL_SCRIPT, json=payload)
                st.success("Registrado"); st.rerun()
        else:
            st.warning("Seleccione un usuario de la tabla para editar (próximamente)")

    with col_u2:
        st.subheader("Lista de Personal")
        st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    st.write("Módulo en construcción")
