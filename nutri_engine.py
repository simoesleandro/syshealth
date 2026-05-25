import os
import json
import re
import requests
import google.generativeai as genai

# Dicionário de Alimentos Comuns (TACO/USDA simplificado para pesos cozidos brasileiros)
# Valores padronizados por 100g de alimento
TABELA_ALIMENTOS_LOCAL = {
    # Carboidratos cozidos/comuns
    "arroz": {"kcal": 130.0, "prot": 2.5, "carb": 28.0, "gord": 0.2, "nome": "Arroz Branco Cozido"},
    "arroz branco": {"kcal": 130.0, "prot": 2.5, "carb": 28.0, "gord": 0.2, "nome": "Arroz Branco Cozido"},
    "arroz integral": {"kcal": 124.0, "prot": 2.6, "carb": 25.8, "gord": 1.0, "nome": "Arroz Integral Cozido"},
    "feijao": {"kcal": 76.0, "prot": 4.8, "carb": 14.0, "gord": 0.5, "nome": "Feijão Cozido"},
    "feijão": {"kcal": 76.0, "prot": 4.8, "carb": 14.0, "gord": 0.5, "nome": "Feijão Cozido"},
    "feijao preto": {"kcal": 77.0, "prot": 4.5, "carb": 14.0, "gord": 0.5, "nome": "Feijão Preto Cozido"},
    "feijão preto": {"kcal": 77.0, "prot": 4.5, "carb": 14.0, "gord": 0.5, "nome": "Feijão Preto Cozido"},
    "batata doce": {"kcal": 86.0, "prot": 1.6, "carb": 20.1, "gord": 0.1, "nome": "Batata Doce Cozida"},
    "batata": {"kcal": 86.0, "prot": 2.0, "carb": 19.0, "gord": 0.1, "nome": "Batata Cozida"},
    "pao de forma": {"kcal": 260.0, "prot": 8.0, "carb": 49.0, "gord": 3.0, "nome": "Pão de Forma"},
    "pao": {"kcal": 265.0, "prot": 9.0, "carb": 55.0, "gord": 1.0, "nome": "Pão Francês"},
    "pão": {"kcal": 265.0, "prot": 9.0, "carb": 55.0, "gord": 1.0, "nome": "Pão Francês"},
    "aveia": {"kcal": 389.0, "prot": 16.9, "carb": 66.3, "gord": 6.9, "nome": "Aveia em Flocos"},
    "tapioca": {"kcal": 240.0, "prot": 0.0, "carb": 60.0, "gord": 0.0, "nome": "Goma de Tapioca Cozida"},

    # Proteínas (pesos cozidos/grelhados médios)
    "alcatra": {"kcal": 200.0, "prot": 28.0, "carb": 0.0, "gord": 9.0, "nome": "Alcatra Grelhada"},
    "frango": {"kcal": 165.0, "prot": 31.0, "carb": 0.0, "gord": 3.6, "nome": "Peito de Frango Grelhado"},
    "peito de frango": {"kcal": 165.0, "prot": 31.0, "carb": 0.0, "gord": 3.6, "nome": "Peito de Frango Grelhado"},
    "patinho": {"kcal": 185.0, "prot": 30.0, "carb": 0.0, "gord": 6.0, "nome": "Patinho Grelhado"},
    "ovo": {"kcal": 143.0, "prot": 13.0, "carb": 0.7, "gord": 9.5, "nome": "Ovo Inteiro Cozido"},
    "ovos": {"kcal": 143.0, "prot": 13.0, "carb": 0.7, "gord": 9.5, "nome": "Ovo Inteiro Cozido"},
    "clara de ovo": {"kcal": 52.0, "prot": 11.0, "carb": 0.7, "gord": 0.2, "nome": "Clara de Ovo"},
    "salmao": {"kcal": 206.0, "prot": 22.0, "carb": 0.0, "gord": 12.0, "nome": "Salmão Grelhado"},
    "salmão": {"kcal": 206.0, "prot": 22.0, "carb": 0.0, "gord": 12.0, "nome": "Salmão Grelhado"},
    "whey": {"kcal": 393.0, "prot": 80.0, "carb": 6.7, "gord": 5.0, "nome": "Whey Protein"},
    "whey protein": {"kcal": 393.0, "prot": 80.0, "carb": 6.7, "gord": 5.0, "nome": "Whey Protein"},
    "carne moida": {"kcal": 210.0, "prot": 26.0, "carb": 0.0, "gord": 11.0, "nome": "Carne Moída Grelhada"},
    "carne moída": {"kcal": 210.0, "prot": 26.0, "carb": 0.0, "gord": 11.0, "nome": "Carne Moída Grelhada"},

    # Gorduras e Miscelâneas
    "azeite": {"kcal": 884.0, "prot": 0.0, "carb": 0.0, "gord": 100.0, "nome": "Azeite de Oliva Extra Virgem"},
    "azeite de oliva": {"kcal": 884.0, "prot": 0.0, "carb": 0.0, "gord": 100.0, "nome": "Azeite de Oliva Extra Virgem"},
    "manteiga": {"kcal": 717.0, "prot": 0.9, "carb": 0.1, "gord": 81.0, "nome": "Manteiga com Sal"},
    "pasta de amendoim": {"kcal": 588.0, "prot": 25.0, "carb": 20.0, "gord": 50.0, "nome": "Pasta de Amendoim"},
    "uva passa": {"kcal": 299.0, "prot": 3.1, "carb": 79.0, "gord": 0.5, "nome": "Uva Passa"},
    "banana": {"kcal": 89.0, "prot": 1.1, "carb": 22.8, "gord": 0.3, "nome": "Banana"},
    "abacate": {"kcal": 160.0, "prot": 2.0, "carb": 9.0, "gord": 15.0, "nome": "Abacate"},
    "queijo": {"kcal": 320.0, "prot": 23.0, "carb": 1.5, "gord": 25.0, "nome": "Queijo Muçarela/Prato"},
    "queijo prato": {"kcal": 350.0, "prot": 23.0, "carb": 1.0, "gord": 28.0, "nome": "Queijo Prato"},
    "queijo mucarela": {"kcal": 300.0, "prot": 22.0, "carb": 2.0, "gord": 22.0, "nome": "Queijo Muçarela"},
    "queijo muçarela": {"kcal": 300.0, "prot": 22.0, "carb": 2.0, "gord": 22.0, "nome": "Queijo Muçarela"},
}

def normalizar_nome(nome: str) -> str:
    """Remove acentos, converte para minúsculas e remove espaços sobressalentes."""
    nome = nome.lower().strip()
    nome = re.sub(r'[áàâãä]', 'a', nome)
    nome = re.sub(r'[éèêë]', 'e', nome)
    nome = re.sub(r'[íìîï]', 'i', nome)
    nome = re.sub(r'[óòôõö]', 'o', nome)
    nome = re.sub(r'[úùûü]', 'u', nome)
    nome = re.sub(r'[ç]', 'c', nome)
    return nome

def lookup_local(nome: str) -> dict | None:
    """Busca o ingrediente na tabela local de alimentos comuns por correspondência parcial ou exata."""
    norm = normalizar_nome(nome)
    # 1. Tenta correspondência exata
    if norm in TABELA_ALIMENTOS_LOCAL:
        return TABELA_ALIMENTOS_LOCAL[norm]
    # 2. Tenta correspondência parcial (se uma chave local estiver contida no nome normalizado)
    for key, values in TABELA_ALIMENTOS_LOCAL.items():
        if key in norm or norm in key:
            return values
    return None

def buscar_usda(query: str) -> dict | None:
    """Consulta o banco de dados da API USDA (FoodData Central)."""
    try:
        api_key = os.getenv("USDA_API_KEY", "DEMO_KEY")
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        r = requests.get(
            url,
            params={
                "query": query,
                "api_key": api_key,
                "dataType": "Foundation,SR Legacy",
                "pageSize": 1
            },
            timeout=5
        )
        if r.status_code == 200:
            foods = r.json().get("foods", [])
            if foods:
                food = foods[0]
                nutrients = {n["nutrientName"]: n.get("value", 0) for n in food.get("foodNutrients", [])}
                kcal = nutrients.get("Energy", 0) or nutrients.get("Energy (Atwater General Factors)", 0)
                return {
                    "kcal": float(kcal),
                    "prot": float(nutrients.get("Protein", 0)),
                    "carb": float(nutrients.get("Carbohydrate, by difference", 0)),
                    "gord": float(nutrients.get("Total lipid (fat)", 0)),
                    "nome": food.get("description", query)
                }
    except Exception:
        pass
    return None

def estimar_densidade_ia(model, nome_pt: str) -> dict:
    """Utiliza a IA estritamente para obter a densidade nutricional por 100g (sem fazer cálculos aritméticos)."""
    prompt = (
        f"Estime a informação nutricional média por 100g para o seguinte alimento brasileiro: '{nome_pt}'.\n"
        "Retorne EXCLUSIVAMENTE um JSON válido no seguinte formato:\n"
        '{"kcal": <float>, "prot": <float>, "carb": <float>, "gord": <float>}\n'
        "Use ponto decimal para frações. Não adicione markdown, textos explicativos, nem aspas de bloco ```json."
    )
    try:
        res = model.generate_content(prompt)
        texto = re.sub(r"```json|```", "", res.text).strip()
        # Encontra o primeiro objeto { ... }
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            texto = match.group(0)
        data = json.loads(texto)
        return {
            "kcal": float(data.get("kcal", 0)),
            "prot": float(data.get("prot", 0)),
            "carb": float(data.get("carb", 0)),
            "gord": float(data.get("gord", 0)),
            "nome": nome_pt
        }
    except Exception:
        return {"kcal": 0.0, "prot": 0.0, "carb": 0.0, "gord": 0.0, "nome": nome_pt}

def decompor_refeicao_ia(model, descricao: str) -> list:
    """Usa a IA para mapear a descrição semântica para uma lista de ingredientes estruturada com quantidades em gramas."""
    prompt = (
        f"Decomponha a seguinte refeição em seus ingredientes e pesos individuais: '{descricao}'.\n"
        "Se o usuário mencionar unidades de medida caseira (colher, fatia, copo, concha, unidade), "
        "converta para o peso correspondente em gramas (ex: 1 colher de azeite -> 12g, 1 ovo -> 50g, "
        "1 fatia de pão -> 25g, 1 concha de feijão -> 100g, 45g de uva passa -> 45g).\n\n"
        "Retorne APENAS um JSON no seguinte formato de array (sem markdown, sem bloco de código ```json):\n"
        "[\n"
        "  {\n"
        '    "ingrediente": "<nome do ingrediente em portugues>",\n'
        '    "ingrediente_en": "<traducao simples do ingrediente para ingles para busca no USDA>",\n'
        '    "peso_g": <int>\n'
        "  }\n"
        "]\n"
        "Não retorne nenhuma mensagem antes ou depois do JSON."
    )
    try:
        res = model.generate_content(prompt)
        texto = re.sub(r"```json|```", "", res.text).strip()
        match = re.search(r"\[.*\]", texto, re.DOTALL)
        if match:
            texto = match.group(0)
        return json.loads(texto)
    except Exception:
        return []

def calcular_macros_refeicao(model, descricao: str) -> dict:
    """Calcula e soma os macronutrientes da refeição de forma determinística."""
    componentes = decompor_refeicao_ia(model, descricao)
    
    total_kcal = 0.0
    total_prot = 0.0
    total_carb = 0.0
    total_gord = 0.0
    detalhes = []

    for comp in componentes:
        nome = comp.get("ingrediente", "")
        nome_en = comp.get("ingrediente_en", "")
        peso = float(comp.get("peso_g", 100))

        # 1. Tabela local
        dados = lookup_local(nome)
        fonte = "LOCAL"

        # 2. USDA fallback
        if not dados and nome_en:
            dados = buscar_usda(nome_en)
            fonte = "USDA"

        # 3. IA fallback (densidade 100g)
        if not dados:
            dados = estimar_densidade_ia(model, nome)
            fonte = "IA (100g)"

        # Multiplicação exata em Python
        fator = peso / 100.0
        k = round(dados["kcal"] * fator, 1)
        p = round(dados["prot"] * fator, 1)
        c = round(dados["carb"] * fator, 1)
        g = round(dados["gord"] * fator, 1)

        total_kcal += k
        total_prot += p
        total_carb += c
        total_gord += g

        detalhes.append({
            "nome": dados.get("nome", nome),
            "gramas": int(peso),
            "kcal": round(k, 1),
            "prot": round(p, 1),
            "carb": round(c, 1),
            "gord": round(g, 1),
            "fonte": fonte
        })

    return {
        "descricao_resumida": ", ".join([f"{d['nome']} ({d['gramas']}g)" for d in detalhes]) or descricao,
        "calorias": round(total_kcal, 1),
        "proteinas": round(total_prot, 1),
        "carboidratos": round(total_carb, 1),
        "gorduras": round(total_gord, 1),
        "detalhes": detalhes
    }

def obter_critica_nutricional(model, refeicao_dados: dict, categoria: str, peso_usuario: float = 93.0) -> str:
    """Solicita a avaliação metabólica qualitativa baseada nos dados matemáticos determinísticos."""
    macros_txt = (
        f"Refeição: {refeicao_dados['descricao_resumida']}\n"
        f"Categoria/Horário: {categoria}\n"
        f"Calorias Totais: {refeicao_dados['calorias']} kcal\n"
        f"Proteínas: {refeicao_dados['proteinas']}g\n"
        f"Carboidratos: {refeicao_dados['carboidratos']}g\n"
        f"Gorduras: {refeicao_dados['gorduras']}g\n"
        f"Peso Corporal do Usuário: {peso_usuario} kg\n"
    )

    user_prompt = (
        f"Aqui estão os dados exatos e calculados da refeição:\n\n"
        f"{macros_txt}\n"
        "Com base em seus conhecimentos como Nutricionista Esportivo Sênior e de Elite, forneça sua crítica focando em:\n"
        "1. VELOCIDADE DE DIGESTÃO & TIMING: Avalie se a distribuição de macros é ideal para o horário e categoria informados.\n"
        "2. QUALIDADE E COMPOSIÇÃO METABÓLICA: Analise a densidade de macros (proporção carboidratos/proteínas e teor de gordura) e se há associação deletéria de carboidratos com gorduras saturadas.\n"
        "3. PONTOS FORTES E FRAQUEZAS: Um ponto forte metabólico desta refeição e uma falha que sabota a performance esportiva.\n"
        "4. DICA DE OTIMIZAÇÃO: O que adicionar ou remover exatamente para otimizar o prato.\n"
        "5. NOTA DA REFEIÇÃO: Uma nota de 0 a 100 baseada na qualidade metabólica.\n\n"
        "Estruture sua resposta de forma cirúrgica, concisa, técnica e direta."
    )

    system_prompt = (
        "Você é um Nutricionista Esportivo de Elite e Arquiteto de Performance Humana. "
        "Sua missão é realizar uma análise clínica e metabólica extremamente crítica e sem rodeios "
        "de uma refeição, baseando-se estritamente nos macronutrientes exatos fornecidos. "
        "Seja direto, técnico e use terminologia clínica apropriada."
    )

    # Nota: Caso a biblioteca não suporte system_instruction diretamente na chamada, concatenamos o contexto no início do prompt.
    prompt_completo = f"Instrução do Sistema:\n{system_prompt}\n\nInstrução do Usuário:\n{user_prompt}"
    
    try:
        res = model.generate_content(prompt_completo)
        return res.text
    except Exception as e:
        return f"Não foi possível obter a crítica nutricional: {e}"
