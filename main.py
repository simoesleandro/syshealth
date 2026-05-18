"""
main.py — Entrypoint da nuvem
Roda o bot do Telegram em paralelo com o sync diário do Zepp (07:00)
"""
import threading
import time
import logging
import os
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")

# Garante que o DB_PATH aponta para o volume persistente
DB_PATH = os.getenv("DB_PATH", "/data/nutricao.db")
os.environ["DB_PATH"] = DB_PATH

# Cria o diretório /data se não existir (ambiente local)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def run_bot():
    """Inicia o bot do Telegram em loop infinito."""
    log.info("Iniciando bot do Telegram...")
    # Importa aqui para garantir que DB_PATH já está setado
    import bot as bot_module
    bot_module.init_amazfit_table()
    bot_module.bot.infinity_polling(timeout=30, long_polling_timeout=30)


def run_zepp_scheduler():
    """Roda o sync do Zepp todo dia às 07:00 (horário de Brasília = UTC-3)."""
    from zepp_sync import zepp_sync, init_db, save
    init_db(DB_PATH)
    log.info("Scheduler do Zepp iniciado — sync diário às 07:00")

    ultimo_sync = None

    while True:
        agora = datetime.utcnow()
        # UTC-3 = Brasília
        hora_br = (agora.hour - 3) % 24
        hoje    = date.today().strftime("%Y-%m-%d")

        if hora_br == 7 and ultimo_sync != hoje:
            log.info("Executando sync automático do Zepp...")
            try:
                row = zepp_sync(hoje)
                if row:
                    save(DB_PATH, row)
                    log.info(f"Sync OK: {row}")
                else:
                    log.warning("Zepp não retornou dados")
            except Exception as e:
                log.error(f"Erro no sync: {e}")
            ultimo_sync = hoje

        time.sleep(60)  # checa a cada 1 minuto


if __name__ == "__main__":
    log.info("=== SYS.HEALTH iniciando ===")
    log.info(f"DB: {DB_PATH}")

    # Thread do scheduler do Zepp
    t_zepp = threading.Thread(target=run_zepp_scheduler, daemon=True)
    t_zepp.start()

    # Bot roda na thread principal
    run_bot()
