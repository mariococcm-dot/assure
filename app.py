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
    st.header("📊 Analítica de Calidad")
    df_eval = get_data("evaluaciones")
    
    if df_eval.empty:
        st.info("Sin datos registrados aún.")
    else:
        # --- PREPARACIÓN DE DATOS (Lógica del Local) ---
        # Convertimos fechas y extraemos periodos
        df_eval['fecha_registro'] = pd.to_datetime(df_eval['fecha_registro'], errors='coerce')
        df_eval['Año'] = df_eval['fecha_registro'].dt.year
        df_eval['Mes_Ing'] = df_eval['fecha_registro'].dt.month_name()
        
        meses_nombres = ["January", "February", "March", "April", "May", "June", 
                          "July", "August", "September", "October", "November", "December"]
        meses_esp = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        dic_meses = dict(zip(meses_nombres, meses_esp))
        df_eval['Mes'] = df_eval['Mes_Ing'].map(dic_meses)

        # --- FILTROS (Estructura del Local) ---
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            df_c = get_data("campañas")
            camps = ["Ver Todas"] + (df_c.iloc[:,0].tolist() if not df_c.empty else [])
            sel_camp = st.selectbox("Campaña:", camps)
        with col_f2:
            años_db = sorted(df_eval['Año'].dropna().unique().astype(int).tolist(), reverse=True)
            if datetime.now().year not in años_db: años_db.append(datetime.now().year)
            sel_año = st.selectbox("Año:", años_db)
        with col_f3:
            sel_mes = st.selectbox("Mes:", meses_esp, index=datetime.now().month - 1)

        # --- PROCESAMIENTO SEGURO (Evita TypeError) ---
        # Filtramos primero
        df_f = df_eval[(df_eval['Año'] == sel_año) & (df_eval['Mes'] == sel_mes)].copy()
        
        if sel_camp != "Ver Todas":
            # En el web, 'campaña' es una de las últimas columnas, o 'area' según el mapeo
            col_area = 'campaña' if 'campaña' in df_f.columns else 'area'
            df_f = df_f[df_f[col_area] == sel_camp]

        if df_f.empty:
            st.warning(f"No hay datos para {sel_mes} de {sel_año}.")
        else:
            # Agregación para cálculo de % Final (Lógica del Local)
            # Usamos iloc para asegurar que sumamos las columnas correctas de puntos (4 y 5)
            df_cons = df_f.groupby(['fecha_registro', 'agente']).agg(
                Suma_Obtenida=(df_f.columns[4], 'sum'),
                Suma_Maxima=(df_f.columns[5], 'sum')
            ).reset_index()
            
            # Convertimos a numérico antes de calcular para evitar errores
            df_cons['Suma_Obtenida'] = pd.to_numeric(df_cons['Suma_Obtenida'], errors='coerce').fillna(0)
            df_cons['Suma_Maxima'] = pd.to_numeric(df_cons['Suma_Maxima'], errors='coerce').fillna(1)
            df_cons['% Final'] = (df_cons['Suma_Obtenida'] / df_cons['Suma_Maxima']) * 100

            st.metric("Total de Monitoreos Realizados", len(df_cons))

            # --- VISUALIZACIÓN (Estructura del Local) ---
            if sel_camp == "Ver Todas":
                # Promedio Global por Campaña (usando la columna de área/campaña)
                col_area_name = 'campaña' if 'campaña' in df_f.columns else 'area'
                fig1 = px.bar(df_f.groupby(col_area_name).apply(
                    lambda x: (pd.to_numeric(x.iloc[:,4]).sum() / pd.to_numeric(x.iloc[:,5]).sum()) * 100
                ).reset_index(name='% Final'), 
                x=col_area_name, y='% Final', title="Promedio Global por Campaña",
                color='% Final', color_continuous_scale='Blues', text_auto='.1f')
                st.plotly_chart(fig1, use_container_width=True)
            else:
                # Desempeño de Asesores por Campaña Seleccionada
                fig_a = px.bar(df_cons.groupby('agente')['% Final'].mean().reset_index(), 
                x='agente', y='% Final', title=f"Desempeño de Asesores: {sel_camp}",
                color='% Final', color_continuous_scale='Blues', text_auto='.1f')
                st.plotly_chart(fig_a, use_container_width=True)

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
