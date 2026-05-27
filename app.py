import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- 1. CONFIGURACIÓN (IDÉNTICO AL WEB) ---
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
    except:
        return pd.DataFrame()

# --- 2. LOGIN (IGUAL AL WEB PERO ASEGURANDO LAS CLAVES) ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.subheader("🔑 QualityScore Login")
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Ingresar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state["autenticado"] = True
            # Definimos 'username' y 'nombre' explícitamente
            st.session_state["user_data"] = {"username": "admin", "nombre": "Administrador", "rol": "Administrador"}
            st.rerun()
        
        df_db = get_data("usuarios")
        if not df_db.empty:
            # Buscamos por posición: Col 0 (user), Col 2 (pass)
            match = df_db[(df_db.iloc[:,0].astype(str) == u_log) & (df_db.iloc[:,2].astype(str) == p_log)]
            if not match.empty:
                row = match.iloc[0]
                st.session_state["autenticado"] = True
                # USAMOS 'username' PARA COINCIDIR CON EL ERROR QUE TENÍAS
                st.session_state["user_data"] = {
                    "username": str(row.iloc[0]),
                    "nombre": str(row.iloc[1]),
                    "rol": str(row.iloc[3])
                }
                st.rerun()
            else: st.error("❌ Credenciales incorrectas")
    st.stop()

# --- 3. BARRA LATERAL (CORREGIDA) ---
# Extraemos los datos con .get() para que si falta algo no explote el código
user_info = st.session_state.get("user_data", {})
st.sidebar.title("🚀 QualityScore")
st.sidebar.write(f"ID: **{user_info.get('username', 'N/A')}**")
st.sidebar.write(f"Nombre: **{user_info.get('nombre', 'Usuario')}**")

menu = ["Dashboard", "Evaluador", "Gestión Campañas", "Gestión Usuarios", "Config Scorecards"] if user_info.get('rol') == 'Administrador' else ["Dashboard", "Evaluador"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 4. DASHBOARD (SÓLO CORRECCIÓN DE CÁLCULO) ---
if choice == "Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        # CREAMOS SERIES NUEVAS PARA EVITAR EL TYPEERROR
        # Columna 4 suele ser puntos obtenidos, Columna 5 puntos máximos
        puntos_obt = pd.to_numeric(df_ev.iloc[:, 4], errors='coerce').fillna(0)
        puntos_max = pd.to_numeric(df_ev.iloc[:, 5], errors='coerce').fillna(1)
        
        # Calculamos el Score en una columna nueva
        df_ev['score_final'] = (puntos_obt / puntos_max) * 100
        
        col1, col2 = st.columns(2)
        col1.metric("Promedio General", f"{df_ev['score_final'].mean():.1f}%")
        col2.metric("Total Evaluaciones", len(df_ev))
        
        # Gráfico usando la columna de agente (Columna 1) y el score calculado
        fig = px.bar(
            df_ev.groupby(df_ev.columns[1])['score_final'].mean().reset_index(), 
            x=df_ev.columns[1], 
            y='score_final', 
            color='score_final',
            text_auto='.1f',
            title="Cumplimiento por Agente"
        )
        st.plotly_chart(fig, use_container_width=True)
    else: 
        st.info("No hay datos registrados en la hoja de evaluaciones.")

# --- 5. EVALUADOR (IGUAL AL WEB) ---
elif choice == "Evaluador":
    st.header("📝 Evaluador")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    df_sc = get_data("scorecards")
    
    with st.form("f_ev"):
        c_sel = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        ags = df_u[df_u.iloc[:,3].str.lower() == 'agente']
        ag_sel = st.selectbox("Agente", ags.iloc[:,0].tolist() if not ags.empty else ["N/A"])
        
        pregs = df_sc[df_sc.iloc[:,0] == c_sel] if not df_sc.empty else pd.DataFrame()
        resps = {}
        for _, r in pregs.iterrows():
            resps[r.iloc[1]] = st.select_slider(f"{r.iloc[1]}", options=[0, int(r.iloc[2])], value=int(r.iloc[2]))
        
        if st.form_submit_button("Guardar"):
            payload = {
                "target_sheet": "evaluaciones", "action": "create",
                "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
                "agente": ag_sel, "puntos_obtenidos": sum(resps.values()), 
                "puntos_maximos": sum(pregs.iloc[:,2]),
                "evaluador": user_info.get('username'), "campaña": c_sel
            }
            requests.post(URL_SCRIPT, json=payload)
            st.success("Enviado")

# --- 6. GESTIÓN USUARIOS (IGUAL AL WEB) ---
elif choice == "Gestión Usuarios":
    st.header("👥 Usuarios")
    df_u = get_data("usuarios")
    df_c = get_data("campañas")
    with st.container(border=True):
        u_id = st.text_input("ID")
        u_nm = st.text_input("Nombre")
        u_ps = st.text_input("Password")
        u_rl = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
        u_cp = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
        
        c1, c2 = st.columns(2)
        if c1.button("Registrar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"create","username":u_id,"nombre":u_nm,"password":u_ps,"rol":u_rl,"campaña":u_cp,"estado":"Activo"})
            st.rerun()
        if c2.button("Modificar"):
            requests.post(URL_SCRIPT, json={"target_sheet":"usuarios","action":"update","username":u_id,"nombre":u_nm,"password":u_ps,"rol":u_rl,"campaña":u_cp})
            st.rerun()
    st.dataframe(df_u, use_container_width=True)

# --- 7. OTROS MÓDULOS (IGUAL AL WEB) ---
elif choice == "Gestión Campañas":
    nc = st.text_input("Nueva Campaña")
    if st.button("Crear"):
        requests.post(URL_SCRIPT, json={"target_sheet":"campañas","action":"create","nombre":nc})
        st.rerun()
    st.dataframe(get_data("campañas"), use_container_width=True)

elif choice == "Config Scorecards":
    df_c = get_data("campañas")
    c_sc = st.selectbox("Campaña", df_c.iloc[:,0].tolist() if not df_c.empty else ["General"])
    p_sc = st.text_input("Pregunta")
    v_sc = st.number_input("Puntos", 1, 100, 10)
    if st.button("Añadir"):
        requests.post(URL_SCRIPT, json={"target_sheet":"scorecards","action":"create","area":c_sc, "pregunta":p_sc, "puntos":v_sc})
        st.rerun()
    st.dataframe(get_data("scorecards"), use_container_width=True)
