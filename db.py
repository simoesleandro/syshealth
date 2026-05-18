"""
db.py — Camada de banco de dados
Usa Turso (nuvem) se TURSO_URL estiver configurado, senão SQLite local.
"""
import os
import sqlite3
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

TURSO_URL   = os.getenv("TURSO_URL", "").strip()
TURSO_TOKEN = os.getenv("TURSO_TOKEN", "").strip()
DB_PATH     = os.getenv("DB_PATH", "nutricao.db").strip()

USE_TURSO = bool(TURSO_URL and TURSO_TOKEN)

if USE_TURSO:
    HTTP_URL = TURSO_URL.replace("libsql://", "https://") + "/v2/pipeline"
    HEADERS  = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type":  "application/json",
    }


# ── Conversão de tipos ────────────────────────────────────────────────────────
def tv(v):
    """Python → Turso value."""
    if v is None:            return {"type": "null"}
    if isinstance(v, bool):  return {"type": "integer", "value": "1" if v else "0"}
    if isinstance(v, int):   return {"type": "integer", "value": str(v)}
    if isinstance(v, float): return {"type": "float",   "value": v}
    if isinstance(v, str):
        try:    return {"type": "integer", "value": str(int(v))}
        except: pass
        try:    return {"type": "float",   "value": float(v)}
        except: pass
        return {"type": "text", "value": v}
    return {"type": "text", "value": str(v)}


def from_turso_value(v):
    """Turso value → Python."""
    if v is None: return None
    if not isinstance(v, dict): return v
    t = v.get("type")
    val = v.get("value")
    if t == "null":    return None
    if t == "integer": return int(val) if val is not None else 0
    if t == "float":   return float(val) if val is not None else 0.0
    return val


# ── Execução Turso ────────────────────────────────────────────────────────────
def _turso_run(statements):
    """Executa lista de (sql, args) no Turso. Retorna lista de resultados."""
    payload = {"requests": [
        {"type": "execute", "stmt": {
            "sql": sql,
            "args": [tv(a) for a in (args or [])]
        }}
        for sql, args in statements
    ] + [{"type": "close"}]}

    r = requests.post(HTTP_URL, headers=HEADERS, json=payload, timeout=15)
    if r.status_code != 200:
        raise Exception(f"Turso HTTP {r.status_code}: {r.text[:200]}")

    body = r.json()
    # Turso pode retornar dict com "results" ou lista direta
    if isinstance(body, list):
        results = body
    else:
        results = body.get("results", [])

    output = []
    for res in results:
        if not isinstance(res, dict):
            continue
        if res.get("type") == "error":
            raise Exception(f"Turso SQL: {res.get('error', {}).get('message')}")
        if res.get("type") == "ok":
            output.append(res.get("response", {}).get("result", {}))
    return output


def _turso_query(sql, args=None):
    """Executa SELECT e retorna DataFrame."""
    results = _turso_run([(sql, args or [])])
    if not results:
        return pd.DataFrame()

    result = results[0]
    if not isinstance(result, dict):
        return pd.DataFrame()

    cols = [c["name"] for c in result.get("cols", [])]
    raw_rows = result.get("rows", [])
    parsed = []
    for row in raw_rows:
        if isinstance(row, dict):
            # formato {"values": [...]}
            parsed.append([from_turso_value(v) for v in row.get("values", [])])
        elif isinstance(row, list):
            # formato direto [val1, val2, ...]
            parsed.append([from_turso_value(v) for v in row])
        else:
            parsed.append([])
    return pd.DataFrame(parsed, columns=cols) if cols else pd.DataFrame()


def _turso_execute(sql, args=None):
    """Executa INSERT/UPDATE/DELETE no Turso."""
    _turso_run([(sql, args or [])])


# ── API pública ───────────────────────────────────────────────────────────────
def query(sql, params=None):
    """Executa SELECT e retorna DataFrame. Funciona com Turso e SQLite."""
    if USE_TURSO:
        return _turso_query(sql, params)
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def execute(sql, params=None):
    """Executa INSERT/UPDATE/DELETE. Funciona com Turso e SQLite."""
    if USE_TURSO:
        _turso_execute(sql, list(params) if params else None)
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute(sql, params or [])
    conn.commit()
    conn.close()


def executemany(sql, rows):
    """Executa INSERT em lote."""
    if USE_TURSO:
        statements = [(sql, list(row)) for row in rows]
        _turso_run(statements)
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


def init_tables():
    """Cria todas as tabelas se não existirem."""
    sqls = [
        """CREATE TABLE IF NOT EXISTS refeicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            categoria TEXT, descricao TEXT,
            calorias REAL DEFAULT 0, proteinas REAL DEFAULT 0,
            carboidratos REAL DEFAULT 0, gorduras REAL DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS agua (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            quantidade_ml INTEGER DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS medidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE DEFAULT CURRENT_DATE,
            peso REAL, cintura REAL, abdomen REAL, peitoral REAL, quadril REAL,
            coxa_dir REAL, coxa_esq REAL, panturrilha_dir REAL,
            panturrilha_esq REAL, biceps_dir REAL, biceps_esq REAL)""",
        """CREATE TABLE IF NOT EXISTS medicacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            dose_mg REAL)""",
        """CREATE TABLE IF NOT EXISTS amazfit_dados (
            data_hora TEXT PRIMARY KEY,
            passos INTEGER DEFAULT 0, calorias_gastas INTEGER DEFAULT 0,
            distancia_km REAL DEFAULT 0, sono_total_min INTEGER DEFAULT 0,
            sono_profundo_min INTEGER DEFAULT 0, hrv_ms INTEGER DEFAULT 0,
            pai INTEGER DEFAULT 0)""",
    ]
    if USE_TURSO:
        _turso_run([(sql, []) for sql in sqls])
    else:
        conn = sqlite3.connect(DB_PATH)
        for sql in sqls:
            conn.execute(sql)
        conn.commit()
        conn.close()


def backend():
    return "Turso" if USE_TURSO else f"SQLite ({DB_PATH})"