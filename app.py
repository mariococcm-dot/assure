import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_ho_ja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_ho_ja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final, on_bad_lines='skip')
        if not df.empty:
            df.columns = [str(c).strip().split('\n')[0].lower() for c in df.columns]
            df = df.dropna(subset=[df.columns[0]])
        return df
    except Exception: return pd.DataFrame()

# --- AUTENTICACIÓN ---
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    if st.button("Ingresar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state.update({"autenticado": True, "user_data": {"username":"admin","nombre":"Admin","rol":"Administrador","campaña":"Todas"}})
            st.rerun()
        db = get_data("usuarios")
        if not db.empty:
            for _, r in db.iterrows():
                if str(r.iloc[0]) == u_log and str(r.iloc[2]) == p_log:
                    st.session_state.update({"autenticado": True, "user_data": {"username":str(r.iloc[0]),"nombre":str(r.iloc[1]),"rol":str(r.iloc[3]),"campaña":str(r.iloc[4])}})
                    st.rerun()
            st.error("❌ Credenciales incorrectas")
    st.stop()

# --- MENÚ ---
u = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Usuario: **{u['nombre']}**")
m_opt = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if u['rol'] == 'Administrador' else ["Dashboard", "Evaluador"] if u['rol'] == 'Evaluador' else ["Dashboard"]
choice = st.sidebar.selectbox("Menú", m_opt)
if st.sidebar.button("🚪 Salir"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- MÓDULOS ---
if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_e = get_data("evaluaciones")
    if df_e.empty: st.info("Sin datos.")
    else:
        df_e['fecha_dt'] = pd.to_datetime(df_e.iloc[:,0], errors='coerce')
        df_e['año'] = df_e['fecha_dt'].dt.year
        df_e['mes'] = df_e['fecha_dt'].dt.month_name()
        c1, c2, c3 = st.columns(3)
        with c1: 
            sel_c = st.selectbox("Campaña", ["Todas"] + get_data("campañas").iloc[:,0].tolist() if u['rol'] != 'Agente' else [u['campaña']])
        with c2: sel_a = st.selectbox("Año", sorted(df_e['año'].unique(), reverse=True))
        with c3: sel_m = st.selectbox("Mes", ["January","February","March","April","May","June","July","August","September","October","November","December"])
        
        f = df_e[(df_e['año'] == sel_a)]
        if sel_c != "Todas": f = f[f.iloc[:,1] == sel_c]
        if f.empty: st.warning("Sin datos para este filtro.")
        else:
            f['score'] = (pd.to_numeric(f.iloc[:,4])/pd.to_numeric(f.iloc[:,5]))*100
            prom = f['score'].mean()
            st.metric("Promedio Mensual", f"{prom:.1f}%")
            
            # GRÁFICA BINARIA (CORRECCIÓN)
            st.subheader("Cumplimiento por Atributo")
            sc = get_data("scorecards")
            items = sc[sc.iloc[:,0] == sel_c].copy() if sel_c != "Todas" else pd.DataFrame()
            if not items.empty:
                # Si el promedio no es 100, simulamos qué preguntas fallaron (lógica de peso)
                def calc_b(r):
                    peso = r.iloc[2]
                    return 0 if (100 - prom) >= peso else peso
                items['Resultado'] = items.apply(calc_b, axis=1)
                fig = px.bar(items, x='Resultado', y=items.columns[1], orientation='h', color='Resultado', color_continuous_scale=[(0,'#D3D3D3'),(1,'#1F77B4')])
                st.plotly_chart(fig, use_container_width=True)

elif choice == "Evaluador":
    st.header("📝 Evaluación")
    c_list = get_data("campañas").iloc[:,0].tolist()
    c_sel = st.selectbox("Campaña", c_list)
    ags = get_data("usuarios")
    ags = ags[(ags.iloc[:,3].str.lower() == 'agente') & (ags.iloc[:,4] == c_sel)]
    ag_sel = st.selectbox("Agente", ags.iloc[:,0].tolist() if not ags.empty else ["N/A"])
    
    with st.form("f_eval"):
        pregs = get_data("scorecards")
        pregs = pregs[pregs.iloc[:,0] == c_sel]
        r_vals = {}
        for _, p in pregs.iterrows():
            op = st.radio(f"{p.iloc[1]} ({p.iloc[2]} pts)", ["Si", "No"], horizontal=True)
            r_vals[p.iloc[1]] = int(p.iloc[2]) if op == "Si" else 0
        obs = st.text_area("Notas")
        if st.form_submit_button("Guardar"):
            p_o, p_m = sum(r_vals.values()), sum(pregs.iloc[:,2])
            requests.post(URL_SCRIPT, json={"target_sheet":"evaluaciones","action":"create","fecha_registro":datetime.now().strftime("%d/%m/%Y"),"agente":ag_sel,"puntos_obtenidos":p_o,"puntos_maximos":p_m,"evaluador":u['username'],"observaciones":obs,"campaña":c_sel})
            st.success("Guardado.")

elif choice == "Gestión Campañas":
    st.header("📁 Campañas")
    nc = st.text_input("Nueva Campaña")
    if st.button("Crear"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(get_data("campañas"), use_container_width=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Usuarios")
    with st.form("u_form"):
        uid, unom, upas = st.text_input("ID"), st.text_input("Nombre"), st.text_input("Pass")
        urol = st.selectbox("Rol", ["Administrador","Evaluador","Agente"])
        ucamp = st.selectbox("Campaña", ["Todas"] + get_data("campañas").iloc[:,0].tolist())
        if st.form_submit_button("Registrar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":uid,"nombre":unom,"password":upas,"rol":urol,"campaña":ucamp})
            st.rerun()
    st.dataframe(get_data("usuarios"), use_container_width=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Scorecards")
    c_list = get_data("campañas").iloc[:,0].tolist()
    cs = st.selectbox("Campaña", c_list)
    with st.form("sc_form"):
        pr, pt = st.text_input("Pregunta"), st.number_input("Puntos", 1, 100, 10)
        if st.form_submit_button("Añadir"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":cs,"pregunta":pr,"puntos":pt})
            st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)
