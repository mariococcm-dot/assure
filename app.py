import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN E INFRAESTRUCTURA ---
st.set_page_config(page_title="QualityScore Enterprise Edition", layout="wide")

# URL de tu Apps Script
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final, on_bad_lines='skip')
        if not df.empty:
            # Normalización para evitar errores de tildes o espacios
            df.columns = [str(c).strip().lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u') for c in df.columns]
            df = df.dropna(subset=[df.columns[0]])
        return df
    except:
        return pd.DataFrame()

# --- 2. LÓGICA DE SESIÓN (LOGIN) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Enterprise - Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        # Acceso administrativo prioritario
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"user": "admin", "nombre": "Admin Maestro", "rol": "Administrador", "campaña": "Todas"}
            st.rerun()
        
        # Validación con Google Sheets
        df_db = get_data("usuarios")
        if not df_db.empty:
            # Col 0: username, Col 2: password
            user_match = df_db[(df_db.iloc[:,0].astype(str) == u_log) & (df_db.iloc[:,2].astype(str) == p_log)]
            if not user_match.empty:
                row = user_match.iloc[0]
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {
                    "user": str(row.iloc[0]),
                    "nombre": str(row.iloc[1]),
                    "rol": str(row.iloc[3]),
                    "campaña": str(row.iloc[4])
                }
                st.rerun()
            else: st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 3. BARRA LATERAL E IDENTIDAD ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.markdown(f"**ID:** `{user_data['user']}`")
st.sidebar.markdown(f"**Nombre:** {user_data.get('nombre', 'Usuario')}")

# Menú según archivo Local
if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Config Scorecards", "Gestión Campañas", "Gestión Usuarios"]
elif user_data['rol'] == 'Evaluador':
    menu = ["Dashboard", "Evaluador"]
else:
    menu = ["Mis Calificaciones"]

choice = st.sidebar.selectbox("Seleccione Módulo", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_eval = get_data("evaluaciones")
    if not df_eval.empty:
        # CORRECCIÓN DE TIPOS (Evita el error de división)
        df_eval['puntos_obtenidos'] = pd.to_numeric(df_eval['puntos_obtenidos'], errors='coerce').fillna(0)
        df_eval['puntos_maximos'] = pd.to_numeric(df_eval['puntos_maximos'], errors='coerce').fillna(1)
        df_eval['% score'] = (df_eval['puntos_obtenidos'] / df_eval['puntos_maximos']) * 100
        
        # Filtros del archivo Local
        c1, c2 = st.columns(2)
        with c1:
            camp_filtro = st.selectbox("Filtrar por Campaña:", ["Todas"] + df_eval['area'].unique().tolist())
        
        df_f = df_eval.copy()
        if camp_filtro != "Todas":
            df_f = df_f[df_f['area'] == camp_filtro]
            
        st.metric("Promedio General", f"{df_f['% score'].mean():.1f}%")
        
        fig = px.bar(df_f.groupby('agente')['% score'].mean().reset_index(), 
                     x='agente', y='% score', color='% score', text_auto='.1f', title="Cumplimiento por Agente")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aún no hay evaluaciones registradas.")

elif choice == "Evaluador":
    st.header("📝 Nueva Evaluación")
    df_sc = get_data("scorecards")
    df_u = get_data("usuarios")
    
    with st.form("form_eval"):
        c1, c2, c3 = st.columns(3)
        areas = df_sc['area'].unique() if not df_sc.empty else ["General"]
        sel_area = c1.selectbox("Campaña/Área", areas)
        
        # Filtro de agentes de la campaña seleccionada
        ags = df_u[(df_u.iloc[:,3].str.lower() == 'agente') & (df_u.iloc[:,4] == sel_area)]
        sel_agente = c2.selectbox("Agente", ags.iloc[:,1].tolist() if not ags.empty else ["Sin agentes"])
        f_ev = c3.date_input("Fecha de la llamada/evento")
        
        st.divider()
        # Scorecard dinámico según archivo Local
        preguntas = df_sc[df_sc['area'] == sel_area]
        respuestas = {}
        for _, row in preguntas.iterrows():
            respuestas[row['pregunta']] = st.select_slider(
                f"{row['pregunta']} (Máx: {row['puntos']})",
                options=[0, int(row['puntos'])],
                value=int(row['puntos'])
            )
        
        obs = st.text_area("Observaciones y Feedback")
        if st.form_submit_button("💾 Guardar Evaluación"):
            p_ob = sum(respuestas.values())
            p_mx = sum(preguntas['puntos'])
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "fecha_evento": str(f_ev), "area": sel_area, "agente": sel_agente,
                "puntos_obtenidos": p_ob, "puntos_maximos": p_mx,
                "evaluador": user_data['user'], "observaciones": obs
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success(f"✅ Registrada con éxito: {(p_ob/p_mx*100):.1f}%")

elif choice == "Gestión Usuarios":
    st.header("👥 Administración de Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    
    col_form, col_view = st.columns([1, 1.5])
    with col_form:
        with st.container(border=True):
            id_u = st.text_input("ID de Empleado")
            nom_u = st.text_input("Nombre Completo")
            pass_u = st.text_input("Password")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            camp_u = st.selectbox("Campaña Asignada", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
            
            b1, b2 = st.columns(2)
            if b1.button("🚀 Registrar Nuevo"):
                p = {"target_sheet":"usuarios","action":"create","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u,"estado":"Activo"}
                requests.post(URL_SCRIPT, json=p); st.rerun()
            if b2.button("📝 Modificar Existente"):
                p = {"target_sheet":"usuarios","action":"update","username":id_u,"nombre":nom_u,"password":pass_u,"rol":rol_u,"campaña":camp_u}
                requests.post(URL_SCRIPT, json=p); st.rerun()
                
    with col_view:
        st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Gestión Campañas":
    st.header("📁 Gestión de Campañas")
    nc = st.text_input("Nombre de Nueva Campaña")
    if st.button("Añadir"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(get_data("campañas"), use_container_width=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_c = get_data("campañas")
    with st.form("form_sc"):
        c_sc = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        p_sc = st.text_input("Pregunta / Criterio")
        v_sc = st.number_input("Puntos", 1, 100, 10)
        if st.form_submit_button("Añadir Pregunta"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_sc,"pregunta":p_sc,"puntos":v_sc})
            st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)
