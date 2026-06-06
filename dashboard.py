import streamlit as st
import logging
import os, pandas as pd, re, json, requests
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import nutri_engine as NE

# Zepp: evita logs de "sem dados" no stderr do Streamlit Cloud (não são erros de app)
logging.getLogger("zepp_sync").setLevel(logging.ERROR)

# Identificador visível no deploy (Streamlit Cloud → Management → Logs)
_APP_BUILD = "2026-06-06-peso-chart"

# ── Streamlit Cloud: sincroniza st.secrets → os.environ para db.py ───────────
# No Streamlit Community Cloud os segredos ficam em st.secrets, não em os.environ.
# Este shim garante que db.py (que usa os.getenv) receba as variáveis corretas.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

import db as DB

# ── Gemini Vision (análise de fotos) ─────────────────────────────────────────
# Lê a chave diretamente dos secrets do Streamlit Cloud primeiro,
# depois fallback para variável de ambiente local.
_GEMINI_KEY = ""
try:
    _GEMINI_KEY = (st.secrets.get("GEMINI_API_KEY") or "").strip()
except Exception:
    pass
if not _GEMINI_KEY:
    _GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if _GEMINI_KEY:
    # Define GOOGLE_API_KEY para evitar fallback para GCP ADC
    os.environ["GOOGLE_API_KEY"] = _GEMINI_KEY
    genai.configure(api_key=_GEMINI_KEY)


def _gemini_model(nome: str = "gemini-2.5-flash"):
    """Retorna GenerativeModel garantindo que a API key está configurada."""
    if _GEMINI_KEY:
        genai.configure(api_key=_GEMINI_KEY)
    return genai.GenerativeModel(nome)

# ── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SYS.HEALTH // Leandro R.",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="auto",
)

# ── RESET STREAMLIT CHROME + SIDEBAR WIDGET THEME ───────────────────────────
@st.cache_resource
def _app_global_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700;800&display=swap');

:root{
  --sh-bg:#080c14;
  --sh-bg-elevated:#0d1424;
  --sh-bg-subtle:#0a0f1a;
  --sh-border:rgba(255,255,255,.07);
  --sh-border-strong:rgba(0,212,255,.22);
  --sh-text:#e8edf5;
  --sh-text-muted:#8b9cb3;
  --sh-text-dim:#5a6b82;
  --sh-accent:#00d4ff;
  --sh-accent-soft:rgba(0,212,255,.10);
  --sh-radius-sm:6px;
  --sh-radius-md:10px;
  --sh-shadow-sm:0 1px 2px rgba(0,0,0,.35);
  --sh-shadow-md:0 8px 24px rgba(0,0,0,.45);
  --sh-space-2:8px;
  --sh-space-3:12px;
  --sh-space-4:16px;
  --sh-space-5:24px;
  --sh-font-display:'DM Sans',system-ui,sans-serif;
  --sh-font-mono:'Space Mono',ui-monospace,monospace;
}

html,body,.stApp{background:radial-gradient(1100px 500px at 8% -8%,rgba(0,212,255,.06),transparent 50%),var(--sh-bg)!important;color:var(--sh-text)!important;font-family:var(--sh-font-display)!important}
.block-container{padding:1.5rem 2rem!important;max-width:1320px!important;margin-left:auto!important;margin-right:auto!important}
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important}
[data-testid="stHeader"]{background:transparent!important;visibility:visible!important;height:auto!important}
[data-testid="collapsedControl"]{visibility:visible!important;opacity:1!important;display:flex!important}
.stDeployButton{display:none!important}

/* ── Sidebar container ── */
section[data-testid="stSidebar"]{background:#080e1a!important;border-right:1px solid #111c2e!important}
section[data-testid="stSidebar"] > div:first-child{padding:0.75rem 1rem 1rem!important}

/* ── Botão de abrir/fechar sidebar — faixa lateral sempre visível ── */
[data-testid="collapsedControl"]{
  background:#0d1424!important;
  border-right:2px solid #00d4ff!important;
  border-top:none!important;border-bottom:none!important;border-left:none!important;
  color:#00d4ff!important;
  opacity:1!important;
  visibility:visible!important;
  display:flex!important;
  align-items:center!important;
  justify-content:center!important;
  width:20px!important;
  min-height:100vh!important;
  position:fixed!important;
  top:0!important;left:0!important;
  z-index:998!important;
  transition:background .2s ease,box-shadow .2s ease!important;
  box-shadow:2px 0 12px rgba(0,212,255,0.15)!important;
  cursor:pointer!important}
[data-testid="collapsedControl"]:hover{
  background:rgba(0,212,255,0.12)!important;
  box-shadow:2px 0 20px rgba(0,212,255,0.35)!important;
  width:28px!important}
[data-testid="collapsedControl"] svg{
  color:#00d4ff!important;fill:#00d4ff!important;
  width:14px!important;height:14px!important}
[data-testid="stSidebarNav"]{display:none!important}

/* ── Expander ── */
[data-testid="stExpander"]{
  background:#0d1424!important;border:1px solid #1a2035!important;
  border-radius:6px!important;margin-bottom:6px!important;overflow:hidden!important}
[data-testid="stExpander"] summary{
  padding:12px 14px!important;color:#e8edf5!important;min-height:44px!important;
  display:flex!important;align-items:center!important;cursor:pointer!important}
[data-testid="stExpander"] summary p{
  font-family:'Space Mono',monospace!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:1.5px!important;text-transform:uppercase!important;
  color:#e8edf5!important}
[data-testid="stExpander"] summary:hover{background:rgba(0,212,255,0.04)!important}
[data-testid="stExpander"] [data-testid="stExpanderDetails"]{
  padding:8px 12px 12px!important;background:#0a0f1a!important}

/* ── Labels ── */
[data-testid="stTextInput"] label,[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label{
  font-family:'Space Mono',monospace!important;font-size:9px!important;font-weight:700!important;
  letter-spacing:1.5px!important;text-transform:uppercase!important;color:#4a5568!important}

/* ── Text inputs ── */
[data-testid="stTextInput"] input{
  background:#080c14!important;border:1px solid #1a2035!important;border-radius:4px!important;
  color:#e8edf5!important;font-family:'DM Sans',sans-serif!important;font-size:12px!important;
  padding:6px 10px!important}
[data-testid="stTextInput"] input:focus{
  border-color:#00d4ff!important;box-shadow:0 0 0 1px rgba(0,212,255,0.25)!important}

/* ── Number inputs ── */
[data-testid="stNumberInput"] input{
  background:#080c14!important;border:1px solid #1a2035!important;border-radius:4px!important;
  color:#e8edf5!important;font-family:'Space Mono',monospace!important;font-size:12px!important}
[data-testid="stNumberInput"] input:focus{
  border-color:#00d4ff!important;box-shadow:0 0 0 1px rgba(0,212,255,0.25)!important}
[data-testid="stNumberInput"] button{
  background:#0d1424!important;border-color:#1a2035!important;color:#e8edf5!important}

/* ── Radio horizontal (seletor de período) ── */
[data-testid="stRadio"] > div{display:flex!important;gap:8px!important;flex-wrap:wrap!important}
[data-testid="stRadio"] label{
  background:#0c1525!important;border:1px solid #1e2840!important;
  color:#7a8a9a!important;font-family:'Space Mono',monospace!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:1px!important;text-transform:uppercase!important;
  border-radius:20px!important;padding:5px 14px!important;cursor:pointer!important;
  transition:all 0.15s ease!important}
[data-testid="stRadio"] label:has(input:checked){
  background:rgba(0,212,255,0.10)!important;border-color:#00d4ff!important;
  color:#00d4ff!important;box-shadow:0 0 12px rgba(0,212,255,0.15)!important}
[data-testid="stRadio"] [data-baseweb="radio"]{display:none!important}
[data-testid="stRadio"] label span{pointer-events:none!important}

/* ── Selectbox ── */
[data-testid="stSelectbox"] [data-baseweb="select"] > div{
  background:#080c14!important;border-color:#1a2035!important;border-radius:4px!important;
  color:#e8edf5!important;font-size:12px!important}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within{
  border-color:#00d4ff!important}
[data-baseweb="popover"],[data-baseweb="menu"]{
  background:#0d1424!important;border:1px solid #1a2035!important;border-radius:4px!important}
[data-baseweb="option"]{
  background:#0d1424!important;color:#e8edf5!important;font-size:12px!important}
[data-baseweb="option"]:hover{background:#1a2035!important}
[aria-selected="true"][data-baseweb="option"]{
  background:rgba(0,212,255,0.08)!important;color:#00d4ff!important}

/* ── Botões regulares (secondary) ── */
[data-testid="stBaseButton-secondary"]{
  background:#0c1525!important;border:1px solid #1e2840!important;
  color:#7a8a9a!important;font-family:'Space Mono',monospace!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:1.2px!important;text-transform:uppercase!important;
  border-radius:8px!important;padding:10px 12px!important;min-height:44px!important;
  transition:border-color 0.15s,color 0.15s,background 0.15s!important}
[data-testid="stBaseButton-secondary"]:hover{
  border-color:#2a3448!important;color:#e8edf5!important;background:#0d1628!important}
[data-testid="stBaseButton-secondary"]:active{
  background:rgba(0,212,255,0.05)!important}

/* ── Botão nav ATIVO (primary) — glow só no hover ── */
[data-testid="stBaseButton-primary"]{
  background:rgba(0,212,255,0.10)!important;border:1.5px solid #00d4ff!important;
  color:#00d4ff!important;font-family:'Space Mono',monospace!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:1.5px!important;text-transform:uppercase!important;
  border-radius:8px!important;padding:10px 12px!important;min-height:44px!important;
  box-shadow:none!important;
  transition:all 0.15s ease!important}
[data-testid="stBaseButton-primary"]:hover{
  background:rgba(0,212,255,0.17)!important;box-shadow:0 0 20px rgba(0,212,255,0.22)!important;
  transform:translateY(-2px)!important}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stFormSubmitButton"] button:hover{
  transform:translateY(-1px)!important;
  box-shadow:0 4px 16px rgba(0,212,255,.12)!important}
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"],
[data-testid="stFormSubmitButton"] button,
a.sh-nav-link,button[data-baseweb="tab"]{
  transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease,background .18s ease,color .18s ease!important}

/* ── Design system: métricas, seções, zonas ── */
.sh-metric{
  background:linear-gradient(165deg,rgba(13,20,36,.95),rgba(8,12,20,.98));
  border:1px solid var(--sh-border);
  border-radius:var(--sh-radius-md);
  padding:var(--sh-space-4) var(--sh-space-4) var(--sh-space-3);
  box-shadow:var(--sh-shadow-sm);
  min-height:132px;
  display:flex;
  flex-direction:column;
  justify-content:space-between;
  transition:border-color .2s ease,box-shadow .2s ease,transform .15s ease;
}
.sh-metric:hover{
  border-color:var(--sh-border-strong);
  box-shadow:var(--sh-shadow-md);
  transform:translateY(-1px);
}
.sh-metric__accent{
  height:3px;border-radius:3px 3px 0 0;
  margin:-16px -16px 12px;opacity:.9;
}
.sh-metric__label{
  font-family:var(--sh-font-mono);font-size:10px;font-weight:700;
  letter-spacing:.12em;text-transform:uppercase;color:var(--sh-text-dim);
}
.sh-metric__value{
  font-family:var(--sh-font-display);
  font-size:clamp(1.35rem,2.2vw,1.85rem);font-weight:800;
  letter-spacing:-.03em;color:var(--sh-text);line-height:1.05;
  margin-top:6px;
}
.sh-metric__unit{
  font-size:.72em;font-weight:500;color:var(--sh-text-muted);margin-left:.15em;
}
.sh-metric__meta{
  font-size:12px;color:var(--sh-text-muted);line-height:1.45;margin-top:8px;
}
.sh-section{
  display:flex;align-items:baseline;gap:var(--sh-space-3);
  margin:var(--sh-space-5) 0 var(--sh-space-3);
}
.sh-section__tag{
  font-family:var(--sh-font-mono);font-size:11px;font-weight:700;
  letter-spacing:.14em;text-transform:uppercase;color:var(--sh-accent);
}
.sh-section__title{font-size:14px;font-weight:500;color:var(--sh-text-muted)}
.sh-section__rule{flex:1;height:1px;background:var(--sh-border);align-self:center}
.sh-zone{
  font-family:var(--sh-font-mono);font-size:10px;font-weight:700;
  letter-spacing:.18em;text-transform:uppercase;color:var(--sh-text-dim);
  margin:var(--sh-space-4) 0 var(--sh-space-2);
  padding:var(--sh-space-2) var(--sh-space-3);
  border-left:2px solid var(--sh-border-strong);
  border-radius:0 var(--sh-radius-sm) var(--sh-radius-sm) 0;
  background:rgba(0,212,255,.03);
}
[data-testid="stTabs"]{margin-bottom:var(--sh-space-4)!important}
button[data-baseweb="tab"]{letter-spacing:.08em!important;color:var(--sh-text-dim)!important}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--sh-accent)!important}

.sh-lane{background:var(--sh-bg-elevated);border:1px solid var(--sh-border);border-radius:var(--sh-radius-lg);padding:var(--sh-space-5);margin-bottom:var(--sh-space-5);box-shadow:var(--sh-shadow-sm)}
.sh-lane__title{font-size:1.125rem;font-weight:700;letter-spacing:-.02em;color:var(--sh-text)}
.sh-lane__desc{font-size:13px;color:var(--sh-text-muted);margin-top:4px}
.sh-app-header{padding:var(--sh-space-3) 0 var(--sh-space-2)}
.sh-app-header__eyebrow{font-family:var(--sh-font-mono);font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--sh-accent)}
.sh-app-header__title{font-size:clamp(1.35rem,2.2vw,1.65rem);font-weight:800;letter-spacing:-.03em;line-height:1.1;color:var(--sh-text);margin-top:2px}
.sh-app-header__meta{font-size:12px;color:var(--sh-text-dim);margin-top:4px}
.sh-app-header__status{font-size:11px;text-align:right;margin-bottom:8px;line-height:1.5;white-space:nowrap}
.sh-status-dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:5px;vertical-align:middle}
[data-testid="stHorizontalBlock"]:has(.sh-topbar) [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"]{
  min-height:32px!important;font-size:10px!important;letter-spacing:.04em!important;text-transform:none!important}
.sh-metric--hero{background:linear-gradient(145deg,rgba(0,212,255,.08),rgba(13,20,36,.95))}
.sh-metric--hero .sh-metric__value{font-size:clamp(1.5rem,2.4vw,1.85rem)}
.sh-metric--compact .sh-metric__value{font-size:clamp(1.35rem,2vw,1.65rem)}
.sh-nutri-metrics [data-testid="stHorizontalBlock"]{align-items:stretch!important}
.sh-nutri-metrics .sh-metric{min-height:128px;height:100%}
.sh-header-actions{display:flex;flex-direction:column;align-items:flex-end;gap:10px;width:100%}
.sh-header-status{font-family:var(--sh-font-display);font-size:12px;font-weight:500;line-height:1.6;text-align:right}
.sh-header-sync{width:100%;max-width:168px;margin-left:auto}
.sh-header-sync [data-testid="stHorizontalBlock"]{gap:8px!important;width:100%!important;max-width:168px!important;margin-left:auto!important}
.sh-header-sync [data-testid="column"]{flex:1 1 0!important;min-width:0!important;width:auto!important}
.sh-header-sync button[data-testid="stBaseButton-secondary"]{
  min-height:32px!important;max-height:36px!important;padding:5px 10px!important;
  font-family:var(--sh-font-display)!important;font-size:12px!important;font-weight:600!important;
  border-radius:8px!important;letter-spacing:0!important;text-transform:none!important;
  border-color:rgba(0,212,255,.28)!important;background:rgba(0,212,255,.07)!important;width:100%!important}
.sh-header-sync button[data-testid="stBaseButton-secondary"]:hover{
  background:rgba(0,212,255,.14)!important;border-color:#00d4ff!important;
  box-shadow:0 0 14px rgba(0,212,255,.22)!important;transform:translateY(-1px)!important}
.sh-chart-frame{background:var(--sh-bg-subtle);border:1px solid var(--sh-border);border-radius:var(--sh-radius-md);padding:8px 4px 0;margin-bottom:12px}
.sh-side-card{background:var(--sh-bg-surface);border:1px solid var(--sh-border);border-radius:var(--sh-radius-md);padding:12px;margin-bottom:12px}
button:focus-visible,a:focus-visible,summary:focus-visible{
  outline:2px solid var(--sh-accent)!important;outline-offset:2px!important;
}

/* ── Sidebar buttons (mantidos) ── */
section[data-testid="stSidebar"] .stButton button{
  background:rgba(13,20,36,.6)!important;border:1px solid #1a2840!important;
  color:#e8edf5!important;font-family:var(--sh-font-display)!important;font-size:13px!important;
  font-weight:600!important;letter-spacing:0!important;text-transform:none!important;
  border-radius:8px!important;padding:10px 12px!important;width:100%!important;
  min-height:40px!important;text-align:left!important}
section[data-testid="stSidebar"] .stButton button:hover{
  border-color:rgba(0,212,255,.45)!important;color:#00d4ff!important;
  background:rgba(0,212,255,0.1)!important;box-shadow:0 0 16px rgba(0,212,255,.18)!important;
  transform:translateX(3px)!important}
section[data-testid="stSidebar"] .stButton button:active{
  background:rgba(0,212,255,0.14)!important;transform:translateX(1px)!important}

/* ── Botões de ação compactos (✏ ✕ nos cards de refeição e medicação) ── */
/* Alvo: botões secundários dentro de colunas muito estreitas (< 80px) */
[data-testid="stHorizontalBlock"]:has([data-testid="stMarkdownContainer"]) [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"]{
  min-height:34px!important;
  padding:2px 4px!important;
  font-size:13px!important;
  letter-spacing:0!important}

/* ── Selectbox: cursor pointer + hover ciano ── */
[data-baseweb="select"]{cursor:pointer!important}
[data-baseweb="select"] *{cursor:pointer!important}
[data-baseweb="select"] > div:hover{border-color:rgba(0,212,255,0.4)!important}

/* ── Date input compacto (Registro do Dia) ── */
[data-testid="stDateInput"] input{
  font-family:'Space Mono',monospace!important;
  font-size:13px!important;font-weight:700!important;
  padding:6px 10px!important;cursor:pointer!important}
[data-testid="stDateInput"] > div > div{cursor:pointer!important}

/* ── Tirzepatida — botões compactos (+ DOSE e ✏ editar) ── */
[data-testid="stHorizontalBlock"]:has(.sh-med-hdr) button,
[data-testid="stHorizontalBlock"]:has(.sh-med-row) button{
  min-height:24px!important;
  padding:1px 6px!important;
  font-size:9px!important;
  line-height:1!important;
  border-radius:4px!important}

/* ── Sync buttons compactos (topbar direito) ── */
/* Targetamos o stHorizontalBlock que contém .sh-topbar (topbar) → última coluna → botões */
[data-testid="stHorizontalBlock"]:has(.sh-topbar) [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"]{
  min-height:30px!important;
  padding:4px 8px!important;
  font-size:9px!important;
  border-radius:20px!important;
  letter-spacing:0.8px!important;
  border-color:#1a2035!important}
[data-testid="stHorizontalBlock"]:has(.sh-topbar) [data-testid="column"]:last-child [data-testid="stBaseButton-secondary"]:hover{
  border-color:#00d4ff88!important;
  color:#00d4ff!important}

/* ── Painel de conteúdo (container com borda) ── */
[data-testid="stVerticalBlockBorderWrapper"]{
  background:#070b15!important;border:1px solid rgba(0,212,255,0.22)!important;
  border-radius:12px!important;padding:6px 4px!important;
  box-shadow:0 4px 32px rgba(0,0,0,0.45),0 0 30px rgba(0,212,255,0.04)!important;
  margin-top:4px!important}

/* ── Form submit button ── */
[data-testid="stFormSubmitButton"] button{
  background:rgba(0,212,255,0.07)!important;border:1px solid rgba(0,212,255,0.25)!important;
  color:#00d4ff!important;font-family:'Space Mono',monospace!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:1.5px!important;text-transform:uppercase!important;
  border-radius:4px!important;padding:10px 12px!important;width:100%!important;
  min-height:44px!important;transition:all 0.15s ease!important}
[data-testid="stFormSubmitButton"] button:hover{
  background:rgba(0,212,255,0.14)!important;border-color:#00d4ff!important}

/* ── Success / Error alerts ── */
[data-testid="stAlert"]{border-radius:4px!important;font-size:11px!important;padding:6px 10px!important}

/* ── Form ── */
[data-testid="stForm"]{border:none!important;padding:0!important}

/* ── Tabs navegação ── */
[data-testid="stTabs"]{margin-bottom:4px!important}
button[data-baseweb="tab"]{
  font-family:'Space Mono',monospace!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:1.5px!important;text-transform:uppercase!important;
  color:#4a5568!important;padding:10px 18px!important;border:none!important;
  background:transparent!important}
button[data-baseweb="tab"][aria-selected="true"]{color:#00d4ff!important}
[data-baseweb="tab-highlight"]{background:#00d4ff!important;height:2px!important}
[data-baseweb="tab-border"]{background:#1a2035!important}

/* ── Painel entrada (expander no body) ── */
.sh-painel [data-testid="stExpander"]{
  border-color:rgba(0,212,255,0.2)!important;
  border-radius:8px!important}
.sh-painel [data-testid="stExpander"] summary p{
  color:#00d4ff!important;font-size:11px!important}

/* ── Scrollbar on sidebar ── */
section[data-testid="stSidebar"] ::-webkit-scrollbar{width:3px}
section[data-testid="stSidebar"] ::-webkit-scrollbar-track{background:transparent}
section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb{background:#1a2035;border-radius:2px}

/* ══════════════════════════════════════════════════════════
   RESPONSIVE — classes JS-driven (sh-xs / sh-sm / sh-md / sh-lg)
   injetadas via st.html() + fallback media queries
   ══════════════════════════════════════════════════════════ */

/* Suaviza o escurecimento durante rerun (padrão Streamlit) */
[data-testid="stApp"][data-stale="true"]{
  opacity:0.75!important;
  transition:opacity 0.15s ease!important}
[data-testid="stApp"]{
  transition:opacity 0.15s ease!important}

/* Mobile hint: oculto por padrão */
.sh-mobile-hint{
  display:none!important;align-items:center;gap:8px;
  padding:8px 12px;margin-bottom:10px;border-radius:8px;
  background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.2);
  font-family:'Space Mono',monospace;font-size:10px;color:#718096;letter-spacing:0.5px}
.sh-table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto!important}}

/* ── TABLET (md): 3 colunas por linha ── */
html.sh-md [data-testid="stHorizontalBlock"],
html.sh-sm [data-testid="stHorizontalBlock"],
html.sh-xs [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important}

html.sh-md [data-testid="stHorizontalBlock"]>[data-testid="column"]{
  flex:1 1 220px!important;min-width:0!important}

/* ── MOBILE (sm): 2 colunas por linha ── */
html.sh-sm [data-testid="stHorizontalBlock"]>[data-testid="column"]{
  flex:1 1 calc(50% - 10px)!important;min-width:0!important}
html.sh-sm .block-container{padding:0.75rem!important}
html.sh-sm .sh-topbar{flex-direction:column!important;gap:8px!important;align-items:flex-start!important}
html.sh-sm .sh-topbar-right{text-align:left!important}
html.sh-sm .sh-mobile-hint{display:flex!important}
html.sh-sm .sh-supp-grid{grid-template-columns:repeat(3,1fr)!important}

/* ── MINI (xs): 1 coluna por linha ── */
html.sh-xs [data-testid="stHorizontalBlock"]>[data-testid="column"]{
  flex:1 1 100%!important;min-width:0!important}
html.sh-xs .block-container{padding:0.5rem!important}
html.sh-xs .sh-topbar{flex-direction:column!important;gap:6px!important;align-items:flex-start!important}
html.sh-xs .sh-topbar-right{text-align:left!important}
html.sh-xs .sh-mobile-hint{display:flex!important}
html.sh-xs .sh-supp-grid{grid-template-columns:repeat(2,1fr)!important}

/* ── FAB (mobile) — aparece como bolinha ciano fixa ── */
html.sh-sm [data-testid="collapsedControl"],
html.sh-xs [data-testid="collapsedControl"]{
  position:fixed!important;
  bottom:22px!important;right:18px!important;
  top:auto!important;left:auto!important;
  width:52px!important;height:52px!important;
  border-radius:50%!important;
  background:#080e1a!important;
  border:1.5px solid #00d4ff!important;
  box-shadow:0 0 20px rgba(0,212,255,.4),0 4px 18px rgba(0,0,0,.7)!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  z-index:9999!important;
  transition:box-shadow .2s ease,transform .15s ease!important}
html.sh-sm [data-testid="collapsedControl"]:hover,
html.sh-xs [data-testid="collapsedControl"]:hover{
  box-shadow:0 0 32px rgba(0,212,255,.65),0 6px 24px rgba(0,0,0,.8)!important;
  transform:scale(1.05)!important}
html.sh-sm [data-testid="collapsedControl"] svg,
html.sh-xs [data-testid="collapsedControl"] svg{
  color:#00d4ff!important;fill:#00d4ff!important;
  width:22px!important;height:22px!important}
html.sh-sm section[data-testid="stSidebar"],
html.sh-xs section[data-testid="stSidebar"]{
  width:100vw!important;max-width:340px!important}

/* ── Fallback com media queries (para o primeiro render antes do JS rodar) ── */
@media(max-width:960px){
  [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important}
  [data-testid="stHorizontalBlock"]>[data-testid="column"]{
    flex:1 1 220px!important;min-width:0!important}}

/* ── MOBILE: sidebar nunca sobrepõe — FAB no canto inferior direito ── */
@media(max-width:768px){
  /* Força sidebar como drawer lateral, não overlay full-screen */
  section[data-testid="stSidebar"]{
    width:280px!important;max-width:88vw!important;
    position:fixed!important;left:0!important;top:0!important;
    height:100vh!important;z-index:1000!important;
    box-shadow:4px 0 24px rgba(0,0,0,0.7)!important}

  /* Garante que o conteúdo principal não fique coberto */
  .main .block-container{
    padding:0.75rem 0.75rem 80px!important;
    margin-left:0!important;width:100%!important}

  /* FAB circular para abrir/fechar sidebar */
  [data-testid="collapsedControl"]{
    position:fixed!important;bottom:20px!important;right:16px!important;
    top:auto!important;left:auto!important;
    width:50px!important;height:50px!important;min-height:50px!important;
    border-radius:50%!important;
    background:#080e1a!important;
    border:2px solid #00d4ff!important;
    box-shadow:0 0 20px rgba(0,212,255,.45),0 4px 16px rgba(0,0,0,.7)!important;
    display:flex!important;align-items:center!important;justify-content:center!important;
    z-index:9999!important;
    transition:box-shadow .2s,transform .15s!important}
  [data-testid="collapsedControl"]:active{transform:scale(0.93)!important}
  [data-testid="collapsedControl"] svg{
    color:#00d4ff!important;fill:#00d4ff!important;
    width:20px!important;height:20px!important}

  /* Colunas: 2 por linha em mobile */
  .block-container{padding:0.75rem!important}
  .sh-mobile-hint{display:flex!important}
  .sh-supp-grid{grid-template-columns:repeat(3,1fr)!important}
  [data-testid="stHorizontalBlock"]>[data-testid="column"]{
    flex:1 1 calc(50% - 10px)!important}
  .sh-topbar{flex-direction:column!important;gap:8px!important;align-items:flex-start!important}
  .sh-topbar-right{text-align:left!important}}

@media(max-width:480px){
  /* Mini mobile: 1 coluna */
  [data-testid="stHorizontalBlock"]>[data-testid="column"]{flex:1 1 100%!important}
  .sh-supp-grid{grid-template-columns:repeat(2,1fr)!important}
  .block-container{padding:0.5rem!important}
  section[data-testid="stSidebar"]{max-width:95vw!important}}


/* ── v4: âncoras + scroll contínuo ── */
div[id^="sec-"]{scroll-margin-top:72px}
.sh-nav-link{text-transform:none!important;transition:border-color .15s,color .15s!important}
.sh-nav-link:hover{border-color:rgba(0,212,255,.35)!important;color:var(--sh-accent)!important;
  background:rgba(0,212,255,.08)!important;transform:translateX(4px)!important;
  box-shadow:0 0 14px rgba(0,212,255,.15)!important}
a.sh-nav-active.sh-nav-link{border-color:rgba(0,212,255,.4)!important;background:rgba(0,212,255,.08)!important}
section[data-testid="stSidebar"]{font-family:var(--sh-font-display)!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]{font-family:var(--sh-font-display)!important}
.sh-sidebar-brand{font-family:var(--sh-font-mono);font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--sh-accent);
  margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--sh-border);display:flex;align-items:center;gap:8px}
.sh-side-section{font-family:var(--sh-font-display);font-size:11px;font-weight:600;color:var(--sh-text-muted);margin:12px 0 8px}
.sh-side-kpis{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.sh-side-kpi{background:var(--sh-bg-subtle);border:1px solid var(--sh-border);border-radius:var(--sh-radius-md);padding:10px 12px}
.sh-side-kpi__l{display:block;font-family:var(--sh-font-display);font-size:11px;color:var(--sh-text-dim);font-weight:500}
.sh-side-kpi__v{display:block;font-family:var(--sh-font-display);font-size:17px;font-weight:800;margin-top:4px;letter-spacing:-.02em}
.sh-wearable-panel{margin-top:12px;padding-top:12px;border-top:1px solid var(--sh-border)}
.sh-wearable-panel__title{font-family:var(--sh-font-display);font-size:12px;font-weight:700;color:var(--sh-text);letter-spacing:.02em;margin-bottom:10px}
.sh-wearable-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.sh-wearable-card{background:var(--sh-bg-subtle);border:1px solid var(--sh-border);border-radius:var(--sh-radius-md);padding:12px 14px;min-height:72px;
  display:flex;flex-direction:column;justify-content:space-between;transition:border-color .18s ease,box-shadow .18s ease}
.sh-wearable-card:hover{border-color:rgba(0,212,255,.3);box-shadow:0 4px 16px rgba(0,0,0,.35)}
.sh-wearable-card__label{font-family:var(--sh-font-display);font-size:11px;font-weight:500;color:var(--sh-text-muted)}
.sh-wearable-card__value{font-family:var(--sh-font-display);font-size:20px;font-weight:800;letter-spacing:-.03em;line-height:1.1;margin-top:6px}
.sh-modal-zone{background:var(--sh-bg-subtle);border:1px solid var(--sh-border);border-radius:var(--sh-radius-md);padding:var(--sh-space-4);margin-bottom:8px}
.sh-modal-zone__title{font-family:var(--sh-font-display);font-size:13px;font-weight:700;color:var(--sh-text);margin-bottom:10px}
.sh-modal-zone__sub{font-size:12px;color:var(--sh-text-muted);margin-bottom:12px}
.sh-agua-chips [data-testid="stHorizontalBlock"]{gap:8px!important}
.sh-agua-chips button[data-testid="stBaseButton-secondary"]{
  min-height:40px!important;font-family:var(--sh-font-display)!important;font-size:12px!important;
  font-weight:600!important;border-radius:8px!important;letter-spacing:0!important;text-transform:none!important}
.sh-agua-chips button[data-testid="stBaseButton-secondary"]:hover{
  border-color:rgba(0,212,255,.45)!important;background:rgba(0,212,255,.1)!important;
  transform:translateY(-2px)!important;box-shadow:0 0 14px rgba(0,212,255,.18)!important}
[data-testid="stDialog"] [data-testid="stFormSubmitButton"] button,
[data-testid="stDialog"] [data-testid="stBaseButton-primary"]{
  font-family:var(--sh-font-display)!important;font-size:13px!important;font-weight:600!important;
  letter-spacing:0!important;text-transform:none!important;min-height:42px!important}
section[data-testid="stSidebar"] .stButton button{text-transform:none!important;letter-spacing:0!important;font-size:13px!important}
button[data-baseweb="tab"]{text-transform:none!important;letter-spacing:.02em!important;font-size:12px!important}
html.sh-sm .sh-metric--hero,html.sh-xs .sh-metric--hero{min-height:140px}
html.sh-sm [data-testid="stHorizontalBlock"]:has(.sh-metric--hero)>[data-testid="column"],
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-metric--hero)>[data-testid="column"]{flex:1 1 100%!important}
html.sh-md [data-testid="stHorizontalBlock"]:has(.sh-metric--compact)>[data-testid="column"]{flex:1 1 calc(33.33% - 8px)!important}
html.sh-sm [data-testid="stHorizontalBlock"]:has(.sh-metric--compact)>[data-testid="column"],
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-metric--compact)>[data-testid="column"]{flex:1 1 calc(50% - 8px)!important}
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-metric--compact)>[data-testid="column"]:only-child,
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-metric--hero)>[data-testid="column"]{flex:1 1 100%!important}
html.sh-sm .sh-header-actions,html.sh-xs .sh-header-actions{align-items:flex-start!important}
html.sh-sm .sh-header-status,html.sh-xs .sh-header-status{text-align:left!important}
html.sh-sm .sh-header-sync,html.sh-xs .sh-header-sync{max-width:100%!important;margin-left:0!important}
html.sh-sm .sh-wearable-card__value,html.sh-xs .sh-wearable-card__value{font-size:18px!important}
@media(max-width:768px){
  div[id^="sec-"]{scroll-margin-top:56px}
  [data-testid="stTabs"] [role="tablist"]{overflow-x:auto!important;flex-wrap:nowrap!important;-webkit-overflow-scrolling:touch}
  button[data-baseweb="tab"]{flex:0 0 auto!important;white-space:nowrap!important}}
@media(max-width:480px){
  .sh-side-kpis{grid-template-columns:1fr!important}
  div[id^="sec-"]{scroll-margin-top:48px}}

/* ── Overlay semitransparente atrás do sidebar aberto em mobile ── */
@media(max-width:768px){
  section[data-testid="stSidebar"][aria-expanded="true"]::before{
    content:'';
    position:fixed;inset:0;
    background:rgba(0,0,0,0.55);
    z-index:999;
    pointer-events:auto;
  }
}
</style>
"""

st.markdown(_app_global_css(), unsafe_allow_html=True)


@st.cache_resource
def _app_breakpoint_js() -> str:
    return """
<script>
(function(){
  function bp(){
    var w=window.innerWidth;
    var h=document.documentElement;
    h.classList.remove('sh-xs','sh-sm','sh-md','sh-lg');
    if(w<=400)      h.classList.add('sh-xs');
    else if(w<=680) h.classList.add('sh-sm');
    else if(w<=960) h.classList.add('sh-md');
    else            h.classList.add('sh-lg');
  }
  bp();
  window.addEventListener('resize',bp);
})();
</script>
"""

st.html(_app_breakpoint_js())

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
    return DB.query(query, params)

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
        f'<span style="font-family:{MONO};font-size:12px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{CYAN};background:rgba(0,212,255,0.07);'
        f'border:1px solid rgba(0,212,255,0.2);border-radius:3px;padding:3px 8px">{tag}</span>'
        f'<span style="font-size:13px;color:{MUTED}">{titulo}</span>'
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
        f'<div style="font-family:{MONO};font-size:13px;font-weight:700;letter-spacing:1px;'
        f'text-transform:uppercase;color:{TEXT};margin-bottom:12px">{txt}</div>'
    )


def sh_section(tag: str, titulo: str = "") -> str:
    title_html = f'<span class="sh-section__title">{titulo}</span>' if titulo else ""
    return (
        f'<div class="sh-section">'
        f'<span class="sh-section__tag">{tag}</span>{title_html}'
        f'<div class="sh-section__rule"></div></div>'
    )


def sh_zone(label: str) -> str:
    return f'<div class="sh-zone">{label}</div>'


def sh_metric(
    accent: str,
    label: str,
    value: str,
    unit: str = "",
    meta: str = "",
    extra_html: str = "",
    variant: str = "",
) -> str:
    unit_html = f'<span class="sh-metric__unit">{unit}</span>' if unit else ""
    meta_html = f'<div class="sh-metric__meta">{meta}</div>' if meta else ""
    extra_block = f'<div class="sh-metric__meta">{extra_html}</div>' if extra_html else ""
    mod = f" sh-metric--{variant}" if variant else ""
    return (
        f'<div class="sh-metric{mod}">'
        f'<div class="sh-metric__accent" style="background:{accent}"></div>'
        f'<div class="sh-metric__label">{label}</div>'
        f'<div class="sh-metric__value">{value}{unit_html}</div>'
        f'{meta_html}{extra_block}</div>'
    )


def sh_lane(title: str, desc: str = "") -> str:
    d = f'<div class="sh-lane__desc">{desc}</div>' if desc else ""
    return f'<div class="sh-lane"><div class="sh-lane__title">{title}</div>{d}'


def sh_lane_close() -> str:
    return "</div>"


def sh_kpi_chip(label: str, value: str, sub: str = "", color: str = "") -> str:
    style = f' style="color:{color}"' if color else ""
    sub_html = f'<span class="sh-kpi-chip__sub">{sub}</span>' if sub else ""
    return (
        f'<div class="sh-kpi-chip"><span class="sh-kpi-chip__label">{label}</span>'
        f'<span class="sh-kpi-chip__value"{style}>{value}</span>{sub_html}</div>'
    )



# ── NOTIFICAÇÕES VISUAIS ─────────────────────────────────────────────────────
def _notif(msg: str, tipo: str = "ok"):
    """
    Agenda uma notificação animada para ser exibida no próximo render.
    tipo: 'ok' (verde) | 'err' (vermelho) | 'info' (ciano)
    """
    st.session_state["_notif_pending"] = (msg, tipo)


def _render_goal_celebration(kind: str):
    """Overlay animado em tela cheia ao bater meta de proteína ou água."""
    cfg = {
        "protein": ("🥩", "Meta de proteína!", "#00e676", "rgba(0,230,118"),
        "agua":    ("💧", "Meta de água!", "#a78bfa", "rgba(167,139,250"),
    }
    ic, titulo, cor, rgba = cfg.get(kind, cfg["protein"])
    particles = "".join(
        f'<div style="position:absolute;left:{10 + i * 11}%;bottom:-20px;font-size:{18 + (i % 3) * 6}px;'
        f'animation:shGoalFloat {2.2 + i * 0.15}s linear {i * 0.08}s forwards">{p}</div>'
        for i, p in enumerate(["✨", "⭐", "💫", "🎉", "✨", "⭐"])
    )
    st.html(f"""
<style>
@keyframes shGoalPop {{
  0%   {{ opacity:0; transform:scale(.6); }}
  18%  {{ opacity:1; transform:scale(1.05); }}
  35%  {{ transform:scale(1); }}
  80%  {{ opacity:1; }}
  100% {{ opacity:0; }}
}}
@keyframes shGoalRing {{
  0%   {{ transform:scale(.4); opacity:.9; }}
  100% {{ transform:scale(2.8); opacity:0; }}
}}
@keyframes shGoalFloat {{
  0%   {{ transform:translateY(0) rotate(0deg); opacity:1; }}
  100% {{ transform:translateY(-120vh) rotate(720deg); opacity:0; }}
}}
</style>
<div style="position:fixed;inset:0;z-index:9999999;pointer-events:none;
  display:flex;align-items:center;justify-content:center;
  background:radial-gradient(circle at 50% 40%,{rgba},.18),rgba(0,0,0,.72);
  animation:shGoalPop 3.2s ease forwards">
  <div style="position:absolute;width:180px;height:180px;border-radius:50%;
    border:3px solid {cor};animation:shGoalRing 1.8s ease-out infinite"></div>
  <div style="text-align:center">
    <div style="font-size:64px;line-height:1;margin-bottom:12px">{ic}</div>
    <div style="font-family:'Space Mono',monospace;font-size:22px;font-weight:800;
      color:{cor};letter-spacing:2px;text-transform:uppercase">{titulo}</div>
  </div>
  {particles}
</div>
""")


def _render_notif_pendente():
    """
    Renderiza a notificação pendente (se houver) como overlay fixo animado.
    Chamar UMA VEZ no início do corpo da página.
    """
    if "_notif_pending" not in st.session_state:
        return
    msg, tipo = st.session_state.pop("_notif_pending")
    cor = {"ok": "#00e676", "err": "#ff6b6b", "info": "#00d4ff"}.get(tipo, "#00e676")
    icone = {"ok": "✓", "err": "✗", "info": "ℹ"}.get(tipo, "✓")
    st.html(f"""
<style>
@keyframes _sh_notif {{
  0%   {{ opacity:0; transform:translate(-50%,20px) scale(.96); }}
  15%  {{ opacity:1; transform:translate(-50%,0)    scale(1);   }}
  75%  {{ opacity:1; transform:translate(-50%,0)    scale(1);   }}
  100% {{ opacity:0; transform:translate(-50%,12px) scale(.97); }}
}}
</style>
<div style="
  position:fixed; bottom:36px; left:50%;
  background:#0c1525; border:1.5px solid {cor};
  border-radius:12px; padding:14px 32px;
  font-family:'Space Mono',monospace; font-size:13px; font-weight:700;
  color:{cor}; letter-spacing:1.2px; white-space:nowrap;
  box-shadow:0 8px 40px rgba(0,0,0,.85), 0 0 28px {cor}44;
  z-index:999999; pointer-events:none;
  animation:_sh_notif 2.8s cubic-bezier(.22,.68,0,1.2) forwards;
">{icone}&nbsp; {msg}</div>
""")


# ── Performance: invalidação cirúrgica + toggles em fragment ───────────────────
def _invalidate_cache(*funcs):
    """Limpa só as funções afetadas — evita st.cache_data.clear() global."""
    for fn in funcs:
        try:
            fn.clear()
        except Exception:
            pass


def _toggle_key(session_key: str, default: bool = False) -> bool:
    return bool(st.session_state.get(session_key, default))


def _flip_toggle(session_key: str) -> None:
    st.session_state[session_key] = not _toggle_key(session_key)


def _ui_toggle_button(label_open: str, label_closed: str, session_key: str, btn_key: str):
    """
    Botão ▾/▴ para seções colapsáveis.
    Usa rerun completo: o painel expansível fica fora desta função.
    (Fragment isolado só no botão não reexecuta o conteúdo — Sessão 2 unifica os dois.)
    """
    open_ = _toggle_key(session_key)
    lbl = label_open if open_ else label_closed
    if st.button(lbl, key=btn_key, use_container_width=True):
        _flip_toggle(session_key)
        st.rerun()


def _append_alimento_carrinho(carrinho: list, row) -> bool:
    """Adiciona alimento ao carrinho se ainda não estiver. Retorna True se adicionou."""
    bid = int(row["id"])
    if any(c["id"] == bid for c in carrinho):
        return False
    carrinho.append({
        "id": bid,
        "descricao": str(row["descricao"]),
        "qtd_ref": float(row.get("qtd_referencia") or 100),
        "unidade": str(row.get("unidade_referencia") or "g"),
        "kcal_ref": float(row.get("calorias") or 0),
        "prot_ref": float(row.get("proteinas") or 0),
        "carb_ref": float(row.get("carboidratos") or 0),
        "gord_ref": float(row.get("gorduras") or 0),
    })
    return True


def _componentes_to_carrinho(comp_json, descricao, kcal=0, prot=0, carb=0, gord=0):
    """Converte componentes_json da refeição para itens do carrinho."""
    items = []
    if comp_json:
        try:
            data = json.loads(comp_json) if isinstance(comp_json, str) else comp_json
            if isinstance(data, list):
                for i, d in enumerate(data):
                    qtd = float(d.get("gramas") or d.get("qtd") or 100)
                    items.append({
                        "id": int(d.get("banco_id") or 0),
                        "descricao": str(d.get("nome") or descricao),
                        "qtd_ref": qtd if qtd > 0 else 100.0,
                        "unidade": str(d.get("unidade") or "g"),
                        "kcal_ref": float(d.get("kcal") or 0),
                        "prot_ref": float(d.get("prot") or 0),
                        "carb_ref": float(d.get("carb") or 0),
                        "gord_ref": float(d.get("gord") or 0),
                        "_uid": int(d.get("banco_id") or 0) or (900000 + i),
                    })
        except Exception:
            pass
    if not items and descricao:
        items.append({
            "id": 0,
            "descricao": descricao,
            "qtd_ref": 100.0,
            "unidade": "g",
            "kcal_ref": float(kcal),
            "prot_ref": float(prot),
            "carb_ref": float(carb),
            "gord_ref": float(gord),
            "_uid": 900001,
        })
    return items


def _salvar_combo_favorito(descricao, componentes, cat, kcal, prot, carb, gord):
    """Salva combinação de refeição (ex: Banana + Pasta de Amendoim) como favorito."""
    desc = (descricao or "").strip()
    if not desc:
        return
    comp_json = json.dumps(componentes, ensure_ascii=False)
    existente = DB.query("SELECT id FROM alimentos_favoritos WHERE descricao=?", [desc])
    if existente.empty:
        DB.execute(
            "INSERT INTO alimentos_favoritos "
            "(descricao,categoria,calorias,proteinas,carboidratos,gorduras,componentes_json,favorito) "
            "VALUES (?,?,?,?,?,?,?,1)",
            [desc, cat, kcal, prot, carb, gord, comp_json],
        )
    else:
        DB.execute(
            "UPDATE alimentos_favoritos SET categoria=?,calorias=?,proteinas=?,carboidratos=?,"
            "gorduras=?,componentes_json=?,favorito=1 WHERE descricao=?",
            [cat, kcal, prot, carb, gord, comp_json, desc],
        )
    _invalidate_cache(_q_alimentos_favoritos)
    _notif(f"⭐ '{desc[:48]}' salvo nos favoritos!")


def _salvar_alimento_db(descricao, categoria, kcal, prot, carb, gord, componentes_json="[]"):
    """Salva ou atualiza alimento no banco de favoritos."""
    if not descricao or not descricao.strip():
        return
    try:
        existente = DB.query(
            "SELECT id, vezes_usado FROM alimentos_favoritos WHERE descricao=?",
            [descricao.strip()]
        )
        if existente.empty:
            DB.execute(
                "INSERT INTO alimentos_favoritos (descricao,categoria,calorias,proteinas,carboidratos,gorduras,componentes_json) VALUES (?,?,?,?,?,?,?)",
                [descricao.strip(), categoria, kcal, prot, carb, gord, componentes_json]
            )
        else:
            DB.execute(
                "UPDATE alimentos_favoritos SET vezes_usado=vezes_usado+1 WHERE descricao=?",
                [descricao.strip()]
            )
    except Exception:
        pass


# ── ZEPP SYNC ─────────────────────────────────────────────────────────────────
def _runtime_allows_zepp_autosync() -> bool:
    """Auto-sync só em dev local; Cloud/headless usa botão 🔄 Zepp (evita crash no boot)."""
    if os.getenv("ZEPP_AUTO_SYNC", "").strip().lower() in ("0", "false", "no"):
        return False
    if os.getenv("STREAMLIT_RUNTIME_ENV") or os.getenv("STREAMLIT_SHARING_MODE"):
        return False
    try:
        if st.get_option("server.headless"):
            return False
    except Exception:
        pass
    return True


def _zepp_sync_dashboard(day: str | None = None) -> str:
    """
    Chama zepp_sync + salva no banco. Retorna mensagem de status.
    Nunca propaga exceção — falha de API não deve derrubar o dashboard.
    """
    try:
        import zepp_sync as _zs
        d = day or datetime.now(_BR).strftime("%Y-%m-%d")
        try:
            row = _zs.zepp_sync(d)
        except Exception:
            return "Zepp: API indisponível"
        if not row:
            return "Zepp: sem dados novos"
        try:
            if not _zs.save(row):
                return "Zepp: falha ao salvar no banco"
        except Exception:
            return "Zepp: falha ao salvar no banco"
        return (
            f"Amazfit sincronizado — {row['passos']:,} passos · "
            f"{row['sono_total_min']} min sono"
        )
    except Exception as e:
        return f"Erro sync: {e}"


def _hevy_sync_dashboard() -> str:
    """
    Sincroniza os treinos do Hevy API e salva no banco de dados.
    """
    hevy_key = os.getenv("HEVY_API_KEY", "").strip()
    if not hevy_key:
        return "⚠️ HEVY_API_KEY não configurada no .env ou Secrets."
    try:
        url = "https://api.hevyapp.com/v1/workouts"
        headers = {
            "api-key": hevy_key,
            "Content-Type": "application/json"
        }
        r = requests.get(url, headers=headers, params={"page": 1, "pageSize": 10}, timeout=10)
        if r.status_code != 200:
            return f"Erro Hevy (HTTP {r.status_code}): {r.text[:100]}"
        data = r.json()
        workouts = data.get("workouts", [])
        if not workouts:
            return "Hevy: Nenhum treino encontrado."
        count = 0
        for w in workouts:
            w_id = w.get("id") or w.get("workout_id")
            title = w.get("title", "Treino de Musculação")
            desc = w.get("description", "")
            start_iso = w.get("start_time")
            end_iso = w.get("end_time")
            dt_formatted = start_iso.replace("T", " ").replace("Z", "") if start_iso else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            duracao = 0
            if start_iso and end_iso:
                try:
                    start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                    duracao = int((end_dt - start_dt).total_seconds() / 60)
                except Exception:
                    pass
            volume_kg = 0.0
            exercises = w.get("exercises", [])
            for ex in exercises:
                sets = ex.get("sets", [])
                for s in sets:
                    w_kg = float(s.get("weight_kg") or 0.0)
                    reps = int(s.get("reps") or 0)
                    volume_kg += w_kg * reps
            exercicios_json = json.dumps(exercises)
            DB.execute("DELETE FROM hevy_treinos WHERE id=?", [w_id])
            DB.execute(
                "INSERT INTO hevy_treinos (id, data_hora, titulo, descricao, exercicios_json, duracao_min, volume_kg) VALUES (?,?,?,?,?,?,?)",
                [w_id, dt_formatted, title, desc, exercicios_json, duracao, volume_kg]
            )
            count += 1
        return f"Hevy sincronizado — {count} treinos atualizados."
    except Exception as e:
        return f"Erro Hevy: {e}"


# ── GOOGLE CALENDAR ──────────────────────────────────────────────────────────
def _gcal_secret(key: str) -> str:
    """Lê secret Google Calendar (st.secrets → os.environ)."""
    try:
        val = st.secrets.get(key)
        if val:
            return str(val).strip()
    except Exception:
        pass
    return (os.getenv(key) or "").strip()


def _gcal_configured() -> bool:
    return all(_gcal_secret(k) for k in (
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN",
    ))


def _get_gcal_creds():
    """Monta credenciais OAuth2 usando refresh_token (sem browser)."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        return None

    client_id = _gcal_secret("GOOGLE_CLIENT_ID")
    client_secret = _gcal_secret("GOOGLE_CLIENT_SECRET")
    refresh_token = _gcal_secret("GOOGLE_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds


def _gcal_erro_msg(exc: Exception) -> str:
    msg = str(exc)
    if "invalid_grant" in msg.lower():
        return (
            "Refresh token expirado ou revogado. Rode "
            "`python get_gcal_token.py` localmente e atualize "
            "GOOGLE_REFRESH_TOKEN nos Secrets do Streamlit (e no .env local)."
        )
    return msg


@st.cache_data(ttl=300)
def _get_gcal_eventos(dia: str) -> list[dict]:
    """
    Busca todos os eventos do Google Calendar para o dia informado.
    Retorna lista de dicts: {titulo, inicio, fim, local, descricao, cor, dia_todo}.
    Cache de 5 minutos.
    """
    try:
        from googleapiclient.discovery import build
        import googleapiclient.errors

        creds = _get_gcal_creds()
        if creds is None:
            if not _gcal_configured():
                return [{"titulo": "Erro ao carregar agenda: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e "
                                   "GOOGLE_REFRESH_TOKEN são obrigatórios nos Secrets.",
                         "inicio": "", "fim": "", "local": "", "descricao": "", "cor": RED, "dia_todo": False}]
            return [{"titulo": "Erro ao carregar agenda: falha ao renovar token OAuth. "
                               "Gere um novo refresh token com get_gcal_token.py.",
                         "inicio": "", "fim": "", "local": "", "descricao": "", "cor": RED, "dia_todo": False}]

        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        # Intervalo do dia em UTC (São Paulo = UTC-3)
        inicio_dia = f"{dia}T03:00:00Z"   # 00:00 BRT = 03:00 UTC
        fim_dia    = f"{dia}T26:59:59Z"   # 23:59 BRT = 02:59+1 UTC → usa dia+1
        from datetime import date as _date2, timedelta
        dia_dt  = _date2.fromisoformat(dia)
        fim_utc = (dia_dt + timedelta(days=1)).isoformat() + "T02:59:59Z"

        result = service.events().list(
            calendarId="primary",
            timeMin=f"{dia}T03:00:00Z",
            timeMax=fim_utc,
            singleEvents=True,
            orderBy="startTime",
            maxResults=15,
        ).execute()

        eventos = []
        for ev in result.get("items", []):
            start = ev.get("start", {})
            end   = ev.get("end",   {})
            dia_todo = "date" in start and "dateTime" not in start

            if dia_todo:
                inicio_fmt = "Dia todo"
                fim_fmt    = ""
            else:
                def _fmt_hr(iso):
                    try:
                        from datetime import datetime as _dt2
                        dt = _dt2.fromisoformat(iso.replace("Z", "+00:00"))
                        dt_br = dt.astimezone(_BR)
                        return dt_br.strftime("%H:%M")
                    except Exception:
                        return iso[:5]
                inicio_fmt = _fmt_hr(start.get("dateTime", ""))
                fim_fmt    = _fmt_hr(end.get("dateTime",   ""))

            # Cor do evento (Google retorna colorId 1-11)
            _gcal_cores = {
                "1":"#7986cb","2":"#33b679","3":"#8e24aa","4":"#e67c73",
                "5":"#f6bf26","6":"#f4511e","7":"#039be5","8":"#616161",
                "9":"#3f51b5","10":"#0b8043","11":"#d50000",
            }
            cor_ev = _gcal_cores.get(ev.get("colorId", ""), CYAN)

            eventos.append({
                "titulo":    ev.get("summary", "(sem título)"),
                "inicio":    inicio_fmt,
                "fim":       fim_fmt,
                "local":     ev.get("location", ""),
                "descricao": ev.get("description", ""),
                "cor":       cor_ev,
                "dia_todo":  dia_todo,
            })
        return eventos
    except Exception as e:
        return [{"titulo": f"Erro ao carregar agenda: {_gcal_erro_msg(e)}", "inicio": "", "fim": "",
                 "local": "", "descricao": "", "cor": RED, "dia_todo": False}]


# ── METAS ────────────────────────────────────────────────────────────────────
TMB       = 1863  # Taxa Metabólica Basal — meta calórica é calculada dinamicamente
META_PROT = 190
META_CARB = 241
META_GORD = 75
META_AGUA = 3.5
META_PASS = 10000
META_SONO = 90
META_PAI  = 100

_BR      = ZoneInfo("America/Sao_Paulo")
hoje_sql = datetime.now(_BR).strftime("%Y-%m-%d")
hoje_pt  = datetime.now(_BR).strftime("%d/%m/%Y")
hora_now = datetime.now(_BR).strftime("%H:%M")
dia_sem  = ["SEG","TER","QUA","QUI","SEX","SAB","DOM"][datetime.now(_BR).weekday()]

# ── DADOS — funções com cache (TTL 60s, invalidadas por _invalidate_cache) ──

@st.cache_data(ttl=60)
def _q_peso():
    return DB.query("SELECT peso FROM medidas WHERE peso IS NOT NULL ORDER BY date(data) DESC LIMIT 1")

@st.cache_data(ttl=60)
def _q_agua(dia: str):
    return DB.query(
        "SELECT COALESCE(SUM(quantidade_ml),0) as t FROM agua "
        "WHERE date(data_hora,'localtime')=?", [dia])

@st.cache_data(ttl=60)
def _q_macros(dia: str):
    return DB.query(
        "SELECT COALESCE(SUM(calorias),0) as cal, COALESCE(SUM(proteinas),0) as prot,"
        "COALESCE(SUM(carboidratos),0) as carb, COALESCE(SUM(gorduras),0) as gord "
        "FROM refeicoes WHERE date(data_hora,'localtime')=?", [dia])

@st.cache_data(ttl=60)
def _q_amazfit():
    return DB.query("SELECT * FROM amazfit_dados ORDER BY date(data_hora) DESC LIMIT 1")


def _amazfit_hoje_df() -> pd.DataFrame:
    """Último registro Amazfit; DataFrame vazio se a consulta ou o sync falhar."""
    try:
        df = _q_amazfit()
        return df if df is not None and not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def _q_refeicoes(dia: str):
    return DB.query(
        "SELECT id, time(datetime(data_hora,'localtime')) as hora, "
        "COALESCE(categoria,'Lanche') as cat, descricao as alimento, "
        "COALESCE(calorias,0) as kcal, COALESCE(proteinas,0) as prot, "
        "COALESCE(carboidratos,0) as carb, COALESCE(gorduras,0) as gord, "
        "componentes_json "
        "FROM refeicoes WHERE date(data_hora,'localtime')=? "
        "ORDER BY data_hora DESC LIMIT 20", [dia])

@st.cache_data(ttl=60)
def _q_supp_check(dia: str):
    return DB.query(
        "SELECT descricao, COUNT(*) as qtd FROM refeicoes "
        "WHERE date(data_hora,'localtime')=? GROUP BY descricao", [dia])

@st.cache_data(ttl=300)
def _q_alimentos_favoritos():
    try:
        return DB.query(
            "SELECT id,descricao,categoria,calorias,proteinas,carboidratos,gorduras,componentes_json,favorito,vezes_usado,"
            "COALESCE(qtd_referencia,100) as qtd_referencia,COALESCE(unidade_referencia,'g') as unidade_referencia "
            "FROM alimentos_favoritos ORDER BY favorito DESC, vezes_usado DESC"
        )
    except Exception:
        df = DB.query(
            "SELECT id,descricao,categoria,calorias,proteinas,carboidratos,gorduras,componentes_json,favorito,vezes_usado "
            "FROM alimentos_favoritos ORDER BY favorito DESC, vezes_usado DESC"
        )
        df["qtd_referencia"] = 100.0
        df["unidade_referencia"] = "g"
        return df

@st.cache_data(ttl=600)
def _q_peso_historico():
    return DB.query(
        "SELECT date(data) as dt, peso FROM medidas "
        "WHERE peso IS NOT NULL ORDER BY date(data) ASC"
    )


def _fig_peso_evolucao(df_raw: pd.DataFrame) -> go.Figure | None:
    """Gráfico de peso — um ponto/dia, eixo X proporcional ao período com dados."""
    _INICIO_DT = pd.Timestamp("2026-01-26")
    _META_PESO = 83.0

    df = df_raw.copy()
    df["dt"] = pd.to_datetime(df["dt"], errors="coerce").dt.normalize()
    df = df.dropna(subset=["dt", "peso"]).sort_values("dt")
    df = df.groupby("dt", as_index=False)["peso"].last()
    if df.empty:
        return None

    peso_min = float(df["peso"].min())
    peso_max = float(df["peso"].max())
    span_days = max(1, (df["dt"].max() - df["dt"].min()).days)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["dt"], y=df["peso"],
        mode="lines+markers",
        line=dict(color=CYAN, width=2),
        marker=dict(size=6, color=CYAN, line=dict(color=BG, width=1.5)),
        fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
        hovertemplate="<b>%{x|%d/%m/%Y}</b><br>%{y:.1f} kg<extra></extra>",
    ))

    fig.add_hline(
        y=_META_PESO, line_dash="dash", line_color=RED, line_width=1, opacity=0.45,
        annotation_text="Meta 83 kg", annotation_font_color=RED, annotation_font_size=10,
    )

    if df["dt"].min() > _INICIO_DT:
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.01, y=0.98, xanchor="left", yanchor="top",
            text="Início 115,3 kg · 26/01/26",
            showarrow=False,
            font=dict(color=RED, size=9, family=MONO),
            bgcolor="rgba(8,12,20,0.75)", bordercolor=RED, borderwidth=1, borderpad=3,
        )

    _x_pad = pd.Timedelta(days=max(1, min(5, span_days // 8)))
    _y_lo = max(80.0, peso_min - 2.5)
    _y_hi = peso_max + 2.5
    _n_ticks = 6 if span_days <= 45 else (8 if span_days <= 180 else 10)
    _tickvals = pd.date_range(df["dt"].min(), df["dt"].max(), periods=_n_ticks)

    fig.update_layout(
        height=300, margin=dict(t=16, b=28, l=4, r=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            type="date",
            range=[df["dt"].min() - _x_pad, df["dt"].max() + _x_pad],
            tickmode="array",
            tickvals=_tickvals,
            tickformat="%d/%m/%y",
            tickfont=dict(color=GHOST, size=9, family="monospace"),
            gridcolor=BORDER,
            title=None,
        ),
        yaxis=dict(
            range=[_y_lo, _y_hi],
            dtick=2 if (_y_hi - _y_lo) <= 12 else 5,
            tickformat=".0f",
            tickfont=dict(color=GHOST, size=9),
            gridcolor=BORDER,
            title=None,
        ),
        showlegend=False,
    )
    return fig

@st.cache_data(ttl=300)
def _q_medicacao():
    return DB.query(
        "SELECT id, "
        "strftime('%d/%m/%Y', datetime(data_hora,'localtime')) as data_fmt, "
        "date(data_hora,'localtime') as data_iso, "
        "dose_mg FROM medicacao ORDER BY date(data_hora,'localtime') DESC")

@st.cache_data(ttl=600)
def _q_medidas():
    return DB.query(
        "SELECT strftime('%d/%m/%Y',data) as data, "
        "cintura, quadril, peito, braco, coxa FROM medidas "
        "WHERE cintura IS NOT NULL ORDER BY date(data) DESC LIMIT 10")

@st.cache_data(ttl=600)
def _q_biometria():
    return DB.query("""
        SELECT date(data) as data_ord,
               strftime('%d/%m/%Y',data) as data_fmt,
               MAX(peso)            as peso,
               MAX(cintura)         as cintura,
               MAX(abdomen)         as abdomen,
               MAX(peitoral)        as peitoral,
               MAX(quadril)         as quadril,
               MAX(coxa_dir)        as coxa_dir,
               MAX(coxa_esq)        as coxa_esq,
               MAX(panturrilha_dir) as panturrilha_dir,
               MAX(panturrilha_esq) as panturrilha_esq,
               MAX(biceps_dir)      as biceps_dir,
               MAX(biceps_esq)      as biceps_esq
        FROM medidas
        WHERE peso IS NOT NULL OR cintura IS NOT NULL OR coxa_dir IS NOT NULL
        GROUP BY date(data)
        ORDER BY date(data) ASC
    """)

@st.cache_data(ttl=60)
def _q_hevy_hoje(dia: str):
    return DB.query(
        "SELECT titulo, duracao_min, volume_kg FROM hevy_treinos "
        "WHERE date(data_hora, 'localtime') = ? ORDER BY data_hora DESC LIMIT 1",
        [dia],
    )

@st.cache_data(ttl=120)
def _q_hevy_ultimo():
    return DB.query(
        "SELECT titulo, date(data_hora, 'localtime') as data_treino, "
        "duracao_min, volume_kg FROM hevy_treinos ORDER BY data_hora DESC LIMIT 1"
    )

@st.cache_data(ttl=60)
def _q_evacuacoes():
    return DB.query(
        "SELECT id, data_hora, esforco, observacao FROM evacuacoes "
        "ORDER BY data_hora DESC"
    )

# Garante que as tabelas existem — chave versionada força remigração em sessões antigas
if "db_init_v3" not in st.session_state:
    DB.init_tables()
    st.session_state["db_init_v3"] = True

# ── Migrações incrementais — roda 1x por sessão para criar tabelas novas ─────
if "migrations_done" not in st.session_state:
    try:
        DB.execute("""CREATE TABLE IF NOT EXISTS alimentos_favoritos (
            id SERIAL PRIMARY KEY,
            descricao TEXT NOT NULL,
            categoria TEXT DEFAULT 'Lanche',
            calorias REAL DEFAULT 0,
            proteinas REAL DEFAULT 0,
            carboidratos REAL DEFAULT 0,
            gorduras REAL DEFAULT 0,
            componentes_json TEXT,
            favorito INTEGER DEFAULT 0,
            vezes_usado INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(descricao))""")
    except Exception:
        pass
    # Adiciona panturrilha_esq se não existir (migração incremental)
    try:
        DB.execute("ALTER TABLE medidas ADD COLUMN panturrilha_esq REAL")
    except Exception:
        pass  # coluna já existe — ignorar
    # Seed panturrilha_esq = 39 cm no registro mais recente
    try:
        DB.execute(
            "UPDATE medidas SET panturrilha_esq=39.0 "
            "WHERE date(data)=(SELECT MAX(date(data)) FROM medidas) "
            "AND (panturrilha_esq IS NULL OR panturrilha_esq=0)"
        )
    except Exception:
        pass
    # qtd_referencia e unidade_referencia em alimentos_favoritos
    try:
        DB.execute("ALTER TABLE alimentos_favoritos ADD COLUMN qtd_referencia REAL DEFAULT 100")
    except Exception:
        pass
    try:
        DB.execute("ALTER TABLE alimentos_favoritos ADD COLUMN unidade_referencia TEXT DEFAULT 'g'")
    except Exception:
        pass
    st.session_state["migrations_done"] = True

# Tabela evacuacoes — chave própria para garantir criação independente
if "evac_table_ok" not in st.session_state:
    try:
        DB.execute("""CREATE TABLE IF NOT EXISTS evacuacoes (
            id SERIAL PRIMARY KEY,
            data_hora TIMESTAMP NOT NULL,
            observacao TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    except Exception:
        pass
    st.session_state["evac_table_ok"] = True

# Coluna esforco em evacuacoes — chave própria
if "evac_esforco_col_ok" not in st.session_state:
    try:
        DB.execute("ALTER TABLE evacuacoes ADD COLUMN esforco INTEGER DEFAULT 0")
    except Exception:
        pass
    st.session_state["evac_esforco_col_ok"] = True

# ── Seed: histórico de doses Tirzepatida ─────────────────────────────────────
if "med_seeded" not in st.session_state:
    st.session_state["med_seeded"] = True
    _datas_seed = {
        "2026-05-10": 7.0,
        "2026-05-03": 7.0,
    }
    for _ds, _dose_s in _datas_seed.items():
        _ex_med = DB.query(
            "SELECT COUNT(*) as cnt FROM medicacao WHERE date(data_hora,'localtime')=?",
            [_ds]
        )
        if int(_ex_med["cnt"].iloc[0]) == 0:
            DB.execute(
                "INSERT INTO medicacao (data_hora, dose_mg) VALUES (?,?)",
                [f"{_ds} 12:00:00", _dose_s]
            )
    _invalidate_cache(_q_medicacao)

# ── Leitura dos dados com cache ───────────────────────────────────────────────
_dp = _q_peso()
_dp_val = _dp["peso"].iloc[0] if not _dp.empty else None
peso = float(_dp_val) if _dp_val is not None else 93.0

_da    = _q_agua(hoje_sql)
agua_l = float(_da["t"].iloc[0] or 0) / 1000

_dr    = _q_macros(hoje_sql)
cal_h  = float(_dr["cal"].iloc[0]  or 0)
prot_h = float(_dr["prot"].iloc[0] or 0)
carb_h = float(_dr["carb"].iloc[0] or 0)
gord_h = float(_dr["gord"].iloc[0] or 0)

_az       = _amazfit_hoje_df()
passos    = int(_az["passos"].iloc[0])            if not _az.empty else 0
cal_gasta = int(_az["calorias_gastas"].iloc[0])   if not _az.empty else 0
dist_km   = float(_az["distancia_km"].iloc[0])    if not _az.empty else 0.0
sono_tot  = int(_az["sono_total_min"].iloc[0])    if not _az.empty else 0
sono_prof = int(_az["sono_profundo_min"].iloc[0]) if not _az.empty else 0
hrv       = int(_az["hrv_ms"].iloc[0])            if not _az.empty else 0
pai       = int(_az["pai"].iloc[0])               if not _az.empty else 0
corrida_km  = float(_az["corrida_km"].iloc[0])  if not _az.empty and "corrida_km" in _az.columns else 0.0
corrida_cal = int(_az["corrida_cal"].iloc[0])   if not _az.empty and "corrida_cal" in _az.columns else 0

# Derivações — Método Dinâmico
gasto_total_dia   = TMB + cal_gasta                    # TMB + atividade registrada
meta_cal_macros   = META_PROT * 4 + META_CARB * 4 + META_GORD * 9
meta_cal_dinamica = meta_cal_macros                   # meta alinhada aos macros
deficit           = gasto_total_dia - int(cal_h)       # gasto real - consumido
def_cor   = GREEN if deficit > 0 else RED
def_txt   = (f"Déficit {abs(deficit):,}" if deficit > 0
             else f"Superávit {abs(deficit):,}" if deficit < 0
             else "Equilíbrio")
sono_h_fmt = f"{sono_tot // 60}h{sono_tot % 60:02d}"
sono_cor  = GREEN if sono_prof >= META_SONO else RED
# HRV para homem 40 anos: ≥35 Bom, 25-34 Médio, <25 Baixo
hrv_cor   = GREEN if hrv >= 35 else (AMBER if hrv >= 25 else RED)
hrv_txt   = "↑ Bom" if hrv >= 35 else ("→ Médio" if hrv >= 25 else "↓ Baixo")
pai_cor   = GREEN if pai >= META_PAI else (AMBER if pai >= 70 else RED)
pai_arc   = min(251, int(251 * pai / META_PAI)) if META_PAI else 0
restam    = int(deficit)                              # mesmo saldo do balanço calórico
rc_cor    = GREEN if restam > 0 else RED


def _check_goal_celebrations(prot_h: float, agua_l: float, dia: str):
    """Dispara animação quando meta de proteína ou água é atingida pela 1ª vez no dia."""
    prev = st.session_state.setdefault("_goals_prev", {"prot": 0.0, "agua": 0.0, "day": ""})
    if prev.get("day") != dia:
        prev.update({"prot": 0.0, "agua": 0.0, "day": dia})
    celebrate = None
    if prot_h >= META_PROT and prev["prot"] < META_PROT:
        celebrate = "protein"
    elif agua_l >= META_AGUA and prev["agua"] < META_AGUA:
        celebrate = "agua"
    prev["prot"] = prot_h
    prev["agua"] = agua_l
    if celebrate:
        st.session_state["_celebrate_pending"] = celebrate


_check_goal_celebrations(prot_h, agua_l, hoje_sql)

# ════════════════════════════════════════════════════════════════════════════
# CONSTANTES DO PAINEL
# ════════════════════════════════════════════════════════════════════════════
CATEGORIAS = [
    "Café da Manhã", "Lanche da Manhã", "Almoço",
    "Lanche da Tarde", "Jantar", "Lanche da Noite",
    "Pré-Treino", "Pós-Treino",
]

SUPP_REGISTER = [
    ("Whey Isolado Dux 30g",  "Whey Protein Isolado Dux (30g)", "Café da Manhã",  118, 24,   2,   1.5),
    ("Creatina 6g",           "Creatina (6g)",                   "Pós-Treino",       0,  0,   0,   0  ),
    ("Pré-Treino More",       "Pré-Treino More Dux",             "Pré-Treino",       0,  0,   0,   0  ),
    ("Magnésio Quelato",      "Magnésio Quelato Trio Vitha",     "Jantar",           0,  0,   0,   0  ),
    ("Ômega 3 Omegafor",      "Ômega 3 Omegafor Plus",          "Jantar",           9,  0,   0,   1  ),
    ("Vit. D3 + K2 BioVit",  "Vit. D3+K2 BioVit",              "Jantar",           0,  0,   0,   0  ),
]


def _cat_hora():
    """Retorna categoria de refeição pelo horário de Brasília."""
    h = datetime.now(_BR).hour
    if   6  <= h <= 9:  return "Café da Manhã"
    elif 10 <= h <= 11: return "Lanche da Manhã"
    elif 12 <= h <= 14: return "Almoço"
    elif 15 <= h <= 17: return "Lanche da Tarde"
    elif 18 <= h <= 20: return "Jantar"
    else:               return "Lanche da Noite"


def _extrair_json(texto: str):
    """
    Extrai o primeiro objeto ou array JSON de uma resposta do Gemini,
    ignorando texto de explicação ao redor.
    Tenta várias estratégias em ordem de robustez.
    """
    # 1. Remove blocos de código markdown (```json ... ``` ou ``` ... ```)
    texto = re.sub(r"```(?:json)?\s*", "", texto)
    texto = texto.strip()

    # 2. Tenta parse direto
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # 3. Extrai o primeiro { ... } ou [ ... ] completo com contagem de chaves
    for inicio_char, fim_char in [('{', '}'), ('[', ']')]:
        idx = texto.find(inicio_char)
        if idx == -1:
            continue
        profundidade = 0
        in_string = False
        escape = False
        for i, c in enumerate(texto[idx:], start=idx):
            if escape:
                escape = False
                continue
            if c == '\\' and in_string:
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if not in_string:
                if c == inicio_char:
                    profundidade += 1
                elif c == fim_char:
                    profundidade -= 1
                    if profundidade == 0:
                        try:
                            return json.loads(texto[idx:i + 1])
                        except json.JSONDecodeError:
                            break
    raise ValueError(f"Gemini não retornou JSON válido. Resposta recebida:\n{texto[:300]}")


# ── USDA FoodData Central ────────────────────────────────────────────────────
_USDA_BASE = "https://api.nal.usda.gov/fdc/v1/foods/search"

def _buscar_usda(query: str) -> dict | None:
    """
    Busca no USDA FoodData Central.
    Retorna {'kcal','prot','carb','gord','nome_usda'} por 100 g, ou None.
    """
    try:
        api_key = os.getenv("USDA_API_KEY", "DEMO_KEY")
        r = requests.get(
            _USDA_BASE,
            params={
                "query":    query,
                "api_key":  api_key,
                "dataType": "Foundation,SR Legacy",
                "pageSize": 1,
            },
            timeout=6,
        )
        if r.status_code != 200:
            return None
        foods = r.json().get("foods", [])
        if not foods:
            return None
        nut = {n["nutrientName"]: n.get("value", 0)
               for n in foods[0].get("foodNutrients", [])}
        kcal = nut.get("Energy", 0) or nut.get("Energy (Atwater General Factors)", 0)
        return {
            "kcal": round(float(kcal), 1),
            "prot": round(float(nut.get("Protein", 0)), 1),
            "carb": round(float(nut.get("Carbohydrate, by difference", 0)), 1),
            "gord": round(float(nut.get("Total lipid (fat)", 0)), 1),
            "nome_usda": foods[0].get("description", query),
        }
    except Exception:
        return None


def _analisar_texto_macros(descricao: str) -> dict:
    """
    Análise híbrida determinística delegada ao nutri_engine.
    """
    vision = _gemini_model()
    # Calcula os macros de forma determinística
    res = NE.calcular_macros_refeicao(vision, descricao)
    
    # Categoria por horário
    cat = _cat_hora()
    res["categoria"] = cat
    res["critica"] = ""
    
    # Mapeia faixas de kcal para exibição
    kcal_tot = int(round(res["calorias"]))
    res["kcal_min"] = int(kcal_tot * 0.95)
    res["kcal_max"] = int(kcal_tot * 1.05)
    res["fonte"] = "TACO / USDA"
    
    return res


def _analisar_foto_gemini(uploaded_file):
    """Gemini Vision com prompt aprimorado: retorna lista com faixas de confiança."""
    import PIL.Image, io
    foto_bytes = uploaded_file.read()
    img        = PIL.Image.open(io.BytesIO(foto_bytes))
    cat        = _cat_hora()
    agora_txt  = datetime.now(_BR).strftime("%H:%M")
    prompt = (
        f"Você é um nutricionista. Analise esta foto e estime macronutrientes.\n"
        f"Hora: {agora_txt} (Brasilia). Categoria sugerida: {cat}.\n\n"
        "IMPORTANTE: responda SOMENTE com JSON, sem texto antes/depois, sem markdown.\n\n"
        "Para um único prato:\n"
        '{"tipo":"refeicao","categoria":"<cat>","descricao_resumida":"<nome e porcao>",'
        '"calorias":<int>,"kcal_min":<int>,"kcal_max":<int>,'
        '"proteinas":<decimal>,"carboidratos":<decimal>,"gorduras":<decimal>,'
        '"fonte":"IA","restaurante":<true/false>}\n\n'
        "Para multiplos alimentos distintos, retorne lista JSON com o mesmo schema.\n\n"
        "Regras:\n"
        "- kcal_min = estimativa conservadora, kcal_max = generosa (variacao tipica ±15-25%).\n"
        "- Para pratos de restaurante use porcoes reais servidas (nao miniaturize).\n"
        "- Ponto decimal para numeros. Resposta so JSON."
    )
    vision = _gemini_model()
    resp   = vision.generate_content([prompt, img])
    dados  = _extrair_json(resp.text)
    if isinstance(dados, dict):
        dados = [dados]
    return dados


def _card_resultado(item: dict, cor: str = "#00d4ff"):
    """
    Renderiza um card de resultado de análise (foto ou texto IA).
    item: dict com campos como calorias, kcal_min, kcal_max, proteinas,
          carboidratos, gorduras, descricao_resumida, categoria, fonte, detalhes.
    cor: cor de destaque (CYAN para foto, GREEN para texto)
    """
    kcal     = item.get("calorias", 0)
    kcal_min = item.get("kcal_min", int(kcal * 0.85))
    kcal_max = item.get("kcal_max", int(kcal * 1.15))
    prot     = item.get("proteinas", 0)
    carb     = item.get("carboidratos", 0)
    gord     = item.get("gorduras", 0)
    nome     = item.get("descricao_resumida", "")
    cat      = item.get("categoria", "")
    fonte    = item.get("fonte", "IA")
    detalhes = item.get("detalhes", [])

    # Badge de fonte
    fonte_cor = {"USDA": "#00e676", "IA": "#fbbf24", "USDA + IA": "#00d4ff"}.get(fonte, "#fbbf24")
    fonte_bg  = {"USDA": "rgba(0,230,118,0.10)", "IA": "rgba(251,191,36,0.10)",
                 "USDA + IA": "rgba(0,212,255,0.10)"}.get(fonte, "rgba(251,191,36,0.10)")

    # Faixa de kcal
    if kcal_min < kcal_max:
        kcal_range = f"{kcal:,} kcal <span style='color:{MUTED};font-size:11px'>({kcal_min:,}–{kcal_max:,})</span>"
    else:
        kcal_range = f"{kcal:,} kcal"

    html_card = f"""
<div style="background:rgba(0,0,0,0.25);border:1px solid {cor}33;border-left:3px solid {cor};
  border-radius:8px;padding:12px 16px;margin:8px 0">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap">
    <div style="flex:1;min-width:0">
      <div style="font-size:13px;font-weight:700;color:{TEXT};margin-bottom:4px;
        white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{nome}</div>
      <div style="font-size:11px;color:{MUTED}">{cat}</div>
    </div>
    <div style="text-align:right;white-space:nowrap">
      <span style="background:{fonte_bg};border:1px solid {fonte_cor}55;border-radius:4px;
        padding:2px 7px;font-family:{MONO};font-size:9px;font-weight:700;
        letter-spacing:1px;color:{fonte_cor}">{fonte}</span>
    </div>
  </div>
  <div style="margin-top:10px;padding-top:8px;border-top:1px solid #111c2e">
    <div style="font-family:{MONO};font-size:16px;font-weight:700;color:{cor};margin-bottom:6px">
      🔥 {kcal_range}</div>
    <div style="display:flex;gap:16px;flex-wrap:wrap">
      <span style="font-size:11px;color:{MUTED}">🥩 <span style="color:{TEXT}">{prot}g</span> prot</span>
      <span style="font-size:11px;color:{MUTED}">🌾 <span style="color:{TEXT}">{carb}g</span> carb</span>
      <span style="font-size:11px;color:{MUTED}">🫒 <span style="color:{TEXT}">{gord}g</span> gord</span>
    </div>
  </div>"""

    # Detalhamento por componente (se disponível)
    if detalhes:
        html_card += f"""
  <details style="margin-top:10px;cursor:pointer">
    <summary style="font-family:{MONO};font-size:9px;color:{GHOST};letter-spacing:1px;
      text-transform:uppercase;list-style:none;padding:4px 0">▸ detalhes por ingrediente</summary>
    <div style="margin-top:8px;display:flex;flex-direction:column;gap:4px">"""
        for d in detalhes:
            d_fonte = d.get("fonte", "IA")
            d_cor   = "#00e676" if d_fonte == "IA" else "#fbbf24" if d_fonte == "USDA" else "#00d4ff"
            d_kcal  = d.get("kcal", 0)
            d_min   = d.get("kcal_min", d_kcal)
            d_max   = d.get("kcal_max", d_kcal)
            d_range = f"({d_min}–{d_max})" if d_min < d_max else ""
            html_card += f"""
      <div style="background:#070b15;border-radius:4px;padding:5px 10px;
        display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
        <span style="font-size:11px;color:{TEXT}">{d.get('nome','?')} <span style="color:{MUTED}">{d.get('gramas',0)}g</span></span>
        <span style="font-size:11px;font-family:{MONO};color:{d_cor}">{d_kcal} kcal <span style="color:{MUTED};font-size:10px">{d_range}</span></span>
      </div>"""
        html_card += "\n    </div>\n  </details>"

    # Crítica do nutricionista (se disponível)
    critica = item.get("critica", "")
    if critica:
        html_card += f"""
  <div style="margin-top:12px;padding-top:10px;border-top:1px dashed {cor}33">
    <div style="font-family:{MONO};font-size:10px;color:{CYAN};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">🩺 Crítica do Nutricionista de Elite</div>
    <div style="font-size:12px;color:#cbd5e1;line-height:1.5;background:#060a13;padding:10px;border-radius:6px;border:1px solid #1a2035;white-space:pre-wrap">{critica}</div>
  </div>"""

    html_card += "\n</div>"
    st.markdown(html_card, unsafe_allow_html=True)


def _render_fav_row(frow, key_prefix=""):
    """Renderiza uma linha de alimento no painel de favoritos."""
    _fc, _fs, _fa = st.columns([1, 0.08, 0.14])
    fid   = int(frow["id"])
    fdesc = str(frow["descricao"])
    fkcal = int(frow["calorias"] or 0)
    fprot = float(frow["proteinas"] or 0)
    fcarb = float(frow["carboidratos"] or 0)
    fgord = float(frow["gorduras"] or 0)
    fcat  = str(frow["categoria"] or "Lanche")
    fcomp = str(frow["componentes_json"] or "[]")
    fstar = int(frow["favorito"] or 0)
    fused = int(frow["vezes_usado"] or 1)
    with _fc:
        st.markdown(
            f'<div style="padding:5px 0;border-bottom:1px solid {BORDER2}">'
            f'<div style="font-size:12px;color:{TEXT};font-weight:600">{fdesc}</div>'
            f'<div style="display:flex;gap:10px;margin-top:2px">'
            f'<span style="font-family:{MONO};font-size:9px;color:{AMBER}">🔥{fkcal}</span>'
            f'<span style="font-size:9px;color:{GREEN}">P:{fprot:.0f}g</span>'
            f'<span style="font-size:9px;color:#2dd4bf">C:{fcarb:.0f}g</span>'
            f'<span style="font-size:9px;color:{PURPLE}">G:{fgord:.0f}g</span>'
            f'<span style="font-size:9px;color:{GHOST}">×{fused}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with _fs:
        _star_lbl = "⭐" if fstar else "☆"
        if st.button(_star_lbl, key=f"fav_star_{key_prefix}{fid}", use_container_width=True, help="Favoritar"):
            DB.execute("UPDATE alimentos_favoritos SET favorito=? WHERE id=?", [1 - fstar, fid])
            _invalidate_cache(_q_alimentos_favoritos)
            st.rerun()
    with _fa:
        if st.button("➕ Usar", key=f"fav_use_{key_prefix}{fid}", use_container_width=True):
            DB.execute(
                "INSERT INTO refeicoes (categoria,descricao,calorias,proteinas,carboidratos,gorduras,componentes_json) VALUES (?,?,?,?,?,?,?)",
                [_cat_hora(), fdesc, fkcal, fprot, fcarb, fgord, fcomp]
            )
            DB.execute("UPDATE alimentos_favoritos SET vezes_usado=vezes_usado+1 WHERE id=?", [fid])
            _invalidate_cache(_q_alimentos_favoritos, _q_refeicoes, _q_macros, _q_supp_check)
            st.session_state["fav_panel_open"] = False
            _notif(f"{fdesc} adicionado · {fkcal} kcal")
            st.rerun()


def _carrinho_snapshot(carrinho_key: str, ks: str):
    """Calcula totais e componentes a partir do carrinho atual."""
    carrinho = st.session_state.get(carrinho_key, [])
    total_kcal = total_prot = total_carb = total_gord = 0.0
    componentes = []
    descricoes = []
    for i, item in enumerate(carrinho):
        qtd = st.session_state.get(f"cart_qtd_{ks}_{i}", item["qtd_ref"])
        fator = qtd / item["qtd_ref"] if item["qtd_ref"] > 0 else 0
        kcal = round(item["kcal_ref"] * fator, 1)
        prot = round(item["prot_ref"] * fator, 1)
        carb = round(item["carb_ref"] * fator, 1)
        gord = round(item["gord_ref"] * fator, 1)
        total_kcal += kcal
        total_prot += prot
        total_carb += carb
        total_gord += gord
        componentes.append({
            "nome": item["descricao"],
            "gramas": qtd,
            "unidade": item["unidade"],
            "kcal": kcal,
            "prot": prot,
            "carb": carb,
            "gord": gord,
            "banco_id": item.get("id") or 0,
        })
        descricoes.append(item["descricao"])
    return total_kcal, total_prot, total_carb, total_gord, componentes, " + ".join(descricoes)


@st.fragment
def _fragment_ref_busca_carrinho(
    carrinho_key: str = "carrinho_refeicao",
    ks: str = "",
    show_register: bool = True,
    register_cat=None,
):
    """Busca + carrinho nativos Streamlit (funciona dentro do modal)."""
    applied_key = f"ref_busca_applied{ks}"
    busca_key = f"ref_busca_rapida{ks}"
    if applied_key not in st.session_state:
        st.session_state[applied_key] = ""
    if carrinho_key not in st.session_state:
        st.session_state[carrinho_key] = []

    def _sync_busca():
        st.session_state[applied_key] = (st.session_state.get(busca_key) or "").strip()

    _df_banco = _q_alimentos_favoritos()
    carrinho = st.session_state[carrinho_key]

    _bq_in, _bq_btn = st.columns([1, 0.12])
    with _bq_in:
        st.text_input(
            "busca",
            placeholder="🔍 Buscar alimento (Enter)...",
            key=busca_key,
            label_visibility="collapsed",
            on_change=_sync_busca,
        )
    with _bq_btn:
        st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)
        if st.button("🔍", key=f"ref_busca_apply{ks}", use_container_width=True, help="Buscar"):
            _sync_busca()
            st.rerun(scope="fragment")

    _busca_ref = st.session_state.get(applied_key, "")

    if _df_banco.empty:
        st.markdown(
            f'<div style="font-size:11px;color:{GHOST};padding:6px 0">'
            f'Banco vazio. Cadastre alimentos na página <b>Banco de Alimentos</b>.</div>',
            unsafe_allow_html=True,
        )
    elif _busca_ref:
        _hits = (
            _df_banco[_df_banco["descricao"].str.contains(_busca_ref, case=False, na=False)]
            .sort_values(["favorito", "vezes_usado"], ascending=[False, False])
            .head(8)
        )
        if _hits.empty:
            st.markdown(
                f'<div style="font-size:11px;color:{GHOST};padding:4px 8px;'
                f'background:{BG2};border-radius:6px;margin-top:2px">'
                f'Nenhum resultado.</div>',
                unsafe_allow_html=True,
            )
        else:
            for _, _hr in _hits.iterrows():
                _qtd_ref = float(_hr.get("qtd_referencia") or 100)
                _unit_ref = str(_hr.get("unidade_referencia") or "g")
                _already = any(c["id"] == int(_hr["id"]) for c in carrinho)
                _star = "⭐ " if int(_hr.get("favorito") or 0) else ""
                _kcal = int(_hr.get("calorias") or 0)
                _prot = float(_hr.get("proteinas") or 0)
                _carb = float(_hr.get("carboidratos") or 0)
                _gord = float(_hr.get("gorduras") or 0)
                _rc, _rb = st.columns([1, 0.22])
                with _rc:
                    st.markdown(
                        f'<div style="padding:5px 10px;border-bottom:1px solid {BORDER2}">'
                        f'<div style="font-size:12px;color:{TEXT};font-weight:600">'
                        f'{_star}{_hr["descricao"]}</div>'
                        f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};margin-top:2px">'
                        f'Ref: {_qtd_ref:.0f} {_unit_ref}</div>'
                        f'<div style="display:flex;gap:10px;margin-top:1px">'
                        f'<span style="font-family:{MONO};font-size:9px;color:{AMBER}">🔥{_kcal}</span>'
                        f'<span style="font-size:9px;color:{GREEN}">P:{_prot:.0f}g</span>'
                        f'<span style="font-size:9px;color:#2dd4bf">C:{_carb:.0f}g</span>'
                        f'<span style="font-size:9px;color:{PURPLE}">G:{_gord:.0f}g</span>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                with _rb:
                    _lbl = "✓" if _already else "➕"
                    if st.button(
                        _lbl, key=f"ref_add_cart_{_hr['id']}{ks}",
                        use_container_width=True, disabled=_already,
                    ):
                        _append_alimento_carrinho(carrinho, _hr)
                        st.rerun(scope="fragment")
    else:
        _fav_df = _df_banco[_df_banco["favorito"] == 1].head(6)
        if not _fav_df.empty:
            st.markdown(
                f'<div style="font-family:{MONO};font-size:8px;color:{GHOST};'
                f'letter-spacing:1px;margin:6px 0 4px">⭐ FAVORITOS RÁPIDOS</div>',
                unsafe_allow_html=True,
            )
            _fav_cols = st.columns(3)
            for _fi, (_, _fr) in enumerate(_fav_df.iterrows()):
                _already_f = any(c["id"] == int(_fr["id"]) for c in carrinho)
                with _fav_cols[_fi % 3]:
                    _fav_lbl = f"{'✓ ' if _already_f else ''}{str(_fr['descricao'])[:18]}"
                    if st.button(
                        _fav_lbl, key=f"ref_fav_cart_{_fr['id']}{ks}",
                        use_container_width=True, disabled=_already_f,
                        help=f"🔥{int(_fr['calorias'] or 0)} kcal",
                    ):
                        _append_alimento_carrinho(carrinho, _fr)
                        st.rerun(scope="fragment")

    if carrinho:
        st.markdown(
            f'<div style="height:1px;background:{BORDER};margin:10px 0 8px"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;'
            f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px">'
            f'🛒 REFEIÇÃO ATUAL · {len(carrinho)} item(s)</div>',
            unsafe_allow_html=True,
        )

        _ch1, _ch2, _ch3, _ch4 = st.columns([1.8, 0.85, 1.7, 0.18])
        with _ch1:
            st.markdown(
                f'<div style="font-family:{MONO};font-size:8px;color:{GHOST};letter-spacing:1px">ALIMENTO</div>',
                unsafe_allow_html=True,
            )
        with _ch2:
            st.markdown(
                f'<div style="font-family:{MONO};font-size:8px;color:{GHOST};letter-spacing:1px">PORÇÃO</div>',
                unsafe_allow_html=True,
            )
        with _ch3:
            st.markdown(
                f'<div style="font-family:{MONO};font-size:8px;color:{GHOST};letter-spacing:1px">MACROS</div>',
                unsafe_allow_html=True,
            )

        total_kcal = total_prot = total_carb = total_gord = 0.0
        _remover = []

        for i, item in enumerate(carrinho):
            _ci1, _ci2, _ci3, _ci4 = st.columns([1.8, 0.85, 1.7, 0.18])
            with _ci1:
                st.markdown(
                    f'<div style="font-size:11px;color:{TEXT};font-weight:600;padding-top:4px">'
                    f'{item["descricao"]}</div>'
                    f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};margin-top:2px">'
                    f'Ref: {item["qtd_ref"]:.0f} {item["unidade"]}</div>',
                    unsafe_allow_html=True,
                )
            with _ci2:
                _qtd = st.number_input(
                    f"Porção ({item['unidade']})",
                    value=float(st.session_state.get(f"cart_qtd_{ks}_{i}", item["qtd_ref"])),
                    min_value=0.0,
                    step=5.0,
                    format="%.0f",
                    label_visibility="collapsed",
                    key=f"cart_qtd_{ks}_{i}",
                )
            with _ci3:
                _fator = _qtd / item["qtd_ref"] if item["qtd_ref"] > 0 else 0
                _kcal_c = item["kcal_ref"] * _fator
                _prot_c = item["prot_ref"] * _fator
                _carb_c = item["carb_ref"] * _fator
                _gord_c = item["gord_ref"] * _fator
                total_kcal += _kcal_c
                total_prot += _prot_c
                total_carb += _carb_c
                total_gord += _gord_c
                st.markdown(
                    f'<div style="font-size:9px;padding-top:8px;display:flex;gap:8px;flex-wrap:wrap">'
                    f'<span style="font-family:{MONO};color:{AMBER}">🔥{_kcal_c:.0f}</span>'
                    f'<span style="color:{GREEN}">P:{_prot_c:.1f}g</span>'
                    f'<span style="color:#2dd4bf">C:{_carb_c:.1f}g</span>'
                    f'<span style="color:{PURPLE}">G:{_gord_c:.1f}g</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with _ci4:
                if st.button("✕", key=f"rm_cart_{ks}_{i}", help="Remover"):
                    _remover.append(i)

        if _remover:
            for _idx in sorted(_remover, reverse=True):
                carrinho.pop(_idx)
            st.rerun(scope="fragment")

        st.markdown(
            f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:6px;'
            f'padding:8px 12px;margin:8px 0;display:flex;gap:16px;align-items:center;flex-wrap:wrap">'
            f'<span style="font-family:{MONO};font-size:9px;color:{GHOST}">TOTAL</span>'
            f'<span style="font-family:{MONO};font-size:13px;color:{AMBER};font-weight:700">🔥{total_kcal:.0f}</span>'
            f'<span style="font-size:11px;color:{GREEN}">P:{total_prot:.1f}g</span>'
            f'<span style="font-size:11px;color:#2dd4bf">C:{total_carb:.1f}g</span>'
            f'<span style="font-size:11px;color:{PURPLE}">G:{total_gord:.1f}g</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

        if show_register:
            _cs, _cf, _cd = st.columns([2, 1, 1])
            with _cs:
                if st.button("✅ REGISTRAR REFEIÇÃO", key=f"btn_registrar_carrinho{ks}", use_container_width=True):
                    tk, tp, tc, tg, comps, desc = _carrinho_snapshot(carrinho_key, ks)
                    _cat = register_cat or _cat_hora()
                    try:
                        for item in carrinho:
                            if item.get("id"):
                                DB.execute(
                                    "UPDATE alimentos_favoritos SET vezes_usado=vezes_usado+1 WHERE id=?",
                                    [item["id"]],
                                )
                        DB.execute(
                            "INSERT INTO refeicoes (categoria,descricao,calorias,proteinas,carboidratos,gorduras,componentes_json) "
                            "VALUES (?,?,?,?,?,?,?)",
                            [_cat, desc, round(tk, 1), round(tp, 1), round(tc, 1), round(tg, 1), json.dumps(comps)],
                        )
                        st.session_state[carrinho_key] = []
                        _invalidate_cache(_q_refeicoes, _q_macros, _q_supp_check, _q_alimentos_favoritos)
                        _notif(f"Refeição registrada · {tk:.0f} kcal total")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao registrar: {e}")
            with _cf:
                if st.button("⭐ Favorito", key=f"btn_fav_combo{ks}", use_container_width=True, help="Salvar combinação nos favoritos"):
                    tk, tp, tc, tg, comps, desc = _carrinho_snapshot(carrinho_key, ks)
                    if desc:
                        _salvar_combo_favorito(desc, comps, register_cat or _cat_hora(), tk, tp, tc, tg)
                        st.rerun(scope="fragment")
            with _cd:
                if st.button("🗑️ Limpar", key=f"btn_limpar_carrinho{ks}", use_container_width=True):
                    st.session_state[carrinho_key] = []
                    st.rerun(scope="fragment")

    st.markdown(f'<div style="height:1px;background:{BORDER};margin:12px 0 8px"></div>', unsafe_allow_html=True)


@st.dialog("➕ Nova Refeição", width="large")
def _tab_refeicao():
    """Painel de registro — múltiplos itens com cálculo proporcional por porção."""
    if "carrinho_refeicao" not in st.session_state:
        st.session_state["carrinho_refeicao"] = []

    _fragment_ref_busca_carrinho()

    # ── Análise por foto ─────────────────────────────────────────────────────
    foto_up = st.file_uploader(
        "📸 Envie uma foto do prato para análise automática de macros",
        type=["jpg", "jpeg", "png", "webp"],
        key="foto_refeicao",
    )
    if foto_up is not None:
        ci, cb = st.columns([3, 1])
        with ci:
            st.image(foto_up, width=220)
        with cb:
            if st.button("🔍 Analisar", key="btn_foto_analisar", width="stretch"):
                if not _GEMINI_KEY:
                    st.error("❌ Chave GEMINI_API_KEY não configurada.")
                else:
                    with st.spinner("🔍 IA analisando foto..."):
                        try:
                            st.session_state["foto_resultado"] = _analisar_foto_gemini(foto_up)
                        except ValueError as e:
                            st.error(f"❌ A IA não retornou formato válido.\n\n{e}")
                        except Exception as e:
                            st.error(f"❌ Erro ao analisar foto: {e}")

    if "foto_resultado" in st.session_state:
        itens = st.session_state["foto_resultado"]
        for item in itens:
            _card_resultado(item, cor=CYAN)
        cs, cd = st.columns(2)
        with cs:
            if st.button("✅ Salvar tudo", key="salvar_foto", width="stretch"):
                for item in itens:
                    DB.execute(
                        "INSERT INTO refeicoes "
                        "(categoria,descricao,calorias,proteinas,carboidratos,gorduras,componentes_json) "
                        "VALUES (?,?,?,?,?,?,?)",
                        [item.get("categoria", "Lanche"),
                         item.get("descricao_resumida", ""),
                         item.get("calorias", 0), item.get("proteinas", 0),
                         item.get("carboidratos", 0), item.get("gorduras", 0),
                         json.dumps([{
                             "nome": item.get("descricao_resumida", ""),
                             "gramas": 0,
                             "kcal": item.get("calorias", 0),
                             "prot": item.get("proteinas", 0),
                             "carb": item.get("carboidratos", 0),
                             "gord": item.get("gorduras", 0),
                             "fonte": "IA"
                         }])],
                    )
                    _salvar_alimento_db(item.get("descricao_resumida",""), item.get("categoria","Lanche"), item.get("calorias",0), item.get("proteinas",0), item.get("carboidratos",0), item.get("gorduras",0), json.dumps([{"nome":item.get("descricao_resumida",""),"gramas":0,"kcal":item.get("calorias",0),"prot":item.get("proteinas",0),"carb":item.get("carboidratos",0),"gord":item.get("gorduras",0),"fonte":"IA"}]))
                del st.session_state["foto_resultado"]
                _invalidate_cache(_q_refeicoes, _q_macros, _q_supp_check, _q_alimentos_favoritos)
                _notif("Foto registrada com sucesso!")
                st.rerun()
        with cd:
            if st.button("✗ Descartar", key="desc_foto", width="stretch"):
                del st.session_state["foto_resultado"]
                st.rerun(scope="fragment")

    # ── IA por texto ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};'
        f'letter-spacing:1.5px;text-align:center;margin:14px 0 8px">'
        f'── OU DESCREVA E DEIXE A IA CALCULAR ──</div>',
        unsafe_allow_html=True,
    )
    desc_ia = st.text_input(
        "Descrição",
        placeholder="Ex: frango grelhado 200g + arroz integral 150g",
        key="ia_text_input",
        label_visibility="collapsed",
    )
    if st.button("🤖 Analisar macros com IA", key="btn_ia_text", width="stretch"):
        if not _GEMINI_KEY:
            st.error("❌ Chave GEMINI_API_KEY não configurada nos Secrets do Streamlit.")
        elif desc_ia.strip():
            with st.spinner("🤖 IA calculando macros..."):
                try:
                    st.session_state["ia_text_result"] = _analisar_texto_macros(desc_ia.strip())
                except ValueError as e:
                    st.error(f"❌ A IA não retornou um formato válido. Tente reformular a descrição.\n\nDetalhe: {e}")
                except Exception as e:
                    st.error(f"❌ Erro ao chamar a IA: {e}")
        else:
            st.warning("Digite o que comeu antes de analisar.")

    if "ia_text_result" in st.session_state:
        r = st.session_state["ia_text_result"]
        _card_resultado(r, cor=GREEN)
        cs2, cd2 = st.columns(2)
        with cs2:
            if st.button("✅ Salvar", key="salvar_ia_text", width="stretch"):
                DB.execute(
                    "INSERT INTO refeicoes "
                    "(categoria,descricao,calorias,proteinas,carboidratos,gorduras,componentes_json) "
                    "VALUES (?,?,?,?,?,?,?)",
                    [r.get("categoria", "Lanche"), r.get("descricao_resumida", ""),
                     r.get("calorias", 0), r.get("proteinas", 0),
                     r.get("carboidratos", 0), r.get("gorduras", 0),
                     json.dumps(r.get("detalhes", []))],
                )
                _salvar_alimento_db(r.get("descricao_resumida",""), r.get("categoria","Lanche"), r.get("calorias",0), r.get("proteinas",0), r.get("carboidratos",0), r.get("gorduras",0), json.dumps(r.get("detalhes",[])))
                del st.session_state["ia_text_result"]
                _invalidate_cache(_q_refeicoes, _q_macros, _q_supp_check, _q_alimentos_favoritos)
                _notif(f"Refeicao salva · {r.get('calorias',0)} kcal")
                st.rerun()
        with cd2:
            if st.button("✗ Descartar", key="desc_ia_text", width="stretch"):
                del st.session_state["ia_text_result"]
                st.rerun(scope="fragment")

@st.dialog("💊 Suplementação")
def _tab_suplemento():
    st.markdown(
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};letter-spacing:1px;'
        f'margin-bottom:10px">Marque um ou mais e clique em Registrar:</div>',
        unsafe_allow_html=True,
    )
    cols_s = st.columns(3)
    _sel_supps = []
    for i, (label, desc_s, _cat_s, kcal_s, prot_s, carb_s, gord_s) in enumerate(SUPP_REGISTER):
        with cols_s[i % 3]:
            if st.checkbox(label, key=f"chk_supp_{label}"):
                _sel_supps.append((label, desc_s, _cat_s, kcal_s, prot_s, carb_s, gord_s))
    _btn_label = (f"✅ Registrar {len(_sel_supps)} selecionado(s)"
                  if _sel_supps else "Selecione suplementos acima")
    if st.button(_btn_label, key="btn_reg_supps", width="stretch",
                 disabled=not _sel_supps):
        cat_agora = _cat_hora()
        for label, desc_s, _cat_s, kcal_s, prot_s, carb_s, gord_s in _sel_supps:
            DB.execute(
                "INSERT INTO refeicoes "
                "(categoria,descricao,calorias,proteinas,carboidratos,gorduras,componentes_json) "
                "VALUES (?,?,?,?,?,?,?)",
                [cat_agora, desc_s, kcal_s, prot_s, carb_s, gord_s,
                 json.dumps([{
                     "nome": label,
                     "gramas": 0,
                     "kcal": kcal_s,
                     "prot": prot_s,
                     "carb": carb_s,
                     "gord": gord_s,
                     "fonte": "Suplemento"
                 }])],
            )
        for label, *_ in _sel_supps:
            if f"chk_supp_{label}" in st.session_state:
                del st.session_state[f"chk_supp_{label}"]
        nomes = " + ".join(l for l, *_ in _sel_supps)
        _invalidate_cache(_q_refeicoes, _q_macros, _q_supp_check)
        _notif(f"{nomes} registrado(s)!")
        st.rerun()


@st.dialog("💧 Hidratação · Recovery", width="large")
def _tab_agua():
    if st.session_state.pop("_agua_meta_atingida", False):
        st.balloons()

    def _reg_agua(ml: int):
        DB.execute("INSERT INTO agua (quantidade_ml) VALUES (?)", [ml])
        _invalidate_cache(_q_agua)
        nova = agua_l + ml / 1000
        if nova >= META_AGUA and agua_l < META_AGUA:
            st.session_state["_agua_meta_atingida"] = True
            st.session_state["_celebrate_pending"] = "agua"
            _notif(f"Meta de água atingida · {nova:.1f} L", "ok")
        else:
            _notif(f"+{ml} ml · {nova:.1f} / {META_AGUA} L", "info")
        st.rerun()

    _pct_agua = agua_l / META_AGUA if META_AGUA else 0
    _cor_agua_modal = "#a78bfa" if _pct_agua < 0.5 else (CYAN if _pct_agua < 1 else GREEN)
    st.markdown(
        sh_metric(
            _cor_agua_modal, "Hidratação hoje", f"{agua_l:.1f}", "L",
            meta=f"Meta {META_AGUA} L · {int(_pct_agua * 100)}%",
            extra_html=pbar(_pct_agua, _cor_agua_modal),
            variant="compact",
        ),
        unsafe_allow_html=True,
    )

    _col_agua, _col_rec = st.columns([1.15, 0.85], gap="medium")
    with _col_agua:
        st.markdown('<div class="sh-modal-zone">', unsafe_allow_html=True)
        st.markdown(
            '<div class="sh-modal-zone__title">💧 Registrar água</div>'
            '<div class="sh-modal-zone__sub">Toque no atalho ou informe outro volume</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sh-agua-chips">', unsafe_allow_html=True)
        _w1, _w2, _w3, _w4 = st.columns(4)
        for _col, _ml, _key in [
            (_w1, 200, "agua_200"), (_w2, 500, "agua_500"),
            (_w3, 750, "agua_750"), (_w4, 1000, "agua_1000"),
        ]:
            with _col:
                if st.button(f"+{_ml} ml", key=_key, type="secondary", use_container_width=True):
                    _reg_agua(_ml)
        st.markdown("</div>", unsafe_allow_html=True)
        with st.form("form_agua_custom_modal", clear_on_submit=True):
            _ml_in = st.number_input("Outro volume (ml)", min_value=50, max_value=2000, value=300, step=50)
            if st.form_submit_button("Registrar volume", type="primary", use_container_width=True):
                _reg_agua(int(_ml_in))
        st.markdown("</div>", unsafe_allow_html=True)

    with _col_rec:
        st.markdown('<div class="sh-modal-zone">', unsafe_allow_html=True)
        st.markdown(
            '<div class="sh-modal-zone__title">💓 Recovery (Amazfit)</div>'
            '<div class="sh-modal-zone__sub">Atualize HRV e PAI do dia</div>',
            unsafe_allow_html=True,
        )
        _hrv_c = GREEN if hrv >= 35 else (AMBER if hrv >= 25 else RED)
        _r1, _r2 = st.columns(2)
        with _r1:
            st.markdown(
                sh_metric(_hrv_c, "HRV", f"{hrv}", "ms", meta=hrv_txt, variant="compact"),
                unsafe_allow_html=True,
            )
        with _r2:
            st.markdown(
                sh_metric(pai_cor, "PAI", f"{pai}", "", meta=f"meta {META_PAI}", variant="compact"),
                unsafe_allow_html=True,
            )
        with st.form("form_hrv_pai_modal"):
            _h1, _h2 = st.columns(2)
            with _h1:
                hrv_in = st.number_input("HRV (ms)", min_value=0, max_value=200, value=int(hrv) if hrv else 0, step=1)
            with _h2:
                pai_in = st.number_input("PAI", min_value=0, max_value=300, value=int(pai) if pai else 0, step=1)
            if st.form_submit_button("Salvar recovery", type="primary", use_container_width=True):
                DB.execute(
                    "INSERT INTO amazfit_dados (data_hora,passos,calorias_gastas,distancia_km,"
                    "sono_total_min,sono_profundo_min,hrv_ms,pai) VALUES (?,0,0,0,0,0,0,0) "
                    "ON CONFLICT(data_hora) DO NOTHING",
                    [f"{hoje_sql} 00:00:00"],
                )
                DB.execute(
                    "UPDATE amazfit_dados SET hrv_ms=?, pai=? WHERE data_hora=?",
                    [hrv_in, pai_in, f"{hoje_sql} 00:00:00"],
                )
                hrv_status = "Bom" if hrv_in >= 35 else ("Médio" if hrv_in >= 25 else "Baixo")
                _invalidate_cache(_q_amazfit)
                _notif(f"HRV {hrv_in} ms ({hrv_status}) · PAI {pai_in}", "info")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


@st.dialog("📏 Nova medida corporal", width="large")
def _dialog_bio_nova():
    st.markdown(sh_section("Biometria", "Registrar medidas corporais"), unsafe_allow_html=True)

    _bio_ultimo = _q_biometria()
    _bio_ult = _bio_ultimo.iloc[-1] if not _bio_ultimo.empty else None

    def _bio_default(col, fallback=0.0):
        if _bio_ult is None:
            return fallback
        v = _bio_ult.get(col, None)
        return float(v) if v is not None and not pd.isna(v) else fallback

    with st.form("form_bio_nova_modal", clear_on_submit=True):
        _bio_data = st.date_input(
            "Data da medição",
            value=(datetime.now(_BR).date() - timedelta(days=1)),
            key="bio_data_modal",
            format="DD/MM/YYYY",
        )
        st.markdown(
            f'<div class="sh-modal-zone__sub" style="margin:12px 0 8px">Composição corporal</div>',
            unsafe_allow_html=True,
        )
        _bc1, _bc2, _bc3 = st.columns(3)
        with _bc1:
            _b_peso = st.number_input("Peso (kg)", min_value=0.0, max_value=300.0, value=_bio_default("peso", 0.0), step=0.1, format="%.1f")
            _b_cintura = st.number_input("Cintura (cm)", min_value=0.0, max_value=200.0, value=_bio_default("cintura", 0.0), step=0.1, format="%.1f")
            _b_abdomen = st.number_input("Abdômen (cm)", min_value=0.0, max_value=200.0, value=_bio_default("abdomen", 0.0), step=0.1, format="%.1f")
        with _bc2:
            _b_peitoral = st.number_input("Peitoral (cm)", min_value=0.0, max_value=200.0, value=_bio_default("peitoral", 0.0), step=0.1, format="%.1f")
            _b_quadril = st.number_input("Quadril (cm)", min_value=0.0, max_value=200.0, value=_bio_default("quadril", 0.0), step=0.1, format="%.1f")
            _b_coxa_d = st.number_input("Coxa dir. (cm)", min_value=0.0, max_value=150.0, value=_bio_default("coxa_dir", 0.0), step=0.1, format="%.1f")
            _b_coxa_e = st.number_input("Coxa esq. (cm)", min_value=0.0, max_value=150.0, value=_bio_default("coxa_esq", 0.0), step=0.1, format="%.1f")
        with _bc3:
            _b_pant_d = st.number_input("Pant. dir. (cm)", min_value=0.0, max_value=100.0, value=_bio_default("panturrilha_dir", 0.0), step=0.1, format="%.1f")
            _b_pant_e = st.number_input("Pant. esq. (cm)", min_value=0.0, max_value=100.0, value=_bio_default("panturrilha_esq", 0.0), step=0.1, format="%.1f")
            _b_bic_d = st.number_input("Bíceps dir. (cm)", min_value=0.0, max_value=80.0, value=_bio_default("biceps_dir", 0.0), step=0.1, format="%.1f")
            _b_bic_e = st.number_input("Bíceps esq. (cm)", min_value=0.0, max_value=80.0, value=_bio_default("biceps_esq", 0.0), step=0.1, format="%.1f")

        if st.form_submit_button("Salvar medidas", type="primary", use_container_width=True):
            _bio_data_sql = str(_bio_data)

            def _nz(v):
                return float(v) if v and float(v) > 0 else None

            _ex = DB.query("SELECT id FROM medidas WHERE date(data)=?", [_bio_data_sql])
            if _ex.empty:
                DB.execute(
                    "INSERT INTO medidas (data,peso,cintura,abdomen,peitoral,quadril,"
                    "coxa_dir,coxa_esq,panturrilha_dir,panturrilha_esq,biceps_dir,biceps_esq) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [_bio_data_sql, _nz(_b_peso), _nz(_b_cintura), _nz(_b_abdomen),
                     _nz(_b_peitoral), _nz(_b_quadril), _nz(_b_coxa_d), _nz(_b_coxa_e),
                     _nz(_b_pant_d), _nz(_b_pant_e), _nz(_b_bic_d), _nz(_b_bic_e)],
                )
            else:
                DB.execute(
                    "UPDATE medidas SET peso=?,cintura=?,abdomen=?,peitoral=?,quadril=?,"
                    "coxa_dir=?,coxa_esq=?,panturrilha_dir=?,panturrilha_esq=?,biceps_dir=?,biceps_esq=? "
                    "WHERE date(data)=?",
                    [_nz(_b_peso), _nz(_b_cintura), _nz(_b_abdomen),
                     _nz(_b_peitoral), _nz(_b_quadril), _nz(_b_coxa_d), _nz(_b_coxa_e),
                     _nz(_b_pant_d), _nz(_b_pant_e), _nz(_b_bic_d), _nz(_b_bic_e), _bio_data_sql],
                )
            _invalidate_cache(_q_peso, _q_peso_historico, _q_medidas, _q_biometria)
            _notif(f"Medidas de {_bio_data.strftime('%d/%m/%Y')} salvas ✓")
            st.rerun()


@st.dialog("✏️ Editar medida corporal", width="large")
def _dialog_bio_editar():
    st.markdown(sh_section("Biometria", "Editar medidas existentes"), unsafe_allow_html=True)

    df_bio = _q_biometria()
    if df_bio.empty:
        st.warning("Nenhuma medida cadastrada.")
        return

    df_bio = df_bio.sort_values("data_ord", ascending=False)
    _datas_bio = [(row["data_fmt"], row["data_ord"]) for _, row in df_bio.iterrows()]
    pre_ord = st.session_state.pop("bio_edit_preselect", None)
    default_ix = next((i for i, d in enumerate(_datas_bio) if d[1] == pre_ord), 0)

    _sel_fmt = st.selectbox(
        "Selecionar data",
        [d[0] for d in _datas_bio],
        index=default_ix,
        key="bio_edit_sel_modal",
    )
    _sel_ord = next(d[1] for d in _datas_bio if d[0] == _sel_fmt)
    _er = df_bio[df_bio["data_ord"] == _sel_ord].iloc[0]

    def _ev(col, fallback=0.0):
        v = _er.get(col, None)
        return float(v) if v is not None and not pd.isna(v) else fallback

    with st.form("form_bio_edit_modal", clear_on_submit=False):
        _ec1, _ec2, _ec3 = st.columns(3)
        with _ec1:
            _e_peso = st.number_input("Peso (kg)", min_value=0.0, max_value=300.0, value=_ev("peso"), step=0.1, format="%.1f")
            _e_cintura = st.number_input("Cintura (cm)", min_value=0.0, max_value=200.0, value=_ev("cintura"), step=0.1, format="%.1f")
            _e_abdomen = st.number_input("Abdômen (cm)", min_value=0.0, max_value=200.0, value=_ev("abdomen"), step=0.1, format="%.1f")
        with _ec2:
            _e_peit = st.number_input("Peitoral (cm)", min_value=0.0, max_value=200.0, value=_ev("peitoral"), step=0.1, format="%.1f")
            _e_quad = st.number_input("Quadril (cm)", min_value=0.0, max_value=200.0, value=_ev("quadril"), step=0.1, format="%.1f")
            _e_coxa_d = st.number_input("Coxa dir. (cm)", min_value=0.0, max_value=150.0, value=_ev("coxa_dir"), step=0.1, format="%.1f")
            _e_coxa_e = st.number_input("Coxa esq. (cm)", min_value=0.0, max_value=150.0, value=_ev("coxa_esq"), step=0.1, format="%.1f")
        with _ec3:
            _e_pant_d = st.number_input("Pant. dir. (cm)", min_value=0.0, max_value=100.0, value=_ev("panturrilha_dir"), step=0.1, format="%.1f")
            _e_pant_e = st.number_input("Pant. esq. (cm)", min_value=0.0, max_value=100.0, value=_ev("panturrilha_esq"), step=0.1, format="%.1f")
            _e_bic_d = st.number_input("Bíceps dir. (cm)", min_value=0.0, max_value=80.0, value=_ev("biceps_dir"), step=0.1, format="%.1f")
            _e_bic_e = st.number_input("Bíceps esq. (cm)", min_value=0.0, max_value=80.0, value=_ev("biceps_esq"), step=0.1, format="%.1f")
        _ef_sv, _ef_dl = st.columns([2, 1])
        with _ef_sv:
            _edit_salvar = st.form_submit_button("✓ Salvar alterações", use_container_width=True, type="primary")
        with _ef_dl:
            _edit_del = st.form_submit_button("🗑 Excluir", use_container_width=True)

    if _edit_salvar:
        def _nz(v):
            return float(v) if v and float(v) > 0 else None

        DB.execute(
            "UPDATE medidas SET peso=?,cintura=?,abdomen=?,peitoral=?,quadril=?,"
            "coxa_dir=?,coxa_esq=?,panturrilha_dir=?,panturrilha_esq=?,biceps_dir=?,biceps_esq=? "
            "WHERE date(data)=?",
            [_nz(_e_peso), _nz(_e_cintura), _nz(_e_abdomen), _nz(_e_peit), _nz(_e_quad),
             _nz(_e_coxa_d), _nz(_e_coxa_e), _nz(_e_pant_d), _nz(_e_pant_e), _nz(_e_bic_d), _nz(_e_bic_e),
             _sel_ord],
        )
        _invalidate_cache(_q_peso, _q_peso_historico, _q_medidas, _q_biometria)
        _notif(f"Medidas de {_sel_fmt} atualizadas ✓")
        st.rerun()

    if _edit_del:
        st.session_state["bio_del_confirm_modal"] = _sel_ord
        st.rerun()

    if st.session_state.get("bio_del_confirm_modal") == _sel_ord:
        st.warning(f"Confirmar exclusão do registro de {_sel_fmt}?")
        _dc1, _dc2 = st.columns(2)
        with _dc1:
            if st.button("✓ Confirmar exclusão", key="bio_del_conf_modal", use_container_width=True):
                DB.execute("DELETE FROM medidas WHERE date(data)=?", [_sel_ord])
                _invalidate_cache(_q_peso, _q_peso_historico, _q_medidas, _q_biometria)
                st.session_state.pop("bio_del_confirm_modal", None)
                _notif(f"Registro de {_sel_fmt} excluído ✓")
                st.rerun()
        with _dc2:
            if st.button("✗ Cancelar", key="bio_del_cancel_modal", use_container_width=True):
                st.session_state.pop("bio_del_confirm_modal", None)
                st.rerun()


def _med_doses_list(df_med):
    """Lista normalizada de doses Tirzepatida."""
    doses = []
    if df_med is None or df_med.empty:
        return doses
    for _, row in df_med.iterrows():
        d = float(row["dose_mg"])
        if d > 100:
            d /= 1000
        doses.append({
            "iso": str(row["data_iso"])[:10],
            "fmt": str(row["data_fmt"]),
            "dose": d,
            "id": int(row["id"]),
        })
    return doses


@st.dialog("💊 Nova dose · Tirzepatida")
def _dialog_med_nova():
    from datetime import date as _date

    st.markdown(sh_section("Medicação", "Registrar dose semanal"), unsafe_allow_html=True)
    with st.form("form_med_nova_modal", clear_on_submit=True):
        _mn1, _mn2 = st.columns(2)
        with _mn1:
            nova_data = st.date_input(
                "Data da aplicação",
                value=_date.fromisoformat(hoje_sql),
                key="mdata_nova_modal",
                format="DD/MM/YYYY",
            )
        with _mn2:
            nova_dose = st.number_input(
                "Dose (mg)",
                value=5.0,
                min_value=0.5,
                max_value=25.0,
                step=0.5,
                format="%.1f",
                key="mdose_nova_modal",
            )
        if st.form_submit_button("Registrar dose", type="primary", use_container_width=True):
            DB.execute(
                "INSERT INTO medicacao (data_hora, dose_mg) VALUES (?,?)",
                [f"{nova_data} 12:00:00", nova_dose],
            )
            _invalidate_cache(_q_medicacao)
            _notif(f"Tirzepatida {nova_dose:.1f} mg registrada")
            st.rerun()


@st.dialog("✏️ Editar dose · Tirzepatida", width="large")
def _dialog_med_editar():
    from datetime import date as _date, datetime as _datetime

    df_med = _q_medicacao()
    doses = _med_doses_list(df_med)
    if not doses:
        st.warning("Nenhuma dose registrada.")
        return

    pre_id = st.session_state.pop("med_edit_preselect_id", None)
    if pre_id:
        match = [d for d in doses if d["id"] == int(pre_id)]
        item = match[0] if match else doses[0]
    else:
        opts = [f'{d["fmt"]} · {d["dose"]:.1f} mg' for d in doses]
        ix = st.selectbox("Dose", range(len(opts)), format_func=lambda i: opts[i], key="med_edit_sel_modal")
        item = doses[ix]

    mid = item["id"]
    dose = item["dose"]
    data_iso = item["iso"]
    data_fmt = item["fmt"]

    st.markdown(
        f'<div class="sh-metric sh-metric--compact" style="min-height:auto;margin-bottom:12px">'
        f'<div class="sh-metric__accent" style="background:{PURPLE}"></div>'
        f'<div class="sh-metric__label">Selecionada</div>'
        f'<div class="sh-metric__value" style="font-size:1.1rem">{data_fmt}</div>'
        f'<div class="sh-metric__meta">{dose:.1f} mg · Tirzepatida</div></div>',
        unsafe_allow_html=True,
    )

    try:
        val_data = _datetime.strptime(data_iso, "%Y-%m-%d").date()
    except Exception:
        val_data = _date.fromisoformat(hoje_sql)

    with st.form(f"form_med_edit_modal_{mid}", border=False):
        _mc1, _mc2 = st.columns(2)
        with _mc1:
            nova_data = st.date_input("Data", value=val_data, key=f"mdata_modal_{mid}", format="DD/MM/YYYY")
        with _mc2:
            nova_dose = st.number_input(
                "Dose (mg)", value=dose, min_value=0.5, max_value=25.0, step=0.5, format="%.1f",
                key=f"mdose_modal_{mid}",
            )
        ba, bd = st.columns([2, 1])
        with ba:
            salvar = st.form_submit_button("✓ Salvar alterações", use_container_width=True, type="primary")
        with bd:
            deletar = st.form_submit_button("🗑 Excluir", use_container_width=True)
        if salvar:
            DB.execute(
                "UPDATE medicacao SET data_hora=?, dose_mg=? WHERE id=?",
                [f"{nova_data} 12:00:00", nova_dose, mid],
            )
            _invalidate_cache(_q_medicacao)
            _notif(f"Dose atualizada: {nova_dose:.1f} mg")
            st.rerun()
        if deletar:
            st.session_state["med_del_confirm_modal"] = mid
            st.rerun()

    if st.session_state.get("med_del_confirm_modal") == mid:
        st.warning(f"Confirmar exclusão da dose de {data_fmt}?")
        _dc1, _dc2 = st.columns(2)
        with _dc1:
            if st.button("✓ Confirmar exclusão", key=f"med_del_ok_{mid}", use_container_width=True):
                DB.execute("DELETE FROM medicacao WHERE id=?", [mid])
                _invalidate_cache(_q_medicacao)
                st.session_state.pop("med_del_confirm_modal", None)
                _notif("Registro removido", "err")
                st.rerun()
        with _dc2:
            if st.button("✗ Cancelar", key=f"med_del_cancel_{mid}", use_container_width=True):
                st.session_state.pop("med_del_confirm_modal", None)
                st.rerun()


def _render_medicacao_section():
    """Seção Tirzepatida — card + timeline; registro/edição via modal."""
    from datetime import date as _date, datetime as _datetime, timedelta as _td

    df_med = _q_medicacao()
    doses = _med_doses_list(df_med)

    dose_atual = doses[0]["dose"] if doses else 0.0
    n_doses = len(doses)
    try:
        dt_inicio = _datetime.strptime(doses[-1]["iso"], "%Y-%m-%d").date() if doses else _date.fromisoformat(hoje_sql)
        semanas = (_date.fromisoformat(hoje_sql) - dt_inicio).days // 7
    except Exception:
        semanas = 0
    try:
        dt_ult = _datetime.strptime(doses[0]["iso"], "%Y-%m-%d").date() if doses else _date.fromisoformat(hoje_sql)
        proxima = (dt_ult + _td(days=7)).strftime("%d/%m")
    except Exception:
        proxima = "—"

    st.markdown(
        f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;'
        f'border-top:3px solid {PURPLE};padding:14px 16px;margin-bottom:8px">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">'
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<span style="font-size:16px">💊</span>'
        f'<div>'
        f'<div style="font-family:{MONO};font-size:10px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{PURPLE}">Tirzepatida</div>'
        f'<div style="font-size:11px;color:{MUTED};margin-top:1px">Protocolo farmacológico · injetável semanal</div>'
        f'</div></div></div>'
        f'<div style="height:1px;background:{BORDER2};margin-bottom:12px"></div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">'
        f'<div style="background:{BG3};border:1px solid rgba(0,230,118,0.15);border-radius:8px;padding:10px 12px;text-align:center">'
        f'<div style="font-family:{MONO};font-size:8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{MUTED};margin-bottom:4px">Dose Atual</div>'
        f'<div style="font-size:20px;font-weight:800;color:{GREEN};letter-spacing:-0.5px">{dose_atual:.1f}</div>'
        f'<div style="font-size:10px;color:{MUTED};margin-top:1px">mg / semana</div></div>'
        f'<div style="background:{BG3};border:1px solid {BORDER};border-radius:8px;padding:10px 12px;text-align:center">'
        f'<div style="font-family:{MONO};font-size:8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{MUTED};margin-bottom:4px">Aplicações</div>'
        f'<div style="font-size:20px;font-weight:800;color:{PURPLE};letter-spacing:-0.5px">{n_doses}</div>'
        f'<div style="font-size:10px;color:{MUTED};margin-top:1px">doses totais</div></div>'
        f'<div style="background:{BG3};border:1px solid {BORDER};border-radius:8px;padding:10px 12px;text-align:center">'
        f'<div style="font-family:{MONO};font-size:8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{MUTED};margin-bottom:4px">Semanas</div>'
        f'<div style="font-size:20px;font-weight:800;color:{AMBER};letter-spacing:-0.5px">{semanas}</div>'
        f'<div style="font-size:10px;color:{MUTED};margin-top:1px">em protocolo</div></div>'
        f'<div style="background:{BG3};border:1px solid {BORDER};border-radius:8px;padding:10px 12px;text-align:center">'
        f'<div style="font-family:{MONO};font-size:8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:{MUTED};margin-bottom:4px">Próxima</div>'
        f'<div style="font-size:20px;font-weight:800;color:{TEXT};letter-spacing:-0.5px">{proxima}</div>'
        f'<div style="font-size:10px;color:{MUTED};margin-top:1px">estimativa</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    _btn_nova, _btn_edit = st.columns(2)
    with _btn_nova:
        if st.button("➕ Nova dose", key="btn_med_nova", use_container_width=True, type="primary"):
            _dialog_med_nova()
    with _btn_edit:
        if st.button("✏️ Editar dose", key="btn_med_edit", use_container_width=True, disabled=not doses):
            _dialog_med_editar()

    st.markdown(
        f'<div class="sh-med-hdr" style="font-family:{MONO};font-size:9px;font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;color:{MUTED};margin:12px 0 6px">Histórico de doses</div>',
        unsafe_allow_html=True,
    )

    if not doses:
        st.markdown(f'<p style="color:{GHOST};font-size:12px">Sem registros.</p>', unsafe_allow_html=True)
        return

    for i, item in enumerate(doses):
        mid = item["id"]
        dose = item["dose"]
        data_fmt = item["fmt"]
        is_atual = i == 0
        _mc, _me = st.columns([1, 0.06])
        with _mc:
            if is_atual:
                st.markdown(
                    f'<div class="sh-med-row" style="display:flex;align-items:center;gap:8px;'
                    f'padding:4px 8px;border-radius:5px;margin-bottom:1px;'
                    f'background:rgba(0,230,118,0.05);border:1px solid rgba(0,230,118,0.15)">'
                    f'<span style="width:6px;height:6px;border-radius:50%;background:{GREEN};'
                    f'box-shadow:0 0 5px rgba(0,230,118,0.5);flex-shrink:0"></span>'
                    f'<span style="font-family:{MONO};font-size:9px;color:{MUTED};flex:1">{data_fmt}</span>'
                    f'<span style="font-size:13px;font-weight:800;color:{GREEN};letter-spacing:-0.3px">{dose:.1f} mg</span>'
                    f'<span style="font-family:{MONO};font-size:7px;font-weight:700;color:{GREEN};'
                    f'background:rgba(0,230,118,0.12);border:1px solid rgba(0,230,118,0.25);'
                    f'padding:1px 5px;border-radius:8px;letter-spacing:1px">ATUAL</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="sh-med-row" style="display:flex;align-items:center;gap:8px;'
                    f'padding:2px 8px;margin-bottom:0;opacity:0.5">'
                    f'<span style="width:3px;height:3px;border-radius:50%;background:{GHOST};flex-shrink:0"></span>'
                    f'<span style="font-family:{MONO};font-size:9px;color:{GHOST};flex:1">{data_fmt}</span>'
                    f'<span style="font-size:11px;font-weight:600;color:{MUTED}">{dose:.1f} mg</span></div>',
                    unsafe_allow_html=True,
                )
        with _me:
            if st.button("✏", key=f"tog_med_{mid}", use_container_width=True, help="Editar dose"):
                st.session_state["med_edit_preselect_id"] = mid
                _dialog_med_editar()


def _form_editar_refeicao(row, form_key_suffix=""):
    """Formulário unificado de edição de refeição (modal) com carrinho de alimentos."""
    rid = int(row["id"])
    cat = str(row["cat"])
    food = str(row["descricao"])
    kcal_v = int(row["calorias"] or 0)
    prot_v = float(row["proteinas"] or 0)
    carb_v = float(row["carboidratos"] or 0)
    gord_v = float(row["gorduras"] or 0)
    hora = str(row["hora"])[:5]
    comp_json = row.get("componentes_json")

    sk = f"{rid}{form_key_suffix}"
    carrinho_key = f"carrinho_edit_{sk}"
    ks = f"_ed{sk}"
    cat_key = f"edit_cat_{sk}"
    desc_key = f"edit_desc_{sk}"

    init_key = f"edit_carrinho_init_{sk}"
    if st.session_state.get(init_key) != rid:
        st.session_state[init_key] = rid
        st.session_state[carrinho_key] = _componentes_to_carrinho(
            comp_json, food, kcal_v, prot_v, carb_v, gord_v
        )
        st.session_state.pop(cat_key, None)
        st.session_state.pop(desc_key, None)

    st.markdown(
        f'<div class="sh-metric sh-metric--compact" style="min-height:auto;margin-bottom:12px">'
        f'<div class="sh-metric__accent" style="background:{CYAN}"></div>'
        f'<div class="sh-metric__label">Selecionada · {hora}</div>'
        f'<div class="sh-metric__value" style="font-size:1.1rem">{food[:56]}</div>'
        f'<div class="sh-metric__meta">🔥 {kcal_v} kcal · P {prot_v:.0f}g</div></div>',
        unsafe_allow_html=True,
    )

    _cat_ix = CATEGORIAS.index(cat) if cat in CATEGORIAS else 0
    if cat_key not in st.session_state:
        st.session_state[cat_key] = _cat_ix
    if desc_key not in st.session_state:
        st.session_state[desc_key] = food

    _ec, _ed = st.columns([1, 2])
    with _ec:
        nova_cat = st.selectbox("Categoria", CATEGORIAS, key=cat_key)
    with _ed:
        nova_desc = st.text_input("Descrição", key=desc_key)

    st.markdown(
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};letter-spacing:1px;margin:8px 0 4px">'
        f'ADICIONAR / EDITAR ALIMENTOS</div>',
        unsafe_allow_html=True,
    )
    _fragment_ref_busca_carrinho(carrinho_key=carrinho_key, ks=ks, show_register=False)

    carrinho = st.session_state.get(carrinho_key, [])
    with st.expander("Ajustar macros manualmente", expanded=not carrinho):
        _em1, _em2, _em3, _em4 = st.columns(4)
        with _em1:
            nova_kcal = st.number_input(
                "Kcal", value=float(kcal_v), min_value=0.0, step=1.0, format="%.0f", key=f"edit_kcal_{sk}"
            )
        with _em2:
            nova_prot = st.number_input(
                "Prot g", value=prot_v, min_value=0.0, step=0.5, format="%.1f", key=f"edit_prot_{sk}"
            )
        with _em3:
            nova_carb = st.number_input(
                "Carb g", value=carb_v, min_value=0.0, step=0.5, format="%.1f", key=f"edit_carb_{sk}"
            )
        with _em4:
            nova_gord = st.number_input(
                "Gord g", value=gord_v, min_value=0.0, step=0.5, format="%.1f", key=f"edit_gord_{sk}"
            )

    ba, bf, bd = st.columns([2, 1, 1])
    with ba:
        if st.button("✓ Salvar alterações", key=f"edit_save_{sk}", use_container_width=True, type="primary"):
            try:
                if carrinho:
                    tk, tp, tc, tg, comps, desc_auto = _carrinho_snapshot(carrinho_key, ks)
                    desc_final = (nova_desc.strip() or desc_auto or food)
                    DB.execute(
                        "UPDATE refeicoes SET categoria=?, descricao=?, calorias=?, "
                        "proteinas=?, carboidratos=?, gorduras=?, componentes_json=? WHERE id=?",
                        [nova_cat, desc_final, round(tk, 1), round(tp, 1), round(tc, 1), round(tg, 1),
                         json.dumps(comps), rid],
                    )
                    for item in carrinho:
                        if item.get("id"):
                            DB.execute(
                                "UPDATE alimentos_favoritos SET vezes_usado=vezes_usado+1 WHERE id=?",
                                [item["id"]],
                            )
                    kcal_msg = int(tk)
                else:
                    DB.execute(
                        "UPDATE refeicoes SET categoria=?, descricao=?, calorias=?, "
                        "proteinas=?, carboidratos=?, gorduras=? WHERE id=?",
                        [nova_cat, nova_desc.strip() or food, nova_kcal, nova_prot, nova_carb, nova_gord, rid],
                    )
                    kcal_msg = int(nova_kcal)
                _invalidate_cache(_q_refeicoes, _q_macros, _q_supp_check, _q_alimentos_favoritos)
                _notif(f"Refeição atualizada · {kcal_msg} kcal")
                st.session_state.pop(init_key, None)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
    with bf:
        if st.button("⭐ Favorito", key=f"edit_fav_{sk}", use_container_width=True):
            if carrinho:
                tk, tp, tc, tg, comps, desc_auto = _carrinho_snapshot(carrinho_key, ks)
                _salvar_combo_favorito(
                    nova_desc.strip() or desc_auto or food, comps, nova_cat, tk, tp, tc, tg
                )
                st.rerun(scope="fragment")
            else:
                st.warning("Adicione alimentos ao carrinho para salvar como favorito.")
    with bd:
        if st.button("🗑 Excluir", key=f"edit_del_{sk}", use_container_width=True):
            try:
                DB.execute("DELETE FROM refeicoes WHERE id=?", [rid])
                _invalidate_cache(_q_refeicoes, _q_macros, _q_supp_check, _q_alimentos_favoritos)
                st.session_state.pop(init_key, None)
                st.session_state.pop(carrinho_key, None)
                _notif("Refeição removida", "err")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")


@st.dialog("✏️ Editar refeições", width="large")
def _tab_editar():
    """Edição unificada via modal — sidebar ou botão ✏ nos cards."""
    pre_id = st.session_state.pop("edit_ref_preselect_id", None)
    if pre_id:
        df_one = DB.query(
            "SELECT id, COALESCE(categoria,'Lanche') as cat, descricao, calorias, proteinas, "
            "carboidratos, gorduras, componentes_json, "
            "time(datetime(data_hora,'localtime')) as hora "
            "FROM refeicoes WHERE id=?",
            [int(pre_id)],
        )
        if df_one.empty:
            st.warning("Refeição não encontrada.")
            return
        _form_editar_refeicao(df_one.iloc[0], "_card")
        return

    df_edit = DB.query(
        "SELECT id, COALESCE(categoria,'Lanche') as cat, descricao, calorias, proteinas, "
        "carboidratos, gorduras, componentes_json, "
        "time(datetime(data_hora,'localtime')) as hora "
        "FROM refeicoes WHERE date(data_hora,'localtime')=? "
        "ORDER BY data_hora DESC LIMIT 20",
        [hoje_sql],
    )
    if df_edit.empty:
        st.markdown(
            f'<div style="text-align:center;padding:28px 16px;border:1px dashed {BORDER};border-radius:10px">'
            f'<div style="font-size:28px;margin-bottom:8px">🍽️</div>'
            f'<div style="font-size:13px;color:{MUTED}">Nenhuma refeição registrada hoje.</div></div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(sh_section("Hoje", f"{len(df_edit)} registro(s)"), unsafe_allow_html=True)

    _opts = []
    for _, row in df_edit.iterrows():
        _kcal = int(row["calorias"] or 0)
        _opts.append(f'{str(row["hora"])[:5]} · {str(row["descricao"])[:40]} · {_kcal} kcal')
    _sel_ix = st.selectbox(
        "Refeição",
        range(len(_opts)),
        format_func=lambda i: _opts[i],
        key="edit_ref_sel_modal",
        label_visibility="collapsed",
    )
    _form_editar_refeicao(df_edit.iloc[_sel_ix], "_list")


# ── Auto-sync Zepp (desligado no Streamlit Cloud — sync via bot 07h ou botão 🔄) ─
_zepp_status_txt = "sincronizado"
_zepp_status_cor = GREEN
if "zepp_auto_synced" not in st.session_state:
    st.session_state["zepp_auto_synced"] = True
    if _runtime_allows_zepp_autosync():
        try:
            _sync_result = _zepp_sync_dashboard(hoje_sql)
            if "passos" in _sync_result or "sincronizado" in _sync_result.lower():
                _invalidate_cache(_q_amazfit)
                _zepp_status_txt = "sincronizado"
                _zepp_status_cor = GREEN
            elif "Erro" in _sync_result or "falha" in _sync_result.lower():
                _zepp_status_txt = "erro de sync"
                _zepp_status_cor = RED
            else:
                _zepp_status_txt = "sem dados novos"
                _zepp_status_cor = AMBER
        except Exception:
            _zepp_status_txt = "sem dados novos"
            _zepp_status_cor = AMBER
    else:
        _zepp_status_txt = "sync manual"
        _zepp_status_cor = MUTED

# ── Auto-sync Hevy na primeira abertura da sessão ────────────────────────────
_hevy_status_txt = "sincronizado"
_hevy_status_cor = GREEN
if "hevy_auto_synced" not in st.session_state:
    st.session_state["hevy_auto_synced"] = True
    _h_sync_result = _hevy_sync_dashboard()
    if "sincronizado" in _h_sync_result.lower() or "atualizados" in _h_sync_result.lower():
        _invalidate_cache(_q_hevy_hoje, _q_hevy_ultimo)
    elif "não configurada" in _h_sync_result.lower():
        _hevy_status_txt = "não configurado"
        _hevy_status_cor = MUTED
    elif "Erro" in _h_sync_result:
        _hevy_status_txt = "erro de sync"
        _hevy_status_cor = RED
    else:
        _hevy_status_txt = "sem dados novos"
        _hevy_status_cor = AMBER

# ════════════════════════════════════════════════════════════════════════════
# APP HEADER (identidade + sync — métricas ficam na página Visão)
# ════════════════════════════════════════════════════════════════════════════
_h_brand, _h_actions = st.columns([2.4, 1])
with _h_brand:
    st.markdown(
        f'<div class="sh-app-header sh-topbar" style="border:none;padding-bottom:0;margin-bottom:0">'
        f'<div class="sh-app-header__eyebrow">SYS.HEALTH</div>'
        f'<div class="sh-app-header__title">Leandro R.</div>'
        f'<div class="sh-app-header__meta">{dia_sem} · {hoje_pt} · {hora_now}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with _h_actions:
    st.markdown('<div class="sh-header-actions">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sh-header-status sh-topbar-right">'
        f'<span style="color:{_zepp_status_cor}"><span class="sh-status-dot" style="background:{_zepp_status_cor}"></span>'
        f'Amazfit · {_zepp_status_txt}</span>'
        f'<span style="color:{GHOST};margin:0 6px">·</span>'
        f'<span style="color:{_hevy_status_cor}"><span class="sh-status-dot" style="background:{_hevy_status_cor}"></span>'
        f'Hevy · {_hevy_status_txt}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sh-header-sync">', unsafe_allow_html=True)
    _hb1, _hb2 = st.columns(2, gap="small")
    with _hb1:
        if st.button("⌚ Zepp", key="btn_zepp_sync_top", type="secondary", use_container_width=True):
            with st.spinner("Zepp…"):
                _sync_result = _zepp_sync_dashboard(hoje_sql)
            _invalidate_cache(_q_amazfit)
            _notif(_sync_result, "ok" if "passos" in _sync_result or "sincronizado" in _sync_result.lower() else "info")
            st.rerun()
    with _hb2:
        if st.button("💪 Hevy", key="btn_hevy_sync_top", type="secondary", use_container_width=True):
            with st.spinner("Hevy…"):
                _h_sync_result = _hevy_sync_dashboard()
            _invalidate_cache(_q_hevy_hoje, _q_hevy_ultimo)
            _notif(_h_sync_result, "ok" if "sincronizado" in _h_sync_result.lower() or "atualizados" in _h_sync_result.lower() else "info")
            st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)
st.markdown(f'<div style="border-bottom:1px solid {BORDER};margin-bottom:12px;padding-bottom:4px"></div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sh-mobile-hint">'
    f'<span style="color:{CYAN};font-size:14px">☰</span>'
    f'<span>Use o menu lateral para navegar e registrar refeições · deslize tabelas horizontalmente</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Notificação animada pendente (roda UMA vez por ação) ─────────────────────
_render_notif_pendente()
_celebrate = st.session_state.pop("_celebrate_pending", None)
if _celebrate:
    _render_goal_celebration(_celebrate)

from app_sidebar import render_app_sidebar, render_mobile_quick_bar

# ── Sidebar — navegação + status + atalhos ────────────────────────────────────
def _render_dashboard_sidebar():
    render_app_sidebar(
        active_page="dashboard",
        kpi_data={
            "cal_h": cal_h,
            "prot_h": prot_h,
            "agua_l": agua_l,
            "def_cor": def_cor,
            "def_txt": def_txt,
            "passos": passos,
            "sono_h_fmt": sono_h_fmt,
            "hrv": hrv,
            "hrv_cor": hrv_cor,
            "pai": pai,
            "pai_cor": pai_cor,
        },
        quick_actions={
            "refeicao": _tab_refeicao,
            "editar": _tab_editar,
            "agua": _tab_agua,
            "supp": _tab_suplemento,
        },
    )

_render_dashboard_sidebar()

_scroll_sec = st.session_state.pop("_scroll_to", None)
if _scroll_sec:
    st.html(f"""
<script>
setTimeout(function() {{
  var t = document.querySelector("#{_scroll_sec}");
  if (t) t.scrollIntoView({{ behavior: "smooth", block: "start" }});
}}, 350);
</script>
""")

_open_dlg = st.session_state.pop("open_dialog", None)
if _open_dlg == "refeicao":
    _tab_refeicao()
elif _open_dlg == "editar":
    _tab_editar()
elif _open_dlg == "agua":
    _tab_agua()
elif _open_dlg == "supp":
    _tab_suplemento()

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — HOJE (tabs: Nutrição · Wearable · Agenda)
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div id="sec-hoje"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Hoje", f"Resumo · {hoje_pt}"), unsafe_allow_html=True)

_gcal_ok = _gcal_configured()

# Sub-seções de Hoje (Nutrição · Wearable · Agenda) = tabs Streamlit — sem anchor sec-* próprio
tab_nutri, tab_wear, tab_agenda = st.tabs(["🥗 Nutrição", "⌚ Wearable", "📅 Agenda"])

with tab_nutri:
    pct_cal = cal_h / meta_cal_dinamica if meta_cal_dinamica > 0 else 0
    pct_agua = agua_l / META_AGUA
    cor_agua = "#a78bfa" if pct_agua < 0.50 else ("#00d4ff" if pct_agua < 1.0 else "#00e676")
    badge_agua = "⚠️ Desidratado" if pct_agua < 0.50 else ("⚡ Em progresso" if pct_agua < 1.0 else "✓ Hidratado")
    st.markdown('<div class="sh-nutri-metrics">', unsafe_allow_html=True)
    h_a, h_b, h_c, h_d = st.columns(4)
    with h_a:
        st.markdown(sh_metric(
            def_cor, "Balanço calórico", f"{int(cal_h):,}", "kcal",
            meta=f"{int(pct_cal * 100)}% da meta · saldo {restam:+,} kcal · {def_txt}",
            extra_html=pbar(pct_cal, GREEN), variant="compact",
        ), unsafe_allow_html=True)
    with h_b:
        st.markdown(sh_metric(CYAN, "Peso", f"{peso:.1f}", "kg", meta=f"meta 83 kg · faltam {peso - 83:.1f}", variant="compact"), unsafe_allow_html=True)
    with h_c:
        st.markdown(sh_metric(RED, "Proteína", f"{int(prot_h)}", "g", meta=f"{int(prot_h / META_PROT * 100) if META_PROT else 0}%", extra_html=pbar(prot_h / META_PROT, RED) if META_PROT else "", variant="compact"), unsafe_allow_html=True)
    with h_d:
        st.markdown(sh_metric(cor_agua, "Hidratação", f"{agua_l:.1f}", "L", meta=badge_agua, extra_html=pbar(pct_agua, cor_agua), variant="compact"), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with tab_wear:
    st.markdown(sh_section("Amazfit Bip 6", "Atividade · recovery"), unsafe_allow_html=True)

    a_col1, a_col2, a_col3, a_col4 = st.columns(4)
    with a_col1:
        pct_p = passos / META_PASS if META_PASS else 0
        st.markdown(sh_metric(
            CYAN, "👟 Passos", f"{passos:,}", "",
            meta=f"{int(pct_p * 100)}% da meta {META_PASS:,}",
            extra_html=pbar(pct_p, CYAN),
        ), unsafe_allow_html=True)
    with a_col2:
        st.markdown(sh_metric(
            GREEN, "🔥 Gasto total", f"{gasto_total_dia:,}", "kcal",
            meta=f"{def_txt} · atividade {cal_gasta:,} kcal",
        ), unsafe_allow_html=True)
    with a_col3:
        st.markdown(sh_metric(
            CYAN, "📍 Distância", f"{dist_km:.1f}", "km",
            meta="distância registrada hoje",
        ), unsafe_allow_html=True)
    with a_col4:
        pct_sp = sono_prof / META_SONO if META_SONO else 0
        st.markdown(sh_metric(
            PURPLE, "🌙 Sono", sono_h_fmt, "",
            meta=f"profundo {sono_prof} min · meta {META_SONO} min",
            extra_html=pbar(pct_sp, sono_cor),
        ), unsafe_allow_html=True)

    if not _az.empty and "data_hora" in _az.columns:
        try:
            _az_ts_fmt = pd.to_datetime(str(_az["data_hora"].iloc[0])).strftime("%d/%m %H:%M")
        except Exception:
            _az_ts_fmt = str(_az["data_hora"].iloc[0])[:16]
        st.markdown(
            f'<p style="color:{MUTED};font-size:10px;text-align:right;font-family:{MONO};'
            f'margin:4px 0 10px;letter-spacing:0.5px">⟳ sincronizado {_az_ts_fmt}</p>',
            unsafe_allow_html=True,
        )

    with st.expander("Recovery · PAI · corrida · musculação", expanded=False):
        a_col5, a_col6, a_col7, a_col8 = st.columns(4)
        with a_col5:
            pct_hrv = min(1.0, max(0, (hrv - 20) / 60)) if hrv else 0
            st.markdown(sh_metric(
                GREEN, "💓 HRV", str(hrv), "ms",
                meta=hrv_txt,
                extra_html=pbar(pct_hrv, hrv_cor),
            ), unsafe_allow_html=True)
        with a_col6:
            svg_pai = (
                f'<div style="position:relative;width:56px;height:56px;margin:0 auto">'
                f'<svg width="56" height="56" viewBox="0 0 60 60" style="transform:rotate(-90deg)">'
                f'<circle cx="30" cy="30" r="24" fill="none" stroke="{BORDER}" stroke-width="6"/>'
                f'<circle cx="30" cy="30" r="24" fill="none" stroke="{pai_cor}" stroke-width="6" '
                f'stroke-dasharray="{pai_arc} 251" stroke-linecap="round"/></svg>'
                f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
                f'font-size:15px;font-weight:800;color:{pai_cor}">{pai}</div></div>'
            )
            st.markdown(sh_metric(
                AMBER, "⚡ PAI", str(pai), "",
                meta=f"meta ≥ {META_PAI}",
                extra_html=svg_pai,
            ), unsafe_allow_html=True)
        with a_col7:
            _corr_meta = (
                f"{corrida_cal} kcal gastas" if corrida_cal > 0
                else "sem corrida registrada"
            )
            st.markdown(sh_metric(
                CYAN, "🏃 Corrida", f"{corrida_km:.2f}", "km",
                meta=_corr_meta,
            ), unsafe_allow_html=True)
        with a_col8:
            df_hevy_hoje = _q_hevy_hoje(hoje_sql)
            hevy_unit = ""
            if not df_hevy_hoje.empty:
                h_title = df_hevy_hoje["titulo"].iloc[0]
                h_dur = int(df_hevy_hoje["duracao_min"].iloc[0])
                h_vol = float(df_hevy_hoje["volume_kg"].iloc[0])
                hevy_val = str(h_dur)
                hevy_unit = "min"
                hevy_meta = f"{h_title} · vol {h_vol:,.0f} kg"
            else:
                df_hevy_last = _q_hevy_ultimo()
                if not df_hevy_last.empty:
                    l_title = df_hevy_last["titulo"].iloc[0]
                    l_date = df_hevy_last["data_treino"].iloc[0]
                    try:
                        l_date_fmt = datetime.strptime(l_date, "%Y-%m-%d").strftime("%d/%m")
                    except Exception:
                        l_date_fmt = l_date
                    hevy_val = "Descanso"
                    hevy_meta = f"último treino {l_date_fmt} · {l_title}"
                else:
                    hevy_val = "—"
                    hevy_meta = "nenhum treino sincronizado"
            st.markdown(sh_metric(
                GREEN, "💪 Hevy", hevy_val, hevy_unit,
                meta=hevy_meta,
            ), unsafe_allow_html=True)

with tab_agenda:
    st.markdown(sh_section("Agenda", f"Hoje · {hoje_pt}"), unsafe_allow_html=True)

    if not _gcal_ok:
        st.markdown(
            f'<div style="background:{BG2};border:1px dashed {BORDER};border-radius:10px;'
            f'padding:20px 24px;display:flex;align-items:center;gap:16px">'
            f'<span style="font-size:28px">📅</span>'
            f'<div>'
            f'<div style="font-family:{MONO};font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{MUTED};margin-bottom:4px">Google Calendar não configurado</div>'
            f'<div style="font-size:12px;color:{GHOST}">Rode <code style="background:#0a1020;padding:1px 6px;'
            f'border-radius:3px;color:{CYAN}">python get_gcal_token.py</code> localmente e adicione '
            f'<code style="background:#0a1020;padding:1px 6px;border-radius:3px;color:{CYAN}">'
            f'GOOGLE_CLIENT_ID</code>, <code style="background:#0a1020;padding:1px 6px;'
            f'border-radius:3px;color:{CYAN}">GOOGLE_CLIENT_SECRET</code> e '
            f'<code style="background:#0a1020;padding:1px 6px;border-radius:3px;color:{CYAN}">'
            f'GOOGLE_REFRESH_TOKEN</code> nos Secrets do Streamlit.</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    else:
        _ag_hdr, _ag_btn = st.columns([3, 1])
        with _ag_hdr:
            st.caption("Google Calendar · eventos de hoje")
        with _ag_btn:
            _gcal_refresh = st.button(
                "🔄 Atualizar",
                key="btn_gcal_refresh",
                use_container_width=True,
                help="Buscar eventos do Google Calendar agora",
            )
        if _gcal_refresh:
            _get_gcal_eventos.clear()
            with st.spinner("Atualizando agenda…"):
                _eventos = _get_gcal_eventos(hoje_sql)
            _n_ev = len(_eventos)
            if _n_ev and str(_eventos[0].get("titulo", "")).startswith("Erro ao carregar"):
                _notif(str(_eventos[0]["titulo"])[:120], "err")
            else:
                _notif(f"Agenda atualizada · {_n_ev} evento(s)", "ok" if _n_ev else "info")
            st.rerun()
        else:
            _eventos = _get_gcal_eventos(hoje_sql)

        _gcal_erro = bool(
            _eventos and str(_eventos[0].get("titulo", "")).startswith("Erro ao carregar")
        )
        if _gcal_erro:
            st.error(_eventos[0]["titulo"])
        elif not _eventos:
            st.markdown(
                f'<div style="text-align:center;padding:24px;border:1px dashed {BORDER};'
                f'border-radius:8px">'
                f'<div style="font-size:24px;margin-bottom:6px">✅</div>'
                f'<div style="font-family:{MONO};font-size:10px;font-weight:700;letter-spacing:1.5px;'
                f'text-transform:uppercase;color:{MUTED}">Sem eventos para hoje</div>'
                f'<div style="font-size:11px;color:{GHOST};margin-top:4px">Dia livre na agenda</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif _eventos:
            _TREINO_KW = ["treino", "série", "serie", "musculação", "musculacao",
                          "cardio", "hiit", "zona 2", "zone 2", "corrida", "gym",
                          "academia", "workout", "cross", "funcional"]
            _cols_ag = st.columns(min(len(_eventos), 4))
            for _i, _ev in enumerate(_eventos):
                _titulo_low = _ev["titulo"].lower()
                _is_treino  = any(kw in _titulo_low for kw in _TREINO_KW)
                _ev_cor     = GREEN if _is_treino else _ev["cor"]
                _ev_bg      = "rgba(0,230,118,0.05)" if _is_treino else f"{BG2}"
                _ev_border  = f"rgba(0,230,118,0.3)" if _is_treino else f"{BORDER}"
                _horario_html = ""
                if _ev["dia_todo"]:
                    _horario_html = (
                        f'<span style="font-family:{MONO};font-size:11px;font-weight:700;'
                        f'color:{MUTED};background:{BORDER};border-radius:3px;'
                        f'padding:2px 8px">DIA TODO</span>'
                    )
                elif _ev["inicio"]:
                    _horario_html = (
                        f'<span style="font-family:{MONO};font-size:15px;font-weight:700;'
                        f'color:{_ev_cor}">{_ev["inicio"]}</span>'
                        + (f'<span style="font-size:13px;color:{GHOST}"> → {_ev["fim"]}</span>'
                           if _ev["fim"] else "")
                    )
                _local_html = ""
                if _ev["local"]:
                    _local_html = (
                        f'<div style="font-size:12px;color:{GHOST};margin-top:7px;'
                        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                        f'📍 {_ev["local"]}</div>'
                    )
                _treino_badge = (
                    f'<span style="font-family:{MONO};font-size:9px;font-weight:700;'
                    f'background:rgba(0,230,118,0.12);color:{GREEN};'
                    f'border:1px solid rgba(0,230,118,0.3);padding:1px 6px;'
                    f'border-radius:3px;letter-spacing:1px;margin-left:6px">TREINO</span>'
                    if _is_treino else ""
                )
                _card_ag = (
                    f'<div style="background:{_ev_bg};border:1px solid {_ev_border};'
                    f'border-top:3px solid {_ev_cor};border-radius:8px;'
                    f'padding:18px 18px 16px;height:100%">'
                    f'<div style="margin-bottom:10px">{_horario_html}</div>'
                    f'<div style="font-size:15px;font-weight:700;color:{TEXT};'
                    f'line-height:1.35;margin-bottom:6px">{_ev["titulo"]}</div>'
                    f'<div style="margin-top:4px">{_treino_badge}</div>'
                    f'{_local_html}</div>'
                )
                with _cols_ag[_i % 4]:
                    st.markdown(_card_ag, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 4 — EVOLUÇÃO
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div id="sec-evolucao"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Evolução", "Peso histórico e macros"), unsafe_allow_html=True)

c1, c2 = st.columns([2, 1])

with c1:
    df_p = _q_peso_historico()
    _fig_p = _fig_peso_evolucao(df_p) if not df_p.empty else None
    if _fig_p is not None:
        st.plotly_chart(_fig_p, width="stretch", config={"displayModeBar": False})

with c2:
    def mrow_dinamico(nome, val, meta):
        if not meta: return ""
        pct = val / meta
        # Proteínas: quanto mais próximo da meta, melhor (laranja -> verde)
        # Carboidratos e Gorduras: se passarem de 100%, alertar com vermelho/laranja
        if nome == "Proteínas":
            cor = "#fbbf24" if pct < 0.70 else ("#00e676" if pct <= 1.10 else "#00d4ff")
        elif nome == "Carboidratos":
            cor = "#00d4ff" if pct <= 1.0 else ("#fbbf24" if pct <= 1.15 else "#ff6b6b")
        else:  # Gorduras
            cor = "#a78bfa" if pct <= 1.0 else ("#fbbf24" if pct <= 1.10 else "#ff6b6b")
            
        p = min(100, int(pct * 100))
        return (
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
            f'<span style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1px;'
            f'text-transform:uppercase;color:{MUTED}">{nome}</span>'
            f'<span style="font-size:10px;color:{GHOST}">'
            f'<b style="color:{TEXT}">{int(val)}</b> / {int(meta)} g ({int(pct * 100)}%)</span>'
            f'</div>'
            f'<div style="background:{BORDER};border-radius:3px;height:5px;overflow:hidden">'
            f'<div style="width:{p}%;height:5px;border-radius:3px;background:{cor}"></div>'
            f'</div></div>'
        )
    st.markdown(
        panel(
            ptitl("Macronutrientes") +
            mrow_dinamico("Proteínas",    prot_h, META_PROT)  +
            mrow_dinamico("Carboidratos", carb_h, META_CARB)   +
            mrow_dinamico("Gorduras",     gord_h, META_GORD) +
            f'<div style="border-top:1px solid {BORDER2};padding-top:10px;display:flex;'
            f'justify-content:space-between;align-items:center">'
            f'<span style="font-family:{MONO};font-size:9px;text-transform:uppercase;'
            f'letter-spacing:1.5px;color:{GHOST}">Saldo calórico</span>'
            f'<span style="font-size:17px;font-weight:800;color:{rc_cor}">{restam:+,} kcal</span>'
            f'</div>',
            extra="height:210px;display:flex;flex-direction:column;justify-content:space-between"
        ),
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO — REGISTROS
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div id="sec-registros"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Registros", "Refeições e suplementação"), unsafe_allow_html=True)


BADGE_STYLE = {
    "Café da Manhã":   f"background:rgba(245,158,11,0.10);color:#f59e0b;border:1px solid rgba(245,158,11,0.28)",
    "Lanche da Manhã": f"background:rgba(129,140,248,0.08);color:#818cf8;border:1px solid rgba(129,140,248,0.22)",
    "Almoço":          f"background:rgba(0,230,118,0.08);color:{GREEN};border:1px solid rgba(0,230,118,0.2)",
    "Lanche da Tarde": f"background:rgba(129,140,248,0.08);color:#818cf8;border:1px solid rgba(129,140,248,0.22)",
    "Jantar":          f"background:rgba(255,107,107,0.08);color:{RED};border:1px solid rgba(255,107,107,0.2)",
    "Lanche da Noite": f"background:rgba(167,139,250,0.08);color:{PURPLE};border:1px solid rgba(167,139,250,0.2)",
    "Pré-Treino":      f"background:rgba(0,212,255,0.08);color:{CYAN};border:1px solid rgba(0,212,255,0.22)",
    "Pós-Treino":      f"background:rgba(0,230,118,0.08);color:{GREEN};border:1px solid rgba(0,230,118,0.2)",
    "Lanche":          f"background:rgba(74,85,104,0.15);color:{MUTED};border:1px solid {BORDER}",
}

_CAT_COLOR_REF = {
    "Café da Manhã":   "#f59e0b",
    "Lanche da Manhã": "#818cf8",
    "Almoço":          GREEN,
    "Lanche da Tarde": "#818cf8",
    "Jantar":          RED,
    "Lanche da Noite": PURPLE,
    "Lanche":          MUTED,
}
_CAT_ICON_REF = {
    "Café da Manhã":   "☕",
    "Lanche da Manhã": "🍎",
    "Almoço":          "🍽️",
    "Lanche da Tarde": "🥪",
    "Jantar":          "🌙",
    "Lanche da Noite": "🌜",
    "Lanche":          "🥤",
}


# Definição dos suplementos — keywords cruzam com refeições do dia
SUPLEMENTOS = [
    {"label": "Whey Isolado",          "meta": 2,    "cor": GREEN,  "marca": "Dux Nutrition",  "keywords": ["whey"]},
    {"label": "Creatina",              "meta": 1,    "cor": CYAN,   "marca": "Creapure Dux",   "keywords": ["creatina"]},
    {"label": "Pré-Treino",            "meta": 1,    "cor": RED,    "marca": "More Treino Dux","keywords": ["pré-treino", "pre-treino", "more treino"]},
    {"label": "Magnésio Quelato Trio", "meta": 1,    "cor": PURPLE, "marca": "Vitha",          "keywords": ["magnésio", "magnesio", "quelato", "vitha"]},
    {"label": "Ômega 3",               "meta": 1,    "cor": AMBER,  "marca": "Omegafor Plus",  "keywords": ["ômega", "omega", "omegafor"]},
    {"label": "Vit. D3 + K2",          "meta": 1,    "cor": AMBER,  "marca": "Bio D3+K2",      "keywords": ["d3", "k2", "vitamina d", "biovit"]},
]


def _checar_supp(supp_registrados: dict, keywords: list) -> int:
    total = 0
    for desc, qtd in supp_registrados.items():
        if any(kw.lower() in desc for kw in keywords):
            total += qtd
    return total


def _render_col_refeicoes():
    """Coluna de refeições (executada dentro de _fragment_registros_dia)."""
    from datetime import date as _date

    # ── Seletor de data: label + input na mesma linha compacta ────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:2px">'
        f'<span style="font-family:{MONO};font-size:9px;font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;color:{CYAN}">📅 Visualizar dia</span>'
        f'<span style="font-size:10px;color:{GHOST}">— toque para consultar outro dia</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    _dc_inp, _ = st.columns([0.42, 0.58])
    with _dc_inp:
        _hist_sel = st.date_input(
            "data",
            value=_date.fromisoformat(hoje_sql),
            max_value=_date.fromisoformat(hoje_sql),
            key="ref_hist_date",
            label_visibility="collapsed",
            format="DD/MM/YYYY",
        )
    _hist_sql   = _hist_sel.strftime("%Y-%m-%d")
    _is_hoje    = _hist_sql == hoje_sql
    _titulo_ref = "Refeições de hoje" if _is_hoje else f"Refeições de {_hist_sel.strftime('%d/%m')}"

    df_ref_hoje = _q_refeicoes(_hist_sql)

    # Título da seção
    st.markdown(
        f'<div style="font-family:{MONO};font-size:11px;font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;color:{TEXT};'
        f'margin-bottom:8px">{_titulo_ref}</div>',
        unsafe_allow_html=True,
    )

    if df_ref_hoje.empty:
        st.markdown(
            f'<div style="text-align:center;padding:28px 16px;border:1px dashed {BORDER};'
            f'border-radius:8px;margin-top:8px">'
            f'<div style="font-size:28px;margin-bottom:8px">🍽️</div>'
            f'<div style="font-family:{MONO};font-size:10px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{MUTED}">Nenhuma refeição registrada</div>'
            f'<div style="font-size:12px;color:{GHOST};margin-top:4px">'
            f'Abra ➕ Refeição nas ações rápidas da sidebar para registrar</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        for _, r in df_ref_hoje.iterrows():
            rid    = int(r["id"])
            hora   = str(r["hora"])[:5]
            cat    = str(r["cat"])
            food   = str(r["alimento"])
            kcal_v = int(r["kcal"])   if r["kcal"] else 0
            prot_v = float(r["prot"]) if r["prot"] else 0.0
            carb_v = float(r["carb"]) if r["carb"] else 0.0
            gord_v = float(r["gord"]) if r["gord"] else 0.0
            icon   = _CAT_ICON_REF.get(cat, "🍴")
            cor    = _CAT_COLOR_REF.get(cat, MUTED)
            bsty   = BADGE_STYLE.get(cat, BADGE_STYLE["Lanche"])

            # ── Card colorido (sempre visível) ────────────────────────────────
            has_macros = kcal_v or prot_v or carb_v or gord_v
            macro_row  = ""
            if has_macros:
                macro_row = (
                    f'<div style="display:flex;gap:14px;flex-wrap:wrap;'
                    f'margin-top:7px;padding-top:7px;border-top:1px solid {cor}22">'
                    f'<span style="font-family:{MONO};font-size:11px;font-weight:700;color:{AMBER}">🔥 {kcal_v}</span>'
                    f'<span style="font-size:11px;color:{MUTED}">🥩<b style="color:{GREEN}"> {prot_v:.0f}g</b></span>'
                    f'<span style="font-size:11px;color:{MUTED}">🌾<b style="color:#2dd4bf"> {carb_v:.0f}g</b></span>'
                    f'<span style="font-size:11px;color:{MUTED}">🫒<b style="color:{PURPLE}"> {gord_v:.0f}g</b></span>'
                    f'</div>'
                )
            comp_json = r.get("componentes_json")
            detalhes_list = []
            if comp_json:
                try:
                    detalhes_list = json.loads(comp_json)
                except Exception:
                    pass
            
            details_html = ""
            if detalhes_list:
                details_html += f"""
<details style="margin-top:6px;cursor:pointer">
  <summary style="font-family:{MONO};font-size:9px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;list-style:none;padding:2px 0">▸ Ver ingredientes</summary>
  <div style="margin-top:4px;display:flex;flex-direction:column;gap:3px;padding-left:10px">"""
                for d in detalhes_list:
                    d_fonte = d.get("fonte", "LOCAL")
                    d_cor = {"LOCAL": GREEN, "USDA": CYAN, "IA (100g)": AMBER}.get(d_fonte, AMBER)
                    _dp = float(d.get("prot", 0) or 0)
                    _dc = float(d.get("carb", 0) or 0)
                    _dg = float(d.get("gord", 0) or 0)
                    _macros_ing = ""
                    if _dp or _dc or _dg:
                        _macros_ing = (
                            f'<span style="font-family:{MONO};font-size:11px;color:{GREEN};margin-left:8px">Prot. {_dp:.0f}g</span>'
                            f'<span style="font-family:{MONO};font-size:11px;color:#2dd4bf;margin-left:8px">Carb. {_dc:.0f}g</span>'
                            f'<span style="font-family:{MONO};font-size:11px;color:{PURPLE};margin-left:8px">Gord. {_dg:.0f}g</span>'
                        )
                    details_html += f"""
    <div style="background:#070b15;border-radius:4px;padding:4px 8px;display:flex;justify-content:space-between;align-items:center;border:1px solid {cor}11">
      <span style="font-size:11px;color:{TEXT}">{d.get('nome','?')} <span style="color:{MUTED};font-size:10px">{d.get('gramas',0)}g</span></span>
      <span style="display:flex;align-items:center;flex-wrap:wrap;gap:0;justify-content:flex-end">
        <span style="font-family:{MONO};font-size:11px;color:{d_cor}">{int(d.get('kcal',0))} kcal</span>{_macros_ing}
      </span>
    </div>"""
                details_html += "\n  </div>\n</details>"

            _cc, _ce = st.columns([1, 0.09])
            with _cc:
                st.markdown(
                    f'<div style="background:{BG2};border:1px solid {cor}22;'
                    f'border-left:3px solid {cor};border-radius:0 8px 8px 0;'
                    f'padding:10px 14px;margin-bottom:2px">'
                    f'<div style="display:flex;align-items:center;gap:8px">'
                    f'<span style="font-family:{MONO};font-size:11px;font-weight:700;'
                    f'color:{cor};white-space:nowrap;min-width:36px">{hora}</span>'
                    f'<span style="font-size:8px;font-weight:700;letter-spacing:1px;'
                    f'text-transform:uppercase;padding:2px 6px;border-radius:3px;'
                    f'white-space:nowrap;{bsty}">{icon} {cat}</span>'
                    f'<span style="font-size:12px;color:{TEXT};overflow:hidden;'
                    f'text-overflow:ellipsis;white-space:nowrap;flex:1">{food}</span>'
                    f'</div>'
                    f'{macro_row}'
                    f'{details_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with _ce:
                st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
                if st.button("✏", key=f"tog_meal_{rid}", use_container_width=True, help="Editar refeição"):
                    st.session_state["edit_ref_preselect_id"] = rid
                    _tab_editar()


def _render_col_suplementos():
    """Coluna de suplementos — recarrega _q_supp_check a cada rerun do fragment."""
    df_supp_check = _q_supp_check(hoje_sql)
    supp_registrados = {}
    for _, r in df_supp_check.iterrows():
        supp_registrados[r["descricao"].lower()] = int(r["qtd"])

    cards = ""
    for s in SUPLEMENTOS:
        if s["keywords"]:
            feito = _checar_supp(supp_registrados, s["keywords"])
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

    # ── Suplementação ─────────────────────────────────────────────────────────
    st.markdown(
        panel(
            ptitl("Suplementação do dia") +
            f'<div class="sh-supp-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">{cards}</div>'
        ),
        unsafe_allow_html=True,
    )


@st.fragment
def _fragment_registros_dia():
    """Refeições + suplementos no mesmo fragment — cards de supp sincronizam ao salvar."""
    col_m, col_s = st.columns([1.6, 1.4])
    with col_m:
        _render_col_refeicoes()
    with col_s:
        _render_col_suplementos()


_fragment_registros_dia()

st.markdown('<div id="sec-treinos"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Treinos", "Hevy e corridas"), unsafe_allow_html=True)

# PAINEL — DETALHES DOS TREINOS (Hevy)
# ════════════════════════════════════════════════════════════════════════════
_tbtn1, _tbtn2 = st.columns(2)
with _tbtn1:
    _ui_toggle_button("📋 TREINOS ▴", "📋 TREINOS ▾", "treino_tab_open", "btn_treino_tab")
with _tbtn2:
    _ui_toggle_button("🏃 CORRIDAS ▴", "🏃 CORRIDAS ▾", "corrida_tab_open", "btn_corrida_tab")

# ── Tabela de treinos (Hevy) ──────────────────────────────────────────────────
if _toggle_key("treino_tab_open", True):
    st.markdown(
        f'<div style="background:{BG3};border:1px solid {GREEN}33;'
        f'border-top:2px solid {GREEN};border-radius:0 0 10px 10px;'
        f'padding:16px 18px 18px;margin-bottom:12px">',
        unsafe_allow_html=True,
    )

    # Seletor de período
    _tw_col1, _tw_col2 = st.columns([2, 1])
    with _tw_col1:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:9px;font-weight:700;'
            f'letter-spacing:1.5px;text-transform:uppercase;color:{GREEN};margin-bottom:4px">'
            f'💪 DIÁRIO DE TREINOS — HEVY</div>',
            unsafe_allow_html=True,
        )
    with _tw_col2:
        _tw_periodo = st.selectbox(
            "Período", ["Últimos 30 dias", "Últimos 90 dias", "Últimos 6 meses", "Tudo"],
            key="tw_periodo", label_visibility="collapsed"
        )

    _tw_dias_map = {"Últimos 30 dias": 30, "Últimos 90 dias": 90,
                    "Últimos 6 meses": 180, "Tudo": 3650}
    _tw_dias = _tw_dias_map[_tw_periodo]

    _df_tw = DB.query(
        f"SELECT id, date(data_hora,'localtime') as data_treino, "
        f"titulo, duracao_min, volume_kg, exercicios_json "
        f"FROM hevy_treinos "
        f"WHERE date(data_hora,'localtime') >= date('now','-{_tw_dias} days') "
        f"ORDER BY data_hora DESC"
    )
    if not _df_tw.empty:
        _df_tw["data_fmt"] = pd.to_datetime(_df_tw["data_treino"]).dt.strftime("%d/%m/%Y")

    if _df_tw.empty:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:11px;color:{MUTED};padding:12px;'
            f'text-align:center">Nenhum treino encontrado neste período</div>',
            unsafe_allow_html=True,
        )
    else:
        # Expande exercicios_json em linhas individuais por série
        _linhas = []
        for _, _tw_row in _df_tw.iterrows():
            try:
                _exs = json.loads(_tw_row["exercicios_json"] or "[]")
            except Exception:
                _exs = []
            _data = _tw_row["data_fmt"]
            _titulo = _tw_row["titulo"]
            _dur = int(_tw_row["duracao_min"] or 0)

            if not _exs:
                _linhas.append({
                    "Data": _data, "Treino": _titulo, "Exercício": "—",
                    "Série": "—", "Tipo": "—", "Carga (kg)": "—",
                    "Reps": "—", "Volume (kg)": "—", "RPE": "—",
                    "Duração": f"{_dur} min",
                })
                continue

            for _ex in _exs:
                _ex_nome = (_ex.get("title") or _ex.get("name") or
                            _ex.get("exercise_title") or "Exercício")
                _sets = _ex.get("sets", [])
                for _si, _s in enumerate(_sets, 1):
                    _kg   = float(_s.get("weight_kg") or 0)
                    _reps = int(_s.get("reps") or 0)
                    _rpe  = _s.get("rpe")
                    _tipo = _s.get("set_type", "normal") or "normal"
                    _tipo_map = {"normal": "Normal", "warmup": "Aquecimento",
                                 "dropset": "Drop", "failure": "Falha", "myorep": "Myo"}
                    _vol_set = round(_kg * _reps, 1)
                    _linhas.append({
                        "Data": _data,
                        "Treino": _titulo,
                        "Exercício": _ex_nome,
                        "Série": _si,
                        "Tipo": _tipo_map.get(_tipo, _tipo.capitalize()),
                        "Carga (kg)": f"{_kg:.1f}" if _kg > 0 else "—",
                        "Reps": _reps if _reps > 0 else "—",
                        "Volume (kg)": f"{_vol_set:.1f}" if _vol_set > 0 else "—",
                        "RPE": f"{float(_rpe):.1f}" if _rpe else "—",
                        "Duração": f"{_dur} min" if _si == 1 else "",
                    })

        _df_exp = pd.DataFrame(_linhas)

        # Filtro por exercício
        _tw_exs = sorted(_df_exp["Exercício"].dropna().unique().tolist())
        _tw_exs = [e for e in _tw_exs if e != "—"]
        _tw_col3, _tw_col4 = st.columns([2, 1])
        with _tw_col3:
            _tw_ex_filter = st.selectbox(
                "Filtrar exercício", ["Todos"] + _tw_exs,
                key="tw_ex_filter", label_visibility="collapsed"
            )
        with _tw_col4:
            _tw_treino_filter = st.selectbox(
                "Filtrar treino", ["Todos"] + sorted(_df_tw["titulo"].unique().tolist()),
                key="tw_treino_filter", label_visibility="collapsed"
            )

        if _tw_ex_filter != "Todos":
            _df_exp = _df_exp[_df_exp["Exercício"] == _tw_ex_filter]
        if _tw_treino_filter != "Todos":
            _df_exp = _df_exp[_df_exp["Treino"] == _tw_treino_filter]

        # Resumo rápido
        _n_treinos = _df_tw.shape[0]
        _n_exs = len([r for r in _linhas if r["Série"] == 1 and r["Exercício"] != "—"])
        _vol_total = sum(float(r["Volume (kg)"].replace("—", "0") or 0)
                         for r in _linhas if r["Volume (kg)"] != "—")

        st.markdown(
            f'<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px">'
            f'<span style="font-family:{MONO};font-size:10px;color:{GREEN}">'
            f'⚡ {_n_treinos} treinos</span>'
            f'<span style="font-family:{MONO};font-size:10px;color:{CYAN}">'
            f'📌 {len(_df_exp)} séries</span>'
            f'<span style="font-family:{MONO};font-size:10px;color:{AMBER}">'
            f'🏋️ {_vol_total:,.0f} kg volume total</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Renderiza tabela
        _th_s = (f"font-family:{MONO};background:{BG3};color:{GHOST};padding:8px 10px;"
                 f"border-bottom:1px solid {BORDER2};text-transform:uppercase;"
                 f"font-size:9px;letter-spacing:1px;text-align:left;white-space:nowrap")
        _td_s = (f"padding:6px 10px;border-bottom:1px solid #0a1020;"
                 f"font-size:11px;color:{TEXT};vertical-align:middle")
        _td_m = _td_s.replace(f"color:{TEXT}", f"color:{MUTED}")

        _cols_tw = ["Data", "Treino", "Exercício", "Série", "Tipo",
                    "Carga (kg)", "Reps", "Volume (kg)", "RPE", "Duração"]
        _ths = "".join(f"<th style='{_th_s}'>{c}</th>" for c in _cols_tw)
        _tbody = ""
        _prev_data = None
        for _, _lr in _df_exp.iterrows():
            _row_bg = "background:rgba(0,230,118,0.03);" if _lr["Data"] != _prev_data else ""
            _prev_data = _lr["Data"]
            _tipo_cor = {"Aquecimento": AMBER, "Drop": PURPLE,
                         "Falha": RED, "Myo": CYAN}.get(str(_lr["Tipo"]), TEXT)
            _tbody += (
                f"<tr style='{_row_bg}'>"
                f"<td style='{_td_s};color:{GHOST};font-family:{MONO};font-size:10px'>{_lr['Data']}</td>"
                f"<td style='{_td_s};max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>{_lr['Treino']}</td>"
                f"<td style='{_td_s};color:{GREEN}'>{_lr['Exercício']}</td>"
                f"<td style='{_td_m};text-align:center'>{_lr['Série']}</td>"
                f"<td style='{_td_s};color:{_tipo_cor};font-family:{MONO};font-size:9px'>{_lr['Tipo']}</td>"
                f"<td style='{_td_s};font-family:{MONO};text-align:right;color:{CYAN}'>{_lr['Carga (kg)']}</td>"
                f"<td style='{_td_s};font-family:{MONO};text-align:right'>{_lr['Reps']}</td>"
                f"<td style='{_td_s};font-family:{MONO};text-align:right;color:{AMBER}'>{_lr['Volume (kg)']}</td>"
                f"<td style='{_td_s};font-family:{MONO};text-align:right;color:{PURPLE}'>{_lr['RPE']}</td>"
                f"<td style='{_td_m};font-family:{MONO};font-size:10px'>{_lr['Duração']}</td>"
                f"</tr>"
            )

        st.markdown(
            f'<div class="sh-table-scroll" style="border-radius:6px;border:1px solid {BORDER};max-height:480px;overflow-y:auto">'
            f'<table style="width:100%;border-collapse:collapse;background:{BG2};min-width:700px">'
            f'<thead style="position:sticky;top:0;z-index:1"><tr>{_ths}</tr></thead>'
            f'<tbody>{_tbody}</tbody></table></div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

# ── Tabela de corridas (Amazfit) ──────────────────────────────────────────────
if _toggle_key("corrida_tab_open"):
    st.markdown(
        f'<div style="background:{BG3};border:1px solid {CYAN}33;'
        f'border-top:2px solid {CYAN};border-radius:0 0 10px 10px;'
        f'padding:16px 18px 18px;margin-bottom:12px">',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;color:{CYAN};margin-bottom:10px">'
        f'🏃 HISTÓRICO DE CORRIDAS — AMAZFIT</div>',
        unsafe_allow_html=True,
    )

    _df_rc = DB.query("""
        SELECT
            data_hora,
            corrida_km,
            corrida_cal,
            passos,
            distancia_km
        FROM amazfit_dados
        WHERE corrida_km > 0
        ORDER BY data_hora DESC
    """)
    if not _df_rc.empty:
        _df_rc["data_fmt"] = pd.to_datetime(_df_rc["data_hora"]).dt.strftime("%d/%m/%Y")

    if _df_rc.empty:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:11px;color:{MUTED};padding:12px;'
            f'text-align:center">Nenhuma corrida registrada. Faça o sync do Amazfit para carregar os dados.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Estatísticas rápidas
        _rc_total_km  = float(_df_rc["corrida_km"].sum())
        _rc_total_cal = int(_df_rc["corrida_cal"].sum())
        _rc_n         = len(_df_rc)
        _rc_media_km  = _rc_total_km / _rc_n if _rc_n > 0 else 0

        st.markdown(
            f'<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px">'
            f'<span style="font-family:{MONO};font-size:10px;color:{CYAN}">'
            f'📍 {_rc_total_km:.1f} km total</span>'
            f'<span style="font-family:{MONO};font-size:10px;color:{GREEN}">'
            f'🔥 {_rc_total_cal:,} kcal</span>'
            f'<span style="font-family:{MONO};font-size:10px;color:{AMBER}">'
            f'📊 {_rc_media_km:.2f} km/sessão</span>'
            f'<span style="font-family:{MONO};font-size:10px;color:{MUTED}">'
            f'🏁 {_rc_n} sessões</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Tabela
        _th_rc = (f"font-family:{MONO};background:{BG3};color:{GHOST};padding:8px 10px;"
                  f"border-bottom:1px solid {BORDER2};text-transform:uppercase;"
                  f"font-size:9px;letter-spacing:1px;text-align:right;white-space:nowrap")
        _th_rc1 = _th_rc.replace("text-align:right", "text-align:left")
        _td_rc  = (f"padding:7px 10px;border-bottom:1px solid #0a1020;"
                   f"font-size:12px;text-align:right;vertical-align:middle")

        _rc_heads = ["Data", "Distância", "Calorias Corrida", "Ritmo estimado",
                     "Passos (dia)", "Dist. total dia"]
        _ths_rc = (f"<th style='{_th_rc1}'>{_rc_heads[0]}</th>" +
                   "".join(f"<th style='{_th_rc}'>{h}</th>" for h in _rc_heads[1:]))

        _tbody_rc = ""
        for _, _rr in _df_rc.iterrows():
            _rkm   = float(_rr["corrida_km"] or 0)
            _rcal  = int(_rr["corrida_cal"] or 0)
            _rpas  = int(_rr["passos"] or 0)
            _rdist = float(_rr["distancia_km"] or 0)
            # Estimativa de ritmo: presume ~6 min/km padrão se não houver dado de duração
            # (Amazfit não expõe duração da corrida separado)
            _ritmo = "—"
            _tbody_rc += (
                f"<tr>"
                f"<td style='{_td_rc};text-align:left;color:{CYAN};font-family:{MONO};font-size:10px'>{_rr['data_fmt']}</td>"
                f"<td style='{_td_rc};font-family:{MONO};font-weight:700;color:{CYAN}'>{_rkm:.2f} km</td>"
                f"<td style='{_td_rc};font-family:{MONO};color:{GREEN}'>{_rcal:,} kcal</td>"
                f"<td style='{_td_rc};color:{GHOST}'>{_ritmo}</td>"
                f"<td style='{_td_rc};color:{MUTED}'>{_rpas:,}</td>"
                f"<td style='{_td_rc};color:{MUTED}'>{_rdist:.2f} km</td>"
                f"</tr>"
            )

        st.markdown(
            f'<div class="sh-table-scroll" style="border-radius:6px;border:1px solid {BORDER};max-height:400px;overflow-y:auto">'
            f'<table style="width:100%;border-collapse:collapse;background:{BG2};min-width:500px">'
            f'<thead style="position:sticky;top:0;z-index:1"><tr>{_ths_rc}</tr></thead>'
            f'<tbody>{_tbody_rc}</tbody></table></div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)



# ── BLOCO: ANÁLISE ───────────────────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 7 — BANCO DE ALIMENTOS (página dedicada)
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div id="sec-banco"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Banco", "Cadastro · Edição · Favoritos"), unsafe_allow_html=True)

_df_banco_cnt = _q_alimentos_favoritos()
_banco_n = len(_df_banco_cnt)
_banco_fav = int((_df_banco_cnt["favorito"] == 1).sum()) if not _df_banco_cnt.empty else 0

st.markdown(
    f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;padding:16px 18px;margin-bottom:12px">'
    f'<div style="font-size:14px;color:{TEXT};font-weight:600;margin-bottom:6px">🍽️ Banco de Alimentos</div>'
    f'<div style="font-size:12px;color:{MUTED};line-height:1.5;margin-bottom:10px">'
    f'Cadastre alimentos, defina porção de referência (g, ml, L, und) e marque favoritos. '
    f'Combinações de refeição também podem ser salvas como favorito na nova/edição de refeição.</div>'
    f'<div style="display:flex;gap:16px;font-family:{MONO};font-size:10px;color:{GHOST}">'
    f'<span>{_banco_n} alimento(s)</span><span>⭐ {_banco_fav} favorito(s)</span></div></div>',
    unsafe_allow_html=True,
)

if st.button("Abrir Banco de Alimentos →", key="btn_open_banco_page", use_container_width=True, type="primary"):
    st.switch_page("pages/1_Banco_de_Alimentos.py")


# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 6 — HISTÓRICO SEMANAL
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div id="sec-historico"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Histórico", "Últimos 30 dias e tendências"), unsafe_allow_html=True)


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

def _trend_data(df, col):
    """Regressão linear: retorna (x_vals, y_fit, slope)."""
    import numpy as np
    if len(df) < 3 or col not in df.columns:
        return None, None, 0
    y = pd.to_numeric(df[col], errors="coerce").fillna(0).values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    slope = float(coeffs[0])
    y_fit = np.polyval(coeffs, x)
    return df["dia"].values, y_fit, slope

def trend_line(df, col, cor="#aaaaaa", name="Tendência"):
    """Trace de linha de tendência (regressão linear)."""
    xs, ys, _ = _trend_data(df, col)
    if xs is None:
        return None
    return go.Scatter(
        x=xs, y=ys, mode="lines", name=name,
        line=dict(color=cor, width=1.5, dash="dot"),
        opacity=0.65,
        hovertemplate=f"<b>%{{x|%d/%m}}</b><br>{name}: %{{y:.1f}}<extra></extra>",
    )

def _trend_badge(df, col, higher_is_better=True):
    """Retorna (ícone, cor_hex, str_pct) comparando 1ª metade vs 2ª metade do período."""
    if len(df) < 4 or col not in df.columns:
        return "→", MUTED, ""
    y = pd.to_numeric(df[col], errors="coerce").fillna(0).values
    half = max(1, len(y) // 2)
    avg1 = float(y[:half].mean())
    avg2 = float(y[half:].mean())
    if avg1 == 0:
        return "→", MUTED, ""
    pct = (avg2 - avg1) / abs(avg1) * 100
    going_up   = pct >  2.5
    going_down = pct < -2.5
    if higher_is_better:
        icon  = "↑" if going_up   else ("↓" if going_down  else "→")
        color = GREEN if going_up  else (RED  if going_down  else AMBER)
    else:
        icon  = "↓" if going_down else ("↑" if going_up    else "→")
        color = GREEN if going_down else (RED if going_up    else AMBER)
    return icon, color, f"{pct:+.1f}%"



def _df_media(df, col):
    if df is None or df.empty or col not in df.columns:
        return 0
    return df[col].replace(0, pd.NA).mean()


def _fmt_metric(val, sufixo="", decimais=0):
    if pd.isna(val) or val == 0:
        return "—"
    return f"{val:.{decimais}f}{sufixo}"


def _ia_coach_periodo_dias():
    periodo = st.session_state.get("ia_periodo", st.session_state.get("periodo_hist", "14 dias"))
    try:
        return int(str(periodo).split()[0])
    except Exception:
        return 14


def _ia_coach_load_data(n_dias):
    df_hist = db(f"""
        SELECT date(data_hora) as dia, passos, calorias_gastas, distancia_km,
               sono_total_min, sono_profundo_min, hrv_ms, pai, corrida_km, corrida_cal
        FROM amazfit_dados
        WHERE date(data_hora) >= date('now', '-{n_dias} days')
        ORDER BY dia ASC
    """)
    df_macro = db(f"""
        SELECT date(data_hora, 'localtime') as dia,
               SUM(calorias) as cal, SUM(proteinas) as prot,
               SUM(carboidratos) as carb, SUM(gorduras) as gord
        FROM refeicoes
        WHERE date(data_hora, 'localtime') >= date('now', '-{n_dias} days')
        GROUP BY dia ORDER BY dia ASC
    """)
    df_hevy = db(f"""
        SELECT COUNT(*) as count_treino, SUM(duracao_min) as dur, SUM(volume_kg) as vol
        FROM hevy_treinos
        WHERE date(data_hora, 'localtime') >= date('now', '-{n_dias} days')
    """)
    total_treinos = 0
    total_vol = 0.0
    total_dur = 0
    if not df_hevy.empty:
        if df_hevy["count_treino"].iloc[0] is not None:
            total_treinos = int(df_hevy["count_treino"].iloc[0])
        if df_hevy["vol"].iloc[0] is not None:
            total_vol = float(df_hevy["vol"].iloc[0])
        if df_hevy["dur"].iloc[0] is not None:
            total_dur = int(df_hevy["dur"].iloc[0])
    media_vol = total_vol / total_treinos if total_treinos > 0 else 0.0
    media_dur = total_dur / total_treinos if total_treinos > 0 else 0.0
    media_deficit = 0.0
    if not df_hist.empty or not df_macro.empty:
        df_h = df_hist.copy() if not df_hist.empty else pd.DataFrame(columns=["dia", "calorias_gastas"])
        df_m = df_macro.copy() if not df_macro.empty else pd.DataFrame(columns=["dia", "cal"])
        if "calorias_gastas" not in df_h.columns:
            df_h["calorias_gastas"] = 0.0
        if "cal" not in df_m.columns:
            df_m["cal"] = 0.0
        merged = pd.merge(df_h, df_m, on="dia", how="outer").fillna(0)
        merged["deficit"] = (TMB + merged["calorias_gastas"]) - merged["cal"]
        media_deficit = merged["deficit"].mean()
    return df_hist, df_macro, total_treinos, media_vol, media_dur, media_deficit


def _render_ia_coach():
    """IA Coach — sempre visível; dados carregados ao gerar análise."""
    # ── IA Coach ─────────────────────────────────────────────────────────────
    st.markdown('<div id="sec-ia"></div>', unsafe_allow_html=True)
    st.markdown(sh_section("IA Coach", "Análise de Emagrecimento & Performance"), unsafe_allow_html=True)

    # Valores padrão do protocolo
    _proto_defaults = {
        "rotina": "Musculação + Cardio (6x/sem)",
        "hiit": "Ter & Sex — Alta Intensidade / EPOC",
        "zona2": "Seg, Qua, Qui, Sáb — Corrida BPM 120-140",
        "peso_inicial": "115.3 kg (Jan/2026)",
    }
    if "coach_proto" not in st.session_state:
        st.session_state["coach_proto"] = _proto_defaults.copy()
    _proto = st.session_state["coach_proto"]

    _proto_hdr, _proto_edit_btn = st.columns([1, 0.2])
    with _proto_hdr:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{CYAN};margin-bottom:6px">📋 PROTOCOLO & METAS METABÓLICAS</div>',
            unsafe_allow_html=True,
        )
    with _proto_edit_btn:
        if st.button("✏ editar" if not st.session_state.get("coach_proto_editing") else "✕ fechar",
                     key="btn_proto_edit", use_container_width=True):
            st.session_state["coach_proto_editing"] = not st.session_state.get("coach_proto_editing", False)
            st.rerun()

    if st.session_state.get("coach_proto_editing", False):
        with st.form("form_proto_coach"):
            _p1, _p2 = st.columns(2)
            with _p1:
                _rotina_in = st.text_input("Rotina de Exercícios", value=_proto["rotina"])
                _hiit_in   = st.text_input("Treinos HIIT", value=_proto["hiit"])
            with _p2:
                _zona2_in  = st.text_input("Treinos Zona 2", value=_proto["zona2"])
                _pinit_in  = st.text_input("Peso inicial (referência)", value=_proto["peso_inicial"])
            if st.form_submit_button("✓ SALVAR PROTOCOLO", use_container_width=True):
                st.session_state["coach_proto"] = {
                    "rotina": _rotina_in, "hiit": _hiit_in,
                    "zona2": _zona2_in, "peso_inicial": _pinit_in,
                }
                st.session_state["coach_proto_editing"] = False
                _notif("Protocolo atualizado")
                st.rerun()

    coach_html = f"""
    <div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;padding:14px 18px;margin-bottom:15px">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px">
            <div style="font-size:11px;color:{MUTED}">Evolução de Peso
              <div style="font-size:13px;font-weight:700;color:{TEXT};margin-top:2px">{_proto["peso_inicial"]} ➔ {peso:.1f} kg atual</div></div>
            <div style="font-size:11px;color:{MUTED}">Rotina
              <div style="font-size:13px;font-weight:700;color:{TEXT};margin-top:2px">{_proto["rotina"]}</div></div>
            <div style="font-size:11px;color:{MUTED}">HIIT
              <div style="font-size:13px;font-weight:700;color:{TEXT};margin-top:2px">{_proto["hiit"]}</div></div>
            <div style="font-size:11px;color:{MUTED}">Zona 2
              <div style="font-size:13px;font-weight:700;color:{TEXT};margin-top:2px">{_proto["zona2"]}</div></div>
        </div>
        <div style="margin-top:8px;padding-top:8px;border-top:1px solid {BORDER};display:flex;gap:8px;align-items:center">
            <span style="background:rgba(167,139,250,0.1);border:1px solid {PURPLE}55;border-radius:4px;padding:2px 8px;font-family:{MONO};font-size:9px;color:{PURPLE};font-weight:700;letter-spacing:0.5px">TIRZEPATIDA</span>
            <span style="font-family:{MONO};font-size:10px;color:{GHOST}">Protocolo farmacológico ativo · injetável semanal</span>
        </div>
    </div>
    """
    st.markdown(coach_html, unsafe_allow_html=True)

    btn_col, sel_col = st.columns([1, 1])
    with btn_col:
        executar_analise = st.button("🧠 NOVA ANÁLISE DE EMAGRECIMENTO", key="btn_ia_coach", use_container_width=True)

    # Busca análises anteriores para o seletor histórico
    df_past = db("""
        SELECT id, data_hora, n_dias
        FROM ia_analises_clinicas
        ORDER BY data_hora DESC
    """)

    past_options = ["📂  Histórico de análises ▾"]
    id_map = {}
    if not df_past.empty:
        for idx, r_row in df_past.iterrows():
            dt_val = r_row["data_hora"]
            try:
                if isinstance(dt_val, str):
                    dt_obj = datetime.strptime(dt_val.split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    dt_obj = dt_val
                dt_str = dt_obj.strftime("%d/%m  %H:%M")
            except Exception:
                dt_str = str(dt_val)
            lbl = f"↩  {dt_str}  ({r_row['n_dias']}d)"
            past_options.append(lbl)
            id_map[lbl] = int(r_row["id"])

    with sel_col:
        _hist_open = st.session_state.get("ia_hist_open", False)
        _hist_lbl = "✕ FECHAR" if _hist_open else "📂 HISTÓRICO ▾"
        if st.button(_hist_lbl, key="btn_ia_hist_toggle", use_container_width=True):
            st.session_state["ia_hist_open"] = not _hist_open
            st.rerun()

    # ── Menu dropdown do histórico ─────────────────────────────────────────────
    if st.session_state.get("ia_hist_open", False):
        if id_map:
            st.markdown(
                f'<div style="background:{BG3};border:1px solid {BORDER};'
                f'border-top:2px solid {CYAN};border-radius:0 0 8px 8px;'
                f'padding:6px 4px;margin-top:-2px">',
                unsafe_allow_html=True,
            )
            for _hlbl, _hid in id_map.items():
                _col_item, = st.columns([1])
                if st.button(
                    f"↩  {_hlbl}",
                    key=f"ia_hist_item_{_hid}",
                    use_container_width=True,
                ):
                    _df_sel = db("SELECT analise_txt FROM ia_analises_clinicas WHERE id = ?", [_hid])
                    if not _df_sel.empty:
                        st.session_state["ia_coach_result"] = _df_sel["analise_txt"].iloc[0]
                    st.session_state["ia_hist_open"] = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div style="background:{BG3};border:1px solid {BORDER};'
                f'border-top:2px solid {BORDER};border-radius:0 0 8px 8px;'
                f'padding:10px 14px;margin-top:-2px;'
                f'font-family:{MONO};font-size:10px;color:{GHOST}">Sem análises salvas</div>',
                unsafe_allow_html=True,
            )

    if executar_analise:
      try:
        with st.status("🧠 IA Coach — coletando dados e gerando análise...", expanded=True) as _ia_status:
            _ia_status.write("📊 Calculando médias do período selecionado...")
            try:
                # ── 1. MÉDIAS DO PERÍODO SELECIONADO ─────────────────────────
                media_passos      = media(df_hist, "passos")
                media_cal_gastas  = media(df_hist, "calorias_gastas")
                media_sono        = media(df_hist, "sono_total_min")
                media_sono_prof   = media(df_hist, "sono_profundo_min")
                media_hrv         = media(df_hist, "hrv_ms")
                media_pai         = media(df_hist, "pai")
                media_cal_ingestao= media(df_macro_hist, "cal")
                media_prot        = media(df_macro_hist, "prot")
                media_carb        = media(df_macro_hist, "carb")
                media_gord        = media(df_macro_hist, "gord")
                media_corrida_km  = media(df_hist, "corrida_km")
                media_corrida_cal = media(df_hist, "corrida_cal")

                # ── 2. DADOS BRUTOS COMPLETOS (queries extras) ────────────────
                _ia_status.write("⚖️ Buscando histórico de peso...")

                # Histórico de peso (medidas)
                _ia_peso_df = DB.query(
                    "SELECT data, peso FROM medidas WHERE peso IS NOT NULL ORDER BY data ASC"
                )

                _ia_status.write("💪 Buscando treinos de musculação...")

                # Treinos detalhados — últimas 100 sessões
                _ia_hevy_df = DB.query(
                    "SELECT date(data_hora,'localtime') as dt, titulo, "
                    "duracao_min, volume_kg, exercicios_json "
                    "FROM hevy_treinos ORDER BY data_hora DESC LIMIT 100"
                )

                _ia_status.write("🏃 Buscando histórico de corridas...")

                # Corridas completas
                _ia_corridas_df = DB.query(
                    "SELECT data_hora, corrida_km, corrida_cal, passos "
                    "FROM amazfit_dados WHERE corrida_km > 0 ORDER BY data_hora DESC"
                )

                _ia_status.write("🌙 Buscando dados diários (sono, HRV, PAI)...")

                # Dados diários Amazfit (sono, HRV, PAI, passos) — últimos 90 dias
                _ia_daily_df = DB.query(
                    "SELECT date(data_hora) as dt, passos, calorias_gastas, "
                    "sono_total_min, sono_profundo_min, hrv_ms, pai, corrida_km "
                    "FROM amazfit_dados "
                    "WHERE date(data_hora) >= date('now','-90 days') "
                    "ORDER BY data_hora ASC"
                )

                _ia_status.write("🥗 Buscando nutrição e medicação...")

                # Nutrição diária — últimos 90 dias
                _ia_nutri_df = DB.query(
                    "SELECT date(data_hora,'localtime') as dt, "
                    "SUM(calorias) as cal, SUM(proteinas) as prot, "
                    "SUM(carboidratos) as carb, SUM(gorduras) as gord "
                    "FROM refeicoes "
                    "WHERE date(data_hora,'localtime') >= date('now','-90 days') "
                    "GROUP BY dt ORDER BY dt ASC"
                )

                # Medicação (Tirzepatida)
                _ia_med_df = DB.query(
                    "SELECT date(data_hora,'localtime') as dt, dose_mg "
                    "FROM medicacao ORDER BY data_hora ASC"
                )

                _ia_status.write("📝 Montando contexto clínico completo...")

                # ── 3. FORMATAR BLOCOS DE TEXTO ───────────────────────────────

                def _fmt_df_linhas(header, df, cols_fmt):
                    """Formata DataFrame como bloco de texto para o prompt."""
                    if df is None or df.empty:
                        return f"{header}\n  [Sem dados]\n\n"
                    txt = header + "\n"
                    for _, r in df.iterrows():
                        linha = "  " + " | ".join(
                            str(cols_fmt[c](r[c])) if c in r else "—"
                            for c in cols_fmt
                        )
                        txt += linha + "\n"
                    return txt + "\n"

                # Peso
                _txt_peso = "📊 HISTÓRICO DE PESO (todas as medidas registradas):\n"
                if not _ia_peso_df.empty:
                    for _, r in _ia_peso_df.iterrows():
                        try:
                            _d = pd.to_datetime(str(r["data"])).strftime("%d/%m/%Y")
                        except Exception:
                            _d = str(r["data"])
                        _txt_peso += f"  {_d}: {float(r['peso']):.1f} kg\n"
                else:
                    _txt_peso += "  [Sem registros de peso]\n"
                _txt_peso += "\n"

                # Medicação Tirzepatida
                _txt_med = "💊 HISTÓRICO TIRZEPATIDA (todas as aplicações):\n"
                if not _ia_med_df.empty:
                    for _, r in _ia_med_df.iterrows():
                        try:
                            _d = pd.to_datetime(str(r["dt"])).strftime("%d/%m/%Y")
                        except Exception:
                            _d = str(r["dt"])
                        _txt_med += f"  {_d}: {float(r['dose_mg']):.1f} mg\n"
                else:
                    _txt_med += "  [Sem registros]\n"
                _txt_med += "\n"

                # Dados diários (Amazfit + Nutrição mesclados)
                _txt_diario = f"📅 DADOS DIÁRIOS — ÚLTIMOS 90 DIAS (Amazfit + Nutrição):\n"
                _txt_diario += "  Data | Passos | Cal.Gasto | Sono(min) | S.Prof(min) | HRV(ms) | PAI | Corrida(km) | Cal.Ingest | Prot(g) | Carb(g) | Gord(g)\n"
                if not _ia_daily_df.empty:
                    # merge com nutrição por dt
                    _nutri_idx = {}
                    if not _ia_nutri_df.empty:
                        for _, nr in _ia_nutri_df.iterrows():
                            _nutri_idx[str(nr["dt"])] = nr
                    for _, dr in _ia_daily_df.iterrows():
                        _dt_str = str(dr["dt"])
                        try:
                            _dt_fmt = pd.to_datetime(_dt_str).strftime("%d/%m")
                        except Exception:
                            _dt_fmt = _dt_str
                        _nr = _nutri_idx.get(_dt_str)
                        _cal_i = f"{int(_nr['cal'])}" if _nr is not None and not pd.isna(_nr.get('cal', float('nan'))) else "—"
                        _prot_i = f"{int(_nr['prot'])}" if _nr is not None and not pd.isna(_nr.get('prot', float('nan'))) else "—"
                        _carb_i = f"{int(_nr['carb'])}" if _nr is not None and not pd.isna(_nr.get('carb', float('nan'))) else "—"
                        _gord_i = f"{int(_nr['gord'])}" if _nr is not None and not pd.isna(_nr.get('gord', float('nan'))) else "—"
                        _txt_diario += (
                            f"  {_dt_fmt} | {int(dr.get('passos',0) or 0):,} | "
                            f"{int(dr.get('calorias_gastas',0) or 0)} | "
                            f"{int(dr.get('sono_total_min',0) or 0)} | "
                            f"{int(dr.get('sono_profundo_min',0) or 0)} | "
                            f"{int(dr.get('hrv_ms',0) or 0)} | "
                            f"{int(dr.get('pai',0) or 0)} | "
                            f"{float(dr.get('corrida_km',0) or 0):.1f} | "
                            f"{_cal_i} | {_prot_i} | {_carb_i} | {_gord_i}\n"
                        )
                elif not _ia_nutri_df.empty:
                    _txt_diario += "  [Dados Amazfit indisponíveis — somente nutrição]\n"
                    for _, nr in _ia_nutri_df.iterrows():
                        try:
                            _dt_fmt = pd.to_datetime(str(nr["dt"])).strftime("%d/%m")
                        except Exception:
                            _dt_fmt = str(nr["dt"])
                        _txt_diario += (
                            f"  {_dt_fmt} | — | — | — | — | — | — | — | "
                            f"{int(nr.get('cal',0) or 0)} | {int(nr.get('prot',0) or 0)} | "
                            f"{int(nr.get('carb',0) or 0)} | {int(nr.get('gord',0) or 0)}\n"
                        )
                else:
                    _txt_diario += "  [Sem dados diários disponíveis]\n"
                _txt_diario += "\n"

                # Corridas
                _txt_corridas = "🏃 HISTÓRICO DE CORRIDAS (Amazfit):\n"
                _txt_corridas += "  Data | KM | Cal corrida | Passos dia\n"
                if not _ia_corridas_df.empty:
                    for _, cr in _ia_corridas_df.iterrows():
                        try:
                            _cd = pd.to_datetime(str(cr["data_hora"])).strftime("%d/%m/%Y")
                        except Exception:
                            _cd = str(cr["data_hora"])
                        _txt_corridas += (
                            f"  {_cd} | {float(cr.get('corrida_km',0) or 0):.2f} km | "
                            f"{int(cr.get('corrida_cal',0) or 0)} kcal | "
                            f"{int(cr.get('passos',0) or 0):,} passos\n"
                        )
                else:
                    _txt_corridas += "  [Sem corridas registradas]\n"
                _txt_corridas += "\n"

                # Treinos detalhados (exercício por série)
                _txt_treinos = "💪 TREINOS DE MUSCULAÇÃO (Hevy) — DETALHADO POR SÉRIE:\n"
                _txt_treinos += "  Data | Treino | Exercício | Série | Tipo | Carga(kg) | Reps | Vol(kg) | RPE\n"
                if not _ia_hevy_df.empty:
                    for _, hw in _ia_hevy_df.iterrows():
                        try:
                            _hd = pd.to_datetime(str(hw["dt"])).strftime("%d/%m/%Y")
                        except Exception:
                            _hd = str(hw["dt"])
                        _htit = str(hw["titulo"])
                        _hdur = int(hw.get("duracao_min") or 0)
                        try:
                            _hexs = json.loads(hw["exercicios_json"] or "[]")
                        except Exception:
                            _hexs = []
                        if not _hexs:
                            _txt_treinos += f"  {_hd} | {_htit} | [sem exercícios] | — | — | — | — | — | —\n"
                            continue
                        for _hex in _hexs:
                            _hex_nome = (_hex.get("title") or _hex.get("name") or
                                         _hex.get("exercise_title") or "Exercício")
                            _hsets = _hex.get("sets", [])
                            for _hsi, _hs in enumerate(_hsets, 1):
                                _hkg   = float(_hs.get("weight_kg") or 0)
                                _hreps = int(_hs.get("reps") or 0)
                                _hrpe  = _hs.get("rpe")
                                _htipo = (_hs.get("set_type") or "normal").capitalize()
                                _hvol  = round(_hkg * _hreps, 1)
                                _txt_treinos += (
                                    f"  {_hd} | {_htit} | {_hex_nome} | {_hsi} | {_htipo} | "
                                    f"{_hkg:.1f} | {_hreps} | {_hvol:.1f} | "
                                    f"{float(_hrpe):.1f}\n" if _hrpe else
                                    f"  {_hd} | {_htit} | {_hex_nome} | {_hsi} | {_htipo} | "
                                    f"{_hkg:.1f} | {_hreps} | {_hvol:.1f} | —\n"
                                )
                else:
                    _txt_treinos += "  [Sem treinos registrados]\n"
                _txt_treinos += "\n"

                # ── 4. PROMPT COMPLETO ────────────────────────────────────────
                _proto = st.session_state.get("coach_proto", {
                    "rotina": "Musculação + Cardio (6x/sem)",
                    "hiit": "Ter & Sex — Alta Intensidade / EPOC",
                    "zona2": "Seg, Qua, Qui, Sáb — Corrida BPM 120-140",
                    "peso_inicial": "115.3 kg (Jan/2026)",
                })

                prompt = (
                    "Você é o IA Coach de Elite do Leandro — Arquiteto de Performance Humana, "
                    "Nutricionista Esportivo de Elite e Endocrinologista de Alta Performance.\n"
                    "Sua missão é gerar uma análise clínica e metabólica COMPLETA, extremamente crítica e sem rodeios, "
                    "baseada nos dados reais abaixo. USE OS DADOS BRUTOS para identificar padrões, tendências, "
                    "inconsistências e oportunidades concretas — não genéricos.\n\n"

                    "═══════════════════════════════════════════════════\n"
                    "CONTEXTO DO ATLETA\n"
                    "═══════════════════════════════════════════════════\n"
                    f"- Peso Inicial: {_proto['peso_inicial']}\n"
                    f"- Peso Atual: {peso:.1f} kg  (Perda total: -{115.3 - peso:.1f} kg)\n"
                    f"- Protocolo Farmacológico: Tirzepatida (injetável semanal)\n"
                    f"- Rotina: {_proto['rotina']}\n"
                    f"- HIIT: {_proto['hiit']}\n"
                    f"- Zona 2: {_proto['zona2']}\n\n"

                    f"═══════════════════════════════════════════════════\n"
                    f"MÉDIAS DO PERÍODO ANALISADO ({n_dias} dias)\n"
                    "═══════════════════════════════════════════════════\n"
                    f"- Calorias ingeridas: {fmt_val(media_cal_ingestao,' kcal',0)} · "
                    f"Proteínas: {fmt_val(media_prot,' g',0)} · "
                    f"Carb: {fmt_val(media_carb,' g',0)} · "
                    f"Gordura: {fmt_val(media_gord,' g',0)}\n"
                    f"- Gasto calórico ativ: {fmt_val(media_cal_gastas,' kcal',0)} · "
                    f"Déficit médio: {fmt_val(media_deficit,' kcal',0)}\n"
                    f"- Corrida: {fmt_val(media_corrida_km,' km/dia',2)} · "
                    f"{fmt_val(media_corrida_cal,' kcal/dia',0)}\n"
                    f"- Musculação: {total_treinos} treinos · "
                    f"Vol médio: {fmt_val(media_vol_treino,' kg',0)} · "
                    f"Duração média: {fmt_val(media_dur_treino,' min',0)}\n"
                    f"- Passos: {fmt_val(media_passos,'',0)}/dia · "
                    f"Sono total: {fmt_val(media_sono,' min',0)} · "
                    f"Sono profundo: {fmt_val(media_sono_prof,' min',0)}\n"
                    f"- HRV: {fmt_val(media_hrv,' ms',0)} · PAI: {fmt_val(media_pai,'',0)}\n\n"

                    "═══════════════════════════════════════════════════\n"
                    "DADOS BRUTOS COMPLETOS\n"
                    "═══════════════════════════════════════════════════\n"
                    + _txt_peso
                    + _txt_med
                    + _txt_corridas
                    + _txt_diario
                    + _txt_treinos +

                    "═══════════════════════════════════════════════════\n"
                    "ANÁLISE SOLICITADA\n"
                    "═══════════════════════════════════════════════════\n"
                    "Com base em TODOS os dados acima — padrão diário de sono, HRV, PAI, carga dos treinos, "
                    "exercícios específicos executados, progressão de cargas, frequência de corridas, "
                    "histórico de peso e protocolo de Tirzepatida — forneça um parecer clínico estruturado "
                    "EXATAMENTE nos 5 tópicos abaixo:\n\n"
                    "1. 🔬 METABOLISMO & TIRZEPATIDA: Avalie o impacto real da medicação no ritmo de "
                    "perda de peso (analise a curva do histórico), risco de catabolismo muscular dado "
                    "o déficit e ingestão proteica, e adequação da dose atual.\n\n"
                    "2. 💪 MUSCULAÇÃO — PROGRESSÃO DE CARGAS: Analise os treinos reais (exercícios, "
                    "cargas, RPE, volume por sessão). Identifique pontos de estagnação, exercícios com "
                    "RPE muito alto/baixo, desequilíbrios musculares e recomende ajustes específicos.\n\n"
                    "3. 🏃 CARDIO (ZONA 2 & HIIT): Avalie a consistência das corridas, volume semanal "
                    "real registrado, correlação com HRV/PAI (recuperação), e se o estímulo está correto "
                    "para lipólise máxima sem comprometer recuperação muscular.\n\n"
                    "4. 😴 RECUPERAÇÃO & BIOMARCADORES: Analise a qualidade do sono (total vs profundo), "
                    "tendência do HRV (melhora ou piora de recuperação), PAI (carga cardiovascular "
                    "acumulada). Identifique dias/semanas de sobrecarga ou subrecuperação.\n\n"
                    "5. ⚡ PLANO DE AÇÃO — PRÓXIMAS 2 SEMANAS: Ações concretas e específicas "
                    "(exercícios, cargas, volume, macros, sono) para maximizar perda de gordura, "
                    "preservar/ganhar massa muscular e melhorar biomarcadores. Seja cirúrgico.\n\n"
                    "Tom: técnico, sênior, clínico, sem introduções genéricas. Cite números reais dos dados."
                )

                _ia_status.write("🤖 Consultando Gemini 2.5 Flash...")
                vision = _gemini_model()
                res = vision.generate_content(prompt)
                st.session_state["ia_coach_result"] = res.text
                _ia_status.update(label="✅ Análise concluída!", state="complete", expanded=False)

                # Salvar no histórico
                try:
                    DB.execute(
                        "INSERT INTO ia_analises_clinicas (analise_txt, n_dias) VALUES (?, ?)",
                        [res.text, n_dias]
                    )
                except Exception as save_err:
                    st.warning(f"⚠️ Erro ao salvar análise no histórico: {save_err}")
                st.rerun()
            except Exception as e:
                _ia_status.update(label=f"❌ Erro: {e}", state="error", expanded=True)
                st.error(f"❌ Erro ao chamar a IA: {e}")
      except Exception as _outer_e:
          st.error(f"❌ Erro ao iniciar análise: {_outer_e}")

    if "ia_coach_result" in st.session_state:
        st.markdown(f"""
        <div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;padding:20px;margin-top:10px;margin-bottom:15px;line-height:1.6">
            <div style="font-family:{MONO};font-size:11px;font-weight:700;color:{GREEN};letter-spacing:1.5px;margin-bottom:15px;text-transform:uppercase">🩺 DIAGNÓSTICO CLÍNICO DA IA</div>
    
        {st.session_state["ia_coach_result"]}
    
        </div>
        """, unsafe_allow_html=True)



@st.fragment
def _fragment_historico():
    """Período + queries + Plotly só após o usuário carregar o histórico."""
    if not st.session_state.get("hist_carregado", False):
        st.markdown(
            f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;'
            f'padding:32px 24px;text-align:center;margin-bottom:16px">'
            f'<div style="font-size:32px;margin-bottom:12px">📊</div>'
            f'<div style="font-family:{MONO};font-size:11px;font-weight:700;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:{MUTED};margin-bottom:8px">Histórico não carregado</div>'
            f'<div style="font-size:12px;color:{GHOST}">Clique em <b style="color:{CYAN}">📊 Carregar</b> '
            f'para buscar e exibir os gráficos do período selecionado</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _hload1, _hload2, _hload3 = st.columns([1, 2, 1])
        with _hload2:
            if st.button("📊 Carregar dados do período", key="btn_hist_load", use_container_width=True):
                st.session_state["hist_carregado"] = True
                st.rerun(scope="fragment")
        return

    st.markdown(
        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{MUTED};margin-bottom:4px">PERÍODO DE ANÁLISE</div>',
        unsafe_allow_html=True,
    )
    periodo = st.radio(
        "Período",
        ["7 dias", "14 dias", "30 dias", "90 dias"],
        index=1,
        horizontal=True,
        label_visibility="collapsed",
        key="periodo_hist",
    )
    n_dias = int(periodo.split()[0])

    df_hist = pd.DataFrame()
    df_macro_hist = pd.DataFrame()
    df_hevy_hist = pd.DataFrame()
    df_hevy_list = pd.DataFrame()
    total_treinos = 0
    total_vol = 0.0
    total_dur = 0
    media_vol_treino = 0.0
    media_dur_treino = 0.0
    media_deficit = 0.0

    df_hist = db(f"""
        SELECT
            date(data_hora) as dia,
            passos, calorias_gastas, distancia_km,
            sono_total_min, sono_profundo_min,
            hrv_ms, pai,
            corrida_km, corrida_cal
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

    # Hevy history query
    df_hevy_hist = db(f"""
        SELECT
            COUNT(*) as count_treino,
            SUM(duracao_min) as dur,
            SUM(volume_kg) as vol
        FROM hevy_treinos
        WHERE date(data_hora, 'localtime') >= date('now', '-{n_dias} days')
    """)
    total_treinos = int(df_hevy_hist["count_treino"].iloc[0]) if not df_hevy_hist.empty and df_hevy_hist["count_treino"].iloc[0] is not None else 0
    total_vol = float(df_hevy_hist["vol"].iloc[0]) if not df_hevy_hist.empty and df_hevy_hist["vol"].iloc[0] is not None else 0.0
    total_dur = int(df_hevy_hist["dur"].iloc[0]) if not df_hevy_hist.empty and df_hevy_hist["dur"].iloc[0] is not None else 0
    media_vol_treino = total_vol / total_treinos if total_treinos > 0 else 0.0
    media_dur_treino = total_dur / total_treinos if total_treinos > 0 else 0.0

    df_hevy_list = db(f"""
        SELECT
            date(data_hora, 'localtime') as dia,
            titulo, duracao_min, volume_kg
        FROM hevy_treinos
        WHERE date(data_hora, 'localtime') >= date('now', '-{n_dias} days')
        ORDER BY data_hora ASC
    """)

    # ── Caption: intervalo real dos dados carregados ─────────────────────────
    if not df_hist.empty:
        try:
            _min_d = pd.to_datetime(df_hist["dia"].min()).strftime("%d/%m/%Y")
            _max_d = pd.to_datetime(df_hist["dia"].max()).strftime("%d/%m/%Y")
            _n_nutri = len(df_macro_hist)
            st.markdown(
                f'<div style="font-size:10px;color:{GHOST};font-family:{MONO};'
                f'letter-spacing:0.5px;margin:4px 0 8px;text-align:right">'
                f'📅 {_min_d} → {_max_d} · {len(df_hist)} dias Amazfit · {_n_nutri} dias nutrição</div>',
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    _tem_qualquer_dado = not df_hist.empty or not df_macro_hist.empty

    if _tem_qualquer_dado:

        # ── Tabela resumo semanal ─────────────────────────────────────────────────
        st.markdown(sh_section("Resumo", f"Médias dos últimos {n_dias} dias"), unsafe_allow_html=True)

        if df_hist.empty and not df_macro_hist.empty:
            st.info("💡 Dados do Amazfit não encontrados para este período. Exibindo dados de nutrição disponíveis.")

        def media(df, col):
            return df[col].replace(0, pd.NA).mean() if col in df.columns else 0

        def fmt_val(val, sufixo="", decimais=0):
            if pd.isna(val) or val == 0:
                return "—"
            return f"{val:.{decimais}f}{sufixo}"

        # Calcular déficit calórico médio para o resumo
        media_deficit = 0.0
        if not df_hist.empty or not df_macro_hist.empty:
            df_h = df_hist.copy() if not df_hist.empty else pd.DataFrame(columns=["dia", "calorias_gastas"])
            df_m = df_macro_hist.copy() if not df_macro_hist.empty else pd.DataFrame(columns=["dia", "cal"])
            if "calorias_gastas" not in df_h.columns:
                df_h["calorias_gastas"] = 0.0
            if "cal" not in df_m.columns:
                df_m["cal"] = 0.0
            df_merged = pd.merge(df_h, df_m, on="dia", how="outer").fillna(0)
            df_merged["deficit"] = (TMB + df_merged["calorias_gastas"]) - df_merged["cal"]
            media_deficit = df_merged["deficit"].mean()

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
                 f"meta {TMB}"),
                ("🥩", "Proteínas/dia", fmt_val(media(df_macro_hist, "prot"), " g", 0),
                 f"meta {META_PROT}g"),
                ("📉", "Déficit/dia",    fmt_val(media_deficit, " kcal", 0),
                 "meta 500 kcal"),
            ]

        # Musculação averages from Hevy
        medias += [
            ("🏋️", "Vol. Musculação", fmt_val(media_vol_treino, " kg", 0), f"{total_treinos} treinos"),
            ("⏱️", "Treino Médio",    fmt_val(media_dur_treino, " min", 0), "musculação"),
        ]

        # Grid 4 colunas
        cols_med = st.columns(4)
        for i, (icon, lbl, val, ref) in enumerate(medias):
            with cols_med[i % 4]:
                ref_html = (f'<div style="font-size:10px;color:{GHOST};margin-top:4px">{ref}</div>'
                            if ref else "")
                st.markdown(
                    f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:9px;'
                    f'padding:14px 14px 12px;margin-bottom:10px;min-height:105px;'
                    f'display:flex;flex-direction:column;justify-content:space-between">'
                    f'<div>'
                    f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
                    f'text-transform:uppercase;color:{GHOST};margin-bottom:6px">{icon} {lbl}</div>'
                    f'<div style="font-size:22px;font-weight:800;color:{TEXT};line-height:1">{val}</div>'
                    f'</div>'
                    f'{ref_html}</div>',
                    unsafe_allow_html=True,
                )

        # ── Linha 1: Passos + Distância ───────────────────────────────────────────
        if not df_hist.empty:
            h1a, h1b = st.columns(2)

            with h1a:
                st.markdown(panel(
                    ptitl("👟 Passos diários") +
                    f'<div id="chart_passos"></div>'
                ), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(barra(df_hist, "passos", CYAN, "Passos"))
                _tl = trend_line(df_hist, "passos", CYAN, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.add_hline(y=META_PASS, line_dash="dash", line_color=GREEN,
                              line_width=1, opacity=0.5,
                              annotation_text=f"Meta {META_PASS:,}",
                              annotation_font_color=GREEN, annotation_font_size=9)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h1b:
                st.markdown(panel(ptitl("📍 Distância (km)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(linha(df_hist, "distancia_km", CYAN, "km", fill=True))
                _tl = trend_line(df_hist, "distancia_km", AMBER, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            # ── Linha 2: Sono ─────────────────────────────────────────────────────────
            h2a, h2b = st.columns(2)

            with h2a:
                st.markdown(panel(ptitl("🌙 Sono total (min)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(barra(df_hist, "sono_total_min", PURPLE, "Total"))
                fig.add_trace(barra(df_hist, "sono_profundo_min", CYAN, "Profundo"))
                _tl_sono = trend_line(df_hist, "sono_total_min", PURPLE, "Tend. Total")
                if _tl_sono: fig.add_trace(_tl_sono)
                fig.add_hline(y=META_SONO, line_dash="dash", line_color=RED,
                              line_width=1, opacity=0.5,
                              annotation_text=f"Meta prof. {META_SONO}min",
                              annotation_font_color=RED, annotation_font_size=9)
                fig.update_layout(**chart_layout(180, show_legend=True),
                                  barmode="overlay",
                                  legend=dict(font=dict(color=GHOST, size=9),
                                              bgcolor="rgba(0,0,0,0)"))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h2b:
                st.markdown(panel(ptitl("💓 HRV · PAI")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(linha(df_hist, "hrv_ms",  GREEN,  "HRV (ms)"))
                fig.add_trace(linha(df_hist, "pai",      AMBER,  "PAI", dash="dot"))
                _tl_hrv = trend_line(df_hist, "hrv_ms", GREEN, "Tend. HRV")
                if _tl_hrv: fig.add_trace(_tl_hrv)
                _tl_pai = trend_line(df_hist, "pai", AMBER, "Tend. PAI")
                if _tl_pai: fig.add_trace(_tl_pai)
                fig.update_layout(**chart_layout(180, show_legend=True),
                                  legend=dict(font=dict(color=GHOST, size=9),
                                              bgcolor="rgba(0,0,0,0)"))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        # ── Linha 3: Nutrição ─────────────────────────────────────────────────────
        if not df_macro_hist.empty:
            h3a, h3b, h3c = st.columns(3)

            with h3a:
                st.markdown(panel(ptitl("🔥 Calorias diárias")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(barra(df_macro_hist, "cal", GREEN, "Calorias"))
                _tl = trend_line(df_macro_hist, "cal", GREEN, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.add_hline(y=TMB, line_dash="dash", line_color=CYAN,
                              line_width=1, opacity=0.5,
                              annotation_text=f"Meta {TMB}",
                              annotation_font_color=CYAN, annotation_font_size=9)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h3b:
                st.markdown(panel(ptitl("🥩 Proteínas diárias (g)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(barra(df_macro_hist, "prot", RED, "Proteínas"))
                _tl = trend_line(df_macro_hist, "prot", RED, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.add_hline(y=META_PROT, line_dash="dash", line_color=CYAN,
                              line_width=1, opacity=0.5,
                              annotation_text=f"Meta {META_PROT}g",
                              annotation_font_color=CYAN, annotation_font_size=9)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h3c:
                st.markdown(panel(ptitl("📉 Déficit Calórico")), unsafe_allow_html=True)
                df_h = df_hist.copy() if not df_hist.empty else pd.DataFrame(columns=["dia", "calorias_gastas"])
                df_m = df_macro_hist.copy() if not df_macro_hist.empty else pd.DataFrame(columns=["dia", "cal"])
                if "calorias_gastas" not in df_h.columns:
                    df_h["calorias_gastas"] = 0.0
                if "cal" not in df_m.columns:
                    df_m["cal"] = 0.0
                df_merged = pd.merge(df_h, df_m, on="dia", how="outer").fillna(0)
                df_merged["deficit"] = (TMB + df_merged["calorias_gastas"]) - df_merged["cal"]
            
                fig = go.Figure()
                fig.add_trace(barra(df_merged, "deficit", PURPLE, "Déficit"))
                _tl = trend_line(df_merged, "deficit", PURPLE, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.add_hline(y=500, line_dash="dash", line_color=CYAN,
                              line_width=1, opacity=0.5,
                              annotation_text="Meta 500",
                              annotation_font_color=CYAN, annotation_font_size=9)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        # ── Linha 4: Musculação (Hevy) ─────────────────────────────────────────────
        if not df_hevy_list.empty:
            h4a, h4b = st.columns(2)
        
            with h4a:
                st.markdown(panel(ptitl("🏋️ Volume de Carga (kg/treino)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_hevy_list["dia"], y=df_hevy_list["volume_kg"],
                    name="Volume", marker_color=GREEN, opacity=0.8,
                    text=df_hevy_list["titulo"],
                    hovertemplate="<b>%{x|%d/%m}</b><br>Treino: %{text}<br>Volume: %{y:,.0f} kg<extra></extra>"
                ))
                _tl_vol = trend_line(df_hevy_list, "volume_kg", GREEN, "Tendência")
                if _tl_vol: fig.add_trace(_tl_vol)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h4b:
                st.markdown(panel(ptitl("⏱️ Duração do Treino (min)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_hevy_list["dia"], y=df_hevy_list["duracao_min"],
                    name="Duração", marker_color=AMBER, opacity=0.8,
                    text=df_hevy_list["titulo"],
                    hovertemplate="<b>%{x|%d/%m}</b><br>Treino: %{text}<br>Duração: %{y} min<extra></extra>"
                ))
                _tl_dur = trend_line(df_hevy_list, "duracao_min", AMBER, "Tendência")
                if _tl_dur: fig.add_trace(_tl_dur)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        # ── Tendências ────────────────────────────────────────────────────────────
        st.markdown(sh_section("Tendências", f"Direção dos indicadores nos últimos {n_dias} dias"), unsafe_allow_html=True)

        # Montar lista de indicadores com badges
        _tend_items = []

        if not df_hist.empty:
            _i_pass, _c_pass, _p_pass = _trend_badge(df_hist, "passos",           higher_is_better=True)
            _i_dist, _c_dist, _p_dist = _trend_badge(df_hist, "distancia_km",     higher_is_better=True)
            _i_sono, _c_sono, _p_sono = _trend_badge(df_hist, "sono_total_min",    higher_is_better=True)
            _i_prof, _c_prof, _p_prof = _trend_badge(df_hist, "sono_profundo_min", higher_is_better=True)
            _i_hrv,  _c_hrv,  _p_hrv  = _trend_badge(df_hist, "hrv_ms",           higher_is_better=True)
            _i_pai,  _c_pai,  _p_pai  = _trend_badge(df_hist, "pai",               higher_is_better=True)
            _tend_items += [
                ("👟", "Passos/dia",       _i_pass, _c_pass, _p_pass, f"média {fmt_val(media(df_hist,'passos'),'',0)}"),
                ("📍", "Distância/dia",    _i_dist, _c_dist, _p_dist, f"média {fmt_val(media(df_hist,'distancia_km'),' km',1)}"),
                ("🌙", "Sono total",       _i_sono, _c_sono, _p_sono, f"média {fmt_val(media(df_hist,'sono_total_min'),' min',0)}"),
                ("💤", "Sono profundo",    _i_prof, _c_prof, _p_prof, f"média {fmt_val(media(df_hist,'sono_profundo_min'),' min',0)}"),
                ("💓", "HRV",             _i_hrv,  _c_hrv,  _p_hrv,  f"média {fmt_val(media(df_hist,'hrv_ms'),' ms',0)}"),
                ("⚡", "PAI",             _i_pai,  _c_pai,  _p_pai,  f"média {fmt_val(media(df_hist,'pai'),'',0)}"),
            ]

        if not df_macro_hist.empty:
            _i_cal,  _c_cal,  _p_cal  = _trend_badge(df_macro_hist, "cal",  higher_is_better=False)
            _i_prot, _c_prot, _p_prot = _trend_badge(df_macro_hist, "prot", higher_is_better=True)
            _i_carb, _c_carb, _p_carb = _trend_badge(df_macro_hist, "carb", higher_is_better=False)
            _i_gord, _c_gord, _p_gord = _trend_badge(df_macro_hist, "gord", higher_is_better=False)
            _tend_items += [
                ("🔥", "Calorias/dia",    _i_cal,  _c_cal,  _p_cal,  f"média {fmt_val(media(df_macro_hist,'cal'),' kcal',0)}"),
                ("🥩", "Proteínas/dia",   _i_prot, _c_prot, _p_prot, f"média {fmt_val(media(df_macro_hist,'prot'),' g',0)}"),
                ("🍞", "Carboidratos",    _i_carb, _c_carb, _p_carb, f"média {fmt_val(media(df_macro_hist,'carb'),' g',0)}"),
                ("🧈", "Gorduras",        _i_gord, _c_gord, _p_gord, f"média {fmt_val(media(df_macro_hist,'gord'),' g',0)}"),
            ]

        if not df_hevy_list.empty:
            _i_vol,  _c_vol,  _p_vol  = _trend_badge(df_hevy_list, "volume_kg",  higher_is_better=True)
            _i_dur,  _c_dur,  _p_dur  = _trend_badge(df_hevy_list, "duracao_min", higher_is_better=True)
            _tend_items += [
                ("🏋️", "Volume/treino",   _i_vol,  _c_vol,  _p_vol,  f"média {fmt_val(media_vol_treino,' kg',0)}"),
                ("⏱️", "Duração/treino",  _i_dur,  _c_dur,  _p_dur,  f"média {fmt_val(media_dur_treino,' min',0)}"),
            ]

        # Renderizar grade de badges de tendência
        if _tend_items:
            _cols_t = st.columns(4)
            for _ti, (icon_t, lbl_t, icon_dir, cor_dir, pct_str, ref_t) in enumerate(_tend_items):
                with _cols_t[_ti % 4]:
                    st.markdown(
                        f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:9px;'
                        f'padding:12px 14px;margin-bottom:10px;min-height:88px;'
                        f'display:flex;flex-direction:column;justify-content:space-between">'
                        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
                        f'text-transform:uppercase;color:{GHOST};margin-bottom:6px">{icon_t} {lbl_t}</div>'
                        f'<div style="display:flex;align-items:center;gap:8px">'
                        f'  <span style="font-size:26px;font-weight:900;color:{cor_dir};line-height:1">{icon_dir}</span>'
                        f'  <span style="font-family:{MONO};font-size:14px;font-weight:700;color:{cor_dir}">{pct_str}</span>'
                        f'</div>'
                        f'<div style="font-size:10px;color:{GHOST};margin-top:4px">{ref_t}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                f'<div style="font-family:{MONO};font-size:11px;color:{MUTED};padding:16px;'
                f'text-align:center">Dados insuficientes para calcular tendências neste período</div>',
                unsafe_allow_html=True,
            )

    else:
        st.markdown(
        panel(f'<p style="color:{GHOST};font-size:13px;padding:8px 0">'
              f'Ainda sem dados históricos do Amazfit. Rode /sync no bot para começar.</p>'),
        unsafe_allow_html=True,
        )






_fragment_historico()

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO — MEDICAÇÃO (Tirzepatida)
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div id="sec-medicacao"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Medicação", "Tirzepatida · protocolo semanal"), unsafe_allow_html=True)
_render_medicacao_section()

st.markdown('<div id="sec-biometria"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Biometria", "Evolução de medidas"), unsafe_allow_html=True)

if st.button("📏 Nova medida", key="btn_bio_nova", type="primary", use_container_width=True):
    _dialog_bio_nova()

df_bio = _q_biometria()

if not df_bio.empty:
    df_bio = df_bio.sort_values("data_ord", ascending=True)
    COLS_NUM = ["peso","cintura","abdomen","peitoral","quadril",
                "coxa_dir","coxa_esq","panturrilha_dir","panturrilha_esq","biceps_dir","biceps_esq"]
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

    # ── Primitivos de estilo ──────────────────────────────────────────────
    _td  = ("padding:7px 6px;border-bottom:1px solid #0a1020;"
            "text-align:center;vertical-align:middle;")
    _tdr = _td + f"background:rgba(0,212,255,0.06);"

    def cel(val, diff, peso=False, rec=False):
        base = _tdr if rec else _td
        if pd.isna(val):
            return f"<td style='{base}color:{GHOST}'>—</td>"
        fmt  = f"{val:.1f}"
        un   = "kg" if peso else "cm"
        cor  = CYAN if rec else TEXT
        num  = f"<b style='font-size:13px;font-weight:700;color:{cor}'>{fmt}</b>"
        if rec and diff:
            arrow      = "▼" if diff < 0 else "▲"
            diff_color = GREEN if diff < 0 else RED
            delta = (f"<span style='color:{diff_color};font-size:10px;"
                     f"display:block;margin-top:1px;font-weight:600'>"
                     f"{arrow} {abs(diff):.1f}{un}</span>")
            return f"<td style='{base}'>{num}{delta}</td>"
        return f"<td style='{base}'>{num}</td>"

    _th = (f"font-family:{MONO};background:{BG3};color:{MUTED};"
           f"padding:9px 6px;border-bottom:2px solid {BORDER2};"
           f"text-transform:uppercase;font-size:10px;letter-spacing:1.5px;"
           f"text-align:center;white-space:nowrap;font-weight:400")

    def _td_data(row, rec):
        badge = (
            f'<span style="background:{CYAN};color:{BG};font-size:8px;'
            f'font-family:{MONO};font-weight:900;padding:1px 4px;border-radius:2px;'
            f'letter-spacing:1px;margin-left:5px;vertical-align:middle">ATUAL</span>'
            if rec else ""
        )
        left_bdr = f"border-left:2px solid {CYAN};" if rec else ""
        bg       = f"background:rgba(0,212,255,0.06);" if rec else ""
        cor      = CYAN if rec else GHOST
        wt       = "700" if rec else "400"
        return (
            f"<td style='{_td}{bg}{left_bdr}'>"
            f"<span style='font-family:{MONO};font-size:11px;color:{cor};"
            f"font-weight:{wt};white-space:nowrap'>{row['data_fmt']}{badge}</span></td>"
        )

    # colgroup: data fixa + colunas de medida uniformes
    _cg1 = ('<colgroup><col style="width:95px">'
            + '<col style="width:68px">' * 5 + '</colgroup>')
    _cg2 = ('<colgroup><col style="width:95px">'
            + '<col style="width:68px">' * 6 + '</colgroup>')
    _tbl = (f"width:100%;border-collapse:collapse;table-layout:fixed;"
            f"background:{BG2}")

    _bio_tab1, _bio_tab2 = st.tabs(["🏛️ Tronco · Composição", "💪 Membros"])

    # ── Tab 1: Peso + medidas do tronco ──────────────────────────────────
    with _bio_tab1:
        HEADS_T1 = ["Data","Peso","Cintura","Abdômen","Peitoral","Quadril"]
        ths1  = "".join(f"<th style='{_th}'>{h}</th>" for h in HEADS_T1)
        body1 = ""
        for i, (_, row) in enumerate(df_bio.iterrows()):
            rec    = (i == 0)
            body1 += f"<tr>{_td_data(row, rec)}"
            body1 += cel(row["peso"], diffs["peso"], peso=True, rec=rec)
            for c in ["cintura","abdomen","peitoral","quadril"]:
                body1 += cel(row[c], diffs[c], rec=rec)
            body1 += "</tr>"
        st.markdown(
            panel(
                ptitl("Evolução — Tronco & Composição Corporal") +
                f'<div class="sh-table-scroll" style="border-radius:6px;border:1px solid {BORDER}">'
                f'<table style="{_tbl}">{_cg1}'
                f'<thead><tr>{ths1}</tr></thead>'
                f'<tbody>{body1}</tbody></table></div>'
            ),
            unsafe_allow_html=True,
        )

    # ── Tab 2: Membros ────────────────────────────────────────────────────
    with _bio_tab2:
        HEADS_T2 = ["Data","Coxa D","Coxa E","Pant. D","Pant. E","Bíceps D","Bíceps E"]
        ths2  = "".join(f"<th style='{_th}'>{h}</th>" for h in HEADS_T2)
        body2 = ""
        for i, (_, row) in enumerate(df_bio.iterrows()):
            rec    = (i == 0)
            body2 += f"<tr>{_td_data(row, rec)}"
            for c in ["coxa_dir","coxa_esq","panturrilha_dir","panturrilha_esq","biceps_dir","biceps_esq"]:
                body2 += cel(row[c], diffs[c], rec=rec)
            body2 += "</tr>"
        st.markdown(
            panel(
                ptitl("Evolução — Membros") +
                f'<div class="sh-table-scroll" style="border-radius:6px;border:1px solid {BORDER}">'
                f'<table style="{_tbl}">{_cg2}'
                f'<thead><tr>{ths2}</tr></thead>'
                f'<tbody>{body2}</tbody></table></div>'
            ),
            unsafe_allow_html=True,
        )

    if st.button("✏️ Editar medida", key="btn_bio_edit", use_container_width=True):
        _dialog_bio_editar()


# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 6 — EVACUAÇÃO (controle intestinal)
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div id="sec-evacuacao"></div>', unsafe_allow_html=True)
st.markdown(sh_section("Evacuação", "Registro intestinal — intervalo e histórico"), unsafe_allow_html=True)

# ── Busca todos os registros de evacuação ────────────────────────────────────
_ev_df = _q_evacuacoes()

# ── Card de resumo ────────────────────────────────────────────────────────────
if not _ev_df.empty:
    _ev_datas = pd.to_datetime(_ev_df["data_hora"])
    _ev_ultima = _ev_datas.iloc[0]
    _agora_brt = datetime.now(_BR)
    _ev_dias_sem = (_agora_brt - _ev_ultima.replace(tzinfo=_BR)).days
    _ev_horas_sem = int((_agora_brt - _ev_ultima.replace(tzinfo=_BR)).total_seconds() / 3600)

    # Intervalo médio entre evacuações
    if len(_ev_datas) >= 2:
        _ev_diffs = _ev_datas.diff(-1).dropna().abs()
        _ev_media_h = _ev_diffs.mean().total_seconds() / 3600
        _ev_media_dias = _ev_media_h / 24
        _ev_media_txt = f"{_ev_media_dias:.1f} dias"
    else:
        _ev_media_txt = "—"

    _ev_cor_alerta = RED if _ev_dias_sem >= 3 else (AMBER if _ev_dias_sem >= 2 else GREEN)
    _ev_status_txt = (
        f"⚠️ {_ev_dias_sem} dias sem evacuar!" if _ev_dias_sem >= 3
        else f"🟡 {_ev_dias_sem} dia(s) sem evacuar" if _ev_dias_sem >= 2
        else f"✓ Último registro há {_ev_horas_sem}h"
    )

    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:16px">'
        # card última evacuação
        f'<div style="background:{BG2};border:1px solid {_ev_cor_alerta}55;border-top:2px solid {_ev_cor_alerta};'
        f'border-radius:8px;padding:14px 16px;text-align:center">'
        f'<div style="font-family:{MONO};font-size:9px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Última evacuação</div>'
        f'<div style="font-size:22px;font-weight:700;color:{_ev_cor_alerta}">{_ev_dias_sem}d</div>'
        f'<div style="font-family:{MONO};font-size:10px;color:{_ev_cor_alerta};margin-top:4px">{_ev_status_txt}</div>'
        f'</div>'
        # card intervalo médio
        f'<div style="background:{BG2};border:1px solid {BORDER};border-top:2px solid {CYAN};'
        f'border-radius:8px;padding:14px 16px;text-align:center">'
        f'<div style="font-family:{MONO};font-size:9px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Intervalo médio</div>'
        f'<div style="font-size:22px;font-weight:700;color:{CYAN}">{_ev_media_txt}</div>'
        f'<div style="font-family:{MONO};font-size:10px;color:{MUTED};margin-top:4px">entre registros</div>'
        f'</div>'
        # card total de registros
        f'<div style="background:{BG2};border:1px solid {BORDER};border-top:2px solid {PURPLE};'
        f'border-radius:8px;padding:14px 16px;text-align:center">'
        f'<div style="font-family:{MONO};font-size:9px;color:{MUTED};letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">Total registrado</div>'
        f'<div style="font-size:22px;font-weight:700;color:{PURPLE}">{len(_ev_df)}</div>'
        f'<div style="font-family:{MONO};font-size:10px;color:{MUTED};margin-top:4px">evacuações</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        panel(f'<p style="color:{GHOST};font-size:13px;padding:8px 0">'
              f'Nenhum registro ainda. Use o formulário abaixo para começar a monitorar.</p>'),
        unsafe_allow_html=True,
    )

# ── Botão + formulário de novo registro ──────────────────────────────────────
@st.dialog("🚽 Registrar Evacuação")
def _dialog_evacuacao():
    _ESF_OPTS = [
        "🟢 ■□□□□□  0 — Sem esforço · saiu sozinho, muito suave",
        "🟡 ■■□□□□  1 — Esforço normal · saiu sem machucar",
        "🟡 ■■■□□□  2 — Esforço leve+ · acima do normal, não machucou",
        "🟠 ■■■■□□  3 — Esforço grande · dificuldade para sair",
        "🔴 ■■■■■□  4 — Esforço forte · machucou e sangrou",
        "🔴 ■■■■■■  5 — Esforço máximo · não saia, ficou muito tempo no banheiro",
    ]
    with st.form("form_evac_modal", clear_on_submit=True):
        _ec1, _ec2 = st.columns(2)
        with _ec1:
            _evac_data = st.date_input(
                "Data", value=datetime.now(_BR).date(), key="evac_data_modal_input"
            )
        with _ec2:
            _evac_hora = st.time_input(
                "Hora", value=datetime.now(_BR).time().replace(second=0, microsecond=0),
                key="evac_hora_modal_input"
            )
        _evac_esforco_sel = st.selectbox(
            "Intensidade de esforço", _ESF_OPTS, index=0, key="evac_esforco_modal_input"
        )
        _evac_obs = st.text_input(
            "Observação (opcional)", placeholder="Ex: consistência normal, dor abdominal…",
            key="evac_obs_modal_input"
        )
        if st.form_submit_button("💾 SALVAR", use_container_width=True):
            _evac_dt = f"{_evac_data} {_evac_hora}"
            _evac_esforco_val = int(next(c for c in _evac_esforco_sel if c.isdigit()))
            DB.execute(
                "INSERT INTO evacuacoes (data_hora, esforco, observacao) VALUES (?, ?, ?)",
                [_evac_dt, _evac_esforco_val, _evac_obs.strip() or None]
            )
            _invalidate_cache(_q_evacuacoes)
            _notif("Evacuação registrada ✓")
            st.rerun()

if st.button("🚽 REGISTRAR EVACUAÇÃO", key="btn_evac_nova", use_container_width=True):
    _dialog_evacuacao()

# ── Tabela de histórico ───────────────────────────────────────────────────────
_ui_toggle_button(
    "📋 HISTÓRICO DE EVACUAÇÕES ▴",
    "📋 HISTÓRICO DE EVACUAÇÕES ▾",
    "evac_hist_open",
    "btn_evac_hist",
)

if _toggle_key("evac_hist_open") and not _ev_df.empty:
    _ev_show = _ev_df.copy()
    _ev_show["data_hora_fmt"] = pd.to_datetime(_ev_show["data_hora"]).dt.strftime("%d/%m/%Y  %H:%M")
    _ev_show["observacao"] = _ev_show["observacao"].fillna("—")

    # Calcula intervalo desde o registro anterior
    _ev_dts_ord = pd.to_datetime(_ev_show["data_hora"]).reset_index(drop=True)
    _intervalos = []
    for _i in range(len(_ev_dts_ord)):
        if _i < len(_ev_dts_ord) - 1:
            _diff = (_ev_dts_ord[_i] - _ev_dts_ord[_i + 1]).total_seconds() / 3600
            _intervalos.append(f"{_diff / 24:.1f}d ({int(_diff)}h)")
        else:
            _intervalos.append("—")
    _ev_show["intervalo"] = _intervalos

    # Mapa de esforço: cor e rótulo curto
    _ESFORCO_COR_T  = ["#00e676", "#7ed321", "#fde047", "#fbbf24", "#f97316", "#ff6b6b"]
    _ESFORCO_LABEL_T = ["0 · suave", "1 · normal", "2 · leve+", "3 · grande", "4 · sangrou", "5 · máximo"]

    # Renderiza tabela estilizada
    _ev_rows_html = ""
    for _, _row in _ev_show.iterrows():
        _esf = int(_row["esforco"]) if _row["esforco"] is not None and not pd.isna(_row["esforco"]) else 0
        _esf_cor = _ESFORCO_COR_T[min(_esf, 5)]
        _esf_lbl = _ESFORCO_LABEL_T[min(_esf, 5)]
        _pct = _esf / 5 * 100
        _ev_rows_html += (
            f'<tr style="border-bottom:1px solid {BORDER}">'
            f'<td style="padding:8px 12px;font-family:{MONO};font-size:12px;color:{TEXT}">{_row["data_hora_fmt"]}</td>'
            f'<td style="padding:8px 12px;font-family:{MONO};font-size:12px;color:{CYAN};text-align:center">{_row["intervalo"]}</td>'
            f'<td style="padding:6px 12px;min-width:110px">'
            f'<div style="font-family:{MONO};font-size:11px;font-weight:700;color:{_esf_cor};margin-bottom:4px">{_esf_lbl}</div>'
            f'<div style="height:5px;border-radius:3px;background:{BORDER};overflow:hidden">'
            f'<div style="height:100%;width:{_pct:.0f}%;border-radius:3px;'
            f'background:linear-gradient(to right,#00e676,#7ed321,#fde047,#fbbf24,#f97316,#ff6b6b);'
            f'background-size:{100 / (_pct/100) if _pct > 0 else 100:.0f}% 100%"></div>'
            f'</div></td>'
            f'<td style="padding:8px 12px;font-size:12px;color:{MUTED}">{_row["observacao"]}</td>'
            f'</tr>'
        )
    st.markdown(
        f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:8px;overflow:hidden;margin-top:8px">'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="background:{BG3};border-bottom:2px solid {BORDER}">'
        f'<th style="padding:8px 12px;font-family:{MONO};font-size:10px;color:{MUTED};text-align:left;letter-spacing:1px">DATA / HORA</th>'
        f'<th style="padding:8px 12px;font-family:{MONO};font-size:10px;color:{MUTED};text-align:center;letter-spacing:1px">INTERVALO</th>'
        f'<th style="padding:8px 12px;font-family:{MONO};font-size:10px;color:{MUTED};text-align:center;letter-spacing:1px">ESFORÇO</th>'
        f'<th style="padding:8px 12px;font-family:{MONO};font-size:10px;color:{MUTED};text-align:left;letter-spacing:1px">OBSERVAÇÃO</th>'
        f'</tr></thead>'
        f'<tbody>{_ev_rows_html}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True,
    )

    # Botão excluir último registro
    st.markdown("<div style='margin-top:10px'>", unsafe_allow_html=True)
    _evac_del_confirm = st.session_state.get("evac_del_confirm", False)
    if _evac_del_confirm:
        _edc1, _edc2 = st.columns(2)
        with _edc1:
            if st.button("✓ Confirmar exclusão do último", key="evac_del_ok", use_container_width=True):
                _ev_ultimo_id = int(_ev_df["id"].iloc[0])
                DB.execute("DELETE FROM evacuacoes WHERE id=?", [_ev_ultimo_id])
                _invalidate_cache(_q_evacuacoes)
                st.session_state.pop("evac_del_confirm", None)
                _notif("Registro removido ✓")
                st.rerun()
        with _edc2:
            if st.button("✗ Cancelar", key="evac_del_cancel", use_container_width=True):
                st.session_state.pop("evac_del_confirm", None)
                st.rerun()
    else:
        if st.button("🗑️ EXCLUIR ÚLTIMO REGISTRO", key="evac_del_btn", use_container_width=True):
            st.session_state["evac_del_confirm"] = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO — IA COACH
# ════════════════════════════════════════════════════════════════════════════
_render_ia_coach()

# ── Barra rápida mobile (rodapé — oculta no desktop) ─────────────────────────
render_mobile_quick_bar(on_dashboard=True)

# ════════════════════════════════════════════════════════════════════════════
# RODAPÉ
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div style="text-align:center;padding:20px 0 6px;border-top:1px solid {BORDER2};margin-top:20px">'
    f'<span style="font-family:{MONO};font-size:9px;color:{GHOST};letter-spacing:2px;text-transform:uppercase">'
    f'sys.health_tracker · leandro r. · rio de janeiro · {_APP_BUILD}</span></div>',
    unsafe_allow_html=True,
)
