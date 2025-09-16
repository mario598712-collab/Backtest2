import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("COT Positions Viewer")

# Subir archivo
uploaded_file = st.file_uploader("📂 Sube tu archivo Excel o CSV", type=["xlsx", "csv"])

if uploaded_file:
    # Leer archivo según extensión
    if uploaded_file.name.endswith("xlsx"):
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    else:
        df = pd.read_csv(uploaded_file)

    # Mostrar preview
    st.write("✅ Vista previa de los datos:")
    st.dataframe(df.head())

    # Asegurarnos que la columna de fecha sea datetime
    if "As of Date in Form YYYY-MM-DD" in df.columns:
        df["As of Date in Form YYYY-MM-DD"] = pd.to_datetime(
            df["As of Date in Form YYYY-MM-DD"], errors="coerce"
        )

    # Gráfico
    if all(col in df.columns for col in [
        "As of Date in Form YYYY-MM-DD",
        "Noncommercial Positions-Long (All)",
        "Noncommercial Positions-Short (All)"
    ]):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df["As of Date in Form YYYY-MM-DD"], df["Noncommercial Positions-Long (All)"],
                label="Noncommercial Long", color="green")
        ax.plot(df["As of Date in Form YYYY-MM-DD"], df["Noncommercial Positions-Short (All)"],
                label="Noncommercial Short", color="red")

        ax.set_title("Noncommercial Positions (Long vs Short)")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Número de contratos")
        ax.legend()
        ax.grid(True, alpha=0.3)

        st.pyplot(fig)
    else:
        st.warning("⚠️ No se encontraron las columnas necesarias en tu archivo.")
