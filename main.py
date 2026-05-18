"""
main.py — Entrypoint da nuvem
Roda o bot do Telegram + sync diario do Zepp (07:00 Brasilia)
Banco de dados: Supabase (PostgreSQL) ou SQLite local via db.py
"""
import threading
import time
import logging
import os
from datetime import date
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")

# Sem criacao de pasta — banco e o Turso
import db as DB
DB.init_tables()
log.info(f"Banco: {DB.backend()}")


def run_bot():
    log.info("Iniciando bot do Telegram...")
    import bot as bot_module
    bot_module.bot.infinity_polling(timeout=30, long_polling_timeout=30)


def run_zepp_scheduler():
    from zepp_sync import zepp_sync, save, init_db
    init_db()
    log.info("Scheduler Zepp iniciado — sync diario as 07:00 Brasilia")
    ultimo_sync = None

    _fuso_br = ZoneInfo("America/Sao_Paulo")
    while True:
        agora_br = datetime.now(_fuso_br)
        hora_br  = agora_br.hour
        hoje     = agora_br.strftime("%Y-%m-%d")

        if hora_br == 7 and ultimo_sync != hoje:
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
    log.info("=== SYS.HEALTH iniciando ===")

    t_zepp = threading.Thread(target=run_zepp_scheduler, daemon=True)
    t_zepp.start()

    run_bot()