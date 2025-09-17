import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="COT – Netos y Variación Mensual", layout="wide")
st.title("COT – Posiciones Netas y Variación Mensual (CME)")

# -------------------- Carga de datos --------------------
@st.cache_data
def load_data(path: str = "CME.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    if "As of Date in Form YYYY-MM-DD" in df.columns:
        df["As of Date in Form YYYY-MM-DD"] = pd.to_datetime(
            df["As of Date in Form YYYY-MM-DD"], errors="coerce", dayfirst=True
        )
    return df

df = load_data()

# -------------------- Columnas esperadas --------------------
COL_MARKET = "Market and Exchange Names"
COL_DATE   = "As of Date in Form YYYY-MM-DD"
COL_NC_L   = "Noncommercial Positions-Long (All)"
COL_NC_S   = "Noncommercial Positions-Short (All)"
COL_C_L    = "Commercial Positions-Long (All)"
COL_C_S    = "Commercial Positions-Short (All)"
COL_OI     = "Open Interest (All)"

need = [COL_MARKET, COL_DATE, COL_NC_L, COL_NC_S, COL_C_L, COL_C_S]
missing = [c for c in need if c not in df.columns]
if missing:
    st.error(f"Faltan columnas en el archivo: {missing}")
    st.stop()

# -------------------- Sidebar: filtros --------------------
markets = sorted(df[COL_MARKET].dropna().unique().tolist())
sel_market = st.sidebar.selectbox("🔎 Mercado", markets, index=0)

years = sorted(df[COL_DATE].dt.year.dropna().unique().tolist())
sel_year = st.sidebar.selectbox("📅 Año", years, index=len(years)-1)

df_plot = df[(df[COL_MARKET] == sel_market) & (df[COL_DATE].dt.year == sel_year)].copy()
df_plot = df_plot.sort_values(COL_DATE)

if df_plot.empty:
    st.info("No hay datos para el mercado/año seleccionado.")
    st.stop()

# -------------------- Derivados (netos y %OI) --------------------
df_plot["NC Net"] = df_plot[COL_NC_L] - df_plot[COL_NC_S]
df_plot["C Net"]  = df_plot[COL_C_L]  - df_plot[COL_C_S]

if COL_OI in df_plot.columns:
    with pd.option_context("mode.use_inf_as_na", True):
        df_plot["NC Net %OI"] = 100 * df_plot["NC Net"] / df_plot[COL_OI]
        df_plot["C Net %OI"]  = 100 * df_plot["C Net"]  / df_plot[COL_OI]
else:
    df_plot["NC Net %OI"] = pd.NA
    df_plot["C Net %OI"]  = pd.NA

# -------------------- KPIs --------------------
st.subheader(f"{sel_market} – {sel_year}")
if len(df_plot) >= 2:
    last = df_plot.iloc[-1]
    prev = df_plot.iloc[-2]
    c1, c2, c3 = st.columns(3)
    c1.metric("NC Net", f"{int(last['NC Net']):,}", int(last["NC Net"] - prev["NC Net"]))
    c2.metric("C Net",  f"{int(last['C Net']):,}",  int(last["C Net"]  - prev["C Net"]))
    if pd.notna(last.get("NC Net %OI")):
        c3.metric("NC Net %OI", f"{last['NC Net %OI']:.2f}%",
                  None if pd.isna(prev.get('NC Net %OI')) else f"{last['NC Net %OI']-prev['NC Net %OI']:.2f}")
    else:
        c3.metric("NC Net %OI", "—")
    st.caption(f"Última fecha en {sel_year}: {last[COL_DATE].date():%d/%m/%Y}")
else:
    st.info("Muy pocos registros en el rango para calcular métricas.")

# -------------------- Variación mensual (%) de netos --------------------
df_m = (
    df_plot.set_index(COL_DATE)[["NC Net", "C Net"]]
    .resample("M").last()
    .dropna(how="all")
)

def pct_change_safe(series: pd.Series) -> pd.Series:
    prev = series.shift(1)
    pct = (series - prev) / prev.abs() * 100.0
    pct = pct.mask((prev.abs() < 1e-12) | prev.isna())
    return pct

df_m["NC Net %MoM"] = pct_change_safe(df_m["NC Net"])
df_m["C Net %MoM"]  = pct_change_safe(df_m["C Net"])

clip_pct = st.sidebar.slider("Limitar % mensual a ±", min_value=10, max_value=500, value=200, step=10)
df_m["NC Net %MoM clipped"] = df_m["NC Net %MoM"].clip(lower=-clip_pct, upper=clip_pct)
df_m["C Net %MoM clipped"]  = df_m["C Net %MoM"].clip(lower=-clip_pct, upper=clip_pct)

# -------------------- Tabs --------------------
tab1, tab2 = st.tabs(["Netos (C vs NC)", "Variación mensual (%)"])

with tab1:
    fig_nets = px.line(
        df_plot, x=COL_DATE, y=["NC Net", "C Net"],
        labels={"value": "Contratos (Netos)", "variable": "Serie", COL_DATE: "Fecha"},
        title=f"Posiciones Netas – Commercial vs Noncommercial ({sel_year})"
    )
    fig_nets.add_hline(y=0, line_dash="dash", opacity=0.5)
    st.plotly_chart(fig_nets, use_container_width=True)

    if df_plot["NC Net %OI"].notna().any():
        fig_pct = px.line(
            df_plot, x=COL_DATE, y=["NC Net %OI", "C Net %OI"],
            labels={"value": "% del Open Interest", "variable": "Serie", COL_DATE: "Fecha"},
            title=f"Netos como % del Open Interest ({sel_year})"
        )
        fig_pct.add_hline(y=0, line_dash="dash", opacity=0.5)
        st.plotly_chart(fig_pct, use_container_width=True)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        y_nc = "NC Net %MoM clipped"
        colors_nc = np.where(df_m[y_nc] >= 0, "rgb(0,150,100)", "rgb(200,60,60)")
        fig_nc = go.Figure(go.Bar(x=df_m.index, y=df_m[y_nc], marker_color=colors_nc))
        fig_nc.update_layout(
            title="No-Commercial: variación mensual de netos (%)",
            xaxis_title="Mes", yaxis_title="% mensual", bargap=0.15
        )
        fig_nc.add_hline(y=0, line_dash="dash", opacity=0.5)
        st.plotly_chart(fig_nc, use_container_width=True)

    with c2:
        y_c = "C Net %MoM clipped"
        colors_c = np.where(df_m[y_c] >= 0, "rgb(0,150,100)", "rgb(200,60,60)")
        fig_c = go.Figure(go.Bar(x=df_m.index, y=df_m[y_c], marker_color=colors_c))
        fig_c.update_layout(
            title="Commercial: variación mensual de netos (%)",
            xaxis_title="Mes", yaxis_title="% mensual", bargap=0.15
        )
        fig_c.add_hline(y=0, line_dash="dash", opacity=0.5)
        st.plotly_chart(fig_c, use_container_width=True)

    st.caption(
        f"Nota: % mensual calculado con el último valor de cada mes. "
        f"Se evita dividir por cero y los cambios extremos se recortan a ±{clip_pct}%."
    )
