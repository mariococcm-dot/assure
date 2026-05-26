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
    # Claridad para el usuario: Se pide el ID
    u_log = st.text_input("ID de Empleado (Usuario)") 
    p_log = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        df_db = get_data("usuarios")
        if not df_db.empty:
            # Validamos contra la columna 'username' que ahora debe contener IDs
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

# --- 4. BARRA LATERAL ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
# Aquí usamos el Nombre para personalizar, pero el ID queda registrado internamente
st.sidebar.write(f"Bienvenido: **{user_data['nombre']}**")
st.sidebar.write(f"ID: `{user_data['id']}`")

if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios"]
else:
    menu = ["Dashboard", "Evaluador"]

choice = st.sidebar.selectbox("Menú", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 5. MÓDULOS ---

if choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data("usuarios")
    
    col_u1, col_u2 = st.columns([1, 2])
    with col_u1:
        st.subheader("Registrar Nuevo")
        with st.form("nuevo_usuario"):
            new_id = st.text_input("ID de Empleado (Clave única)")
            new_name = st.text_input("Nombre Completo (Personalización)")
            new_pass = st.text_input("Password", type="password")
            new_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            
            df_camps = get_data("campañas")
            lista_c = df_camps['campaña'].unique().tolist() if not df_camps.empty else ["Todas"]
            new_camp = st.selectbox("Campaña", lista_c)
            
            if st.form_submit_button("🚀 Registrar"):
                if new_id and new_name and new_pass:
                    payload = {
                        "target_sheet": "usuarios", 
                        "action": "create", 
                        "username": new_id,   # ID va a la columna técnica
                        "nombre": new_name,   # Nombre va a la columna visual
                        "password": new_pass, 
                        "rol": new_rol, 
                        "campaña": new_camp
                    }
                    requests.post(URL_SCRIPT, json=payload)
                    st.success(f"Usuario {new_id} creado")
                    st.rerun()
                else:
                    st.warning("Completa todos los campos")

    with col_u2:
        st.subheader("Lista de Personal Activo")
        if not df_u.empty:
            # Mostramos nombre e ID juntos para control
            st.dataframe(df_u[['username', 'nombre', 'rol', 'campaña']], use_container_width=True, hide_index=True)

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_base = get_data("usuarios")
    
    with st.form("eval"):
        # El evaluador busca por nombre, pero el sistema guardará el ID
        agentes_df = df_base[df_base['rol'] == 'Agente']
        # Creamos una lista tipo "ID - Nombre" para que el evaluador no se pierda
        lista_agentes = (agentes_df['username'].astype(str) + " - " + agentes_df['nombre'].astype(str)).tolist()
        
        ag_seleccionado = st.selectbox("Seleccionar Agente", lista_agentes)
        score = st.slider("Calidad (%)", 0, 100, 85)
        
        if st.form_submit_button("Guardar"):
            id_real = ag_seleccionado.split(" - ")[0] # Extraemos solo el ID
            payload = {
                "target_sheet": "evaluaciones",
                "agente_id": id_real,
                "puntos": score,
                "fecha": datetime.now().strftime("%Y-%m-%d")
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success(f"Evaluación guardada para el ID: {id_real}")

else:
    st.write(f"Módulo {choice} en mantenimiento.")
