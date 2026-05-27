import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
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
    except Exception as e:
        return pd.DataFrame()

# --- 2. LÓGICA DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"username": "admin", "nombre": "Administrador", "rol": "Administrador", "campaña": "Todas"}
            st.rerun()
        
        df_db = get_data("usuarios")
        if not df_db.empty:
            encontrado = False
            for _, row in df_db.iterrows():
                # Columna 0: Username, Columna 2: Password
                if str(row.iloc[0]).strip() == u_log and str(row.iloc[2]).strip() == p_log:
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {
                        "username": str(row.iloc[0]).strip(),
                        "nombre": str(row.iloc[1]).strip(),
                        "rol": str(row.iloc[3]).strip(),
                        "campaña": str(row.iloc[4]).strip()
                    }
                    encontrado = True
                    break
            if encontrado: st.rerun()
            else: st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# --- 3. BARRA LATERAL ---
user = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user['nombre']}**")
st.sidebar.write(f"Rol: **{user['rol']}**")

menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS ---

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_eval = get_data("evaluaciones")
    
    if df_eval.empty:
        st.info("Sin datos registrados aún.")
    else:
        # Lógica de fechas y meses del LOCAL
        df_eval['fecha_registro'] = pd.to_datetime(df_eval['fecha_registro'], errors='coerce')
        df_eval['Año'] = df_eval['fecha_registro'].dt.year
        df_eval['Mes_Ing'] = df_eval['fecha_registro'].dt.month_name()
        
        meses_esp = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        dic_meses = dict(zip(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], meses_esp))
        df_eval['Mes'] = df_eval['Mes_Ing'].map(dic_meses)

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            df_c_list = get_data("campañas")
            camps = ["Ver Todas"] + (df_c_list.iloc[:,0].tolist() if not df_c_list.empty else [])
            sel_camp = st.selectbox("Campaña:", camps)
        with col_f2:
            años_db = sorted(df_eval['Año'].dropna().unique().astype(int).tolist(), reverse=True)
            sel_año = st.selectbox("Año:", años_db if años_db else [datetime.now().year])
        with col_f3:
            sel_mes = st.selectbox("Mes:", meses_esp, index=datetime.now().month - 1)

        # Filtrado
        df_f = df_eval[(df_eval['Año'] == sel_año) & (df_eval['Mes'] == sel_mes)].copy()
        if sel_camp != "Ver Todas":
            df_f = df_f[df_f.iloc[:, 1] == sel_camp]

        if df_f.empty:
            st.warning(f"No hay datos para {sel_mes} de {sel_año}.")
        else:
            # Cálculo seguro de puntos (Col 4 y 5)
            p_obt = pd.to_numeric(df_f.iloc[:, 4], errors='coerce').fillna(0)
            p_max = pd.to_numeric(df_f.iloc[:, 5], errors='coerce').fillna(1)
            df_f['score_p'] = (p_obt / p_max) * 100

            st.metric("Total Monitoreos", len(df_f))

            if sel_camp == "Ver Todas":
                fig = px.bar(df_f.groupby(df_f.columns[1])['score_p'].mean().reset_index(), 
                             x=df_f.columns[1], y='score_p', title="Promedio por Campaña", text_auto='.1f')
            else:
                fig = px.bar(df_f.groupby('agente')['score_p'].mean().reset_index(), 
                             x='agente', y='score_p', title=f"Asesores en {sel_camp}", text_auto='.1f')
            st.plotly_chart(fig, use_container_width=True)

elif choice == "Evaluador":
    st.header("📝 Módulo de Evaluación")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    df_sc = get_data("scorecards")
    
    with st.form("form_eval"):
        c_list = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
        c_sel = st.selectbox("Campaña", c_list)
        
        ags = df_u[df_u.iloc[:,3].astype(str).str.lower() == 'agente']
        ag_list = (ags.iloc[:,0].astype(str) + " - " + ags.iloc[:,1].astype(str)).tolist()
        ag_sel = st.selectbox("Agente", ag_list if ag_list else ["Sin agentes"])
        
        pregs = df_sc[df_sc.iloc[:,0] == c_sel]
        resps = {}
        for _, r in pregs.iterrows():
            resps[r.iloc[1]] = st.select_slider(f"{r.iloc[1]}", options=[0, int(r.iloc[2])], value=int(r.iloc[2]))
        
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Guardar"):
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "agente": ag_sel.split(" - ")[0], "puntos_obtenidos": sum(resps.values()),
                "puntos_maximos": sum(pregs.iloc[:,2]), "evaluador": user['username'],
                "observaciones": obs, "campaña": c_sel
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success("✅ Guardado")

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    nc = st.text_input("Nombre de la Campaña")
    if st.button("🚀 Crear"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(df_c, use_container_width=True, hide_index=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        u_id = st.text_input("ID / Username")
        u_nom = st.text_input("Nombre")
        u_pass = st.text_input("Password")
        u_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
        u_camp = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["Todas"])
        
        b1, b2 = st.columns(2)
        if b1.button("🚀 Registrar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp,"estado":"Activo"})
            st.rerun()
        if b2.button("📝 Modificar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp})
            st.rerun()
        
        st.divider()
        if not df_u.empty:
            u_sel = st.selectbox("Seleccionar ID para borrar/inhabilitar:", df_u.iloc[:,0].tolist())
            if st.button("🗑️ Borrar Usuario"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel})
                st.rerun()

    with col_r:
        st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_sc = get_data("scorecards")
    df_c = get_data("campañas")
    with st.container(border=True):
        c_sc = st.selectbox("Campaña vinculada", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        preg_sc = st.text_input("Pregunta")
        pts_sc = st.number_input("Puntos", 1, 100, 10)
        if st.button("➕ Añadir"):
            requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_sc, "pregunta":preg_sc, "puntos":pts_sc})
            st.rerun()
    st.dataframe(df_sc, use_container_width=True, hide_index=True)
