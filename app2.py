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

need = [COL_MARKET, COL_DATE, COL_NC_L, COL_NC_S, COL_C_L, COL_C_S]
missing = [c for c in need if c not in df.columns]
if missing:
    st.error(f"Faltan columnas en el archivo: {missing}")
    st.stop()

# -------------------- Sidebar: filtros --------------------
markets = sorted(df[COL_MARKET].dropna().unique().tolist())
sel_market = st.sidebar.selectbox("🔎 Mercado", markets, index=0)

all_years = sorted(df[COL_DATE].dt.year.dropna().astype(int).unique().tolist())
y_min, y_max = int(min(all_years)), int(max(all_years))
default_start = max(y_min, y_max - 1) if y_max > y_min else y_min
sel_years = st.sidebar.slider("📅 Rango de años", min_value=y_min, max_value=y_max,
                              value=(default_start, y_max), step=1)

df_plot = df[(df[COL_MARKET] == sel_market) &
             (df[COL_DATE].dt.year.between(sel_years[0], sel_years[1]))].copy()
df_plot = df_plot.sort_values(COL_DATE)

if df_plot.empty:
    st.info("No hay datos para el mercado/años seleccionado(s).")
    st.stop()

# -------------------- Derivados (netos) --------------------
df_plot["NC Net"] = df_plot[COL_NC_L] - df_plot[COL_NC_S]
df_plot["C Net"]  = df_plot[COL_C_L]  - df_plot[COL_C_S]

# -------------------- KPIs + Sentimiento (basado en NONCOMMERCIALS) --------------------
st.subheader(f"{sel_market} – {sel_years[0]}–{sel_years[1]}")

def build_sentiment_from_nc(nc_net_now: float, nc_net_4w: float | None) -> tuple[str, str, float, float]:
    """
    Dirección por signo de NC Net actual (Alcista/Bajista/Neutral).
    Intensidad por |% cambio 4 semanas| de NC Net.
    Devuelve (label, color_hex, delta_abs, delta_pct).
    """
    # delta 4 semanas
    if nc_net_4w is None or pd.isna(nc_net_4w):
        delta_abs = np.nan
        delta_pct = np.nan
    else:
        delta_abs = nc_net_now - nc_net_4w
        denom = max(1.0, abs(nc_net_4w))  # evita división por ~0
        delta_pct = (delta_abs / denom) * 100.0

    # dirección por signo
    eps = 1e-9
    if nc_net_now > eps:
        base = "Alcista"
        palette = {"ligera": "#58d68d", "media": "#27ae60", "fuerte": "#0ea65d"}
    elif nc_net_now < -eps:
        base = "Bajista"
        palette = {"ligera": "#e67e22", "media": "#d35400", "fuerte": "#c0392b"}
    else:
        return ("Sentimiento Neutral", "#808080", delta_abs, delta_pct)

    mag = abs(delta_pct) if not pd.isna(delta_pct) else 0.0
    if mag >= 30:
        label = f"Sentimiento {base}"
        color = palette["fuerte"]
    elif 15 <= mag < 30:
        label = f"Sentimiento Medianamente {base}"
        color = palette["media"]
    elif 5 <= mag < 15:
        label = f"Sentimiento Ligeramente {base}"
        color = palette["ligera"]
    else:
        label = "Sentimiento Neutral"
        color = "#808080"

    return (label, color, delta_abs, delta_pct)

last = df_plot.iloc[-1]
if len(df_plot) >= 5:
    nc_net_4w = df_plot.iloc[-5]["NC Net"]  # ~4 semanas atrás
else:
    nc_net_4w = np.nan

# Fila 1: Netos + Tarjeta de Sentimiento (NC-based)
c1, c2, c3 = st.columns([1, 1, 1.2])

with c1:
    if len(df_plot) >= 2:
        prev = df_plot.iloc[-2]
        c1.metric("NC Net", f"{int(last['NC Net']):,}", int(last["NC Net"] - prev["NC Net"]))
    else:
        st.metric("NC Net", f"{int(last['NC Net']):,}")

with c2:
    if len(df_plot) >= 2:
        prev = df_plot.iloc[-2]
        c2.metric("C Net", f"{int(last['C Net']):,}", int(last["C Net"] - prev["C Net"]))
    else:
        st.metric("C Net", f"{int(last['C Net']):,}")

with c3:
    sentiment_text, sentiment_color, nc_delta_abs, nc_delta_pct = build_sentiment_from_nc(last["NC Net"], nc_net_4w)
    st.markdown(
        f"""
        <div style="
            padding:14px 18px;
            border-radius:14px;
            background:{sentiment_color}22;
            border:1px solid {sentiment_color};
        ">
            <div style="font-weight:700; font-size:18px; color:{sentiment_color};">{sentiment_text}</div>
            <div style="color:#555; margin-top:4px;">
                Cambio 4 semanas (NC Net): 
                <b>{'—' if pd.isna(nc_delta_abs) else f'{int(nc_delta_abs):,}'}</b> contratos 
                ({'—' if pd.isna(nc_delta_pct) else f'{nc_delta_pct:.1f}%'}).
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.caption(f"Última fecha en el rango: {last[COL_DATE].date():%d/%m/%Y}")

# Fila 2: Totales Long/Short (último dato)
c4, c5, c6, c7 = st.columns(4)
c4.metric("NC Long (último)",  f"{int(last[COL_NC_L]):,}")
c5.metric("NC Short (último)", f"{int(last[COL_NC_S]):,}")
c6.metric("C Long (último)",   f"{int(last[COL_C_L]):,}")
c7.metric("C Short (último)",  f"{int(last[COL_C_S]):,}")

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

# -------------------- Tabs --------------------
tab1, tab2 = st.tabs(["Netos (C vs NC)", "Variación mensual (%)"])

with tab1:
    fig_nets = px.line(
        df_plot, x=COL_DATE, y=["NC Net", "C Net"],
        labels={"value": "Contratos (Netos)", "variable": "Serie", COL_DATE: "Fecha"},
        title=f"Posiciones Netas – Commercial vs Noncommercial ({sel_years[0]}–{sel_years[1]})"
    )
    fig_nets.add_hline(y=0, line_dash="dash", opacity=0.5)
    st.plotly_chart(fig_nets, use_container_width=True)

with tab2:
    cA, cB = st.columns(2)

    with cA:
        base_nc = df_m["NC Net %MoM"]
        colors_nc = np.where(base_nc.fillna(0) >= 0, "rgb(0,150,100)", "rgb(200,60,60)")
        fig_nc = go.Figure(go.Bar(x=df_m.index, y=base_nc, marker_color=colors_nc, name="NC Net %MoM"))
        fig_nc.update_layout(
            title="No-Commercial: variación mensual de netos (%)",
            xaxis_title="Mes", yaxis_title="% mensual", bargap=0.15, showlegend=False
        )
        fig_nc.add_hline(y=0, line_dash="dash", opacity=0.5)
        st.plotly_chart(fig_nc, use_container_width=True)

    with cB:
        base_c = df_m["C Net %MoM"]
        colors_c = np.where(base_c.fillna(0) >= 0, "rgb(0,150,100)", "rgb(200,60,60)")
        fig_c = go.Figure(go.Bar(x=df_m.index, y=base_c, marker_color=colors_c, name="C Net %MoM"))
        fig_c.update_layout(
            title="Commercial: variación mensual de netos (%)",
            xaxis_title="Mes", yaxis_title="% mensual", bargap=0.15, showlegend=False
        )
        fig_c.add_hline(y=0, line_dash="dash", opacity=0.5)
        st.plotly_chart(fig_c, use_container_width=True)

    st.caption("Nota: % mensual calculado con el último valor de cada mes. Si el valor previo es 0 o no existe, el % se deja como NaN para evitar distorsiones.")
