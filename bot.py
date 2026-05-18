import telebot
import google.generativeai as genai
import json
import re
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, date
import db as DB
from zepp_sync import zepp_sync, save as _zepp_save, make_headers as _zepp_headers

load_dotenv()

log = logging.getLogger("bot")

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ZEPP_TOKEN     = os.getenv('ZEPP_APP_TOKEN', '').strip()
ZEPP_USER_ID   = os.getenv('ZEPP_USER_ID', '').strip()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# ── Macros fixos ──────────────────────────────────────────────────────────────
MACROS_WHEY = {
    "descricao_resumida": "Whey Protein Isolado Dux (30g)",
    "calorias": 118, "proteinas": 24, "carboidratos": 2, "gorduras": 1.5
}
MACROS_CREATINA = {
    "descricao_resumida": "Creatina (6g)",
    "calorias": 0, "proteinas": 0, "carboidratos": 0, "gorduras": 0
}

# ── DB helpers ────────────────────────────────────────────────────────────────
def executar_query(query, params=()):
    DB.execute(query, list(params) if params else [])

def salvar_refeicao(dados):
    DB.execute(
        'INSERT INTO refeicoes (categoria, descricao, calorias, proteinas, carboidratos, gorduras) VALUES (?, ?, ?, ?, ?, ?)',
        [dados.get('categoria', 'Lanche'), dados['descricao_resumida'],
         dados['calorias'], dados['proteinas'], dados['carboidratos'], dados['gorduras']]
    )

def salvar_agua(ml):
    executar_query('INSERT INTO agua (quantidade_ml) VALUES (?)', (ml,))

def salvar_peso(kg):
    executar_query('INSERT INTO medidas (peso) VALUES (?)', (kg,))

def salvar_medicacao(mg):
    executar_query('INSERT INTO medicacao (dose_mg) VALUES (?)', (mg,))

def init_amazfit_table():
    DB.init_tables()

def _criar_registro_vazio(day):
    """Cria registro do dia com zeros se não existir."""
    DB.execute(
        "INSERT INTO amazfit_dados (data_hora,passos,calorias_gastas,distancia_km,"
        "sono_total_min,sono_profundo_min,hrv_ms,pai) VALUES (?,0,0,0,0,0,0,0) "
        "ON CONFLICT(data_hora) DO NOTHING",
        [f"{day} 00:00:00"]
    )

def get_amazfit_hoje(day=None):
    day = day or date.today().strftime("%Y-%m-%d")
    df  = DB.query("SELECT * FROM amazfit_dados WHERE data_hora=?", [f"{day} 00:00:00"])
    if df.empty:
        return None
    return df.iloc[0].to_dict()

def update_hrv_pai(day, hrv, pai):
    DB.execute(
        "UPDATE amazfit_dados SET hrv_ms=?, pai=? WHERE data_hora=?",
        [hrv, pai, f"{day} 00:00:00"]
    )

def fmt_sono(m):
    return f"{m//60}h{m%60:02d}" if m else "—"

# ── Resumo diário ─────────────────────────────────────────────────────────────
def build_resumo(data, day_pt):
    if not data:
        return (f"⚡ *SYS.HEALTH — {day_pt}*\n\n"
                "⚠️ Sem dados. Tente: /sync")
    hrv = f"*{data['hrv_ms']} ms*" if data['hrv_ms'] else "⏳ use /hrv 38"
    pai = f"*{data['pai']}*"       if data['pai']    else "⏳ use /pai 117"
    return (
        f"⚡ *SYS.HEALTH — {day_pt}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👟 Passos: *{data['passos']:,}*\n"
        f"🔥 Calorias gastas: *{data['calorias_gastas']:,} kcal*\n"
        f"📍 Distância: *{data['distancia_km']} km*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌙 Sono total: *{fmt_sono(data['sono_total_min'])}*\n"
        f"💤 Sono profundo: *{fmt_sono(data['sono_profundo_min'])}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💓 HRV: {hrv}\n"
        f"⚡ PAI: {pai}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"_Use /hrv <valor> e /pai <valor> para completar_"
    )

# ── IA ────────────────────────────────────────────────────────────────────────
def analisar_texto_com_ia(texto):
    hora_atual = datetime.now().strftime("%H:%M")
    prompt = (
        f'Você é um assistente de saúde e nutrição. O usuário enviou: "{texto}". '
        f'Hora atual: {hora_atual}.\n\n'
        'Retorne APENAS JSON puro, sem markdown, sem ```json.\n'
        'Retorne um objeto ou lista de objetos se houver múltiplas ações.\n\n'
        'O campo "tipo" é OBRIGATÓRIO. Valores: "refeicao", "agua", "peso", "medicacao".\n\n'
        'REFEIÇÃO (tipo="refeicao"):\n'
        '{"tipo":"refeicao","categoria":"<Café da Manhã|Lanche da Manhã|Almoço|Lanche da Tarde|Jantar|Lanche da Noite>",'
        '"descricao_resumida":"<texto>","calorias":<n>,"proteinas":<g>,"carboidratos":<g>,"gorduras":<g>}\n\n'
        'ÁGUA: {"tipo":"agua","quantidade_ml":<n>}\n'
        'PESO: {"tipo":"peso","peso_kg":<n>}\n'
        'MEDICAÇÃO (só Tirzepatida): {"tipo":"medicacao","dose_mg":<n>}\n\n'
        'REGRAS ESPECIAIS (rotina do Leandro):\n'
        '- Whey de manhã → categoria "Café da Manhã", cal 118, prot 24, carb 2, gord 1.5\n'
        '- Whey à noite/pós-treino/com creatina → LISTA com 2 objetos (Whey + Creatina 0cal)\n'
        '- Ômega 3/Omegafor → tipo "refeicao", cal 9, prot 0, carb 0, gord 1, desc "Ômega 3 Omegafor Plus"\n'
        '- Magnésio/quelato/Vitha → tipo "refeicao", cal 0, prot 0, carb 0, gord 0, desc "Magnésio Quelato Trio Vitha"\n'
        '- D3/K2/BioVit/vitamina D → tipo "refeicao", cal 0, prot 0, carb 0, gord 0, desc "Vit. D3+K2 BioVit"\n'
        '- Categoria: use o que o usuário disser; se não informar, infira pela hora.\n'
        '- Para qualquer alimento, estime macros pelo peso informado.\n'
        'NUNCA omita o campo "tipo":"refeicao" para comidas.'
    )
    resposta    = model.generate_content(prompt)
    texto_limpo = re.sub(r'```json|```', '', resposta.text).strip()
    return json.loads(texto_limpo)

# ════════════════════════════════════════════════════════════════════════════
# HANDLERS
# ════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.reply_to(message,
        "⚡ *SYS.HEALTH Bot Online!*\n\n"
        "*Comandos disponíveis:*\n"
        "/sync — sincroniza dados do Bip 6\n"
        "/status — resumo do dia\n"
        "/hrv 38 — salva HRV do dia\n"
        "/pai 117 — salva PAI do dia\n"
        "/hrv 38 /pai 117 — salva os dois juntos\n\n"
        "Para registrar alimentação, água ou peso, basta digitar normalmente.",
        parse_mode='Markdown')


@bot.message_handler(commands=['sync'])
def cmd_sync(message):
    bot.send_message(message.chat.id, "⏳ Sincronizando com o Zepp...")
    today  = date.today().strftime("%Y-%m-%d")
    result = zepp_sync(today)
    if result:
        _zepp_save(result)
        day_pt = date.today().strftime("%d/%m/%Y")
        bot.send_message(message.chat.id, build_resumo(result, day_pt),
                         parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id,
            "⚠️ Não foi possível sincronizar. Verifique se o Zepp está conectado "
            "e se ZEPP_APP_TOKEN está no .env")


@bot.message_handler(commands=['status'])
def cmd_status(message):
    today  = date.today().strftime("%Y-%m-%d")
    day_pt = date.today().strftime("%d/%m/%Y")
    data   = get_amazfit_hoje(today)
    bot.send_message(message.chat.id, build_resumo(data, day_pt),
                     parse_mode='Markdown')


@bot.message_handler(commands=['hrv'])
def cmd_hrv(message):
    try:
        val = int(message.text.split()[1])
        today = date.today().strftime("%Y-%m-%d")
        existing = get_amazfit_hoje(today)
        if not existing:
            _criar_registro_vazio(today)
            existing = {"hrv_ms": 0, "pai": 0}
        update_hrv_pai(today, val, existing["pai"])
        bot.reply_to(message, f"💓 HRV salvo: *{val} ms*", parse_mode='Markdown')
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Uso: /hrv 38")


@bot.message_handler(commands=['pai'])
def cmd_pai(message):
    try:
        val = int(message.text.split()[1])
        today = date.today().strftime("%Y-%m-%d")
        existing = get_amazfit_hoje(today)
        if not existing:
            _criar_registro_vazio(today)
            existing = {"hrv_ms": 0, "pai": 0}
        update_hrv_pai(today, existing["hrv_ms"], val)
        bot.reply_to(message, f"⚡ PAI salvo: *{val}*", parse_mode='Markdown')
    except (IndexError, ValueError):
        bot.reply_to(message, "❌ Uso: /pai 117")


@bot.message_handler(func=lambda message: True)
def processar_mensagem(message):
    texto = message.text.strip()

    # Atalho: /hrv 38 /pai 117 em mensagem livre
    hrv_match = re.search(r'/hrv\s+(\d+)', texto, re.IGNORECASE)
    pai_match = re.search(r'/pai\s+(\d+)', texto, re.IGNORECASE)
    if hrv_match or pai_match:
        today    = date.today().strftime("%Y-%m-%d")
        existing = get_amazfit_hoje(today) or {"hrv_ms": 0, "pai": 0}
        hrv_val  = int(hrv_match.group(1)) if hrv_match else existing["hrv_ms"]
        pai_val  = int(pai_match.group(1)) if pai_match  else existing["pai"]
        update_hrv_pai(today, hrv_val, pai_val)
        bot.reply_to(message,
            f"✅ Salvo!\n💓 HRV: *{hrv_val} ms*\n⚡ PAI: *{pai_val}*",
            parse_mode='Markdown')
        return

    # Processamento de alimentação/água/peso via IA
    bot.send_message(message.chat.id, "⏳ Processando...")
    try:
        dados = analisar_texto_com_ia(texto)
        if isinstance(dados, dict):
            dados = [dados]

        respostas = []
        for item in dados:
            tipo = item.get('tipo')
            if tipo == 'refeicao':
                salvar_refeicao(item)
                respostas.append(
                    f"🍽️ *{item.get('categoria', 'Refeição')}:* "
                    f"{item['descricao_resumida']} (+{item['proteinas']}g Prot)"
                )
            elif tipo == 'agua':
                salvar_agua(item['quantidade_ml'])
                respostas.append(f"💧 *Água:* {item['quantidade_ml']} ml")
            elif tipo == 'peso':
                salvar_peso(item['peso_kg'])
                respostas.append(f"⚖️ *Peso:* {item['peso_kg']} kg")
            elif tipo == 'medicacao':
                salvar_medicacao(item['dose_mg'])
                respostas.append(f"💉 *Medicação:* {item['dose_mg']}mg")

        if respostas:
            bot.reply_to(message,
                "✅ *Registros salvos!*\n\n" + "\n".join(respostas),
                parse_mode='Markdown')
        else:
            bot.reply_to(message, "❓ Não entendi. Tente descrever sua refeição ou use /sync, /hrv, /pai.")
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Não consegui interpretar. Tente reformular a mensagem.")
    except Exception as e:
        log.error(f"Erro processando mensagem: {e}", exc_info=True)
        bot.reply_to(message, "❌ Erro interno. Tente novamente em instantes.")


# ── Init ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_amazfit_table()
    print("🚀 SYS.HEALTH Bot iniciado!")
    bot.infinity_polling()
