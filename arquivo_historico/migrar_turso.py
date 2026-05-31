"""
migrar_turso.py — Migra nutricao.db para o Turso via HTTP API
"""
import sqlite3, os, sys, requests
from dotenv import load_dotenv

load_dotenv()

TURSO_URL   = os.getenv("TURSO_URL", "").strip()
TURSO_TOKEN = os.getenv("TURSO_TOKEN", "").strip()

if not TURSO_URL or not TURSO_TOKEN:
    print("ERRO: Configure TURSO_URL e TURSO_TOKEN no .env")
    sys.exit(1)

HTTP_URL = TURSO_URL.replace("libsql://", "https://") + "/v2/pipeline"
HEADERS  = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}


def run(statements):
    payload = {"requests": [
        {"type": "execute", "stmt": {"sql": s, "args": a}} for s, a in statements
    ] + [{"type": "close"}]}
    r = requests.post(HTTP_URL, headers=HEADERS, json=payload, timeout=30)
    if r.status_code != 200:
        print(f"  ERRO HTTP {r.status_code}: {r.text[:300]}")
        return False
    for res in r.json().get("results", []):
        if res.get("type") == "error":
            print(f"  ERRO SQL: {res.get('error', {}).get('message', '')}")
            return False
    return True


def run1(sql, args=None):
    return run([(sql, args or [])])


def tv(v):
    """Converte valor Python para tipo Turso correto."""
    if v is None:
        return {"type": "null"}
    # Tenta converter string numérica para número
    if isinstance(v, str):
        try:
            iv = int(v)
            return {"type": "integer", "value": str(iv)}
        except ValueError:
            pass
        try:
            fv = float(v)
            return {"type": "float", "value": fv}   # float como número, não string
        except ValueError:
            pass
        return {"type": "text", "value": v}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}         # float como número nativo
    return {"type": "text", "value": str(v)}


def inserir(tabela, colunas, rows, lote=50):
    cols = ", ".join(colunas)
    ph   = ", ".join(["?" for _ in colunas])
    sql  = f"INSERT OR IGNORE INTO {tabela} ({cols}) VALUES ({ph})"
    total = 0
    for i in range(0, len(rows), lote):
        batch = rows[i:i+lote]
        if run([(sql, [tv(v) for v in row]) for row in batch]):
            total += len(batch)
        else:
            # Tenta linha a linha para identificar o problema
            for row in batch:
                if run([(sql, [tv(v) for v in row])]):
                    total += 1
    return total


print("="*50)
print("  MIGRACAO nutricao.db -> Turso")
print("="*50)
print(f"Destino: {TURSO_URL}")

r = requests.post(HTTP_URL, headers=HEADERS,
    json={"requests":[{"type":"execute","stmt":{"sql":"SELECT 1"}},{"type":"close"}]}, timeout=10)
if r.status_code != 200:
    print(f"ERRO de conexao: {r.status_code}")
    sys.exit(1)
print("Conexao OK!\n")

print("Criando tabelas...")
for sql in [
    """CREATE TABLE IF NOT EXISTS refeicoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
        categoria TEXT, descricao TEXT, calorias REAL DEFAULT 0, proteinas REAL DEFAULT 0,
        carboidratos REAL DEFAULT 0, gorduras REAL DEFAULT 0)""",
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
    nome = sql.split("EXISTS")[1].split("(")[0].strip()
    print(f"  {nome} {'OK' if run1(sql) else 'ERRO'}")

print("\nMigrando dados...")
local = sqlite3.connect("nutricao.db")

for tabela, colunas in [
    ("refeicoes",     ["id","data_hora","categoria","descricao","calorias","proteinas","carboidratos","gorduras"]),
    ("agua",          ["id","data_hora","quantidade_ml"]),
    ("medidas",       ["id","data","peso","cintura","abdomen","peitoral","quadril",
                       "coxa_dir","coxa_esq","panturrilha_dir","panturrilha_esq","biceps_dir","biceps_esq"]),
    ("medicacao",     ["id","data_hora","dose_mg"]),
    ("amazfit_dados", ["data_hora","passos","calorias_gastas","distancia_km",
                       "sono_total_min","sono_profundo_min","hrv_ms","pai"]),
]:
    try:
        rows = local.execute(f"SELECT {', '.join(colunas)} FROM {tabela}").fetchall()
        if not rows:
            print(f"  {tabela}: vazia")
            continue
        n = inserir(tabela, colunas, rows)
        status = "OK" if n == len(rows) else f"PARCIAL ({n}/{len(rows)})"
        print(f"  {tabela}: {n} registros {status}")
    except Exception as e:
        print(f"  {tabela}: ERRO — {e}")

local.close()
print("\n" + "="*50)
print("  Migracao concluida!")
print("  Verifique em turso.tech -> Edit Data")
print("="*50)