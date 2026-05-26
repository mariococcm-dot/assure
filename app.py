import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
from urllib.parse import quote # Esto permite traducir la "ñ" a código web

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

# URL DE TU GOOGLE APPS SCRIPT (Copia aquí la URL que generaste en Apps Script)
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

# --- 2. CONEXIÓN A GOOGLE SHEET (LECTURA) ---
def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        nombre_hoja_web = quote(nombre_hoja)
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={nombre_hoja_web}&cache={datetime.now().timestamp()}"
        
        df = pd.read_csv(url_final)
        
        # --- LIMPIEZA TOTAL DE COLUMNAS ---
        # Esto convierte 'Username ' o 'USERNAME' en 'username' automáticamente
        df.columns = df.columns.str.strip().str.lower()
        
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
        df_db = get_data()
        if not df_db.empty:
            user_row = df_db[(df_db['username'].astype(str) == u_log) & (df_db['password'].astype(str) == p_log)]
            if not user_row.empty:
                user = user_row.iloc[0]
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {"user": user['username'], "rol": user['rol'], "campaña": user['campaña']}
                st.rerun()
            else: st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 4. BARRA LATERAL ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Usuario: **{user_data['user']}**")
st.sidebar.write(f"Rol: **{user_data['rol']}**")

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

# --- MÓDULO 1: DASHBOARD ---
if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_dash = get_data()
    if not df_dash.empty:
        camps_dash = ["Ver Todas"] + df_dash['campaña'].unique().tolist()
        sel_camp = st.selectbox("Filtrar por Campaña:", camps_dash)
        st.info(f"Mostrando datos reales para: {sel_camp}")

# --- MÓDULO 2: EVALUADOR ---
elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_base = get_data()
    camps_reales = df_base['campaña'].unique().tolist() if not df_base.empty else []
    
    if not camps_reales:
        st.warning("No hay campañas configuradas.")
    else:
        with st.form("form_eval"):
            c1, c2 = st.columns(2)
            a_sel = c1.selectbox("Campaña", camps_reales)
            ags = df_base[(df_base['rol'] == 'Agente') & (df_base['campaña'] == a_sel)]['username'].tolist()
            ag_sel = c2.selectbox("Agente", ags) if ags else c2.text_input("Nombre Agente (Manual)")
            
            f_ev = st.date_input("Fecha de Evento", datetime.now())
            t_eval = st.selectbox("Evaluado por:", ["Calidad", "Operaciones"])
            score_val = st.slider("Calidad de Proceso (%)", 0, 100, 85)
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar Evaluación"):
                payload = {
                    "target_sheet": "evaluaciones",
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "fecha_evento": str(f_ev),
                    "area": a_sel,
                    "evaluador": user_data['user'],
                    "agente": ag_sel,
                    "pregunta": "Evaluación General",
                    "puntos_obtenidos": score_val,
                    "puntos_maximos": 100,
                    "observaciones": obs,
                    "tipo_evaluador": t_eval
                }
                res = requests.post(URL_SCRIPT, json=payload)
                if res.text == "Éxito":
                    st.success("✅ Evaluación guardada")
                    st.balloons()

# --- MÓDULO 3: GESTIÓN CAMPAÑAS (RESTAURADO) ---

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Acciones")
        modo_c = st.radio("Operación:", ["Nueva", "Editar / Acción"])
        
        if modo_c == "Nueva":
            nc = st.text_input("Nombre de Campaña")
            if st.button("🚀 Crear Campaña"):
                res = requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "create", "nombre": nc})
                if res.text == "Éxito": 
                    st.success("Creada"); st.rerun()
        else:
            camp_list = df_c['campaña'].unique().tolist() if not df_c.empty else []
            sel_c = st.selectbox("Seleccionar Campaña:", camp_list)
            nuevo_n = st.text_input("Renombrar a:")
            
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("📝 Modificar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "update", "old": sel_c, "new": nuevo_n})
                st.rerun()
            if b2.button("✅ Hab."):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "status", "nombre": sel_c, "val": "Activo"})
                st.rerun()
            if b3.button("🚫 Desh."):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "status", "nombre": sel_c, "val": "Inactivo"})
                st.rerun()
            if b4.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "campañas", "action": "delete", "nombre": sel_c})
                st.rerun()

    with col2:
        st.subheader("Campañas en Sistema")
        st.dataframe(df_c[['campaña', 'estado']].drop_duplicates() if not df_c.empty else pd.DataFrame())

# --- MÓDULO 4: GESTIÓN USUARIOS (RESTAURADO) ---
elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data()
    
    col_u1, col_u2 = st.columns([1, 2])
    with col_u1:
        st.subheader("Acciones")
        modo_u = st.radio("Operación:", ["Nuevo", "Modificar / Acción"])
            
        if modo_u == "Nuevo":
            nu = st.text_input("Username")
            np = st.text_input("Password", type="password")
            nr = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            
            # --- CORRECCIÓN AQUÍ ---
            # Traemos las campañas directamente de la hoja 'campañas'
            df_camps_aux = get_data("campañas")
            if not df_camps_aux.empty:
                lista_c = df_camps_aux[df_camps_aux['estado'] == 'Activo']['campaña'].unique().tolist()
            else:
                lista_c = ["Todas"]
            
            nc_u = st.selectbox("Asignar a Campaña", lista_c)
            # -----------------------

            if st.button("🚀 Registrar"):
                payload = {
                    "target_sheet": "usuarios", 
                    "action": "create", 
                    "username": nu, 
                    "password": np, 
                    "rol": nr, 
                    "campaña": nc_u
                }
                res = requests.post(URL_SCRIPT, json=payload)
                if res.text == "Éxito":
                    st.success(f"Usuario {nu} registrado con éxito")
                    st.rerun()
        
        else:
            sel_user = st.selectbox("Usuario:", df_u['username'].tolist() if not df_u.empty else [])
            ub1, ub2, ub3 = st.columns(3)
            if ub1.button("✅ Habilitar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "status", "user": sel_user, "val": "Activo"})
                st.rerun()
            if ub2.button("🚫 Deshabilitar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "status", "user": sel_user, "val": "Inactivo"})
                st.rerun()
            if ub3.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet": "usuarios", "action": "delete", "user": sel_user})
                st.rerun()

    with col_u2:
        st.subheader("Lista de Personal")
        st.dataframe(df_u[['username', 'rol', 'campaña', 'estado']] if not df_u.empty else pd.DataFrame())

# --- MÓDULO 5: CONFIG SCORECARDS (ADAPTADO A GOOGLE SHEETS) ---
elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    
    # 1. Obtenemos campañas activas desde la hoja 'campañas'
    df_camps = get_data("campañas")
    if df_camps.empty:
        st.warning("Crea una campaña activa primero.")
    else:
        # Filtramos solo las que están 'Activo'
        c_act = df_camps[df_camps['estado'] == 'Activo']['campaña'].tolist()
        
        if not c_act:
            st.warning("No hay campañas activas en el sistema.")
        else:
            with st.form("sc"):
                f_c = st.selectbox("Campaña", c_act)
                f_p = st.text_input("Criterio")
                f_t = st.selectbox("Tipo", ["Escala (Slider)", "Sí / No"])
                f_pts = st.number_input("Puntos", 1, 100, 10)
                
                if st.form_submit_button("Añadir"):
                    if f_p:
                        # Enviamos a la pestaña 'scorecards' mediante el script
                        payload = {
                            "target_sheet": "scorecards",
                            "action": "create",
                            "area": f_c,
                            "pregunta": f_p,
                            "puntos": f_pts,
                            "tipo": f_t
                        }
                        res = requests.post(URL_SCRIPT, json=payload)
                        if res.text == "Éxito":
                            st.success(f"✅ Criterio '{f_p}' añadido a {f_c}")
                            st.rerun()
                        else:
                            st.error(f"Error al guardar: {res.text}")
                    else:
                        st.error("Por favor escribe un nombre para el criterio.")
    
    st.markdown("---")
    st.subheader("Criterios Configurados")
    # Leemos la pestaña 'scorecards' para mostrar lo que ya existe
    df_sc = get_data("scorecards")
    if not df_sc.empty:
        st.dataframe(df_sc, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay criterios configurados en el Scorecard.")
