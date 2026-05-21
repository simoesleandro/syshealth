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
_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
if _GEMINI_KEY:
    genai.configure(api_key=_GEMINI_KEY)

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
.block-container{padding:1.5rem 2rem!important;max-width:100%!important}
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

/* ── Buttons (regular) ── */
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
_dp = db("SELECT peso FROM medidas ORDER BY date(data) DESC LIMIT 1")
peso = float(_dp["peso"].iloc[0]) if not _dp.empty else 93.0

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


def _analisar_texto_macros(descricao: str) -> dict:
    """Usa Gemini para estimar macros de uma descrição textual."""
    cat      = _cat_hora()
    hora_txt = datetime.now(_BR).strftime("%H:%M")
    prompt = (
        f"Você é um nutricionista. Estime os macronutrientes para: '{descricao}'.\n"
        f"Hora: {hora_txt} (Brasília). Categoria sugerida: {cat}.\n\n"
        "Retorne APENAS JSON puro, sem markdown:\n"
        '{"categoria":"<cat>","descricao_resumida":"<nome normalizado e porção>",'
        '"calorias":<int>,"proteinas":<float>,"carboidratos":<float>,"gorduras":<float>}\n\n'
        "Use valores realistas baseados em tabelas nutricionais brasileiras.\n"
        "Se houver múltiplos alimentos separados por vírgula ou '+', some os macros e descreva tudo."
    )
    vision = genai.GenerativeModel("gemini-2.5-flash")
    resp   = vision.generate_content(prompt)
    return json.loads(re.sub(r"```json|```", "", resp.text).strip())


def _analisar_foto_gemini(uploaded_file):
    """Envia foto para Gemini Vision e retorna lista de itens de refeição."""
    import PIL.Image, io
    foto_bytes = uploaded_file.read()
    img        = PIL.Image.open(io.BytesIO(foto_bytes))
    cat        = _cat_hora()
    agora_txt  = datetime.now(_BR).strftime("%H:%M")
    prompt = (
        f"Você é um nutricionista. Analise esta foto de alimento e estime macronutrientes.\n"
        f"Hora: {agora_txt} (Brasília). Categoria sugerida: {cat}.\n\n"
        "Retorne APENAS JSON puro, sem markdown, sem ```json:\n"
        '{"tipo":"refeicao","categoria":"<cat>","descricao_resumida":"<nome e porção estimada>",'
        '"calorias":<int>,"proteinas":<float>,"carboidratos":<float>,"gorduras":<float>}\n\n'
        "Se houver múltiplos alimentos, retorne lista JSON.\n"
        "Seja realista com as porções visíveis na foto."
    )
    vision = genai.GenerativeModel("gemini-2.5-flash")
    resp   = vision.generate_content([prompt, img])
    dados  = json.loads(re.sub(r"```json|```", "", resp.text).strip())
    if isinstance(dados, dict):
        dados = [dados]
    return dados


def _painel_entrada():
    """Painel de entrada inline — substituiu a sidebar."""
    st.markdown('<div class="sh-painel">', unsafe_allow_html=True)

    # ── Tabs do painel ────────────────────────────────────────────────────────
    tp1, tp2, tp3, tp4 = st.tabs(["➕ Refeição", "💊 Suplem.", "💧 Água · ⚖️ Peso · 💓 HRV", "✏️ Editar"])

    with tp1:
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
                    with st.spinner("IA analisando..."):
                        try:
                            st.session_state["foto_resultado"] = _analisar_foto_gemini(foto_up)
                        except Exception as e:
                            st.error(f"Erro: {e}")

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
                    st.toast("📸 ✓ Foto registrada!")
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
            if desc_ia.strip():
                with st.spinner("IA calculando..."):
                    try:
                        st.session_state["ia_text_result"] = _analisar_texto_macros(desc_ia.strip())
                    except Exception as e:
                        st.error(f"Erro: {e}")
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
                    st.toast("🤖 ✓ Refeição salva pela IA!")
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
                    st.toast("✓ Refeição salva!")
                    st.rerun()
                else:
                    st.error("Descrição obrigatória.")

    with tp2:
        cols_s = st.columns(3)
        for i, (label, desc_s, _cat_s, kcal_s, prot_s, carb_s, gord_s) in enumerate(SUPP_REGISTER):
            with cols_s[i % 3]:
                if st.button(label, key=f"supp_{label}", width="stretch"):
                    DB.execute(
                        "INSERT INTO refeicoes "
                        "(categoria,descricao,calorias,proteinas,carboidratos,gorduras) "
                        "VALUES (?,?,?,?,?,?)",
                        [_cat_hora(), desc_s, kcal_s, prot_s, carb_s, gord_s],
                    )
                    st.cache_data.clear()
                    st.toast(f"✓ {label}")
                    st.rerun()

    with tp3:
        cA, cB, cC = st.columns(3)
        with cA:
            st.markdown(f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">💧 Água · {agua_l:.1f}L / {META_AGUA}L</div>', unsafe_allow_html=True)
            wa1, wa2 = st.columns(2)
            with wa1:
                if st.button("+ 200ml", key="agua_200", width="stretch"): DB.execute("INSERT INTO agua (quantidade_ml) VALUES (?)", [200]); st.cache_data.clear(); st.toast("💧 +200 ml"); st.rerun()
                if st.button("+ 500ml", key="agua_500", width="stretch"): DB.execute("INSERT INTO agua (quantidade_ml) VALUES (?)", [500]); st.cache_data.clear(); st.toast("💧 +500 ml"); st.rerun()
            with wa2:
                if st.button("+ 350ml", key="agua_350", width="stretch"): DB.execute("INSERT INTO agua (quantidade_ml) VALUES (?)", [350]); st.cache_data.clear(); st.toast("💧 +350 ml"); st.rerun()
                if st.button("+ 750ml", key="agua_750", width="stretch"): DB.execute("INSERT INTO agua (quantidade_ml) VALUES (?)", [750]); st.cache_data.clear(); st.toast("💧 +750 ml"); st.rerun()
            with st.form("form_agua_custom", clear_on_submit=True):
                ml_in = st.number_input("Outro (ml)", min_value=50, max_value=2000, value=300, step=50)
                if st.form_submit_button("+ Registrar", width="stretch"):
                    DB.execute("INSERT INTO agua (quantidade_ml) VALUES (?)", [int(ml_in)])
                    st.cache_data.clear(); st.rerun()
        with cB:
            st.markdown(f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">⚖️ Peso de hoje</div>', unsafe_allow_html=True)
            with st.form("form_peso_hoje"):
                peso_in = st.number_input("kg", min_value=40.0, max_value=200.0, value=round(peso,1), step=0.1, format="%.1f")
                if st.form_submit_button("SALVAR", width="stretch"):
                    DB.execute("DELETE FROM medidas WHERE date(data)=? AND cintura IS NULL", [hoje_sql])
                    DB.execute("INSERT INTO medidas (data, peso) VALUES (?, ?)", [hoje_sql, float(peso_in)])
                    st.cache_data.clear(); st.toast(f"⚖️ ✓ {peso_in:.1f} kg"); st.rerun()
        with cC:
            st.markdown(f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px">💓 HRV / PAI</div>', unsafe_allow_html=True)
            with st.form("form_hrv_pai"):
                hrv_in = st.number_input("HRV (ms)", min_value=0, max_value=200, value=int(hrv) if hrv else 0, step=1)
                pai_in = st.number_input("PAI", min_value=0, max_value=300, value=int(pai) if pai else 0, step=1)
                if st.form_submit_button("SALVAR", width="stretch"):
                    DB.execute("INSERT INTO amazfit_dados (data_hora,passos,calorias_gastas,distancia_km,sono_total_min,sono_profundo_min,hrv_ms,pai) VALUES (?,0,0,0,0,0,0,0) ON CONFLICT(data_hora) DO NOTHING", [f"{hoje_sql} 00:00:00"])
                    DB.execute("UPDATE amazfit_dados SET hrv_ms=?, pai=? WHERE data_hora=?", [hrv_in, pai_in, f"{hoje_sql} 00:00:00"])
                    st.cache_data.clear(); st.toast(f"💓 HRV {hrv_in}ms · PAI {pai_in}"); st.rerun()

    with tp4:
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
                        st.cache_data.clear(); st.toast("✓ Categoria atualizada!"); st.rerun()
                    if deletar:
                        DB.execute("DELETE FROM refeicoes WHERE id=?", [rid])
                        st.cache_data.clear(); st.toast("🗑 Refeição removida"); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TOPBAR
# ════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="sh-topbar" style="display:flex;justify-content:space-between;align-items:flex-end;'
    f'padding-bottom:14px;border-bottom:1px solid {BORDER2};margin-bottom:6px">'
    f'<div>'
    f'<div style="font-family:{MONO};font-size:12px;letter-spacing:2px;color:{CYAN};text-transform:uppercase">sys.health_tracker</div>'
    f'<div style="font-size:28px;font-weight:800;color:{TEXT};line-height:1;letter-spacing:-0.5px;margin-top:2px">Leandro R.</div>'
    f'<div style="font-size:12px;color:{GHOST};text-transform:uppercase;letter-spacing:1px;margin-top:4px">Rio de Janeiro &nbsp;·&nbsp; Dashboard v2.1</div>'
    f'</div>'
    f'<div class="sh-topbar-right" style="text-align:right">'
    f'<div style="font-family:{MONO};font-size:13px;color:{GHOST}">{dia_sem} · {hoje_pt} · {hora_now}</div>'
    f'<div style="font-family:{MONO};font-size:13px;color:{GREEN};font-weight:700;margin-top:3px">'
    f'<span style="display:inline-block;width:6px;height:6px;border-radius:50%;'
    f'background:{GREEN};margin-right:5px;vertical-align:middle"></span>'
    f'Amazfit Bip 6 — sincronizado</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

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
    df_ref_hoje = db(
        "SELECT time(datetime(data_hora,'localtime')) as hora, "
        "COALESCE(categoria,'Lanche') as cat, descricao as alimento "
        "FROM refeicoes WHERE date(data_hora,'localtime')=? "
        "ORDER BY data_hora DESC LIMIT 6",
        [hoje_sql],
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
                f'<span style="font-size:14px;color:{MUTED};flex:1">{r["alimento"]}</span>'
                f'</div>'
            )
    else:
        rows = f'<p style="color:{GHOST};font-size:12px;margin-top:8px">Nenhuma refeição registrada hoje.</p>'

    st.markdown(panel(ptitl("Refeições de hoje") + rows), unsafe_allow_html=True)

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
        SELECT date(data) as data_ord, strftime('%d/%m/%Y',data) as data_fmt,
               peso, cintura, abdomen,
               peitoral, quadril,
               coxa_dir, coxa_esq,
               panturrilha_dir, biceps_dir, biceps_esq
        FROM medidas WHERE coxa_dir IS NOT NULL
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
