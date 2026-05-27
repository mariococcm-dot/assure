import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN (IDÉNTICO AL WEB) [cite: 1] ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final, on_bad_lines='skip') [cite: 2]
        if not df.empty:
            df.columns = [str(c).strip().split('\n')[0].lower() for c in df.columns] [cite: 2]
            df = df.dropna(subset=[df.columns[0]]) [cite: 2]
        return df
    except Exception as e:
        return pd.DataFrame() [cite: 3]

# --- 2. LÓGICA DE LOGIN (IDÉNTICO AL WEB) [cite: 3, 4] ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"username": "admin", "nombre": "Administrador", "rol": "Administrador", "campaña": "Todas"} [cite: 4]
            st.rerun()
        
        df_db = get_data("usuarios")
        if not df_db.empty:
            encontrado = False
            for _, row in df_db.iterrows():
                if str(row.iloc[0]).strip() == u_log and str(row.iloc[2]).strip() == p_log: [cite: 5]
                    st.session_state["autenticado"] = True
                    st.session_state["user_data"] = {
                        "username": str(row.iloc[0]).strip(),
                        "nombre": str(row.iloc[1]).strip(), [cite: 6]
                        "rol": str(row.iloc[3]).strip(),
                        "campaña": str(row.iloc[4]).strip()
                    }
                    encontrado = True [cite: 7]
                    break
            if encontrado: st.rerun()
            else: st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# --- 3. BARRA LATERAL (IDÉNTICO AL WEB) [cite: 7] ---
user = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"Bienvenido: **{user['nombre']}**")
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
        st.info("Sin datos registrados aún.") [cite: 28]
    else:
        # LÓGICA DE FECHAS Y MESES DEL LOCAL [cite: 27, 28]
        df_eval['fecha_registro'] = pd.to_datetime(df_eval['fecha_registro'], errors='coerce')
        df_eval['Año'] = df_eval['fecha_registro'].dt.year
        df_eval['Mes_Ing'] = df_eval['fecha_registro'].dt.month_name()
        
        meses_esp = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        dic_meses = dict(zip(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], meses_esp)) [cite: 27]
        df_eval['Mes'] = df_eval['Mes_Ing'].map(dic_meses)

        # FILTROS DEL LOCAL [cite: 29, 30]
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            df_c_list = get_data("campañas")
            camps = ["Ver Todas"] + (df_c_list.iloc[:,0].tolist() if not df_c_list.empty else [])
            sel_camp = st.selectbox("Campaña:", camps) [cite: 29]
        with col_f2:
            años_db = sorted(df_eval['Año'].dropna().unique().astype(int).tolist(), reverse=True)
            sel_año = st.selectbox("Año:", años_db if años_db else [datetime.now().year]) [cite: 30]
        with col_f3:
            sel_mes = st.selectbox("Mes:", meses_esp, index=datetime.now().month - 1) [cite: 30]

        # PROCESAMIENTO DE DATOS (Filtro y Agregación del Local) [cite: 31, 32]
        df_f = df_eval[(df_eval['Año'] == sel_año) & (df_eval['Mes'] == sel_mes)].copy()
        if sel_camp != "Ver Todas":
            df_f = df_f[df_f.iloc[:, 1] == sel_camp] [cite: 31]

        if df_f.empty:
            st.warning(f"No hay datos para {sel_mes} de {sel_año}.")
        else:
            # Corrección de tipos para evitar TypeError
            df_f.iloc[:, 4] = pd.to_numeric(df_f.iloc[:, 4], errors='coerce').fillna(0)
            df_f.iloc[:, 5] = pd.to_numeric(df_f.iloc[:, 5], errors='coerce').fillna(1)
            
            df_cons = df_f.groupby(['fecha_registro', 'agente']).agg(
                Suma_Obtenida=(df_f.columns[4], 'sum'),
                Suma_Maxima=(df_f.columns[5], 'sum')
            ).reset_index() [cite: 32]
            df_cons['% Final'] = (df_cons['Suma_Obtenida'] / df_cons['Suma_Maxima']) * 100 [cite: 32]

            st.metric("Total de Monitoreos", len(df_cons)) [cite: 32]

            if sel_camp == "Ver Todas":
                fig = px.bar(df_cons.groupby(df_f.columns[1])['% Final'].mean().reset_index(), 
                             x=df_f.columns[1], y='% Final', title="Promedio Global por Campaña",
                             color='% Final', color_continuous_scale='Blues', text_auto='.1f') [cite: 33]
            else:
                fig = px.bar(df_cons.groupby('agente')['% Final'].mean().reset_index(), 
                             x='agente', y='% Final', title=f"Desempeño de Asesores: {sel_camp}",
                             color='% Final', color_continuous_scale='Blues', text_auto='.1f') [cite: 34]
            st.plotly_chart(fig, use_container_width=True)

elif choice == "Evaluador":
    st.header("📝 Módulo de Evaluación")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    df_sc = get_data("scorecards")
    
    with st.form("form_eval"):
        col1, col2 = st.columns(2)
        c_list = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"] [cite: 9]
        c_sel = col1.selectbox("Campaña", c_list)
        
        ags = df_u[df_u.iloc[:,3].astype(str).str.lower() == 'agente'] if not df_u.empty else pd.DataFrame()
        ag_list = (ags.iloc[:,0].astype(str) + " - " + ags.iloc[:,1].astype(str)).tolist()
        ag_sel = col2.selectbox("Agente", ag_list if ag_list else ["Sin agentes"]) [cite: 9]
        
        # SCORECARD DINÁMICO (Lógica del Local) [cite: 39, 40]
        pregs = df_sc[df_sc.iloc[:,0] == c_sel] if not df_sc.empty else pd.DataFrame()
        resps = {}
        for _, row in pregs.iterrows():
            resps[row.iloc[1]] = st.select_slider(f"{row.iloc[1]} (Max: {row.iloc[2]})", options=[0, int(row.iloc[2])], value=int(row.iloc[2])) [cite: 40]
        
        obs = st.text_area("Observaciones") [cite: 10]
        
        if st.form_submit_button("Guardar Evaluación"):
            p_ob = sum(resps.values())
            p_mx = sum(pregs.iloc[:,2]) if not pregs.empty else 100
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "agente": ag_sel.split(" - ")[0], "puntos_obtenidos": p_ob, "puntos_maximos": p_mx,
                "evaluador": user['username'], "observaciones": obs, "campaña": c_sel
            } [cite: 11]
            requests.post(URL_SCRIPT, json=payload)
            st.success("✅ Evaluación registrada")

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas") [cite: 11]
    c1, c2 = st.columns([1, 2])
    with c1:
        nc = st.text_input("Nombre de la Campaña") [cite: 11]
        if st.button("🚀 Crear Campaña"):
            requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc}) [cite: 12]
            st.rerun()
    with c2: st.dataframe(df_c, use_container_width=True, hide_index=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Personal")
    df_u = get_data("usuarios") [cite: 12]
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1.2, 2])
    with col_l:
        with st.container(border=True):
            st.subheader("Datos de Usuario") [cite: 13]
            u_id = st.text_input("ID / Username")
            u_nom = st.text_input("Nombre Completo")
            u_pass = st.text_input("Password")
            u_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            u_camp = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["Todas"]) [cite: 13]
            b_reg, b_mod = st.columns(2)
            if b_reg.button("🚀 Registrar"):
                p = {"target_sheet":"usuarios","action":"create","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp,"estado":"Activo"}
                requests.post(URL_SCRIPT, json=p); st.rerun() [cite: 14, 15]
            if b_mod.button("📝 Modificar"):
                p = {"target_sheet":"usuarios","action":"update","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp}
                requests.post(URL_SCRIPT, json=p); st.rerun() [cite: 15, 16]
        st.divider()
        if not df_u.empty:
            u_sel = st.selectbox("Seleccionar ID:", df_u.iloc[:,0].tolist()) [cite: 16]
            a1, a2 = st.columns(2)
            if a1.button("🚫 Inhabilitar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"status","user":u_sel,"val":"Inactivo"}); st.rerun() [cite: 16, 17]
            if a2.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel}); st.rerun() [cite: 17, 18]
    with col_r:
        st.subheader("Lista de Usuarios")
        st.dataframe(df_u, use_container_width=True, hide_index=True) [cite: 18]

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    df_sc = get_data("scorecards") [cite: 18]
    df_c = get_data("campañas")
    with st.container(border=True):
        c_sc = st.selectbox("Campaña vinculada", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        preg_sc = st.text_input("Pregunta / Criterio") [cite: 18]
        pts_sc = st.number_input("Puntos", 1, 100, 10) [cite: 19]
        if st.button("➕ Añadir Criterio"):
            p = {"target_sheet":"scorecards","action":"create","area":c_sc, "pregunta":preg_sc, "puntos":pts_sc}
            requests.post(URL_SCRIPT, json=p); st.rerun() [cite: 19, 20]
    st.subheader("Criterios Registrados")
    st.dataframe(df_sc, use_container_width=True, hide_index=True) [cite: 20]
