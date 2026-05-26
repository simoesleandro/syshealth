import streamlit as st
import os, pandas as pd, re, json, requests
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime
from zoneinfo import ZoneInfo
import nutri_engine as NE

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

/* Suaviza o escurecimento durante rerun (padrão Streamlit) */
[data-testid="stApp"][data-stale="true"]{
  opacity:0.75!important;
  transition:opacity 0.15s ease!important}
[data-testid="stApp"]{
  transition:opacity 0.15s ease!important}

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

# ── DADOS — funções com cache (TTL 60s, invalidadas por st.cache_data.clear()) ──

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

@st.cache_data(ttl=60)
def _q_peso_historico():
    return DB.query("SELECT date(data) as dt, peso FROM medidas ORDER BY date(data) ASC")

@st.cache_data(ttl=60)
def _q_medicacao():
    return DB.query(
        "SELECT id, "
        "strftime('%d/%m/%Y', datetime(data_hora,'localtime')) as data_fmt, "
        "date(data_hora,'localtime') as data_iso, "
        "dose_mg FROM medicacao ORDER BY date(data_hora,'localtime') DESC")

@st.cache_data(ttl=60)
def _q_medidas():
    return DB.query(
        "SELECT strftime('%d/%m/%Y',data) as data, "
        "cintura, quadril, peito, braco, coxa FROM medidas "
        "WHERE cintura IS NOT NULL ORDER BY date(data) DESC LIMIT 10")

@st.cache_data(ttl=60)
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
               MAX(biceps_dir)      as biceps_dir,
               MAX(biceps_esq)      as biceps_esq
        FROM medidas
        WHERE peso IS NOT NULL OR cintura IS NOT NULL OR coxa_dir IS NOT NULL
        GROUP BY date(data)
        ORDER BY date(data) ASC
    """)

# Garante que as tabelas existem — UMA vez por sessão
if "db_init_done" not in st.session_state:
    DB.init_tables()
    st.session_state["db_init_done"] = True

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
    st.cache_data.clear()

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

_az       = _q_amazfit()
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
                    "(categoria,descricao,calorias,proteinas,carboidratos,gorduras,componentes_json) "
                    "VALUES (?,?,?,?,?,?,?)",
                    [cat_sel, desc_in.strip(), kcal_in, prot_in, carb_in, gord_in,
                     json.dumps([{
                         "nome": desc_in.strip(),
                         "gramas": 0,
                         "kcal": kcal_in,
                         "prot": prot_in,
                         "carb": carb_in,
                         "gord": gord_in,
                         "fonte": "Manual"
                     }])],
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
    if "passos" in _sync_result or "sincronizado" in _sync_result.lower():
        DB.init_tables()
        st.cache_data.clear()
    elif "Erro" in _sync_result:
        _zepp_status_txt = "erro de sync"
        _zepp_status_cor = RED
    else:
        _zepp_status_txt = "sem dados novos"
        _zepp_status_cor = AMBER

# ── Auto-sync Hevy na primeira abertura da sessão ────────────────────────────
_hevy_status_txt = "sincronizado"
_hevy_status_cor = GREEN
if "hevy_auto_synced" not in st.session_state:
    st.session_state["hevy_auto_synced"] = True
    _h_sync_result = _hevy_sync_dashboard()
    if "sincronizado" in _h_sync_result.lower() or "atualizados" in _h_sync_result.lower():
        st.cache_data.clear()
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
# TOPBAR
# ════════════════════════════════════════════════════════════════════════════
_tb_left, _tb_right = st.columns([3, 1.2])
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
        f'<div style="font-family:{MONO};font-size:11px;color:{_zepp_status_cor};font-weight:700;margin-top:3px">'
        f'<span style="display:inline-block;width:5px;height:5px;border-radius:50%;'
        f'background:{_zepp_status_cor};margin-right:5px;vertical-align:middle"></span>'
        f'Amazfit — {_zepp_status_txt}</div>'
        f'<div style="font-family:{MONO};font-size:11px;color:{_hevy_status_cor};font-weight:700;margin-top:1px">'
        f'<span style="display:inline-block;width:5px;height:5px;border-radius:50%;'
        f'background:{_hevy_status_cor};margin-right:5px;vertical-align:middle"></span>'
        f'Hevy — {_hevy_status_txt}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    col_sync1, col_sync2 = st.columns(2)
    with col_sync1:
        if st.button("🔄 Sync Zepp", key="btn_zepp_sync_top", width="stretch"):
            with st.spinner("Sincronizando Zepp..."):
                _sync_result = _zepp_sync_dashboard(hoje_sql)
            st.cache_data.clear()
            _notif(_sync_result, "ok" if "passos" in _sync_result or "sincronizado" in _sync_result.lower() else "info")
            st.rerun()
    with col_sync2:
        if st.button("💪 Sync Hevy", key="btn_hevy_sync_top", width="stretch"):
            with st.spinner("Sincronizando Hevy..."):
                _h_sync_result = _hevy_sync_dashboard()
            st.cache_data.clear()
            _notif(_h_sync_result, "ok" if "sincronizado" in _h_sync_result.lower() or "atualizados" in _h_sync_result.lower() else "info")
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
    pct_agua = agua_l / META_AGUA
    # Cor dinâmica: roxo sob déficit, ciano ao se aproximar e verde esmeralda ao bater
    cor_agua = "#a78bfa" if pct_agua < 0.50 else ("#00d4ff" if pct_agua < 1.0 else "#00e676")
    badge_agua = "⚠️ Desidratado" if pct_agua < 0.50 else ("⚡ Em Progresso" if pct_agua < 1.0 else "✓ Hidratado")
    
    st.markdown(kpi_card(
        cor_agua, "Hidratação", f"{agua_l:.1f}", "L",
        pbar(pct_agua, cor_agua) +
        f'<div style="font-family:{MONO};font-size:13px;color:{cor_agua};margin-top:6px;font-weight:700">'
        f'{badge_agua} · {int(pct_agua * 100)}%</div>'
        f'<div style="font-size:12px;color:{MUTED};margin-top:3px">Meta: {META_AGUA}L · Faltam {max(0.0, META_AGUA - agua_l):.1f}L</div>',
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

a_col1, a_col2, a_col3, a_col4 = st.columns(4)

with a_col1:
    pct_p = passos / META_PASS if META_PASS else 0
    st.markdown(az_card(
        "👟", "Passos", f"{passos:,}", f"meta {META_PASS:,}",
        pbar(pct_p, CYAN) +
        f'<div style="font-size:14px;font-weight:700;color:{CYAN};margin-top:7px;text-align:center">'
        f'{int(pct_p * 100)}%</div>',
    ), unsafe_allow_html=True)

with a_col2:
    st.markdown(az_card(
        "🔥", "Gasto Total", f"{gasto_total_dia:,}", "kcal (TMB + Atividade)",
        f'<div style="font-size:14px;font-weight:700;color:{def_cor};margin-top:7px;text-align:center">'
        f'{def_txt} real</div>'
        f'<div style="font-size:13px;color:{MUTED};margin-top:4px;text-align:center">'
        f'Só atividade: {cal_gasta:,} kcal</div>',
    ), unsafe_allow_html=True)

with a_col3:
    st.markdown(az_card("📍", "Distância Total", f"{dist_km:.1f}", "km hoje"),
                unsafe_allow_html=True)

with a_col4:
    pct_sp = sono_prof / META_SONO if META_SONO else 0
    st.markdown(az_card(
        "🌙", "Sono total", sono_h_fmt, "Sono profundo",
        pbar(pct_sp, sono_cor) +
        f'<div style="font-size:14px;font-weight:700;color:{sono_cor};margin-top:6px;text-align:center">'
        f'{sono_prof} min · meta {META_SONO}</div>',
    ), unsafe_allow_html=True)

a_col5, a_col6, a_col7, a_col8 = st.columns(4)

with a_col5:
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

with a_col6:
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

with a_col7:
    corrida_info = f'<div style="font-size:14px;font-weight:700;color:{CYAN};margin-top:7px;text-align:center">{corrida_cal} kcal gastas</div>' if corrida_cal > 0 else f'<div style="font-size:13px;color:{MUTED};margin-top:7px;text-align:center">Sem corrida registrada</div>'
    st.markdown(az_card(
        "🏃", "Corrida (Amazfit)", f"{corrida_km:.2f} km", "distância hoje",
        corrida_info
    ), unsafe_allow_html=True)

with a_col8:
    df_hevy_hoje = db("""
        SELECT titulo, duracao_min, volume_kg
        FROM hevy_treinos
        WHERE date(data_hora, 'localtime') = ?
        ORDER BY data_hora DESC LIMIT 1
    """, [hoje_sql])
    if not df_hevy_hoje.empty:
        h_title = df_hevy_hoje["titulo"].iloc[0]
        h_dur = int(df_hevy_hoje["duracao_min"].iloc[0])
        h_vol = float(df_hevy_hoje["volume_kg"].iloc[0])
        hevy_val = f"🏋️ {h_dur} min"
        hevy_extra = (
            f'<div style="font-size:12px;font-weight:700;color:{GREEN};margin-top:6px;text-align:center;text-overflow:ellipsis;overflow:hidden;white-space:nowrap">{h_title}</div>'
            f'<div style="font-size:11px;color:{MUTED};margin-top:2px;text-align:center">Vol: {h_vol:,.0f} kg</div>'
        )
    else:
        df_hevy_last = db("""
            SELECT titulo, date(data_hora, 'localtime') as data_treino, duracao_min, volume_kg
            FROM hevy_treinos
            ORDER BY data_hora DESC LIMIT 1
        """)
        if not df_hevy_last.empty:
            l_title = df_hevy_last["titulo"].iloc[0]
            l_date = df_hevy_last["data_treino"].iloc[0]
            try:
                l_date_fmt = datetime.strptime(l_date, "%Y-%m-%d").strftime("%d/%m")
            except Exception:
                l_date_fmt = l_date
            hevy_val = "Descanso"
            hevy_extra = (
                f'<div style="font-size:11px;color:{MUTED};margin-top:6px;text-align:center">Último: {l_date_fmt}</div>'
                f'<div style="font-size:11px;font-weight:700;color:{TEXT};margin-top:2px;text-align:center;text-overflow:ellipsis;overflow:hidden;white-space:nowrap">{l_title}</div>'
            )
        else:
            hevy_val = "Sem treinos"
            hevy_extra = f'<div style="font-size:11px;color:{MUTED};margin-top:6px;text-align:center">Nenhum treino sincronizado</div>'
    st.markdown(az_card(
        "💪", "Musculação (Hevy)", hevy_val, "volume / tempo",
        hevy_extra
    ), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3 — EVOLUÇÃO
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Evolução", "Peso histórico · Macros do dia"), unsafe_allow_html=True)

c1, c2 = st.columns([2, 1])

with c1:
    df_p = _q_peso_historico()
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

col_m, col_s = st.columns([1.6, 1.4])

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
    _hist_sql   = _hist_sel.strftime("%Y-%m-%d")
    _is_hoje    = _hist_sql == hoje_sql
    _titulo_ref = "Refeições de hoje" if _is_hoje else f"Refeições de {_hist_sel.strftime('%d/%m')}"

    df_ref_hoje = _q_refeicoes(_hist_sql)

    # Mapeamentos de cor e ícone por categoria
    _CAT_COLOR = {
        "Café da Manhã":   CYAN,
        "Lanche da Manhã": PURPLE,
        "Almoço":          GREEN,
        "Lanche da Tarde": PURPLE,
        "Jantar":          RED,
        "Lanche da Noite": PURPLE,
        "Lanche":          MUTED,
    }
    _CAT_ICON = {
        "Café da Manhã":   "☕",
        "Lanche da Manhã": "🍎",
        "Almoço":          "🍽️",
        "Lanche da Tarde": "🥪",
        "Jantar":          "🌙",
        "Lanche da Noite": "🌜",
        "Lanche":          "🥤",
    }

    # Título da seção
    st.markdown(
        f'<div style="font-family:{MONO};font-size:11px;font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;color:{TEXT};'
        f'margin-bottom:8px">{_titulo_ref}</div>',
        unsafe_allow_html=True,
    )

    if df_ref_hoje.empty:
        st.markdown(
            f'<p style="color:{GHOST};font-size:12px;margin-top:4px">'
            f'Nenhuma refeição registrada neste dia.</p>',
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
            icon   = _CAT_ICON.get(cat, "🍴")
            cor    = _CAT_COLOR.get(cat, MUTED)
            bsty   = BADGE_STYLE.get(cat, BADGE_STYLE["Lanche"])

            edit_key = f"meal_edit_{rid}"
            is_editing = st.session_state.get(edit_key, False)

            # ── Card colorido (sempre visível) ────────────────────────────────
            has_macros = kcal_v or prot_v or carb_v or gord_v
            macro_row  = ""
            if has_macros:
                macro_row = (
                    f'<div style="display:flex;gap:14px;flex-wrap:wrap;'
                    f'margin-top:7px;padding-top:7px;border-top:1px solid {cor}22">'
                    f'<span style="font-family:{MONO};font-size:11px;font-weight:700;color:{AMBER}">🔥 {kcal_v}</span>'
                    f'<span style="font-size:11px;color:{MUTED}">🥩<b style="color:{GREEN}"> {prot_v:.0f}g</b></span>'
                    f'<span style="font-size:11px;color:{MUTED}">🌾<b style="color:{CYAN}"> {carb_v:.0f}g</b></span>'
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
                    details_html += f"""
    <div style="background:#070b15;border-radius:4px;padding:3px 8px;display:flex;justify-content:space-between;align-items:center;border:1px solid {cor}11">
      <span style="font-size:11px;color:{TEXT}">{d.get('nome','?')} <span style="color:{MUTED}">{d.get('gramas',0)}g</span></span>
      <span style="font-size:11px;font-family:{MONO};color:{d_cor}">{int(d.get('kcal',0))} kcal</span>
    </div>"""
                details_html += "\n  </div>\n</details>"

            _cc, _ce = st.columns([1, 0.1])
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
                _edit_lbl = "✕" if is_editing else "✏"
                if st.button(_edit_lbl, key=f"tog_meal_{rid}", width="stretch",
                             help="Editar / Fechar"):
                    st.session_state[edit_key] = not is_editing
                    st.rerun()

            # ── Form de edição (só aparece quando aberto) ─────────────────────
            if is_editing:
                with st.container():
                    st.markdown(
                        f'<div style="height:1px;background:{cor}33;margin:0 0 6px 3px"></div>',
                        unsafe_allow_html=True,
                    )
                    with st.form(f"form_edit_ref_{rid}"):
                        _ec, _ed = st.columns([1, 2])
                        with _ec:
                            idx_cat  = CATEGORIAS.index(cat) if cat in CATEGORIAS else 0
                            nova_cat = st.selectbox("Categoria", CATEGORIAS, index=idx_cat,
                                                    key=f"ecat_{rid}")
                        with _ed:
                            nova_desc = st.text_input("Descrição", value=food,
                                                      key=f"edesc_{rid}")
                        _em1, _em2, _em3, _em4 = st.columns(4)
                        with _em1:
                            nova_kcal = st.number_input("Kcal", value=float(kcal_v),
                                                        min_value=0.0, step=1.0, format="%.0f",
                                                        key=f"ekcal_{rid}")
                        with _em2:
                            nova_prot = st.number_input("Prot g", value=prot_v,
                                                        min_value=0.0, step=0.5, format="%.1f",
                                                        key=f"eprot_{rid}")
                        with _em3:
                            nova_carb = st.number_input("Carb g", value=carb_v,
                                                        min_value=0.0, step=0.5, format="%.1f",
                                                        key=f"ecarb_{rid}")
                        with _em4:
                            nova_gord = st.number_input("Gord g", value=gord_v,
                                                        min_value=0.0, step=0.5, format="%.1f",
                                                        key=f"egord_{rid}")
                        _ba, _bd = st.columns([3, 1])
                        with _ba:
                            _salvar  = st.form_submit_button("✓ SALVAR", width="stretch")
                        with _bd:
                            _deletar = st.form_submit_button("🗑", width="stretch")
                        if _salvar:
                            DB.execute(
                                "UPDATE refeicoes SET categoria=?, descricao=?, calorias=?, "
                                "proteinas=?, carboidratos=?, gorduras=? WHERE id=?",
                                [nova_cat, nova_desc.strip(), nova_kcal,
                                 nova_prot, nova_carb, nova_gord, rid],
                            )
                            st.cache_data.clear()
                            st.session_state[edit_key] = False
                            _notif(f"Refeição atualizada · {int(nova_kcal)} kcal")
                            st.rerun()
                        if _deletar:
                            DB.execute("DELETE FROM refeicoes WHERE id=?", [rid])
                            st.cache_data.clear()
                            st.session_state.pop(edit_key, None)
                            _notif("Refeição removida", "err")
                            st.rerun()
                    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

# Busca refeições de hoje para checar suplementos registrados (cached)
df_supp_check = _q_supp_check(hoje_sql)
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

    # ── Suplementação ─────────────────────────────────────────────────────────
    st.markdown(
        panel(
            ptitl("Suplementação do dia") +
            f'<div class="sh-supp-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">{cards}</div>'
        ),
        unsafe_allow_html=True,
    )

    # ── Tirzepatida — timeline colorida ──────────────────────────────────────
    df_med = _q_medicacao()
    from datetime import date as _date, datetime as _datetime

    # Cabeçalho com botão de nova dose
    _th, _tn = st.columns([1, 0.55])
    with _th:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:11px;font-weight:700;'
            f'letter-spacing:1.5px;text-transform:uppercase;color:{TEXT};'
            f'margin:14px 0 8px">💉 Tirzepatida</div>',
            unsafe_allow_html=True,
        )
    with _tn:
        st.markdown('<div style="margin-top:14px"></div>', unsafe_allow_html=True)
        if st.button("＋ Dose", key="btn_med_nova_toggle", width="stretch"):
            st.session_state["med_nova_open"] = not st.session_state.get("med_nova_open", False)
            st.rerun()

    # Form de nova dose (toggle)
    if st.session_state.get("med_nova_open", False):
        with st.container():
            st.markdown(
                f'<div style="border-left:3px solid {GREEN};padding:2px 0 2px 0;'
                f'margin-bottom:6px"></div>',
                unsafe_allow_html=True,
            )
            with st.form("form_med_nova", clear_on_submit=True):
                _mn1, _mn2 = st.columns(2)
                with _mn1:
                    nova_data_n = st.date_input(
                        "Data", value=_date.fromisoformat(hoje_sql),
                        key="mdata_nova", format="DD/MM/YYYY"
                    )
                with _mn2:
                    nova_dose_n = st.number_input(
                        "Dose (mg)", value=5.0,
                        min_value=0.5, max_value=25.0, step=0.5, format="%.1f",
                        key="mdose_nova"
                    )
                if st.form_submit_button("REGISTRAR DOSE", width="stretch"):
                    DB.execute(
                        "INSERT INTO medicacao (data_hora, dose_mg) VALUES (?,?)",
                        [f"{nova_data_n} 12:00:00", nova_dose_n],
                    )
                    st.cache_data.clear()
                    st.session_state["med_nova_open"] = False
                    _notif(f"Tirzepatida {nova_dose_n:.1f} mg registrada")
                    st.rerun()

    if df_med.empty:
        st.markdown(
            f'<p style="color:{GHOST};font-size:12px;margin-bottom:8px">Sem registros.</p>',
            unsafe_allow_html=True,
        )
    else:
        for i, (_, r) in enumerate(df_med.iterrows()):
            mid      = int(r["id"])
            dose     = float(r["dose_mg"])
            if dose > 100:
                dose /= 1000
            data_fmt = str(r["data_fmt"])
            data_iso = str(r["data_iso"])[:10]
            is_atual = (i == 0)

            cor_med  = GREEN if is_atual else GHOST
            bg_med   = "rgba(0,230,118,0.05)" if is_atual else "transparent"
            bd_med   = "rgba(0,230,118,0.28)" if is_atual else f"{BORDER}"

            edit_key  = f"med_edit_{mid}"
            is_editing = st.session_state.get(edit_key, False)

            # ── Card da dose ──────────────────────────────────────────────────
            _mc, _me = st.columns([1, 0.1])
            with _mc:
                atual_badge = (
                    f'<span style="font-family:{MONO};font-size:8px;font-weight:700;'
                    f'background:rgba(0,230,118,0.12);color:{GREEN};'
                    f'border:1px solid rgba(0,230,118,0.3);padding:2px 7px;'
                    f'border-radius:3px;letter-spacing:1px;margin-left:6px">ATUAL</span>'
                    if is_atual else ""
                )
                st.markdown(
                    f'<div style="background:{bg_med};border:1px solid {bd_med};'
                    f'border-left:3px solid {cor_med};border-radius:0 8px 8px 0;'
                    f'padding:10px 14px;margin-bottom:3px;'
                    f'display:flex;align-items:center;gap:10px">'
                    f'<span style="width:8px;height:8px;border-radius:50%;'
                    f'background:{cor_med};flex-shrink:0;display:inline-block"></span>'
                    f'<span style="font-family:{MONO};font-size:11px;color:{MUTED}">'
                    f'{data_fmt}</span>'
                    f'<span style="font-size:18px;font-weight:800;color:{cor_med};'
                    f'letter-spacing:-0.5px">{dose:.1f} mg</span>'
                    f'{atual_badge}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with _me:
                _edit_lbl = "✕" if is_editing else "✏"
                if st.button(_edit_lbl, key=f"tog_med_{mid}", width="stretch",
                             help="Editar / Fechar"):
                    st.session_state[edit_key] = not is_editing
                    st.rerun()

            # ── Form de edição inline ─────────────────────────────────────────
            if is_editing:
                st.markdown(
                    f'<div style="height:1px;background:{cor_med}33;margin:0 0 6px 3px"></div>',
                    unsafe_allow_html=True,
                )
                with st.form(f"form_med_edit_{mid}"):
                    _mc1, _mc2 = st.columns(2)
                    with _mc1:
                        try:
                            _val_data = _datetime.strptime(data_iso, "%Y-%m-%d").date()
                        except Exception:
                            _val_data = _date.fromisoformat(hoje_sql)
                        nova_data_med = st.date_input(
                            "Data", value=_val_data,
                            key=f"mdata_{mid}", format="DD/MM/YYYY"
                        )
                    with _mc2:
                        nova_dose_med = st.number_input(
                            "Dose (mg)", value=dose,
                            min_value=0.5, max_value=25.0, step=0.5, format="%.1f",
                            key=f"mdose_{mid}"
                        )
                    _msb, _mdb = st.columns([3, 1])
                    with _msb:
                        _med_salvar = st.form_submit_button("✓ SALVAR", width="stretch")
                    with _mdb:
                        _med_del    = st.form_submit_button("🗑", width="stretch")
                    if _med_salvar:
                        DB.execute(
                            "UPDATE medicacao SET data_hora=?, dose_mg=? WHERE id=?",
                            [f"{nova_data_med} 12:00:00", nova_dose_med, mid],
                        )
                        st.cache_data.clear()
                        st.session_state[edit_key] = False
                        _notif(f"Dose atualizada: {nova_dose_med:.1f} mg")
                        st.rerun()
                    if _med_del:
                        DB.execute("DELETE FROM medicacao WHERE id=?", [mid])
                        st.cache_data.clear()
                        st.session_state.pop(edit_key, None)
                        _notif("Registro removido", "err")
                        st.rerun()
                st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# SEÇÃO 5 — EVOLUÇÃO DE MEDIDAS (largura total — 11 colunas cabem melhor)
# ════════════════════════════════════════════════════════════════════════════
st.markdown(sec("Biometria", "Evolução de medidas — histórico completo"), unsafe_allow_html=True)

if True:  # bloco de escopo para df_bio
    df_bio = _q_biometria()

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
        h3a, h3b, h3c = st.columns(3)

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

    # ── IA Coach ─────────────────────────────────────────────────────────────
    st.markdown(sec("IA Coach", "Análise de Emagrecimento & Performance"), unsafe_allow_html=True)
    
    coach_html = f"""
    <div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;padding:16px 20px;margin-bottom:15px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-family:{MONO};font-size:11px;font-weight:700;color:{CYAN};letter-spacing:1px">📋 PROTOCOLO & METAS METABÓLICAS</span>
            <span style="background:rgba(167,139,250,0.1);border:1px solid {PURPLE}55;border-radius:4px;padding:2px 8px;font-family:{MONO};font-size:9px;color:{PURPLE};font-weight:700;letter-spacing:0.5px">TIRZEPATIDA</span>
        </div>
        <div style="display:grid;grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));gap:12px">
            <div style="font-size:12px;color:{MUTED}">Evolução de Peso: <br><span style="font-size:13px;font-weight:700;color:{TEXT}">115.3 kg (Jan/2026) ➔ {peso:.1f} kg atual</span></div>
            <div style="font-size:12px;color:{MUTED}">Rotina de Exercícios: <br><span style="font-size:13px;font-weight:700;color:{TEXT}">Musculação + Cardio (6x/sem)</span></div>
            <div style="font-size:12px;color:{MUTED}">Treinos HIIT (Ter & Sex): <br><span style="font-size:13px;font-weight:700;color:{TEXT}">Alta Intensidade / EPOC</span></div>
            <div style="font-size:12px;color:{MUTED}">Treinos Zona 2 (Seg, Qua, Qui, Sáb): <br><span style="font-size:13px;font-weight:700;color:{TEXT}">Corrida BPM 120-140 max</span></div>
        </div>
    </div>
    """
    st.markdown(coach_html, unsafe_allow_html=True)

    btn_col, sel_col = st.columns([1, 1])
    with btn_col:
        executar_analise = st.button("🔄 Nova Análise de Emagrecimento", key="btn_ia_coach", width="stretch")
    
    # Busca análises anteriores para o seletor histórico
    df_past = db("""
        SELECT id, data_hora, n_dias 
        FROM ia_analises_clinicas 
        ORDER BY data_hora DESC
    """)
    
    past_options = ["-- Ver análises anteriores --"]
    id_map = {}
    if not df_past.empty:
        for idx, r_row in df_past.iterrows():
            dt_val = r_row["data_hora"]
            try:
                if isinstance(dt_val, str):
                    dt_obj = datetime.strptime(dt_val.split(".")[0], "%Y-%m-%d %H:%M:%S")
                else:
                    dt_obj = dt_val
                dt_str = dt_obj.strftime("%d/%m/%Y %H:%M")
            except Exception:
                dt_str = str(dt_val)
            lbl = f"📅 {dt_str} ({r_row['n_dias']}d)"
            past_options.append(lbl)
            id_map[lbl] = int(r_row["id"])
            
    with sel_col:
        sel_past = st.selectbox("Histórico de Análises:", options=past_options, label_visibility="collapsed")
        
    if sel_past != "-- Ver análises anteriores --":
        sel_id = id_map[sel_past]
        df_sel = db("SELECT analise_txt FROM ia_analises_clinicas WHERE id = ?", [sel_id])
        if not df_sel.empty:
            st.session_state["ia_coach_result"] = df_sel["analise_txt"].iloc[0]

    if executar_analise:
        with st.spinner("🧠 IA Coach analisando dados clínicos, metabólicos e rotinas..."):
            try:
                # Obter médias
                media_passos = media(df_hist, "passos")
                media_cal_gastas = media(df_hist, "calorias_gastas")
                media_sono = media(df_hist, "sono_total_min")
                media_sono_prof = media(df_hist, "sono_profundo_min")
                media_hrv = media(df_hist, "hrv_ms")
                media_pai = media(df_hist, "pai")
                
                media_cal_ingestao = media(df_macro_hist, "cal")
                media_prot = media(df_macro_hist, "prot")
                media_carb = media(df_macro_hist, "carb")
                media_gord = media(df_macro_hist, "gord")
                
                media_corrida_km = media(df_hist, "corrida_km")
                media_corrida_cal = media(df_hist, "corrida_cal")
                
                # Prompt clínico
                prompt = (
                    "Você é o IA Coach de Elite do Leandro — atuando como Arquiteto de Performance Humana, Nutricionista Esportivo de Elite e Endocrinologista de Alta Performance.\\n"
                    "Sua missão é realizar uma análise clínica e metabólica extremamente crítica e sem rodeios sobre a evolução do Leandro.\\n\\n"
                    "PARÂMETROS DE EVOLUÇÃO E ROTINA:\\n"
                    "- Peso Inicial (Janeiro/2026): 115,3 kg\\n"
                    f"- Peso Atual: {peso:.1f} kg (Evolução: -{115.3 - peso:.1f} kg)\\n"
                    "- Protocolo Farmacológico: Tirzepatida (injetável semanal)\\n"
                    "- Frequência de Treino: 6x por semana (Musculação + Cardio)\\n"
                    "- Terça & Sexta: Cardio HIIT\\n"
                    "- Segunda, Quarta, Quinta & Sábado: Corrida em Zona 2 (BPM entre 120 e 140 no máximo)\\n\\n"
                    f"MÉDIAS REAIS REGISTRADAS NOS ÚLTIMOS {n_dias} DIAS:\\n"
                    f"- Consumo de Calorias: {fmt_val(media_cal_ingestao, ' kcal', 0)}\\n"
                    f"- Consumo de Proteínas: {fmt_val(media_prot, ' g', 0)}\\n"
                    f"- Consumo de Carboidratos: {fmt_val(media_carb, ' g', 0)}\\n"
                    f"- Consumo de Gorduras: {fmt_val(media_gord, ' g', 0)}\\n"
                    f"- Gasto Calórico de Atividade (Amazfit): {fmt_val(media_cal_gastas, ' kcal', 0)}\\n"
                    f"- Média de Corrida (Amazfit): {fmt_val(media_corrida_km, ' km/dia', 2)} ({fmt_val(media_corrida_cal, ' kcal/dia', 0)})\\n"
                    f"- Treinos de Musculação (Hevy): {total_treinos} treinos realizados no período\\n"
                    f"- Média de Volume de Treino: {fmt_val(media_vol_treino, ' kg', 0)}\\n"
                    f"- Média de Duração de Treino: {fmt_val(media_dur_treino, ' min', 0)}\\n"
                    f"- Déficit Calórico Médio Estimado: {fmt_val(media_deficit, ' kcal', 0)}\\n"
                    f"- Média de Passos Diários: {fmt_val(media_passos, '', 0)}\\n"
                    f"- Média de Sono Total: {fmt_val(media_sono, ' min', 0)}\\n"
                    f"- Média de Sono Profundo: {fmt_val(media_sono_prof, ' min', 0)}\\n"
                    f"- Média de HRV: {fmt_val(media_hrv, ' ms', 0)}\\n"
                    f"- Média de PAI: {fmt_val(media_pai, '', 0)}\\n\\n"
                    "Forneça um parecer crítico estruturado EXATAMENTE nos 4 tópicos abaixo:\\n"
                    "1. 🔬 AJUSTE DE METABOLISMO & TIRZEPATIDA: Avalie o impacto metabólico da medicação associado ao déficit calórico atual e ingestão de proteínas (evitando perda de massa muscular).\\n"
                    "2. 🏃 ANÁLISE DE CARDIO (ZONE 2 & HIIT): Avalie se o estímulo de Zone 2 (bpm 120-140) e HIIT nas terças/sextas está correto para otimização da lipólise, recuperação e melhora do HRV/PAI.\\n"
                    "3. 📊 BALANÇO ENERGÉTICO & MACROS: Crítica sobre os números de ingestão x gasto energético.\\n"
                    "4. ⚡ PLANO DE AÇÃO PRÁTICO: Próximos passos clínicos/alimentares para manter o emagrecimento saudável e quebrar platôs.\\n\\n"
                    "Escreva com tom técnico, extremamente sênior e clínico, sem rodeios ou parágrafos introdutórios/conclusivos genéricos. Vá direto à análise de cada ponto."
                )
                
                vision = _gemini_model()
                res = vision.generate_content(prompt)
                st.session_state["ia_coach_result"] = res.text
                
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
                st.error(f"❌ Erro ao chamar a IA: {e}")

    if "ia_coach_result" in st.session_state:
        st.markdown(f"""
        <div style="background:{BG2};border:1px solid {BORDER};border-radius:10px;padding:20px;margin-top:10px;margin-bottom:15px;line-height:1.6">
            <div style="font-family:{MONO};font-size:11px;font-weight:700;color:{GREEN};letter-spacing:1.5px;margin-bottom:15px;text-transform:uppercase">🩺 DIAGNÓSTICO CLÍNICO DA IA</div>
            
        {st.session_state["ia_coach_result"]}
        
        </div>
        """, unsafe_allow_html=True)

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
