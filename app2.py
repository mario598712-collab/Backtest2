import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="COT – CME FX Viewer", layout="wide")
st.title("COT – CME FX Viewer")

# -------------------- Carga de datos --------------------
@st.cache_data
def load_data(path: str = "CME.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    # Normaliza nombres por si vienen con saltos/espacios raros
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    # Asegura datetime (tu archivo suele venir DD/MM/YYYY)
    if "As of Date in Form YYYY-MM-DD" in df.columns:
        df["As of Date in Form YYYY-MM-DD"] = pd.to_datetime(
            df["As of Date in Form YYYY-MM-DD"], errors="coerce", dayfirst=True
        )
    return df

df = load_data()

# Nombres de columnas esperadas (como tu Excel)
COL_MARKET = "Market and Exchange Names"
COL_DATE   = "As of Date in Form YYYY-MM-DD"
COL_NC_L   = "Noncommercial Positions-Long (All)"
COL_NC_S   = "Noncommercial Positions-Short (All)"
COL_C_L    = "Commercial Positions-Long (All)"
COL_C_S    = "Commercial Positions-Short (All)"

need = [COL_MARKET, COL_DATE, COL_NC_L, COL_NC_S, COL_C_L, COL_C_S]
missing = [c for c in need if c not in df.columns]
if missing:
    st.error(f"Faltan columnas en el archivo: {missing}")
    st.stop()

# -------------------- Sidebar: Filtros --------------------
markets = sorted(df[COL_MARKET].dropna().unique().tolist())
sel_market = st.sidebar.selectbox("🔎 Mercado", markets, index=0)

# Rango de fechas para el mercado seleccionado
df_mkt = df[df[COL_MARKET] == sel_market].copy()
df_mkt = df_mkt.dropna(subset=[COL_DATE]).sort_values(COL_DATE)

if df_mkt.empty:
    st.info("No hay datos para el mercado seleccionado.")
    st.stop()

d_min = df_mkt[COL_DATE].min().date()
d_max = df_mkt[COL_DATE].max().date()
rango = st.sidebar.date_input("📅 Rango de fechas", (d_min, d_max), min_value=d_min, max_value=d_max)

# Asegurar tupla (start, end)
if isinstance(rango, (list, tuple)) and len(rango) == 2:
    d_start, d_end = rango
else:
    d_start, d_end = d_min, d_max

mask = df_mkt[COL_DATE].between(pd.to_datetime(d_start), pd.to_datetime(d_end))
df_plot = df_mkt.loc[mask].copy()

# Métricas derivadas
df_plot["NC Net"] = df_plot[COL_NC_L] - df_plot[COL_NC_S]
df_plot["C Net"]  = df_plot[COL_C_L]  - df_plot[COL_C_S]

# -------------------- KPIs --------------------
st.subheader(sel_market)
if len(df_plot) >= 2:
    last  = df_plot.iloc[-1]
    prev  = df_plot.iloc[-2]
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("NC Long",  f"{int(last[COL_NC_L]):,}",  int(last[COL_NC_L] - prev[COL_NC_L]))
    c2.metric("NC Short", f"{int(last[COL_NC_S]):,}",  int(last[COL_NC_S] - prev[COL_NC_S]))
    c3.metric("NC Net",   f"{int(last['NC Net']):,}",  int(last["NC Net"]  - prev["NC Net"]))
    c4.metric("C Long",   f"{int(last[COL_C_L]):,}",   int(last[COL_C_L]  - prev[COL_C_L]))
    c5.metric("C Short",  f"{int(last[COL_C_S]):,}",   int(last[COL_C_S]  - prev[COL_C_S]))
    c6.metric("C Net",    f"{int(last['C Net']):,}",   int(last["C Net"]   - prev["C Net"]))
    st.caption(f"Última fecha: {last[COL_DATE].date():%d/%m/%Y}")
else:
    st.info("Hay muy pocos registros en el rango para calcular variaciones.")

# -------------------- Gráficos --------------------
tab1, tab2, tab3 = st.tabs(["Largos/Cortos", "Netos", "Tabla"])

with tab1:
    fig1 = px.line(
        df_plot,
        x=COL_DATE,
        y=[COL_NC_L, COL_NC_S, COL_C_L, COL_C_S],
        labels={"value": "Contratos", "variable": "Serie", COL_DATE: "Fecha"},
        title="Largos y Cortos – Noncommercial vs Commercial",
    )
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    fig2 = px.line(
        df_plot,
        x=COL_DATE,
        y=["NC Net", "C Net"],
        labels={"value": "Contratos (Netos)", "variable": "Serie", COL_DATE: "Fecha"},
        title="Posiciones Netas",
    )
    fig2.add_hline(y=0, line_dash="dash", opacity=0.5)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.dataframe(
        df_plot[[COL_DATE, COL_NC_L, COL_NC_S, "NC Net", COL_C_L, COL_C_S, "C Net"]]
        .sort_values(COL_DATE),
        use_container_width=True,
    )
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        df_plot.to_csv(index=False).encode("utf-8"),
        file_name="cot_filtrado.csv",
        mime="text/csv",
    )
