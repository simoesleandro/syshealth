"""Design tokens SYS.HEALTH — fonte única de cores, spacing e tipografia."""

# ── Cores semânticas ─────────────────────────────────────────────────────────
BG = "#080c14"
BG2 = "#0d1424"
BG3 = "#080e1a"
BG_SUBTLE = "#0a0f1a"
BORDER = "#1a2035"
BORDER2 = "#111c2e"
CYAN = "#00d4ff"
GREEN = "#00e676"
RED = "#ff6b6b"
PURPLE = "#a78bfa"
AMBER = "#fbbf24"
TEXT = "#e8edf5"
MUTED = "#6b7c93"  # Fase 5: contraste ≥4.5:1 em fundo escuro (era #4a5568)
GHOST = "#2a3448"

# ── Tipografia ───────────────────────────────────────────────────────────────
MONO = "'Space Mono',monospace"
DISPLAY = "'DM Sans',system-ui,sans-serif"

# ── Spacing (grid 8px) ─────────────────────────────────────────────────────
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 24
SPACE_6 = 32

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 12

# ── CSS :root (injeta em dashboard / sidebar) ────────────────────────────────
ROOT_CSS = f"""
:root{{
  --sh-bg:{BG};
  --sh-bg-elevated:{BG2};
  --sh-bg-subtle:{BG_SUBTLE};
  --sh-border:rgba(255,255,255,.07);
  --sh-border-strong:rgba(0,212,255,.22);
  --sh-text:{TEXT};
  --sh-text-muted:#8b9cb3;
  --sh-text-dim:{MUTED};
  --sh-accent:{CYAN};
  --sh-accent-soft:rgba(0,212,255,.10);
  --sh-success:{GREEN};
  --sh-error:{RED};
  --sh-warning:{AMBER};
  --sh-info:{PURPLE};
  --sh-radius-sm:{RADIUS_SM}px;
  --sh-radius-md:{RADIUS_MD}px;
  --sh-radius-lg:{RADIUS_LG}px;
  --sh-shadow-sm:0 1px 2px rgba(0,0,0,.35);
  --sh-shadow-md:0 8px 24px rgba(0,0,0,.45);
  --sh-space-1:{SPACE_1}px;
  --sh-space-2:{SPACE_2}px;
  --sh-space-3:{SPACE_3}px;
  --sh-space-4:{SPACE_4}px;
  --sh-space-5:{SPACE_5}px;
  --sh-space-6:{SPACE_6}px;
  --sh-font-display:{DISPLAY};
  --sh-font-mono:{MONO};
}}
"""

# ── Ícones Material (Streamlit st.button icon=) ───────────────────────────────
EDIT_ICON = ":material/edit:"
STAR_ICON = ":material/star:"
STAR_OUTLINE_ICON = ":material/star_outline:"
DELETE_ICON = ":material/delete:"
