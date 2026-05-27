import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN (IGUAL AL WEB) ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final, on_bad_lines='skip')
        if not df.empty:
            df.columns = [str(c).strip().split('\n')[0].lower() for c in df.columns]
            df = df.dropna(subset=[df.columns[0]])
        return df
    except:
        return pd.DataFrame()

# --- 2. LOGIN (IGUAL AL WEB) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"username": "admin", "nombre": "Administrador", "rol": "Administrador"}
            st.rerun()
        
        df_db = get_data("usuarios")
        if not df_db.empty:
            # Login usando la lógica del archivo WEB (iloc[0] y iloc[2])
            encontrado = False
            for _, row in df_db.iterrows():
                if str(row.iloc[0]).strip() == u_log and str(row.iloc[2]).strip() == p_log:
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {
                        "username": str(row.iloc[0]).strip(),
                        "nombre": str(row.iloc[1]).strip(),
                        "rol": str(row.iloc[3]).strip()
                    }
                    encontrado = True
                    break
            if encontrado: st.rerun()
            else: st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# --- 3. BARRA LATERAL (IGUAL AL WEB + NOMBRES LOCAL) ---
user = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"ID: **{user['username']}**")
st.sidebar.write(f"Nombre: **{user['nombre']}**")

menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS (ESTRUCTURA WEB CON LÓGICA LOCAL) ---

if choice == "Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        # Lógica de cálculo del LOCAL adaptada a las columnas del WEB
        df_ev['puntos_obtenidos'] = pd.to_numeric(df_ev['puntos_obtenidos'], errors='coerce').fillna(0)
        df_ev['puntos_maximos'] = pd.to_numeric(df_ev['puntos_maximos'], errors='coerce').fillna(1)
        df_ev['% score'] = (df_ev['puntos_obtenidos'] / df_ev['puntos_maximos']) * 100
        
        col1, col2 = st.columns(2)
        col1.metric("Promedio General", f"{df_ev['% score'].mean():.1f}%")
        col2.metric("Total Evaluaciones", len(df_ev))
        
        # Gráfico Plotly del LOCAL
        fig = px.bar(df_ev.groupby('agente')['% score'].mean().reset_index(), 
                     x='agente', y='% score', color='% score', text_auto='.1f')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("No hay datos.")

elif choice == "Evaluador":
    st.header("📝 Módulo de Evaluación")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    df_sc = get_data("scorecards") # Traemos scorecards para la lógica local
    
    with st.form("form_eval"):
        c_list = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
        c_sel = st.selectbox("Campaña", c_list)
        
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente']
        ag_list = (ags.iloc[:,0].astype(str) + " - " + ags.iloc[:,1].astype(str)).tolist()
        ag_sel = st.selectbox("Agente", ag_list if ag_list else ["Sin agentes"])
        
        # Scorecard Dinámico del LOCAL
        preguntas = df_sc[df_sc.iloc[:,0] == c_sel] if not df_sc.empty else pd.DataFrame()
        respuestas = {}
        for _, row in preguntas.iterrows():
            respuestas[row.iloc[1]] = st.select_slider(f"{row.iloc[1]} (Max: {row.iloc[2]})", options=[0, int(row.iloc[2])], value=int(row.iloc[2]))
        
        obs = st.text_area("Observaciones")
        
        if st.form_submit_button("Guardar Evaluación"):
            p_ob = sum(respuestas.values())
            p_mx = sum(preguntas.iloc[:,2]) if not preguntas.empty else 100
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "agente": ag_sel.split(" - ")[0], "puntos_obtenidos": p_ob, "puntos_maximos": p_mx,
                "evaluador": user['username'], "observaciones": obs, "campaña": c_sel
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success("✅ Evaluación registrada")

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1.2, 2])
    
    with col_l:
        u_id = st.text_input("ID / Username")
        u_nom = st.text_input("Nombre Completo")
        u_pass = st.text_input("Password")
        u_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
        u_camp = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["Todas"])
        
        # Botones del WEB (Registrar y Modificar)
        b1, b2 = st.columns(2)
        if b1.button("🚀 Registrar"):
            p = {"target_sheet":"usuarios","action":"create","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp,"estado":"Activo"}
            requests.post(URL_SCRIPT, json=p); st.rerun()
        if b2.button("📝 Modificar"):
            p = {"target_sheet":"usuarios","action":"update","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp}
            requests.post(URL_SCRIPT, json=p); st.rerun()

    with col_r:
        st.dataframe(df_u, use_container_width=True, hide_index=True)

# Módulos faltantes (Campañas y Scorecards) exactamente como en el WEB
elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    nc = st.text_input("Nombre de la Campaña")
    if st.button("🚀 Crear Campaña"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(df_c, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_sc = get_data("scorecards")
    df_c = get_data("campañas")
    with st.container(border=True):
        c_sc = st.selectbox("Campaña vinculada", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        preg_sc = st.text_input("Pregunta / Criterio")
        pts_sc = st.number_input("Puntos", 1, 100, 10)
        if st.button("➕ Añadir Criterio"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_sc, "pregunta":preg_sc, "puntos":pts_sc})
            st.rerun()
    st.dataframe(df_sc, use_container_width=True, hide_index=True)
