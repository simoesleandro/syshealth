# SYS.HEALTH — Context for Claude

## Stack
- Bot Telegram: Fly.io worker (`fly deploy --config fly.toml`), região `gru`
- Dashboard: Streamlit Community Cloud (auto-deploy via push em `main`)
- Banco: Supabase PostgreSQL (`SUPABASE_URL`) ou SQLite local (`nutricao.db`)
- IA: Gemini 2.5 Flash via `google-generativeai==0.8.3`

## Arquivos principais
- `dashboard.py` — Streamlit app (~4700 linhas)
- `bot.py` — Telegram bot com Gemini NLP e Vision
- `db.py` — abstração SQLite/PostgreSQL com `_pg_sql()` para dialect translation
- `main.py` — entrypoint Fly.io (bot + scheduler Zepp 07:00 BRT)
- `zepp_sync.py` — sync Amazfit Bip 6 via API Zepp

## Banco de dados
- `_pg_sql()` em db.py traduz SQLite→PostgreSQL por substituição de strings exatas
- Padrões traduzidos: `date(data_hora,'localtime')`, `strftime('%d/%m/%Y',data)` (sem wrapper `date()`)
- `strftime('%d/%m/%Y', date(data))` NÃO é traduzido — usar `strftime('%d/%m/%Y',data)`
- Colunas nullable: sempre proteger `iloc[0]` com `if val is not None`
- Tabela `medidas`: upsert por data — `UPDATE` se existe linha do dia, `INSERT` se não

## Timezone
- Streamlit Cloud e Fly.io rodam em UTC — sempre usar `ZoneInfo("America/Sao_Paulo")`
- `hoje_sql = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d")`

## Deploy
- Dashboard: push em `main` → Streamlit Cloud redeploya automaticamente (~1 min)
- Bot: requer `fly deploy --config fly.toml` após cada mudança em bot.py/main.py
- `fly secrets set VAR="valor" --app syshealth-bot` — setar UMA variável por vez (PowerShell)
- Após `fly scale count 1`: confirmar com `fly status --app syshealth-bot`

## Padrões do dashboard
- Feedback visual: usar `st.toast()`, nunca `st.success()` + `st.rerun()` (some antes do rerun)
- Timezone: todas as datas usam `_BR = ZoneInfo("America/Sao_Paulo")`
- SQL params: usar `db(query, params)` com lista de params — nunca f-string com valores
- Categorias dinâmicas: `_cat_hora()` retorna categoria pela hora atual de Brasília
- Toggle panels: `st.session_state.get("chave_open", False)` + botão `▾/▴` + `st.rerun()` — padrão usado em nova medida, banco, biometria
- Modais de registro: usar `@st.dialog("Título")` — chamar a função diretamente no clique do botão, sem session_state flag; definir em nível de módulo
- `st.rerun(scope="fragment")` dentro de `@st.dialog` mantém o modal aberto; bare `st.rerun()` fecha o modal — Streamlit ≥ 1.37 exigido
- Edição de registros: selectbox de datas + form pré-preenchido com helper `_ev(col)` que retorna `float(v) if v is not None and not pd.isna(v) else fallback`
- Imports de data: usar `from datetime import datetime, timedelta` — `timedelta` necessário para cálculos de datas

## Streamlit — Gotchas
- JS injection: `st.markdown(unsafe_allow_html=True)` NÃO executa `<script>` (stripped pelo DOMPurify) — usar `st.html()` para scripts
- CSS em `st.markdown` funciona normalmente; separar CSS (`st.markdown`) de JS (`st.html`) quando injetando ambos
- Widget keys dentro de `@st.dialog` devem ser distintas das keys de forms inline — usar sufixo `_modal` para evitar conflitos
- IntersectionObserver existente em `st.html` ~linha 418 (breakpoint detection + antigo nav observer) — não duplicar observers de scroll

## Gemini Vision
- Usar prompt unificado que detecta tipo (refeição/medidas/outro) + extrai dados numa chamada
- Não depender de legenda do usuário para rotear — Gemini detecta automaticamente
- Importar `PIL.Image` dentro da função, não no topo do módulo

## GitHub (sem gh CLI)
- Credenciais: `printf "protocol=https\nhost=github.com\n" | git credential fill`
- Criar PR: `curl -X POST -H "Authorization: token <tok>" https://api.github.com/repos/simoesleandro/syshealth-fit/pulls`

## Secrets (Streamlit Cloud)
- Secrets ficam em `st.secrets`, não em `os.environ`
- Shim no topo do dashboard.py copia `st.secrets → os.environ` para que `db.py` funcione
