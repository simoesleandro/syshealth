"""Seção Histórico — gráficos e tendências semanais."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sh_components import panel, ptitl, section_actions, sh_empty_state, sh_section
from sh_tokens import AMBER, BG2, BORDER, CYAN, GHOST, GREEN, MONO, MUTED, PURPLE, RED, TEXT

def chart_layout(height=200, show_legend=False):
    return dict(
        height=height, margin=dict(t=10, b=10, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor=BORDER, title=None,
                   tickformat="%d/%m", tickfont=dict(color=GHOST, size=9, family="monospace"),
                   showgrid=True),
        yaxis=dict(gridcolor=BORDER, title=None,
                   tickfont=dict(color=GHOST, size=9), showgrid=True),
        showlegend=show_legend,
        font=dict(family="monospace", color=GHOST),
    )

def linha(df, col, cor, name="", fill=False, dash=None):
    return go.Scatter(
        x=df["dia"], y=df[col], mode="lines+markers", name=name,
        line=dict(color=cor, width=2, dash=dash),
        marker=dict(size=5, color=cor),
        fill="tozeroy" if fill else "none",
        fillcolor=cor.replace("ff", "22") if fill and cor.startswith("#") else "rgba(0,0,0,0)",
        hovertemplate=f"<b>%{{x|%d/%m}}</b><br>{name}: %{{y}}<extra></extra>",
    )

def barra(df, col, cor, name=""):
    return go.Bar(
        x=df["dia"], y=df[col], name=name,
        marker_color=cor, opacity=0.8,
        hovertemplate=f"<b>%{{x|%d/%m}}</b><br>{name}: %{{y}}<extra></extra>",
    )

def _trend_data(df, col):
    """Regressão linear: retorna (x_vals, y_fit, slope)."""
    import numpy as np
    if len(df) < 3 or col not in df.columns:
        return None, None, 0
    y = pd.to_numeric(df[col], errors="coerce").fillna(0).values
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    slope = float(coeffs[0])
    y_fit = np.polyval(coeffs, x)
    return df["dia"].values, y_fit, slope

def trend_line(df, col, cor="#aaaaaa", name="Tendência"):
    """Trace de linha de tendência (regressão linear)."""
    xs, ys, _ = _trend_data(df, col)
    if xs is None:
        return None
    return go.Scatter(
        x=xs, y=ys, mode="lines", name=name,
        line=dict(color=cor, width=1.5, dash="dot"),
        opacity=0.65,
        hovertemplate=f"<b>%{{x|%d/%m}}</b><br>{name}: %{{y:.1f}}<extra></extra>",
    )

def _trend_badge(df, col, higher_is_better=True):
    """Retorna (ícone, cor_hex, str_pct) comparando 1ª metade vs 2ª metade do período."""
    if len(df) < 4 or col not in df.columns:
        return "→", MUTED, ""
    y = pd.to_numeric(df[col], errors="coerce").fillna(0).values
    half = max(1, len(y) // 2)
    avg1 = float(y[:half].mean())
    avg2 = float(y[half:].mean())
    if avg1 == 0:
        return "→", MUTED, ""
    pct = (avg2 - avg1) / abs(avg1) * 100
    going_up   = pct >  2.5
    going_down = pct < -2.5
    if higher_is_better:
        icon  = "↑" if going_up   else ("↓" if going_down  else "→")
        color = GREEN if going_up  else (RED  if going_down  else AMBER)
    else:
        icon  = "↓" if going_down else ("↑" if going_up    else "→")
        color = GREEN if going_down else (RED if going_up    else AMBER)
    return icon, color, f"{pct:+.1f}%"



def df_media(df, col):
    if df is None or df.empty or col not in df.columns:
        return 0
    return df[col].replace(0, pd.NA).mean()


def fmt_metric(val, sufixo="", decimais=0):
    if pd.isna(val) or val == 0:
        return "—"
    return f"{val:.{decimais}f}{sufixo}"



@st.fragment
def render_historico_fragment(db_fn, *, tmb, meta_pass, meta_sono, meta_prot):
    """Período + queries + Plotly só após o usuário carregar o histórico."""
    if not st.session_state.get("hist_carregado", False):
        st.markdown(
            sh_empty_state(
                "📊",
                "Histórico não carregado",
                f'Clique em <b style="color:{CYAN}">📊 Carregar</b> para buscar e exibir os gráficos do período selecionado',
            ),
            unsafe_allow_html=True,
        )
        with section_actions():
            if st.button("📊 Carregar dados do período", key="btn_hist_load", use_container_width=False, help="Carregar gráficos do histórico"):
                st.session_state["hist_carregado"] = True
                st.rerun(scope="fragment")
        return

    st.markdown(
        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{MUTED};margin-bottom:4px">PERÍODO DE ANÁLISE</div>',
        unsafe_allow_html=True,
    )
    periodo = st.radio(
        "Período",
        ["7 dias", "14 dias", "30 dias", "90 dias"],
        index=1,
        horizontal=True,
        label_visibility="collapsed",
        key="periodo_hist",
    )
    n_dias = int(periodo.split()[0])

    df_hist = pd.DataFrame()
    df_macro_hist = pd.DataFrame()
    df_hevy_hist = pd.DataFrame()
    df_hevy_list = pd.DataFrame()
    total_treinos = 0
    total_vol = 0.0
    total_dur = 0
    media_vol_treino = 0.0
    media_dur_treino = 0.0
    media_deficit = 0.0

    df_hist = db_fn(f"""
        SELECT
            date(data_hora) as dia,
            passos, calorias_gastas, distancia_km,
            sono_total_min, sono_profundo_min,
            hrv_ms, pai,
            corrida_km, corrida_cal
        FROM amazfit_dados
        WHERE date(data_hora) >= date('now', '-{n_dias} days')
        ORDER BY dia ASC
    """)

    df_macro_hist = db_fn(f"""
        SELECT
            date(data_hora, 'localtime') as dia,
            SUM(calorias)    as cal,
            SUM(proteinas)   as prot,
            SUM(carboidratos) as carb,
            SUM(gorduras)    as gord
        FROM refeicoes
        WHERE date(data_hora, 'localtime') >= date('now', '-{n_dias} days')
        GROUP BY dia
        ORDER BY dia ASC
    """)

    # Hevy history query
    df_hevy_hist = db_fn(f"""
        SELECT
            COUNT(*) as count_treino,
            SUM(duracao_min) as dur,
            SUM(volume_kg) as vol
        FROM hevy_treinos
        WHERE date(data_hora, 'localtime') >= date('now', '-{n_dias} days')
    """)
    total_treinos = int(df_hevy_hist["count_treino"].iloc[0]) if not df_hevy_hist.empty and df_hevy_hist["count_treino"].iloc[0] is not None else 0
    total_vol = float(df_hevy_hist["vol"].iloc[0]) if not df_hevy_hist.empty and df_hevy_hist["vol"].iloc[0] is not None else 0.0
    total_dur = int(df_hevy_hist["dur"].iloc[0]) if not df_hevy_hist.empty and df_hevy_hist["dur"].iloc[0] is not None else 0
    media_vol_treino = total_vol / total_treinos if total_treinos > 0 else 0.0
    media_dur_treino = total_dur / total_treinos if total_treinos > 0 else 0.0

    df_hevy_list = db_fn(f"""
        SELECT
            date(data_hora, 'localtime') as dia,
            titulo, duracao_min, volume_kg
        FROM hevy_treinos
        WHERE date(data_hora, 'localtime') >= date('now', '-{n_dias} days')
        ORDER BY data_hora ASC
    """)

    # ── Caption: intervalo real dos dados carregados ─────────────────────────
    if not df_hist.empty:
        try:
            _min_d = pd.to_datetime(df_hist["dia"].min()).strftime("%d/%m/%Y")
            _max_d = pd.to_datetime(df_hist["dia"].max()).strftime("%d/%m/%Y")
            _n_nutri = len(df_macro_hist)
            st.markdown(
                f'<div style="font-size:10px;color:{GHOST};font-family:{MONO};'
                f'letter-spacing:0.5px;margin:4px 0 8px;text-align:right">'
                f'📅 {_min_d} → {_max_d} · {len(df_hist)} dias Amazfit · {_n_nutri} dias nutrição</div>',
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    _tem_qualquer_dado = not df_hist.empty or not df_macro_hist.empty

    if _tem_qualquer_dado:

        # ── Tabela resumo semanal ─────────────────────────────────────────────────
        st.markdown(sh_section("Resumo", f"Médias dos últimos {n_dias} dias"), unsafe_allow_html=True)

        if df_hist.empty and not df_macro_hist.empty:
            st.info("💡 Dados do Amazfit não encontrados para este período. Exibindo dados de nutrição disponíveis.")

        def _media_local(df, col):
            return df[col].replace(0, pd.NA).mean() if col in df.columns else 0

        def _fmt_val_local(val, sufixo="", decimais=0):
            if pd.isna(val) or val == 0:
                return "—"
            return f"{val:.{decimais}f}{sufixo}"

        # Calcular déficit calórico médio para o resumo
        media_deficit = 0.0
        if not df_hist.empty or not df_macro_hist.empty:
            df_h = df_hist.copy() if not df_hist.empty else pd.DataFrame(columns=["dia", "calorias_gastas"])
            df_m = df_macro_hist.copy() if not df_macro_hist.empty else pd.DataFrame(columns=["dia", "cal"])
            if "calorias_gastas" not in df_h.columns:
                df_h["calorias_gastas"] = 0.0
            if "cal" not in df_m.columns:
                df_m["cal"] = 0.0
            df_merged = pd.merge(df_h, df_m, on="dia", how="outer").fillna(0)
            df_merged["deficit"] = (tmb + df_merged["calorias_gastas"]) - df_merged["cal"]
            media_deficit = df_merged["deficit"].mean()

        medias = [
            ("👟", "Passos/dia",       _fmt_val_local(_media_local(df_hist, "passos"), "", 0),
             f"meta {meta_pass:,}"),
            ("📍", "Distância/dia",    _fmt_val_local(_media_local(df_hist, "distancia_km"), " km", 1),
             ""),
            ("🌙", "Sono total/dia",   _fmt_val_local(_media_local(df_hist, "sono_total_min"), " min", 0),
             "≥ 420 min"),
            ("💤", "Sono profundo/dia",_fmt_val_local(_media_local(df_hist, "sono_profundo_min"), " min", 0),
             f"meta {meta_sono} min"),
            ("💓", "HRV médio",        _fmt_val_local(_media_local(df_hist, "hrv_ms"), " ms", 0),
             ""),
            ("⚡", "PAI médio",        _fmt_val_local(_media_local(df_hist, "pai"), "", 0),
             "meta ≥ 100"),
        ]
        if not df_macro_hist.empty:
            medias += [
                ("🔥", "Calorias/dia",  _fmt_val_local(_media_local(df_macro_hist, "cal"), " kcal", 0),
                 f"meta {tmb}"),
                ("🥩", "Proteínas/dia", _fmt_val_local(_media_local(df_macro_hist, "prot"), " g", 0),
                 f"meta {meta_prot}g"),
                ("📉", "Déficit/dia",    _fmt_val_local(media_deficit, " kcal", 0),
                 "meta 500 kcal"),
            ]

        # Musculação averages from Hevy
        medias += [
            ("🏋️", "Vol. Musculação", _fmt_val_local(media_vol_treino, " kg", 0), f"{total_treinos} treinos"),
            ("⏱️", "Treino Médio",    _fmt_val_local(media_dur_treino, " min", 0), "musculação"),
        ]

        # Grid 4 colunas
        cols_med = st.columns(4)
        for i, (icon, lbl, val, ref) in enumerate(medias):
            with cols_med[i % 4]:
                ref_html = (f'<div style="font-size:10px;color:{GHOST};margin-top:4px">{ref}</div>'
                            if ref else "")
                st.markdown(
                    f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:9px;'
                    f'padding:14px 14px 12px;margin-bottom:10px;min-height:105px;'
                    f'display:flex;flex-direction:column;justify-content:space-between">'
                    f'<div>'
                    f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
                    f'text-transform:uppercase;color:{GHOST};margin-bottom:6px">{icon} {lbl}</div>'
                    f'<div style="font-size:22px;font-weight:800;color:{TEXT};line-height:1">{val}</div>'
                    f'</div>'
                    f'{ref_html}</div>',
                    unsafe_allow_html=True,
                )

        # ── Linha 1: Passos + Distância ───────────────────────────────────────────
        if not df_hist.empty:
            h1a, h1b = st.columns(2)

            with h1a:
                st.markdown(panel(
                    ptitl("👟 Passos diários") +
                    f'<div id="chart_passos"></div>'
                ), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(barra(df_hist, "passos", CYAN, "Passos"))
                _tl = trend_line(df_hist, "passos", CYAN, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.add_hline(y=meta_pass, line_dash="dash", line_color=GREEN,
                              line_width=1, opacity=0.5,
                              annotation_text=f"Meta {meta_pass:,}",
                              annotation_font_color=GREEN, annotation_font_size=9)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h1b:
                st.markdown(panel(ptitl("📍 Distância (km)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(linha(df_hist, "distancia_km", CYAN, "km", fill=True))
                _tl = trend_line(df_hist, "distancia_km", AMBER, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            # ── Linha 2: Sono ─────────────────────────────────────────────────────────
            h2a, h2b = st.columns(2)

            with h2a:
                st.markdown(panel(ptitl("🌙 Sono total (min)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(barra(df_hist, "sono_total_min", PURPLE, "Total"))
                fig.add_trace(barra(df_hist, "sono_profundo_min", CYAN, "Profundo"))
                _tl_sono = trend_line(df_hist, "sono_total_min", PURPLE, "Tend. Total")
                if _tl_sono: fig.add_trace(_tl_sono)
                fig.add_hline(y=meta_sono, line_dash="dash", line_color=RED,
                              line_width=1, opacity=0.5,
                              annotation_text=f"Meta prof. {meta_sono}min",
                              annotation_font_color=RED, annotation_font_size=9)
                fig.update_layout(**chart_layout(180, show_legend=True),
                                  barmode="overlay",
                                  legend=dict(font=dict(color=GHOST, size=9),
                                              bgcolor="rgba(0,0,0,0)"))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h2b:
                st.markdown(panel(ptitl("💓 HRV · PAI")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(linha(df_hist, "hrv_ms",  GREEN,  "HRV (ms)"))
                fig.add_trace(linha(df_hist, "pai",      AMBER,  "PAI", dash="dot"))
                _tl_hrv = trend_line(df_hist, "hrv_ms", GREEN, "Tend. HRV")
                if _tl_hrv: fig.add_trace(_tl_hrv)
                _tl_pai = trend_line(df_hist, "pai", AMBER, "Tend. PAI")
                if _tl_pai: fig.add_trace(_tl_pai)
                fig.update_layout(**chart_layout(180, show_legend=True),
                                  legend=dict(font=dict(color=GHOST, size=9),
                                              bgcolor="rgba(0,0,0,0)"))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        # ── Linha 3: Nutrição ─────────────────────────────────────────────────────
        if not df_macro_hist.empty:
            h3a, h3b, h3c = st.columns(3)

            with h3a:
                st.markdown(panel(ptitl("🔥 Calorias diárias")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(barra(df_macro_hist, "cal", GREEN, "Calorias"))
                _tl = trend_line(df_macro_hist, "cal", GREEN, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.add_hline(y=tmb, line_dash="dash", line_color=CYAN,
                              line_width=1, opacity=0.5,
                              annotation_text=f"Meta {tmb}",
                              annotation_font_color=CYAN, annotation_font_size=9)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h3b:
                st.markdown(panel(ptitl("🥩 Proteínas diárias (g)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(barra(df_macro_hist, "prot", RED, "Proteínas"))
                _tl = trend_line(df_macro_hist, "prot", RED, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.add_hline(y=meta_prot, line_dash="dash", line_color=CYAN,
                              line_width=1, opacity=0.5,
                              annotation_text=f"Meta {meta_prot}g",
                              annotation_font_color=CYAN, annotation_font_size=9)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h3c:
                st.markdown(panel(ptitl("📉 Déficit Calórico")), unsafe_allow_html=True)
                df_h = df_hist.copy() if not df_hist.empty else pd.DataFrame(columns=["dia", "calorias_gastas"])
                df_m = df_macro_hist.copy() if not df_macro_hist.empty else pd.DataFrame(columns=["dia", "cal"])
                if "calorias_gastas" not in df_h.columns:
                    df_h["calorias_gastas"] = 0.0
                if "cal" not in df_m.columns:
                    df_m["cal"] = 0.0
                df_merged = pd.merge(df_h, df_m, on="dia", how="outer").fillna(0)
                df_merged["deficit"] = (tmb + df_merged["calorias_gastas"]) - df_merged["cal"]
            
                fig = go.Figure()
                fig.add_trace(barra(df_merged, "deficit", PURPLE, "Déficit"))
                _tl = trend_line(df_merged, "deficit", PURPLE, "Tendência")
                if _tl: fig.add_trace(_tl)
                fig.add_hline(y=500, line_dash="dash", line_color=CYAN,
                              line_width=1, opacity=0.5,
                              annotation_text="Meta 500",
                              annotation_font_color=CYAN, annotation_font_size=9)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        # ── Linha 4: Musculação (Hevy) ─────────────────────────────────────────────
        if not df_hevy_list.empty:
            h4a, h4b = st.columns(2)
        
            with h4a:
                st.markdown(panel(ptitl("🏋️ Volume de Carga (kg/treino)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_hevy_list["dia"], y=df_hevy_list["volume_kg"],
                    name="Volume", marker_color=GREEN, opacity=0.8,
                    text=df_hevy_list["titulo"],
                    hovertemplate="<b>%{x|%d/%m}</b><br>Treino: %{text}<br>Volume: %{y:,.0f} kg<extra></extra>"
                ))
                _tl_vol = trend_line(df_hevy_list, "volume_kg", GREEN, "Tendência")
                if _tl_vol: fig.add_trace(_tl_vol)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            with h4b:
                st.markdown(panel(ptitl("⏱️ Duração do Treino (min)")), unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_hevy_list["dia"], y=df_hevy_list["duracao_min"],
                    name="Duração", marker_color=AMBER, opacity=0.8,
                    text=df_hevy_list["titulo"],
                    hovertemplate="<b>%{x|%d/%m}</b><br>Treino: %{text}<br>Duração: %{y} min<extra></extra>"
                ))
                _tl_dur = trend_line(df_hevy_list, "duracao_min", AMBER, "Tendência")
                if _tl_dur: fig.add_trace(_tl_dur)
                fig.update_layout(**chart_layout(180))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

        # ── Tendências ────────────────────────────────────────────────────────────
        st.markdown(sh_section("Tendências", f"Direção dos indicadores nos últimos {n_dias} dias"), unsafe_allow_html=True)

        # Montar lista de indicadores com badges
        _tend_items = []

        if not df_hist.empty:
            _i_pass, _c_pass, _p_pass = _trend_badge(df_hist, "passos",           higher_is_better=True)
            _i_dist, _c_dist, _p_dist = _trend_badge(df_hist, "distancia_km",     higher_is_better=True)
            _i_sono, _c_sono, _p_sono = _trend_badge(df_hist, "sono_total_min",    higher_is_better=True)
            _i_prof, _c_prof, _p_prof = _trend_badge(df_hist, "sono_profundo_min", higher_is_better=True)
            _i_hrv,  _c_hrv,  _p_hrv  = _trend_badge(df_hist, "hrv_ms",           higher_is_better=True)
            _i_pai,  _c_pai,  _p_pai  = _trend_badge(df_hist, "pai",               higher_is_better=True)
            _tend_items += [
                ("👟", "Passos/dia",       _i_pass, _c_pass, _p_pass, f"média {_fmt_val_local(_media_local(df_hist,'passos'),'',0)}"),
                ("📍", "Distância/dia",    _i_dist, _c_dist, _p_dist, f"média {_fmt_val_local(_media_local(df_hist,'distancia_km'),' km',1)}"),
                ("🌙", "Sono total",       _i_sono, _c_sono, _p_sono, f"média {_fmt_val_local(_media_local(df_hist,'sono_total_min'),' min',0)}"),
                ("💤", "Sono profundo",    _i_prof, _c_prof, _p_prof, f"média {_fmt_val_local(_media_local(df_hist,'sono_profundo_min'),' min',0)}"),
                ("💓", "HRV",             _i_hrv,  _c_hrv,  _p_hrv,  f"média {_fmt_val_local(_media_local(df_hist,'hrv_ms'),' ms',0)}"),
                ("⚡", "PAI",             _i_pai,  _c_pai,  _p_pai,  f"média {_fmt_val_local(_media_local(df_hist,'pai'),'',0)}"),
            ]

        if not df_macro_hist.empty:
            _i_cal,  _c_cal,  _p_cal  = _trend_badge(df_macro_hist, "cal",  higher_is_better=False)
            _i_prot, _c_prot, _p_prot = _trend_badge(df_macro_hist, "prot", higher_is_better=True)
            _i_carb, _c_carb, _p_carb = _trend_badge(df_macro_hist, "carb", higher_is_better=False)
            _i_gord, _c_gord, _p_gord = _trend_badge(df_macro_hist, "gord", higher_is_better=False)
            _tend_items += [
                ("🔥", "Calorias/dia",    _i_cal,  _c_cal,  _p_cal,  f"média {_fmt_val_local(_media_local(df_macro_hist,'cal'),' kcal',0)}"),
                ("🥩", "Proteínas/dia",   _i_prot, _c_prot, _p_prot, f"média {_fmt_val_local(_media_local(df_macro_hist,'prot'),' g',0)}"),
                ("🍞", "Carboidratos",    _i_carb, _c_carb, _p_carb, f"média {_fmt_val_local(_media_local(df_macro_hist,'carb'),' g',0)}"),
                ("🧈", "Gorduras",        _i_gord, _c_gord, _p_gord, f"média {_fmt_val_local(_media_local(df_macro_hist,'gord'),' g',0)}"),
            ]

        if not df_hevy_list.empty:
            _i_vol,  _c_vol,  _p_vol  = _trend_badge(df_hevy_list, "volume_kg",  higher_is_better=True)
            _i_dur,  _c_dur,  _p_dur  = _trend_badge(df_hevy_list, "duracao_min", higher_is_better=True)
            _tend_items += [
                ("🏋️", "Volume/treino",   _i_vol,  _c_vol,  _p_vol,  f"média {_fmt_val_local(media_vol_treino,' kg',0)}"),
                ("⏱️", "Duração/treino",  _i_dur,  _c_dur,  _p_dur,  f"média {_fmt_val_local(media_dur_treino,' min',0)}"),
            ]

        # Renderizar grade de badges de tendência
        if _tend_items:
            _cols_t = st.columns(4)
            for _ti, (icon_t, lbl_t, icon_dir, cor_dir, pct_str, ref_t) in enumerate(_tend_items):
                with _cols_t[_ti % 4]:
                    st.markdown(
                        f'<div style="background:{BG2};border:1px solid {BORDER};border-radius:9px;'
                        f'padding:12px 14px;margin-bottom:10px;min-height:88px;'
                        f'display:flex;flex-direction:column;justify-content:space-between">'
                        f'<div style="font-family:{MONO};font-size:9px;font-weight:700;letter-spacing:1.5px;'
                        f'text-transform:uppercase;color:{GHOST};margin-bottom:6px">{icon_t} {lbl_t}</div>'
                        f'<div style="display:flex;align-items:center;gap:8px">'
                        f'  <span style="font-size:26px;font-weight:900;color:{cor_dir};line-height:1">{icon_dir}</span>'
                        f'  <span style="font-family:{MONO};font-size:14px;font-weight:700;color:{cor_dir}">{pct_str}</span>'
                        f'</div>'
                        f'<div style="font-size:10px;color:{GHOST};margin-top:4px">{ref_t}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                f'<div style="font-family:{MONO};font-size:11px;color:{MUTED};padding:16px;'
                f'text-align:center">Dados insuficientes para calcular tendências neste período</div>',
                unsafe_allow_html=True,
            )

    else:
        st.markdown(
        panel(f'<p style="color:{GHOST};font-size:13px;padding:8px 0">'
              f'Ainda sem dados históricos do Amazfit. Rode /sync no bot para começar.</p>'),
        unsafe_allow_html=True,
        )

