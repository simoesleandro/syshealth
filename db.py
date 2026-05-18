"""
db.py — Banco de dados
Supabase (PostgreSQL via pg8000) ou SQLite local.
"""
import os, re, sqlite3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
DB_PATH      = os.getenv("DB_PATH", "nutricao.db").strip()
USE_PG       = bool(SUPABASE_URL)

if USE_PG:
    import pg8000.native
    from urllib.parse import urlparse

    def _get_pg():
        p = urlparse(SUPABASE_URL)
        return pg8000.native.Connection(
            p.username, host=p.hostname, port=p.port or 5432,
            database=p.path.lstrip("/"), password=p.password,
            ssl_context=True, timeout=15
        )


def _pg_sql(sql):
    """Converte SQL SQLite → PostgreSQL e ? → $1,$2..."""
    sql = sql.replace("date(data_hora,'localtime')", "DATE(data_hora AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("date(data_hora, 'localtime')", "DATE(data_hora AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("datetime(data_hora,'localtime')", "(data_hora AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("datetime(data_hora, 'localtime')", "(data_hora AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("time(datetime(data_hora,'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo','HH24:MI:SS')")
    sql = sql.replace("time(datetime(data_hora, 'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo','HH24:MI:SS')")
    sql = sql.replace("strftime('%d/%m/%Y',data)", "TO_CHAR(data,'DD/MM/YYYY')")
    sql = sql.replace("strftime('%d/%m/%Y', data)", "TO_CHAR(data,'DD/MM/YYYY')")
    sql = sql.replace("strftime('%d/%m/%Y', datetime(data_hora,'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo','DD/MM/YYYY')")
    sql = sql.replace("strftime('%d/%m/%Y', datetime(data_hora, 'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo','DD/MM/YYYY')")
    sql = re.sub(r"date\('now',\s*'-(\d+)\s+days'\)", r"(CURRENT_DATE - INTERVAL '\1 days')", sql)
    sql = sql.replace("COALESCE(categoria, 'Lanche')", "COALESCE(categoria, 'Lanche')")
    # Converte ? para $1, $2, $3...
    counter = [0]
    def to_dollar(m):
        counter[0] += 1
        return f"${counter[0]}"
    sql = re.sub(r'\?', to_dollar, sql)
    return sql


def query(sql, params=None):
    """SELECT → DataFrame."""
    if USE_PG:
        conn   = _get_pg()
        sql_pg = _pg_sql(sql)
        try:
            if params:
                rows = conn.run(sql_pg, *params)
            else:
                rows = conn.run(sql_pg)
            cols = [c["name"] for c in conn.columns]
            return pd.DataFrame(rows, columns=cols)
        finally:
            conn.close()
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def execute(sql, params=None):
    """INSERT/UPDATE/DELETE."""
    if USE_PG:
        conn   = _get_pg()
        sql_pg = _pg_sql(sql)
        try:
            if params:
                conn.run(sql_pg, *params)
            else:
                conn.run(sql_pg)
        finally:
            conn.close()
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute(sql, params or [])
    conn.commit()
    conn.close()


def executemany(sql, rows):
    """INSERT em lote."""
    for row in rows:
        execute(sql, list(row))


def init_tables():
    if USE_PG:
        conn = _get_pg()
        try:
            for sql in [
                """CREATE TABLE IF NOT EXISTS refeicoes (
                    id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    categoria TEXT, descricao TEXT, calorias REAL DEFAULT 0,
                    proteinas REAL DEFAULT 0, carboidratos REAL DEFAULT 0, gorduras REAL DEFAULT 0)""",
                """CREATE TABLE IF NOT EXISTS agua (
                    id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    quantidade_ml INTEGER DEFAULT 0)""",
                """CREATE TABLE IF NOT EXISTS medidas (
                    id SERIAL PRIMARY KEY, data DATE DEFAULT CURRENT_DATE,
                    peso REAL, cintura REAL, abdomen REAL, peitoral REAL, quadril REAL,
                    coxa_dir REAL, coxa_esq REAL, panturrilha_dir REAL,
                    panturrilha_esq REAL, biceps_dir REAL, biceps_esq REAL)""",
                """CREATE TABLE IF NOT EXISTS medicacao (
                    id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    dose_mg REAL)""",
                """CREATE TABLE IF NOT EXISTS amazfit_dados (
                    data_hora TEXT PRIMARY KEY, passos INTEGER DEFAULT 0,
                    calorias_gastas INTEGER DEFAULT 0, distancia_km REAL DEFAULT 0,
                    sono_total_min INTEGER DEFAULT 0, sono_profundo_min INTEGER DEFAULT 0,
                    hrv_ms INTEGER DEFAULT 0, pai INTEGER DEFAULT 0)""",
            ]:
                conn.run(sql)
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        for sql in [
            """CREATE TABLE IF NOT EXISTS refeicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                categoria TEXT, descricao TEXT, calorias REAL DEFAULT 0,
                proteinas REAL DEFAULT 0, carboidratos REAL DEFAULT 0, gorduras REAL DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS agua (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                quantidade_ml INTEGER DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS medidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data DATE DEFAULT CURRENT_DATE,
                peso REAL, cintura REAL, abdomen REAL, peitoral REAL, quadril REAL,
                coxa_dir REAL, coxa_esq REAL, panturrilha_dir REAL,
                panturrilha_esq REAL, biceps_dir REAL, biceps_esq REAL)""",
            """CREATE TABLE IF NOT EXISTS medicacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                dose_mg REAL)""",
            """CREATE TABLE IF NOT EXISTS amazfit_dados (
                data_hora TEXT PRIMARY KEY, passos INTEGER DEFAULT 0,
                calorias_gastas INTEGER DEFAULT 0, distancia_km REAL DEFAULT 0,
                sono_total_min INTEGER DEFAULT 0, sono_profundo_min INTEGER DEFAULT 0,
                hrv_ms INTEGER DEFAULT 0, pai INTEGER DEFAULT 0)""",
        ]:
            conn.execute(sql)
        conn.commit()
        conn.close()


def backend():
    if USE_PG:
        h = SUPABASE_URL.split("@")[-1].split("/")[0] if "@" in SUPABASE_URL else "pg"
        return f"Supabase ({h})"
    return f"SQLite ({DB_PATH})"
