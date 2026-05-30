import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from urllib.parse import quote 

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="QualityScore Enterprise", layout="wide")
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwOzQXYSGb1aFciCb28ivzWtV9PjhITXKpacPTzpszvEoCFFcxlr5AUgn1V-g1lHyuJ/exec" 

def get_data(nombre_ho_ja):
    try:
        url_base = st.secrets["url_base"].split('/export')[0]
        url_final = f"{url_base}/gviz/tq?tqx=out:csv&sheet={quote(nombre_ho_ja)}&cache={datetime.now().timestamp()}"
        df = pd.read_csv(url_final, on_bad_lines='skip')
        if not df.empty:
            df.columns = [str(c).strip().split('\n')[0].lower() for c in df.columns]
        return df
    except: return pd.DataFrame()

# --- LOGIN SIMPLIFICADO ---
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    u_log = st.text_input("Usuario")
    p_log = st.text_input("Password", type="password")
    if st.button("Entrar"):
        if u_log == "admin" and p_log == "admin123":
            st.session_state.update({"autenticado": True, "user_data": {"nombre":"Admin","rol":"Administrador","campaña":"Todas"}})
            st.rerun()
    st.stop()

# --- MENÚ LATERAL ---
user = st.session_state["user_data"]
menu = ["Dashboard", "Evaluador", "Configuraciones"]
choice = st.sidebar.selectbox("Ir a:", menu)

if choice == "Dashboard":
    st.header("📊 Analítica de Calidad")
    df_eval = get_data("evaluaciones")
    
    if not df_eval.empty:
        # Filtros rápidos
        sel_camp = st.selectbox("Campaña", ["Todas"] + get_data("campañas").iloc[:,0].tolist())
        
        df_f = df_eval.copy()
        if sel_camp != "Todas": df_f = df_f[df_f.iloc[:,1] == sel_camp]
        
        if not df_f.empty:
            # Cálculo de Score Real
            df_f['p_obt'] = pd.to_numeric(df_f.iloc[:,4], errors='coerce').fillna(0)
            df_f['p_max'] = pd.to_numeric(df_f.iloc[:,5], errors='coerce').fillna(1)
            promedio_actual = (df_f['p_obt'].sum() / df_f['p_max'].sum()) * 100
            
            st.metric("Cumplimiento General", f"{promedio_actual:.1f}%")

            # --- GRÁFICA BINARIA (EL CAMBIO QUE NECESITAS) ---
            st.subheader("Cumplimiento por Atributo")
            df_sc = get_data("scorecards")
            if sel_camp != "Todas":
                items = df_sc[df_sc.iloc[:,0] == sel_camp].copy()
                
                # Lógica: Si el promedio general es menor a 100, 
                # restamos los puntos de la gráfica empezando por el final.
                def logic_binaria(row):
                    puntos_item = row.iloc[2]
                    # Si el score es 100, todo es azul. Si es menos, mostramos qué falló.
                    if promedio_actual >= 100: return puntos_item
                    # Si la pérdida total es mayor o igual al peso de este item, lo ponemos en 0
                    return 0 if (100 - promedio_actual) >= puntos_item else puntos_item

                items['Cumplimiento'] = items.apply(logic_binaria, axis=1)
                
                fig = px.bar(items, x='Cumplimiento', y=items.columns[1], orientation='h',
                             color='Cumplimiento', color_continuous_scale=[(0,'#D3D3D3'), (1,'#1F77B4')])
                fig.update_layout(coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
