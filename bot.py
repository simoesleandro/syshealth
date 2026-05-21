import telebot
import sqlite3
import google.generativeai as genai
import json
import re
import os
import base64
import requests
from dotenv import load_dotenv
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import db as DB

FUSO_BR = ZoneInfo("America/Sao_Paulo")

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ZEPP_TOKEN     = os.getenv('ZEPP_APP_TOKEN', '').strip()
ZEPP_USER_ID   = os.getenv('ZEPP_USER_ID', '').strip()
DB_PATH        = os.getenv('DB_PATH', 'nutricao.db')

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
    hoje = date.today().strftime("%Y-%m-%d")
    df = DB.query("SELECT id FROM medidas WHERE date(data)=?", [hoje])
    if not df.empty:
        DB.execute("UPDATE medidas SET peso=? WHERE date(data)=?", [kg, hoje])
    else:
        DB.execute("INSERT INTO medidas (data, peso) VALUES (?, ?)", [hoje, kg])

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

def save_amazfit(row):
    DB.execute("DELETE FROM amazfit_dados WHERE data_hora=?", [row["data_hora"]])
    DB.execute(
        "INSERT INTO amazfit_dados VALUES (?,?,?,?,?,?,?,?)",
        [row["data_hora"], row["passos"], row["calorias_gastas"], row["distancia_km"],
         row["sono_total_min"], row["sono_profundo_min"], row["hrv_ms"], row["pai"]]
    )

def update_hrv_pai(day, hrv, pai):
    DB.execute(
        "UPDATE amazfit_dados SET hrv_ms=?, pai=? WHERE data_hora=?",
        [hrv, pai, f"{day} 00:00:00"]
    )

# ── Zepp sync ─────────────────────────────────────────────────────────────────
def zepp_headers():
    return {
        "Accept": "*/*", "appname": "com.huami.midong",
        "appplatform": "ios_phone", "apptoken": ZEPP_TOKEN,
        "channel": "appstore", "country": "BR", "lang": "pt_BR",
        "timezone": "America/Sao_Paulo",
        "User-Agent": "Zepp/10.3.1 (iPhone; iOS 26.4.2; Scale/3.00)", "v": "2.0",
    }

def decode_summary(b64):
    try:
        pad = b64 + "=" * (4 - len(b64) % 4)
        return json.loads(base64.b64decode(pad).decode("utf-8", "replace"))
    except Exception:
        return {}

def zepp_sync(day=None):
    """Sincroniza dados do Zepp. Retorna (row, erro_str) — erro_str é None se OK."""
    if not ZEPP_TOKEN or not ZEPP_USER_ID:
        return None, "ZEPP_APP_TOKEN ou ZEPP_USER_ID não configurados no .env"
    day = day or date.today().strftime("%Y-%m-%d")
    try:
        r = requests.get(
            "https://api-mifit-us3.zepp.com/v1/data/band_data.json",
            headers=zepp_headers(),
            params={"query_type": "summary", "device_type": "0",
                    "object_id": ZEPP_USER_ID, "from_date": day, "to_date": day},
            timeout=15
        )

        # HTTP fora do 200 → erro de rede/autenticação
        if r.status_code != 200:
            return None, f"HTTP {r.status_code} — {r.text[:120]}"

        data  = r.json()
        code  = data.get("code", "?")
        msg   = data.get("message", "")
        items = data.get("data", [])

        # Zepp retorna code != 1 quando o token expirou ou há erro de auth
        if code not in (1, "1", 0, "0"):
            dica = ""
            if "token" in msg.lower() or code in (6, "6", 7, "7"):
                dica = "\n\n🔑 *Token expirado.* Abra o app Zepp no celular, depois atualize ZEPP\\_APP\\_TOKEN no Render."
            return None, f"Zepp code={code}: {msg}{dica}"

        if not items:
            return None, f"Zepp não enviou dados para {day} (sem sincronização ainda?)"

        s    = decode_summary(items[0].get("summary", ""))
        stp  = s.get("stp", {}) or {}
        slp  = s.get("slp", {}) or {}
        deep = int(slp.get("dp", 0) or 0)
        lt   = int(slp.get("lt", 0) or 0)
        rem  = int(slp.get("dt", 0) or 0)
        tot  = deep + lt + rem or int(slp.get("ebt", 0) or 0)

        existing = get_amazfit_hoje(day) or {}
        row = {
            "data_hora":         f"{day} 00:00:00",
            "passos":            int(stp.get("ttl", 0) or 0),
            "calorias_gastas":   int(stp.get("cal", 0) or 0),
            "distancia_km":      round(int(stp.get("dis", 0) or 0) / 1000, 2),
            "sono_total_min":    tot,
            "sono_profundo_min": deep,
            "hrv_ms":            existing.get("hrv_ms", 0),
            "pai":               existing.get("pai", 0),
        }
        save_amazfit(row)
        return row, None

    except requests.Timeout:
        return None, "Timeout — servidor Zepp não respondeu em 15s"
    except requests.ConnectionError as e:
        return None, f"Erro de conexão com Zepp: {e}"
    except Exception as e:
        return None, f"Erro inesperado: {e}"

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
    agora_br = datetime.now(FUSO_BR)
    hora_atual = agora_br.strftime("%H:%M")
    # Detecta categoria explícita no texto
    texto_lower = texto.lower()
    categoria_forcada = None
    mapa_keywords = {
        "Café da Manhã":   ["café da manhã", "cafe da manha", "café:", "cafe:"],
        "Lanche da Manhã": ["lanche da manhã", "lanche da manha", "lanche manhã", "lanche manha"],
        "Almoço":          ["almoço:", "almoco:", "almoço", "almoco"],
        "Lanche da Tarde": ["lanche da tarde", "lanche tarde"],
        "Jantar":          ["jantar:", "jantar"],
        "Lanche da Noite": ["lanche da noite", "lanche noite"],
    }
    for cat, keywords in mapa_keywords.items():
        if any(kw in texto_lower for kw in keywords):
            categoria_forcada = cat
            break

    # Categoria por horário se não foi forçada
    hora_int = agora_br.hour
    if not categoria_forcada:
        if   6  <= hora_int <= 9:  cat_horario = "Café da Manhã"
        elif 10 <= hora_int <= 11: cat_horario = "Lanche da Manhã"
        elif 12 <= hora_int <= 14: cat_horario = "Almoço"
        elif 15 <= hora_int <= 17: cat_horario = "Lanche da Tarde"
        elif 18 <= hora_int <= 20: cat_horario = "Jantar"
        else:                      cat_horario = "Lanche da Noite"
    else:
        cat_horario = categoria_forcada

    prompt = (
        f'Você é um assistente de saúde e nutrição. O usuário enviou: "{texto}". '
        f'Hora atual (Brasília): {hora_atual}.\n\n'
        'Retorne APENAS JSON puro, sem markdown, sem ```json.\n'
        'Retorne um objeto ou lista de objetos se houver múltiplas ações.\n\n'
        'O campo "tipo" é OBRIGATÓRIO. Valores: "refeicao", "agua", "peso", "medicacao".\n\n'
        'REFEIÇÃO (tipo="refeicao"):\n'
        '{"tipo":"refeicao","categoria":"<valor>","descricao_resumida":"<texto>",'
        '"calorias":<n>,"proteinas":<g>,"carboidratos":<g>,"gorduras":<g>}\n\n'
        'ÁGUA: {"tipo":"agua","quantidade_ml":<n>}\n'
        'PESO: {"tipo":"peso","peso_kg":<n>}\n'
        'MEDICAÇÃO (só Tirzepatida): {"tipo":"medicacao","dose_mg":<n>}\n\n'
        f'CATEGORIA OBRIGATÓRIA para esta mensagem: "{cat_horario}"\n'
        'Use EXATAMENTE este valor no campo categoria, a menos que o usuário mencione\n'
        'explicitamente outro nome de refeição no texto.\n\n'
        'Horários de referência (use apenas se o usuário forçar outra categoria):\n'
        '06:00-09:30 → Café da Manhã\n'
        '09:31-11:30 → Lanche da Manhã\n'
        '11:31-14:30 → Almoço\n'
        '14:31-17:30 → Lanche da Tarde\n'
        '17:31-20:30 → Jantar\n'
        '20:31-23:59 → Lanche da Noite\n\n'
        'REGRAS ESPECIAIS (rotina do Leandro):\n'
        '- Whey de manhã → categoria "Café da Manhã", cal 118, prot 24, carb 2, gord 1.5\n'
        '- Whey à noite/pós-treino/com creatina → LISTA com 2 objetos (Whey + Creatina 0cal)\n'
        '- Ômega 3/Omegafor → tipo "refeicao", cal 9, prot 0, carb 0, gord 1, desc "Ômega 3 Omegafor Plus"\n'
        '- Magnésio/quelato/Vitha → tipo "refeicao", cal 0, prot 0, carb 0, gord 0, desc "Magnésio Quelato Trio Vitha"\n'
        '- D3/K2/BioVit/vitamina D → tipo "refeicao", cal 0, prot 0, carb 0, gord 0, desc "Vit. D3+K2 BioVit"\n'
        '- Para qualquer alimento, estime macros pelo peso/quantidade informado.\n'
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
        "📸 Foto do prato → IA identifica e registra macros automaticamente\n"
        "📏 Foto de tabela de medidas → IA detecta e salva as circunferências\n\n"
        "Para registrar alimentação, água ou peso, basta digitar normalmente.",
        parse_mode='Markdown')


@bot.message_handler(commands=['sync'])
def cmd_sync(message):
    bot.send_message(message.chat.id, "⏳ Sincronizando com o Zepp...")
    today        = date.today().strftime("%Y-%m-%d")
    result, erro = zepp_sync(today)
    if result:
        day_pt = date.today().strftime("%d/%m/%Y")
        bot.send_message(message.chat.id, build_resumo(result, day_pt),
                         parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id,
            f"⚠️ *Sync falhou*\n\n{erro}",
            parse_mode='Markdown')


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


# ── Helpers de foto ───────────────────────────────────────────────────────────

def _baixar_foto(message):
    """Baixa a maior resolução disponível."""
    info = bot.get_file(message.photo[-1].file_id)
    return bot.download_file(info.file_path)


def _cat_hora_bot():
    """Categoria de refeição pelo horário de Brasília."""
    h = datetime.now(FUSO_BR).hour
    if   6  <= h <= 9:  return "Café da Manhã"
    elif 10 <= h <= 11: return "Lanche da Manhã"
    elif 12 <= h <= 14: return "Almoço"
    elif 15 <= h <= 17: return "Lanche da Tarde"
    elif 18 <= h <= 20: return "Jantar"
    else:               return "Lanche da Noite"


def _processar_foto(message, foto_bytes):
    """
    Prompt unificado: Gemini detecta o tipo da foto (refeição ou medidas corporais)
    e extrai os dados em uma única chamada — sem depender de legenda.
    """
    import PIL.Image, io
    img      = PIL.Image.open(io.BytesIO(foto_bytes))
    cat      = _cat_hora_bot()
    hora_txt = datetime.now(FUSO_BR).strftime("%H:%M")

    prompt = (
        "Analise esta imagem e determine seu tipo, depois extraia os dados correspondentes.\n\n"

        "TIPO A — Prato de comida / alimento:\n"
        f"Hora: {hora_txt} (Brasília). Categoria sugerida: {cat}.\n"
        'Retorne: {{"tipo":"refeicao","categoria":"<cat>","descricao_resumida":"<nome e porção>",'
        '"calorias":<int>,"proteinas":<float>,"carboidratos":<float>,"gorduras":<float>}}\n'
        "Se houver múltiplos alimentos, retorne lista JSON de objetos com tipo=refeicao.\n\n"

        "TIPO B — Tabela / relatório de medidas corporais (bioimpedância, avaliação física,\n"
        "fichas com circunferências, peso, dobras cutâneas etc.):\n"
        'Retorne: {{"tipo":"medidas","data":"YYYY-MM-DD ou null",'
        '"peso":null,"cintura":null,"abdomen":null,"peitoral":null,"quadril":null,'
        '"coxa_dir":null,"coxa_esq":null,"panturrilha_dir":null,"panturrilha_esq":null,'
        '"biceps_dir":null,"biceps_esq":null}}\n'
        "Use null para campos não encontrados. Se só houver um valor de coxa/panturrilha/bíceps,\n"
        "repita em _dir e _esq. Unidades: peso em kg, demais em cm.\n\n"

        "TIPO C — Outra coisa:\n"
        'Retorne: {{"tipo":"outro","descricao":"<descrição breve do que é a imagem>"}}\n\n'

        "Retorne APENAS JSON puro, sem markdown, sem ```json."
    )

    resposta = model.generate_content([prompt, img])
    dados    = json.loads(re.sub(r'```json|```', '', resposta.text).strip())

    # ── Refeição ─────────────────────────────────────────────────────────────
    if isinstance(dados, list) or (isinstance(dados, dict) and dados.get("tipo") == "refeicao"):
        itens = dados if isinstance(dados, list) else [dados]
        respostas = []
        for item in itens:
            if item.get("tipo") == "refeicao":
                salvar_refeicao(item)
                respostas.append(
                    f"🍽️ *{item.get('categoria','Refeição')}:* {item['descricao_resumida']}\n"
                    f"   🔥 {item['calorias']} kcal · 🥩 {item['proteinas']}g · "
                    f"🌾 {item['carboidratos']}g · 🫒 {item['gorduras']}g"
                )
        if respostas:
            bot.reply_to(message,
                "✅ *Foto analisada e registrada!*\n\n" + "\n\n".join(respostas),
                parse_mode='Markdown')
        else:
            bot.reply_to(message, "❓ Não consegui identificar alimentos. Tente com uma foto mais clara.")

    # ── Medidas corporais ─────────────────────────────────────────────────────
    elif isinstance(dados, dict) and dados.get("tipo") == "medidas":
        data = dados.get("data") or date.today().strftime("%Y-%m-%d")
        if not data or data in ("null", ""):
            data = date.today().strftime("%Y-%m-%d")

        campos = ["peso", "cintura", "abdomen", "peitoral", "quadril",
                  "coxa_dir", "coxa_esq", "panturrilha_dir", "panturrilha_esq",
                  "biceps_dir", "biceps_esq"]
        vals = {c: float(dados[c]) for c in campos if dados.get(c) is not None}

        if not vals:
            bot.reply_to(message,
                "❓ Encontrei uma tabela de medidas, mas não consegui ler os valores.\n"
                "Tente com a imagem mais nítida ou com melhor iluminação.")
            return

        cols_sql = ", ".join(vals.keys())
        plhold   = ", ".join(["?"] * len(vals))
        DB.execute("DELETE FROM medidas WHERE date(data)=?", [data])
        DB.execute(
            f"INSERT INTO medidas (data, {cols_sql}) VALUES (?, {plhold})",
            [data] + list(vals.values())
        )

        labels = {
            "peso": "⚖️ Peso", "cintura": "📏 Cintura", "abdomen": "📏 Abdômen",
            "peitoral": "📏 Peitoral", "quadril": "📏 Quadril",
            "coxa_dir": "📏 Coxa D.", "coxa_esq": "📏 Coxa E.",
            "panturrilha_dir": "📏 Panturrilha D.", "panturrilha_esq": "📏 Panturrilha E.",
            "biceps_dir": "📏 Bíceps D.", "biceps_esq": "📏 Bíceps E.",
        }
        linhas = [f"📅 *{data}*\n"]
        for c, label in labels.items():
            v = vals.get(c)
            if v is not None:
                unit = "kg" if c == "peso" else "cm"
                linhas.append(f"{label}: *{v} {unit}*")

        bot.reply_to(message,
            f"✅ *Medidas registradas!* ({len(vals)} campos)\n\n" + "\n".join(linhas),
            parse_mode='Markdown')

    # ── Outro ─────────────────────────────────────────────────────────────────
    else:
        desc = dados.get("descricao", "imagem não reconhecida") if isinstance(dados, dict) else ""
        bot.reply_to(message,
            f"❓ Não reconheci esta imagem como alimento nem como tabela de medidas.\n"
            f"_{desc}_\n\n"
            "Envie a foto de um prato de comida, ou de uma tabela de medidas corporais.",
            parse_mode='Markdown')


@bot.message_handler(content_types=['photo'])
def handle_foto(message):
    try:
        bot.send_message(message.chat.id, "🔍 Analisando foto...")
        _processar_foto(message, _baixar_foto(message))
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ A IA não retornou dados válidos. Tente reenviar a foto.")
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao analisar foto: {e}")


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
    except Exception as e:
        bot.reply_to(message, f"❌ Erro: {e}")


# ── Init ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_amazfit_table()
    print("🚀 SYS.HEALTH Bot iniciado!")
    bot.infinity_polling(timeout=60, long_polling_timeout=60, logger_level=None, restart_on_change=False)
