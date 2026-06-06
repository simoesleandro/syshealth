"""Página do Banco de Alimentos — cadastro, edição e favoritos."""
import html as html_mod
import json
import os

import pandas as pd
import streamlit as st

from busca_alimentos_ui import embed_html_iframe

try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass

import db as DB

BG = "#080c14"
BG2 = "#0d1424"
BG3 = "#080e1a"
BORDER = "#1a2035"
BORDER2 = "#111c2e"
CYAN = "#00d4ff"
GREEN = "#00e676"
AMBER = "#fbbf24"
TEXT = "#e8edf5"
MUTED = "#4a5568"
GHOST = "#2a3448"
PURPLE = "#a78bfa"
MONO = "'Space Mono',monospace"


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


def _handle_banco_url_actions():
    """Ações star/edit/del vindas dos links da busca HTML."""
    act = st.query_params.get("banco_act")
    bid = st.query_params.get("banco_id")
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

    st.query_params.clear()
    st.rerun()


def _render_banco_edit_form(_brow):
    _bid = int(_brow["id"])
    _bdesc = str(_brow["descricao"])
    _bkcal = float(_brow["calorias"] or 0)
    _bprot = float(_brow["proteinas"] or 0)
    _bcarb = float(_brow["carboidratos"] or 0)
    _bgord = float(_brow["gorduras"] or 0)
    _bqtd = float(_brow.get("qtd_referencia") or 100)
    _bunit = str(_brow.get("unidade_referencia") or "g")

    with st.container(border=True):
        st.caption(f"✏️ Editando: {_bdesc}")
        with st.form(f"form_banco_edit_page_{_bid}"):
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
            if st.form_submit_button("✅ Salvar", use_container_width=True):
                DB.execute(
                    "UPDATE alimentos_favoritos SET descricao=?,calorias=?,proteinas=?,"
                    "carboidratos=?,gorduras=?,qtd_referencia=?,unidade_referencia=? WHERE id=?",
                    [_e_desc.strip(), _e_kcal, _e_prot, _e_carb, _e_gord, _e_qtd, _e_unit, _bid],
                )
                st.session_state["banco_edit_id"] = None
                _invalidate_cache(_q_alimentos_favoritos)
                _notif(f"'{_e_desc.strip()}' atualizado!")
                st.rerun()


def _render_banco_busca_live(_df_banco_all: pd.DataFrame):
    """Busca instantânea no navegador — filtra a cada tecla, sem Enter."""
    if _df_banco_all.empty:
        st.info("Nenhum alimento cadastrado ainda.")
        return

    _rows = []
    for _, r in _df_banco_all.sort_values(["favorito", "vezes_usado"], ascending=[False, False]).iterrows():
        bid = int(r["id"])
        desc = html_mod.escape(str(r["descricao"]))
        q = html_mod.escape(str(r["descricao"]).lower())
        fav = int(r.get("favorito") or 0)
        star = "⭐" if fav else "☆"
        kcal = int(r.get("calorias") or 0)
        prot = float(r.get("proteinas") or 0)
        carb = float(r.get("carboidratos") or 0)
        gord = float(r.get("gorduras") or 0)
        used = int(r.get("vezes_usado") or 0)
        qtd = float(r.get("qtd_referencia") or 100)
        unit = html_mod.escape(str(r.get("unidade_referencia") or "g"))
        _rows.append(
            f'<div class="banco-hit" data-q="{q}">'
            f'<div class="banco-hit__info">'
            f'<div class="banco-hit__name">{"⭐ " if fav else ""}{desc}</div>'
            f'<div class="banco-hit__ref">Ref: {qtd:.0f} {unit}</div>'
            f'<div class="banco-hit__macros">'
            f'<span class="kcal">🔥{kcal}</span>'
            f'<span class="prot">P:{prot:.0f}g</span>'
            f'<span class="carb">C:{carb:.0f}g</span>'
            f'<span class="gord">G:{gord:.0f}g</span>'
            f'<span class="used">×{used}</span>'
            f"</div></div>"
            f'<div class="banco-hit__acts">'
            f'<a class="banco-act" href="?banco_act=star&banco_id={bid}" target="_parent" title="Favorito">{star}</a>'
            f'<a class="banco-act" href="?banco_act=edit&banco_id={bid}" target="_parent" title="Editar">✏️</a>'
            f'<a class="banco-act" href="?banco_act=del&banco_id={bid}" target="_parent" title="Excluir">🗑️</a>'
            f"</div></div>"
        )

    _hits_html = "\n".join(_rows)
    _n = len(_rows)
    _frame_h = min(520, max(220, 150 + min(_n, 7) * 58))

    _html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
* {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 0;
  font-family: 'DM Sans', system-ui, sans-serif;
  background: {BG};
  color: {TEXT};
}}
#banco-live-q {{
  width: 100%;
  background: {BG3};
  border: 1px solid {CYAN};
  border-radius: 8px;
  color: {TEXT};
  font-size: 14px;
  padding: 10px 12px;
  outline: none;
}}
#banco-live-q::placeholder {{ color: {GHOST}; }}
#banco-live-meta {{
  font-family: {MONO};
  font-size: 9px;
  color: {GHOST};
  letter-spacing: 1px;
  margin: 8px 0 6px;
}}
#banco-live-empty {{ display: none; font-size: 11px; color: {GHOST}; padding: 10px 12px;
  background: {BG2}; border: 1px solid {BORDER}; border-radius: 8px; }}
#banco-live-list {{ display: none; background: {BG2}; border: 1px solid {BORDER};
  border-radius: 8px; max-height: 400px; overflow-y: auto; }}
.banco-hit {{
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid {BORDER2};
}}
.banco-hit:last-child {{ border-bottom: none; }}
.banco-hit__info {{ flex: 1; min-width: 0; }}
.banco-hit__name {{ font-size: 12px; font-weight: 600; color: {TEXT};
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.banco-hit__ref {{ font-family: {MONO}; font-size: 9px; color: {CYAN}; margin-top: 2px; }}
.banco-hit__macros {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; font-size: 9px; }}
.banco-hit__macros .kcal {{ font-family: {MONO}; color: {AMBER}; }}
.banco-hit__macros .prot {{ color: {GREEN}; }}
.banco-hit__macros .carb {{ color: #2dd4bf; }}
.banco-hit__macros .gord {{ color: {PURPLE}; }}
.banco-hit__macros .used {{ color: {GHOST}; }}
.banco-hit__acts {{ display: flex; gap: 6px; flex-shrink: 0; }}
.banco-act {{
  display: inline-flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; border: 1px solid {BORDER}; border-radius: 8px;
  background: {BG3}; color: {TEXT}; text-decoration: none; font-size: 14px;
}}
.banco-act:hover {{ border-color: {CYAN}; color: {CYAN}; background: rgba(0,212,255,0.08); }}
</style></head><body>
<input type="search" id="banco-live-q" placeholder="🔍 Digite o nome do alimento..." autocomplete="off" />
<div id="banco-live-meta">Digite para buscar entre {_n} alimento(s)</div>
<div id="banco-live-empty">Nenhum resultado</div>
<div id="banco-live-list">{_hits_html}</div>
<script>
(function() {{
  var q = document.getElementById("banco-live-q");
  var meta = document.getElementById("banco-live-meta");
  var empty = document.getElementById("banco-live-empty");
  var list = document.getElementById("banco-live-list");
  var hits = list.querySelectorAll(".banco-hit");
  function filter() {{
    var term = (q.value || "").toLowerCase().trim();
    var visible = 0;
    for (var i = 0; i < hits.length; i++) {{
      var el = hits[i];
      var match = term.length > 0 && (el.getAttribute("data-q") || "").indexOf(term) >= 0;
      el.style.display = match ? "flex" : "none";
      if (match) visible++;
    }}
    if (!term) {{
      meta.textContent = "Digite para buscar entre {_n} alimento(s)";
      list.style.display = "none";
      empty.style.display = "none";
    }} else if (visible === 0) {{
      meta.textContent = "0 resultado(s)";
      list.style.display = "none";
      empty.style.display = "block";
    }} else {{
      meta.textContent = visible + " resultado(s)";
      list.style.display = "block";
      empty.style.display = "none";
    }}
  }}
  q.addEventListener("input", filter);
  q.addEventListener("keyup", filter);
  filter();
}})();
</script>
</body></html>"""

    embed_html_iframe(_html_doc, _frame_h)


def render_banco_page():
    DB.init_tables()
    _handle_banco_url_actions()

    from app_sidebar import render_app_sidebar, render_mobile_quick_bar

    render_app_sidebar(
        active_page="banco",
        quick_actions={
            "refeicao": lambda: _open_dialog_on_dashboard("refeicao"),
            "editar": lambda: _open_dialog_on_dashboard("editar"),
            "agua": lambda: _open_dialog_on_dashboard("agua"),
            "supp": lambda: _open_dialog_on_dashboard("supp"),
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

    with _banco_cols[0]:
        st.markdown(
            f'<div style="font-family:{MONO};font-size:9px;color:{CYAN};font-weight:700;'
            f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px">'
            f'➕ CADASTRAR NOVO ALIMENTO</div>',
            unsafe_allow_html=True,
        )
        with st.form("form_banco_add_page", clear_on_submit=True):
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
            if st.form_submit_button("✅ Cadastrar", use_container_width=True):
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
        _df_busca = _q_alimentos_favoritos()

        _edit_id = st.session_state.get("banco_edit_id")
        if _edit_id:
            _edit_row = _df_busca[_df_busca["id"] == int(_edit_id)]
            if not _edit_row.empty:
                _render_banco_edit_form(_edit_row.iloc[0])

        _del_id = st.session_state.get("banco_del_confirm")
        if _del_id:
            _del_row = _df_busca[_df_busca["id"] == int(_del_id)]
            if not _del_row.empty:
                _ddesc = str(_del_row.iloc[0]["descricao"])
                st.warning(f"Excluir **{_ddesc}**?")
                _dc1, _dc2 = st.columns(2)
                with _dc1:
                    if st.button("Confirmar exclusão", key="banco_del_ok", use_container_width=True):
                        DB.execute("DELETE FROM alimentos_favoritos WHERE id=?", [int(_del_id)])
                        st.session_state.pop("banco_del_confirm", None)
                        _invalidate_cache(_q_alimentos_favoritos)
                        _notif(f"'{_ddesc}' excluído.")
                        st.rerun()
                with _dc2:
                    if st.button("Cancelar", key="banco_del_cancel", use_container_width=True):
                        st.session_state.pop("banco_del_confirm", None)
                        st.rerun()

        _render_banco_busca_live(_df_busca)

    render_mobile_quick_bar(on_dashboard=False)
