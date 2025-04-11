# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from utils import (
    procesar_archivo,
    cargar_desde_google_sheets,
    kpis_generales,
    graficar_plotly_candidatos_viables,
    graficar_plotly_descartes,
    graficar_plotly_comparativa
)

st.set_page_config(page_title="Dashboard de Reclutamiento", layout="wide")
st.title("📊 Dashboard de Reclutamiento")

params = st.query_params
sheet_id = params.get("sheet_id")
sheet_name = params.get("sheet_name")

opcion = st.radio("Origen de datos:", ["CSV", "Google Sheets", "Auto (desde link)"])

df_limpio, stats = None, None

if opcion == "CSV":
    uploaded_file = st.file_uploader("Carga un archivo CSV con datos de reclutamiento", type=["csv"])
    if uploaded_file:
        df_limpio, stats = procesar_archivo(uploaded_file)

elif opcion == "Google Sheets":
    manual_id = st.text_input("🔗 ID del archivo de Google Sheets")
    manual_name = st.text_input("📄 Nombre de la hoja")
    creds = st.file_uploader("🔐 Sube credenciales JSON de cuenta de servicio", type='json')

    if manual_id and manual_name and creds:
        df_limpio, stats = cargar_desde_google_sheets(manual_id, manual_name, creds)

elif opcion == "Auto (desde link)":
    st.info("Usando parámetros del URL para cargar hoja automáticamente")
    creds = st.file_uploader("🔐 Sube credenciales JSON de cuenta de servicio", type='json')

    if sheet_id and sheet_name and creds:
        df_limpio, stats = cargar_desde_google_sheets(sheet_id, sheet_name, creds)

if df_limpio is not None:
    st.dataframe(df_limpio, use_container_width=True)

    total, viables, conversion, descarte = kpis_generales(df_limpio)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total candidatos", total)
    col2.metric("✅ Viables", viables)
    col3.metric("📈 % Conversión", f"{conversion:.1f}%")
    col4.metric("🚫 % Descarte", f"{descarte:.1f}%")

    st.plotly_chart(graficar_plotly_candidatos_viables(df_limpio), use_container_width=True)
    st.plotly_chart(graficar_plotly_descartes(df_limpio), use_container_width=True)
    st.plotly_chart(graficar_plotly_comparativa(df_limpio), use_container_width=True)

    if stats is not None:
        st.subheader("📊 Estadísticas Visuales por Mes")
        option = st.selectbox("Selecciona tipo de estadística", stats.columns.levels[1])
        stat_df = stats.xs(option, axis=1, level=1)
        st.plotly_chart(px.imshow(stat_df.T, aspect='auto', title=f"Heatmap: {option} por variable"))
else:
    st.info("Carga un archivo para iniciar.")
