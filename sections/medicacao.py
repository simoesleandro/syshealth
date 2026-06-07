"""Seção Medicação — Tirzepatida."""
from __future__ import annotations

from datetime import date as _date
from datetime import datetime as _datetime
from datetime import timedelta as _td
from typing import Callable

import streamlit as st

from sh_components import (
    section_actions,
    sh_dose_row,
    sh_feature_panel,
    sh_stat_card,
    sh_stat_grid,
    sh_subheading,
)
from sh_tokens import BG_SUBTLE, RADIUS_SM, SPACE_2, SPACE_3
from sh_tokens import AMBER, GREEN, PURPLE, TEXT


def med_doses_list(df_med) -> list[dict]:
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


def render_medicacao_section(
    hoje_sql: str,
    df_med,
    *,
    edit_icon: str,
    on_nova: Callable[[], None],
    on_edit: Callable[[], None],
    on_edit_dose: Callable[[int], None],
) -> None:
    """Card + timeline; registro/edição via modais no dashboard."""
    doses = med_doses_list(df_med)

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

    stats = sh_stat_grid(
        sh_stat_card("Dose Atual", f"{dose_atual:.1f}", "mg / semana", value_color=GREEN, accent=GREEN),
        sh_stat_card("Aplicações", str(n_doses), "doses totais", value_color=PURPLE, accent=PURPLE),
        sh_stat_card("Semanas", str(semanas), "em protocolo", value_color=AMBER, accent=AMBER),
        sh_stat_card("Próxima", proxima, "estimativa", value_color=TEXT),
        cols=4,
    )

    st.markdown(
        sh_feature_panel(
            "💊",
            "Tirzepatida",
            "Protocolo farmacológico · injetável semanal",
            stats,
            PURPLE,
        ),
        unsafe_allow_html=True,
    )

    with section_actions():
        if st.button("➕ Nova dose", key="btn_med_nova", use_container_width=False, help="Registrar nova dose de Tirzepatida"):
            on_nova()
        if st.button(
            "Editar dose",
            key="btn_med_edit",
            use_container_width=False,
            icon=edit_icon,
            disabled=not doses,
            help="Editar dose selecionada",
        ):
            on_edit()

    st.markdown('<div class="sh-med-hdr"></div>', unsafe_allow_html=True)
    st.markdown(sh_subheading("Histórico de doses"), unsafe_allow_html=True)

    if not doses:
        st.markdown(
            '<p style="font-size:12px;color:#6b7c93;margin:4px 0">Sem registros.</p>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div style="background:{BG_SUBTLE};border:1px solid rgba(255,255,255,.07);'
        f'border-radius:{RADIUS_SM}px;padding:{SPACE_2}px {SPACE_3}px;margin-top:{SPACE_2}px">',
        unsafe_allow_html=True,
    )

    for i, item in enumerate(doses):
        mid = item["id"]
        _mc, _me = st.columns([1, 0.07])
        with _mc:
            st.markdown(
                sh_dose_row(item["fmt"], item["dose"], is_current=(i == 0)),
                unsafe_allow_html=True,
            )
        with _me:
            if st.button(
                "",
                key=f"tog_med_{mid}",
                use_container_width=False,
                icon=edit_icon,
                help=f"Editar dose de {item['fmt']}",
            ):
                on_edit_dose(mid)

    st.markdown("</div>", unsafe_allow_html=True)
