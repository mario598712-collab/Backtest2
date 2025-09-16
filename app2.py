# app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import re

st.set_page_config(page_title="COT – CME FX Viewer", layout="wide")
st.title("COT – CME FX Viewer")

DATA_PATH = Path(__file__).resolve().parent / "CME.xlsx"

# -------------------- utilidades --------------------
def norm_cols(cols):
    """Aplana saltos de línea y espacios en nombres de columnas."""
    return [re.sub(r"\s+", " ", str(c)).strip() for c in cols]

def required_present(df, req):
    missing = [c for c in req if c not in df.columns]
    return len(missing) == 0, missing

def standardize(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Estandariza columnas clave y calcula métricas derivadas."""
    df = df_raw.copy()
    df.columns = norm_cols(df.columns)

    # Mapas de columnas esperadas (tal como vienen del portal de la CFTC)
    c_market = "Market and Exchange Names"
    c_date   = "As of Date in Form YYYY-MM-DD"
    c_oi     = "Open Interest (All)"
    c_nc_l   = "Noncommercial Positions-Long (All)"
    c_nc_s   = "Noncommercial Positions-Short (All)"
    c_c_l    = "Commercial Positions-Long (All)"
    c_c_s    = "Commercial Positions-Short (All)"

    ok, missing = required_present(df, [c_market, c_date, c_nc_l, c_nc_s, c_c_l, c_c_s])
    if not ok:
        st.error("Faltan columnas en el Excel: " + ", ".join(missing))
        st.stop()

    # Fechas
    df[c_date] = pd.to_datetime(df[c_date], errors="coerce", dayfirst=True)

    out = pd.DataFrame({
        "market": df[c_market].astype(str).str.replace(r"\s+", " ", regex=True).str.strip(),
        "date": df[c_date],
        "open_interest": pd.to_numeric(df.get(c_oi), errors="coerce"),
        "nc_long": pd.to_numeric(df[c_nc_l], errors="coerce"),
        "nc_short": pd.to_numeric(df[c_nc_s], errors="coerce"),
        "c_long": pd.to_numeric(df[c_c_l], errors="coerce"),
        "c_short": pd.to_numeric(df[c_c_s], errors="coerce"),
    }).dropna(subset=["date"]).sort_values("date")

    # Derivados
    out["nc_net"] = out["nc_long"] - out["nc_short"]
    out["c_net"]  = out["c_long"]  - out["c_short"]
    return out.reset_index(drop=True)

def plot_longs_shorts(df_plot):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df_plot["date"], df_plot["nc_long"], label="Noncommercial Long")
    ax.plot(df_plot["date"], df_plot["nc_short"], label="Noncommercial Short")
    ax.plot(df_plot["date"], df_plot["c_long"],  label="Commercial Long")
    ax.plot(df_plot["date"], df_plot["c_short"], label="Commercial Short")
    ax.set_title("Largos & Cortos (Commercial vs Noncommercial)")
    ax.set_xlabel("Fecha"); ax.set_ylabel("Contratos")
    ax.grid(True, alpha=0.3); ax.legend(loc="upper left", ncol=2)
    st.pyplot(fig, clear_figure=True)

def plot_nets(df_plot):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df_plot["date"], df_plot["nc_net"], label="Noncommercial Net")
    ax.plot(df_plot["date"], df_plot["c_net"],  label="Commercial Net")
    ax.axhline(0, ls="--", lw=1, color="k", alpha=0.5)
    ax.set_title("Posiciones Netas")
    ax.set_xlabel("Fecha"); ax.set_ylabel("Contratos (Netos)")
    ax.grid(True, alpha=0.3); ax.legend(loc="upper left")
    st.pyplot(fig, clear_figure=True)

# -------------------- carga de datos --------------------
if not DATA_PATH.exists():
    st.error(f"No encontré el archivo {DATA_PATH.name} en la carpeta del repositorio.")
    st.stop()

try:
    df_raw = pd.read_excel(DATA_PATH, engine="openpyxl")
except Exception as e:
    st.error(f"No pude leer {DATA_PATH.name}: {e}")
    st.stop()

df = standardize(df_raw)

# -------------------- UI: filtros --------------------
markets = sorted(df["market"].unique())
market_sel = st.sidebar.selectbox("Mercado", markets, index=0)

date_min, date_max = df["date"].min(), df["date"].max()
r1, r2 = st.sidebar.date_input(
    "Rango de fechas",
    value=(date_min, date_max),
    min_value=date_min, max_value=date_max
)
mask = (df["market"] == market_sel) & df["date"].between(pd.to_datetime(r1), pd.to_datetime(r2))
df_plot = df[mask].copy()

st.subheader(market_sel)

# KPIs
if len(df_plot) >= 2:
    last, prev = df_plot.iloc[-1], df_plot.iloc[-2]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NC Long",  f'{int(last["nc_long"]):,}',  int(last["nc_long"]-prev["nc_long"]))
    c2.metric("NC Short", f'{int(last["nc_short"]):,}', int(last["nc_short"]-prev["nc_short"]))
    c3.metric("C Long",   f'{int(last["c_long"]):,}',   int(last["c_long"]-prev["c_long"]))
    c4.metric("C Short",  f'{int(last["c_short"]):,}',  int(last["c_short"]-prev["c_short"]))

# Pestañas de gráficos
tab1, tab2, tab3 = st.tabs(["Largos/Cortos", "Netos", "Tabla"])
with tab1:
    if df_plot.empty:
        st.info("No hay datos para el rango seleccionado.")
    else:
        plot_longs_shorts(df_plot)

with tab2:
    if df_plot.empty:
        st.info("No hay datos para el rango seleccionado.")
    else:
        plot_nets(df_plot)

with tab3:
    st.dataframe(df_plot.sort_values("date"), use_container_width=True)
    st.download_button(
        "Descargar CSV filtrado",
        df_plot.to_csv(index=False).encode("utf-8"),
        file_name="cot_filtrado.csv",
        mime="text/csv"
    )
