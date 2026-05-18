import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import db as db_nuvem  # Importa o seu arquivo tradutor do Supabase

# ── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SYS.HEALTH // Leandro R.",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── RESET STREAMLIT CHROME ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700;800&display=swap');
html,body,.stApp{background:#080c14!important;color:#e8edf5!important;font-family:'DM Sans',sans-serif!important}
.block-container{padding:1.5rem 2rem!important;max-width:100%!important}
#MainMenu,footer,header,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important}
.stDeployButton{display:none!important}
section[data-testid="stSidebar"]{background:#0d1424!important}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTES DE COR ────────────────────────────────────────────────────────
BG      = "#080c14"
BG2     = "#0d1424"
BG3     = "#080e1a"
BORDER  = "#1a2035"
BORDER2 = "#111c2e"
CYAN    = "#00d4ff"
GREEN   = "#00e676"
RED     = "#ff6b6b"
PURPLE  = "#a78bfa"
AMBER   = "#fbbf24"
TEXT    = "#e8edf5"
MUTED   = "#4a5568"
GHOST   = "#2a3448"
MONO    = "'Space Mono',monospace"

# ── HELPERS ──────────────────────────────────────────────────────────────────
def db(query, params=None):
    return db_nuvem.query(query, params)

def pbar(pct, cor, h=4):
    p = min(100, max(0, int(pct * 100)))
    return (
        f'<div style="background:{BORDER};border-radius:3px;height:{h}px;'
        f'overflow:hidden;margin-top:8px">'
        f'<div style="width:{p}%;height:{h}px;border-radius:3px;background:{cor}"></div>'
        f'</div>'
    )

def sec(tag, titulo):
    return (
        f'<div style="display:flex;align-items:center;gap:10px;margin:18px 0 12px">'
        f'<span style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:{CYAN};background:rgba(0,212,255,0.07);'
        f'border:1px solid rgba(0,212,255,0.2);border-radius:3px;padding:3px 8px">{tag}</span>'
        f'<span style="font-size:11px;color:{GHOST}">{titulo}</span>'
        f'<div style="flex:1;height:1px;background:{BORDER2}"></div>'
        f'</div>'
    )

def panel(conteudo, extra=""):
    return (
        f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;'
        f'padding:14px 16px;{extra}">{conteudo}</div>'
    )

def ptitl(txt):
    return (
        f'<div style="font-family:{MONO};font-size:10px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{TEXT};margin-bottom:12px">{txt}</div>'
    )

# ── METAS ────────────────────────────────────────────────────────────────────
META_CAL  = 2400
META_PROT = 190
META_CARB = 241
META_GORD = 75
META_AGUA = 3.5
META_PASS = 10000
META_SONO = 90
META_PAI  = 100

from zoneinfo import ZoneInfo
fuso_br = ZoneInfo("America/Sao_Paulo")
agora = datetime.now(fuso_br)

hoje_sql = agora.strftime("%Y-%m-%d")
hoje_pt  = agora.strftime("%d/%m/%Y")
hora_now = agora.strftime("%H:%M")
dia_sem  = ["SEG","TER","QUA","QUI","SEX","SAB","DOM"][agora.weekday()]
# ── DADOS ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def _fetch_dados(hoje):
    _dp = db("SELECT peso FROM medidas ORDER BY date(data) DESC LIMIT 1")
    _peso = float(_dp["peso"].iloc[0]) if not _dp.empty else 93.0

    _da = db(
        "SELECT COALESCE(SUM(quantidade_ml),0) as t FROM agua WHERE date(data_hora,'localtime')=?",
        [hoje]
    )
    _agua_l = float(_da["t"].iloc[0] or 0) / 1000

    _dr = db(
        "SELECT COALESCE(SUM(calorias),0) as cal, COALESCE(SUM(proteinas),0) as prot,"
        "COALESCE(SUM(carboidratos),0) as carb, COALESCE(SUM(gorduras),0) as gord "
        "FROM refeicoes WHERE date(data_hora,'localtime')=?",
        [hoje]
    )
    _cal_h  = float(_dr["cal"].iloc[0]  or 0)
    _prot_h = float(_dr["prot"].iloc[0] or 0)
    _carb_h = float(_dr["carb"].iloc[0] or 0)
    _gord_h = float(_dr["gord"].iloc[0] or 0)

    _az = db("SELECT * FROM amazfit_dados ORDER BY date(data_hora) DESC LIMIT 1")
    _passos    = int(_az["passos"].iloc[0])            if not _az.empty else 0
    _cal_gasta = int(_az["calorias_gastas"].iloc[0])   if not _az.empty else 0
    _dist_km   = float(_az["distancia_km"].iloc[0])    if not _az.empty else 0.0
    _sono_tot  = int(_az["sono_total_min"].iloc[0])    if not _az.empty else 0
    _sono_prof = int(_az["sono_profundo_min"].iloc[0]) if not _az.empty else 0
    _hrv       = int(_az["hrv_ms"].iloc[0])            if not _az.empty else 0
    _pai       = int(_az["pai"].iloc[0])               if not _az.empty else 0

    return (_peso, _agua_l, _cal_h, _prot_h, _carb_h, _gord_h,
            _passos, _cal_gasta, _dist_km, _sono_tot, _sono_prof, _hrv, _pai)

(peso, agua_l, cal_h, prot_h, carb_h, gord_h,
 passos, cal_gasta, dist_km, sono_tot, sono_prof, hrv, pai) = _fetch_dados(hoje_sql)

# Derivações
deficit   = cal_gasta - int(cal_h)
def_cor   = GREEN if deficit > 0 else RED
def_txt   = (f"Déficit {abs(deficit):,}" if deficit > 0
             else f"Superávit {abs(deficit):,}" if deficit < 0
             else "Equilíbrio")
sono_h_fmt = f"{sono_tot // 60}h{sono_tot % 60:02d}"
sono_cor  = GREEN if sono_prof >= META_SONO else RED
hrv_cor   = GREEN if hrv >= 50 else (AMBER if hrv >= 35 else RED)
hrv_txt   = "↑ Bom" if hrv >= 50 else ("→ Médio" if hrv >= 35 else "↓ Baixo")
pai_cor   = GREEN if pai >= META_PAI else (AMBER if pai >= 70 else RED)
pai_arc   = min(251, int(251 * pai / META_PAI)) if META_PAI else 0
restam    = int(META_CAL - cal_h)
rc_cor    = GREEN if restam > 0 else RED

# ════════════════════════════════════════════════════════════════════════════
# TOPBAR
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div style="display:flex;justify-content:space-between;align-items:flex-end;'
    f'padding-bottom:14px;border-bottom:1px solid {BORDER2};margin-bottom:6px">'
    f'<div>'
    f'<div style="font-family:{MONO};font-size:10px;letter-spacing:3px;color:{CYAN};text-transform:uppercase">sys.health_tracker</div>'
    f'<div style="font-size:26px;font-weight:800;color:{TEXT};line-height:1;letter-spacing:-0.5px;margin-top:2px">Leandro R.</div>'
    f'<div style="font-size:10px;color:{GHOST};text-transform:uppercase;letter-spacing:1.5px;margin-top:4px">Rio de Janeiro &nbsp;·&nbsp; Dashboard v2.1</div>'
    f'</div>'
    f'<div style="text-align:right">'
    f'<div style="font-family:{MONO};font-size:11px;color:{GHOST}">{dia_sem} · {hoje_pt} · {hora_now}</div>'
    f'<div style="font-family:{MONO};font-size:11px;color:{GREEN};font-weight:700;margin-top:3px">'
    f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
    f'background:{GREEN};margin-right:5px;vertical-align:middle"></span>'
    f'Amazfit Bip 6 — sincronizado</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — NUTRIÇÃO
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Nutrição", "Metas do dia"), unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

def kpi_card(acento, lbl, val, unit, extra=""):
    return panel(
        f'<div style="position:absolute;top:0;left:0;right:0;height:2px;'
        f'border-radius:10px 10px 0 0;background:{acento}"></div>'
        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;color:{GHOST};margin-bottom:7px">{lbl}</div>'
        f'<div><span style="font-size:28px;font-weight:800;color:{TEXT};line-height:1;'
        f'letter-spacing:-1px">{val}</span>'
        f'<span style="font-size:13px;color:{MUTED};margin-left:3px">{unit}</span></div>'
        f'{extra}',
        extra="position:relative;overflow:hidden"
    )

with k1:
    st.markdown(kpi_card(
        CYAN, "Peso atual", f"{peso:.1f}", "kg",
        f'<div style="font-size:11px;font-weight:700;color:{GREEN};margin-top:6px">▼ {110 - peso:.1f} kg desde o início</div>'
        f'<div style="font-size:10px;color:{MUTED};margin-top:3px">Meta: 83 kg · faltam {peso - 83:.1f} kg</div>',
    ), unsafe_allow_html=True)

with k2:
    st.markdown(kpi_card(
        GREEN, "Calorias", f"{int(cal_h):,}", "kcal",
        pbar(cal_h / META_CAL, GREEN) +
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};margin-top:4px">'
        f'{int(cal_h / META_CAL * 100)}% · restam {restam} kcal</div>',
    ), unsafe_allow_html=True)

with k3:
    st.markdown(kpi_card(
        RED, "Proteínas", f"{int(prot_h)}", "g",
        pbar(prot_h / META_PROT, RED) +
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};margin-top:4px">'
        f'{int(prot_h / META_PROT * 100)}% · meta {META_PROT} g</div>',
    ), unsafe_allow_html=True)

with k4:
    st.markdown(kpi_card(
        PURPLE, "Hidratação", f"{agua_l:.1f}", "L",
        pbar(agua_l / META_AGUA, PURPLE) +
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};margin-top:4px">'
        f'{int(agua_l / META_AGUA * 100)}% · meta {META_AGUA} L</div>',
    ), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — AMAZFIT
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Amazfit Bip 6", "Atividade · Recovery · Sono"), unsafe_allow_html=True)

def az_card(icon, lbl, val, unit, extra=""):
    return panel(
        f'<div style="font-size:20px;margin-bottom:6px;text-align:center">{icon}</div>'
        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{GHOST};margin-bottom:5px;text-align:center">{lbl}</div>'
        f'<div style="font-size:20px;font-weight:800;color:{TEXT};line-height:1;'
        f'text-align:center;letter-spacing:-0.5px">{val}</div>'
        f'<div style="font-size:10px;color:{MUTED};margin-top:2px;text-align:center">{unit}</div>'
        f'{extra}'
    )

a1, a2, a3, a4, a5, a6 = st.columns(6)

with a1:
    pct_p = passos / META_PASS if META_PASS else 0
    st.markdown(az_card(
        "👟", "Passos", f"{passos:,}", f"meta {META_PASS:,}",
        pbar(pct_p, CYAN) +
        f'<div style="font-size:11px;font-weight:700;color:{CYAN};margin-top:5px;text-align:center">'
        f'{int(pct_p * 100)}%</div>',
    ), unsafe_allow_html=True)

with a2:
    st.markdown(az_card(
        "🔥", "Cal. gastas", f"{cal_gasta:,}", "kcal totais",
        f'<div style="font-size:11px;font-weight:700;color:{def_cor};margin-top:5px;text-align:center">'
        f'{def_txt} kcal</div>',
    ), unsafe_allow_html=True)

with a3:
    st.markdown(az_card("📍", "Distância", f"{dist_km:.1f}", "km hoje"),
                unsafe_allow_html=True)

with a4:
    pct_sp = sono_prof / META_SONO if META_SONO else 0
    st.markdown(az_card(
        "🌙", "Sono total", sono_h_fmt, "Sono profundo",
        pbar(pct_sp, sono_cor) +
        f'<div style="font-size:10px;font-weight:700;color:{sono_cor};margin-top:4px;text-align:center">'
        f'{sono_prof} min · meta {META_SONO}</div>',
    ), unsafe_allow_html=True)

with a5:
    pct_hrv = hrv / 100 if hrv else 0
    st.markdown(az_card(
        "💓", "HRV", str(hrv), "ms",
        pbar(pct_hrv, hrv_cor) +
        f'<div style="display:flex;justify-content:space-between;margin-top:3px">'
        f'<span style="font-family:{MONO};font-size:9px;color:{GHOST}">20</span>'
        f'<span style="font-family:{MONO};font-size:9px;color:{GHOST}">{hrv}</span>'
        f'<span style="font-family:{MONO};font-size:9px;color:{GHOST}">100</span></div>'
        f'<div style="font-size:11px;font-weight:700;color:{hrv_cor};margin-top:3px;text-align:center">{hrv_txt}</div>',
    ), unsafe_allow_html=True)

with a6:
    svg_pai = (
        f'<div style="position:relative;width:60px;height:60px;margin:4px auto 2px">'
        f'<svg width="60" height="60" viewBox="0 0 60 60" style="transform:rotate(-90deg)">'
        f'<circle cx="30" cy="30" r="24" fill="none" stroke="{BORDER}" stroke-width="6"/>'
        f'<circle cx="30" cy="30" r="24" fill="none" stroke="{pai_cor}" stroke-width="6" '
        f'stroke-dasharray="{pai_arc} 251" stroke-linecap="round"/></svg>'
        f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
        f'font-size:16px;font-weight:800;color:{pai_cor}">{pai}</div></div>'
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};text-transform:uppercase;'
        f'letter-spacing:1px;text-align:center">meta >= {META_PAI}</div>'
    )
    st.markdown(az_card("⚡", "PAI", "", "", svg_pai), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3 — EVOLUÇÃO
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Evolução", "Peso histórico · Macros do dia"), unsafe_allow_html=True)

c1, c2 = st.columns([2, 1])

with c1:
    df_p = db("SELECT date(data) as dt, peso FROM medidas WHERE coxa_dir IS NOT NULL ORDER BY date(data) ASC")
    if not df_p.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_p["dt"], y=df_p["peso"], mode="lines+markers",
            line=dict(color=CYAN, width=2),
            marker=dict(size=7, color=CYAN, line=dict(color=BG, width=1.5)),
            fill="tozeroy", fillcolor="rgba(0,212,255,0.04)",
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>%{y} kg<extra></extra>",
        ))
        fig.add_hline(y=83, line_dash="dash", line_color=RED, line_width=1, opacity=0.4,
                      annotation_text="Meta 83 kg", annotation_font_color=RED,
                      annotation_font_size=10)
        fig.update_layout(
            height=210, margin=dict(t=8, b=8, l=0, r=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor=BORDER, title=None, tickformat="%d/%m/%y",
                       tickfont=dict(color=GHOST, size=9, family="monospace")),
            yaxis=dict(gridcolor=BORDER, title=None,
                       tickfont=dict(color=GHOST, size=9)),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with c2:
    def mrow(nome, val, meta, cor):
        p = min(100, int(val / meta * 100)) if meta else 0
        return (
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
            f'<span style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1px;'
            f'text-transform:uppercase;color:{MUTED}">{nome}</span>'
            f'<span style="font-size:10px;color:{GHOST}">'
            f'<b style="color:{TEXT}">{int(val)}</b> / {int(meta)} g</span>'
            f'</div>'
            f'<div style="background:{BORDER};border-radius:3px;height:5px;overflow:hidden">'
            f'<div style="width:{p}%;height:5px;border-radius:3px;background:{cor}"></div>'
            f'</div></div>'
        )
    st.markdown(
        panel(
            ptitl("Macronutrientes") +
            mrow("Proteínas",    prot_h, META_PROT, GREEN)  +
            mrow("Carboidratos", carb_h, META_CARB, CYAN)   +
            mrow("Gorduras",     gord_h, META_GORD, PURPLE) +
            f'<div style="border-top:1px solid {BORDER2};padding-top:10px;display:flex;'
            f'justify-content:space-between;align-items:center">'
            f'<span style="font-family:{MONO};font-size:9px;text-transform:uppercase;'
            f'letter-spacing:1.5px;color:{GHOST}">Calorias restantes</span>'
            f'<span style="font-size:17px;font-weight:800;color:{rc_cor}">{restam:+,} kcal</span>'
            f'</div>',
            extra="height:210px;display:flex;flex-direction:column;justify-content:space-between"
        ),
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 4 — REFEIÇÕES + SUPLEMENTOS
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Registros do dia", "Refeições · Suplementação"), unsafe_allow_html=True)

col_m, col_s = st.columns([1.4, 2.6])

BADGE_STYLE = {
    "Café da Manhã":   f"background:rgba(0,212,255,0.08);color:{CYAN};border:1px solid rgba(0,212,255,0.2)",
    "Lanche da Manhã": f"background:rgba(167,139,250,0.08);color:{PURPLE};border:1px solid rgba(167,139,250,0.2)",
    "Almoço":          f"background:rgba(0,230,118,0.08);color:{GREEN};border:1px solid rgba(0,230,118,0.2)",
    "Lanche da Tarde": f"background:rgba(167,139,250,0.08);color:{PURPLE};border:1px solid rgba(167,139,250,0.2)",
    "Jantar":          f"background:rgba(255,107,107,0.08);color:{RED};border:1px solid rgba(255,107,107,0.2)",
    "Lanche da Noite": f"background:rgba(167,139,250,0.08);color:{PURPLE};border:1px solid rgba(167,139,250,0.2)",
    "Lanche":          f"background:rgba(74,85,104,0.15);color:{MUTED};border:1px solid {BORDER}",
}

with col_m:
    df_ref_hoje = db(
        f"SELECT time(datetime(data_hora,'localtime')) as hora, "
        f"COALESCE(categoria,'Lanche') as cat, descricao as alimento "
        f"FROM refeicoes WHERE date(data_hora,'localtime')='{hoje_sql}' "
        f"ORDER BY data_hora DESC LIMIT 6"
    )
    rows = ""
    if not df_ref_hoje.empty:
        for _, r in df_ref_hoje.iterrows():
            bsty = BADGE_STYLE.get(r["cat"], BADGE_STYLE["Lanche"])
            rows += (
                f'<div style="display:flex;align-items:center;gap:9px;padding:8px 0;'
                f'border-bottom:1px solid {BG3}">'
                f'<span style="font-family:{MONO};font-size:12px;font-weight:700;'
                f'color:{CYAN};min-width:36px">{r["hora"][:5]}</span>'
                f'<span style="font-size:9px;font-weight:700;letter-spacing:1px;'
                f'text-transform:uppercase;padding:2px 7px;border-radius:3px;'
                f'white-space:nowrap;{bsty}">{r["cat"]}</span>'
                f'<span style="font-size:12px;color:{MUTED};flex:1">{r["alimento"]}</span>'
                f'</div>'
            )
    else:
        rows = f'<p style="color:{GHOST};font-size:12px;margin-top:8px">Nenhuma refeição registrada hoje.</p>'

    st.markdown(panel(ptitl("Refeições de hoje") + rows), unsafe_allow_html=True)

# Busca refeições de hoje para checar suplementos registrados
df_supp_check = db(
    f"SELECT descricao, COUNT(*) as qtd FROM refeicoes "
    f"WHERE date(data_hora,'localtime')='{hoje_sql}' "
    f"GROUP BY descricao"
)
# Monta dicionário: keyword → quantidade registrada hoje
supp_registrados = {}
for _, r in df_supp_check.iterrows():
    desc = r["descricao"].lower()
    supp_registrados[desc] = int(r["qtd"])

def checar_supp(keywords):
    """Retorna quantas vezes qualquer keyword aparece nas descrições de hoje."""
    total = 0
    for desc, qtd in supp_registrados.items():
        if any(kw.lower() in desc for kw in keywords):
            total += qtd
    return total

# Definição dos suplementos com keywords para busca no banco
# "feito": True = sempre marcado (sem rastreio automático)
# "keywords": lista de termos que identificam o suplemento nas refeições
SUPLEMENTOS = [
    {"label": "Whey Isolado",          "meta": 2,    "cor": GREEN,  "marca": "Dux Nutrition",  "keywords": ["whey"]},
    {"label": "Creatina",              "meta": 1,    "cor": CYAN,   "marca": "Creapure Dux",   "keywords": ["creatina"]},
    {"label": "Pré-Treino",            "meta": 1,    "cor": RED,    "marca": "More Treino Dux","keywords": ["pré-treino", "pre-treino", "more treino"]},
    {"label": "Magnésio Quelato Trio", "meta": 1,    "cor": PURPLE, "marca": "Vitha",          "keywords": ["magnésio", "magnesio", "quelato", "vitha"]},
    {"label": "Ômega 3",               "meta": 1,    "cor": AMBER,  "marca": "Omegafor Plus",  "keywords": ["ômega", "omega", "omegafor"]},
    {"label": "Vit. D3 + K2",          "meta": 1,    "cor": AMBER,  "marca": "Bio D3+K2",      "keywords": ["d3", "k2", "vitamina d", "biovit"]},
]

with col_s:
    cards = ""
    for s in SUPLEMENTOS:
        if s["keywords"]:
            feito = checar_supp(s["keywords"])
            meta  = s["meta"] or 1
            if feito >= meta:
                # Completo — borda colorida + ✓
                borda     = s["cor"]
                valor_txt = f'✓ {feito}x' if feito > 1 else '✓'
                val_cor   = s["cor"]
                opac      = "1"
            elif feito > 0:
                # Parcialmente feito
                borda     = s["cor"]
                valor_txt = f'{feito}/{meta}x'
                val_cor   = AMBER
                opac      = "1"
            else:
                # Não feito — apagado
                borda     = BORDER
                valor_txt = f'0/{meta}x'
                val_cor   = GHOST
                opac      = "0.45"
        else:
            # Suplemento manual (Magnésio, Ômega, D3) — sempre ✓ fixo
            borda     = s["cor"]
            valor_txt = "✓"
            val_cor   = s["cor"]
            opac      = "1"

        cards += (
            f'<div style="background:{BG3};border:1px solid {borda};border-radius:8px;'
            f'padding:10px 8px;text-align:center;opacity:{opac}">'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;'
            f'color:{GHOST};margin-bottom:4px;line-height:1.4">{s["label"]}</div>'
            f'<div style="font-size:16px;font-weight:800;line-height:1;color:{val_cor}">{valor_txt}</div>'
            f'<div style="font-size:9px;color:{GHOST};margin-top:4px;line-height:1.3">{s["marca"]}</div>'
            f'</div>'
        )

    st.markdown(
        panel(
            ptitl("Suplementação do dia") +
            f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px">{cards}</div>'
        ),
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 5 — BIOMETRIA + MEDICAÇÃO
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Biometria", "Evolução de medidas · Tirzepatida"), unsafe_allow_html=True)

col_med, col_bio = st.columns([1, 2.5])

with col_med:
    df_med = db(
        "SELECT strftime('%d/%m/%Y', datetime(data_hora,'localtime')) as data, "
        "dose_mg FROM medicacao ORDER BY date(data_hora) DESC"
    )
    med_rows = ""
    for i, (_, r) in enumerate(df_med.iterrows()):
        dose = float(r["dose_mg"])
        if dose > 100:
            dose = dose / 1000
        badge = (
            f'<span style="font-family:{MONO};font-size:8px;font-weight:700;'
            f'background:rgba(0,230,118,0.08);color:{GREEN};'
            f'border:1px solid rgba(0,230,118,0.2);padding:1px 6px;'
            f'border-radius:3px;letter-spacing:1px">ATUAL</span>'
            if i == 0 else ""
        )
        med_rows += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 0;border-bottom:1px solid {BG3}">'
            f'<span style="font-family:{MONO};font-size:11px;color:{MUTED}">{r["data"]}</span>'
            f'<span style="font-size:13px;font-weight:700;color:{TEXT}">{dose:.1f} mg</span>'
            f'{badge}</div>'
        )
    st.markdown(
        panel(
            ptitl("Tirzepatida") +
            (med_rows or f'<p style="color:{GHOST};font-size:12px">Sem registros.</p>')
        ),
        unsafe_allow_html=True,
    )

with col_bio:
    df_bio = db("""
        SELECT date(data) as data_ord, strftime('%d/%m/%Y',data) as "Data",
               peso as "Peso", cintura as "Cintura", abdomen as "Abdomen",
               peitoral as "Peitoral", quadril as "Quadril",
               coxa_dir as "CoxaD", coxa_esq as "CoxaE",
               panturrilha_dir as "PantD", biceps_dir as "BicepsD", biceps_esq as "BicepsE"
        FROM medidas WHERE coxa_dir IS NOT NULL
    """)

    if not df_bio.empty:
        df_bio = df_bio.sort_values("data_ord", ascending=True)
        COLS_NUM = ["Peso","Cintura","Abdomen","Peitoral","Quadril",
                    "CoxaD","CoxaE","PantD","BicepsD","BicepsE"]
        idx_rec = df_bio.index[-1]
        diffs = {}
        for c in COLS_NUM:
            atual = df_bio.loc[idx_rec, c]
            if pd.isna(atual):
                diffs[c] = 0
            else:
                dm = atual - df_bio[c].max()
                dn = atual - df_bio[c].min()
                diffs[c] = dm if abs(dm) >= abs(dn) else dn

        df_bio = df_bio.sort_values("data_ord", ascending=False)

        td_base = f"text-align:right;padding:7px 8px;border-bottom:1px solid #0a1020;"

        def cel(val, diff, peso=False, rec=False):
            if pd.isna(val):
                return f"<td style='{td_base}color:{GHOST}'>—</td>"
            fmt = f"{val:.2f}" if peso else f"{val:.1f}"
            un  = "kg" if peso else "cm"
            if not rec or not diff:
                return f"<td style='{td_base}'><b style='color:{TEXT}'>{fmt}</b></td>"
            if diff < 0:
                d = (f"<span style='color:{GREEN};font-size:9px;font-weight:700;"
                     f"display:block'>▼ {abs(diff):.1f}{un}</span>")
            else:
                d = (f"<span style='color:{RED};font-size:9px;font-weight:700;"
                     f"display:block'>+{diff:.1f}{un}</span>")
            return f"<td style='{td_base}'><b style='color:{TEXT}'>{fmt}</b>{d}</td>"

        HEADS = ["Data","Peso","Cintura","Abdômen","Peitoral","Quadril",
                 "Coxa D","Coxa E","Pant. D","Bíceps D","Bíceps E"]
        th_s  = (f"font-family:{MONO};background:{BG3};color:{GHOST};padding:9px 8px;"
                 f"border-bottom:1px solid {BORDER2};text-transform:uppercase;font-size:9px;"
                 f"letter-spacing:1px;text-align:right;white-space:nowrap")
        th_s1 = th_s.replace("text-align:right", "text-align:left")
        ths = (f"<th style='{th_s1}'>{HEADS[0]}</th>" +
               "".join(f"<th style='{th_s}'>{h}</th>" for h in HEADS[1:]))

        body = ""
        for i, (_, row) in enumerate(df_bio.iterrows()):
            rec    = (i == 0)
            row_bg = f"background:rgba(0,212,255,0.04);" if rec else ""
            data_val = (
                f'{row["Data"]} <span style="background:{CYAN};color:{BG};font-size:8px;'
                f'font-weight:900;padding:1px 4px;border-radius:2px;margin-left:4px;'
                f'font-family:{MONO};letter-spacing:1px">ATUAL</span>'
                if rec else row["Data"]
            )
            td_data = (
                f"<td style='text-align:left;padding:7px 8px;border-bottom:1px solid #0a1020;"
                f"color:{CYAN if rec else GHOST};font-weight:{'700' if rec else '400'};{row_bg}'>"
                f"{data_val}</td>"
            )
            body += f"<tr>{td_data}"
            body += cel(row["Peso"], diffs["Peso"], peso=True, rec=rec)
            for c in ["Cintura","Abdomen","Peitoral","Quadril",
                      "CoxaD","CoxaE","PantD","BicepsD","BicepsE"]:
                body += cel(row[c], diffs[c], rec=rec)
            body += "</tr>"

        st.markdown(
            panel(
                ptitl("Evolução de medidas — dos extremos") +
                f'<div style="overflow-x:auto;border-radius:6px;border:1px solid {BORDER}">'
                f'<table style="width:100%;border-collapse:collapse;font-size:12px;'
                f'background:{BG2};min-width:620px">'
                f'<thead><tr>{ths}</tr></thead><tbody>{body}</tbody></table>'
                f'</div>'
            ),
            unsafe_allow_html=True,
        )

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 6 — HISTÓRICO SEMANAL
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Histórico", "Últimos 30 dias · Tendências"), unsafe_allow_html=True)

# Seletor de período
periodo_col, _ = st.columns([1, 3])
with periodo_col:
    periodo = st.selectbox(
        "Período",
        ["7 dias", "14 dias", "30 dias", "90 dias"],
        index=1,
        label_visibility="collapsed"
    )
n_dias = int(periodo.split()[0])

# ── Dados históricos ──────────────────────────────────────────────────────────
df_hist = db(f"""
    SELECT
        date(data_hora) as dia,
        passos, calorias_gastas, distancia_km,
        sono_total_min, sono_profundo_min,
        hrv_ms, pai
    FROM amazfit_dados
    WHERE date(data_hora) >= date('now', '-{n_dias} days')
    ORDER BY dia ASC
""")

df_macro_hist = db(f"""
    SELECT
        date(data_hora, 'localtime') as dia,
        SUM(calorias)    as cal,
        SUM(proteinas)   as prot,
        SUM(carboidratos) as carb,
        SUM(gorduras)    as gord
    FROM refeicoes
    WHERE date(data_hora, 'localtime') >= date('now', '-{n_dias} days')
    GROUP BY dia
    ORDER BY dia ASC
""")

def chart_layout(height=200, show_legend=False):
    return dict(
        height=height, margin=dict(t=10, b=10, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor=BORDER, title=None,
                   tickformat="%d/%m", tickfont=dict(color=GHOST, size=9, family="monospace"),
                   showgrid=True),
        yaxis=dict(gridcolor=BORDER, title=None,
                   tickfont=dict(color=GHOST, size=9), showgrid=True),
        showlegend=show_legend,
        font=dict(family="monospace", color=GHOST),
    )

def linha(df, col, cor, name="", fill=False, dash=None):
    return go.Scatter(
        x=df["dia"], y=df[col], mode="lines+markers", name=name,
        line=dict(color=cor, width=2, dash=dash),
        marker=dict(size=5, color=cor),
        fill="tozeroy" if fill else "none",
        fillcolor=cor.replace("ff", "22") if fill and cor.startswith("#") else "rgba(0,0,0,0)",
        hovertemplate=f"<b>%{{x|%d/%m}}</b><br>{name}: %{{y}}<extra></extra>",
    )

def barra(df, col, cor, name=""):
    return go.Bar(
        x=df["dia"], y=df[col], name=name,
        marker_color=cor, opacity=0.8,
        hovertemplate=f"<b>%{{x|%d/%m}}</b><br>{name}: %{{y}}<extra></extra>",
    )

if not df_hist.empty:

    # ── Linha 1: Passos + Distância ───────────────────────────────────────────
    h1a, h1b = st.columns(2)

    with h1a:
        st.markdown(panel(
            ptitl("👟 Passos diários") +
            f'<div id="chart_passos"></div>'
        ), unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(barra(df_hist, "passos", CYAN, "Passos"))
        fig.add_hline(y=META_PASS, line_dash="dash", line_color=GREEN,
                      line_width=1, opacity=0.5,
                      annotation_text=f"Meta {META_PASS:,}",
                      annotation_font_color=GREEN, annotation_font_size=9)
        fig.update_layout(**chart_layout(180))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with h1b:
        st.markdown(panel(ptitl("📍 Distância (km)")), unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(linha(df_hist, "distancia_km", CYAN, "km", fill=True))
        fig.update_layout(**chart_layout(180))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Linha 2: Sono ─────────────────────────────────────────────────────────
    h2a, h2b = st.columns(2)

    with h2a:
        st.markdown(panel(ptitl("🌙 Sono total (min)")), unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(barra(df_hist, "sono_total_min", PURPLE, "Total"))
        fig.add_trace(barra(df_hist, "sono_profundo_min", CYAN, "Profundo"))
        fig.add_hline(y=META_SONO, line_dash="dash", line_color=RED,
                      line_width=1, opacity=0.5,
                      annotation_text=f"Meta prof. {META_SONO}min",
                      annotation_font_color=RED, annotation_font_size=9)
        fig.update_layout(**chart_layout(180, show_legend=True),
                          barmode="overlay",
                          legend=dict(font=dict(color=GHOST, size=9),
                                      bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with h2b:
        st.markdown(panel(ptitl("💓 HRV · PAI")), unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(linha(df_hist, "hrv_ms",  GREEN,  "HRV (ms)"))
        fig.add_trace(linha(df_hist, "pai",     AMBER,  "PAI", dash="dot"))
        fig.update_layout(**chart_layout(180, show_legend=True),
                          legend=dict(font=dict(color=GHOST, size=9),
                                      bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Linha 3: Nutrição ─────────────────────────────────────────────────────
    if not df_macro_hist.empty:
        h3a, h3b = st.columns(2)

        with h3a:
            st.markdown(panel(ptitl("🔥 Calorias diárias")), unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(barra(df_macro_hist, "cal", GREEN, "Calorias"))
            fig.add_hline(y=META_CAL, line_dash="dash", line_color=CYAN,
                          line_width=1, opacity=0.5,
                          annotation_text=f"Meta {META_CAL}",
                          annotation_font_color=CYAN, annotation_font_size=9)
            fig.update_layout(**chart_layout(180))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with h3b:
            st.markdown(panel(ptitl("🥩 Proteínas diárias (g)")), unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(barra(df_macro_hist, "prot", RED, "Proteínas"))
            fig.add_hline(y=META_PROT, line_dash="dash", line_color=CYAN,
                          line_width=1, opacity=0.5,
                          annotation_text=f"Meta {META_PROT}g",
                          annotation_font_color=CYAN, annotation_font_size=9)
            fig.update_layout(**chart_layout(180))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Tabela resumo semanal ─────────────────────────────────────────────────
    st.markdown(sec("Resumo", f"Médias dos últimos {n_dias} dias"), unsafe_allow_html=True)

    def media(df, col):
        return df[col].replace(0, pd.NA).mean() if col in df.columns else 0

    def fmt_val(val, sufixo="", decimais=0):
        if pd.isna(val) or val == 0:
            return "—"
        return f"{val:.{decimais}f}{sufixo}"

    medias = [
        ("👟", "Passos/dia",       fmt_val(media(df_hist, "passos"), "", 0),
         f"meta {META_PASS:,}"),
        ("📍", "Distância/dia",    fmt_val(media(df_hist, "distancia_km"), " km", 1),
         ""),
        ("🌙", "Sono total/dia",   fmt_val(media(df_hist, "sono_total_min"), " min", 0),
         "≥ 420 min"),
        ("💤", "Sono profundo/dia",fmt_val(media(df_hist, "sono_profundo_min"), " min", 0),
         f"meta {META_SONO} min"),
        ("💓", "HRV médio",        fmt_val(media(df_hist, "hrv_ms"), " ms", 0),
         ""),
        ("⚡", "PAI médio",        fmt_val(media(df_hist, "pai"), "", 0),
         "meta ≥ 100"),
    ]
    if not df_macro_hist.empty:
        medias += [
            ("🔥", "Calorias/dia",  fmt_val(media(df_macro_hist, "cal"), " kcal", 0),
             f"meta {META_CAL}"),
            ("🥩", "Proteínas/dia", fmt_val(media(df_macro_hist, "prot"), " g", 0),
             f"meta {META_PROT}g"),
        ]

    # Grid 4 colunas
    cols_med = st.columns(4)
    for i, (icon, lbl, val, ref) in enumerate(medias):
        with cols_med[i % 4]:
            ref_html = (f'<div style="font-size:10px;color:{GHOST};margin-top:3px">{ref}</div>'
                        if ref else "")
            st.markdown(
                f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:9px;'
                f'padding:12px 14px;margin-bottom:10px">'
                f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
                f'text-transform:uppercase;color:{GHOST};margin-bottom:5px">{icon} {lbl}</div>'
                f'<div style="font-size:20px;font-weight:800;color:{TEXT}">{val}</div>'
                f'{ref_html}</div>',
                unsafe_allow_html=True,
            )

else:
    st.markdown(
        panel(f'<p style="color:{GHOST};font-size:13px;padding:8px 0">'
              f'Ainda sem dados históricos do Amazfit. Rode /sync no bot para começar.</p>'),
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════
# RODAPÉ
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div style="text-align:center;padding:20px 0 6px;border-top:1px solid {BORDER2};margin-top:20px">'
    f'<span style="font-family:{MONO};font-size:9px;color:{GHOST};letter-spacing:2px;text-transform:uppercase">'
    f'sys.health_tracker · leandro r. · rio de janeiro</span></div>',
    unsafe_allow_html=True,
)