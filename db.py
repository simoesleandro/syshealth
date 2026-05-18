"""
db.py — Camada de banco de dados
Usa Supabase (PostgreSQL) se SUPABASE_URL estiver configurado, senão SQLite local.
"""
import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
DB_PATH      = os.getenv("DB_PATH", "nutricao.db").strip()

USE_PG = bool(SUPABASE_URL)

if USE_PG:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        raise ImportError("psycopg2 nao instalado. Adicione psycopg2-binary ao requirements.txt")


def _get_pg():
    return psycopg2.connect(SUPABASE_URL, connect_timeout=15)


def query(sql, params=None):
    """Executa SELECT e retorna DataFrame."""
    if USE_PG:
        sql_pg = sql.replace("?", "%s")
        # Corrige date() do SQLite para PostgreSQL
        sql_pg = sql_pg.replace("date(data_hora,'localtime')", "DATE(data_hora AT TIME ZONE 'America/Sao_Paulo')")
        sql_pg = sql_pg.replace("date(data_hora, 'localtime')", "DATE(data_hora AT TIME ZONE 'America/Sao_Paulo')")
        sql_pg = sql_pg.replace("datetime(data_hora,'localtime')", "(data_hora AT TIME ZONE 'America/Sao_Paulo')")
        sql_pg = sql_pg.replace("datetime(data_hora, 'localtime')", "(data_hora AT TIME ZONE 'America/Sao_Paulo')")
        sql_pg = sql_pg.replace("time(datetime(data_hora,'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo', 'HH24:MI:SS')")
        sql_pg = sql_pg.replace("time(datetime(data_hora, 'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo', 'HH24:MI:SS')")
        sql_pg = sql_pg.replace("strftime('%d/%m/%Y',data)", "TO_CHAR(data, 'DD/MM/YYYY')")
        sql_pg = sql_pg.replace("strftime('%d/%m/%Y', data)", "TO_CHAR(data, 'DD/MM/YYYY')")
        sql_pg = sql_pg.replace("strftime('%d/%m/%Y', datetime(data_hora,'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo', 'DD/MM/YYYY')")
        sql_pg = sql_pg.replace("strftime('%d/%m/%Y', datetime(data_hora, 'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'America/Sao_Paulo', 'DD/MM/YYYY')")
        sql_pg = sql_pg.replace("date('now', '-", "CURRENT_DATE - INTERVAL '")
        sql_pg = sql_pg.replace("days')", "days'")
        conn = _get_pg()
        df   = pd.read_sql_query(sql_pg, conn, params=params)
        conn.close()
        return df
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def execute(sql, params=None):
    """Executa INSERT/UPDATE/DELETE."""
    if USE_PG:
        sql_pg = sql.replace("?", "%s")
        conn   = _get_pg()
        cur    = conn.cursor()
        cur.execute(sql_pg, params or [])
        conn.commit()
        conn.close()
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute(sql, params or [])
    conn.commit()
    conn.close()


def executemany(sql, rows):
    """Executa INSERT em lote."""
    if USE_PG:
        sql_pg = sql.replace("?", "%s")
        conn   = _get_pg()
        cur    = conn.cursor()
        cur.executemany(sql_pg, rows)
        conn.commit()
        conn.close()
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


def init_tables():
    """Cria todas as tabelas se nao existirem."""
    if USE_PG:
        sqls = [
            """CREATE TABLE IF NOT EXISTS refeicoes (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                categoria TEXT, descricao TEXT,
                calorias REAL DEFAULT 0, proteinas REAL DEFAULT 0,
                carboidratos REAL DEFAULT 0, gorduras REAL DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS agua (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                quantidade_ml INTEGER DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS medidas (
                id SERIAL PRIMARY KEY,
                data DATE DEFAULT CURRENT_DATE,
                peso REAL, cintura REAL, abdomen REAL, peitoral REAL, quadril REAL,
                coxa_dir REAL, coxa_esq REAL, panturrilha_dir REAL,
                panturrilha_esq REAL, biceps_dir REAL, biceps_esq REAL)""",
            """CREATE TABLE IF NOT EXISTS medicacao (
                id SERIAL PRIMARY KEY,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                dose_mg REAL)""",
            """CREATE TABLE IF NOT EXISTS amazfit_dados (
                data_hora TEXT PRIMARY KEY,
                passos INTEGER DEFAULT 0, calorias_gastas INTEGER DEFAULT 0,
                distancia_km REAL DEFAULT 0, sono_total_min INTEGER DEFAULT 0,
                sono_profundo_min INTEGER DEFAULT 0, hrv_ms INTEGER DEFAULT 0,
                pai INTEGER DEFAULT 0)""",
        ]
        conn = _get_pg()
        cur  = conn.cursor()
        for sql in sqls:
            cur.execute(sql)
        conn.commit()
        conn.close()
    else:
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
        conn = sqlite3.connect(DB_PATH)
        for sql in sqls:
            conn.execute(sql)
        conn.commit()
        conn.close()


def backend():
    if USE_PG:
        host = SUPABASE_URL.split("@")[-1].split("/")[0] if "@" in SUPABASE_URL else "postgres"
        return f"Supabase PostgreSQL ({host})"
    return f"SQLite ({DB_PATH})"
