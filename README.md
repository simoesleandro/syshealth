### ⚠️ AVISO DE DEPRECIAÇÃO
Este projeto foi a primeira versão do sistema (Python/Streamlit) e está arquivado. 
A versão definitiva encontra-se em: [[https://github.com/simoesleandro/sys-health]]

# ⚡ SYS.HEALTH

> Ecossistema pessoal de saúde e performance — dashboard em tempo real, bot Telegram com IA e sincronização automática de wearable.

🔗 **[Demo ao vivo](https://syshealth.streamlit.app/)**

---

## 📌 Sobre o Projeto

**SYS.HEALTH** é um sistema completo de monitoramento de saúde e performance desenvolvido como projeto de portfólio durante minha transição de carreira para a área de tecnologia, com foco em Análise e Desenvolvimento de Sistemas (FIAP).

O sistema integra dados de nutrição, treino, sono, HRV e agenda em um único painel — permitindo tomar decisões estratégicas sobre dieta e recuperação com base em dados reais do corpo, não em achismos.

---

## 🏗️ Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                        SYS.HEALTH                           │
├──────────────────┬───────────────────┬───────────────────────┤
│   DASHBOARD      │    BOT TELEGRAM   │    SYNC WEARABLE      │
│   Streamlit      │    Fly.io worker  │    Zepp API           │
│   Community      │    Gemini 2.5     │    Amazfit Bip 6      │
│   Cloud          │    Flash          │    10:00 BRT daily    │
└────────┬─────────┴─────────┬─────────┴───────────┬───────────┘
         │                   │                     │
         └───────────────────▼─────────────────────┘
                      ┌──────────────┐
                      │   Supabase   │
                      │  PostgreSQL  │
                      │   (nuvem)    │
                      └──────────────┘
```

### Fluxo principal

1. **Wearable** — Amazfit Bip 6 sincroniza passos, sono, HRV e PAI via API Zepp às 10h BRT
2. **Bot Telegram** — registra refeições por texto livre ou foto, água, peso e medicação via Gemini NLP/Vision
3. **Dashboard** — consolida todos os dados em tempo real, calcula déficit calórico, tendências e métricas de recuperação
4. **Banco** — Supabase PostgreSQL em produção, SQLite local para desenvolvimento

---

## 🧠 Funcionalidades

### Dashboard (Streamlit)
- **Nutrição** — controle de calorias, macros (proteínas, carboidratos, gorduras) e hidratação com metas diárias
- **Wearable + Agenda** — dados do Amazfit Bip 6 (passos, distância, sono, HRV, PAI) cruzados com Google Calendar
- **Evolução + Registros** — histórico de peso, medidas corporais e tendências ao longo do tempo
- **Banco de Refeições** — biblioteca pessoal de refeições com macros calculados
- **Histórico + Tendências** — gráficos de evolução de composição corporal e performance
- **Evacuação** — tracking de saúde intestinal para correlação com dieta

### Bot Telegram (IA)
- **Registro por texto livre** — "comi frango com arroz" → Gemini extrai e salva macros automaticamente
- **Análise de foto de prato** — envia foto → Gemini Vision identifica alimentos e calcula macros
- **Leitura de bioimpedância** — envia foto da tabela de avaliação física → IA extrai e salva medidas corporais
- **Sync manual** — `/sync` força sincronização imediata com o Zepp
- **Registro de HRV e PAI** — `/hrv 38` e `/pai 117` diretamente pelo chat
- **Presets de suplementos** — Whey Protein e Creatina com macros fixos pré-configurados

---

## 🛠️ Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.x |
| Dashboard | Streamlit (Streamlit Community Cloud) |
| Bot | pyTelegramBotAPI + Fly.io worker |
| IA | Google Gemini 2.5 Flash (NLP + Vision) |
| Banco (produção) | Supabase PostgreSQL |
| Banco (local) | SQLite3 |
| Wearable | Zepp API (Amazfit Bip 6) |
| Deploy bot | Fly.io (região GRU — São Paulo) |
| Concorrência | threading (bot + scheduler em daemon threads) |

---

## 🚀 Como Executar Localmente

### Pré-requisitos

- Python 3.10+
- Conta no [Supabase](https://supabase.com/) ou SQLite local
- Bot Telegram criado via [@BotFather](https://t.me/BotFather)
- Chave de API do [Google AI Studio](https://aistudio.google.com/)
- Conta Zepp com token de acesso (opcional)

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/simoesleandro/syshealth.git
cd syshealth

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Instale as dependências do dashboard
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais
```

### Variáveis de ambiente necessárias

```env
# Telegram
TELEGRAM_TOKEN=

# Google Gemini
GEMINI_API_KEY=

# Supabase (produção)
SUPABASE_URL=

# Zepp / Amazfit (opcional)
ZEPP_APP_TOKEN=
ZEPP_USER_ID=

# Google Calendar (opcional)
GOOGLE_CALENDAR_ID=
```

### Rodando o dashboard

```bash
streamlit run dashboard.py
```

### Rodando o bot

```bash
python main.py
```

---

## 📂 Estrutura do Projeto

```
syshealth/
├── dashboard.py          # Streamlit app (~5000 linhas)
├── bot.py                # Telegram bot com Gemini NLP e Vision
├── main.py               # Entrypoint Fly.io (bot + scheduler Zepp)
├── db.py                 # Abstração SQLite/PostgreSQL
├── nutri_engine.py       # Engine de cálculo de macros
├── zepp_sync.py          # Sync Amazfit Bip 6 via API Zepp
├── get_gcal_token.py     # Google Calendar integration
├── Dockerfile.bot        # Container do bot para Fly.io
├── fly.toml              # Config deploy Fly.io
├── requirements.txt      # Dependências do dashboard
├── requirements-bot.txt  # Dependências do bot
├── .env.example          # Template de variáveis
└── .gitignore
```

---

## 💡 Decisões de Arquitetura

**Por que dois serviços separados (dashboard + bot)?**
O dashboard é stateless e serve apenas leitura — deploy ideal no Streamlit Community Cloud com auto-redeploy no push. O bot precisa de processo contínuo rodando 24/7 — deploy ideal no Fly.io como worker sem porta HTTP exposta. Separar os dois permite escalar e debugar cada um de forma independente.

**Por que abstração SQLite/PostgreSQL no `db.py`?**
Desenvolvimento local usa SQLite (zero configuração). Produção usa Supabase PostgreSQL. A função `_pg_sql()` traduz dialeto SQLite para PostgreSQL via substituição de strings, permitindo usar o mesmo código nos dois ambientes sem branches condicionais espalhados pelo projeto.

**Por que Gemini Vision para registro de refeições?**
Um único prompt detecta automaticamente o tipo da imagem (prato de comida vs tabela de bioimpedância) e extrai os dados correspondentes — eliminando a necessidade de o usuário categorizar manualmente o que está enviando. Menos atrito = mais consistência nos dados.

**Por que threads daemon para o scheduler Zepp?**
O bot precisa responder a mensagens em tempo real enquanto o scheduler dorme até às 10h. Threads daemon garantem que o processo principal (bot) controla o ciclo de vida do scheduler — se o bot cair, o scheduler para junto.

---

## 👤 Autor

**Leandro Simões** — Desenvolvedor em transição de carreira, estudante de Análise e Desenvolvimento de Sistemas (FIAP 2026).

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Leandro%20Sim%C3%B5es-blue?logo=linkedin)](https://www.linkedin.com/in/leandro-sim%C3%B5es-7a0b3537b/)
[![GitHub](https://img.shields.io/badge/GitHub-simoesleandro-black?logo=github)](https://github.com/simoesleandro)

---

## ⚠️ Aviso

Este projeto foi desenvolvido para uso pessoal. Os dados de saúde são privados e não são compartilhados com terceiros.
