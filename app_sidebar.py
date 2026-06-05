"""Sidebar compartilhada — dashboard e páginas secundárias."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import pandas as pd
import streamlit as st
from zoneinfo import ZoneInfo

import db as DB

TEXT = "#e8edf5"
BORDER = "#1a2035"
CYAN = "#00d4ff"
GREEN = "#00e676"
RED = "#ff6b6b"
AMBER = "#fbbf24"
PURPLE = "#a78bfa"
MUTED = "#4a5568"

TMB = 1863
META_PAI = 100
_BR = ZoneInfo("America/Sao_Paulo")
BANCO_PAGE = "pages/1_Banco_de_Alimentos.py"
DASHBOARD_PAGE = "dashboard.py"

_NAV_ANCHORS = [
    ("sec-hoje", "🎯", "Hoje"),
    ("sec-evolucao", "📈", "Evolução"),
    ("sec-registros", "📝", "Registros"),
    ("sec-treinos", "🏋️", "Treinos"),
    ("sec-historico", "📊", "Histórico"),
    ("sec-medicacao", "💊", "Medicação"),
    ("sec-biometria", "📏", "Biometria"),
    ("sec-evacuacao", "🚽", "Evacuação"),
    ("sec-ia", "🤖", "IA Coach"),
]

_SIDEBAR_SHELL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700;800&display=swap');
:root{
  --sh-bg:#080c14;--sh-bg-subtle:#0a0f1a;--sh-border:rgba(255,255,255,.07);
  --sh-text:#e8edf5;--sh-text-muted:#8b9cb3;--sh-text-dim:#5a6b82;
  --sh-accent:#00d4ff;--sh-radius-md:10px;
  --sh-font-display:'DM Sans',system-ui,sans-serif;--sh-font-mono:'Space Mono',ui-monospace,monospace;
}
html,body,.stApp{background:var(--sh-bg)!important;color:var(--sh-text)!important;font-family:var(--sh-font-display)!important}
section[data-testid="stSidebar"]{background:#080e1a!important;border-right:1px solid #111c2e!important;font-family:var(--sh-font-display)!important}
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
.sh-wearable-card{background:var(--sh-bg-subtle);border:1px solid var(--sh-border);border-radius:var(--sh-radius-md);padding:12px 14px;min-height:72px}
.sh-wearable-card__label{font-family:var(--sh-font-display);font-size:11px;color:var(--sh-text-dim);font-weight:500}
.sh-wearable-card__value{font-family:var(--sh-font-display);font-size:18px;font-weight:800;margin-top:6px;letter-spacing:-.02em}
.sh-nav-link{text-transform:none!important;transition:border-color .15s,color .15s!important}
.sh-nav-link:hover{border-color:rgba(0,212,255,.35)!important;color:var(--sh-accent)!important;
  background:rgba(0,212,255,.08)!important;transform:translateX(4px)!important}
/* Botões da sidebar — paridade com dashboard.py (alinhamento à esquerda) */
section[data-testid="stSidebar"] .stButton button,
section[data-testid="stSidebar"] [data-testid="stButton"] button,
section[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] button,
section[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] button{
  background:rgba(13,20,36,.6)!important;border:1px solid #1a2840!important;
  color:#e8edf5!important;font-family:var(--sh-font-display)!important;font-size:13px!important;
  font-weight:600!important;letter-spacing:0!important;text-transform:none!important;
  border-radius:8px!important;padding:10px 12px!important;width:100%!important;
  min-height:40px!important;text-align:left!important;
  display:flex!important;align-items:center!important;justify-content:flex-start!important}
section[data-testid="stSidebar"] .stButton button:hover,
section[data-testid="stSidebar"] [data-testid="stButton"] button:hover{
  border-color:rgba(0,212,255,.45)!important;color:#00d4ff!important;
  background:rgba(0,212,255,0.1)!important;box-shadow:0 0 16px rgba(0,212,255,.18)!important;
  transform:translateX(3px)!important}
section[data-testid="stSidebar"] [data-testid="stButton"] button p,
section[data-testid="stSidebar"] [data-testid="stButton"] button div,
section[data-testid="stSidebar"] .stButton button p,
section[data-testid="stSidebar"] .stButton button div{
  text-align:left!important;width:100%!important;margin:0!important;
  display:flex!important;justify-content:flex-start!important}
section[data-testid="stSidebar"] > div:first-child{padding:0.75rem 1rem 1rem!important}
#MainMenu,footer,header,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important}
</style>
"""

_SIDEBAR_NAV_CSS = """
<style>
a.sh-nav-active {
    background: rgba(0,212,255,0.12) !important;
    border-color: rgba(0,212,255,0.35) !important;
    color: #00d4ff !important;
    border-left: 2px solid #00d4ff !important;
}
a.sh-nav-active span { color: #00d4ff !important; }
section[data-testid="stSidebar"] .sh-nav-menu [data-testid="stButton"],
section[data-testid="stSidebar"] .sh-quick-banco [data-testid="stButton"] {
    margin-bottom: 4px;
}
section[data-testid="stSidebar"] .sh-nav-menu [data-testid="stButton"] > button,
section[data-testid="stSidebar"] .sh-quick-banco [data-testid="stButton"] > button {
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 8px !important;
    padding: 8px 10px !important;
    border-radius: 6px !important;
    font-family: var(--sh-font-display) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--sh-text) !important;
    background: transparent !important;
    border: 1px solid #1a2035 !important;
    box-shadow: none !important;
    text-align: left !important;
    transition: border-color .15s, color .15s, background .15s, transform .15s !important;
}
section[data-testid="stSidebar"] .sh-nav-menu [data-testid="stButton"] > button:hover,
section[data-testid="stSidebar"] .sh-quick-banco [data-testid="stButton"] > button:hover {
    border-color: rgba(0,212,255,.35) !important;
    color: var(--sh-accent) !important;
    background: rgba(0,212,255,.08) !important;
    transform: translateX(4px) !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] .sh-nav-menu [data-testid="stButton"] > button p,
section[data-testid="stSidebar"] .sh-nav-menu [data-testid="stButton"] > button div,
section[data-testid="stSidebar"] .sh-quick-banco [data-testid="stButton"] > button p,
section[data-testid="stSidebar"] .sh-quick-banco [data-testid="stButton"] > button div {
    font-size: 13px !important;
    font-weight: 600 !important;
    text-align: left !important;
    width: 100% !important;
    justify-content: flex-start !important;
}
section[data-testid="stSidebar"] .sh-quick-menu [data-testid="stButton"] > button,
section[data-testid="stSidebar"] .sh-quick-menu [data-testid="stButton"] > button p {
    text-align: left !important;
    justify-content: flex-start !important;
}
section[data-testid="stSidebar"] .sh-quick-banco.is-active [data-testid="stButton"] > button {
    background: rgba(0,212,255,0.12) !important;
    border-color: rgba(0,212,255,0.35) !important;
    color: #00d4ff !important;
    border-left: 2px solid #00d4ff !important;
}
section[data-testid="stSidebar"] .sh-quick-banco.is-active [data-testid="stButton"] > button:hover {
    transform: none !important;
}
section[data-testid="stSidebar"] .sh-quick-banco.is-active [data-testid="stButton"] > button:disabled {
    opacity: 1 !important;
    cursor: default !important;
}
</style>
"""

_SIDEBAR_NAV_JS = """
<script>
(function() {
  if (window.__shNavInit) return;
  window.__shNavInit = true;

  document.addEventListener('click', function(e) {
    var link = e.target.closest('a[href^="#sec-"]');
    if (!link) return;
    var target = document.querySelector(link.getAttribute('href'));
    if (target) {
      e.preventDefault();
      var smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      target.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
    }
  });

  var NAV_IDS = ['sec-hoje','sec-evolucao','sec-registros','sec-treinos',
                 'sec-historico','sec-medicacao','sec-biometria','sec-evacuacao','sec-ia'];
  var links = document.querySelectorAll('a[href^="#sec-"]');
  var secs = Array.from(document.querySelectorAll('div[id^="sec-"]')).filter(function(el) {
    return NAV_IDS.indexOf(el.id) >= 0;
  });
  if (!links.length || !secs.length) return;

  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (!entry.isIntersecting) return;
      var id = entry.target.id;
      links.forEach(function(l) { l.classList.remove('sh-nav-active'); });
      var active = document.querySelector('a.sh-nav-link[href="#' + id + '"]');
      if (active) active.classList.add('sh-nav-active');
    });
  }, { threshold: 0.2, rootMargin: '-8% 0px -55% 0px' });

  secs.forEach(function(sec) { observer.observe(sec); });
})();
</script>
"""


@st.cache_data(ttl=60)
def _q_agua(dia: str):
    return DB.query(
        "SELECT COALESCE(SUM(quantidade_ml),0) as t FROM agua "
        "WHERE date(data_hora,'localtime')=?",
        [dia],
    )


@st.cache_data(ttl=60)
def _q_macros(dia: str):
    return DB.query(
        "SELECT COALESCE(SUM(calorias),0) as cal, COALESCE(SUM(proteinas),0) as prot,"
        "COALESCE(SUM(carboidratos),0) as carb, COALESCE(SUM(gorduras),0) as gord "
        "FROM refeicoes WHERE date(data_hora,'localtime')=?",
        [dia],
    )


@st.cache_data(ttl=60)
def _q_amazfit():
    return DB.query("SELECT * FROM amazfit_dados ORDER BY date(data_hora) DESC LIMIT 1")


def _load_kpi_data(hoje_sql: str) -> dict:
    _da = _q_agua(hoje_sql)
    agua_l = float(_da["t"].iloc[0] or 0) / 1000

    _dr = _q_macros(hoje_sql)
    cal_h = float(_dr["cal"].iloc[0] or 0)
    prot_h = float(_dr["prot"].iloc[0] or 0)

    try:
        _az = _q_amazfit()
        _az = _az if _az is not None and not _az.empty else pd.DataFrame()
    except Exception:
        _az = pd.DataFrame()

    passos = int(_az["passos"].iloc[0]) if not _az.empty else 0
    cal_gasta = int(_az["calorias_gastas"].iloc[0]) if not _az.empty else 0
    sono_tot = int(_az["sono_total_min"].iloc[0]) if not _az.empty else 0
    hrv = int(_az["hrv_ms"].iloc[0]) if not _az.empty else 0
    pai = int(_az["pai"].iloc[0]) if not _az.empty else 0

    gasto_total_dia = TMB + cal_gasta
    deficit = gasto_total_dia - int(cal_h)
    def_cor = GREEN if deficit > 0 else RED
    def_txt = (
        f"Déficit {abs(deficit):,}" if deficit > 0
        else f"Superávit {abs(deficit):,}" if deficit < 0
        else "Equilíbrio"
    )
    sono_h_fmt = f"{sono_tot // 60}h{sono_tot % 60:02d}"
    hrv_cor = GREEN if hrv >= 35 else (AMBER if hrv >= 25 else RED)
    pai_cor = GREEN if pai >= META_PAI else (AMBER if pai >= 70 else RED)

    return {
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
    }


def _go_dashboard(section: Optional[str] = None):
    if section:
        st.session_state["_scroll_to"] = section
    st.switch_page(DASHBOARD_PAGE)


def _render_nav_menu(active_page: str):
    st.markdown('<div class="sh-nav-menu">', unsafe_allow_html=True)

    for anc, ic, lb in _NAV_ANCHORS:
        if active_page == "dashboard":
            st.markdown(
                f'<a href="#{anc}" class="sh-nav-link" style="display:flex;align-items:center;gap:8px;'
                f'padding:8px 10px;border-radius:6px;text-decoration:none;margin-bottom:4px;'
                f'font-family:var(--sh-font-display);font-size:13px;font-weight:600;color:{TEXT};'
                f'background:transparent;border:1px solid {BORDER}">'
                f'<span>{ic}</span><span>{lb}</span></a>',
                unsafe_allow_html=True,
            )
        else:
            if st.button(f"{ic} {lb}", key=f"sb_nav_{anc}", use_container_width=True):
                _go_dashboard(anc)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_banco_quick_action(active_page: str):
    """Banco de Alimentos — último item de Ações rápidas, estilo igual ao menu."""
    _active_cls = " is-active" if active_page == "banco" else ""
    st.markdown(f'<div class="sh-quick-banco{_active_cls}">', unsafe_allow_html=True)
    if active_page == "banco":
        st.button("🍽️ Banco de Alimentos", key="sb_btn_banco_banco", use_container_width=True, disabled=True)
    elif st.button("🍽️ Banco de Alimentos", key=f"sb_btn_banco_{active_page}", use_container_width=True):
        st.switch_page(BANCO_PAGE)
    st.markdown("</div>", unsafe_allow_html=True)


def render_app_sidebar(
    active_page: str = "dashboard",
    kpi_data: Optional[dict] = None,
    quick_actions: Optional[dict[str, Callable[[], None]]] = None,
):
    """Renderiza sidebar idêntica em dashboard e subpáginas."""
    hoje_sql = datetime.now(_BR).strftime("%Y-%m-%d")
    kpi = kpi_data or _load_kpi_data(hoje_sql)

    with st.sidebar:
        st.markdown(_SIDEBAR_SHELL_CSS, unsafe_allow_html=True)
        st.markdown(_SIDEBAR_NAV_CSS, unsafe_allow_html=True)
        if active_page == "dashboard":
            st.html(_SIDEBAR_NAV_JS)

        st.markdown(
            '<div class="sh-sidebar-brand"><span style="font-size:16px">⚡</span> SYS.HEALTH</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sh-side-section">Resumo do dia</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="sh-side-kpis">'
            f'<div class="sh-side-kpi"><span class="sh-side-kpi__l">Calorias</span>'
            f'<span class="sh-side-kpi__v" style="color:{CYAN}">{int(kpi["cal_h"]):,}</span></div>'
            f'<div class="sh-side-kpi"><span class="sh-side-kpi__l">Proteína</span>'
            f'<span class="sh-side-kpi__v" style="color:{RED}">{int(kpi["prot_h"])}g</span></div>'
            f'<div class="sh-side-kpi"><span class="sh-side-kpi__l">Água</span>'
            f'<span class="sh-side-kpi__v" style="color:#a78bfa">{kpi["agua_l"]:.1f} L</span></div>'
            f'<div class="sh-side-kpi"><span class="sh-side-kpi__l">Balanço</span>'
            f'<span class="sh-side-kpi__v" style="color:{kpi["def_cor"]}">{kpi["def_txt"]}</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="sh-wearable-panel">'
            f'<div class="sh-wearable-panel__title">⌚ Amazfit hoje</div>'
            f'<div class="sh-wearable-grid">'
            f'<div class="sh-wearable-card">'
            f'<div class="sh-wearable-card__label">👟 Passos</div>'
            f'<div class="sh-wearable-card__value" style="color:{CYAN}">{kpi["passos"]:,}</div></div>'
            f'<div class="sh-wearable-card">'
            f'<div class="sh-wearable-card__label">🌙 Sono</div>'
            f'<div class="sh-wearable-card__value" style="color:{PURPLE}">{kpi["sono_h_fmt"]}</div></div>'
            f'<div class="sh-wearable-card">'
            f'<div class="sh-wearable-card__label">💓 HRV</div>'
            f'<div class="sh-wearable-card__value" style="color:{kpi["hrv_cor"]}">{kpi["hrv"]} '
            f'<span style="font-size:12px;font-weight:600">ms</span></div></div>'
            f'<div class="sh-wearable-card">'
            f'<div class="sh-wearable-card__label">⚡ PAI</div>'
            f'<div class="sh-wearable-card__value" style="color:{kpi["pai_cor"]}">{kpi["pai"]}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sh-side-section">Menu</div>', unsafe_allow_html=True)
        _render_nav_menu(active_page)

        st.markdown(
            '<div class="sh-side-section" style="margin-top:14px;padding-top:12px;'
            'border-top:1px solid var(--sh-border)">Ações rápidas</div>',
            unsafe_allow_html=True,
        )

        actions = quick_actions or {}
        st.markdown('<div class="sh-quick-menu">', unsafe_allow_html=True)
        _qa = [
            ("refeicao", "➕ Nova refeição", "sb_btn_ref"),
            ("editar", "✏️ Editar refeições", "sb_btn_edit_ref"),
            ("agua", "💧 Água / HRV", "sb_btn_agua"),
            ("supp", "💊 Suplemento", "sb_btn_supp"),
        ]
        for action_key, label, key_base in _qa:
            key = f"{key_base}_{active_page}"
            handler = actions.get(action_key)
            if handler and st.button(label, key=key, use_container_width=True):
                handler()
        _render_banco_quick_action(active_page)
        st.markdown("</div>", unsafe_allow_html=True)
