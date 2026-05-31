import db
import datetime

hoje_sql = datetime.date.today().strftime("%Y-%m-%d")
print("Hoje SQL:", hoje_sql)

# Query 1: Todos os dados da hevy_treinos
df = db.query("SELECT id, data_hora, titulo FROM hevy_treinos ORDER BY data_hora DESC LIMIT 5")
print("\nWorkouts:")
print(df)

# Query 2: Testar a tradução de data_hora local_date
df_date = db.query("SELECT data_hora, date(data_hora, 'localtime') as local_date, date(data_hora) as raw_date FROM hevy_treinos ORDER BY data_hora DESC LIMIT 5")
print("\nTimezones:")
print(df_date)

# Query 3: Verificar o que a query do dashboard retorna (Corrigido para db.query)
df_hoje = db.query("""
    SELECT titulo, duracao_min, volume_kg, date(data_hora, 'localtime') as data_local
    FROM hevy_treinos
    WHERE date(data_hora, 'localtime') = ?
    ORDER BY data_hora DESC LIMIT 1
""", [hoje_sql])
print("\nTreino de Hoje:")
print(df_hoje)
