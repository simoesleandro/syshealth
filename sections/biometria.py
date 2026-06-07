"""Seção Biometria — tabelas de evolução corporal."""
from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

from sh_components import panel, ptitl, section_actions
from sh_tokens import BG, BG2, BG3, BORDER, BORDER2, CYAN, GHOST, GREEN, MONO, MUTED, RED, TEXT

_COLS_NUM = [
    "peso", "cintura", "abdomen", "peitoral", "quadril",
    "coxa_dir", "coxa_esq", "panturrilha_dir", "panturrilha_esq", "biceps_dir", "biceps_esq",
]


def render_biometria_section(
    df_bio: pd.DataFrame,
    *,
    edit_icon: str,
    on_nova: Callable[[], None],
    on_edit: Callable[[], None],
) -> None:
    """Ações + tabelas tronco/membro (modais no dashboard)."""
    with section_actions():
        if st.button("📏 Nova medida", key="btn_bio_nova", use_container_width=False, help="Registrar nova medida corporal"):
            on_nova()
        if not df_bio.empty:
            if st.button(
                "Editar medida",
                key="btn_bio_edit",
                use_container_width=False,
                icon=edit_icon,
                help="Editar medida corporal",
            ):
                on_edit()

    if df_bio.empty:
        return

    df_work = df_bio.sort_values("data_ord", ascending=True)
    idx_rec = df_work.index[-1]
    diffs: dict[str, float] = {}
    for c in _COLS_NUM:
        atual = df_work.loc[idx_rec, c]
        if pd.isna(atual):
            diffs[c] = 0
        else:
            dm = atual - df_work[c].max()
            dn = atual - df_work[c].min()
            diffs[c] = dm if abs(dm) >= abs(dn) else dn

    df_work = df_work.sort_values("data_ord", ascending=False)

    _td = (
        "padding:7px 6px;border-bottom:1px solid #0a1020;"
        "text-align:center;vertical-align:middle;"
    )
    _tdr = _td + "background:rgba(0,212,255,0.06);"

    def cel(val, diff, peso=False, rec=False):
        base = _tdr if rec else _td
        if pd.isna(val):
            return f"<td style='{base}color:{GHOST}'>—</td>"
        fmt = f"{val:.1f}"
        un = "kg" if peso else "cm"
        cor = CYAN if rec else TEXT
        num = f"<b style='font-size:13px;font-weight:700;color:{cor}'>{fmt}</b>"
        if rec and diff:
            arrow = "▼" if diff < 0 else "▲"
            diff_color = GREEN if diff < 0 else RED
            delta = (
                f"<span style='color:{diff_color};font-size:10px;"
                f"display:block;margin-top:1px;font-weight:600'>"
                f"{arrow} {abs(diff):.1f}{un}</span>"
            )
            return f"<td style='{base}'>{num}{delta}</td>"
        return f"<td style='{base}'>{num}</td>"

    _th = (
        f"font-family:{MONO};background:{BG3};color:{MUTED};"
        f"padding:9px 6px;border-bottom:2px solid {BORDER2};"
        f"text-transform:uppercase;font-size:10px;letter-spacing:1.5px;"
        f"text-align:center;white-space:nowrap;font-weight:400"
    )

    def _td_data(row, rec):
        badge = (
            f'<span style="background:{CYAN};color:{BG};font-size:8px;'
            f'font-family:{MONO};font-weight:900;padding:1px 4px;border-radius:2px;'
            f'letter-spacing:1px;margin-left:5px;vertical-align:middle">ATUAL</span>'
            if rec
            else ""
        )
        left_bdr = f"border-left:2px solid {CYAN};" if rec else ""
        bg = "background:rgba(0,212,255,0.06);" if rec else ""
        cor = CYAN if rec else GHOST
        wt = "700" if rec else "400"
        return (
            f"<td style='{_td}{bg}{left_bdr}'>"
            f"<span style='font-family:{MONO};font-size:11px;color:{cor};"
            f"font-weight:{wt};white-space:nowrap'>{row['data_fmt']}{badge}</span></td>"
        )

    _cg1 = '<colgroup><col style="width:95px">' + '<col style="width:68px">' * 5 + "</colgroup>"
    _cg2 = '<colgroup><col style="width:95px">' + '<col style="width:68px">' * 6 + "</colgroup>"
    _tbl = f"width:100%;border-collapse:collapse;table-layout:fixed;background:{BG2}"

    bio_tab1, bio_tab2 = st.tabs(["🏛️ Tronco · Composição", "💪 Membros"])

    with bio_tab1:
        heads_t1 = ["Data", "Peso", "Cintura", "Abdômen", "Peitoral", "Quadril"]
        ths1 = "".join(f"<th style='{_th}'>{h}</th>" for h in heads_t1)
        body1 = ""
        for i, (_, row) in enumerate(df_work.iterrows()):
            rec = i == 0
            body1 += f"<tr>{_td_data(row, rec)}"
            body1 += cel(row["peso"], diffs["peso"], peso=True, rec=rec)
            for c in ["cintura", "abdomen", "peitoral", "quadril"]:
                body1 += cel(row[c], diffs[c], rec=rec)
            body1 += "</tr>"
        st.markdown(
            panel(
                ptitl("Evolução — Tronco & Composição Corporal")
                + f'<div class="sh-table-scroll" style="border-radius:6px;border:1px solid {BORDER}">'
                f'<table style="{_tbl}">{_cg1}'
                f"<thead><tr>{ths1}</tr></thead>"
                f"<tbody>{body1}</tbody></table></div>"
            ),
            unsafe_allow_html=True,
        )

    with bio_tab2:
        heads_t2 = ["Data", "Coxa D", "Coxa E", "Pant. D", "Pant. E", "Bíceps D", "Bíceps E"]
        ths2 = "".join(f"<th style='{_th}'>{h}</th>" for h in heads_t2)
        body2 = ""
        for i, (_, row) in enumerate(df_work.iterrows()):
            rec = i == 0
            body2 += f"<tr>{_td_data(row, rec)}"
            for c in [
                "coxa_dir", "coxa_esq", "panturrilha_dir",
                "panturrilha_esq", "biceps_dir", "biceps_esq",
            ]:
                body2 += cel(row[c], diffs[c], rec=rec)
            body2 += "</tr>"
        st.markdown(
            panel(
                ptitl("Evolução — Membros")
                + f'<div class="sh-table-scroll" style="border-radius:6px;border:1px solid {BORDER}">'
                f'<table style="{_tbl}">{_cg2}'
                f"<thead><tr>{ths2}</tr></thead>"
                f"<tbody>{body2}</tbody></table></div>"
            ),
            unsafe_allow_html=True,
        )
