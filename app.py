# --- BUSCA ESTA SECCIÓN EN TU CÓDIGO (DASHBOARD) Y REEMPLÁZALA ---

if choice == "Dashboard":
    st.header("📊 Dashboard de Calidad")
    df_ev = get_data("evaluaciones")
    if not df_ev.empty:
        # Resolvemos nombres de columnas
        col_fecha = 'fecha_registro' if 'fecha_registro' in df_ev.columns else df_ev.columns[0]
        col_puntos = 'puntos_obtenidos' if 'puntos_obtenidos' in df_ev.columns else df_ev.columns[4]
        col_max = 'puntos_maximos' if 'puntos_maximos' in df_ev.columns else df_ev.columns[5]
        
        # --- CORRECCIÓN DEL ERROR DE TIPO (TRUEDIV) ---
        # Convertimos a numérico forzando errores a NaN y luego a 0 para poder dividir
        df_ev[col_puntos] = pd.to_numeric(df_ev[col_puntos], errors='coerce').fillna(0)
        df_ev[col_max] = pd.to_numeric(df_ev[col_max], errors='coerce').fillna(1) # Evitamos división por cero
        
        df_ev[col_fecha] = pd.to_datetime(df_ev[col_fecha], errors='coerce')
        
        # Ahora la división funcionará porque ambos son floats/ints
        df_ev['% score'] = (df_ev[col_puntos] / df_ev[col_max]) * 100
        
        m1, m2 = st.columns(2)
        m1.metric("Promedio General", f"{df_ev['% score'].mean():.1f}%")
        m2.metric("Total Evaluaciones", len(df_ev))
        
        fig = px.bar(df_ev.groupby('agente')['% score'].mean().reset_index(), 
                     x='agente', y='% score', color='% score', text_auto='.1f', title="Desempeño por Agente")
        st.plotly_chart(fig, use_container_width=True)
    else: 
        st.info("No hay datos registrados.")
