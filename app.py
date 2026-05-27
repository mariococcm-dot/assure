import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN E INFRAESTRUCTURA ---
st.set_page_config(page_title="QualityScore Enterprise Edition", layout="wide")

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

# --- 2. LÓGICA DE LOGIN (ADMIN FIJO SIEMPRE ACTIVO) ---
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
            # Login por ID (Col 0) y Pass (Col 2)
            user_match = df_db[(df_db.iloc[:,0].astype(str) == u_log) & (df_db.iloc[:,2].astype(str) == p_log)]
            if not user_match.empty:
                row = user_match.iloc[0]
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {"id": str(row.iloc[0]), "nombre": str(row.iloc[1]), "rol": str(row.iloc[3])}
                st.rerun()
            else: st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 3. INTERFAZ Y MENÚ ---
u_session = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"ID: **{u_session['id']}**")
st.sidebar.write(f"Nombre: **{u_session['nombre']}**")

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
        # Lógica de cálculo del archivo Local
        df_ev['fecha_registro'] = pd.to_datetime(df_ev['fecha_registro'], errors='coerce')
        df_ev['% Score'] = (df_ev['puntos_obtenidos'] / df_ev['puntos_maximos']) * 100
        
        c1, c2 = st.columns(2)
        c1.metric("Promedio General", f"{df_ev['% Score'].mean():.1f}%")
        c2.metric("Total Evaluaciones", len(df_ev))
        
        fig = px.bar(df_ev.groupby('agente')['% Score'].mean().reset_index(), x='agente', y='% Score', color='% Score', title="Calificación promedio por Agente")
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("No hay datos.")

elif choice == "Evaluador":
    st.header("📝 Nueva Evaluación")
    df_sc = get_data("scorecards")
    df_u = get_data("usuarios")
    
    with st.form("f_eval"):
        camp_list = df_sc['área'].unique() if not df_sc.empty else ["General"]
        c_sel = st.selectbox("Campaña", camp_list)
        
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente']
        ag_sel = st.selectbox("Agente", ags.iloc[:,0].tolist() if not ags.empty else ["Sin agentes"])
        
        # Generar preguntas dinámicas del scorecard
        pregs = df_sc[df_sc['área'] == c_sel]
        resultados = {}
        for _, r in pregs.iterrows():
            resultados[r['pregunta']] = st.slider(f"{r['pregunta']} (Max: {r['puntos']})", 0, int(r['puntos']), int(r['puntos']))
        
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Guardar"):
            p_ob = sum(resultados.values())
            p_mx = sum(pregs['puntos'])
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "agente": ag_sel, "puntos_obtenidos": p_ob, "puntos_maximos": p_mx,
                "evaluador": u_session['id'], "observaciones": obs, "área": c_sel
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success("✅ Guardado")

elif choice == "Gestión Campañas":
    st.header("📁 Gestión de Campañas")
    df_c = get_data("campañas")
    nc = st.text_input("Nueva Campaña")
    if st.button("Crear"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(df_c, use_container_width=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    
    col_l, col_r = st.columns([1, 2])
    with col_l:
        with st.container(border=True):
            id_u = st.text_input("ID")
            nom_u = st.text_input("Nombre")
            pw_u = st.text_input("Password")
            rol_u = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            cp_u = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["Todas"])
            
            b1, b2 = st.columns(2)
            if b1.button("🚀 Registrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":id_u,"nombre":nom_u,"password":pw_u,"rol":rol_u,"campaña":cp_u,"estado":"Activo"})
                st.rerun()
            if b2.button("📝 Modificar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":id_u,"nombre":nom_u,"password":pw_u,"rol":rol_u,"campaña":cp_u})
                st.rerun()
        
        st.divider()
        u_sel = st.selectbox("ID para borrar/bloquear", df_u.iloc[:,0].tolist() if not df_u.empty else [])
        if st.button("🗑️ Borrar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel})
            st.rerun()

    with col_r: st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_c = get_data("campañas")
    with st.container(border=True):
        c_sc = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["Todas"])
        p_sc = st.text_input("Pregunta")
        v_sc = st.number_input("Puntos", 1, 100, 10)
        if st.button("Añadir"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","área":c_sc,"pregunta":p_sc,"puntos":v_sc})
            st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)
