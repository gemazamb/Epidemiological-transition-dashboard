
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ruta del CSV relativa a este archivo (funciona local y en Streamlit Cloud)
DATA_PATH = Path(__file__).parent / "annual_deaths_by_causes.csv"

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------
# Configuración de página y paleta
# ----------------------------------------------------------------------
st.set_page_config(page_title="Evolución de mortalidad epidemiológica mundial",
                 layout="wide")


COL_NCD   = "#2E86AB"   # No transmisibles  (azul)
COL_COM   = "#E4572E"   # Transmisibles     (coral)
COL_INJ   = "#C98A1B"   # Lesiones          (ámbar)
COL_INK   = "#1A1A2E"
SEQ_SCALE = "Teal"      # rampa secuencial para el mapa

CAT_COLORS = {"No transmisibles": COL_NCD,
              "Transmisibles": COL_COM,
              "Lesiones": COL_INJ}

# Paleta cualitativa para las líneas de tendencia
LINE_PALETTE = ["#7C5CD3", "#E4572E", "#1D9E75", "#B14FB8",
                "#EF9F27", "#2E86AB", "#C0392B", "#3B6D11"]

# ----------------------------------------------------------------------
# Íconos SVG (línea, autosuficientes, sin dependencias)
# ----------------------------------------------------------------------
def _svg(path, c):
    return (f'<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
            f'stroke="{c}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{path}</svg>')

IC_ACTIVITY = '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
IC_TREND    = '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>'
IC_SHIELD   = '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
IC_ALERT    = ('<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3'
               'L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/>'
               '<line x1="12" y1="17" x2="12.01" y2="17"/>')


# ----------------------------------------------------------------------
# Categorías GBD y etiquetas legibles en español
# ----------------------------------------------------------------------
CATEGORY = {
    "meningitis": "Transmisibles", "nutritional_deficiency": "Transmisibles",
    "malaria": "Transmisibles", "maternal_disorders": "Transmisibles",
    "hiv/aids": "Transmisibles", "tuberculosis": "Transmisibles",
    "lower_respiratory_infections": "Transmisibles", "neonatal_disorders": "Transmisibles",
    "diarrheal_diseases": "Transmisibles", "protein_energy_malnutrition": "Transmisibles",
    "acute_hepatitis": "Transmisibles",
    "alzheimer's_diesease": "No transmisibles", "parkinson's_disease": "No transmisibles",
    "drug_use_disorders": "No transmisibles", "cardiovascular_diseases": "No transmisibles",
    "alcohol_use_disorders": "No transmisibles", "neoplasms": "No transmisibles",
    "diabetes_mellitus": "No transmisibles", "chronic_kidney_disease": "No transmisibles",
    "chronic_respiratory_diseases": "No transmisibles", "chronic_liver_diseases": "No transmisibles",
    "digestive_diseases": "No transmisibles",
    "drowning": "Lesiones", "interpersonal_violence": "Lesiones", "self_harm": "Lesiones",
    "exposure_to_forces_of_nature": "Lesiones", "environmental_heat_and_cold_exposure": "Lesiones",
    "conflict_and_terrorism": "Lesiones", "poisonings": "Lesiones",
    "road_injuries": "Lesiones", "fire_heat_hot_substance": "Lesiones",
}
LABELS = {
    "meningitis": "Meningitis", "nutritional_deficiency": "Deficiencias nutricionales",
    "malaria": "Malaria", "maternal_disorders": "Trastornos maternos", "hiv/aids": "VIH/SIDA",
    "tuberculosis": "Tuberculosis", "lower_respiratory_infections": "Infecciones respiratorias bajas",
    "neonatal_disorders": "Trastornos neonatales", "diarrheal_diseases": "Enfermedades diarreicas",
    "protein_energy_malnutrition": "Desnutrición proteico-energética", "acute_hepatitis": "Hepatitis aguda",
    "alzheimer's_diesease": "Alzheimer y demencias", "parkinson's_disease": "Parkinson",
    "drug_use_disorders": "Trastornos por drogas", "cardiovascular_diseases": "Enf. cardiovasculares",
    "alcohol_use_disorders": "Trastornos por alcohol", "neoplasms": "Neoplasias (cáncer)",
    "diabetes_mellitus": "Diabetes", "chronic_kidney_disease": "Enf. renal crónica",
    "chronic_respiratory_diseases": "Enf. respiratorias crónicas", "chronic_liver_diseases": "Enf. hepáticas crónicas",
    "digestive_diseases": "Enfermedades digestivas", "drowning": "Ahogamiento",
    "interpersonal_violence": "Violencia interpersonal", "self_harm": "Autolesiones (suicidio)",
    "exposure_to_forces_of_nature": "Desastres naturales",
    "environmental_heat_and_cold_exposure": "Exposición a calor/frío",
    "conflict_and_terrorism": "Conflicto y terrorismo", "poisonings": "Envenenamientos",
    "road_injuries": "Lesiones de tránsito", "fire_heat_hot_substance": "Fuego y quemaduras",
}
CAUSES = list(CATEGORY.keys())   # 31 causas (terrorism excluido del total)


# ----------------------------------------------------------------------
# Carga y limpieza (cacheada)
# ----------------------------------------------------------------------
@st.cache_data
def load_data(path=DATA_PATH):
    if not Path(path).exists():
        st.error(
            "No se encontró 'annual_deaths_by_causes.csv'. "
            "Debe estar en el repositorio, en la misma carpeta que app.py."
        )
        st.stop()
    df = pd.read_csv(path)
    # tipos
    df["year"] = df["year"].astype(int)
    for c in CAUSES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # bandera de agregado (sin código ISO)
    df["es_agregado"] = df["code"].isna()
    # derivados: total y participación porcentual
    df["total_deaths"] = df[CAUSES].sum(axis=1)
    for c in CAUSES:
        df[f"pct_{c}"] = np.where(df["total_deaths"] > 0,
                                  df[c] / df["total_deaths"] * 100, np.nan)
    # categoría amplia en formato largo (para áreas apiladas)
    return df

df = load_data()
PAISES = sorted(df.loc[~df["es_agregado"], "country"].unique())
ENTIDADES = sorted(df["country"].unique())
YEARS = sorted(df["year"].unique())

def cat_share(sub):
    """Suma por categoría amplia GBD para un subconjunto de filas."""
    out = {"Transmisibles": 0.0, "No transmisibles": 0.0, "Lesiones": 0.0}
    for c in CAUSES:
        out[CATEGORY[c]] += sub[c].sum()
    return out

# ----------------------------------------------------------------------
# Estilo: tarjeta KPI con borde, acento e ícono
# ----------------------------------------------------------------------
def render_kpis(cards):
    """cards: lista de dict(label, value, accent, delta_txt, delta_dir)."""
    html = ('<div style="display:grid;gap:14px;margin:4px 0 2px;'
            'grid-template-columns:repeat(auto-fit,minmax(190px,1fr));">')
    for c in cards:
        accent = c["accent"]
        delta = ""
        if c.get("delta_txt"):
            arrow = "▲" if c["delta_dir"] >= 0 else "▼"
            delta = (f'<div style="font-size:12.5px;color:#475467;margin-top:6px;">'
                     f'<span style="color:{accent}">{arrow}</span> {c["delta_txt"]}</div>')
        html += (
            f'<div style="background:{accent}14;border-radius:14px;padding:16px 18px;">'
            f'<div style="font-size:12px;color:#475467;font-weight:600;'
            f'letter-spacing:.4px;text-transform:uppercase;">{c["label"]}</div>'
            f'<div style="font-size:26px;font-weight:700;color:{accent};'
            f'margin-top:8px;line-height:1.1;">{c["value"]}</div>{delta}</div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)



# ----------------------------------------------------------------------
# Barra lateral (filtros)
# ----------------------------------------------------------------------
st.sidebar.title("Controles del tablero")


entidad = st.sidebar.selectbox("Unidad de análisis", ENTIDADES,
                               index=ENTIDADES.index("World") if "World" in ENTIDADES else 0)

st.sidebar.markdown("**Periodo de análisis**")
cdesde, chasta = st.sidebar.columns(2)
y0 = cdesde.selectbox("Desde", YEARS, index=0)
y1 = chasta.selectbox("Hasta", YEARS, index=len(YEARS) - 1)
if y0 > y1:
    y0, y1 = y1, y0   # tolera el orden invertido

metrica = st.sidebar.radio("Métrica", ["% del total", "Conteo absoluto"], horizontal=True)
st.sidebar.markdown("---")
st.sidebar.title("**Controles del mapa interactivo**")
causa_sel = st.sidebar.selectbox("Causa de muerte", CAUSES,
                                 index=CAUSES.index("malaria"),
                                 format_func=lambda c: LABELS[c])

sub_ent = df[(df["country"] == entidad) & df["year"].between(y0, y1)].sort_values("year")
row0 = df[(df["country"] == entidad) & (df["year"] == y0)]
row1 = df[(df["country"] == entidad) & (df["year"] == y1)]
st.sidebar.caption("Fuente: Global Burden of Disease vía Our World in Data.")    
# ----------------------------------------------------------------------
# Encabezado + KPIs (con variación vs. año inicial = tendencia)
# ----------------------------------------------------------------------
st.title("Evolución de mortalidad epidemiológica mundial")
st.markdown(f"#### Causas de muerte · **{entidad}** · {y0}–{y1}")

cs0 = tot0 = None  # se usan luego en el insight
if not row1.empty:
    r1 = row1.iloc[0]
    cs1 = cat_share(row1); tot1 = r1["total_deaths"]
    ncd1 = cs1["No transmisibles"] / tot1 * 100
    com1 = cs1["Transmisibles"] / tot1 * 100
    lead = max(CAUSES, key=lambda c: (r1[c] if pd.notna(r1[c]) else -1))

    d_tot = d_ncd = d_com = None
    if not row0.empty and y0 != y1:
        r0 = row0.iloc[0]; cs0 = cat_share(row0); tot0 = r0["total_deaths"]
        if tot0 > 0:
            d_tot = (tot1 / tot0 - 1) * 100
            d_ncd = ncd1 - cs0["No transmisibles"] / tot0 * 100
            d_com = com1 - cs0["Transmisibles"] / tot0 * 100

    render_kpis([
        {"label": f"Muertes totales {y1}", "value": f"{tot1:,.0f}", "icon": IC_ACTIVITY,
         "accent": COL_INK,
         "delta_txt": (f"{d_tot:+.1f}% vs {y0}" if d_tot is not None else ""),
         "delta_dir": (d_tot or 0)},
        {"label": "% No transmisibles", "value": f"{ncd1:.1f}%", "icon": IC_TREND,
         "accent": COL_NCD,
         "delta_txt": (f"{d_ncd:+.1f} pp vs {y0}" if d_ncd is not None else ""),
         "delta_dir": (d_ncd or 0)},
        {"label": "% Transmisibles", "value": f"{com1:.1f}%", "icon": IC_SHIELD,
         "accent": COL_COM,
         "delta_txt": (f"{d_com:+.1f} pp vs {y0}" if d_com is not None else ""),
         "delta_dir": (d_com or 0)},
        {"label": f"Causa líder {y1}", "value": LABELS[lead], "icon": IC_ALERT,
         "accent": "#6D28D9", "delta_txt": "", "delta_dir": 0},
    ])

st.write("")
tab1, tab2, tab3 = st.tabs(
    [" Detalle general", " Geografía y comparación", " Ranking 1990 vs 2019"])

# ======================================================================
# TAB 1 — Panorama (área + tendencia de líneas + insight + cambios)
# ======================================================================
with tab1:
    if cs0 is not None and tot0 and not row1.empty and y0 != y1:
        dir_txt = "aumentaron" if (d_ncd or 0) > 0 else "disminuyeron"
        st.markdown(
            f"""<div style="background:#EEF4F8;border-left:4px solid {COL_NCD};
            border-radius:10px;padding:12px 16px;font-size:14px;color:#243B4A;">
            </b> Entre {y0} y {y1}, en {entidad} las enfermedades
            <b>no transmisibles</b> {dir_txt} del <b>{cs0['No transmisibles']/tot0*100:.1f}%</b> al
            <b>{ncd1:.1f}%</b> del total de muertes, mientras las <b>transmisibles</b> pasaron del
            <b>{cs0['Transmisibles']/tot0*100:.1f}%</b> al <b>{com1:.1f}%</b>.</div>""",
            unsafe_allow_html=True)
        st.write("")

    col_a, col_b = st.columns([3, 2])

    # Área apilada por categoría
    with col_a:
        st.subheader("Composición por categoría en el tiempo")
        recs = []
        for _, rr in sub_ent.iterrows():
            cc = cat_share(rr.to_frame().T)
            for k, v in cc.items():
                recs.append({"year": rr["year"], "Categoría": k, "Muertes": v})
        long = pd.DataFrame(recs)
        if metrica == "% del total":
            tot_y = long.groupby("year")["Muertes"].transform("sum")
            long["valor"] = long["Muertes"] / tot_y * 100
            ytitle = "% del total"
        else:
            long["valor"] = long["Muertes"]; ytitle = "Número de muertes"
        figA = px.area(long, x="year", y="valor", color="Categoría",
                       color_discrete_map=CAT_COLORS,
                       category_orders={"Categoría": ["No transmisibles", "Transmisibles", "Lesiones"]})
        figA.update_layout(template="plotly_white", height=380, hovermode="x unified",
                           yaxis_title=ytitle, xaxis_title="Año", legend_title="",
                           margin=dict(t=10, b=0, l=0, r=0),
                           legend=dict(orientation="h", y=-0.2))
        figA.update_traces(line=dict(width=0.5))
        st.plotly_chart(figA, use_container_width=True)

    # Mayores cambios (sube / baja)
    with col_b:
        st.subheader("Variación porcentual por causa de muerte")
        if not row0.empty and not row1.empty and y0 != y1:
            r0 = row0.iloc[0]; r1b = row1.iloc[0]
            chg = []
            for c in CAUSES:
                if pd.notna(r0[c]) and pd.notna(r1b[c]) and r0[c] > 0:
                    chg.append((LABELS[c], (r1b[c] / r0[c] - 1) * 100))
            chg.sort(key=lambda x: x[1])
            bajan, suben = chg[:4], chg[-4:][::-1]
            def chips(items, color):
                h = ""
                for name, pc in items:
                    h += (f'<div style="display:flex;justify-content:space-between;'
                          f'padding:6px 10px;margin-bottom:6px;border-radius:8px;'
                          f'background:#F7F8FA;border:1px solid #ECEEF2;font-size:13px;">'
                          f'<span>{name}</span>'
                          f'<span style="color:{color};font-weight:700;">{pc:+.0f}%</span></div>')
                return h
            st.markdown(f"**Top 4 que aumentaron ({y0}→{y1})**")
            st.markdown(chips(suben, COL_COM), unsafe_allow_html=True)
            st.markdown(f"**Top 4 que disminuyeron ({y0}→{y1})**")
            st.markdown(chips(bajan, "#1D9E75"), unsafe_allow_html=True)
        else:
            st.info("Elige un año inicial distinto del final para ver los cambios.")

    st.markdown("---")

    # Tendencia por causa (líneas) con multiselect
    st.subheader("Tendencia por causa")
    default_trend = ["hiv/aids", "tuberculosis", "malaria", "diarrheal_diseases", "meningitis"]
    causas_trend = st.multiselect(
        "Causas a comparar (selección múltiple)", CAUSES,
        default=[c for c in default_trend if c in CAUSES],
        format_func=lambda c: LABELS[c])
    if causas_trend:
        recs = []
        for _, rr in sub_ent.iterrows():
            for c in causas_trend:
                val = rr[f"pct_{c}"] if metrica == "% del total" else rr[c]
                recs.append({"Año": rr["year"], "Causa": LABELS[c], "valor": val})
        td = pd.DataFrame(recs)
        figT = px.line(td, x="Año", y="valor", color="Causa", markers=False,
                       color_discrete_sequence=LINE_PALETTE)
        figT.update_layout(template="plotly_white", height=420, hovermode="x unified",
                           yaxis_title=("% del total" if metrica == "% del total" else "Muertes"),
                           xaxis_title="Año", legend_title="",
                           margin=dict(t=10, b=0, l=0, r=0))
        figT.update_traces(line=dict(width=2.4))
        st.plotly_chart(figT, use_container_width=True)
       
    else:
        st.info("Selecciona al menos una causa para ver la tendencia.")

# ======================================================================
# TAB 2 — Mapa + comparación entre países
# ======================================================================
with tab2:
    st.subheader(f"Distribución geográfica · {LABELS[causa_sel]} · {y1}")
    geo = df[(df["year"] == y1) & (~df["es_agregado"]) & (df["code"].notna())].copy()
    if metrica == "% del total":
        geo["val"] = geo[f"pct_{causa_sel}"]; cbar = "% del total"
    else:
        geo["val"] = geo[causa_sel]; cbar = "Muertes"
    figM = px.choropleth(geo, locations="code", color="val", hover_name="country",
                         color_continuous_scale=SEQ_SCALE, labels={"val": cbar})
    figM.update_layout(template="plotly_white", height=460, margin=dict(l=0, r=0, t=0, b=0),
                       coloraxis_colorbar_title=cbar,
                       geo=dict(showframe=False, projection_type="natural earth"))
    st.plotly_chart(figM, use_container_width=True)
    #st.caption("  ")

    st.markdown("---")
    st.subheader("Perfil de mortalidad: comparación entre entidades")
    anio_cmp = st.selectbox(
    "Año de comparación",
    YEARS,
    index=YEARS.index(y1) if y1 in YEARS else len(YEARS) - 1,
    help="Instantánea de un solo año, no un acumulado.",
)
    sel = st.multiselect("Selecciona 2 a 4 entidades", ENTIDADES,
                         default=[e for e in [entidad, "Nigeria", "Japan"] if e in ENTIDADES][:3])
    if sel:
        recs = []
        for e in sel:
            rr = df[(df["country"] == e) & (df["year"] == anio_cmp)]
            if rr.empty:
                continue
            cs = cat_share(rr); tot = sum(cs.values())
            for k, v in cs.items():
                recs.append({"Entidad": e, "Categoría": k, "pct": v / tot * 100 if tot else 0})
        comp = pd.DataFrame(recs)
        figC = px.bar(comp, x="pct", y="Entidad", color="Categoría", orientation="h",
                      color_discrete_map=CAT_COLORS,
                      category_orders={"Categoría": ["No transmisibles", "Transmisibles", "Lesiones"]})
        figC.update_yaxes(
        categoryorder="array",
        categoryarray=sel,                       # respeta el orden del multiselect
        tickvals=sel,
        ticktext=[f"<b style='color:#111827'>{e}</b>" if e == entidad
                else f"<span style='color:#98A2B3'>{e}</span>"
                for e in sel],
    )
        figC.update_layout(template="plotly_white", height=120 + 70 * len(sel), barmode="stack",
                           xaxis_title="% del total de muertes", yaxis_title="", legend_title="")
        st.plotly_chart(figC, use_container_width=True)
        st.caption("Barras 100 % apiladas: alinean las composiciones a la misma base, haciendo directa "
                   "la comparación parte-todo entre países de distinto tamaño.")

# ======================================================================
# TAB 3 — Dumbbell 1990 vs 2019
# ======================================================================
with tab3:
    st.subheader(f"Las causas principales y su cambio — {entidad}")
    top_n = st.slider("Número de causas (top por 2019)", 5, 15, 10)
    a = df[(df["country"] == entidad) & (df["year"] == 1990)]
    b = df[(df["country"] == entidad) & (df["year"] == 2019)]
    if not a.empty and not b.empty:
        a, b = a.iloc[0], b.iloc[0]
        rows = [(LABELS[c], a[c], b[c]) for c in CAUSES
                if pd.notna(a[c]) and pd.notna(b[c])]
        d = pd.DataFrame(rows, columns=["Causa", "y1990", "y2019"]).sort_values("y2019").tail(top_n)
        figD = go.Figure()
        for _, rr in d.iterrows():
            figD.add_trace(go.Scatter(x=[rr.y1990, rr.y2019], y=[rr.Causa, rr.Causa],
                                      mode="lines", line=dict(color="#B9C0CC", width=3),
                                      showlegend=False, hoverinfo="skip"))
        figD.add_trace(go.Scatter(x=d.y1990, y=d.Causa, mode="markers", name="1990",
                                  marker=dict(color=COL_COM, size=12)))
        figD.add_trace(go.Scatter(x=d.y2019, y=d.Causa, mode="markers", name="2019",
                                  marker=dict(color=COL_NCD, size=12)))
        figD.update_layout(template="plotly_white", height=130 + 38 * len(d),
                           xaxis_title="Número de muertes", yaxis_title="",
                           legend_title="Año", hovermode="closest", margin=dict(t=10))
        st.plotly_chart(figD, use_container_width=True)
        
    else:
        st.info("Esta entidad no tiene datos completos para 1990 y 2019.")
