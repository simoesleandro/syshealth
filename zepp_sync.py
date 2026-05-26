"""
zepp_sync.py — versão nuvem
"""
import base64, json, logging, os, time
from datetime import date, timedelta
import requests
from dotenv import load_dotenv
import db as DB

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
        df = DB.query("SELECT hrv_ms, pai FROM amazfit_dados WHERE data_hora=?", [f"{day} 00:00:00"])
        if df.empty: return {}
        return df.iloc[0].to_dict()
    except Exception:
        return {}


def zepp_sync(day=None):
    token   = os.getenv("ZEPP_APP_TOKEN", "").strip()
    user_id = os.getenv("ZEPP_USER_ID", "").strip()
    if not token or not user_id:
        log.error("ZEPP_APP_TOKEN ou ZEPP_USER_ID não configurados")
        return None
    day = day or date.today().strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{BASE}/v1/data/band_data.json",
                         headers=make_headers(token),
                         params={"query_type": "summary", "device_type": "0",
                                 "object_id": user_id,
                                 "from_date": day, "to_date": day},
                         timeout=15)

        if r.status_code != 200:
            log.error(f"Zepp HTTP {r.status_code}: {r.text[:200]}")
            return None

        data  = r.json()
        code  = data.get("code", "?")
        msg   = data.get("message", "")
        items = data.get("data", [])

        if code not in (1, "1", 0, "0"):
            log.error(f"Zepp API code={code}: {msg} — resposta: {json.dumps(data)[:300]}")
            return None

        if not items:
            log.warning(f"Zepp sem dados para {day} (code={code}, msg={msg})")
            return None

        s    = decode_summary(items[0].get("summary", ""))
        stp  = s.get("stp", {}) or {}
        slp  = s.get("slp", {}) or {}
        deep = int(slp.get("dp", 0) or 0)
        lt   = int(slp.get("lt", 0) or 0)
        rem  = int(slp.get("dt", 0) or 0)
        tot  = deep + lt + rem or int(slp.get("ebt", 0) or 0)
        prev = _get_existing(day)
        
        run_dist_m = float(stp.get("runDist", 0) or 0)
        run_cal = int(stp.get("runCal", 0) or 0)
        
        return {
            "data_hora":         f"{day} 00:00:00",
            "passos":            int(stp.get("ttl", 0) or 0),
            "calorias_gastas":   int(stp.get("cal", 0) or 0),
            "distancia_km":      round(int(stp.get("dis", 0) or 0) / 1000, 2),
            "sono_total_min":    tot,
            "sono_profundo_min": deep,
            "hrv_ms":            prev.get("hrv_ms", 0),
            "pai":               prev.get("pai", 0),
            "corrida_km":        round(run_dist_m / 1000.0, 2),
            "corrida_cal":       run_cal,
        }
    except requests.Timeout:
        log.error(f"Zepp timeout para {day}")
        return None
    except Exception as e:
        log.error(f"Erro zepp_sync: {e}", exc_info=True)
        return None


def init_db(path=None):
    DB.init_tables()


def save(path_or_row, row=None):
    if row is None:
        row = path_or_row
    DB.execute("DELETE FROM amazfit_dados WHERE data_hora=?", [row["data_hora"]])
    DB.execute(
        "INSERT INTO amazfit_dados (data_hora, passos, calorias_gastas, distancia_km, sono_total_min, sono_profundo_min, hrv_ms, pai, corrida_km, corrida_cal) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [row["data_hora"], row["passos"], row["calorias_gastas"], row["distancia_km"],
         row["sono_total_min"], row["sono_profundo_min"], row["hrv_ms"], row["pai"],
         row.get("corrida_km", 0.0), row.get("corrida_cal", 0)]
    )


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
