import streamlit as st
import pandas as pd
import plotly.express as px

st.title("COT Positions Viewer 📊")

# Cargar el archivo fijo CME.xlsx
@st.cache_data
def load_data():
    return pd.read_excel("CME.xlsx")

df = load_data()
st.write("Vista previa de los datos:", df.head())

# Convertir columna de fechas a tipo datetime
df["As of Date in Form YYYY-MM-DD"] = pd.to_datetime(df["As of Date in Form YYYY-MM-DD"])

# Crear gráfico interactivo con Plotly
fig = px.line(
    df,
    x="As of Date in Form YYYY-MM-DD",
    y=[
        "Noncommercial Positions-Long (All)",
        "Noncommercial Positions-Short (All)",
        "Commercial Positions-Long (All)",
        "Commercial Positions-Short (All)",
    ],
    labels={"value": "Posiciones", "variable": "Tipo de posición", "As of Date in Form YYYY-MM-DD": "Fecha"},
    title="COT Positions (Commercial vs Noncommercial)"
)

st.plotly_chart(fig, use_container_width=True)
