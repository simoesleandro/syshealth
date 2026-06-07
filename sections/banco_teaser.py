"""Card teaser do Banco de Alimentos (página dedicada)."""
from __future__ import annotations

import streamlit as st

from sh_components import section_actions, sh_card, sh_section


def render_banco_teaser(df_banco_cnt) -> None:
    """Renderiza âncora + card + CTA — fora da ordem principal do menu."""
    st.markdown('<div id="sec-banco"></div>', unsafe_allow_html=True)
    st.markdown(sh_section("Banco", "Cadastro · Edição · Favoritos"), unsafe_allow_html=True)

    n = len(df_banco_cnt)
    fav = int((df_banco_cnt["favorito"] == 1).sum()) if not df_banco_cnt.empty else 0

    st.markdown(
        sh_card(
            title="Banco de Alimentos",
            icon="🍽️",
            body=(
                "Cadastre alimentos, defina porção de referência (g, ml, L, und) e marque favoritos. "
                "Combinações de refeição também podem ser salvas como favorito na nova/edição de refeição."
            ),
            footer=f"<span>{n} alimento(s)</span><span>⭐ {fav} favorito(s)</span>",
        ),
        unsafe_allow_html=True,
    )

    with section_actions():
        if st.button("Abrir Banco de Alimentos →", key="btn_open_banco_page", use_container_width=False):
            st.switch_page("pages/1_Banco_de_Alimentos.py")
