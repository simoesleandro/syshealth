# SYS.HEALTH — Context for Claude

## Stack
- Bot Telegram: Fly.io worker (`fly deploy --config fly.toml`), região `gru`
- Dashboard: Streamlit Community Cloud (auto-deploy via push em `main`)
- Banco: Supabase PostgreSQL (`SUPABASE_URL`) ou SQLite local (`nutricao.db`)
- IA: Gemini 2.5 Flash via `google-generativeai==0.8.3`

## Arquivos principais
- `dashboard.py` — Streamlit app (~1400 linhas)
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
