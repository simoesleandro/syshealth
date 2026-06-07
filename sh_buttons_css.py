"""CSS compartilhado — botões fluidos + hover azul SYS.HEALTH."""

FLUID_BUTTONS_CSS = """
/* ── Botões fluidos — só no conteúdo principal (não sidebar) ── */
.stApp [data-testid="stAppViewContainer"] [data-testid="stButton"],
.stApp .block-container [data-testid="stButton"],
[data-testid="stDialog"] [data-testid="stButton"],
[data-testid="stForm"] [data-testid="stButton"]{
  width:auto!important;max-width:100%!important;align-self:flex-start!important;
  flex:0 0 auto!important}
.stApp [data-testid="stAppViewContainer"] [data-testid="stButton"] button,
.stApp [data-testid="stAppViewContainer"] [data-testid="stBaseButton-secondary"],
.stApp [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"],
.stApp .block-container [data-testid="stButton"] button,
.stApp .block-container [data-testid="stBaseButton-secondary"],
.stApp .block-container [data-testid="stBaseButton-primary"],
[data-testid="stDialog"] [data-testid="stButton"] button,
[data-testid="stDialog"] [data-testid="stBaseButton-secondary"],
[data-testid="stDialog"] [data-testid="stBaseButton-primary"]{
  width:auto!important;max-width:100%!important;white-space:nowrap!important}
.stApp [data-testid="stAppViewContainer"] [data-testid="stFormSubmitButton"],
.stApp .block-container [data-testid="stFormSubmitButton"],
[data-testid="stDialog"] [data-testid="stFormSubmitButton"]{
  width:auto!important;align-self:flex-start!important;flex:0 0 auto!important}
.stApp [data-testid="stAppViewContainer"] [data-testid="stFormSubmitButton"] button,
.stApp .block-container [data-testid="stFormSubmitButton"] button,
[data-testid="stDialog"] [data-testid="stFormSubmitButton"] button{
  width:auto!important;min-width:108px!important;max-width:100%!important;white-space:nowrap!important}

/* Botão sozinho na vertical — só main */
.stApp [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"]:has(> [data-testid="stButton"]),
.stApp .block-container [data-testid="stVerticalBlock"]:has(> [data-testid="stButton"]){
  align-items:flex-start!important}
.stApp [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] > [data-testid="stButton"],
.stApp .block-container [data-testid="stVerticalBlock"] > [data-testid="stButton"]{
  width:auto!important;align-self:flex-start!important}

/* Linha de ações de seção — gap 8px, alinhada à esquerda */
[data-testid="stMarkdownContainer"]:has(.sh-section-actions-mark)+[data-testid="stHorizontalBlock"],
[data-testid="stVerticalBlock"]:has(.sh-section-actions-mark)>[data-testid="stHorizontalBlock"]{
  gap:8px!important;flex-wrap:wrap!important;justify-content:flex-start!important;
  align-items:center!important;margin:8px 0 12px!important}
[data-testid="stMarkdownContainer"]:has(.sh-section-actions-mark)+[data-testid="stHorizontalBlock"] [data-testid="stButton"],
[data-testid="stVerticalBlock"]:has(.sh-section-actions-mark)>[data-testid="stHorizontalBlock"] [data-testid="stButton"],
[data-testid="stMarkdownContainer"]:has(.sh-section-actions-mark)+[data-testid="stHorizontalBlock"] [data-testid="stFormSubmitButton"],
[data-testid="stVerticalBlock"]:has(.sh-section-actions-mark)>[data-testid="stHorizontalBlock"] [data-testid="stFormSubmitButton"]{
  width:auto!important;align-self:flex-start!important;flex:0 0 auto!important}

/* Linhas de botões: colunas encolhem ao conteúdo */
.stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="column"] [data-testid="stButton"]),
.stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="column"] [data-testid="stFormSubmitButton"]),
[data-testid="stDialog"] [data-testid="stHorizontalBlock"]:has(> [data-testid="column"] [data-testid="stButton"]),
[data-testid="stDialog"] [data-testid="stHorizontalBlock"]:has(> [data-testid="column"] [data-testid="stFormSubmitButton"]){
  gap:8px!important;flex-wrap:wrap!important;justify-content:flex-start!important;
  align-items:center!important}
.stApp [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([data-testid="stButton"]),
.stApp [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([data-testid="stFormSubmitButton"]),
[data-testid="stDialog"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([data-testid="stButton"]),
[data-testid="stDialog"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([data-testid="stFormSubmitButton"]){
  flex:0 0 auto!important;width:auto!important;min-width:0!important;max-width:100%!important}

/* Estado padrão unificado — primary/submit = secondary (cyan só no hover) */
.stApp [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"],
.stApp .block-container [data-testid="stBaseButton-primary"],
[data-testid="stDialog"] [data-testid="stBaseButton-primary"],
.stApp [data-testid="stFormSubmitButton"] button,
[data-testid="stDialog"] [data-testid="stFormSubmitButton"] button{
  background:#0c1525!important;border:1px solid #1e2840!important;
  color:#e8edf5!important;box-shadow:none!important}

/* Tamanho base compacto */
.stApp [data-testid="stAppViewContainer"] [data-testid="stBaseButton-secondary"],
.stApp [data-testid="stAppViewContainer"] [data-testid="stBaseButton-primary"],
.stApp .block-container [data-testid="stBaseButton-secondary"],
.stApp .block-container [data-testid="stBaseButton-primary"],
[data-testid="stDialog"] [data-testid="stBaseButton-secondary"],
[data-testid="stDialog"] [data-testid="stBaseButton-primary"],
.stApp [data-testid="stFormSubmitButton"] button,
[data-testid="stDialog"] [data-testid="stFormSubmitButton"] button{
  min-height:36px!important;padding:8px 14px!important;
  font-family:var(--sh-font-display,'DM Sans',system-ui,sans-serif)!important;
  font-size:12px!important;font-weight:600!important;
  letter-spacing:0!important;text-transform:none!important;border-radius:8px!important;
  transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease,background .18s ease,color .18s ease!important}

/* ── Hover padrão SYS.HEALTH — highlight azul ── */
.stApp [data-testid="stBaseButton-secondary"]:hover,
.stApp [data-testid="stBaseButton-primary"]:hover,
.stApp [data-testid="stFormSubmitButton"] button:hover,
[data-testid="stDialog"] [data-testid="stBaseButton-secondary"]:hover,
[data-testid="stDialog"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stDialog"] [data-testid="stFormSubmitButton"] button:hover{
  border-color:rgba(0,212,255,.45)!important;color:#00d4ff!important;
  background:rgba(0,212,255,.1)!important;box-shadow:0 0 16px rgba(0,212,255,.2)!important;
  transform:translateY(-1px)!important}

/* Sidebar links + botões — hover alinhado ao design system */
a.sh-side-btn:hover{
  border-color:rgba(0,212,255,.45)!important;color:#00d4ff!important;
  background:rgba(0,212,255,.08)!important;box-shadow:0 0 12px rgba(0,212,255,.16)!important;
  transform:none!important}
section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover{
  border-color:rgba(0,212,255,.45)!important;color:#00d4ff!important;
  background:rgba(0,212,255,.08)!important;box-shadow:0 0 12px rgba(0,212,255,.16)!important;
  transform:none!important}
.sh-agua-chips [data-testid="stButton"],
.sh-agua-chips [data-testid="stButton"] button{
  width:auto!important;max-width:100%!important}

/* Banco: ícones 32px fixos (exceção) */
[data-testid="stMarkdownContainer"]:has(.sh-banco-hit-mark)+[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] button{
  min-width:32px!important;max-width:32px!important;width:32px!important;
  min-height:32px!important;max-height:32px!important;height:32px!important;padding:0!important}

/* Métricas: colunas de cards intactas */
[data-testid="stHorizontalBlock"]:has(.sh-metric) > [data-testid="column"],
[data-testid="stHorizontalBlock"]:has(.sh-metric--hero) > [data-testid="column"],
[data-testid="stHorizontalBlock"]:has(.sh-metric--compact) > [data-testid="column"]{
  flex:1 1 auto!important;width:auto!important}

/* Modal — X do header: ghost, hover ciano sem caixa */
[data-testid="stDialog"] header button:hover,
[data-testid="stDialog"] [data-testid="stModalHeader"] button:hover{
  color:#00d4ff!important;background:rgba(0,212,255,.08)!important;
  border-radius:6px!important;box-shadow:none!important;transform:none!important}

/* Header sync — ver .sh-sync-btn em dashboard.py */
"""

A11Y_CSS = """
/* ── Acessibilidade — Fase 5 ── */

/* Skip link */
.sh-skip-link{
  position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden;
  z-index:100001;padding:10px 18px;background:var(--sh-bg-elevated,#0d1424);
  color:var(--sh-accent,#00d4ff);border:2px solid var(--sh-accent,#00d4ff);
  border-radius:8px;font-family:var(--sh-font-display);font-size:13px;font-weight:700;
  text-decoration:none;letter-spacing:.02em}
.sh-skip-link:focus,.sh-skip-link:focus-visible{
  left:16px!important;top:16px!important;width:auto!important;height:auto!important;
  overflow:visible!important;outline:none!important;
  box-shadow:0 0 0 3px rgba(0,212,255,.35)!important}

/* Foco visível — controles interativos */
button:focus-visible,
a:focus-visible,
summary:focus-visible,
[data-testid="stBaseButton-secondary"]:focus-visible,
[data-testid="stBaseButton-primary"]:focus-visible,
[data-testid="stFormSubmitButton"] button:focus-visible,
button[data-baseweb="tab"]:focus-visible,
[data-testid="stTextInput"] input:focus-visible,
[data-testid="stTextArea"] textarea:focus-visible,
[data-testid="stNumberInput"] input:focus-visible,
[data-testid="stDateInput"] input:focus-visible,
[data-testid="stTimeInput"] input:focus-visible,
[data-baseweb="select"]:focus-within,
[data-testid="stRadio"] label:focus-within{
  outline:2px solid var(--sh-accent,#00d4ff)!important;
  outline-offset:2px!important}
button:focus:not(:focus-visible),
[data-testid="stBaseButton-secondary"]:focus:not(:focus-visible),
[data-testid="stBaseButton-primary"]:focus:not(:focus-visible){
  outline:none!important}

/* Estados disabled / active */
[data-testid="stBaseButton-secondary"]:disabled,
[data-testid="stBaseButton-primary"]:disabled,
[data-testid="stFormSubmitButton"] button:disabled{
  opacity:.45!important;cursor:not-allowed!important;
  transform:none!important;box-shadow:none!important}
[data-testid="stBaseButton-secondary"]:active:not(:disabled),
[data-testid="stBaseButton-primary"]:active:not(:disabled){
  transform:translateY(0)!important;background:rgba(0,212,255,.06)!important}

/* Contraste — texto secundário em fundo escuro (≥4.5:1 onde possível) */
button[data-baseweb="tab"]{color:var(--sh-text-dim,#6b7c93)!important}
.sh-mobile-hint{color:var(--sh-text-dim,#6b7c93)!important}
.sh-section__title{color:var(--sh-text-muted,#8b9cb3)!important}

/* Âncoras de seção — scroll-margin para teclado / skip link */
div[id^="sec-"]{scroll-margin-top:72px}

/* Tabelas largas — hint scroll mobile */
html.sh-xs .sh-table-scroll,
html.sh-sm .sh-table-scroll{
  -webkit-overflow-scrolling:touch}
html.sh-xs .sh-table-scroll::after,
html.sh-sm .sh-table-scroll::after{
  content:'Deslize para ver mais →';display:block;font-size:10px;
  color:var(--sh-text-dim,#6b7c93);text-align:center;padding:6px 0 2px;
  font-family:var(--sh-font-mono)}

/* Alvos de toque mínimos (WCAG 2.5.5) — mobile */
html.sh-xs [data-testid="stHorizontalBlock"]:has(.sh-med-row) button,
html.sh-xs [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child:has([data-testid="stIconMaterial"]) button,
html.sh-xs .sh-mob-quick-nav button{
  min-height:44px!important;min-width:44px!important}

/* prefers-reduced-motion */
@media(prefers-reduced-motion:reduce){
  html{scroll-behavior:auto!important}
  [data-testid="stApp"],
  [data-testid="stApp"][data-stale="true"]{
    transition:none!important}
  [data-testid="stBaseButton-secondary"],
  [data-testid="stBaseButton-primary"],
  [data-testid="stFormSubmitButton"] button,
  .sh-metric,.sh-card,.sh-stat-card,.sh-feature-panel,
  section[data-testid="stSidebar"] [data-testid="stButton"] > button{
    transition:none!important}
  [data-testid="stBaseButton-secondary"]:hover,
  [data-testid="stBaseButton-primary"]:hover,
  [data-testid="stFormSubmitButton"] button:hover,
  .sh-metric:hover,
  section[data-testid="stSidebar"] [data-testid="stButton"] > button:hover{
    transform:none!important}
  .sh-goal-overlay,.sh-goal-overlay *,.sh-notif-overlay,.sh-notif-overlay *{
    animation:none!important;transition:none!important}}
"""
