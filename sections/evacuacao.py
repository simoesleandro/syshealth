"""Seção Evacuação — resumo, ações e histórico."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

import pandas as pd
import streamlit as st
from zoneinfo import ZoneInfo

from sh_components import panel, section_actions, sh_feature_panel, sh_stat_card, sh_stat_grid
from sh_tokens import AMBER, BG2, BG3, BORDER, CYAN, GREEN, MONO, MUTED, PURPLE, RED, TEXT

_BR = ZoneInfo("America/Sao_Paulo")
_ESFORCO_COR = ["#00e676", "#7ed321", "#fde047", "#fbbf24", "#f97316", "#ff6b6b"]
_ESFORCO_LABEL = ["0 · suave", "1 · normal", "2 · leve+", "3 · grande", "4 · sangrou", "5 · máximo"]


def render_evacuacao_summary(ev_df: pd.DataFrame) -> None:
    """Cards KPI ou empty panel."""
    if ev_df.empty:
        st.markdown(
            panel('<p class="sh-empty__hint" style="padding:8px 0">'
                  'Nenhum registro ainda. Use o botão abaixo para começar a monitorar.</p>'),
            unsafe_allow_html=True,
        )
        return

    ev_datas = pd.to_datetime(ev_df["data_hora"])
    ev_ultima = ev_datas.iloc[0]
    agora_brt = datetime.now(_BR)
    ev_dias_sem = (agora_brt - ev_ultima.replace(tzinfo=_BR)).days
    ev_horas_sem = int((agora_brt - ev_ultima.replace(tzinfo=_BR)).total_seconds() / 3600)

    if len(ev_datas) >= 2:
        ev_diffs = ev_datas.diff(-1).dropna().abs()
        ev_media_dias = ev_diffs.mean().total_seconds() / 3600 / 24
        ev_media_txt = f"{ev_media_dias:.1f} dias"
    else:
        ev_media_txt = "—"

    ev_cor_alerta = RED if ev_dias_sem >= 3 else (AMBER if ev_dias_sem >= 2 else GREEN)
    ev_status_txt = (
        f"⚠️ {ev_dias_sem} dias sem evacuar!" if ev_dias_sem >= 3
        else f"🟡 {ev_dias_sem} dia(s) sem evacuar" if ev_dias_sem >= 2
        else f"✓ Último registro há {ev_horas_sem}h"
    )

    stats = sh_stat_grid(
        sh_stat_card(
            "Última evacuação",
            f"{ev_dias_sem}d",
            ev_status_txt,
            value_color=ev_cor_alerta,
            accent=ev_cor_alerta,
        ),
        sh_stat_card("Intervalo médio", ev_media_txt, "entre registros", value_color=CYAN, accent=CYAN),
        sh_stat_card("Total registrado", str(len(ev_df)), "evacuações", value_color=PURPLE, accent=PURPLE),
        cols=3,
    )
    st.markdown(
        sh_feature_panel(
            "🚽",
            "Resumo intestinal",
            "Intervalo entre registros e alertas",
            stats,
            CYAN,
        ),
        unsafe_allow_html=True,
    )


def render_evacuacao_actions(
    on_register: Callable[[], None],
    toggle_fn: Callable[[str, str, str, str], None],
) -> None:
    """Botões registrar + toggle histórico."""
    with section_actions():
        if st.button("🚽 Registrar evacuação", key="btn_evac_nova", use_container_width=False, help="Registrar nova evacuação"):
            on_register()
        toggle_fn(
            "📋 Histórico de evacuações ▴",
            "📋 Histórico de evacuações ▾",
            "evac_hist_open",
            "btn_evac_hist",
        )


def render_evacuacao_history(ev_df: pd.DataFrame) -> None:
    """Tabela de histórico + exclusão do último registro."""
    if ev_df.empty:
        return

    ev_show = ev_df.copy()
    ev_show["data_hora_fmt"] = pd.to_datetime(ev_show["data_hora"]).dt.strftime("%d/%m/%Y  %H:%M")
    ev_show["observacao"] = ev_show["observacao"].fillna("—")

    ev_dts_ord = pd.to_datetime(ev_show["data_hora"]).reset_index(drop=True)
    intervalos = []
    for i in range(len(ev_dts_ord)):
        if i < len(ev_dts_ord) - 1:
            diff = (ev_dts_ord[i] - ev_dts_ord[i + 1]).total_seconds() / 3600
            intervalos.append(f"{diff / 24:.1f}d ({int(diff)}h)")
        else:
            intervalos.append("—")
    ev_show["intervalo"] = intervalos

    rows_html = ""
    for _, row in ev_show.iterrows():
        esf = int(row["esforco"]) if row["esforco"] is not None and not pd.isna(row["esforco"]) else 0
        esf_cor = _ESFORCO_COR[min(esf, 5)]
        esf_lbl = _ESFORCO_LABEL[min(esf, 5)]
        pct = esf / 5 * 100
        rows_html += (
            f'<tr style="border-bottom:1px solid {BORDER}">'
            f'<td style="padding:8px 12px;font-family:{MONO};font-size:12px;color:{TEXT}">{row["data_hora_fmt"]}</td>'
            f'<td style="padding:8px 12px;font-family:{MONO};font-size:12px;color:{CYAN};text-align:center">{row["intervalo"]}</td>'
            f'<td style="padding:6px 12px;min-width:110px">'
            f'<div style="font-family:{MONO};font-size:11px;font-weight:700;color:{esf_cor};margin-bottom:4px">{esf_lbl}</div>'
            f'<div style="height:5px;border-radius:3px;background:{BORDER};overflow:hidden">'
            f'<div style="height:100%;width:{pct:.0f}%;border-radius:3px;'
            f'background:linear-gradient(to right,#00e676,#7ed321,#fde047,#fbbf24,#f97316,#ff6b6b);'
            f'background-size:{100 / (pct / 100) if pct > 0 else 100:.0f}% 100%"></div>'
            f'</div></td>'
            f'<td style="padding:8px 12px;font-size:12px;color:{MUTED}">{row["observacao"]}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="sh-table-scroll" style="background:{BG2};border:1px solid {BORDER};'
        f'border-radius:8px;overflow:hidden;margin-top:8px">'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="background:{BG3};border-bottom:2px solid {BORDER}">'
        f'<th style="padding:8px 12px;font-family:{MONO};font-size:10px;color:{MUTED};text-align:left">DATA / HORA</th>'
        f'<th style="padding:8px 12px;font-family:{MONO};font-size:10px;color:{MUTED};text-align:center">INTERVALO</th>'
        f'<th style="padding:8px 12px;font-family:{MONO};font-size:10px;color:{MUTED};text-align:center">ESFORÇO</th>'
        f'<th style="padding:8px 12px;font-family:{MONO};font-size:10px;color:{MUTED};text-align:left">OBSERVAÇÃO</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def render_evacuacao_delete(
    ev_df: pd.DataFrame,
    *,
    on_confirm: Callable[[int], None],
    on_cancel: Callable[[], None],
    on_request_delete: Callable[[], None],
) -> None:
    """Confirmação de exclusão do último registro."""
    if ev_df.empty:
        return

    if st.session_state.get("evac_del_confirm", False):
        with section_actions():
            if st.button("✓ Confirmar exclusão", key="evac_del_ok", use_container_width=False):
                on_confirm(int(ev_df["id"].iloc[0]))
            if st.button("✗ Cancelar", key="evac_del_cancel", use_container_width=False):
                on_cancel()
    else:
        with section_actions():
            if st.button("🗑 Excluir último registro", key="evac_del_btn", use_container_width=False):
                on_request_delete()
