# -*- coding: utf-8 -*-
"""v4: scroll + âncoras, remove páginas CSS."""
from pathlib import Path
import re

p = Path(__file__).parent / "dashboard.py"
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
text = "".join(lines)

text = text.replace(
    '_APP_BUILD = "2026-06-03-premium-v3"',
    '_APP_BUILD = "2026-06-03-scroll-v4"',
)

# Remove page-nav + page-block CSS
text = re.sub(
    r"\.sh-page-nav\{[^}]+\}\n"
    r"\.sh-page-nav \[data-testid=\"stHorizontalBlock\"\]\{[^}]+\}\n"
    r"\.sh-page-nav button\[data-testid=\"stBaseButton-primary\"\]\{[^}]+\}\n"
    r"\.sh-page-nav button\[data-testid=\"stBaseButton-secondary\"\]\{[^}]+\}\n",
    "",
    text,
    count=1,
)
text = re.sub(
    r"\.sh-page-block\{display:none!important\}\n"
    r"html\[data-sh-page=\"visao\"\][^\n]+\n"
    r"html\[data-sh-page=\"registrar\"\][^\n]+\n"
    r"html\[data-sh-page=\"analise\"\][^\n]+\n"
    r"html\[data-sh-page=\"mais\"\][^\n]+\n",
    "",
    text,
    count=1,
)

# Remove page helpers
text = re.sub(
    r"\ndef _sh_page_open\(page: str\) -> None:.*?def _sh_page_nav\(\) -> None:.*?\n    _sh_sync_page_attr\(\)\n\n",
    "\n",
    text,
    count=1,
    flags=re.DOTALL,
)

# Nav call
text = text.replace("_painel_entrada()\n_sh_page_nav()\n\n# ── Sidebar", "_painel_entrada()\n\n# ── Sidebar")

# Page wrappers
for s in [
    '_sh_page_open("visao")\n',
    '_sh_page_open("registrar")\n',
    '_sh_page_open("analise")\n',
    '_sh_page_open("mais")\n',
    "sh_lane_close()\n",
    "_sh_page_close()\n",
]:
    text = text.replace(s, "")

# Hoje section
text = text.replace(
    'st.markdown(sh_lane("Visão do dia", "Nutrição, wearable e agenda"), unsafe_allow_html=True)\n\n',
    'st.markdown(\'<div id="sec-hoje"></div>\', unsafe_allow_html=True)\n'
    'st.markdown(sh_section("Hoje", f"Resumo · {hoje_pt}"), unsafe_allow_html=True)\n\n',
)

# Redundant nutri section title inside tab
text = text.replace(
    "    st.markdown('<div id=\"sec-nutricao\"></div>', unsafe_allow_html=True)\n"
    "    st.markdown(sh_section(\"Nutrição\", \"Metas do dia\"), unsafe_allow_html=True)\n",
    "    st.markdown('<div id=\"sec-nutricao\"></div>', unsafe_allow_html=True)\n",
    count=1,
)

# Banners
text = re.sub(
    r"st\.markdown\(\n"
    r"    f'<div style=\"font-family:\{MONO\};font-size:8px;font-weight:700;letter-spacing:2\.5px;'\n"
    r"    f'text-transform:uppercase;color:\{GHOST\};margin:24px 0 10px;'\n"
    r"    f'padding:6px 10px;background:[^']+;'\n"
    r"    f'border-left:2px solid [^']+;'\n"
    r"    f'border-radius:0 4px 4px 0'>▸[^<]+</div>',\n"
    r"    unsafe_allow_html=True,\n\)\n\n",
    "",
    text,
)

# Registros anchor
text = text.replace(
    "# ── BLOCO: REGISTROS ─────────────────────────────────────────────────────────\n"
    "# ════════════════════════════════════════════════════════════════════════════\n"
    "# SEÇÃO 4 — EVOLUÇÃO",
    "st.markdown('<div id=\"sec-registros\"></div>', unsafe_allow_html=True)\n"
    "st.markdown(sh_section(\"Registros\", \"Refeições e suplementação\"), unsafe_allow_html=True)\n\n"
    "# ════════════════════════════════════════════════════════════════════════════\n"
    "# SEÇÃO 4 — EVOLUÇÃO",
    count=1,
)

# Treinos anchor
text = text.replace(
    "# PAINEL — DETALHES DOS TREINOS (Hevy)",
    "st.markdown('<div id=\"sec-treinos\"></div>', unsafe_allow_html=True)\n"
    "st.markdown(sh_section(\"Treinos\", \"Hevy e corridas\"), unsafe_allow_html=True)\n\n"
    "# PAINEL — DETALHES DOS TREINOS (Hevy)",
    count=1,
)

text = text.replace(
    'st.markdown(sec("Evolução", "Peso histórico · Macros do dia"), unsafe_allow_html=True)',
    'st.markdown(sh_section("Evolução", "Peso histórico e macros"), unsafe_allow_html=True)',
    count=1,
)
text = text.replace(
    'st.markdown(sec("Histórico", "Últimos 30 dias · Tendências"), unsafe_allow_html=True)',
    'st.markdown(sh_section("Histórico", "Últimos 30 dias e tendências"), unsafe_allow_html=True)',
    count=1,
)

# Dedent biometria blocks
out = []
i = 0
n = len(text.splitlines(keepends=True))
raw_lines = text.splitlines(keepends=True)
while i < n:
    line = raw_lines[i]
    if line.startswith("if True:  # página Mais: biometria e correlatos\n"):
        i += 1
        while i < n:
            ln = raw_lines[i]
            if ln.startswith("# ════════════════════════════════════════════════════════════════════════════\n") and "EVACUAÇÃO" in (raw_lines[i + 1] if i + 1 < n else ""):
                break
            if ln.startswith("# ════════════════════════════════════════════════════════════════════════════\n") and i + 1 < n and "EVACUAÇÃO" in raw_lines[i + 1]:
                break
            if ln.startswith("# ════════════════════════════════════════════════════════════════════════════\n") and "SEÇÃO 6 — EVACUAÇÃO" in "".join(raw_lines[i : i + 3]):
                break
            if ln.startswith("# ════════════════════════════════════════════════════════════════════════════\n"):
                peek = "".join(raw_lines[i : min(i + 4, n)])
                if "EVACUAÇÃO" in peek:
                    break
            if ln.startswith("if True:  # bloco de escopo para df_bio\n"):
                i += 1
                while i < n:
                    ln2 = raw_lines[i]
                    if ln2.startswith("# ════════════════════════════════════════════════════════════════════════════\n"):
                        peek = "".join(raw_lines[i : min(i + 4, n)])
                        if "EVACUAÇÃO" in peek:
                            break
                    if ln2.startswith("# ══") and "EVACUAÇÃO" in "".join(raw_lines[i : i + 3]):
                        break
                    if ln2.startswith("    "):
                        out.append(ln2[4:])
                    else:
                        out.append(ln2)
                    i += 1
                continue
            if ln.startswith("    "):
                out.append(ln[4:])
            else:
                out.append(ln)
            i += 1
        continue
    out.append(line)
    i += 1

text = "".join(out)

# Sidebar: replace page buttons block (done via separate patch if pattern fails)
old_sb = """    st.markdown(f'<div style="font-size:11px;font-weight:600;color:{MUTED};margin:8px 0 8px">Navegação</div>', unsafe_allow_html=True)
    for _pk, _pl, _pi in [("visao","Visão","🎯"),("registrar","Registrar","📝"),("analise","Análise","📊"),("mais","Mais","⚙️")]:
        if st.button(f"{_pi} {_pl}", key=f"sb_page_{_pk}", use_container_width=True, type="primary" if st.session_state.get("sh_page","visao")==_pk else "secondary"):
            st.session_state["sh_page"] = _pk
            st.rerun()

    # ── Toggle Avançado"""

new_sb = """    st.markdown(
        f'<div class="sh-side-kpis">'
        f'<div class="sh-side-kpi"><span class="sh-side-kpi__l">Calorias</span>'
        f'<span class="sh-side-kpi__v" style="color:{CYAN}">{int(cal_h):,}</span></div>'
        f'<div class="sh-side-kpi"><span class="sh-side-kpi__l">Proteína</span>'
        f'<span class="sh-side-kpi__v" style="color:{RED}">{int(prot_h)}g</span></div>'
        f'<div class="sh-side-kpi"><span class="sh-side-kpi__l">Água</span>'
        f'<span class="sh-side-kpi__v" style="color:#a78bfa">{agua_l:.1f}L</span></div>'
        f'<div class="sh-side-kpi"><span class="sh-side-kpi__l">Balanço</span>'
        f'<span class="sh-side-kpi__v" style="color:{def_cor}">{def_txt}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f'<div style="font-size:11px;font-weight:600;color:{MUTED};margin:12px 0 8px">Seções</div>', unsafe_allow_html=True)
    _nav_main = [
        ("sec-hoje", "🎯", "Hoje"),
        ("sec-evolucao", "📈", "Evolução"),
        ("sec-registros", "📝", "Registros"),
        ("sec-treinos", "🏋️", "Treinos"),
        ("sec-banco", "🍽️", "Banco"),
        ("sec-historico", "📊", "Histórico"),
    ]
    _nav_html = ""
    for _anc, _ic, _lb in _nav_main:
        _nav_html += (
            f'<a href="#{_anc}" class="sh-nav-link" style="display:flex;align-items:center;gap:8px;'
            f'padding:8px 10px;border-radius:6px;text-decoration:none;margin-bottom:4px;'
            f'font-size:13px;font-weight:600;color:{TEXT};background:transparent;'
            f'border:1px solid {BORDER}">'
            f'<span>{_ic}</span><span>{_lb}</span></a>'
        )
    st.markdown(_nav_html, unsafe_allow_html=True)

    # ── Toggle Avançado"""

text = text.replace(old_sb, new_sb)

old_card = """    st.markdown(
        f'<div class="sh-side-card">'
        f'<div style="font-size:10px;color:{MUTED};margin-bottom:4px">{hoje_pt}</div>'
        f'<div style="font-size:12px;color:{TEXT}">Métricas na aba <b style="color:{CYAN}">Visão</b></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

"""

text = text.replace(old_card, "")

# Advanced nav links
text = text.replace(
    """        _sec_av = [
            ("sec-ia",        "🤖", "IA Coach"),
            ("sec-biometria", "📏", "Biometria"),
            ("sec-medicacao", "💊", "Medicação"),
        ]""",
    """        _sec_av = [
            ("sec-medicacao", "💊", "Medicação"),
            ("sec-biometria", "📏", "Biometria"),
            ("sec-evacuacao", "🚽", "Evacuação"),
            ("sec-ia",        "🤖", "IA Coach"),
        ]""",
)

# v4 responsive + anchor CSS (before closing </style> in _app_global_css)
v4_css = """
/* ── v4: âncoras + scroll contínuo ── */
div[id^="sec-"]{scroll-margin-top:72px}
.sh-nav-link{text-transform:none!important;transition:border-color .15s,color .15s!important}
.sh-nav-link:hover{border-color:rgba(0,212,255,.35)!important;color:var(--sh-accent)!important}
a.sh-nav-active.sh-nav-link{border-color:rgba(0,212,255,.4)!important;background:rgba(0,212,255,.08)!important}
.sh-side-kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:4px}
.sh-side-kpi{background:var(--sh-bg-subtle);border:1px solid var(--sh-border);border-radius:var(--sh-radius-sm);padding:8px 10px}
.sh-side-kpi__l{display:block;font-size:9px;color:var(--sh-text-dim);text-transform:none;letter-spacing:0}
.sh-side-kpi__v{display:block;font-family:var(--sh-font-mono);font-size:12px;font-weight:700;margin-top:2px}
section[data-testid="stSidebar"] .stButton button{text-transform:none!important;letter-spacing:0!important;font-size:12px!important}
button[data-baseweb="tab"]{text-transform:none!important;letter-spacing:.02em!important;font-size:12px!important}
html.sh-sm .sh-metric--hero,html.sh-xs .sh-metric--hero{min-height:140px}
html.sh-sm [data-testid="stHorizontalBlock"]:has(.sh-metric--hero)>[data-testid="column"],
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-metric--hero)>[data-testid="column"]{flex:1 1 100%!important}
html.sh-md [data-testid="stHorizontalBlock"]:has(.sh-metric--compact)>[data-testid="column"]{flex:1 1 calc(33.33% - 8px)!important}
html.sh-sm [data-testid="stHorizontalBlock"]:has(.sh-metric--compact)>[data-testid="column"],
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-metric--compact)>[data-testid="column"]{flex:1 1 calc(50% - 8px)!important}
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-metric--compact)>[data-testid="column"]:only-child,
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-metric--hero)>[data-testid="column"]{flex:1 1 100%!important}
.sh-toolbar-wrap [data-testid="stHorizontalBlock"]{flex-wrap:wrap!important}
html.sh-sm .sh-toolbar-wrap [data-testid="column"],html.sh-xs .sh-toolbar-wrap [data-testid="column"]{flex:1 1 100%!important}
@media(max-width:768px){
  div[id^="sec-"]{scroll-margin-top:56px}
  [data-testid="stTabs"] [role="tablist"]{overflow-x:auto!important;flex-wrap:nowrap!important;-webkit-overflow-scrolling:touch}
  button[data-baseweb="tab"]{flex:0 0 auto!important;white-space:nowrap!important}}
@media(max-width:480px){
  .sh-side-kpis{grid-template-columns:1fr!important}
  div[id^="sec-"]{scroll-margin-top:48px}}

"""
if "div[id^=\"sec-\"]{scroll-margin-top:72px}" not in text:
    text = text.replace(
        "/* ── Overlay semitransparente atrás do sidebar aberto em mobile ── */",
        v4_css + "/* ── Overlay semitransparente atrás do sidebar aberto em mobile ── */",
    )

# Observer: add sh-nav-link class to active links
text = text.replace(
    "      var active = document.querySelector('a[href=\"#' + id + '\"]');",
    "      var active = document.querySelector('a.sh-nav-link[href=\"#' + id + '\"]') || document.querySelector('a[href=\"#' + id + '\"]');",
)

p.write_text(text, encoding="utf-8")
print("v4 applied")
