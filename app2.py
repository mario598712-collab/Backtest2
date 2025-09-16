import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("COT Positions Viewer")

uploaded_file = st.file_uploader("Sube tu archivo Excel", type=["xlsx", "csv"])
if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith("xlsx") else pd.read_csv(uploaded_file)

    st.write("Vista previa:", df.head())

    # Gráfico ejemplo
    fig, ax = plt.subplots()
    ax.plot(df["As of Date in Form YYYY-MM-DD"], df["Noncommercial Positions-Long (All)"], label="Noncomm Long", color="green")
    ax.plot(df["As of Date in Form YYYY-MM-DD"], df["Noncommercial Positions-Short (All)"], label="Noncomm Short", color="red")
    ax.legend()
    st.pyplot(fig)
