import os
import re
import json
import sqlite3
import sys

# Caminhos dos arquivos
DUMP_FILE = r"C:\Users\Leand\.gemini\antigravity\brain\8766e350-647b-44d4-833c-389147a845de\.system_generated\steps\903\output.txt"
DB_PATH = r"C:\Users\Leand\OneDrive\Desktop\Projeto_Fit\nutricao.db"

# Força o encoding do console do Python para utf-8
if sys.platform.startswith("win"):
    import ctypes
    # Configura para CP_UTF8 (65001) para evitar UnicodeEncodeError ao imprimir emojis/caracteres utf-8
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)
sys.stdout.reconfigure(encoding='utf-8')

def extract_json_dump():
    print(f"Lendo dump do arquivo: {DUMP_FILE}")
    with open(DUMP_FILE, "r", encoding="utf-8") as f:
        outer_data = json.load(f)
    
    result_str = outer_data.get("result", "")
    if not result_str:
        raise ValueError("Chave 'result' não encontrada ou vazia no dump externo.")
    
    # Encontra o bloco JSON [ ... ]
    match = re.search(r"(\[.*\])", result_str, re.DOTALL)
    if not match:
        raise ValueError("Não foi possível encontrar a lista JSON contendo 'full_dump' no resultado.")
    
    json_str = match.group(1).strip()
    data_list = json.loads(json_str)
    if not data_list or not isinstance(data_list, list):
        raise ValueError("O conteúdo extraído não é uma lista JSON válida.")
    
    full_dump = data_list[0].get("full_dump")
    if not full_dump:
        raise ValueError("Chave 'full_dump' não encontrada no JSON extraído.")
    
    return full_dump

def init_sqlite_tables(conn):
    cursor = conn.cursor()
    # Garante que a tabela evacuacoes existe no SQLite
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evacuacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_hora DATETIME,
        observacao TEXT,
        criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
        esforco INTEGER DEFAULT 0
    )
    """)
    conn.commit()

def import_table_generic(conn, table_name, rows, columns):
    if not rows:
        print(f"  Tabela {table_name}: Nenhum dado para importar.")
        return 0
    
    cursor = conn.cursor()
    placeholders = ", ".join(["?"] * len(columns))
    cols_str = ", ".join(columns)
    sql = f"INSERT OR REPLACE INTO {table_name} ({cols_str}) VALUES ({placeholders})"
    
    imported_count = 0
    for row in rows:
        # Se components_json em refeicoes ou exercicios_json em hevy_treinos for dict/list, converte para string
        row_values = []
        for col in columns:
            val = row.get(col)
            if isinstance(val, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)
            row_values.append(val)
        
        cursor.execute(sql, row_values)
        imported_count += 1
    
    conn.commit()
    print(f"  Tabela {table_name}: {imported_count} registros importados com sucesso.")
    return imported_count

def merge_amazfit_dados(conn, rows):
    if not rows:
        print("  Tabela amazfit_dados: Nenhum dado para mesclar.")
        return 0
    
    cursor = conn.cursor()
    cursor.execute("SELECT data_hora, passos, calorias_gastas, distancia_km, sono_total_min, sono_profundo_min, hrv_ms, pai, corrida_km, corrida_cal FROM amazfit_dados")
    local_rows = {r[0]: {
        "passos": r[1], "calorias_gastas": r[2], "distancia_km": r[3],
        "sono_total_min": r[4], "sono_profundo_min": r[5],
        "hrv_ms": r[6], "pai": r[7], "corrida_km": r[8], "corrida_cal": r[9]
    } for r in cursor.fetchall()}
    
    inserted = 0
    updated = 0
    
    for row in rows:
        dt = row.get("data_hora")
        # Garante que a data_hora está no formato correto 'YYYY-MM-DD 00:00:00'
        if len(dt) == 10:
            dt = f"{dt} 00:00:00"
            
        passos = int(row.get("passos", 0) or 0)
        cal = int(row.get("calorias_gastas", 0) or 0)
        dist = float(row.get("distancia_km", 0.0) or 0.0)
        sono_tot = int(row.get("sono_total_min", 0) or 0)
        sono_prof = int(row.get("sono_profundo_min", 0) or 0)
        hrv = int(row.get("hrv_ms", 0) or 0)
        pai = int(row.get("pai", 0) or 0)
        corr_km = float(row.get("corrida_km", 0.0) or 0.0)
        corr_cal = int(row.get("corrida_cal", 0) or 0)
        
        if dt in local_rows:
            local = local_rows[dt]
            # Mescla inteligente: atualiza se HRV/PAI forem zero localmente mas existirem na nuvem,
            # ou se passos/calorias forem maiores na nuvem.
            need_update = False
            new_hrv = local["hrv_ms"]
            new_pai = local["pai"]
            new_passos = local["passos"]
            new_cal = local["calorias_gastas"]
            
            if local["hrv_ms"] == 0 and hrv > 0:
                new_hrv = hrv
                need_update = True
            if local["pai"] == 0 and pai > 0:
                new_pai = pai
                need_update = True
            if passos > local["passos"]:
                new_passos = passos
                need_update = True
            if cal > local["calorias_gastas"]:
                new_cal = cal
                need_update = True
                
            if need_update:
                cursor.execute("""
                    UPDATE amazfit_dados 
                    SET passos=?, calorias_gastas=?, hrv_ms=?, pai=?
                    WHERE data_hora=?
                """, (new_passos, new_cal, new_hrv, new_pai, dt))
                updated += 1
        else:
            # Insere registro que só existia no Supabase
            cursor.execute("""
                INSERT INTO amazfit_dados (data_hora, passos, calorias_gastas, distancia_km, sono_total_min, sono_profundo_min, hrv_ms, pai, corrida_km, corrida_cal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (dt, passos, cal, dist, sono_tot, sono_prof, hrv, pai, corr_km, corr_cal))
            inserted += 1
            
    conn.commit()
    print(f"  Tabela amazfit_dados: {inserted} inseridos, {updated} mesclados/atualizados.")
    return inserted + updated

def main():
    print("=" * 60)
    print("  INICIANDO IMPORTACAO DE DADOS DO SUPABASE PARA O SQLITE LOCAL")
    print("=" * 60)
    
    try:
        full_dump = extract_json_dump()
        conn = sqlite3.connect(DB_PATH)
        init_sqlite_tables(conn)
        
        # 1. Refeições
        import_table_generic(conn, "refeicoes", full_dump.get("refeicoes"), 
                             ["id", "data_hora", "categoria", "descricao", "calorias", "proteinas", "carboidratos", "gorduras", "componentes_json"])
        
        # 2. Água
        import_table_generic(conn, "agua", full_dump.get("agua"), 
                             ["id", "data_hora", "quantidade_ml"])
        
        # 3. Medidas (Peso)
        import_table_generic(conn, "medidas", full_dump.get("medidas"), 
                             ["id", "data", "peso", "cintura", "abdomen", "peitoral", "quadril", "coxa_dir", "coxa_esq", "panturrilha_dir", "panturrilha_esq", "biceps_dir", "biceps_esq"])
        
        # 4. Medicação
        import_table_generic(conn, "medicacao", full_dump.get("medicacao"), 
                             ["id", "data_hora", "dose_mg"])
        
        # 5. Hevy Treinos
        import_table_generic(conn, "hevy_treinos", full_dump.get("hevy_treinos"), 
                             ["id", "data_hora", "titulo", "descricao", "exercicios_json", "duracao_min", "volume_kg"])
        
        # 6. Alimentos Favoritos
        import_table_generic(conn, "alimentos_favoritos", full_dump.get("alimentos_favoritos"), 
                             ["id", "descricao", "categoria", "calorias", "proteinas", "carboidratos", "gorduras", "componentes_json", "favorito", "vezes_usado", "criado_em", "qtd_referencia", "unidade_referencia"])
        
        # 7. Evacuações
        import_table_generic(conn, "evacuacoes", full_dump.get("evacuacoes"), 
                             ["id", "data_hora", "observacao", "criado_em", "esforco"])
        
        # 8. IA Análises Clínicas
        import_table_generic(conn, "ia_analises_clinicas", full_dump.get("ia_analises_clinicas"), 
                             ["id", "data_hora", "analise_txt", "n_dias"])
        
        # 9. Amazfit Dados (Fusão inteligente de HRV e PAI)
        merge_amazfit_dados(conn, full_dump.get("amazfit_dados"))
        
        conn.close()
        print("=" * 60)
        print("  FUSAO E IMPORTACAO CONCLUIDAS COM SUCESSO!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Erro durante a importacao: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
