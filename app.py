import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise Edition", layout="wide")

# URL de tu Apps Script
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final, on_bad_lines='skip')
        if not df.empty:
            # Normalizamos: todo a minúsculas, sin espacios y quitamos tildes para evitar KeyError
            df.columns = [str(c).strip().lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u') for c in df.columns]
            df = df.dropna(subset=[df.columns[0]])
        return df
    except:
        return pd.DataFrame()

# --- 2. LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"id": "admin", "nombre": "Admin Maestro", "rol": "Administrador"}
            st.rerun()
        
        df_db = get_data("usuarios")
        if not df_db.empty:
            # Buscamos en col 0 (username) y col 2 (password)
            match = df_db[(df_db.iloc[:,0].astype(str) == u_log) & (df_db.iloc[:,2].astype(str) == p_log)]
            if not match.empty:
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {
                    "id": str(match.iloc[0,0]), 
                    "nombre": str(match.iloc[0,1]), 
                    "rol": str(match.iloc[0,3])
                }
                st.rerun()
            else: st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 3. SIDEBAR ---
u_session = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.markdown(f"**ID:** {u_session['id']}\n\n**Nombre:** {u_session['nombre']}")

menu = ["Dashboard", "Evaluador", "Config Scorecards", "Gestión Campañas", "Gestión Usuarios"] if u_session['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Analítica de Desempeño")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        # Usamos nombres normalizados (sin tildes) para evitar el error anterior
        df_ev['fecha_registro'] = pd.to_datetime(df_ev['fecha_registro'], errors='coerce')
        df_ev['score'] = (df_ev['puntos_obtenidos'] / df_ev['puntos_maximos']) * 100
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Promedio General", f"{df_ev['score'].mean():.1f}%")
        m2.metric("Evaluaciones", len(df_ev))
        m3.metric("Agentes", df_ev['agente'].nunique())
        
        fig = px.line(df_ev.sort_values('fecha_registro'), x='fecha_registro', y='score', color='area', title="Evolución de Calidad")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_ev, use_container_width=True, hide_index=True)
    else: st.info("No hay datos.")

elif choice == "Evaluador":
    st.header("📝 Módulo de Evaluación")
    df_sc = get_data("scorecards")
    df_u = get_data("usuarios")
    
    with st.form("eval_form"):
        col1, col2, col3 = st.columns(3)
        # Selectores dinámicos
        areas = df_sc['area'].unique() if not df_sc.empty else ["General"]
        c_sel = col1.selectbox("Campaña", areas)
        
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente']
        ag_sel = col2.selectbox("Agente", ags.iloc[:,0].tolist() if not ags.empty else ["N/A"])
        f_evento = col3.date_input("Fecha del Evento")
        
        st.divider()
        # Generar Scorecard dinámico (Como en el Local)
        pregs = df_sc[df_sc['area'] == c_sel]
        respuestas = {}
        for _, r in pregs.iterrows():
            respuestas[r['pregunta']] = st.select_slider(f"{r['pregunta']} (Max: {r['puntos']})", options=[0, int(r['puntos'])], value=int(r['puntos']))
        
        obs = st.text_area("Observaciones / Feedback")
        if st.form_submit_button("Guardar Evaluación"):
            p_ob = sum(respuestas.values())
            p_mx = sum(pregs['puntos'])
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "fecha_evento": str(f_evento), "area": c_sel, "agente": ag_sel,
                "puntos_obtenidos": p_ob, "puntos_maximos": p_mx,
                "evaluador": u_session['id'], "observaciones": obs
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success(f"✅ Evaluación registrada: {(p_ob/p_mx*100):.1f}%")

elif choice == "Gestión Campañas":
    st.header("📁 Gestión de Campañas")
    df_c = get_data("campañas")
    with st.container(border=True):
        nc = st.text_input("Nombre de la Campaña")
        if st.button("🚀 Crear"):
            requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
            st.rerun()
    st.dataframe(df_c, use_container_width=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        with st.form("user_form"):
            uid = st.text_input("ID Usuario")
            unom = st.text_input("Nombre Completo")
            upass = st.text_input("Contraseña")
            urol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            ucamp = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["Todas"])
            
            c1, c2 = st.columns(2)
            reg = c1.form_submit_button("Registrar")
            mod = c2.form_submit_button("Modificar")
            
            if reg:
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":uid,"nombre":unom,"password":upass,"rol":urol,"campaña":ucamp,"estado":"Activo"})
                st.rerun()
            if mod:
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":uid,"nombre":unom,"password":upass,"rol":urol,"campaña":ucamp})
                st.rerun()
        
        st.divider()
        u_del = st.selectbox("ID para Eliminar", df_u.iloc[:,0].tolist() if not df_u.empty else [])
        if st.button("🗑️ Eliminar Usuario"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_del})
            st.rerun()

    with col_r: st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_c = get_data("campañas")
    with st.form("sc_form"):
        c_area = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        c_preg = st.text_input("Criterio / Pregunta")
        c_pts = st.number_input("Puntaje", 1, 100, 10)
        if st.form_submit_button("Añadir Pregunta"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_area,"pregunta":c_preg,"puntos":c_pts})
            st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)
