import streamlit as st
import os, pandas as pd, re, json
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime
from zoneinfo import ZoneInfo

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
    initial_sidebar_state="collapsed",
)

# ── RESET STREAMLIT CHROME + SIDEBAR WIDGET THEME ───────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700;800&display=swap');

html,body,.stApp{background:#080c14!important;color:#e8edf5!important;font-family:'DM Sans',sans-serif!important}
.block-container{padding:1.5rem 2rem!important;max-width:1440px!important;margin-left:auto!important;margin-right:auto!important}
#MainMenu,footer,header,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important}
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

/* ── Botão nav ATIVO (primary) — destaque ciano ── */
[data-testid="stBaseButton-primary"]{
  background:rgba(0,212,255,0.10)!important;border:1.5px solid #00d4ff!important;
  color:#00d4ff!important;font-family:'Space Mono',monospace!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:1.5px!important;text-transform:uppercase!important;
  border-radius:8px!important;padding:10px 12px!important;min-height:44px!important;
  box-shadow:0 0 18px rgba(0,212,255,0.18)!important;
  transition:all 0.15s ease!important}
[data-testid="stBaseButton-primary"]:hover{
  background:rgba(0,212,255,0.17)!important;box-shadow:0 0 26px rgba(0,212,255,0.28)!important}

/* ── Sidebar buttons (mantidos) ── */
section[data-testid="stSidebar"] .stButton button{
  background:transparent!important;border:1px solid #1a2035!important;
  color:#e8edf5!important;font-family:'Space Mono',monospace!important;font-size:10px!important;
  font-weight:700!important;letter-spacing:1px!important;text-transform:uppercase!important;
  border-radius:4px!important;padding:8px 10px!important;width:100%!important;
  min-height:44px!important;transition:all 0.15s ease!important;text-align:left!important}
section[data-testid="stSidebar"] .stButton button:hover{
  border-color:#00d4ff!important;color:#00d4ff!important;
  background:rgba(0,212,255,0.04)!important}
section[data-testid="stSidebar"] .stButton button:active{
  background:rgba(0,212,255,0.08)!important}

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

/* Mobile hint: oculto por padrão */
.sh-mobile-hint{display:none!important}

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
@media(max-width:680px){
  .block-container{padding:0.75rem!important}
  .sh-mobile-hint{display:flex!important}
  .sh-supp-grid{grid-template-columns:repeat(3,1fr)!important}
  [data-testid="stHorizontalBlock"]>[data-testid="column"]{
    flex:1 1 calc(50% - 10px)!important}
  .sh-topbar{flex-direction:column!important;gap:8px!important;align-items:flex-start!important}
  .sh-topbar-right{text-align:left!important}
  [data-testid="collapsedControl"]{
    position:fixed!important;bottom:22px!important;right:18px!important;
    top:auto!important;left:auto!important;
    width:52px!important;height:52px!important;border-radius:50%!important;
    background:#080e1a!important;border:1.5px solid #00d4ff!important;
    box-shadow:0 0 20px rgba(0,212,255,.4),0 4px 18px rgba(0,0,0,.7)!important;
    display:flex!important;align-items:center!important;justify-content:center!important;
    z-index:9999!important}
  [data-testid="collapsedControl"] svg{
    color:#00d4ff!important;fill:#00d4ff!important;
    width:22px!important;height:22px!important}
  section[data-testid="stSidebar"]{width:100vw!important;max-width:340px!important}}
@media(max-width:400px){
  [data-testid="stHorizontalBlock"]>[data-testid="column"]{flex:1 1 100%!important}
  .sh-supp-grid{grid-template-columns:repeat(2,1fr)!important}}
</style>
""", unsafe_allow_html=True)

# ── JS: detecta largura via st.html (sem iframe filho) ───────────────────────
st.html("""
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
""")

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
        f'<span style="font-size:13px;color:{GHOST}">{titulo}</span>'
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

# ── NOTIFICAÇÕES VISUAIS ─────────────────────────────────────────────────────
def _notif(msg: str, tipo: str = "ok"):
    """
    Agenda uma notificação animada para ser exibida no próximo render.
    tipo: 'ok' (verde) | 'err' (vermelho) | 'info' (ciano)
    """
    st.session_state["_notif_pending"] = (msg, tipo)


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


# ── ZEPP SYNC ─────────────────────────────────────────────────────────────────
def _zepp_sync_dashboard(day: str | None = None) -> str:
    """
    Chama zepp_sync + salva no banco. Retorna mensagem de status.
    Precisa de ZEPP_APP_TOKEN e ZEPP_USER_ID nos secrets.
    """
    try:
        import zepp_sync as _zs
        d = day or datetime.now(_BR).strftime("%Y-%m-%d")
        row = _zs.zepp_sync(d)
        if row:
            _zs.save(row)
            return f"Amazfit sincronizado — {row['passos']:,} passos · {row['sono_total_min']} min sono"
        return "Zepp: sem dados novos"
    except Exception as e:
        return f"Erro sync: {e}"


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

# ── DADOS ────────────────────────────────────────────────────────────────────
_dp = db("SELECT peso FROM medidas WHERE peso IS NOT NULL ORDER BY date(data) DESC LIMIT 1")
_dp_val = _dp["peso"].iloc[0] if not _dp.empty else None
peso = float(_dp_val) if _dp_val is not None else 93.0

_da = db(f"SELECT COALESCE(SUM(quantidade_ml),0) as t FROM agua WHERE date(data_hora,'localtime')='{hoje_sql}'")
agua_l = float(_da["t"].iloc[0] or 0) / 1000

_dr = db(
    f"SELECT COALESCE(SUM(calorias),0) as cal, COALESCE(SUM(proteinas),0) as prot,"
    f"COALESCE(SUM(carboidratos),0) as carb, COALESCE(SUM(gorduras),0) as gord "
    f"FROM refeicoes WHERE date(data_hora,'localtime')='{hoje_sql}'"
)
cal_h  = float(_dr["cal"].iloc[0]  or 0)
prot_h = float(_dr["prot"].iloc[0] or 0)
carb_h = float(_dr["carb"].iloc[0] or 0)
gord_h = float(_dr["gord"].iloc[0] or 0)

# Garante que as tabelas existem (Supabase ou SQLite)
DB.init_tables()

_az = db("SELECT * FROM amazfit_dados ORDER BY date(data_hora) DESC LIMIT 1")
passos    = int(_az["passos"].iloc[0])            if not _az.empty else 0
cal_gasta = int(_az["calorias_gastas"].iloc[0])   if not _az.empty else 0
dist_km   = float(_az["distancia_km"].iloc[0])    if not _az.empty else 0.0
sono_tot  = int(_az["sono_total_min"].iloc[0])    if not _az.empty else 0
sono_prof = int(_az["sono_profundo_min"].iloc[0]) if not _az.empty else 0
hrv       = int(_az["hrv_ms"].iloc[0])            if not _az.empty else 0
pai       = int(_az["pai"].iloc[0])               if not _az.empty else 0

# Derivações — Método Dinâmico
gasto_total_dia   = TMB + cal_gasta                    # TMB + atividade registrada
meta_cal_dinamica = gasto_total_dia - 500              # déficit fixo de 500 kcal/dia
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
restam    = int(meta_cal_dinamica - cal_h)             # quanto ainda pode comer
rc_cor    = GREEN if restam > 0 else RED

# ════════════════════════════════════════════════════════════════════════════
# CONSTANTES DO PAINEL
# ════════════════════════════════════════════════════════════════════════════
CATEGORIAS = [
    "Café da Manhã", "Lanche da Manhã", "Almoço",
    "Lanche da Tarde", "Jantar", "Lanche da Noite",
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


def _analisar_texto_macros(descricao: str) -> dict:
    """Usa Gemini para estimar macros de uma descrição textual."""
    cat      = _cat_hora()
    hora_txt = datetime.now(_BR).strftime("%H:%M")
    prompt = (
        f"Você é um nutricionista registrado. Estime os macronutrientes para: '{descricao}'.\n"
        f"Hora atual: {hora_txt} (Brasília). Categoria sugerida: {cat}.\n\n"
        "IMPORTANTE: Responda SOMENTE com o JSON abaixo, sem nenhum texto antes ou depois, "
        "sem markdown, sem explicações:\n"
        '{"categoria":"<cat>","descricao_resumida":"<nome normalizado e porção estimada>",'
        '"calorias":<numero inteiro>,"proteinas":<numero decimal>,'
        '"carboidratos":<numero decimal>,"gorduras":<numero decimal>}\n\n'
        "Regras:\n"
        "- Use valores realistas das tabelas nutricionais brasileiras (TACO/IBGE).\n"
        "- Se a descricao incluir quantidade (ex: 6 conchas, 200g, 1 prato), use essa quantidade para calcular.\n"
        "- Se houver multiplos alimentos (virgula ou +), some os macros e descreva tudo na descricao.\n"
        "- Numeros devem ser decimais com ponto (nao virgula). Ex: 12.5 nao 12,5"
    )
    vision = _gemini_model()
    resp   = vision.generate_content(prompt)
    return _extrair_json(resp.text)


def _analisar_foto_gemini(uploaded_file):
    """Envia foto para Gemini Vision e retorna lista de itens de refeição."""
    import PIL.Image, io
    foto_bytes = uploaded_file.read()
    img        = PIL.Image.open(io.BytesIO(foto_bytes))
    cat        = _cat_hora()
    agora_txt  = datetime.now(_BR).strftime("%H:%M")
    prompt = (
        f"Você é um nutricionista. Analise esta foto e estime macronutrientes.\n"
        f"Hora: {agora_txt} (Brasília). Categoria sugerida: {cat}.\n\n"
        "IMPORTANTE: Responda SOMENTE com o JSON abaixo, sem texto antes ou depois, "
        "sem markdown, sem explicações.\n\n"
        "Para um único prato:\n"
        '{"tipo":"refeicao","categoria":"<cat>","descricao_resumida":"<nome e porção estimada>",'
        '"calorias":<int>,"proteinas":<decimal>,"carboidratos":<decimal>,"gorduras":<decimal>}\n\n'
        "Para múltiplos alimentos distintos, retorne uma lista JSON:\n"
        '[{"tipo":"refeicao","categoria":"<cat>","descricao_resumida":"<item>",'
        '"calorias":<int>,"proteinas":<decimal>,"carboidratos":<decimal>,"gorduras":<decimal>},...]\n\n'
        "Numeros devem usar ponto decimal (nao virgula). Seja realista com as porcoes visiveis."
    )
    vision = _gemini_model()
    resp   = vision.generate_content([prompt, img])
    dados  = _extrair_json(resp.text)
    if isinstance(dados, dict):
        dados = [dados]
    return dados


def _painel_entrada():
    """Nav bar colapsável com session_state — sem tabs."""
    PAINEIS = [
        ("➕", "Refeição",    "refeicao"),
        ("💊", "Suplem.",     "suplemento"),
        ("💧", "Água / Peso", "agua"),
        ("✏️", "Editar",      "editar"),
    ]
    atual = st.session_state.get("painel_aberto", None)

    # ── Barra de navegação ────────────────────────────────────────────────────
    _nav_cols = st.columns([1, 1, 1, 1, 0.28])
    for i, (icon, label, key) in enumerate(PAINEIS):
        with _nav_cols[i]:
            ativo = (atual == key)
            lbl   = f"{icon}  {label}" + ("  ▲" if ativo else "")
            if st.button(lbl, key=f"nav_{key}", width="stretch",
                         type="primary" if ativo else "secondary"):
                st.session_state["painel_aberto"] = None if ativo else key
                st.rerun()
    with _nav_cols[4]:
        if atual:
            if st.button("✕", key="nav_fechar", width="stretch"):
                st.session_state["painel_aberto"] = None
                st.rerun()

    # ── Conteúdo do painel ativo ──────────────────────────────────────────────
    if atual is None:
        return  # nada aberto → dashboard renderiza normalmente

    with st.container(border=True):
        if atual == "refeicao":
            _tab_refeicao()
        elif atual == "suplemento":
            _tab_suplemento()
        elif atual == "agua":
            _tab_agua()
        elif atual == "editar":
            _tab_editar()


def _tab_refeicao():
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
            st.markdown(
                f'<div style="background:rgba(0,212,255,0.07);border:1px solid rgba(0,212,255,0.22);'
                f'border-radius:6px;padding:10px 14px;margin:6px 0">'
                f'<div style="font-size:13px;font-weight:600;color:{TEXT}">'
                f'{item.get("descricao_resumida","")}</div>'
                f'<div style="font-size:11px;color:{MUTED};margin-top:5px">'
                f'🔥 {item.get("calorias",0)} kcal &nbsp;·&nbsp; '
                f'🥩 {item.get("proteinas",0)}g prot &nbsp;·&nbsp; '
                f'🌾 {item.get("carboidratos",0)}g carb &nbsp;·&nbsp; '
                f'🫒 {item.get("gorduras",0)}g gord</div>'
                f'<div style="font-size:10px;color:{CYAN};margin-top:3px;font-family:{MONO}">'
                f'{item.get("categoria","")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        cs, cd = st.columns(2)
        with cs:
            if st.button("✅ Salvar tudo", key="salvar_foto", width="stretch"):
                for item in itens:
                    DB.execute(
                        "INSERT INTO refeicoes "
                        "(categoria,descricao,calorias,proteinas,carboidratos,gorduras) "
                        "VALUES (?,?,?,?,?,?)",
                        [item.get("categoria", "Lanche"),
                         item.get("descricao_resumida", ""),
                         item.get("calorias", 0), item.get("proteinas", 0),
                         item.get("carboidratos", 0), item.get("gorduras", 0)],
                    )
                del st.session_state["foto_resultado"]
                st.cache_data.clear()
                _notif("Foto registrada com sucesso!")
                st.rerun()
        with cd:
            if st.button("✗ Descartar", key="desc_foto", width="stretch"):
                del st.session_state["foto_resultado"]
                st.rerun()

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
        st.markdown(
            f'<div style="background:rgba(0,230,118,0.07);border:1px solid rgba(0,230,118,0.22);'
            f'border-radius:6px;padding:10px 14px;margin:6px 0">'
            f'<div style="font-size:13px;font-weight:600;color:{TEXT}">'
            f'{r.get("descricao_resumida","")}</div>'
            f'<div style="font-size:11px;color:{MUTED};margin-top:5px">'
            f'🔥 {r.get("calorias",0)} kcal &nbsp;·&nbsp; '
            f'🥩 {r.get("proteinas",0)}g prot &nbsp;·&nbsp; '
            f'🌾 {r.get("carboidratos",0)}g carb &nbsp;·&nbsp; '
            f'🫒 {r.get("gorduras",0)}g gord</div>'
            f'<div style="font-size:10px;color:{GREEN};margin-top:3px;font-family:{MONO}">'
            f'{r.get("categoria","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        cs2, cd2 = st.columns(2)
        with cs2:
            if st.button("✅ Salvar", key="salvar_ia_text", width="stretch"):
                DB.execute(
                    "INSERT INTO refeicoes "
                    "(categoria,descricao,calorias,proteinas,carboidratos,gorduras) "
                    "VALUES (?,?,?,?,?,?)",
                    [r.get("categoria", "Lanche"), r.get("descricao_resumida", ""),
                     r.get("calorias", 0), r.get("proteinas", 0),
                     r.get("carboidratos", 0), r.get("gorduras", 0)],
                )
                del st.session_state["ia_text_result"]
                st.cache_data.clear()
                _notif(f"Refeicao salva · {r.get('calorias',0)} kcal")
                st.rerun()
        with cd2:
            if st.button("✗ Descartar", key="desc_ia_text", width="stretch"):
                del st.session_state["ia_text_result"]
                st.rerun()

    st.markdown(
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};'
        f'letter-spacing:1.5px;text-align:center;margin:14px 0 6px">'
        f'── OU PREENCHA MANUALMENTE ──</div>',
        unsafe_allow_html=True,
    )

    # ── Form manual ──────────────────────────────────────────────────────────
    with st.form("form_add_refeicao", clear_on_submit=True):
        cat_sel = st.selectbox("Categoria", CATEGORIAS)
        desc_in = st.text_input("Descrição do alimento")
        c1, c2  = st.columns(2)
        with c1:
            kcal_in = st.number_input("Kcal", min_value=0.0, step=1.0, format="%.0f")
            carb_in = st.number_input("Carb (g)", min_value=0.0, step=0.5, format="%.1f")
        with c2:
            prot_in = st.number_input("Prot (g)", min_value=0.0, step=0.5, format="%.1f")
            gord_in = st.number_input("Gord (g)", min_value=0.0, step=0.5, format="%.1f")
        if st.form_submit_button("SALVAR REFEIÇÃO", width="stretch"):
            if desc_in.strip():
                DB.execute(
                    "INSERT INTO refeicoes "
                    "(categoria,descricao,calorias,proteinas,carboidratos,gorduras) "
                    "VALUES (?,?,?,?,?,?)",
                    [cat_sel, desc_in.strip(), kcal_in, prot_in, carb_in, gord_in],
                )
                st.cache_data.clear()
                _notif(f"Refeicao salva · {int(kcal_in)} kcal")
                st.rerun()
            else:
                st.error("Descrição obrigatória.")

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
                "(categoria,descricao,calorias,proteinas,carboidratos,gorduras) "
                "VALUES (?,?,?,?,?,?)",
                [cat_agora, desc_s, kcal_s, prot_s, carb_s, gord_s],
            )
        for label, *_ in _sel_supps:
            if f"chk_supp_{label}" in st.session_state:
                del st.session_state[f"chk_supp_{label}"]
        nomes = " + ".join(l for l, *_ in _sel_supps)
        st.cache_data.clear()
        _notif(f"{nomes} registrado(s)!")
        st.rerun()


def _tab_agua():
    if st.session_state.pop("_agua_meta_atingida", False):
        st.balloons()

    def _reg_agua(ml: int):
        DB.execute("INSERT INTO agua (quantidade_ml) VALUES (?)", [ml])
        st.cache_data.clear()
        nova = agua_l + ml / 1000
        if nova >= META_AGUA and agua_l < META_AGUA:
            st.session_state["_agua_meta_atingida"] = True
            _notif(f"META DE AGUA ATINGIDA!  {nova:.1f}L", "ok")
        else:
            _notif(f"+{ml} ml  |  {nova:.1f} / {META_AGUA}L", "info")
        st.rerun()

    cA, cB, cC = st.columns(3)
    with cA:
        st.markdown(f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">💧 Água · {agua_l:.1f}L / {META_AGUA}L</div>', unsafe_allow_html=True)
        wa1, wa2 = st.columns(2)
        with wa1:
            if st.button("+ 200ml", key="agua_200", width="stretch"): _reg_agua(200)
            if st.button("+ 500ml", key="agua_500", width="stretch"): _reg_agua(500)
        with wa2:
            if st.button("+ 350ml", key="agua_350", width="stretch"): _reg_agua(350)
            if st.button("+ 750ml", key="agua_750", width="stretch"): _reg_agua(750)
        with st.form("form_agua_custom", clear_on_submit=True):
            ml_in = st.number_input("Outro (ml)", min_value=50, max_value=2000, value=300, step=50)
            if st.form_submit_button("+ Registrar", width="stretch"):
                DB.execute("INSERT INTO agua (quantidade_ml) VALUES (?)", [int(ml_in)])
                nova = agua_l + int(ml_in) / 1000
                st.cache_data.clear()
                if nova >= META_AGUA and agua_l < META_AGUA:
                    st.session_state["_agua_meta_atingida"] = True
                _notif(f"+{int(ml_in)} ml  |  {nova:.1f} / {META_AGUA}L", "info")
                st.rerun()
    with cB:
        st.markdown(f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">⚖️ Peso de hoje</div>', unsafe_allow_html=True)
        with st.form("form_peso_hoje"):
            peso_in = st.number_input("kg", min_value=40.0, max_value=200.0, value=round(peso,1), step=0.1, format="%.1f")
            if st.form_submit_button("SALVAR", width="stretch"):
                _ex = DB.query("SELECT id FROM medidas WHERE date(data)=?", [hoje_sql])
                if not _ex.empty:
                    DB.execute("UPDATE medidas SET peso=? WHERE date(data)=?", [float(peso_in), hoje_sql])
                else:
                    DB.execute("INSERT INTO medidas (data, peso) VALUES (?, ?)", [hoje_sql, float(peso_in)])
                st.cache_data.clear(); _notif(f"Peso {peso_in:.1f} kg salvo"); st.rerun()
    with cC:
        st.markdown(f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">💓 HRV / PAI</div>', unsafe_allow_html=True)
        with st.form("form_hrv_pai"):
            hrv_in = st.number_input("HRV (ms)", min_value=0, max_value=200, value=int(hrv) if hrv else 0, step=1)
            pai_in = st.number_input("PAI", min_value=0, max_value=300, value=int(pai) if pai else 0, step=1)
            if st.form_submit_button("SALVAR", width="stretch"):
                DB.execute("INSERT INTO amazfit_dados (data_hora,passos,calorias_gastas,distancia_km,sono_total_min,sono_profundo_min,hrv_ms,pai) VALUES (?,0,0,0,0,0,0,0) ON CONFLICT(data_hora) DO NOTHING", [f"{hoje_sql} 00:00:00"])
                DB.execute("UPDATE amazfit_dados SET hrv_ms=?, pai=? WHERE data_hora=?", [hrv_in, pai_in, f"{hoje_sql} 00:00:00"])
                hrv_status = "BOM" if hrv_in >= 35 else ("MED" if hrv_in >= 25 else "BAIXO")
                st.cache_data.clear()
                _notif(f"HRV {hrv_in}ms [{hrv_status}]  PAI {pai_in}", "info")
                st.rerun()


def _tab_editar():
    df_edit = DB.query(
        "SELECT id, COALESCE(categoria,'Lanche') as cat, descricao, "
        "time(datetime(data_hora,'localtime')) as hora "
        "FROM refeicoes WHERE date(data_hora,'localtime')=? "
        "ORDER BY data_hora DESC LIMIT 15",
        [hoje_sql],
    )
    if df_edit.empty:
        st.markdown(f'<p style="color:{GHOST};font-size:12px;margin-top:8px">Nenhuma refeição registrada hoje.</p>', unsafe_allow_html=True)
    else:
        for _, row in df_edit.iterrows():
            rid  = int(row["id"])
            hora = str(row["hora"])[:5]
            nome = str(row["descricao"])[:32]
            st.markdown(f'<div style="font-size:9px;color:{GHOST};margin:10px 0 4px;font-family:{MONO};border-top:1px solid #111c2e;padding-top:8px">{hora} — {nome}</div>', unsafe_allow_html=True)
            with st.form(f"edit_ref_{rid}"):
                idx = CATEGORIAS.index(row["cat"]) if row["cat"] in CATEGORIAS else 0
                nova_cat = st.selectbox("Categoria", CATEGORIAS, index=idx, key=f"sel_{rid}")
                ba, bd = st.columns([3, 1])
                with ba: atualizar = st.form_submit_button("✓ ATUALIZAR", width="stretch")
                with bd: deletar   = st.form_submit_button("🗑", width="stretch")
                if atualizar:
                    DB.execute("UPDATE refeicoes SET categoria=? WHERE id=?", [nova_cat, rid])
                    st.cache_data.clear(); _notif("Categoria atualizada"); st.rerun()
                if deletar:
                    DB.execute("DELETE FROM refeicoes WHERE id=?", [rid])
                    st.cache_data.clear(); _notif("Refeicao removida", "err"); st.rerun()


# ── Auto-sync Zepp na primeira abertura da sessão ────────────────────────────
_zepp_status_txt = "sincronizado"
_zepp_status_cor = GREEN
if "zepp_auto_synced" not in st.session_state:
    st.session_state["zepp_auto_synced"] = True
    _sync_result = _zepp_sync_dashboard(hoje_sql)
    if "passos" in _sync_result:
        DB.init_tables()
        st.cache_data.clear()
    elif "Erro" in _sync_result:
        _zepp_status_txt = "erro de sync"
        _zepp_status_cor = RED
    else:
        _zepp_status_txt = "sem dados novos"
        _zepp_status_cor = AMBER

# ════════════════════════════════════════════════════════════════════════════
# TOPBAR
# ════════════════════════════════════════════════════════════════════════════
_tb_left, _tb_right = st.columns([3, 1])
with _tb_left:
    st.markdown(
        f'<div class="sh-topbar" style="padding-bottom:14px;border-bottom:1px solid {BORDER2};margin-bottom:6px">'
        f'<div style="font-family:{MONO};font-size:12px;letter-spacing:2px;color:{CYAN};text-transform:uppercase">sys.health_tracker</div>'
        f'<div style="font-size:28px;font-weight:800;color:{TEXT};line-height:1;letter-spacing:-0.5px;margin-top:2px">Leandro R.</div>'
        f'<div style="font-size:12px;color:{GHOST};text-transform:uppercase;letter-spacing:1px;margin-top:4px">Rio de Janeiro &nbsp;·&nbsp; Dashboard v2.2</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with _tb_right:
    st.markdown(
        f'<div class="sh-topbar-right" style="text-align:right;padding-bottom:6px;border-bottom:1px solid {BORDER2};margin-bottom:6px">'
        f'<div style="font-family:{MONO};font-size:13px;color:{GHOST}">{dia_sem} · {hoje_pt} · {hora_now}</div>'
        f'<div style="font-family:{MONO};font-size:12px;color:{_zepp_status_cor};font-weight:700;margin-top:3px">'
        f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
        f'background:{_zepp_status_cor};margin-right:5px;vertical-align:middle"></span>'
        f'Amazfit Bip 6 — {_zepp_status_txt}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("🔄 Sync Zepp", key="btn_zepp_sync_top", width="stretch"):
        with st.spinner("Sincronizando Zepp..."):
            _sync_result = _zepp_sync_dashboard(hoje_sql)
        st.cache_data.clear()
        _notif(_sync_result, "ok" if "passos" in _sync_result else "info")
        st.rerun()

# ── Notificação animada pendente (roda UMA vez por ação) ─────────────────────
_render_notif_pendente()

# ── Painel de entrada inline (substituiu sidebar) ────────────────────────────
_painel_entrada()

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1 — NUTRIÇÃO
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Nutrição", "Metas do dia"), unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

def kpi_card(acento, lbl, val, unit, extra=""):
    return panel(
        f'<div style="position:absolute;top:0;left:0;right:0;height:3px;'
        f'border-radius:10px 10px 0 0;background:{acento}"></div>'
        f'<div style="font-family:{MONO};font-size:11px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{MUTED};margin-bottom:10px">{lbl}</div>'
        f'<div><span style="font-size:36px;font-weight:800;color:{TEXT};line-height:1;'
        f'letter-spacing:-1px">{val}</span>'
        f'<span style="font-size:18px;color:{MUTED};margin-left:5px">{unit}</span></div>'
        f'{extra}',
        extra="position:relative;overflow:hidden"
    )

with k1:
    st.markdown(kpi_card(
        CYAN, "Peso atual", f"{peso:.1f}", "kg",
        f'<div style="font-size:14px;font-weight:700;color:{GREEN};margin-top:10px">▼ {115.3 - peso:.1f} kg desde 26/01/2026</div>'
        f'<div style="font-size:13px;color:{MUTED};margin-top:5px">Meta: 83 kg · faltam {peso - 83:.1f} kg</div>',
    ), unsafe_allow_html=True)

with k2:
    pct_cal = cal_h / meta_cal_dinamica if meta_cal_dinamica > 0 else 0
    st.markdown(kpi_card(
        GREEN, "Calorias", f"{int(cal_h):,}", "kcal",
        pbar(pct_cal, GREEN) +
        f'<div style="font-family:{MONO};font-size:13px;color:{MUTED};margin-top:6px">'
        f'{int(pct_cal * 100)}% · restam {restam} kcal</div>'
        f'<div style="font-size:13px;color:{MUTED};margin-top:5px">Meta hoje: {int(meta_cal_dinamica):,} kcal</div>',
    ), unsafe_allow_html=True)

with k3:
    st.markdown(kpi_card(
        RED, "Proteínas", f"{int(prot_h)}", "g",
        pbar(prot_h / META_PROT, RED) +
        f'<div style="font-family:{MONO};font-size:13px;color:{MUTED};margin-top:6px">'
        f'{int(prot_h / META_PROT * 100)}% · meta {META_PROT} g</div>',
    ), unsafe_allow_html=True)

with k4:
    st.markdown(kpi_card(
        PURPLE, "Hidratação", f"{agua_l:.1f}", "L",
        pbar(agua_l / META_AGUA, PURPLE) +
        f'<div style="font-family:{MONO};font-size:13px;color:{MUTED};margin-top:6px">'
        f'{int(agua_l / META_AGUA * 100)}% · meta {META_AGUA} L</div>',
    ), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — AMAZFIT
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Amazfit Bip 6", "Atividade · Recovery · Sono"), unsafe_allow_html=True)

def az_card(icon, lbl, val, unit, extra=""):
    return panel(
        f'<div style="font-size:24px;margin-bottom:8px;text-align:center">{icon}</div>'
        f'<div style="font-family:{MONO};font-size:11px;font-weight:700;letter-spacing:1px;'
        f'text-transform:uppercase;color:{MUTED};margin-bottom:6px;text-align:center">{lbl}</div>'
        f'<div style="font-size:24px;font-weight:800;color:{TEXT};line-height:1;'
        f'text-align:center;letter-spacing:-0.5px">{val}</div>'
        f'<div style="font-size:14px;color:{MUTED};margin-top:5px;text-align:center">{unit}</div>'
        f'{extra}'
    )

a1, a2, a3, a4, a5, a6 = st.columns(6)

with a1:
    pct_p = passos / META_PASS if META_PASS else 0
    st.markdown(az_card(
        "👟", "Passos", f"{passos:,}", f"meta {META_PASS:,}",
        pbar(pct_p, CYAN) +
        f'<div style="font-size:14px;font-weight:700;color:{CYAN};margin-top:7px;text-align:center">'
        f'{int(pct_p * 100)}%</div>',
    ), unsafe_allow_html=True)

with a2:
    st.markdown(az_card(
        "🔥", "Gasto Total", f"{gasto_total_dia:,}", "kcal (TMB + Atividade)",
        f'<div style="font-size:14px;font-weight:700;color:{def_cor};margin-top:7px;text-align:center">'
        f'{def_txt} real</div>'
        f'<div style="font-size:13px;color:{MUTED};margin-top:4px;text-align:center">'
        f'Só atividade: {cal_gasta:,} kcal</div>',
    ), unsafe_allow_html=True)

with a3:
    st.markdown(az_card("📍", "Distância", f"{dist_km:.1f}", "km hoje"),
                unsafe_allow_html=True)

with a4:
    pct_sp = sono_prof / META_SONO if META_SONO else 0
    st.markdown(az_card(
        "🌙", "Sono total", sono_h_fmt, "Sono profundo",
        pbar(pct_sp, sono_cor) +
        f'<div style="font-size:14px;font-weight:700;color:{sono_cor};margin-top:6px;text-align:center">'
        f'{sono_prof} min · meta {META_SONO}</div>',
    ), unsafe_allow_html=True)

with a5:
    pct_hrv = min(1.0, max(0, (hrv - 20) / 60)) if hrv else 0  # escala 20-80ms (range real masculino)
    st.markdown(az_card(
        "💓", "HRV", str(hrv), "ms",
        pbar(pct_hrv, hrv_cor) +
        f'<div style="display:flex;justify-content:space-between;margin-top:3px">'
        f'<span style="font-family:{MONO};font-size:12px;color:{MUTED}">20</span>'
        f'<span style="font-family:{MONO};font-size:12px;color:{MUTED}">{hrv}</span>'
        f'<span style="font-family:{MONO};font-size:12px;color:{MUTED}">80</span></div>'
        f'<div style="font-size:15px;font-weight:700;color:{hrv_cor};margin-top:5px;text-align:center">{hrv_txt}</div>',
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
    df_p = db("SELECT date(data) as dt, peso FROM medidas ORDER BY date(data) ASC")
    if not df_p.empty:
        # Converte dt para string antes de qualquer operação
        df_p["dt"] = df_p["dt"].apply(lambda x: str(x)[:10] if x else "")
        # Adiciona ponto inicial se não existir
        ponto_inicial = pd.DataFrame([{"dt": "2026-01-26", "peso": 115.3}])
        df_p = pd.concat([ponto_inicial, df_p]).drop_duplicates("dt").sort_values("dt").reset_index(drop=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_p["dt"], y=df_p["peso"], mode="lines+markers",
            line=dict(color=CYAN, width=2),
            marker=dict(size=7, color=CYAN, line=dict(color=BG, width=1.5)),
            fill="tozeroy", fillcolor="rgba(0,212,255,0.04)",
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>%{y} kg<extra></extra>",
        ))
        # Marca ponto inicial
        fig.add_trace(go.Scatter(
            x=["2026-01-26"], y=[115.3], mode="markers+text",
            marker=dict(size=10, color=RED, symbol="star"),
            text=["Início 115,3kg"], textposition="top right",
            textfont=dict(color=RED, size=10),
            hovertemplate="<b>Início</b><br>115,3 kg<extra></extra>",
            showlegend=False,
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
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

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
    # ── Seletor de data para histórico ────────────────────────────────────────
    from datetime import date as _date
    _hist_sel = st.date_input(
        "📅 Consultar dia",
        value=_date.fromisoformat(hoje_sql),
        max_value=_date.fromisoformat(hoje_sql),
        key="ref_hist_date",
        label_visibility="collapsed",
        format="DD/MM/YYYY",
    )
    _hist_sql = _hist_sel.strftime("%Y-%m-%d")
    _is_hoje = _hist_sql == hoje_sql
    _titulo_ref = "Refeições de hoje" if _is_hoje else f"Refeições de {_hist_sel.strftime('%d/%m')}"

    df_ref_hoje = db(
        "SELECT time(datetime(data_hora,'localtime')) as hora, "
        "COALESCE(categoria,'Lanche') as cat, descricao as alimento, "
        "COALESCE(calorias,0) as kcal, COALESCE(proteinas,0) as prot, "
        "COALESCE(carboidratos,0) as carb, COALESCE(gorduras,0) as gord "
        "FROM refeicoes WHERE date(data_hora,'localtime')=? "
        "ORDER BY data_hora DESC LIMIT 20",
        [_hist_sql],
    )
    rows = ""
    if not df_ref_hoje.empty:
        for _, r in df_ref_hoje.iterrows():
            bsty = BADGE_STYLE.get(r["cat"], BADGE_STYLE["Lanche"])
            kcal_v = int(r["kcal"]) if r["kcal"] else 0
            prot_v = float(r["prot"]) if r["prot"] else 0
            carb_v = float(r["carb"]) if r["carb"] else 0
            gord_v = float(r["gord"]) if r["gord"] else 0
            # Só mostra linha de macros se houver algum valor
            macro_html = ""
            if kcal_v or prot_v or carb_v or gord_v:
                macro_html = (
                    f'<div style="font-size:10px;color:{GHOST};margin-top:3px;'
                    f'font-family:{MONO};letter-spacing:0.5px">'
                    f'🔥<b style="color:{AMBER}">{kcal_v}</b> kcal&nbsp;'
                    f'🥩<b style="color:{GREEN}">{prot_v:.0f}</b>g&nbsp;'
                    f'🌾<b style="color:{CYAN}">{carb_v:.0f}</b>g&nbsp;'
                    f'🫒<b style="color:{PURPLE}">{gord_v:.0f}</b>g'
                    f'</div>'
                )
            rows += (
                f'<div style="padding:8px 0;border-bottom:1px solid {BG3}">'
                f'<div style="display:flex;align-items:center;gap:9px">'
                f'<span style="font-family:{MONO};font-size:12px;font-weight:700;'
                f'color:{CYAN};min-width:36px">{str(r["hora"])[:5]}</span>'
                f'<span style="font-size:9px;font-weight:700;letter-spacing:1px;'
                f'text-transform:uppercase;padding:2px 7px;border-radius:3px;'
                f'white-space:nowrap;{bsty}">{r["cat"]}</span>'
                f'<span style="font-size:13px;color:{MUTED};flex:1;overflow:hidden;'
                f'text-overflow:ellipsis;white-space:nowrap">{r["alimento"]}</span>'
                f'</div>'
                f'{macro_html}'
                f'</div>'
            )
    else:
        rows = f'<p style="color:{GHOST};font-size:12px;margin-top:8px">Nenhuma refeição registrada neste dia.</p>'

    st.markdown(panel(ptitl(_titulo_ref) + rows), unsafe_allow_html=True)

# Busca refeições de hoje para checar suplementos registrados
df_supp_check = db(
    "SELECT descricao, COUNT(*) as qtd FROM refeicoes "
    "WHERE date(data_hora,'localtime')=? "
    "GROUP BY descricao",
    [hoje_sql],
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
            f'<div class="sh-supp-grid" style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px">{cards}</div>'
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
               MAX(biceps_dir)      as biceps_dir,
               MAX(biceps_esq)      as biceps_esq
        FROM medidas
        WHERE peso IS NOT NULL OR cintura IS NOT NULL OR coxa_dir IS NOT NULL
        GROUP BY date(data)
        ORDER BY date(data) ASC
    """)

    if not df_bio.empty:
        df_bio = df_bio.sort_values("data_ord", ascending=True)
        COLS_NUM = ["peso","cintura","abdomen","peitoral","quadril",
                    "coxa_dir","coxa_esq","panturrilha_dir","biceps_dir","biceps_esq"]
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
                f'{row["data_fmt"]} <span style="background:{CYAN};color:{BG};font-size:8px;'
                f'font-weight:900;padding:1px 4px;border-radius:2px;margin-left:4px;'
                f'font-family:{MONO};letter-spacing:1px">ATUAL</span>'
                if rec else row["data_fmt"]
            )
            td_data = (
                f"<td style='text-align:left;padding:7px 8px;border-bottom:1px solid #0a1020;"
                f"color:{CYAN if rec else GHOST};font-weight:{'700' if rec else '400'};{row_bg}'>"
                f"{data_val}</td>"
            )
            body += f"<tr>{td_data}"
            body += cel(row["peso"], diffs["peso"], peso=True, rec=rec)
            for c in ["cintura","abdomen","peitoral","quadril",
                      "coxa_dir","coxa_esq","panturrilha_dir","biceps_dir","biceps_esq"]:
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
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with h1b:
        st.markdown(panel(ptitl("📍 Distância (km)")), unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(linha(df_hist, "distancia_km", CYAN, "km", fill=True))
        fig.update_layout(**chart_layout(180))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

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
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with h2b:
        st.markdown(panel(ptitl("💓 HRV · PAI")), unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(linha(df_hist, "hrv_ms",  GREEN,  "HRV (ms)"))
        fig.add_trace(linha(df_hist, "pai",      AMBER,  "PAI", dash="dot"))
        fig.update_layout(**chart_layout(180, show_legend=True),
                          legend=dict(font=dict(color=GHOST, size=9),
                                      bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ── Linha 3: Nutrição ─────────────────────────────────────────────────────
    if not df_macro_hist.empty:
        h3a, h3b = st.columns(2)

        with h3a:
            st.markdown(panel(ptitl("🔥 Calorias diárias")), unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(barra(df_macro_hist, "cal", GREEN, "Calorias"))
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
            fig.add_hline(y=META_PROT, line_dash="dash", line_color=CYAN,
                          line_width=1, opacity=0.5,
                          annotation_text=f"Meta {META_PROT}g",
                          annotation_font_color=CYAN, annotation_font_size=9)
            fig.update_layout(**chart_layout(180))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

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
             f"meta {TMB}"),
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
