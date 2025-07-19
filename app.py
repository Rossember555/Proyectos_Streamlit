# ============================================================
# DASHBOARD DE VENTAS PRO  —  Diseño Glass / Hero Integrado
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
import requests
from streamlit_option_menu import option_menu
from datetime import date

# ------------------------------------------------------------
# 1. CONFIGURACIÓN BÁSICA DE LA PÁGINA
# ------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard de Ventas PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# 2. UTILIDADES
# ------------------------------------------------------------
def get_data(seed: int = 42, n: int = 5000) -> pd.DataFrame:
    """Genera datos sintéticos de ventas reproducibles."""
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", "2025-07-31", freq="D")
    categories = ["Electrónica", "Ropa", "Hogar", "Alimentos"]
    regions = ["Norte", "Sur", "Este", "Oeste"]

    return pd.DataFrame({
        "Fecha": np.random.choice(dates, n),
        "Categoría": np.random.choice(categories, n),
        "Región": np.random.choice(regions, n),
        "Ventas": np.random.gamma(shape=5, scale=120, size=n).round(2),
    })

def fmt_moneda(x, dec=0):
    """Formatea números a moneda en español CO/ES (puntos miles, coma dec)."""
    if pd.isna(x):
        return "—"
    pattern = f"{{:,.{dec}f}}"
    return "$" + pattern.format(x).replace(",", "X").replace(".", ",").replace("X", ".")

def delta_pct(actual, pasado):
    if pasado in (0, None) or pd.isna(pasado):
        return np.nan
    return (actual - pasado) / pasado * 100

def badge(pct):
    """Devuelve span HTML con flecha ↑/↓ y color."""
    if pd.isna(pct):
        return "<span style='color:#9ca3af'>n/d</span>"
    arrow = "▲" if pct >= 0 else "▼"
    color = "#16a34a" if pct >= 0 else "#dc2626"
    return f"<span style='color:{color};font-size:0.85rem;'>{arrow} {pct:,.1f}%</span>"

def periodo_anterior(df, rango, modo="dias"):
    """Devuelve DataFrame del periodo comparable (anterior o mismo rango hace 1 año)."""
    ini, fin = pd.to_datetime(rango[0]), pd.to_datetime(rango[1])
    if modo == "dias":           # mismo nº de días inmediatamente anterior
        dias = (fin - ini).days + 1
        fin_prev = ini - pd.Timedelta(days=1)
        ini_prev = fin_prev - pd.Timedelta(days=dias-1)
    else:                        # 'anio': mismo rango pero -1 año
        ini_prev = ini - pd.DateOffset(years=1)
        fin_prev = fin - pd.DateOffset(years=1)
    return df[(df["Fecha"] >= ini_prev) & (df["Fecha"] <= fin_prev)]

# ------------------------------------------------------------
# 3. CARGA DE DATOS (caché)
# ------------------------------------------------------------
@st.cache_data
def load_df():
    return get_data()

df_full = load_df()

# ------------------------------------------------------------
# 4. ESTILOS GLOBAL (CSS)
# ------------------------------------------------------------
st.markdown("""
<style>
:root{
  --red:#ff4b4b; --mag:#f72585; --green:#0f9d58;
  --glass-bg:rgba(255,255,255,.08); --glass-brd:rgba(255,255,255,.15);
  --blur:12px;
}
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
/* ---------- HERO ---------- */
.hero{
  display:flex;align-items:center;justify-content:space-between;gap:1.8rem;
  margin-bottom:1.2rem;padding:1.6rem 2rem;border-radius:18px;
  background:linear-gradient(135deg,rgba(255,75,75,.25)0%,rgba(247,37,133,.25)90%);
  backdrop-filter:blur(var(--blur));-webkit-backdrop-filter:blur(var(--blur));
  border:1px solid var(--glass-brd);
}
.hero h1{margin:0 0 .3rem 0;font-size:2.1rem;}
.hero p {margin:0;font-size:1rem;color:#e5e7eb;}
/* ---------- KPI ---------- */
.kpi{background:var(--glass-bg);border:1px solid var(--glass-brd);
     backdrop-filter:blur(var(--blur));border-radius:16px;
     padding:1.3rem 1rem;text-align:center;transition:transform .2s;}
.kpi:hover{transform:translateY(-4px) scale(1.01);}
.kpi .val{font-size:1.9rem;font-weight:800;color:var(--green);line-height:1;}
.kpi .lab{font-size:.95rem;color:#d1d5db;margin-top:.15rem;}
.kpi .del{margin-top:.35rem;display:block;}
/* ---------- SIDEBAR ---------- */
section[data-testid="stSidebar"]{background:#111827;}
/* ---------- NAVBAR ---------- */
ul.nav.nav-pills li a div{display:flex;align-items:center;gap:.35rem;}
/* Ocultar menú y footer streamlit */
#MainMenu,footer,header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# 5. SIDEBAR (Filtros)
# ------------------------------------------------------------
with st.sidebar:
    st.image("https://github.com/Rosse555/imagenes/blob/main/1.png?raw=true", width=150)
    st.markdown("### Filtros 🌐")

    dmin, dmax = df_full["Fecha"].min(), df_full["Fecha"].max()
    rango = st.date_input("Rango de fechas", value=(dmin, dmax), min_value=dmin, max_value=dmax)

    regiones = st.multiselect("Región", df_full["Región"].unique(), default=list(df_full["Región"].unique()))
    categorias = st.multiselect("Categoría", df_full["Categoría"].unique(), default=list(df_full["Categoría"].unique()))

    modo_comp = st.radio("Comparar contra:", ["Periodo anterior", "Mismo periodo año anterior", "Sin comparación"], index=0)
    st.caption("Creado con ❤️ usando Streamlit")

# ------------------------------------------------------------
# 6. FILTRADO PRINCIPAL
# ------------------------------------------------------------
df = df_full[
    (df_full["Fecha"].dt.date >= rango[0]) &
    (df_full["Fecha"].dt.date <= rango[1]) &
    (df_full["Región"].isin(regiones)) &
    (df_full["Categoría"].isin(categorias))
].copy()

# ------------------------------------------------------------
# 7. HERO (texto + animación Lottie vía HTML)
# ------------------------------------------------------------
lottie_url = "https://assets1.lottiefiles.com/private_files/lf30_m6j5igxb.json"
hero_html = f"""
<!-- Cargador de Lottie Player -->
<script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
<div class="hero">
  <div>
    <h1>📈 Dashboard de Ventas PRO</h1>
    <p>Explora, filtra y compara el rendimiento de ventas por región y categoría en tiempo real.</p>
  </div>
  <lottie-player src="{lottie_url}" background="transparent" speed="1"
                 style="width:120px;height:120px;" loop autoplay></lottie-player>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

# ------------------------------------------------------------
# 8. KPIs + comparación
# ------------------------------------------------------------
tot = df["Ventas"].sum()
avg = df["Ventas"].mean()
cnt = df.shape[0]

if modo_comp != "Sin comparación":
    modo_calc = "dias" if modo_comp == "Periodo anterior" else "anio"
    prev_df = periodo_anterior(df_full, rango, modo=modo_calc)
    prev_tot, prev_avg, prev_cnt = prev_df["Ventas"].sum(), prev_df["Ventas"].mean(), prev_df.shape[0]
else:
    prev_tot = prev_avg = prev_cnt = np.nan

col1, col2, col3 = st.columns(3)
for col, valor, etiqueta, prev in [
    (col1, tot, "Ventas Totales", prev_tot),
    (col2, avg, "Promedio por Orden", prev_avg),
    (col3, cnt, "Número de Órdenes", prev_cnt),
]:
    with col:
        pct = delta_pct(valor, prev)
        col.markdown(f"""
        <div class='kpi'>
          <span class='val'>{fmt_moneda(valor, 0 if etiqueta!='Promedio por Orden' else 2)}</span>
          <div class='lab'>{etiqueta}</div>
          <span class='del'>{badge(pct)}</span>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------
# 9. MENÚ HORIZONTAL (Option-Menu)
# ------------------------------------------------------------
seleccion = option_menu(
    None,
    ["Visualizaciones", "Detalle de Datos", "Exportar"],
    icons=["bar-chart-fill", "table", "cloud-arrow-down-fill"],
    orientation="horizontal",
    default_index=0,
    styles={
        "container":{"padding":"0!important","background":"rgba(0,0,0,0)"},
        "nav-link":{"font-size":"1rem","font-weight":"500","color":"#d1d5db","margin":"0 1.5rem"},
        "nav-link-selected":{"color":"var(--red)","border-bottom":"3px solid var(--red)","font-weight":"700"},
        "icon":{"font-size":"1.1rem"},
    },
)

# ------------------------------------------------------------
# 10. CONTENIDO SEGÚN SELECCIÓN
# ------------------------------------------------------------
if seleccion == "Visualizaciones":
    a, b = st.columns((3,2))

    # --- Barras por categoría ---
    with a:
        st.subheader("Ventas por Categoría")
        cat = df.groupby("Categoría")["Ventas"].sum().sort_values()
        fig_bar = px.bar(
            cat, x=cat.values, y=cat.index, orientation="h",
            color=cat.values, text_auto=".2s",
            color_continuous_scale=["#ff4b4b","#f72585","#b5179e","#7209b7"],
            labels={"x":"Ventas","y":"Categoría"},
            template="plotly_white",
        ).update_layout(coloraxis_showscale=False, margin=dict(l=10,r=10,t=40,b=10))
        fig_bar.update_traces(hovertemplate="<b>%{y}</b><br>Ventas: %{x:,.2f}<extra></extra>")
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- Pie por región ---
    with b:
        st.subheader("Distribución por Región")
        reg = df.groupby("Región")["Ventas"].sum().reset_index()
        fig_pie = px.pie(
            reg, names="Región", values="Ventas", hole=0.45,
            template="plotly_white",
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label",
                              hovertemplate="<b>%{label}</b><br>Ventas: %{value:,.2f}<extra></extra>")
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- Área mensual ---
    st.subheader("Tendencia Mensual de Ventas")
    mensual = df.resample("ME", on="Fecha")["Ventas"].sum().reset_index()
    fig_area = px.area(mensual, x="Fecha", y="Ventas",
                       labels={"Fecha":"Mes","Ventas":"Ventas"},
                       template="plotly_white")
    fig_area.update_traces(hovertemplate="<b>%{x|%Y-%m}</b><br>Ventas: %{y:,.2f}<extra></extra>")
    st.plotly_chart(fig_area, use_container_width=True)

elif seleccion == "Detalle de Datos":
    st.subheader("Tabla de Detalle")
    tabla = df.copy()
    tabla["Fecha"] = tabla["Fecha"].dt.strftime("%Y-%m-%d")
    tabla["Ventas"] = tabla["Ventas"].map(lambda x: fmt_moneda(x,2))
    st.dataframe(tabla.sort_values("Fecha", ascending=False), use_container_width=True, height=500)

else:  # Exportar
    st.subheader("Descargar Datos Filtrados")

    csv = df.to_csv(index=False).encode("utf-8")
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Ventas")

    c1, c2 = st.columns(2)
    with c1:
        if st.download_button("⬇️ CSV", csv, "ventas_filtradas.csv", "text/csv"):
            st.success("CSV descargado")
    with c2:
        if st.download_button("⬇️ Excel", buf.getvalue(), "ventas_filtradas.xlsx",
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
            st.success("Excel descargado")