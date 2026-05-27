import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise Edition", layout="wide")

URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final, on_bad_lines='skip')
        if not df.empty:
            # LIMPIEZA AGRESIVA DE COLUMNAS: minúsculas, sin tildes, sin espacios
            df.columns = [
                str(c).strip().lower()
                .replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                .replace('area','area') # Asegura consistencia
                for c in df.columns
            ]
            df = df.dropna(subset=[df.columns[0]])
        return df
    except:
        return pd.DataFrame()

# --- 2. LOGIN (CON ID Y NOMBRE) ---
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
            # Login: Col 0 es ID/User, Col 2 es Password
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

# --- 3. BARRA LATERAL ---
u_session = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.info(f"**ID:** {u_session['id']}\n\n**Nombre:** {u_session['nombre']}")

menu = ["Dashboard", "Evaluador", "Config Scorecards", "Gestión Campañas", "Gestión Usuarios"] if u_session['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS (LÓGICA DEL ARCHIVO LOCAL + CONEXIÓN WEB) ---

if choice == "Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        # Resolvemos nombres de columnas para el Dashboard
        col_fecha = 'fecha_registro' if 'fecha_registro' in df_ev.columns else df_ev.columns[0]
        col_puntos = 'puntos_obtenidos' if 'puntos_obtenidos' in df_ev.columns else df_ev.columns[4]
        col_max = 'puntos_maximos' if 'puntos_maximos' in df_ev.columns else df_ev.columns[5]
        
        df_ev[col_fecha] = pd.to_datetime(df_ev[col_fecha], errors='coerce')
        df_ev['% score'] = (df_ev[col_puntos] / df_ev[col_max]) * 100
        
        m1, m2 = st.columns(2)
        m1.metric("Promedio General", f"{df_ev['% score'].mean():.1f}%")
        m2.metric("Total Evaluaciones", len(df_ev))
        
        fig = px.bar(df_ev.groupby('agente')['% score'].mean().reset_index(), 
                     x='agente', y='% score', color='% score', text_auto='.1f', title="Desempeño por Agente")
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("No hay datos registrados.")

elif choice == "Evaluador":
    st.header("📝 Evaluador")
    df_sc = get_data("scorecards")
    df_u = get_data("usuarios")
    
    with st.form("eval_form"):
        c1, c2, c3 = st.columns(3)
        areas = df_sc['area'].unique() if not df_sc.empty else ["General"]
        c_sel = c1.selectbox("Campaña", areas)
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente']
        ag_sel = c2.selectbox("Agente", ags.iloc[:,1].tolist() if not ags.empty else ["N/A"])
        f_ev = c3.date_input("Fecha Evento")
        
        st.write("---")
        pregs = df_sc[df_sc['area'] == c_sel]
        respuestas = {}
        for _, r in pregs.iterrows():
            # Lógica de Sliders del archivo LOCAL
            respuestas[r['pregunta']] = st.select_slider(f"{r['pregunta']} (Max: {r['puntos']})", options=[0, int(r['puntos'])], value=int(r['puntos']))
        
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Guardar Evaluación"):
            p_ob = sum(respuestas.values())
            p_mx = sum(pregs['puntos'])
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "fecha_evento": str(f_ev), "area": c_sel, "agente": ag_sel,
                "puntos_obtenidos": p_ob, "puntos_maximos": p_mx,
                "evaluador": u_session['id'], "observaciones": obs
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success(f"Guardado con éxito: {(p_ob/p_mx*100):.1f}%")

elif choice == "Gestión Campañas":
    st.header("📁 Gestión de Campañas")
    nc = st.text_input("Nombre de la Campaña")
    if st.button("🚀 Crear"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(get_data("campañas"), use_container_width=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    
    col_f, col_t = st.columns([1, 1.5])
    with col_f:
        with st.container(border=True):
            st.subheader("Formulario de Usuario")
            uid = st.text_input("ID / Username")
            unom = st.text_input("Nombre Completo")
            upass = st.text_input("Contraseña")
            urol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            ucamp = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["Todas"])
            
            # BOTONES DE EDITAR Y REGISTRAR (Funcionalidad Local)
            c1, c2 = st.columns(2)
            if c1.button("🚀 Registrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":uid,"nombre":unom,"password":upass,"rol":urol,"campaña":ucamp,"estado":"Activo"})
                st.rerun()
            if c2.button("📝 Modificar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":uid,"nombre":unom,"password":upass,"rol":urol,"campaña":ucamp})
                st.rerun()
        
        st.divider()
        u_sel = st.selectbox("ID para Eliminar/Inhabilitar", df_u.iloc[:,0].tolist() if not df_u.empty else [])
        if st.button("🗑️ Eliminar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel})
            st.rerun()

    with col_t:
        st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_c = get_data("campañas")
    with st.form("sc_form"):
        c_area = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        c_preg = st.text_input("Pregunta / Criterio")
        c_pts = st.number_input("Puntos", 1, 100, 10)
        if st.form_submit_button("Añadir Pregunta"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_area,"pregunta":c_preg,"puntos":c_pts})
            st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)
