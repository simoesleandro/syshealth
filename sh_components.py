"""Componentes HTML reutilizáveis — SYS.HEALTH design system."""
from __future__ import annotations

import streamlit as st

from sh_tokens import (
    BG2,
    BG_SUBTLE,
    BORDER,
    BORDER2,
    CYAN,
    GREEN,
    MONO,
    MUTED,
    RADIUS_MD,
    RADIUS_SM,
    SPACE_2,
    SPACE_3,
    SPACE_4,
    TEXT,
)


def sh_skip_link(target: str = "#sec-hoje", label: str = "Ir para o conteúdo principal") -> str:
    return f'<a class="sh-skip-link" href="{target}">{label}</a>'


def section_anchor(sec_id: str, label: str) -> str:
    """Âncora de seção com landmark ARIA para navegação por teclado."""
    safe = label.replace('"', "&quot;")
    return f'<div id="{sec_id}" role="region" aria-label="{safe}"></div>'


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


def sh_card(
    title: str,
    body: str = "",
    footer: str = "",
    icon: str = "",
) -> str:
    """Card informativo padrão (substitui divs inline)."""
    head = f"{icon} {title}".strip() if icon else title
    body_html = f'<div class="sh-card__body">{body}</div>' if body else ""
    foot_html = f'<div class="sh-card__footer">{footer}</div>' if footer else ""
    return (
        f'<div class="sh-card">'
        f'<div class="sh-card__title">{head}</div>'
        f'{body_html}{foot_html}</div>'
    )


def sh_empty_state(icon: str, title: str, hint: str = "") -> str:
    hint_html = f'<div class="sh-empty__hint">{hint}</div>' if hint else ""
    return (
        f'<div class="sh-empty">'
        f'<div class="sh-empty__icon">{icon}</div>'
        f'<div class="sh-empty__title">{title}</div>'
        f'{hint_html}</div>'
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


def panel(conteudo: str, extra: str = "") -> str:
    return f'<div class="sh-panel" style="{extra}">{conteudo}</div>'


def ptitl(txt: str) -> str:
    return f'<div class="sh-panel-title">{txt}</div>'


def pbar(pct: float, cor: str, h: int = 4) -> str:
    p = min(100, max(0, int(pct * 100)))
    return (
        f'<div class="sh-pbar" style="height:{h}px">'
        f'<div class="sh-pbar__fill" style="width:{p}%;height:{h}px;background:{cor}"></div>'
        f'</div>'
    )


def sec(tag: str, titulo: str) -> str:
    """Legado — preferir sh_section()."""
    return (
        f'<div style="display:flex;align-items:center;gap:10px;margin:18px 0 12px">'
        f'<span style="font-family:{MONO};font-size:12px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{CYAN};background:rgba(0,212,255,0.07);'
        f'border:1px solid rgba(0,212,255,0.2);border-radius:3px;padding:3px 8px">{tag}</span>'
        f'<span style="font-size:13px;color:{MUTED}">{titulo}</span>'
        f'<div style="flex:1;height:1px;background:{BORDER2}"></div>'
        f'</div>'
    )


def section_actions():
    """Linha horizontal de ações (gap 8px via CSS .sh-section-actions-mark)."""
    st.markdown('<div class="sh-section-actions-mark" aria-hidden="true"></div>', unsafe_allow_html=True)
    return st.container(horizontal=True, gap="small")


def sh_subheading(text: str) -> str:
    return (
        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;color:{MUTED};'
        f'margin:{SPACE_3}px 0 {SPACE_2}px">{text}</div>'
    )


def sh_stat_card(
    label: str,
    value: str,
    meta: str = "",
    value_color: str = "",
    accent: str = "",
) -> str:
    """KPI compacto — grid de estatísticas (inline styles para Streamlit markdown)."""
    top = accent or "rgba(255,255,255,.07)"
    val_color = value_color or TEXT
    meta_html = (
        f'<div style="font-size:10px;color:{MUTED};margin-top:4px">{meta}</div>'
        if meta
        else ""
    )
    return (
        f'<div class="sh-stat-card" style="background:{BG_SUBTLE};'
        f'border:1px solid rgba(255,255,255,.07);border-radius:{RADIUS_SM}px;'
        f'padding:{SPACE_3}px;text-align:center;border-top:2px solid {top}">'
        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1px;'
        f'text-transform:uppercase;color:{MUTED};margin-bottom:4px">{label}</div>'
        f'<div style="font-size:22px;font-weight:800;letter-spacing:-.03em;'
        f'color:{val_color};line-height:1.1">{value}</div>'
        f'{meta_html}</div>'
    )


def sh_stat_grid(*cards: str, cols: int = 3) -> str:
    inner = "".join(cards)
    tpl = "repeat(4,1fr)" if cols == 4 else "repeat(3,1fr)"
    return (
        f'<div class="sh-stat-grid sh-stat-grid--{cols}" '
        f'style="display:grid;grid-template-columns:{tpl};gap:{SPACE_2}px;'
        f'margin-bottom:{SPACE_2}px;width:100%">{inner}</div>'
    )


def sh_feature_panel(
    icon: str,
    title: str,
    subtitle: str,
    body_html: str,
    accent: str,
) -> str:
    return (
        f'<div class="sh-feature-panel" style="background:{BG2};'
        f'border:1px solid rgba(255,255,255,.07);border-radius:{RADIUS_MD}px;'
        f'border-top:3px solid {accent};padding:{SPACE_4}px;margin-bottom:{SPACE_2}px">'
        f'<div style="display:flex;align-items:center;gap:{SPACE_2}px">'
        f'<span style="font-size:16px">{icon}</span>'
        f'<div><div style="font-family:{MONO};font-size:10px;font-weight:700;'
        f'letter-spacing:1.5px;text-transform:uppercase;color:{accent}">{title}</div>'
        f'<div style="font-size:11px;color:{MUTED};margin-top:2px">{subtitle}</div>'
        f'</div></div>'
        f'<div style="height:1px;background:rgba(255,255,255,.07);margin:{SPACE_3}px 0"></div>'
        f'{body_html}</div>'
    )


def sh_chip_row(*chips: tuple[str, str]) -> str:
    """chips = (label com emoji, cor_hex)."""
    parts = [f'<span class="sh-chip" style="color:{c}">{t}</span>' for t, c in chips]
    return f'<div class="sh-chip-row">{"".join(parts)}</div>'


def sh_dose_row(data_fmt: str, dose: float, is_current: bool) -> str:
    dot = (
        f'<span style="width:6px;height:6px;border-radius:50%;flex-shrink:0;'
        f'background:{GREEN};box-shadow:0 0 5px rgba(0,230,118,.5)"></span>'
    )
    if is_current:
        return (
            f'<div class="sh-med-row" style="display:flex;align-items:center;gap:{SPACE_2}px;'
            f'padding:6px 10px;border-radius:5px;margin-bottom:2px;'
            f'background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.15)">'
            f'{dot}'
            f'<span style="font-family:{MONO};font-size:9px;color:{MUTED};flex:1">'
            f'{data_fmt}</span>'
            f'<span style="font-size:13px;font-weight:800;color:{GREEN};letter-spacing:-.03em">'
            f'{dose:.1f} mg</span>'
            f'<span style="font-family:{MONO};font-size:7px;font-weight:700;color:{GREEN};'
            f'background:rgba(0,230,118,.12);border:1px solid rgba(0,230,118,.25);'
            f'padding:1px 5px;border-radius:8px;letter-spacing:1px">ATUAL</span></div>'
        )
    return (
        f'<div class="sh-med-row" style="display:flex;align-items:center;gap:{SPACE_2}px;'
        f'padding:4px 10px;border-radius:5px;margin-bottom:2px;opacity:.6">'
        f'<span style="width:3px;height:3px;border-radius:50%;flex-shrink:0;'
        f'background:{MUTED}"></span>'
        f'<span style="font-family:{MONO};font-size:9px;color:{MUTED};flex:1">'
        f'{data_fmt}</span>'
        f'<span style="font-size:11px;font-weight:600;color:{MUTED};letter-spacing:-.03em">'
        f'{dose:.1f} mg</span></div>'
    )


def sh_treino_shell_open(accent: str) -> str:
    return f'<div class="sh-treino-shell" style="--sh-shell-accent:{accent}">'


def sh_treino_shell_close() -> str:
    return "</div>"


COMPONENTS_CSS = """
.sh-card{
  background:var(--sh-bg-elevated);border:1px solid var(--sh-border);
  border-radius:var(--sh-radius-md);padding:var(--sh-space-4);
  margin-bottom:var(--sh-space-3);
}
.sh-card__title{font-size:14px;color:var(--sh-text);font-weight:600;margin-bottom:var(--sh-space-2)}
.sh-card__body{font-size:12px;color:var(--sh-text-muted);line-height:1.5;margin-bottom:var(--sh-space-2)}
.sh-card__footer{
  display:flex;gap:var(--sh-space-4);font-family:var(--sh-font-mono);
  font-size:10px;color:var(--sh-text-dim);
}
.sh-panel{
  background:var(--sh-bg-elevated);border:1px solid var(--sh-border);
  border-radius:var(--sh-radius-md);padding:14px 16px;
}
.sh-panel-title{
  font-family:var(--sh-font-mono);font-size:13px;font-weight:700;
  letter-spacing:1px;text-transform:uppercase;color:var(--sh-text);margin-bottom:12px;
}
.sh-pbar{background:var(--sh-border);border-radius:3px;overflow:hidden;margin-top:8px}
.sh-pbar__fill{border-radius:3px}
.sh-empty{
  background:var(--sh-bg-elevated);border:1px solid var(--sh-border);
  border-radius:var(--sh-radius-md);padding:var(--sh-space-6) var(--sh-space-5);
  text-align:center;margin-bottom:var(--sh-space-4);
}
.sh-empty__icon{font-size:32px;margin-bottom:var(--sh-space-3)}
.sh-empty__title{
  font-family:var(--sh-font-mono);font-size:11px;font-weight:700;
  letter-spacing:1.5px;text-transform:uppercase;color:var(--sh-text-muted);
  margin-bottom:var(--sh-space-2);
}
.sh-empty__hint{font-size:12px;color:var(--sh-text-dim)}
.sh-subheading{
  font-family:var(--sh-font-mono);font-size:9px;font-weight:700;
  letter-spacing:1.5px;text-transform:uppercase;color:var(--sh-text-dim);
  margin:var(--sh-space-3) 0 var(--sh-space-2);
}
.sh-stat-grid{display:grid;gap:var(--sh-space-2);margin-bottom:var(--sh-space-2)}
.sh-stat-grid--4{grid-template-columns:repeat(4,1fr)}
.sh-stat-grid--3{grid-template-columns:repeat(3,1fr)}
.sh-stat-card{
  background:var(--sh-bg-subtle);border:1px solid var(--sh-border);
  border-radius:var(--sh-radius-sm);padding:var(--sh-space-3);
  text-align:center;border-top:2px solid var(--sh-stat-accent,var(--sh-border));
}
.sh-stat-card__label{
  font-family:var(--sh-font-mono);font-size:9px;font-weight:700;
  letter-spacing:1px;text-transform:uppercase;color:var(--sh-text-dim);
  margin-bottom:4px;
}
.sh-stat-card__value{
  font-size:22px;font-weight:800;letter-spacing:-.03em;color:var(--sh-text);
  line-height:1.1;
}
.sh-stat-card__meta{font-size:10px;color:var(--sh-text-dim);margin-top:4px}
.sh-feature-panel{
  background:var(--sh-bg-elevated);border:1px solid var(--sh-border);
  border-radius:var(--sh-radius-md);border-top:3px solid var(--sh-panel-accent);
  padding:var(--sh-space-4);margin-bottom:var(--sh-space-2);
}
.sh-feature-panel__head{display:flex;align-items:center;gap:var(--sh-space-2)}
.sh-feature-panel__icon{font-size:16px}
.sh-feature-panel__title{
  font-family:var(--sh-font-mono);font-size:10px;font-weight:700;
  letter-spacing:1.5px;text-transform:uppercase;color:var(--sh-panel-accent);
}
.sh-feature-panel__sub{font-size:11px;color:var(--sh-text-dim);margin-top:2px}
.sh-feature-panel__rule{height:1px;background:var(--sh-border);margin:var(--sh-space-3) 0}
.sh-chip-row{display:flex;gap:var(--sh-space-4);flex-wrap:wrap;margin-bottom:var(--sh-space-3)}
.sh-chip{font-family:var(--sh-font-mono);font-size:10px;font-weight:600}
.sh-dose-row{
  display:flex;align-items:center;gap:var(--sh-space-2);
  padding:4px 8px;border-radius:5px;margin-bottom:1px;
}
.sh-dose-row--current{
  background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.15);
}
.sh-dose-row--past{opacity:.55;padding:2px 8px}
.sh-dose-row__dot{
  width:6px;height:6px;border-radius:50%;flex-shrink:0;
  background:var(--sh-success);box-shadow:0 0 5px rgba(0,230,118,.5);
}
.sh-dose-row--past .sh-dose-row__dot{width:3px;height:3px;background:var(--sh-text-dim);box-shadow:none}
.sh-dose-row__date{
  font-family:var(--sh-font-mono);font-size:9px;color:var(--sh-text-dim);flex:1;
}
.sh-dose-row--current .sh-dose-row__date{color:var(--sh-text-muted)}
.sh-dose-row__val{font-size:13px;font-weight:800;color:var(--sh-success);letter-spacing:-.03em}
.sh-dose-row--past .sh-dose-row__val{font-size:11px;font-weight:600;color:var(--sh-text-muted)}
.sh-dose-row__badge{
  font-family:var(--sh-font-mono);font-size:7px;font-weight:700;color:var(--sh-success);
  background:rgba(0,230,118,.12);border:1px solid rgba(0,230,118,.25);
  padding:1px 5px;border-radius:8px;letter-spacing:1px;
}
.sh-treino-shell{
  background:var(--sh-bg-subtle);border:1px solid color-mix(in srgb,var(--sh-shell-accent) 20%,transparent);
  border-top:2px solid var(--sh-shell-accent);
  border-radius:0 0 var(--sh-radius-md) var(--sh-radius-md);
  padding:var(--sh-space-4);margin-bottom:var(--sh-space-3);
}
html.sh-sm .sh-stat-grid--4,html.sh-xs .sh-stat-grid--4{grid-template-columns:repeat(2,1fr)}
html.sh-xs .sh-stat-grid--3,html.sh-sm .sh-stat-grid--3{grid-template-columns:1fr}
"""
