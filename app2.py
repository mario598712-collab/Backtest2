import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="COT – Netos & COT Index", layout="wide")
st.title("COT – Netos & COT Index (CME)")

# -------------------- Carga de datos --------------------
@st.cache_data
def load_data(path: str = "CME.xlsx") -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    # normaliza nombres (quita saltos/espacios)
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    # fechas (tu archivo suele venir DD/MM/YYYY)
    if "As of Date in Form YYYY-MM-DD" in df.columns:
        df["As of Date in Form YYYY-MM-DD"] = pd.to_datetime(
            df["As of Date in Form YYYY-MM-DD"], errors="coerce", dayfirst=True
        )
    return df

df = load_data()

# columnas esperadas
COL_MARKET = "Market and Exchange Names"
COL_DATE   = "As of Date in Form YYYY-MM-DD"
COL_NC_L   = "Noncommercial Positions-Long (All)"
COL_NC_S   = "Noncommercial Positions-Short (All)"
COL_C_L    = "Commercial Positions-Long (All)"
COL_C_S    = "Commercial Positions-Short (All)"
COL_OI     = "Open Interest (All)"  # opcional

need = [COL_MARKET, COL_DATE, COL_NC_L, COL_NC_S, COL_C_L, COL_C_S]
missing = [c for c in need if c not in df.columns]
if missing:
    st.error(f"Faltan columnas en el archivo: {missing}")
    st.stop()

# -------------------- Sidebar: filtros --------------------
markets = sorted(df[COL_MARKET].dropna().unique().tolist())
sel_market = st.sidebar.selectbox("🔎 Mercado", markets, index=0)

df_mkt = df[df[COL_MARKET] == sel_market].dropna(subset=[COL_DATE]).sort_values(COL_DATE)
if df_mkt.empty:
    st.info("No hay datos para el mercado seleccionado.")
    st.stop()

d_min = df_mkt[COL_DATE].min().date()
d_max = df_mkt[COL_DATE].max().date()

rango = st.sidebar.date_input(
    "📅 Rango de fechas",
    (d_min, d_max),
    min_value=d_min, max_value=d_max
)
if isinstance(rango, (list, tuple)) and len(rango) == 2:
    d_start, d_end = rango
else:
    d_start, d_end = d_min, d_max

mask = df_mkt[COL_DATE].between(pd.to_datetime(d_start), pd.to_datetime(d_end))
df_plot = df_mkt.loc[mask].copy()

# -------------------- Derivados --------------------
df_plot["NC Net"] = df_plot[COL_NC_L] - df_plot[COL_NC_S]
df_plot["C Net"]  = df_plot[COL_C_L]  - df_plot[COL_C_S]

# % del OI (si está disponible)
if COL_OI in df_plot.columns:
    with pd.option_context("mode.use_inf_as_na", True):
        df_plot["NC Net %OI"] = 100 * df_plot["NC Net"] / df_plot[COL_OI]
        df_plot["C Net %OI"]  = 100 * df_plot["C Net"]  / df_plot[COL_OI]
else:
    df_plot["NC Net %OI"] = pd.NA
    df_plot["C Net %OI"]  = pd.NA

# COT Index (rolling percentil) configurable
st.sidebar.markdown("---")
win = st.sidebar.select_slider("Ventana COT Index (semanas)", options=[26, 52, 78, 104, 156], value=156)
roll_min = df_plot["NC Net"].rolling(win, min_periods=max(5, int(win*0.2))).min()
roll_max = df_plot["NC Net"].rolling(win, min_periods=max(5, int(win*0.2))).max()
df_plot["COT Index"] = 100 * (df_plot["NC Net"] - roll_min) / (roll_max - roll_min)

# -------------------- KPIs --------------------
st.subheader(sel_market)
if len(df_plot) >= 2:
    last  = df_plot.iloc[-1]
    prev  = df_plot.iloc[-2]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NC Net", f"{int(last['NC Net']):,}", int(last["NC Net"] - prev["NC Net"]))
    c2.metric("C Net",  f"{int(last['C Net']):,}",  int(last["C Net"]  - prev["C Net"]))
    if pd.notna(last.get("NC Net %OI")):
        c3.metric("NC Net %OI", f"{last['NC Net %OI']:.2f}%", 
                  None if pd.isna(prev.get('NC Net %OI')) else f"{last['NC Net %OI']-prev['NC Net %OI']:.2f}")
    else:
        c3.metric("NC Net %OI", "—")
    c4.metric(f"COT Index ({win})", f"{last['COT Index']:.1f}" if pd.notna(last["COT Index"]) else "—",
              None if pd.isna(prev["COT Index"]) else f"{(last['COT Index']-prev['COT Index']):.1f}")
    st.caption(f"Última fecha: {last[COL_DATE].date():%d/%m/%Y}")
else:
    st.info("Hay muy pocos registros en el rango para calcular variaciones.")

# -------------------- Gráficos --------------------
tab1, tab2 = st.tabs(["Netos (C vs NC)", "COT Index"])

with tab1:
    # Netos absolutos
    fig_nets = px.line(
        df_plot, x=COL_DATE, y=["NC Net", "C Net"],
        labels={"value": "Contratos (Netos)", "variable": "Serie", COL_DATE: "Fecha"},
        title="Posiciones Netas – Commercial vs Noncommercial"
    )
    fig_nets.add_hline(y=0, line_dash="dash", opacity=0.5)
    st.plotly_chart(fig_nets, use_container_width=True)

    # Si hay OI, mostramos netos como % del OI debajo
    if df_plot["NC Net %OI"].notna().any():
        fig_pct = px.line(
            df_plot, x=COL_DATE, y=["NC Net %OI", "C Net %OI"],
            labels={"value": "% del Open Interest", "variable": "Serie", COL_DATE: "Fecha"},
            title="Netos como % del Open Interest"
        )
        fig_pct.add_hline(y=0, line_dash="dash", opacity=0.5)
        st.plotly_chart(fig_pct, use_container_width=True)

with tab2:
    fig_idx = px.line(
        df_plot, x=COL_DATE, y="COT Index",
        labels={"COT Index": "Índice (0–100)", COL_DATE: "Fecha"},
        title=f"COT Index (ventana {win} semanas) – Noncommercial Net"
    )
    # bandas 20/80
    fig_idx.add_hline(y=20, line_dash="dot", opacity=0.6)
    fig_idx.add_hline(y=80, line_dash="dot", opacity=0.6)
    st.plotly_chart(fig_idx, use_container_width=True)

    # Hint si la ventana es más grande que el rango
    if df_plot["COT Index"].isna().mean() > 0.5:
        st.caption("ℹ️ Amplía el rango de fechas o usa una ventana menor para ver más COT Index calculado.")
