import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(sheet):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(sheet)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url, on_bad_lines='skip')
        if not df.empty: df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except: return pd.DataFrame()

# --- 2. LOGIN ---
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔑 QualityScore")
    u_log = st.text_input("Usuario")
    p_log = st.text_input("Password", type="password")
    if st.button("Ingresar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state.update({"autenticado":True, "user_data":{"username":"admin","nombre":"Admin","rol":"Administrador","campaña":"Todas"}})
            st.rerun()
        db_u = get_data("usuarios")
        for _, r in db_u.iterrows():
            if str(r.iloc[0]) == u_log and str(r.iloc[2]) == p_log:
                st.session_state.update({"autenticado":True, "user_data":{"username":str(r.iloc[0]),"nombre":str(r.iloc[1]),"rol":str(r.iloc[3]),"campaña":str(r.iloc[4])}})
                st.rerun()
        st.error("Error en credenciales")
    st.stop()

# --- 3. MENÚ ---
user = st.session_state["user_data"]
st.sidebar.title(f"Hola, {user['nombre']}")
opciones = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user['rol'] == "Administrador" else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú", opciones)
if st.sidebar.button("Salir"): 
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---
if choice == "Dashboard":
    st.header("📊 Dashboard")
    df_e = get_data("evaluaciones")
    if not df_e.empty:
        c1, c2 = st.columns(2)
        with c1: sel_c = st.selectbox("Campaña", ["Todas"] + get_data("campañas").iloc[:,0].tolist())
        
        f = df_e.copy()
        if sel_c != "Todas": f = f[f.iloc[:,1] == sel_c]
        
        if not f.empty:
            f['score'] = (pd.to_numeric(f.iloc[:,4])/pd.to_numeric(f.iloc[:,5]))*100
            prom = f['score'].mean()
            st.metric("Promedio", f"{prom:.1f}%")
            
            # GRÁFICA BINARIA (SI=PESO, NO=0)
            sc = get_data("scorecards")
            items = sc[sc.iloc[:,0] == sel_c].copy() if sel_c != "Todas" else pd.DataFrame()
            if not items.empty:
                items['Cumplimiento'] = items.apply(lambda r: 0 if (100 - prom) >= r.iloc[2] else r.iloc[2], axis=1)
                fig = px.bar(items, x='Cumplimiento', y=items.columns[1], orientation='h', color='Cumplimiento', color_continuous_scale=[(0,'#D3D3D3'),(1,'#1F77B4')])
                st.plotly_chart(fig, use_container_width=True)

elif choice == "Evaluador":
    st.header("📝 Evaluación")
    c_list = get_data("campañas").iloc[:,0].tolist()
    c_sel = st.selectbox("Campaña", c_list)
    ags = get_data("usuarios")
    ag_list = ags[(ags.iloc[:,3].str.lower()=="agente") & (ags.iloc[:,4]==c_sel)].iloc[:,0].tolist()
    
    with st.form("eval_form"):
        agente = st.selectbox("Agente", ag_list if ag_list else ["N/A"])
        pregs = get_data("scorecards")
        pregs = pregs[pregs.iloc[:,0] == c_sel]
        resp = {}
        for _, p in pregs.iterrows():
            v = st.radio(f"{p.iloc[1]} ({p.iloc[2]} pts)", ["Si", "No"], horizontal=True)
            resp[p.iloc[1]] = int(p.iloc[2]) if v == "Si" else 0
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Guardar"):
            payload = {"target_sheet":"evaluaciones","action":"create","fecha_registro":datetime.now().strftime("%d/%m/%Y"),"agente":agente,"puntos_obtenidos":sum(resp.values()),"puntos_maximos":sum(pregs.iloc[:,2]),"evaluador":user['username'],"observaciones":obs,"campaña":c_sel}
            requests.post(URL_SCRIPT, json=payload)
            st.success("Guardado!")

elif choice == "Gestión Campañas":
    st.header("📁 Campañas")
    nc = st.text_input("Nombre de Campaña")
    if st.button("Crear"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(get_data("campañas"), use_container_width=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Usuarios")
    with st.form("u_f"):
        uid, unom, upas = st.text_input("ID"), st.text_input("Nombre"), st.text_input("Pass")
        urol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
        ucamp = st.selectbox("Campaña", ["Todas"] + get_data("campañas").iloc[:,0].tolist())
        if st.form_submit_button("Registrar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":uid,"nombre":unom,"password":upas,"rol":urol,"campaña":ucamp})
            st.rerun()
    st.dataframe(get_data("usuarios"), use_container_width=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Scorecards")
    c_list = get_data("campañas").iloc[:,0].tolist()
    cs = st.selectbox("Campaña", c_list)
    with st.form("sc_f"):
        pr, pt = st.text_input("Pregunta"), st.number_input("Puntos", 1, 100, 10)
        if st.form_submit_button("Añadir"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":cs,"pregunta":pr,"puntos":pt})
            st.rerun()
    st.dataframe(get_data("scorecards")[get_data("scorecards").iloc[:,0]==cs], use_container_width=True)
