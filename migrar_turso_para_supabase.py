"""
migrar_turso_para_supabase.py
Migra dados do Turso diretamente para o Supabase.
"""
import os, sys, requests
from dotenv import load_dotenv
load_dotenv()

TURSO_URL   = os.getenv("TURSO_URL","").strip()
TURSO_TOKEN = os.getenv("TURSO_TOKEN","").strip()
SUPABASE_URL= os.getenv("SUPABASE_URL","").strip()

if not all([TURSO_URL, TURSO_TOKEN, SUPABASE_URL]):
    print("ERRO: Configure TURSO_URL, TURSO_TOKEN e SUPABASE_URL no .env")
    sys.exit(1)

import psycopg2

TURSO_HTTP = TURSO_URL.replace("libsql://","https://") + "/v2/pipeline"
HEADERS    = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}

def turso_query(sql):
    r = requests.post(TURSO_HTTP, headers=HEADERS,
        json={"requests":[{"type":"execute","stmt":{"sql":sql}},{"type":"close"}]}, timeout=15)
    data = r.json()
    results = data.get("results",[]) if isinstance(data,dict) else data
    for res in results:
        if not isinstance(res,dict): continue
        if res.get("type")=="ok":
            result = res.get("response",{}).get("result",{})
            cols   = [c["name"] for c in result.get("cols",[])]
            rows   = []
            for row in result.get("rows",[]):
                if isinstance(row, list):
                    rows.append([v.get("value") if isinstance(v,dict) else v for v in row])
                elif isinstance(row, dict):
                    rows.append([v.get("value") if isinstance(v,dict) else v
                                 for v in row.get("values",[])])
            return cols, rows
    return [], []

print("="*50)
print("  Turso → Supabase")
print("="*50)

pg  = psycopg2.connect(SUPABASE_URL, connect_timeout=15)
cur = pg.cursor()
print("Supabase OK!")

# Cria tabelas no Supabase
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
    cur.execute(sql)
pg.commit()
print("Tabelas OK!\n")

# Migra cada tabela
tabelas = [
    ("refeicoes",     "id,data_hora,categoria,descricao,calorias,proteinas,carboidratos,gorduras"),
    ("agua",          "id,data_hora,quantidade_ml"),
    ("medidas",       "id,data,peso,cintura,abdomen,peitoral,quadril,coxa_dir,coxa_esq,panturrilha_dir,panturrilha_esq,biceps_dir,biceps_esq"),
    ("medicacao",     "id,data_hora,dose_mg"),
    ("amazfit_dados", "data_hora,passos,calorias_gastas,distancia_km,sono_total_min,sono_profundo_min,hrv_ms,pai"),
]

for tabela, colunas in tabelas:
    cols, rows = turso_query(f"SELECT {colunas} FROM {tabela}")
    if not rows:
        print(f"  {tabela}: vazia")
        continue
    ph  = ",".join(["%s"]*len(colunas.split(",")))
    sql = f"INSERT INTO {tabela} ({colunas}) VALUES ({ph}) ON CONFLICT DO NOTHING"
    cur.executemany(sql, rows)
    pg.commit()
    print(f"  {tabela}: {len(rows)} registros OK")

# Reseta sequences
for t in ["refeicoes","agua","medidas","medicacao"]:
    cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}','id'), COALESCE((SELECT MAX(id) FROM {t}),1))")
pg.commit()
pg.close()

print("\n" + "="*50)
print("  Migracao concluida!")
print("  Verifique em supabase.com -> Table Editor")
print("="*50)
