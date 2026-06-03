"""
main.py — Entrypoint da nuvem
Roda o bot do Telegram + sync diario do Zepp (07:00 Brasilia)
Banco de dados: Turso (nuvem) — sem arquivo local necessario
"""
import threading
import time
import logging
import os
from datetime import datetime, date
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

FUSO_BR = ZoneInfo("America/Sao_Paulo")

load_dotenv()

log = logging.getLogger("main")


def _bootstrap_db():
    """Inicializa o banco — só no processo worker (nunca como import do dashboard)."""
    import db as DB
    DB.init_tables()
    log.info(f"Banco: {DB.backend()}")
    return DB


def run_bot():
    log.info("Iniciando bot do Telegram...")
    import bot as bot_module
    bot_module.bot.infinity_polling(timeout=30, long_polling_timeout=30)


def run_zepp_scheduler():
    from zepp_sync import zepp_sync, save, init_db
    init_db()
    log.info("Scheduler Zepp iniciado — sync diario as 10:00 Brasilia")
    ultimo_sync = None

    while True:
        agora_br = datetime.now(FUSO_BR)
        hoje     = agora_br.date().strftime("%Y-%m-%d")

        if agora_br.hour == 10 and ultimo_sync != hoje:
            log.info("Executando sync automatico do Zepp...")
            try:
                row = zepp_sync(hoje)
                if row:
                    save(row)
                    log.info(f"Sync OK — passos={row['passos']} sono={row['sono_total_min']}min")
                else:
                    log.warning("Zepp nao retornou dados")
            except Exception as e:
                log.error(f"Erro no sync: {e}")
            ultimo_sync = hoje

        time.sleep(60)


if __name__ == "__main__":
    import sys

    if "streamlit" in sys.modules:
        raise RuntimeError(
            "main.py is the Fly.io bot worker entrypoint. "
            "Run the dashboard with: streamlit run dashboard.py"
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    log.info("=== SYS.HEALTH iniciando ===")
    _bootstrap_db()

    t_zepp = threading.Thread(target=run_zepp_scheduler, daemon=True)
    t_zepp.start()

    run_bot()
