"""
zepp_sync.py — versão nuvem
"""
import base64, json, logging, os, sqlite3, time
from datetime import date, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()
log     = logging.getLogger("zepp_sync")
BASE    = "https://api-mifit-us3.zepp.com"
DB_PATH = os.getenv("DB_PATH", "nutricao.db")


def make_headers(token):
    return {
        "Accept": "*/*", "appname": "com.huami.midong",
        "appplatform": "ios_phone", "apptoken": token,
        "channel": "appstore", "country": "BR", "lang": "pt_BR",
        "timezone": "America/Sao_Paulo",
        "User-Agent": "Zepp/10.3.1 (iPhone; iOS 26.4.2; Scale/3.00)", "v": "2.0",
    }


def decode_summary(b64):
    try:
        pad = b64 + "=" * (4 - len(b64) % 4)
        return json.loads(base64.b64decode(pad).decode("utf-8", "replace"))
    except Exception:
        return {}


def _get_existing(day):
    try:
        conn = sqlite3.connect(DB_PATH)
        row  = conn.execute(
            "SELECT hrv_ms, pai FROM amazfit_dados WHERE data_hora=?",
            (f"{day} 00:00:00",)).fetchone()
        conn.close()
        return {"hrv_ms": row[0], "pai": row[1]} if row else {}
    except Exception:
        return {}


def zepp_sync(day=None):
    token   = os.getenv("ZEPP_APP_TOKEN", "").strip()
    user_id = os.getenv("ZEPP_USER_ID", "").strip()
    if not token or not user_id:
        return None
    day = day or date.today().strftime("%Y-%m-%d")
    try:
        r     = requests.get(f"{BASE}/v1/data/band_data.json",
                             headers=make_headers(token),
                             params={"query_type": "summary", "device_type": "0",
                                     "object_id": user_id,
                                     "from_date": day, "to_date": day},
                             timeout=15)
        items = r.json().get("data", [])
        if not items:
            return None
        s    = decode_summary(items[0].get("summary", ""))
        stp  = s.get("stp", {}) or {}
        slp  = s.get("slp", {}) or {}
        deep = int(slp.get("dp", 0) or 0)
        lt   = int(slp.get("lt", 0) or 0)
        rem  = int(slp.get("dt", 0) or 0)
        tot  = deep + lt + rem or int(slp.get("ebt", 0) or 0)
        prev = _get_existing(day)
        return {
            "data_hora":         f"{day} 00:00:00",
            "passos":            int(stp.get("ttl", 0) or 0),
            "calorias_gastas":   int(stp.get("cal", 0) or 0),
            "distancia_km":      round(int(stp.get("dis", 0) or 0) / 1000, 2),
            "sono_total_min":    tot,
            "sono_profundo_min": deep,
            "hrv_ms":            prev.get("hrv_ms", 0),
            "pai":               prev.get("pai", 0),
        }
    except Exception as e:
        log.error(f"Erro zepp_sync: {e}")
        return None


def init_db(path=None):
    path = path or DB_PATH
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE IF NOT EXISTS amazfit_dados (
        data_hora TEXT, passos INTEGER DEFAULT 0,
        calorias_gastas INTEGER DEFAULT 0, distancia_km REAL DEFAULT 0,
        sono_total_min INTEGER DEFAULT 0, sono_profundo_min INTEGER DEFAULT 0,
        hrv_ms INTEGER DEFAULT 0, pai INTEGER DEFAULT 0)""")
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_az ON amazfit_dados(data_hora)")
    except Exception:
        pass
    conn.commit()
    conn.close()


def save(path_or_row, row=None):
    if row is None:
        row, path = path_or_row, DB_PATH
    else:
        path = path_or_row
    conn = sqlite3.connect(path)
    conn.execute("DELETE FROM amazfit_dados WHERE data_hora=?", (row["data_hora"],))
    conn.execute("""INSERT INTO amazfit_dados VALUES
        (:data_hora,:passos,:calorias_gastas,:distancia_km,
         :sono_total_min,:sono_profundo_min,:hrv_ms,:pai)""", row)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--date");  parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    init_db()
    days = ([args.date] if args.date else
            [(date.today()-timedelta(days=i)).strftime("%Y-%m-%d") for i in range(args.days)])
    for d in days:
        row = zepp_sync(d)
        if row:
            if args.debug: print(json.dumps(row, indent=2))
            save(row); log.info(f"Salvo: passos={row['passos']} sono={row['sono_total_min']}min")
        else:
            log.warning(f"Sem dados: {d}")
        time.sleep(0.5)
