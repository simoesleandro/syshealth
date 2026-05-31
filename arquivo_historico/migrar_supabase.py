"""
migrar_supabase.py — Migra nutricao.db local para o Supabase
Execute uma vez: python migrar_supabase.py
"""
import sqlite3, os, sys
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
if not SUPABASE_URL:
    print("ERRO: Configure SUPABASE_URL no .env")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    os.system("pip install psycopg2-binary")
    import psycopg2

print("="*50)
print("  MIGRACAO nutricao.db -> Supabase")
print("="*50)

pg   = psycopg2.connect(SUPABASE_URL, connect_timeout=15)
cur  = pg.cursor()
print("Conexao OK!\n")

# Cria tabelas
print("Criando tabelas...")
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
    nome = sql.split("EXISTS")[1].split("(")[0].strip()
    cur.execute(sql)
    print(f"  {nome} OK")
pg.commit()

# Migra dados
print("\nMigrando dados...")
local = sqlite3.connect("nutricao.db")

tabelas = [
    ("refeicoes",     "id,data_hora,categoria,descricao,calorias,proteinas,carboidratos,gorduras"),
    ("agua",          "id,data_hora,quantidade_ml"),
    ("medidas",       "id,data,peso,cintura,abdomen,peitoral,quadril,coxa_dir,coxa_esq,panturrilha_dir,panturrilha_esq,biceps_dir,biceps_esq"),
    ("medicacao",     "id,data_hora,dose_mg"),
    ("amazfit_dados", "data_hora,passos,calorias_gastas,distancia_km,sono_total_min,sono_profundo_min,hrv_ms,pai"),
]

for tabela, colunas in tabelas:
    cols  = colunas.split(",")
    rows  = local.execute(f"SELECT {colunas} FROM {tabela}").fetchall()
    if not rows:
        print(f"  {tabela}: vazia")
        continue
    ph  = ",".join(["%s"] * len(cols))
    sql = f"INSERT INTO {tabela} ({colunas}) VALUES ({ph}) ON CONFLICT DO NOTHING"
    cur.executemany(sql, rows)
    pg.commit()
    print(f"  {tabela}: {len(rows)} registros OK")

# Reseta sequences dos IDs
for tabela in ["refeicoes","agua","medidas","medicacao"]:
    cur.execute(f"SELECT setval('{tabela}_id_seq', (SELECT MAX(id) FROM {tabela}))")
pg.commit()

local.close()
pg.close()
print("\n" + "="*50)
print("  Migracao concluida!")
print("  Verifique em supabase.com -> Table Editor")
print("="*50)
