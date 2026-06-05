"""Iframe HTML para busca ao vivo — usado na página Banco de Alimentos."""
from __future__ import annotations

import streamlit as st


def embed_html_iframe(html_doc: str, height: int):
    st.iframe(html_doc, height=height, width="stretch")
