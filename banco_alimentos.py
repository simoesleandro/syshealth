"""Página do Banco de Alimentos — cadastro, edição e favoritos."""
import html as html_mod
import json
import os

import pandas as pd
import streamlit as st

try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

import db as DB
from sh_tokens import DELETE_ICON, EDIT_ICON, STAR_ICON, STAR_OUTLINE_ICON
from sh_tokens import AMBER, BG, BG2, BG3, BORDER, BORDER2, CYAN, GHOST, GREEN, MONO, MUTED, PURPLE, TEXT

_BANCO_HIT_CSS = f"""
<style>
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]{{
  align-items:center!important;gap:10px!important;margin:0!important;
  padding:8px 10px!important;border-bottom:1px solid {BORDER2}!important;
  background:{BG2}!important;border-radius:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:first-child{{
  min-width:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child{{
  flex:0 0 auto!important;width:auto!important;min-width:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stVerticalBlock"]{{
  gap:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"]{{
  gap:8px!important;flex-wrap:nowrap!important;justify-content:flex-end!important;
  width:auto!important;margin:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"]>[data-testid="column"]{{
  flex:0 0 32px!important;width:32px!important;min-width:32px!important;max-width:32px!important;
  padding:0!important;margin:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] [data-testid="stButton"]{{
  margin:0!important;padding:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] button{{
  min-width:32px!important;max-width:32px!important;width:32px!important;
  min-height:32px!important;max-height:32px!important;height:32px!important;
  padding:0!important;margin:0!important;display:inline-flex!important;
  align-items:center!important;justify-content:center!important;
  border-radius:8px!important;background:{BG3}!important;
  border:1px solid {BORDER}!important;color:{TEXT}!important;
  font-size:16px!important;line-height:1!important;letter-spacing:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] button:hover{{
  border-color:rgba(0,212,255,.45)!important;color:{CYAN}!important;
  background:rgba(0,212,255,.08)!important;transform:none!important;
  box-shadow:none!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] button p,
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] button div{{
  margin:0!important;padding:0!important;line-height:1!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] button svg,
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] [data-testid="stIconMaterial"]{{
  width:16px!important;height:16px!important;font-size:16px!important;color:{TEXT}!important;
  fill:currentColor!important;margin:0!important}}
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] button:hover svg,
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"]>[data-testid="column"]:last-child [data-testid="stHorizontalBlock"] button:hover [data-testid="stIconMaterial"]{{
  color:{CYAN}!important}}
</style>
"""


def _invalidate_cache(*funcs):
    for fn in funcs:
        fn.clear()


@st.cache_data(ttl=300)
def _q_alimentos_favoritos():
    try:
        return DB.query(
            "SELECT id,descricao,categoria,calorias,proteinas,carboidratos,gorduras,componentes_json,favorito,vezes_usado,"
            "COALESCE(qtd_referencia,100) as qtd_referencia,COALESCE(unidade_referencia,'g') as unidade_referencia "
            "FROM alimentos_favoritos ORDER BY favorito DESC, vezes_usado DESC"
        )
    except Exception:
        df = DB.query(
            "SELECT id,descricao,categoria,calorias,proteinas,carboidratos,gorduras,componentes_json,favorito,vezes_usado "
            "FROM alimentos_favoritos ORDER BY favorito DESC, vezes_usado DESC"
        )
        df["qtd_referencia"] = 100.0
        df["unidade_referencia"] = "g"
        return df


def _notif(msg: str, tipo: str = "ok"):
    st.session_state["_notif_pending"] = (msg, tipo)


def _render_notif():
    if "_notif_pending" not in st.session_state:
        return
    msg, tipo = st.session_state.pop("_notif_pending")
    cor = {"ok": GREEN, "err": "#ff6b6b", "info": CYAN}.get(tipo, GREEN)
    if tipo == "ok":
        st.toast(msg, icon="✅")
    else:
        st.toast(msg)


def _open_dialog_on_dashboard(dialog: str):
    st.session_state["open_dialog"] = dialog
    st.switch_page("dashboard.py")


def _qp_val(key: str):
    """Lê query param (Streamlit pode devolver str ou lista)."""
    val = st.query_params.get(key)
    if isinstance(val, list):
        return val[0] if val else None
    return val


def _handle_banco_url_actions():
    """Ações star/edit/del vindas dos links da busca HTML."""
    act = _qp_val("banco_act")
    bid = _qp_val("banco_id")
    if not act or not bid:
        return
    try:
        rid = int(bid)
    except (TypeError, ValueError):
        return

    if act == "star":
        row = DB.query("SELECT favorito FROM alimentos_favoritos WHERE id=?", [rid])
        if not row.empty:
            fav = int(row["favorito"].iloc[0] or 0)
            DB.execute("UPDATE alimentos_favoritos SET favorito=? WHERE id=?", [1 - fav, rid])
            _invalidate_cache(_q_alimentos_favoritos)
            _notif("Favorito atualizado!")
    elif act == "edit":
        st.session_state["banco_edit_id"] = rid
    elif act == "del":
        st.session_state["banco_del_confirm"] = rid

    for _k in ("banco_act", "banco_id"):
        try:
            del st.query_params[_k]
        except Exception:
            pass
    st.rerun()


def _render_banco_edit_form(_brow, in_dialog: bool = False):
    _bid = int(_brow["id"])
    _bdesc = str(_brow["descricao"])
    _bkcal = float(_brow["calorias"] or 0)
    _bprot = float(_brow["proteinas"] or 0)
    _bcarb = float(_brow["carboidratos"] or 0)
    _bgord = float(_brow["gorduras"] or 0)
    _bqtd = float(_brow.get("qtd_referencia") or 100)
    _bunit = str(_brow.get("unidade_referencia") or "g")

    _wrap = st.container(border=not in_dialog)
    with _wrap:
        if not in_dialog:
            st.caption(f"Editando: {_bdesc}")
        with st.form(f"form_banco_edit_page_{_bid}", border=False):
            _e_desc = st.text_input("Nome", value=_bdesc)
            _eq1, _eq2 = st.columns(2)
            with _eq1:
                _e_qtd = st.number_input("Ref.", value=_bqtd, min_value=0.0, step=1.0, format="%.0f")
            with _eq2:
                _units = ["g", "kg", "ml", "L", "und"]
                _e_unit = st.selectbox(
                    "Unidade", _units,
                    index=_units.index(_bunit) if _bunit in _units else 0,
                )
            _em1, _em2 = st.columns(2)
            with _em1:
                _e_kcal = st.number_input("Kcal", value=_bkcal, min_value=0.0, step=1.0, format="%.0f")
                _e_carb = st.number_input("Carb (g)", value=_bcarb, min_value=0.0, step=0.5, format="%.1f")
            with _em2:
                _e_prot = st.number_input("Prot (g)", value=_bprot, min_value=0.0, step=0.5, format="%.1f")
                _e_gord = st.number_input("Gord (g)", value=_bgord, min_value=0.0, step=0.5, format="%.1f")
            if st.form_submit_button("✅ Salvar", use_container_width=False):
                DB.execute(
                    "UPDATE alimentos_favoritos SET descricao=?,calorias=?,proteinas=?,"
                    "carboidratos=?,gorduras=?,qtd_referencia=?,unidade_referencia=? WHERE id=?",
                    [_e_desc.strip(), _e_kcal, _e_prot, _e_carb, _e_gord, _e_qtd, _e_unit, _bid],
                )
                st.session_state["banco_edit_id"] = None
                _invalidate_cache(_q_alimentos_favoritos)
                _notif(f"'{_e_desc.strip()}' atualizado!")
                st.rerun()


def _banco_toggle_star(rid: int):
    row = DB.query("SELECT favorito FROM alimentos_favoritos WHERE id=?", [rid])
    if row.empty:
        return
    fav = int(row["favorito"].iloc[0] or 0)
    DB.execute("UPDATE alimentos_favoritos SET favorito=? WHERE id=?", [1 - fav, rid])
    _invalidate_cache(_q_alimentos_favoritos)
    _notif("Favorito atualizado!")


@st.fragment
def _fragment_banco_busca(_df_banco_all: pd.DataFrame):
    """Busca + ações nativas Streamlit (iframe sandbox impede editar/favoritar/excluir)."""
    if _df_banco_all.empty:
        st.info("Nenhum alimento cadastrado ainda.")
        return

    st.markdown(_BANCO_HIT_CSS, unsafe_allow_html=True)

    if "banco_busca_applied" not in st.session_state:
        st.session_state["banco_busca_applied"] = ""

    def _sync_busca():
        st.session_state["banco_busca_applied"] = (st.session_state.get("banco_busca_q") or "").strip()

    _iq, _ib = st.columns([0.88, 0.12])
    with _iq:
        st.text_input(
            "busca",
            placeholder="🔍 Digite o nome do alimento...",
            key="banco_busca_q",
            label_visibility="collapsed",
            on_change=_sync_busca,
        )
    with _ib:
        if st.button("🔍", key="banco_busca_go", use_container_width=False, help="Buscar alimentos"):
            _sync_busca()
            st.rerun(scope="fragment")

    _term = st.session_state.get("banco_busca_applied", "")
    _n = len(_df_banco_all)

    if not _term:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};letter-spacing:1px;'
            f'margin:8px 0 6px">Digite para buscar entre {_n} alimento(s)</div>',
            unsafe_allow_html=True,
        )
        return

    _hits = (
        _df_banco_all[_df_banco_all["descricao"].str.contains(_term, case=False, na=False)]
        .sort_values(["favorito", "vezes_usado"], ascending=[False, False])
    )
    if _hits.empty:
        st.markdown(
            f'<div style="font-size:11px;color:{GHOST};padding:10px 12px;'
            f'background:{BG2};border:1px solid {BORDER};border-radius:8px">Nenhum resultado</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div style="font-family:{MONO};font-size:9px;color:{GHOST};letter-spacing:1px;'
        f'margin:8px 0 6px">{len(_hits)} resultado(s)</div>',
        unsafe_allow_html=True,
    )

    for _, r in _hits.iterrows():
        bid = int(r["id"])
        desc = html_mod.escape(str(r["descricao"]))
        fav = int(r.get("favorito") or 0)
        kcal = int(r.get("calorias") or 0)
        prot = float(r.get("proteinas") or 0)
        carb = float(r.get("carboidratos") or 0)
        gord = float(r.get("gorduras") or 0)
        used = int(r.get("vezes_usado") or 0)
        qtd = float(r.get("qtd_referencia") or 100)
        unit = html_mod.escape(str(r.get("unidade_referencia") or "g"))

        st.markdown('<div class="sh-banco-hit-mark"></div>', unsafe_allow_html=True)
        _rc, _ra = st.columns([5.6, 1.4], vertical_alignment="center")
        with _rc:
            st.markdown(
                f'<div>'
                f'<div style="font-size:12px;font-weight:600;color:{TEXT}">'
                f'{"⭐ " if fav else ""}{desc}</div>'
                f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};margin-top:2px">'
                f'Ref: {qtd:.0f} {unit}</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:4px;font-size:9px">'
                f'<span style="font-family:{MONO};color:{AMBER}">🔥{kcal}</span>'
                f'<span style="color:{GREEN}">P:{prot:.0f}g</span>'
                f'<span style="color:#2dd4bf">C:{carb:.0f}g</span>'
                f'<span style="color:{PURPLE}">G:{gord:.0f}g</span>'
                f'<span style="color:{GHOST}">×{used}</span>'
                f"</div></div>",
                unsafe_allow_html=True,
            )
        with _ra:
            _bs1, _bs2, _bs3 = st.columns(3, gap="small")
            with _bs1:
                if st.button(
                    "", key=f"banco_star_{bid}",
                    icon=STAR_ICON if fav else STAR_OUTLINE_ICON,
                    help="Favorito",
                ):
                    _banco_toggle_star(bid)
                    st.rerun()
            with _bs2:
                if st.button("", key=f"banco_edit_{bid}", icon=EDIT_ICON, help="Editar"):
                    st.session_state["banco_edit_id"] = bid
                    st.rerun()
            with _bs3:
                if st.button("", key=f"banco_del_{bid}", icon=DELETE_ICON, help="Excluir"):
                    st.session_state["banco_del_confirm"] = bid
                    st.rerun()


@st.dialog("Editar alimento", width="medium")
def _dialog_banco_edit(_brow):
    from sh_components import section_actions

    _render_banco_edit_form(_brow, in_dialog=True)
    with section_actions():
        if st.button("✕ Fechar", key="banco_edit_close_dlg", use_container_width=False):
            st.session_state.pop("banco_edit_id", None)
            st.rerun()


def render_banco_page():
    DB.init_tables()
    _handle_banco_url_actions()

    from app_sidebar import render_app_sidebar

    render_app_sidebar(
        active_page="banco",
        quick_actions={
            "refeicao": True,
            "editar": True,
            "agua": True,
            "supp": True,
        },
    )

    st.markdown(
        f'<div style="font-family:{MONO};font-size:10px;color:{CYAN};letter-spacing:2px;'
        f'text-transform:uppercase;margin-bottom:4px">SYS.HEALTH</div>',
        unsafe_allow_html=True,
    )
    st.title("🍽️ Banco de Alimentos")
    st.caption("Cadastre alimentos, marque favoritos e defina porção de referência (g, ml, L, und).")

    _render_notif()

    _banco_cols = st.columns([1.1, 1.9])

    _df_busca = _q_alimentos_favoritos()

    with _banco_cols[0]:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;'
            f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px">'
            f'➕ CADASTRAR NOVO ALIMENTO</div>',
            unsafe_allow_html=True,
        )
        with st.form("form_banco_add_page", clear_on_submit=True, border=False):
            b_desc = st.text_input("Nome do alimento *", placeholder="Ex: Banana, Whey Protein...")
            bcq1, bcq2 = st.columns([2, 1])
            with bcq1:
                b_qtd = st.number_input("Qtd. de referência", min_value=0.0, value=100.0, step=1.0, format="%.0f")
            with bcq2:
                b_unit = st.selectbox("Unidade", ["g", "kg", "ml", "L", "und"])
            bc1, bc2 = st.columns(2)
            with bc1:
                b_kcal = st.number_input("Kcal", min_value=0.0, step=1.0, format="%.0f")
                b_carb = st.number_input("Carb (g)", min_value=0.0, step=0.5, format="%.1f")
            with bc2:
                b_prot = st.number_input("Prot (g)", min_value=0.0, step=0.5, format="%.1f")
                b_gord = st.number_input("Gord (g)", min_value=0.0, step=0.5, format="%.1f")
            if st.form_submit_button("✅ Cadastrar", use_container_width=False):
                if b_desc.strip():
                    _existente = DB.query(
                        "SELECT id FROM alimentos_favoritos WHERE descricao=?",
                        [b_desc.strip()],
                    )
                    if _existente.empty:
                        DB.execute(
                            "INSERT INTO alimentos_favoritos "
                            "(descricao,calorias,proteinas,carboidratos,gorduras,componentes_json,qtd_referencia,unidade_referencia) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            [
                                b_desc.strip(), b_kcal, b_prot, b_carb, b_gord,
                                json.dumps([{
                                    "nome": b_desc.strip(), "gramas": b_qtd, "unidade": b_unit,
                                    "kcal": b_kcal, "prot": b_prot, "carb": b_carb, "gord": b_gord,
                                }]),
                                b_qtd, b_unit,
                            ],
                        )
                        _invalidate_cache(_q_alimentos_favoritos)
                        _notif(f"'{b_desc.strip()}' cadastrado!")
                        st.rerun()
                    else:
                        st.warning("Já existe um alimento com este nome.")
                else:
                    st.warning("Nome obrigatório.")

    with _banco_cols[1]:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;'
            f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px">'
            f'🔍 BUSCAR ALIMENTO</div>',
            unsafe_allow_html=True,
        )
        _del_id = st.session_state.get("banco_del_confirm")
        if _del_id:
            _del_row = _df_busca[_df_busca["id"] == int(_del_id)]
            if not _del_row.empty:
                _ddesc = str(_del_row.iloc[0]["descricao"])
                st.warning(f"Excluir **{_ddesc}**?")
                _dc1, _dc2 = st.columns(2)
                with _dc1:
                    if st.button("Confirmar exclusão", key="banco_del_ok", use_container_width=False):
                        DB.execute("DELETE FROM alimentos_favoritos WHERE id=?", [int(_del_id)])
                        st.session_state.pop("banco_del_confirm", None)
                        _invalidate_cache(_q_alimentos_favoritos)
                        _notif(f"'{_ddesc}' excluído.")
                        st.rerun()
                with _dc2:
                    if st.button("Cancelar", key="banco_del_cancel", use_container_width=False):
                        st.session_state.pop("banco_del_confirm", None)
                        st.rerun()

        _fragment_banco_busca(_df_busca)

    _edit_id = st.session_state.get("banco_edit_id")
    if _edit_id:
        _edit_match = _df_busca[_df_busca["id"] == int(_edit_id)]
        if not _edit_match.empty:
            _dialog_banco_edit(_edit_match.iloc[0])
        else:
            st.session_state.pop("banco_edit_id", None)
