import sqlite3

def init_db():
    # Conecta (ou cria) o arquivo do banco de dados
    conn = sqlite3.connect('nutricao.db')
    cursor = conn.cursor()

    # 1. Tabela de Refeições
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS refeicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            descricao TEXT,
            calorias REAL,
            proteinas REAL,
            carboidratos REAL,
            gorduras REAL
        )
    ''')

    # 2. Tabela de Água
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agua (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            quantidade_ml INTEGER
        )
    ''')

    # 3. Tabela de Medicação (Tirzepatida - Sextas-feiras)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            medicamento TEXT DEFAULT 'Tirzepatida',
            dose_mg REAL
        )
    ''')

    # 4. Tabela de Medidas Corporais (Quintas-feiras)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATETIME DEFAULT CURRENT_DATE,
            peso REAL,
            coxa_dir REAL,
            coxa_esq REAL,
            biceps_dir REAL,
            biceps_esq REAL,
            peitoral REAL,
            abdomen REAL,
            cintura REAL,
            panturrilha_dir REAL,
            panturrilha_esq REAL,
            quadril REAL
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Banco de dados 'nutricao.db' e tabelas criados com sucesso!")

if __name__ == '__main__':
    init_db()