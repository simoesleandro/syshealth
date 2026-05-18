"""
db.py — Banco de dados
Usa Supabase (PostgreSQL via pg8000) ou SQLite local.
"""
import os, sqlite3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL","").strip()
DB_PATH      = os.getenv("DB_PATH","nutricao.db").strip()
USE_PG       = bool(SUPABASE_URL)

if USE_PG:
    import pg8000.native
    from urllib.parse import urlparse

    def _parse_url(url):
        p = urlparse(url)
        return {
            "host":     p.hostname,
            "port":     p.port or 5432,
            "database": p.path.lstrip("/"),
            "user":     p.username,
            "password": p.password,
        }

    def _get_pg():
        c = _parse_url(SUPABASE_URL)
        return pg8000.native.Connection(
            c["user"], host=c["host"], port=c["port"],
            database=c["database"], password=c["password"],
            ssl_context=True, timeout=15
        )


def _adapt_sql(sql):
    """Converte SQL SQLite para PostgreSQL."""
    sql = sql.replace("?", "%s")
    sql = sql.replace("date(data_hora,'localtime')",
                      "DATE(data_hora AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("date(data_hora, 'localtime')",
                      "DATE(data_hora AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("datetime(data_hora,'localtime')",
                      "(data_hora AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("datetime(data_hora, 'localtime')",
                      "(data_hora AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("time(datetime(data_hora,'localtime'))",
                      "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo','HH24:MI:SS')")
    sql = sql.replace("time(datetime(data_hora, 'localtime'))",
                      "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo','HH24:MI:SS')")
    sql = sql.replace("strftime('%d/%m/%Y',data)",
                      "TO_CHAR(data,'DD/MM/YYYY')")
    sql = sql.replace("strftime('%d/%m/%Y', data)",
                      "TO_CHAR(data,'DD/MM/YYYY')")
    sql = sql.replace("strftime('%d/%m/%Y', datetime(data_hora,'localtime'))",
                      "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo','DD/MM/YYYY')")
    sql = sql.replace("strftime('%d/%m/%Y', datetime(data_hora, 'localtime'))",
                      "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo','DD/MM/YYYY')")
    # date('now', '-N days') → CURRENT_DATE - INTERVAL 'N days'
    import re
    sql = re.sub(r"date\('now',\s*'-(\d+)\s+days'\)",
                 r"(CURRENT_DATE - INTERVAL '\1 days')", sql)
    return sql


def query(sql, params=None):
    """SELECT → DataFrame."""
    if USE_PG:
        conn = _get_pg()
        sql_pg = _adapt_sql(sql)
        # pg8000 usa $1,$2 em vez de %s
        import re
        i = [0]
        def repl(m):
            i[0] += 1
            return f"${i[0]}"
        sql_pg = re.sub(r'%s', repl, sql_pg)
        rows = conn.run(sql_pg, *(params or []))
        cols = [c["name"] for c in conn.columns]
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def execute(sql, params=None):
    """INSERT/UPDATE/DELETE."""
    if USE_PG:
        conn = _get_pg()
        sql_pg = _adapt_sql(sql)
        import re
        i = [0]
        def repl(m):
            i[0] += 1
            return f"${i[0]}"
        sql_pg = re.sub(r'%s', repl, sql_pg)
        conn.run(sql_pg, *(params or []))
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
