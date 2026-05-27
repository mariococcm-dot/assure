import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN (BASE WEB) ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")

URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_hoja="usuarios"):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_hoja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final, on_bad_lines='skip')
        if not df.empty:
            # Limpieza estándar del archivo WEB
            df.columns = [str(c).strip().split('\n')[0].lower() for c in df.columns]
            df = df.dropna(subset=[df.columns[0]])
        return df
    except:
        return pd.DataFrame()

# --- 2. LOGIN (BASE WEB CON EXTRACTOR SEGURO) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            st.session_state["user_data"] = {"id": "admin", "nombre": "Administrador", "rol": "Administrador"}
            st.rerun()
        
        df_db = get_data("usuarios")
        if not df_db.empty:
            # Buscamos fila donde coincida usuario (Col 0) y pass (Col 2)
            match = df_db[(df_db.iloc[:,0].astype(str) == u_log) & (df_db.iloc[:,2].astype(str) == p_log)]
            if not match.empty:
                row = match.iloc[0]
                st.session_state["autenticado"] = True
                # Guardamos por posición de columna para evitar KeyError
                st.session_state["user_data"] = {
                    "id": str(row.iloc[0]),
                    "nombre": str(row.iloc[1]),
                    "rol": str(row.iloc[3])
                }
                st.rerun()
            else: st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# --- 3. BARRA LATERAL (USANDO CLAVES SEGURAS 'id' y 'nombre') ---
user = st.session_state["user_data"]
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"ID: **{user['id']}**")
st.sidebar.write(f"Nombre: **{user['nombre']}**")

menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user['rol'] == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. MÓDULOS (LÓGICA LOCAL DENTRO DE ESTRUCTURA WEB) ---

if choice == "Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        # Convertimos columnas 4 (obtenidos) y 5 (maximos) a números por posición
        df_ev.iloc[:, 4] = pd.to_numeric(df_ev.iloc[:, 4], errors='coerce').fillna(0)
        df_ev.iloc[:, 5] = pd.to_numeric(df_ev.iloc[:, 5], errors='coerce').fillna(1)
        df_ev['% score'] = (df_ev.iloc[:, 4] / df_ev.iloc[:, 5]) * 100
        
        c1, c2 = st.columns(2)
        c1.metric("Promedio General", f"{df_ev['% score'].mean():.1f}%")
        c2.metric("Total Evaluaciones", len(df_ev))
        
        # Gráfico por Agente (Columna 1 en evaluaciones suele ser el Agente)
        fig = px.bar(df_ev.groupby(df_ev.columns[1])['% score'].mean().reset_index(), 
                     x=df_ev.columns[1], y='% score', color='% score', text_auto='.1f')
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("No hay datos.")

elif choice == "Evaluador":
    st.header("📝 Módulo de Evaluación")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    df_sc = get_data("scorecards")
    
    with st.form("form_eval"):
        c_sel = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente']
        ag_sel = st.selectbox("Agente", ags.iloc[:,0].tolist() if not ags.empty else ["Sin agentes"])
        
        # Scorecard dinámico del LOCAL (basado en el web_scorecards)
        preguntas = df_sc[df_sc.iloc[:,0] == c_sel] if not df_sc.empty else pd.DataFrame()
        resps = {}
        for _, row in preguntas.iterrows():
            resps[row.iloc[1]] = st.select_slider(f"{row.iloc[1]} (Max: {row.iloc[2]})", options=[0, int(row.iloc[2])], value=int(row.iloc[2]))
        
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Guardar Evaluación"):
            p_ob = sum(resps.values())
            p_mx = sum(preguntas.iloc[:,2]) if not preguntas.empty else 100
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "agente": ag_sel, "puntos_obtenidos": p_ob, "puntos_maximos": p_mx,
                "evaluador": user['id'], "observaciones": obs, "campaña": c_sel
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success("✅ Evaluación registrada")

elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    col_l, col_r = st.columns([1, 2])
    with col_l:
        u_id = st.text_input("ID")
        u_nom = st.text_input("Nombre")
        u_pass = st.text_input("Pass")
        u_rol = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
        u_camp = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        if st.button("Registrar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp,"estado":"Activo"})
            st.rerun()
        if st.button("Modificar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":u_id,"nombre":u_nom,"password":u_pass,"rol":u_rol,"campaña":u_camp})
            st.rerun()
    with col_r: st.dataframe(df_u, use_container_width=True, hide_index=True)

elif choice == "Gestión Campañas":
    st.header("📁 Gestión Campañas")
    nc = st.text_input("Nombre Campaña")
    if st.button("Crear"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(get_data("campañas"), use_container_width=True)

elif choice == "Config Scorecards":
    st.header("⚙️ Configuración Scorecards")
    df_c = get_data("campañas")
    c_sc = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
    p_sc = st.text_input("Pregunta")
    v_sc = st.number_input("Puntos", 1, 100, 10)
    if st.button("Añadir"):
        requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_sc, "pregunta":p_sc, "puntos":v_sc})
        st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)
