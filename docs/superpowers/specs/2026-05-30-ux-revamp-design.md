# UX Revamp — SYS.HEALTH Dashboard

**Data:** 2026-05-30  
**Status:** Aprovado  
**Escopo:** Melhoria de navegação, registros via modal e ocultação de seções secundárias

---

## Contexto

O dashboard (`dashboard.py`, ~4.900 linhas) é um Streamlit app de saúde pessoal com seções de Nutrição, Wearable, Treinos, Agenda, Evolução, Banco de Refeições, Histórico, Biometria, Evacuação e Medicação. Três problemas de UX identificados pelo usuário:

1. A navegação no sidebar não tem feedback visual de posição nem transição suave.
2. Formulários de registro abrem painéis inline (▾/▴) que empurram o conteúdo e desorientam.
3. Seções pouco usadas (IA Coach, Biometria, Medicação) poluem a navegação principal.

---

## Decisões de Design

| Tema | Decisão |
|---|---|
| Navegação | Sidebar com pill ativo + smooth scroll (Opção A) |
| Abertura de registros | Modal `@st.dialog` centralizado (Opção B) |
| Seções secundárias | Ocultas por padrão, acessíveis via toggle `⚙️ Avançado` |

---

## Parte 1 — Sidebar: Pill Ativo + Smooth Scroll

### Comportamento
- Clicar em qualquer link de seção no sidebar faz scroll suave até ela (`scrollIntoView({ behavior: 'smooth', block: 'start' })`).
- Um `IntersectionObserver` detecta qual seção está no viewport e aplica classe `active` ao link correspondente no sidebar.
- O link ativo recebe estilo pill: fundo `rgba(0,212,255,0.12)`, borda esquerda `2px solid #00d4ff`, texto na cor `#00d4ff`.

### Implementação
- Um bloco único de CSS + JS é injetado via `st.markdown(unsafe_allow_html=True)` no início do bloco `with st.sidebar:`.
- O script seleciona os elementos `<a>` do sidebar pelo atributo `href` (âncoras `#sec-*`) e os elementos `<div id="sec-*">` no corpo.
- Nenhuma alteração na estrutura Python das seções ou nos links existentes.
- O `IntersectionObserver` usa `threshold: 0.2` — seção é considerada "ativa" quando 20% dela está visível.

### O que não muda
- Posição e texto dos links de navegação.
- Atalhos rápidos do sidebar.
- Layout geral do sidebar.

---

## Parte 2 — Registros via `@st.dialog`

### Comportamento
- Botões de registro (Nova Refeição, Água, Suplemento, Evacuação) deixam de ter o padrão toggle `▾/▴`.
- Ao clicar, setam um flag em `st.session_state` (ex: `st.session_state["open_modal_refeicao"] = True`) e fazem `st.rerun()`.
- No topo do arquivo (após imports), funções decoradas com `@st.dialog` são definidas para cada tipo de registro. O Streamlit renderiza overlay modal com backdrop escuro e botão `×` automaticamente.
- Os atalhos rápidos do sidebar (➕ Refeição, 💧 Água, 💊 Suplemento) também ativam os mesmos flags — comportamento idêntico.

### Formulários convertidos
| Registro | Função atual | Nova função dialog |
|---|---|---|
| Refeição | `_tab_refeicao()` inline | `@st.dialog("➕ Nova Refeição", width="large")` |
| Água | `_tab_agua()` inline | `@st.dialog("💧 Registrar Água")` |
| Suplemento | `_tab_suplemento()` inline | `@st.dialog("💊 Suplemento")` |
| Evacuação | form inline | `@st.dialog("🚽 Registrar Evacuação")` |

### O que não muda
- Lógica interna dos formulários (validação, banco de dados, `st.toast`, `st.rerun` pós-save).
- Estrutura das queries e inserts.
- Os botões `▾/▴` das seções de visualização (histórico, edição) — apenas os de novo registro são convertidos.

### Requisito técnico
- Streamlit ≥ 1.31 (suporte a `@st.dialog`). Streamlit Cloud usa versão compatível.

---

## Parte 3 — Seções Secundárias Ocultas por Padrão

### Seções afetadas
- 🤖 IA Coach (Gemini)
- 📏 Biometria
- 💊 Medicação (Tirzepatida)

### Comportamento no sidebar
- Abaixo dos links de navegação principais, um item `⚙️ Avançado ▾/▴` é adicionado.
- Ao clicar, expande 3 sub-links: `🤖 IA Coach`, `📏 Biometria`, `💊 Medicação`.
- Estado salvo em `st.session_state["sidebar_avancado_open"]` (padrão: `False`).

### Comportamento no corpo da página
- Os blocos das 3 seções (incluindo seus `<div id="sec-*">`) são envoltos em `if st.session_state.get("sidebar_avancado_open", False):`.
- Quando fechadas, não são renderizadas — reduz tempo de carregamento e queries desnecessárias.
- Os links de âncora são removidos do nav principal do sidebar; as âncoras no corpo só existem quando as seções estão visíveis.
- Os sub-links dentro de `⚙️ Avançado` fazem dois passos: (1) setam `sidebar_avancado_open = True` + `scroll_to_sec = "biometria"` em session_state e fazem `rerun()`; (2) após o rerun, a seção renderiza e um JS lê `scroll_to_sec` para fazer o scroll suave até ela.
- O `IntersectionObserver` (Parte 1) só observa seções que existem no DOM — seções ocultas são ignoradas automaticamente.

### O que não muda
- Lógica, dados e layout interno das 3 seções quando abertas.
- Funcionamento completo quando o toggle `⚙️ Avançado` está ativo.

---

## Ordem de Implementação Recomendada

1. **Parte 3** (ocultar seções) — mais simples, zero risco, melhoria imediata de performance.
2. **Parte 1** (smooth scroll + pill) — CSS/JS injection isolada, não toca lógica.
3. **Parte 2** (modais) — maior esforço, fazer por formulário (Água primeiro, depois Suplemento, Refeição, Evacuação).

---

## Fora de Escopo

- Redesign visual (cores, tipografia, cards) — estrutura visual mantida.
- Remoção permanente de seções — todas as 3 continuam funcionais.
- Mudança de stack (Streamlit permanece).
- Novos campos ou funcionalidades nos formulários.
