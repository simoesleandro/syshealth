"""Sidebar compartilhada — dashboard e páginas secundárias."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import pandas as pd
import streamlit as st
from zoneinfo import ZoneInfo

import db as DB
from sh_tokens import AMBER, CYAN, GREEN, MUTED, PURPLE, RED, ROOT_CSS, TEXT

TMB = 1863
META_PAI = 100
_BR = ZoneInfo("America/Sao_Paulo")
BANCO_PAGE = "pages/1_Banco_de_Alimentos.py"
DASHBOARD_PAGE = "dashboard.py"
EDIT_ICON = ":material/edit:"
STAR_ICON = ":material/star:"
STAR_OUTLINE_ICON = ":material/star_outline:"
DELETE_ICON = ":material/delete:"

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

_SIDEBAR_SHELL_CSS = (
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700;800&display=swap');
"""
    + ROOT_CSS
    + """
html,body,.stApp{background:var(--sh-bg)!important;color:var(--sh-text)!important;font-family:var(--sh-font-display)!important}
section[data-testid="stSidebar"]{background:#080e1a!important;border-right:1px solid #111c2e!important;font-family:var(--sh-font-display)!important}
.sh-sidebar-brand{font-family:var(--sh-font-mono);font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--sh-accent);
  margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid var(--sh-border);display:flex;align-items:center;gap:8px}
.sh-side-section{font-family:var(--sh-font-display);font-size:11px;font-weight:600;color:var(--sh-text-muted);margin:16px 0 8px;letter-spacing:.02em}
.sh-side-kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
.sh-side-kpi{background:var(--sh-bg-subtle);border:1px solid var(--sh-border);border-radius:var(--sh-radius-md);padding:12px}
.sh-side-kpi__l{display:block;font-family:var(--sh-font-display);font-size:11px;color:var(--sh-text-dim);font-weight:500}
.sh-side-kpi__v{display:block;font-family:var(--sh-font-display);font-size:17px;font-weight:800;margin-top:4px;letter-spacing:-.02em}
.sh-wearable-panel{margin-top:12px;padding-top:12px;border-top:1px solid var(--sh-border)}
.sh-wearable-panel__title{font-family:var(--sh-font-display);font-size:12px;font-weight:700;color:var(--sh-text);letter-spacing:.02em;margin-bottom:10px}
.sh-wearable-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.sh-wearable-card{background:var(--sh-bg-subtle);border:1px solid var(--sh-border);border-radius:var(--sh-radius-md);padding:12px;min-height:72px}
.sh-wearable-card__label{font-family:var(--sh-font-display);font-size:11px;color:var(--sh-text-dim);font-weight:500}
.sh-wearable-card__value{font-family:var(--sh-font-display);font-size:18px;font-weight:800;margin-top:6px;letter-spacing:-.02em}
.sh-nav-link{text-transform:none!important;transition:border-color .15s,color .15s!important}
.sh-nav-link:hover{border-color:rgba(0,212,255,.35)!important;color:var(--sh-accent)!important;
  background:rgba(0,212,255,.08)!important;transform:translateX(2px)!important}
section[data-testid="stSidebar"] > div:first-child{padding:16px!important}
#MainMenu,footer,header,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important}
/* Modais — centro do viewport (não da coluna main ao lado da sidebar) */
.react-aria-ModalOverlay{
  position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  padding:24px 16px!important;box-sizing:border-box!important;z-index:1000010!important}
.react-aria-ModalOverlay [data-testid="stDialog"]{
  margin:0!important;position:relative!important;left:auto!important;top:auto!important;
  right:auto!important;bottom:auto!important;max-height:calc(100vh - 48px)!important}
/* Botão fechar do modal — não herdar estilo de botão secundário */
[data-testid="stDialog"] header button,
[data-testid="stDialog"] [data-testid="stModalHeader"] button{
  background:transparent!important;border:none!important;box-shadow:none!important;
  min-width:36px!important;min-height:36px!important;padding:6px!important;
  color:#c8d0dc!important;transform:none!important}
[data-testid="stDialog"] header button svg,
[data-testid="stDialog"] [data-testid="stModalHeader"] button svg{
  display:block!important;width:20px!important;height:20px!important;
  stroke:#c8d0dc!important;fill:none!important;opacity:1!important}
[data-testid="stDialog"] header button:hover svg,
[data-testid="stDialog"] [data-testid="stModalHeader"] button:hover svg{
  stroke:#00d4ff!important}
</style>
"""
)

_DIALOG_CENTER_JS = """
<script>
(function(){
  if(window.__shDlgCenter)return;
  window.__shDlgCenter=true;
  function sbWidth(){
    var sb=document.querySelector('section[data-testid="stSidebar"]');
    if(!sb)return 0;
    var r=sb.getBoundingClientRect();
    if(r.width<40||r.right<=0)return 0;
    if(window.innerWidth<=768)return 0;
    return r.width;
  }
  function patch(){
    var shift=-(sbWidth()/2);
    document.querySelectorAll('.react-aria-ModalOverlay').forEach(function(ov){
      if(ov.parentElement&&ov.parentElement!==document.body){
        document.body.appendChild(ov);
      }
      ov.style.setProperty('position','fixed','important');
      ov.style.setProperty('inset','0','important');
      ov.style.setProperty('width','100vw','important');
      ov.style.setProperty('height','100vh','important');
      ov.style.setProperty('display','flex','important');
      ov.style.setProperty('align-items','center','important');
      ov.style.setProperty('justify-content','center','important');
      ov.style.setProperty('padding','24px 16px','important');
      ov.style.setProperty('box-sizing','border-box','important');
      ov.style.setProperty('z-index','1000010','important');
      var dlg=ov.querySelector('[data-testid="stDialog"]');
      if(dlg){
        dlg.style.setProperty('margin','0','important');
        dlg.style.setProperty('position','relative','important');
        dlg.style.setProperty('left','auto','important');
        dlg.style.setProperty('top','auto','important');
        dlg.style.setProperty('transform','translateX('+shift+'px)','important');
        dlg.style.setProperty('max-height','calc(100vh - 48px)','important');
      }
      ov.querySelectorAll('header button, [data-testid="stModalHeader"] button').forEach(function(btn){
        btn.style.setProperty('background','transparent','important');
        btn.style.setProperty('border','none','important');
        btn.style.setProperty('box-shadow','none','important');
        var svg=btn.querySelector('svg');
        if(svg){
          svg.style.setProperty('display','block','important');
          svg.style.setProperty('stroke','#c8d0dc','important');
          svg.style.setProperty('fill','none','important');
        }
      });
    });
  }
  patch();
  new MutationObserver(patch).observe(document.documentElement,{childList:true,subtree:true});
})();
</script>
"""


def inject_dialog_center_fix():
    """Garante modais @st.dialog centralizados na tela inteira."""
    st.html(_DIALOG_CENTER_JS)

_SIDEBAR_NAV_CSS = """
<style>
.sh-nav-mark,.sh-quick-stack-mark,.sh-page-active-mark{display:none!important;height:0!important;margin:0!important;padding:0!important}
/* ── Sidebar — links HTML unificados (menu + ações rápidas) ── */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{
  align-items:stretch!important;width:100%!important;padding:0!important;margin:0!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-nav),
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-quick-nav){
  width:100%!important;padding:0!important;margin:0!important}
.sh-side-nav,.sh-side-quick-nav{display:flex!important;flex-direction:column!important;gap:8px!important;
  width:100%!important;margin:0!important;padding:0!important}
.sh-side-btn,.sh-side-btn--disabled{
  display:flex!important;align-items:center!important;justify-content:flex-start!important;
  gap:10px!important;width:100%!important;box-sizing:border-box!important;
  min-height:44px!important;padding:10px 14px!important;margin:0!important;
  font-family:var(--sh-font-display)!important;font-size:13px!important;font-weight:600!important;
  letter-spacing:0!important;text-transform:none!important;text-decoration:none!important;
  color:#e8edf5!important;background:rgba(13,20,36,.55)!important;
  border:1px solid #1a2840!important;border-radius:8px!important;cursor:pointer!important;
  transition:border-color .18s,color .18s,background .18s,box-shadow .18s!important}
button.sh-side-btn{
  appearance:none!important;-webkit-appearance:none!important;border-style:solid!important;
  text-align:left!important;line-height:1.3!important}
a.sh-side-btn:hover,button.sh-side-btn:hover{
  border-color:rgba(0,212,255,.45)!important;color:#00d4ff!important;
  background:rgba(0,212,255,.08)!important;box-shadow:0 0 12px rgba(0,212,255,.16)!important;
  transform:none!important}
a.sh-side-btn:focus-visible,button.sh-side-btn:focus-visible{
  outline:2px solid rgba(0,212,255,.45)!important;outline-offset:2px!important}
.sh-side-btn.is-active,.sh-side-btn--active,.sh-side-btn--disabled{
  background:rgba(0,212,255,.1)!important;border-color:rgba(0,212,255,.32)!important;
  color:#00d4ff!important;border-left:3px solid #00d4ff!important;padding-left:11px!important;
  cursor:default!important;pointer-events:none!important}
/* Sidebar st.button — alinhado (ações rápidas + menu em subpáginas) */
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-quick-mark)~[data-testid="stElementContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-nav-st-mark)~[data-testid="stElementContainer"]{
  width:100%!important;max-width:100%!important;margin:0!important;padding:0!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-quick-mark)~[data-testid="stElementContainer"] [data-testid="stButton"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-nav-st-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]{
  width:100%!important;margin:0 0 8px!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-quick-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-nav-st-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button{
  width:100%!important;min-height:44px!important;padding:10px 14px!important;
  display:flex!important;align-items:center!important;justify-content:flex-start!important;
  gap:10px!important;text-align:left!important;font-family:var(--sh-font-display)!important;
  font-size:13px!important;font-weight:600!important;letter-spacing:0!important;
  text-transform:none!important;border-radius:8px!important;color:#e8edf5!important;
  background:rgba(13,20,36,.55)!important;border:1px solid #1a2840!important;
  box-shadow:none!important;transform:none!important;margin:0!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-quick-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-nav-st-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-quick-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button div,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-nav-st-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button div{
  text-align:left!important;width:100%!important;margin:0!important;display:flex!important;
  align-items:center!important;justify-content:flex-start!important;gap:10px!important;
  font-size:13px!important;font-weight:600!important;color:inherit!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-quick-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button:hover,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-nav-st-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button:hover{
  border-color:rgba(0,212,255,.45)!important;color:#00d4ff!important;
  background:rgba(0,212,255,.08)!important;box-shadow:0 0 12px rgba(0,212,255,.16)!important}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-quick-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button:disabled,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"]:has(.sh-side-nav-st-mark)~[data-testid="stElementContainer"] [data-testid="stButton"]>button:disabled{
  background:rgba(0,212,255,.1)!important;border-color:rgba(0,212,255,.32)!important;
  color:#00d4ff!important;border-left:3px solid #00d4ff!important;padding-left:11px!important;opacity:1!important}
@media(prefers-reduced-motion:reduce){
  a.sh-side-btn,a.sh-side-btn:hover,button.sh-side-btn,button.sh-side-btn:hover{
    transition:none!important;transform:none!important}}
</style>
"""

_SIDEBAR_NAV_JS = """
<script>
(function() {
  if (window.__shNavInit) return;
  window.__shNavInit = true;

  var NAV_IDS = ['sec-hoje','sec-evolucao','sec-registros','sec-treinos',
                 'sec-historico','sec-medicacao','sec-biometria','sec-evacuacao','sec-ia'];
  var smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.addEventListener('click', function(e) {
    var link = e.target.closest('a[href^="#sec-"]');
    if (!link) return;
    var target = document.querySelector(link.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
    }
  });

  function clearNavActive() {
    document.querySelectorAll('.sh-side-nav .sh-side-btn.is-active').forEach(function(l) {
      l.classList.remove('is-active');
    });
  }

  function setNavActive(secId) {
    clearNavActive();
    var link = document.querySelector('.sh-side-nav .sh-side-btn[data-sec="' + secId + '"]');
    if (link) link.classList.add('is-active');
  }

  var secs = Array.from(document.querySelectorAll('div[id^="sec-"]')).filter(function(el) {
    return NAV_IDS.indexOf(el.id) >= 0;
  });
  if (!secs.length) return;

  var observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (!entry.isIntersecting) return;
      setNavActive(entry.target.id);
    });
  }, { threshold: 0.2, rootMargin: '-8% 0px -55% 0px' });

  secs.forEach(function(sec) { observer.observe(sec); });
})();
</script>
"""

_MOB_QUICK_JS = """
<script>
(function(){
  if (window.__shMobQuickInit) return;
  window.__shMobQuickInit = true;
  function findRow(host){
    var ec = host.closest('[data-testid="stElementContainer"]');
    if (!ec || !ec.parentElement) return null;
    var kids = Array.prototype.slice.call(ec.parentElement.children);
    var idx = kids.indexOf(ec);
    for (var i = idx + 1; i < kids.length; i++) {
      if (kids[i].querySelector && kids[i].querySelector('[data-testid="stHorizontalBlock"]')) {
        return kids[i];
      }
    }
    return null;
  }
  function apply(){
    document.querySelectorAll('.sh-mob-quick-host').forEach(function(host){
      var row = findRow(host);
      if (!row) return;
      row.classList.add('sh-mob-quick-bar');
      var show = window.innerWidth <= 680;
      row.style.setProperty('display', show ? 'block' : 'none', 'important');
      var hb = row.querySelector('[data-testid="stHorizontalBlock"]');
      if (hb) hb.style.setProperty('display', show ? 'flex' : 'none', 'important');
    });
  }
  apply();
  window.addEventListener('resize', apply);
  new MutationObserver(apply).observe(document.documentElement, {childList:true, subtree:true});
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


def _nav_to_dashboard_section(section: str):
    st.session_state["_scroll_to"] = section
    st.session_state["_pending_switch"] = DASHBOARD_PAGE


def _queue_open_dialog(dlg: str):
    if dlg == "refeicao":
        st.session_state["_ref_busca_reset"] = True
    st.session_state["open_dialog"] = dlg


def _sidebar_goto_banco():
    st.session_state["_pending_switch"] = BANCO_PAGE


def _flush_pending_switch():
    target = st.session_state.pop("_pending_switch", None)
    if target:
        st.switch_page(target)


def _render_nav_menu(active_page: str):
    """Menu — âncoras HTML no dashboard; st.button nas subpáginas."""
    if active_page == "dashboard":
        _links = "".join(
            f'<a class="sh-side-btn sh-nav-link" href="#{anc}" data-sec="{anc}">{ic} {lb}</a>'
            for anc, ic, lb in _NAV_ANCHORS
        )
        st.markdown(
            f'<nav class="sh-side-nav" aria-label="Menu">{_links}</nav>',
            unsafe_allow_html=True,
        )
        return
    st.markdown('<div class="sh-side-nav-st-mark" aria-hidden="true"></div>', unsafe_allow_html=True)
    for anc, ic, lb in _NAV_ANCHORS:
        st.button(
            f"{ic} {lb}",
            key=f"sb_nav_{anc}_{active_page}",
            use_container_width=True,
            on_click=_nav_to_dashboard_section,
            kwargs={"section": anc},
        )


def _render_quick_actions(active_page: str, quick_actions: Optional[dict[str, Callable[[], None]]]):
    """Ações rápidas — st.button + session_state (sem rerun/switch em callback)."""
    if quick_actions is None:
        return
    st.markdown('<div class="sh-side-quick-mark" aria-hidden="true"></div>', unsafe_allow_html=True)
    _items = (
        ("refeicao", "Nova refeição", "➕"),
        ("editar", "Editar refeições", "✏️"),
        ("agua", "Água / HRV", "💧"),
        ("supp", "Suplemento", "💊"),
    )
    for action_key, label, icon in _items:
        if action_key not in quick_actions:
            continue
        st.button(
            f"{icon} {label}",
            key=f"sb_{action_key}_{active_page}",
            use_container_width=True,
            on_click=_queue_open_dialog,
            kwargs={"dlg": action_key},
        )
    if active_page == "banco":
        st.button(
            "🍽️ Banco de Alimentos",
            key="sb_banco_active",
            use_container_width=True,
            disabled=True,
        )
    else:
        st.button(
            "🍽️ Banco de Alimentos",
            key=f"sb_banco_{active_page}",
            use_container_width=True,
            on_click=_sidebar_goto_banco,
        )


def _qp_val(key: str):
    val = st.query_params.get(key)
    if isinstance(val, list):
        return val[0] if val else None
    return val


def handle_quick_dialog_query():
    """Abre modal via ?open_dialog=refeicao|agua|supp (links da barra mobile)."""
    dlg = _qp_val("open_dialog")
    if not dlg or dlg not in ("refeicao", "editar", "agua", "supp"):
        return
    if dlg == "refeicao":
        st.session_state["_ref_busca_reset"] = True
    st.session_state["open_dialog"] = dlg
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()


def handle_nav_scroll_query():
    """Navega para secção do dashboard via ?scroll=sec-hoje (links da sidebar)."""
    sec = _qp_val("scroll")
    if not sec or not str(sec).startswith("sec-"):
        return
    st.session_state["_scroll_to"] = sec
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()


def render_mobile_quick_bar(
    on_dashboard: bool = False,
    on_refeicao: Optional[Callable[[], None]] = None,
    on_agua: Optional[Callable[[], None]] = None,
    on_supp: Optional[Callable[[], None]] = None,
):
    """Barra mobile — st.button (sem links que abrem nova aba)."""
    st.markdown(
        """
<style>
.sh-mob-quick-host{display:none!important;height:0!important;margin:0!important;padding:0!important}
html.sh-md .sh-mob-quick-bar,html.sh-lg .sh-mob-quick-bar{display:none!important}
html.sh-sm .sh-mob-quick-bar,html.sh-xs .sh-mob-quick-bar{display:block!important;margin:12px 0!important}
html.sh-sm .sh-mob-quick-bar [data-testid="stHorizontalBlock"],
html.sh-xs .sh-mob-quick-bar [data-testid="stHorizontalBlock"]{
  display:flex!important;gap:8px!important;flex-wrap:nowrap!important}
html.sh-sm .sh-mob-quick-bar [data-testid="stButton"],
html.sh-xs .sh-mob-quick-bar [data-testid="stButton"]{flex:1 1 0!important;width:auto!important;margin:0!important}
html.sh-sm .sh-mob-quick-bar button,html.sh-xs .sh-mob-quick-bar button{
  width:100%!important;min-height:44px!important;font-size:11px!important}
</style>
<div class="sh-mob-quick-host" aria-hidden="true"></div>
""",
        unsafe_allow_html=True,
    )

    def _dispatch(dlg: str, fn: Optional[Callable[[], None]]):
        if on_dashboard and fn:
            fn()
        elif not on_dashboard:
            st.session_state["open_dialog"] = dlg
            if dlg == "refeicao":
                st.session_state["_ref_busca_reset"] = True
            st.switch_page(DASHBOARD_PAGE)

    with st.container(horizontal=True):
        if st.button("➕ Refeição", key=f"mob_ref_{on_dashboard}"):
            _dispatch("refeicao", on_refeicao)
        if st.button("💧 Água", key=f"mob_agua_{on_dashboard}"):
            _dispatch("agua", on_agua)
        if st.button("💊 Suplemento", key=f"mob_supp_{on_dashboard}"):
            _dispatch("supp", on_supp)
    st.html(_MOB_QUICK_JS)


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
            '<div class="sh-side-section" style="margin-top:16px;padding-top:16px;'
            'border-top:1px solid var(--sh-border)">Ações rápidas</div>',
            unsafe_allow_html=True,
        )

        _render_quick_actions(active_page, quick_actions)

    _flush_pending_switch()
    inject_dialog_center_fix()
