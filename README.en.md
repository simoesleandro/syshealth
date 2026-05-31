# ⚡ SYS.HEALTH

> Personal health and performance ecosystem — real-time dashboard, AI-powered Telegram bot, and automatic wearable sync.

🔗 **[Live Demo](https://syshealth-fit.streamlit.app/)**

---

## 📌 About

**SYS.HEALTH** is a complete health and performance monitoring system built as a portfolio project during my career transition into tech, with a focus on Systems Analysis and Development (FIAP).

The system integrates nutrition, training, sleep, HRV, and calendar data into a single dashboard — enabling strategic decisions about diet and recovery based on real body data, not guesswork.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        SYS.HEALTH                           │
├──────────────────┬───────────────────┬───────────────────────┤
│   DASHBOARD      │   TELEGRAM BOT    │   WEARABLE SYNC       │
│   Streamlit      │   Fly.io worker   │   Zepp API            │
│   Community      │   Gemini 2.5      │   Amazfit Bip 6       │
│   Cloud          │   Flash           │   10:00 BRT daily     │
└────────┬─────────┴─────────┬─────────┴───────────┬───────────┘
         │                   │                     │
         └───────────────────▼─────────────────────┘
                      ┌──────────────┐
                      │   Supabase   │
                      │  PostgreSQL  │
                      │   (cloud)    │
                      └──────────────┘
```

### Main Flow

1. **Wearable** — Amazfit Bip 6 syncs steps, sleep, HRV, and PAI via Zepp API daily at 10:00 BRT
2. **Telegram Bot** — logs meals via free text or photo, water, weight, and medication using Gemini NLP/Vision
3. **Dashboard** — consolidates all data in real time, calculates caloric deficit, trends, and recovery metrics
4. **Database** — Supabase PostgreSQL in production, SQLite locally for development

---

## 🧠 Features

### Dashboard (Streamlit)
- **Nutrition** — calorie and macro tracking (protein, carbs, fat) with daily goals and hydration control
- **Wearable + Calendar** — Amazfit Bip 6 data (steps, distance, sleep, HRV, PAI) crossed with Google Calendar cognitive load
- **Evolution + Records** — body weight history, measurements, and long-term trends
- **Meal Bank** — personal library of meals with pre-calculated macros
- **History + Trends** — body composition and performance evolution charts
- **Gut Health** — bowel tracking for correlation with diet

### Telegram Bot (AI)
- **Free-text logging** — "had chicken with rice" → Gemini extracts and saves macros automatically
- **Meal photo analysis** — send a photo → Gemini Vision identifies foods and calculates macros
- **Body measurement reading** — send a photo of a physical assessment form → AI extracts and saves measurements
- **Manual sync** — `/sync` forces an immediate Zepp synchronization
- **HRV and PAI logging** — `/hrv 38` and `/pai 117` directly via chat
- **Supplement presets** — Whey Protein and Creatine with pre-configured fixed macros

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.x |
| Dashboard | Streamlit (Streamlit Community Cloud) |
| Bot | pyTelegramBotAPI + Fly.io worker |
| AI | Google Gemini 2.5 Flash (NLP + Vision) |
| Database (prod) | Supabase PostgreSQL |
| Database (local) | SQLite3 |
| Wearable | Zepp API (Amazfit Bip 6) |
| Bot deploy | Fly.io (GRU region — São Paulo) |
| Concurrency | threading (bot + scheduler as daemon threads) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [Supabase](https://supabase.com/) account or local SQLite
- Telegram bot created via [@BotFather](https://t.me/BotFather)
- [Google AI Studio](https://aistudio.google.com/) API key
- Zepp account with access token (optional)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/simoesleandro/syshealth-fit.git
cd syshealth-fit

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install dashboard dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

```env
# Telegram
TELEGRAM_TOKEN=

# Google Gemini
GEMINI_API_KEY=

# Supabase (production)
SUPABASE_URL=

# Zepp / Amazfit (optional)
ZEPP_APP_TOKEN=
ZEPP_USER_ID=

# Google Calendar (optional)
GOOGLE_CALENDAR_ID=
```

### Running the dashboard

```bash
streamlit run dashboard.py
```

### Running the bot

```bash
python main.py
```

---

## 📂 Project Structure

```
syshealth-fit/
├── dashboard.py          # Streamlit app (~5000 lines)
├── bot.py                # Telegram bot with Gemini NLP and Vision
├── main.py               # Fly.io entrypoint (bot + Zepp scheduler)
├── db.py                 # SQLite/PostgreSQL abstraction layer
├── nutri_engine.py       # Macro calculation engine
├── zepp_sync.py          # Amazfit Bip 6 sync via Zepp API
├── get_gcal_token.py     # Google Calendar integration
├── Dockerfile.bot        # Bot container for Fly.io
├── fly.toml              # Fly.io deploy config
├── requirements.txt      # Dashboard dependencies
├── requirements-bot.txt  # Bot dependencies
├── .env.example          # Environment variables template
└── .gitignore
```

---

## 💡 Architecture Decisions

**Why two separate services (dashboard + bot)?**
The dashboard is stateless and read-only — ideal for Streamlit Community Cloud with auto-redeploy on push. The bot needs a continuous process running 24/7 — ideal for Fly.io as an HTTP-less worker. Separating them allows independent scaling and debugging.

**Why a SQLite/PostgreSQL abstraction layer in `db.py`?**
Local development uses SQLite (zero configuration). Production uses Supabase PostgreSQL. The `_pg_sql()` function translates SQLite dialect to PostgreSQL via string substitution, enabling the same codebase to run in both environments without conditional branches scattered throughout the project.

**Why Gemini Vision for meal logging?**
A single prompt automatically detects the image type (food plate vs. body measurement table) and extracts the corresponding data — eliminating the need for the user to manually categorize what they're sending. Less friction = more consistent data.

**Why daemon threads for the Zepp scheduler?**
The bot must respond to messages in real time while the scheduler sleeps until 10:00. Daemon threads ensure the main process (bot) controls the scheduler's lifecycle — if the bot crashes, the scheduler stops with it.

---

## 👤 Author

**Leandro Simões** — Developer transitioning into tech, studying Systems Analysis and Development (FIAP 2026).

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Leandro%20Sim%C3%B5es-blue?logo=linkedin)](https://www.linkedin.com/in/leandro-sim%C3%B5es-7a0b3537b/)
[![GitHub](https://img.shields.io/badge/GitHub-simoesleandro-black?logo=github)](https://github.com/simoesleandro)

---

## ⚠️ Notice

This project was built for personal use. Health data is private and not shared with third parties.
