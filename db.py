"""
db.py — Banco de dados
Supabase (PostgreSQL via pg8000) ou SQLite local.
"""
import os, re, sqlite3, threading
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
DB_PATH      = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "nutricao.db")).strip()
USE_PG       = bool(SUPABASE_URL)

if USE_PG:
    import pg8000.native
    from urllib.parse import urlparse

    _local = threading.local()

    def _get_pg():
        conn = getattr(_local, "conn", None)
        if conn is not None:
            try:
                conn.run("SELECT 1")
                return conn
            except Exception:
                _local.conn = None
        p = urlparse(SUPABASE_URL)
        _local.conn = pg8000.native.Connection(
            p.username, host=p.hostname, port=p.port or 5432,
            database=p.path.lstrip("/"), password=p.password,
            ssl_context=True, timeout=15
        )
        return _local.conn


def _pg_sql(sql):
    """Converte dialetos de data/hora do SQLite → PostgreSQL."""
    # 1. Mais longos/específicos PRIMEIRO para evitar quebrar a string
    sql = sql.replace("time(datetime(data_hora,'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo','HH24:MI:SS')")
    sql = sql.replace("time(datetime(data_hora, 'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo','HH24:MI:SS')")

    sql = sql.replace("strftime('%d/%m/%Y', datetime(data_hora,'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo','DD/MM/YYYY')")
    sql = sql.replace("strftime('%d/%m/%Y', datetime(data_hora, 'localtime'))", "TO_CHAR(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo','DD/MM/YYYY')")

    # 2. Intermediários
    sql = sql.replace("strftime('%d/%m/%Y',data)", "TO_CHAR(data,'DD/MM/YYYY')")
    sql = sql.replace("strftime('%d/%m/%Y', data)", "TO_CHAR(data,'DD/MM/YYYY')")

    # 3. Curtos POR ÚLTIMO
    sql = sql.replace("datetime(data_hora,'localtime')", "(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("datetime(data_hora, 'localtime')", "(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo')")

    sql = sql.replace("date(data_hora,'localtime')", "DATE(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo')")
    sql = sql.replace("date(data_hora, 'localtime')", "DATE(data_hora AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo')")

    sql = re.sub(r"date\('now',\s*'-(\d+)\s+days'\)", r"(CURRENT_DATE - INTERVAL '\1 days')", sql)
    return sql


def _pg_kwargs(sql_pg, params):
    """Converte ? → :p0, :p1... e retorna (sql_traduzido, kwargs)."""
    kwargs = {}
    if params:
        for i, val in enumerate(params):
            p_name = f"p{i}"
            sql_pg = sql_pg.replace("?", f":{p_name}", 1)
            kwargs[p_name] = val
    return sql_pg, kwargs


def query(sql, params=None):
    """SELECT → DataFrame."""
    if USE_PG:
        conn = _get_pg()
        sql_pg, kwargs = _pg_kwargs(_pg_sql(sql), params)
        try:
            rows = conn.run(sql_pg, **kwargs)
            cols = [c["name"] for c in conn.columns]
            return pd.DataFrame(rows, columns=cols)
        except Exception:
            _local.conn = None
            raise
    conn = sqlite3.connect(DB_PATH)
    df   = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def execute(sql, params=None):
    """INSERT/UPDATE/DELETE."""
    if USE_PG:
        conn = _get_pg()
        sql_pg, kwargs = _pg_kwargs(_pg_sql(sql), params)
        try:
            conn.run(sql_pg, **kwargs)
        except Exception:
            _local.conn = None
            raise
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute(sql, params or [])
    conn.commit()
    conn.close()


def executemany(sql, rows):
    """INSERT em lote — usa uma única conexão para todas as linhas."""
    if USE_PG:
        conn = _get_pg()
        try:
            for row in rows:
                sql_pg, kwargs = _pg_kwargs(_pg_sql(sql), list(row))
                conn.run(sql_pg, **kwargs)
        except Exception:
            _local.conn = None
            raise
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(sql, rows)
    conn.commit()
    conn.close()


_TABLES_PG = [
    """CREATE TABLE IF NOT EXISTS refeicoes (
        id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        categoria TEXT, descricao TEXT, calorias REAL DEFAULT 0,
        proteinas REAL DEFAULT 0, carboidratos REAL DEFAULT 0, gorduras REAL DEFAULT 0,
        componentes_json TEXT)""",
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
        hrv_ms INTEGER DEFAULT 0, pai INTEGER DEFAULT 0,
        corrida_km REAL DEFAULT 0, corrida_cal INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS hevy_treinos (
        id TEXT PRIMARY KEY, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        titulo TEXT, descricao TEXT, exercicios_json TEXT,
        duracao_min INTEGER, volume_kg REAL)""",
    """CREATE TABLE IF NOT EXISTS ia_analises_clinicas (
        id SERIAL PRIMARY KEY, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        analise_txt TEXT NOT NULL, n_dias INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS alimentos_favoritos (
        id SERIAL PRIMARY KEY,
        descricao TEXT NOT NULL,
        categoria TEXT DEFAULT 'Lanche',
        calorias REAL DEFAULT 0,
        proteinas REAL DEFAULT 0,
        carboidratos REAL DEFAULT 0,
        gorduras REAL DEFAULT 0,
        componentes_json TEXT,
        favorito INTEGER DEFAULT 0,
        vezes_usado INTEGER DEFAULT 1,
        qtd_referencia REAL DEFAULT 100,
        unidade_referencia TEXT DEFAULT 'g',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(descricao))""",
    "CREATE INDEX IF NOT EXISTS idx_refeicoes_data ON refeicoes(data_hora)",
    "CREATE INDEX IF NOT EXISTS idx_agua_data ON agua(data_hora)",
    "CREATE INDEX IF NOT EXISTS idx_medicacao_data ON medicacao(data_hora)",
    "CREATE INDEX IF NOT EXISTS idx_ia_analises_data ON ia_analises_clinicas(data_hora)",
]

_TABLES_SQLITE = [
    """CREATE TABLE IF NOT EXISTS refeicoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
        categoria TEXT, descricao TEXT, calorias REAL DEFAULT 0,
        proteinas REAL DEFAULT 0, carboidratos REAL DEFAULT 0, gorduras REAL DEFAULT 0,
        componentes_json TEXT)""",
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
        hrv_ms INTEGER DEFAULT 0, pai INTEGER DEFAULT 0,
        corrida_km REAL DEFAULT 0, corrida_cal INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS hevy_treinos (
        id TEXT PRIMARY KEY, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
        titulo TEXT, descricao TEXT, exercicios_json TEXT,
        duracao_min INTEGER, volume_kg REAL)""",
    """CREATE TABLE IF NOT EXISTS ia_analises_clinicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
        analise_txt TEXT NOT NULL, n_dias INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS alimentos_favoritos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        categoria TEXT DEFAULT 'Lanche',
        calorias REAL DEFAULT 0,
        proteinas REAL DEFAULT 0,
        carboidratos REAL DEFAULT 0,
        gorduras REAL DEFAULT 0,
        componentes_json TEXT,
        favorito INTEGER DEFAULT 0,
        vezes_usado INTEGER DEFAULT 1,
        qtd_referencia REAL DEFAULT 100,
        unidade_referencia TEXT DEFAULT 'g',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(descricao))""",
    "CREATE INDEX IF NOT EXISTS idx_refeicoes_data ON refeicoes(data_hora)",
    "CREATE INDEX IF NOT EXISTS idx_agua_data ON agua(data_hora)",
    "CREATE INDEX IF NOT EXISTS idx_medicacao_data ON medicacao(data_hora)",
    "CREATE INDEX IF NOT EXISTS idx_ia_analises_data_sq ON ia_analises_clinicas(data_hora)",
]


def init_tables():
    if USE_PG:
        conn = _get_pg()
        for sql in _TABLES_PG:
            conn.run(sql)
        try:
            # Check and migrate Supabase column components_json
            cols = conn.run("SELECT column_name FROM information_schema.columns WHERE table_name='refeicoes' AND column_name='componentes_json'")
            if not cols:
                conn.run("ALTER TABLE refeicoes ADD COLUMN componentes_json TEXT")
                print("✅ Supabase: Coluna 'componentes_json' adicionada à tabela 'refeicoes'.")

            # Check and migrate Supabase columns corrida_km and corrida_cal
            cols_corrida = conn.run("SELECT column_name FROM information_schema.columns WHERE table_name='amazfit_dados' AND column_name='corrida_km'")
            if not cols_corrida:
                conn.run("ALTER TABLE amazfit_dados ADD COLUMN corrida_km REAL DEFAULT 0")
                conn.run("ALTER TABLE amazfit_dados ADD COLUMN corrida_cal INTEGER DEFAULT 0")
                print("✅ Supabase: Colunas 'corrida_km' e 'corrida_cal' adicionadas à tabela 'amazfit_dados'.")

            # Check and migrate qtd_referencia / unidade_referencia em alimentos_favoritos
            conn.run("ALTER TABLE alimentos_favoritos ADD COLUMN IF NOT EXISTS qtd_referencia REAL DEFAULT 100")
            conn.run("ALTER TABLE alimentos_favoritos ADD COLUMN IF NOT EXISTS unidade_referencia TEXT DEFAULT 'g'")
        except Exception as e:
            print(f"⚠️ Erro ao verificar/adicionar colunas no Supabase: {e}")
    else:
        conn = sqlite3.connect(DB_PATH)
        for sql in _TABLES_SQLITE:
            conn.execute(sql)
        conn.commit()
        try:
            # Check and migrate SQLite column components_json
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(refeicoes)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'componentes_json' not in columns:
                conn.execute("ALTER TABLE refeicoes ADD COLUMN componentes_json TEXT")
                conn.commit()
                print("✅ SQLite: Coluna 'componentes_json' adicionada à tabela 'refeicoes'.")
            
            # Check and migrate SQLite columns corrida_km and corrida_cal
            cursor.execute("PRAGMA table_info(amazfit_dados)")
            columns_az = [info[1] for info in cursor.fetchall()]
            if 'corrida_km' not in columns_az:
                conn.execute("ALTER TABLE amazfit_dados ADD COLUMN corrida_km REAL DEFAULT 0")
                conn.execute("ALTER TABLE amazfit_dados ADD COLUMN corrida_cal INTEGER DEFAULT 0")
                conn.commit()
                print("✅ SQLite: Colunas 'corrida_km' e 'corrida_cal' adicionadas à tabela 'amazfit_dados'.")

            # Check and migrate qtd_referencia / unidade_referencia em alimentos_favoritos
            cursor.execute("PRAGMA table_info(alimentos_favoritos)")
            columns_af = [info[1] for info in cursor.fetchall()]
            if 'qtd_referencia' not in columns_af:
                conn.execute("ALTER TABLE alimentos_favoritos ADD COLUMN qtd_referencia REAL DEFAULT 100")
                conn.execute("ALTER TABLE alimentos_favoritos ADD COLUMN unidade_referencia TEXT DEFAULT 'g'")
                conn.commit()
                print("✅ SQLite: Colunas 'qtd_referencia' e 'unidade_referencia' adicionadas à tabela 'alimentos_favoritos'.")
        except Exception as e:
            print(f"⚠️ Erro ao verificar/adicionar colunas no SQLite: {e}")
        finally:
            conn.close()


def backend():
    if USE_PG:
        h = SUPABASE_URL.split("@")[-1].split("/")[0] if "@" in SUPABASE_URL else "pg"
        return f"Supabase ({h})"
    return f"SQLite ({DB_PATH})"
