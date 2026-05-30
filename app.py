import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN ---
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
        df_eval['fecha_dt'] = pd.to_datetime(df_eval.iloc[:, 0], errors='coerce')
        df_eval['año_f'] = df_eval['fecha_dt'].dt.year
        df_eval['mes_n'] = df_eval['fecha_dt'].dt.month_name()
        
        meses_esp = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        dic_meses = dict(zip(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], meses_esp))
        df_eval['mes_f'] = df_eval['mes_n'].map(dic_meses)
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            # AJUSTE PARA AGENTE: Bloqueo de campaña
            if user['rol'] == 'Agente':
                sel_camp = st.selectbox("Campaña:", [user['campaña']], disabled=True)
            else:
                df_c_list = get_data("campañas")
                camps = ["Ver Todas"] + (df_c_list.iloc[:,0].tolist() if not df_c_list.empty else [])
                sel_camp = st.selectbox("Campaña:", camps)
        
        with col_f2:
            años_db = sorted(df_eval['año_f'].dropna().unique().astype(int).tolist(), reverse=True)
            sel_año = st.selectbox("Año:", años_db if años_db else [datetime.now().year])
        with col_f3:
            sel_mes = st.selectbox("Mes:", meses_esp, index=datetime.now().month - 1)
            
        df_f = df_eval[(df_eval['año_f'] == sel_año) & (df_eval['mes_f'] == sel_mes)].copy()
        
        if sel_camp != "Ver Todas":
            df_f = df_f[df_f.iloc[:, 1] == sel_camp]
        
        # AJUSTE PARA AGENTE: Solo ve sus propios registros
        if user['rol'] == 'Agente':
            df_f = df_f[df_f.iloc[:, 2] == user['username']]
            
        if df_f.empty:
            st.warning(f"No hay datos para {sel_mes} de {sel_año}.")
        else:
            df_f['p_obt'] = pd.to_numeric(df_f.iloc[:, 4], errors='coerce').fillna(0)
            df_f['p_max'] = pd.to_numeric(df_f.iloc[:, 5], errors='coerce').fillna(1)
            df_f['score_final'] = (df_f['p_obt'] / df_f['p_max']) * 100
            
            st.metric("Total Monitoreos", len(df_f), f"{df_f['score_final'].mean():.1f}% Promedio")
            
            color_scale = ['#D3D3D3', '#1F77B4'] 

            if sel_camp == "Ver Todas":
                fig = px.bar(df_f.groupby(df_f.columns[1])['score_final'].mean().reset_index(), 
                             x=df_f.columns[1], y='score_final', 
                             title="Promedio Global por Campaña", text_auto='.1f',
                             color='score_final', color_continuous_scale=color_scale)
                st.plotly_chart(fig, use_container_width=True)
            else:
                fig = px.bar(df_f.groupby(df_f.columns[2])['score_final'].mean().reset_index(), 
                             x=df_f.columns[2], y='score_final', 
                             title=f"Desempeño en {sel_camp}", text_auto='.1f',
                             color='score_final', color_continuous_scale=color_scale)
                st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
                st.subheader(f"🔍 Cumplimiento por Atributo: {sel_camp}")
                
                df_sc = get_data("scorecards")
                pregs_camp = df_sc[df_sc.iloc[:,0] == sel_camp].copy()
                
                if not pregs_camp.empty:
                    ratio_cumplimiento = (df_f['p_obt'].sum() / df_f['p_max'].sum())
                    pregs_camp['Puntos Logrados'] = pregs_camp.iloc[:, 2] * ratio_cumplimiento

                    fig_items = px.bar(pregs_camp, 
                                       x='Puntos Logrados', y=pregs_camp.columns[1], 
                                       orientation='h', 
                                       title="Porcentaje de Logro por Item",
                                       text_auto='.1f',
                                       labels={'Puntos Logrados': 'Calificación', pregs_camp.columns[1]: 'Atributo'},
                                       color='Puntos Logrados', 
                                       color_continuous_scale=['#D3D3D3', '#1F77B4'])
                    
                    st.plotly_chart(fig_items, use_container_width=True)
                else:
                    st.info("No hay detalles de preguntas para esta campaña.")

elif choice == "Evaluador":
    st.header("📝 Módulo de Evaluación")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    df_sc = get_data("scorecards")
    
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        fecha_interaccion = st.date_input("📅 Fecha de la Interacción", datetime.now(), key="fecha_auditoria")
    
    lista_c_completa = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
    c_opciones = [user['campaña']] if user['campaña'] != "Todas" else lista_c_completa
    c_sel = st.selectbox("Campaña", c_opciones, key="sel_camp_eval")
    
    ags = df_u[(df_u.iloc[:,3].astype(str).str.lower() == 'agente') & (df_u.iloc[:,4] == c_sel)]
    ag_list = (ags.iloc[:,0].astype(str) + " - " + ags.iloc[:,1].astype(str)).tolist()
    ag_sel = st.selectbox("Agente", ag_list if ag_list else ["Sin agentes en esta campaña"], key="sel_agente_eval")

    st.divider()

    with st.form("form_eval_v2", clear_on_submit=True):
        pregs = df_sc[df_sc.iloc[:,0] == c_sel]
        resps = {}
        
        if pregs.empty:
            st.info(f"No hay preguntas configuradas para {c_sel}")
        else:
            for _, r in pregs.iterrows():
                opcion = st.radio(f"{r.iloc[1]} ({r.iloc[2]} pts)", ["Si", "No"], horizontal=True, key=f"radio_{r.iloc[1]}")
                resps[r.iloc[1]] = int(r.iloc[2]) if opcion == "Si" else 0
            
            puntos_actuales = sum(resps.values())
            puntos_totales = sum(pregs.iloc[:,2])
            porcentaje = (puntos_actuales / puntos_totales * 100) if puntos_totales > 0 else 0
            
            st.subheader("📊 Avance de la Evaluación")
            st.progress(porcentaje / 100)
            
            if porcentaje < 70:
                st.error(f"Score actual: {porcentaje:.1f}% - ESTADO: MAL 🔴")
            elif porcentaje < 90:
                st.warning(f"Score actual: {porcentaje:.1f}% - ESTADO: REGULAR 🟡")
            else:
                st.success(f"Score actual: {porcentaje:.1f}% - ESTADO: BIEN 🟢")

        obs = st.text_area("Observaciones", key="obs_eval")
        
        if st.form_submit_button("Guardar Evaluación"):
            if not ag_list or "Sin agentes" in ag_sel:
                st.error("No puedes guardar sin un agente válido.")
            elif pregs.empty:
                st.error("No hay preguntas para evaluar.")
            else:
                payload = {
                    "target_sheet": "evaluaciones", 
                    "action": "create", 
                    "fecha_registro": fecha_interaccion.strftime("%d/%m/%Y"), 
                    "agente": ag_sel.split(" - ")[0], 
                    "puntos_obtenidos": puntos_actuales, 
                    "puntos_maximos": puntos_totales, 
                    "evaluador": user['username'], 
                    "observaciones": obs, 
                    "campaña": c_sel
                }
                requests.post(URL_SCRIPT, json=payload)
                st.success(f"✅ Guardado con fecha {fecha_interaccion.strftime('%d/%m/%Y')}.")

elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        with st.container(border=True):
            st.subheader("Configurar Campaña")
            nc = st.text_input("Nombre de la Campaña")
            c1, c2 = st.columns(2)
            if c1.button("🚀 Crear"):
                requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
                st.rerun()
            if c2.button("📝 Editar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"update","nombre":nc})
                st.rerun()
            st.divider()
            if not df_c.empty:
                c_sel = st.selectbox("Seleccionar para Inhabilitar/Borrar:", df_c.iloc[:,0].tolist())
                b1, b2 = st.columns(2)
                if b1.button("🚫 Inhabilitar"):
                    requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"status","nombre":c_sel,"val":"Inactiva"})
                    st.rerun()
                if b2.button("🗑️ Borrar"):
                    requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"delete","nombre":c_sel})
                    st.rerun()
    with col_r:
        st.subheader("Campañas Activas")
        st.dataframe(df_c, use_container_width=True, hide_index=True)

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        u_id = st.text_input("ID")
        u_nom = st.text_input("Nombre")
        u_pass = st.text_input("Password")
        u_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
        lista_c = df_c.iloc[:,0].tolist() if not df_c.empty else []
        opciones_c = ["Todas"] + lista_c if u_rol == "Administrador" else (lista_c if lista_c else ["Sin Campañas"])
        u_camp = st.selectbox("Campaña", opciones_c)
        if st.button("🚀 Registrar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp,"estado":"Activo"})
            st.rerun()
        if st.button("📝 Modificar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp})
            st.rerun()
        if not df_u.empty:
            u_sel = st.selectbox("ID para borrar:", df_u.iloc[:,0].tolist())
            if st.button("🗑️ Borrar"):
                requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"delete","user":u_sel})
                st.rerun()
    with col_r:
        st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Scorecards")
    df_sc = get_data("scorecards")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        with st.container(border=True):
            st.subheader("Configurar Criterio")
            c_list = df_c.iloc[:,0].tolist() if not df_c.empty else ["General"]
            c_sc = st.selectbox("Campaña", c_list)
            
            preg_sc = st.text_input("Pregunta / Item")
            pts_sc = st.number_input("Puntos", 1, 100, 10)
            
            if st.button("➕ Añadir Item"):
                if preg_sc:
                    requests.post(URL_SCRIPT, json={
                        "target_sheet":"scorecards",
                        "action":"create",
                        "area":c_sc, 
                        "pregunta":preg_sc, 
                        "puntos":pts_sc
                    })
                    st.success("Item añadido")
                    st.rerun()
            
            st.divider()
            if not df_sc.empty:
                st.subheader("Gestión de Scorecard")
                criterios_camp = df_sc[df_sc.iloc[:,0] == c_sc]
                if not criterios_camp.empty:
                    item_sel = st.selectbox("Seleccionar Item para borrar:", criterios_camp.iloc[:,1].tolist())
                    if st.button("🗑️ Eliminar Item Seleccionado"):
                        requests.post(URL_SCRIPT, json={
                            "target_sheet":"scorecards",
                            "action":"delete",
                            "pregunta":item_sel,
                            "area":c_sc
                        })
                        st.rerun()
                
                st.divider()
                st.error(f"⚠️ ELIMINAR CAMPAÑA: {c_sc}")
                if st.button(f"🔥 Borrar '{c_sc}' por completo"):
                    requests.post(URL_SCRIPT, json={
                        "target_sheet":"scorecards",
                        "action":"delete",
                        "area":c_sc,
                        "modo": "completo" 
                    })
                    requests.post(URL_SCRIPT, json={
                        "target_sheet":"campañas",
                        "action":"delete",
                        "nombre": c_sc
                    })
                    st.success(f"Campaña {c_sc} eliminada globalmente")
                    st.rerun()

    with col_r:
        st.subheader(f"Configuración Actual: {c_sc}")
        if not df_sc.empty:
            df_sc_filtrado = df_sc[df_sc.iloc[:,0] == c_sc]
            if not df_sc_filtrado.empty:
                st.dataframe(df_sc_filtrado, use_container_width=True, hide_index=True)
            else:
                st.info("No hay preguntas configuradas para esta campaña.")
