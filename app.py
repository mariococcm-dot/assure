import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN E INFRAESTRUCTURA ---
st.set_page_config(page_title="QualityScore Enterprise Edition", layout="wide")

# URL de tu Apps Script corregida
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        
        # Lectura blindada para evitar el error de encabezados mezclados 
        df = pd.read_csv(url_final, on_bad_lines='skip')
        if not df.empty:
            df.columns = [str(c).strip().split('\n')[0].lower() for c in df.columns]
            df = df.dropna(subset=[df.columns[0]]) # Limpia filas basura 
        return df
    except:
        return pd.DataFrame()

# --- 2. LÓGICA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Enterprise - Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        # Admin maestro por código [cite: 68]
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"user": "admin", "rol": "Administrador", "campaña": "Todas"}
            st.rerun()
        
        # Validación contra base de datos Excel [cite: 69]
        df_db = get_data("usuarios")
        if not df_db.empty:
            user_row = df_db[(df_db.iloc[:,0].astype(str) == u_log) & (df_db.iloc[:,2].astype(str) == p_log)]
            if not user_row.empty:
                row = user_row.iloc[0]
                if str(row.iloc[5]).lower() == 'inactivo':
                    st.error("🚫 Usuario inactivo.")
                else:
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {"user": str(row.iloc[0]), "rol": str(row.iloc[3]), "campaña": str(row.iloc[4])}
                    st.rerun()
            else: st.error("❌ Credenciales incorrectas.")
    st.stop()

user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Usuario: **{user_data['user']}**")

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# Menú dinámico según rol [cite: 82]
if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Config Scorecards", "Gestión Campañas", "Gestión Usuarios"]
elif user_data['rol'] == 'Evaluador':
    menu = ["Dashboard", "Evaluador"]
else:
    menu = ["Mis Calificaciones"]

choice = st.sidebar.selectbox("Menú Principal", menu)

# --- 3. MÓDULOS HÍBRIDOS ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_eval = get_data("evaluaciones")
    
    if df_eval.empty:
        st.info("Sin datos registrados aún.")
    else:
        # Lógica de fechas y meses del archivo Local [cite: 91, 92]
        df_eval['fecha_registro'] = pd.to_datetime(df_eval['fecha_registro'], errors='coerce')
        df_eval = df_eval.dropna(subset=['fecha_registro'])
        df_eval['Año'] = df_eval['fecha_registro'].dt.year
        df_eval['Mes'] = df_eval['fecha_registro'].dt.month_name()

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_camp = st.selectbox("Campaña:", ["Ver Todas"] + df_eval['área'].unique().tolist())
        with col_f2:
            sel_año = st.selectbox("Año:", sorted(df_eval['Año'].unique(), reverse=True))

        df_f = df_eval[df_eval['Año'] == sel_año]
        if sel_camp != "Ver Todas": df_f = df_f[df_f['área'] == sel_camp]

        # Cálculo de Scores del archivo Local [cite: 96, 97]
        df_f['% Final'] = (df_f['puntos_obtenidos'] / df_f['puntos_maximos']) * 100
        st.metric("Total Monitoreos", len(df_f))
        
        fig = px.bar(df_f.groupby('agente')['% Final'].mean().reset_index(), 
                     x='agente', y='% Final', title="Desempeño por Agente",
                     color='% Final', color_continuous_scale='Blues', text_auto='.1f')
        st.plotly_chart(fig, use_container_width=True)

elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    df_sc = get_data("scorecards")
    df_u = get_data("usuarios")
    
    if df_sc.empty:
        st.warning("Configure los scorecards primero.")
    else:
        with st.form("eval_form"):
            col1, col2 = st.columns(2)
            c_sel = col1.selectbox("Campaña", df_sc['área'].unique())
            ags = df_u[(df_u.iloc[:,3].str.lower() == 'agente') & (df_u.iloc[:,4] == c_sel)]
            ag_sel = col2.selectbox("Agente", ags.iloc[:,0].tolist() if not ags.empty else ["Manual"])
            
            # Carga dinámica de preguntas del Scorecard [cite: 103, 104]
            pregs = df_sc[df_sc['área'] == c_sel]
            resps = {}
            for _, row in pregs.iterrows():
                resps[row['pregunta']] = st.slider(f"{row['pregunta']} ({row['puntos']} pts)", 0, int(row['puntos']), int(row['puntos']))
            
            obs = st.text_area("Observaciones")
            if st.form_submit_button("Guardar Evaluación"):
                s_o = sum(resps.values())
                s_m = sum(pregs['puntos'])
                payload = {
                    "target_sheet": "evaluaciones", "action": "create",
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "agente": ag_sel, "puntos_obtenidos": s_o, "puntos_maximos": s_m,
                    "evaluador": user_data['user'], "observaciones": obs, "área": c_sel
                }
                requests.post(URL_SCRIPT, json=payload)
                st.success(f"✅ Evaluación guardada: {(s_o/s_m*100):.1f}%")

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data("usuarios")
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        st.subheader("Nuevo / Editar")
        u_id = st.text_input("ID / Username")
        u_nom = st.text_input("Nombre Completo")
        u_pass = st.text_input("Password")
        u_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
        
        if st.button("🚀 Registrar/Actualizar"):
            p = {"target_sheet":"usuarios","action":"create","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":"General","estado":"Activo"}
            requests.post(URL_SCRIPT, json=p)
            st.rerun()

    with col_r:
        st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Criterios")
    # Lógica de creación de criterios [cite: 108, 109]
    with st.container(border=True):
        c_sc = st.text_input("Nombre de Campaña")
        preg_sc = st.text_input("Criterio / Pregunta")
        pts_sc = st.number_input("Puntos Máximos", 1, 100, 10)
        if st.button("➕ Añadir"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","área":c_sc,"pregunta":preg_sc,"puntos":pts_sc})
            st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)

elif choice == "Mis Calificaciones":
    st.header(f"📈 Resultados para: {user_data['user']}")
    df_ev = get_data("evaluaciones")
    mis_ev = df_ev[df_ev['agente'].str.lower() == user_data['user'].lower()]
    if mis_ev.empty:
        st.info("Aún no tienes evaluaciones registradas.")
    else:
        mis_ev['%'] = (mis_ev['puntos_obtenidos'] / mis_ev['puntos_maximos']) * 100
        st.dataframe(mis_ev[['fecha_registro', 'área', 'puntos_obtenidos', '%', 'observaciones']], use_container_width=True)
