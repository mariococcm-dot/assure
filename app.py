import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import os
import shutil

# Configuración de la página
st.set_page_config(page_title="Centro de Control y Mejora", layout="wide")

# --- 🗄️ LOGICA DE BASE DE DATOS PARA NUBE ---
DB_ORIGINAL = 'calidad.db'
DB_NUBE = '/tmp/calidad.db'

# Copiamos la base de datos a una ubicación con permisos de escritura en la nube
if not os.path.exists(DB_NUBE):
    if os.path.exists(DB_ORIGINAL):
        shutil.copy2(DB_ORIGINAL, DB_NUBE)

def get_connection():
    return sqlite3.connect(DB_NUBE, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS campañas 
                 (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE, estado TEXT DEFAULT 'Activo')''')
    c.execute('''CREATE TABLE IF NOT EXISTS scorecards 
                 (id INTEGER PRIMARY KEY, area TEXT, pregunta TEXT, puntos INTEGER, tipo TEXT DEFAULT 'Escala')''')
    c.execute('''CREATE TABLE IF NOT EXISTS evaluaciones 
                 (id INTEGER PRIMARY KEY, fecha_registro TEXT, fecha_evento TEXT, area TEXT, 
                  evaluador TEXT, agente TEXT, pregunta TEXT, puntos_obtenidos INTEGER, 
                  puntos_maximos INTEGER, observaciones TEXT, tipo_evaluador TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, rol TEXT, campaña TEXT, estado TEXT DEFAULT 'Activo')''')
    
    try:
        c.execute("ALTER TABLE evaluaciones ADD COLUMN tipo_evaluador TEXT DEFAULT 'Calidad'")
    except:
        pass

    c.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO usuarios (username, password, rol, campaña, estado) VALUES (?,?,?,?,?)",
                  ('admin', 'admin123', 'Administrador', 'Todas', 'Activo'))
    conn.commit()
    conn.close()

init_db()

# --- 🔑 LÓGICA DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# --- 🚪 LOGIN ---
if not st.session_state["autenticado"]:
    st.subheader("🔑 Call Center de México | Quality Assurance")
    u_log = st.text_input("Usuario")
    p_log = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT username, rol, campaña, estado FROM usuarios WHERE username=? AND password=?", (u_log, p_log))
        user = c.fetchone()
        conn.close()
        if user:
            if user[3] == 'Inactivo': st.error("🚫 Usuario inactivo.")
            else:
                st.session_state["autenticado"] = True
                st.session_state["user_data"] = {"user": user[0], "rol": user[1], "campaña": user[2]}
                st.rerun()
        else: st.error("❌ Credenciales incorrectas.")
    st.stop()

# --- 🔓 APP PRINCIPAL ---
user_data = st.session_state["user_data"]
st.sidebar.title("🚀 QualityAssurance")
st.sidebar.write(f"Usuario: **{user_data['user']}**")

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

if user_data['rol'] == 'Administrador':
    menu = ["Dashboard", "Evaluador", "Config Scorecards", "Gestión Campañas", "Gestión Usuarios"]
elif user_data['rol'] == 'Evaluador':
    menu = ["Dashboard", "Evaluador"]
else:
    menu = ["Mis Calificaciones"]

choice = st.sidebar.selectbox("Menú", menu)

# --- 📊 DASHBOARD ---
if choice == "Dashboard":
    st.header("📊 Dashboard Evaluaciones")
    conn = get_connection()
    df_eval = pd.read_sql_query("SELECT * FROM evaluaciones", conn)
    
    meses_esp = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    if df_eval.empty:
        st.info("Sin datos registrados aún.")
    else:
        df_eval['fecha_registro'] = pd.to_datetime(df_eval['fecha_registro'])
        df_eval['Año'] = df_eval['fecha_registro'].dt.year
        df_eval['Mes'] = df_eval['fecha_registro'].dt.month.apply(lambda x: meses_esp[x-1])

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            c = conn.cursor()
            c.execute("SELECT nombre FROM campañas WHERE estado='Activo'")
            camps = ["Ver Todas"] + [r[0] for r in c.fetchall()]
            sel_camp = st.selectbox("Campaña:", camps)
        with col_f2:
            años_db = sorted(df_eval['Año'].unique().tolist(), reverse=True)
            sel_año = st.selectbox("Año:", años_db)
        with col_f3:
            sel_mes = st.selectbox("Mes:", meses_esp, index=datetime.now().month - 1)

        df_f = df_eval[(df_eval['Año'] == sel_año) & (df_eval['Mes'] == sel_mes)]
        if sel_camp != "Ver Todas":
            df_f = df_f[df_f['area'] == sel_camp]

        if df_f.empty:
            st.warning(f"No hay datos para {sel_mes} de {sel_año}.")
        else:
            df_cons = df_f.groupby(['fecha_registro', 'agente', 'area']).agg(
                Suma_Obtenida=('puntos_obtenidos', 'sum'),
                Suma_Maxima=('puntos_maximos', 'sum')
            ).reset_index()
            df_cons['% Final'] = (df_cons['Suma_Obtenida'] / df_cons['Suma_Maxima']) * 100

            st.metric("Monitoreos realizados", len(df_cons))

            if sel_camp == "Ver Todas":
                fig1 = px.bar(df_cons.groupby('area')['% Final'].mean().reset_index(), 
                              x='area', y='% Final', title="Promedio Global por Campaña",
                              color='% Final', color_continuous_scale='Blues', text_auto='.1f')
                st.plotly_chart(fig1, use_container_width=True)
            else:
                fig_a = px.bar(df_cons.groupby('agente')['% Final'].mean().reset_index(), 
                               x='agente', y='% Final', title=f"Desempeño de Asesores: {sel_camp}",
                               color='% Final', color_continuous_scale='Blues', text_auto='.1f')
                st.plotly_chart(fig_a, use_container_width=True)
    conn.close()

# --- 📝 EVALUADOR (RESTORED WITH FEEDBACK) ---
elif choice == "Evaluador":
    st.header("📝 Evaluación de Calidad")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT area FROM scorecards")
    areas = [r[0] for r in c.fetchall()]
    
    if not areas:
        st.warning("Configura scorecards primero.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1: a_sel = st.selectbox("Campaña", areas)
        with c2:
            c.execute("SELECT username FROM usuarios WHERE rol='Agente' AND campaña=? AND estado='Activo'", (a_sel,))
            ags = [r[0] for r in c.fetchall()]
            ag_sel = st.selectbox("Agente", ags) if ags else st.text_input("Nombre Agente (Manual)")
        with c3: f_ev = st.date_input("Fecha de Evento", datetime.now())
        with c4: t_eval = st.selectbox("Evaluado por:", ["Calidad", "Operaciones"])

        c.execute("SELECT id, pregunta, puntos, tipo FROM scorecards WHERE area=?", (a_sel,))
        pregs = c.fetchall()
        resps = {}
        
        st.markdown("---")
        for idp, txt, pts, t in pregs:
            if t == "Sí / No":
                r = st.radio(txt, ["Sí", "No"], key=idp)
                resps[idp] = {"o": pts if r == "Sí" else 0, "m": pts, "t": txt}
            else:
                r = st.slider(txt, 0, pts, pts, key=idp)
                resps[idp] = {"o": r, "m": pts, "t": txt}
        
        st.markdown("---")
        obs = st.text_area("Observaciones y Feedback")
        
        # Lógica de Score y Feedback Visual
        s_o = sum(x["o"] for x in resps.values())
        s_m = sum(x["m"] for x in resps.values())
        pct = (s_o/s_m*100) if s_m>0 else 0
        
        st.markdown("### 🎯 Resultado de la Evaluación")
        
        # Indicadores de estado restaurados
        if pct >= 90:
            st.metric("Score Final", f"{pct:.1f}%", delta="🎯 Excelente", delta_color="normal")
        elif pct >= 80:
            st.metric("Score Final", f"{pct:.1f}%", delta="✔️ Aprobado", delta_color="off")
        else:
            st.metric("Score Final", f"{pct:.1f}%", delta="🚨 Requiere Mejora", delta_color="inverse")

        if st.button("💾 Guardar Evaluación"):
            f_r = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for idp, v in resps.items():
                c.execute('''INSERT INTO evaluaciones 
                             (fecha_registro, fecha_evento, area, evaluador, agente, pregunta, 
                              puntos_obtenidos, puntos_maximos, observaciones, tipo_evaluador) 
                             VALUES (?,?,?,?,?,?,?,?,?,?)''',
                          (f_r, str(f_ev), a_sel, user_data['user'], ag_sel, v['t'], v['o'], v['m'], obs, t_eval))
            conn.commit()
            st.success(f"✅ Evaluación guardada exitosamente con un puntaje de {pct:.1f}%")
    conn.close()

# --- ⚙️ CONFIG SCORECARDS ---
elif choice == "Config Scorecards":
    st.header("⚙️ Configuración de Scorecards")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT nombre FROM campañas WHERE estado='Activo'")
    c_act = [r[0] for r in c.fetchall()]
    if not c_act: st.warning("Crea una campaña activa primero.")
    else:
        with st.form("sc"):
            f_c = st.selectbox("Campaña", c_act)
            f_p = st.text_input("Criterio")
            f_t = st.selectbox("Tipo", ["Escala (Slider)", "Sí / No"])
            f_pts = st.number_input("Puntos", 1, 100, 10)
            if st.form_submit_button("Añadir Criterio"):
                c.execute("INSERT INTO scorecards (area, pregunta, puntos, tipo) VALUES (?,?,?,?)", (f_c, f_p, f_pts, f_t))
                conn.commit()
                st.success("Criterio añadido.")
    st.dataframe(pd.read_sql_query("SELECT * FROM scorecards", conn), use_container_width=True)
    conn.close()

# --- 📁 GESTIÓN CAMPAÑAS ---
elif choice == "Gestión Campañas":
    st.header("📁 Administración de Campañas")
    conn = get_connection()
    c = conn.cursor()
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Acciones")
        modo = st.radio("Operación:", ["Nueva", "Editar Existente"])
        if modo == "Nueva":
            nc = st.text_input("Nombre Campaña")
            if st.button("Guardar Nueva"):
                if nc:
                    try:
                        c.execute("INSERT INTO campañas (nombre) VALUES (?)", (nc,))
                        conn.commit(); st.success("Creada"); st.rerun()
                    except: st.error("Error al crear.")
        else:
            c.execute("SELECT id, nombre FROM campañas")
            lista = c.fetchall()
            if lista:
                sel_edit = st.selectbox("Seleccionar:", [f"{r[0]}-{r[1]}" for r in lista])
                nuevo_n = st.text_input("Nuevo Nombre")
                if st.button("Actualizar"):
                    c.execute("UPDATE campañas SET nombre=? WHERE id=?", (nuevo_n, sel_edit.split("-")[0]))
                    conn.commit(); st.rerun()

    with col2:
        df_c = pd.read_sql_query("SELECT * FROM campañas", conn)
        st.dataframe(df_c, use_container_width=True)
    conn.close()

# --- 👥 GESTIÓN USUARIOS ---
elif choice == "Gestión Usuarios":
    st.header("👥 Gestión de Usuarios")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT nombre FROM campañas WHERE estado='Activo'")
    camps_avail = [r[0] for r in c.fetchall()]
    
    col_u1, col_u2 = st.columns([1, 2])
    with col_u1:
        modo_u = st.radio("Operación:", ["Nuevo", "Editar"])
        if modo_u == "Nuevo":
            nu = st.text_input("Username")
            np = st.text_input("Password")
            nr = st.selectbox("Rol", ["Administrador", "Evaluador", "Agente"])
            nc_u = st.selectbox("Campaña", ["Todas"] + camps_avail)
            if st.button("Registrar Usuario"):
                c.execute("INSERT INTO usuarios (username, password, rol, campaña) VALUES (?,?,?,?)", (nu, np, nr, nc_u))
                conn.commit(); st.success("Registrado"); st.rerun()
    with col_u2:
        df_u = pd.read_sql_query("SELECT id, username, rol, campaña, estado FROM usuarios", conn)
        st.dataframe(df_u, use_container_width=True)
    conn.close()

# --- 📈 VISTA AGENTE ---
elif choice == "Mis Calificaciones":
    st.header(f"📈 Panel de Resultados: {user_data['user']}")
    conn = get_connection()
    query = "SELECT * FROM evaluaciones WHERE LOWER(agente) = LOWER(?)"
    df_raw = pd.read_sql_query(query, conn, params=(user_data['user'],))
    conn.close()
    if df_raw.empty:
        st.warning("Sin evaluaciones registradas.")
    else:
        df_raw['observaciones'] = df_raw['observaciones'].fillna('Sin comentarios')
        df_resumen = df_raw.groupby(['fecha_registro', 'area', 'observaciones']).agg(
            Obtenido=('puntos_obtenidos', 'sum'), Maximo=('puntos_maximos', 'sum')
        ).reset_index()
        df_resumen['% Score'] = (df_resumen['Obtenido'] / df_resumen['Maximo']) * 100
        st.dataframe(df_resumen[['fecha_registro', 'area', 'Obtenido', '% Score', 'observaciones']], use_container_width=True, hide_index=True)
