import os
import json
import re
import requests
import google.generativeai as genai

# Dicionário de Alimentos Comuns (TACO/USDA simplificado para pesos cozidos brasileiros)
# Valores padronizados por 100g de alimento
TABELA_ALIMENTOS_LOCAL = {
    # ── Carboidratos cozidos/comuns (TACO) ────────────────────────────────────
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
    "macarrao": {"kcal": 149.0, "prot": 5.0, "carb": 29.0, "gord": 1.0, "nome": "Macarrão Cozido"},
    "macarrão": {"kcal": 149.0, "prot": 5.0, "carb": 29.0, "gord": 1.0, "nome": "Macarrão Cozido"},
    "lentilha": {"kcal": 93.0, "prot": 7.0, "carb": 15.5, "gord": 0.3, "nome": "Lentilha Cozida"},
    "grao de bico": {"kcal": 164.0, "prot": 8.9, "carb": 27.4, "gord": 2.6, "nome": "Grão-de-Bico Cozido"},
    "inhame": {"kcal": 108.0, "prot": 1.5, "carb": 25.6, "gord": 0.1, "nome": "Inhame Cozido"},
    "mandioca": {"kcal": 125.0, "prot": 0.6, "carb": 30.1, "gord": 0.3, "nome": "Mandioca Cozida"},

    # ── Proteínas (pesos cozidos/grelhados — TACO) ────────────────────────────
    "alcatra": {"kcal": 200.0, "prot": 28.0, "carb": 0.0, "gord": 9.0, "nome": "Alcatra Grelhada"},
    "contrafile": {"kcal": 218.0, "prot": 27.0, "carb": 0.0, "gord": 12.0, "nome": "Contrafilé Grelhado"},
    "frango": {"kcal": 165.0, "prot": 31.0, "carb": 0.0, "gord": 3.6, "nome": "Peito de Frango Grelhado"},
    "peito de frango": {"kcal": 165.0, "prot": 31.0, "carb": 0.0, "gord": 3.6, "nome": "Peito de Frango Grelhado"},
    "frango grelhado": {"kcal": 165.0, "prot": 31.0, "carb": 0.0, "gord": 3.6, "nome": "Peito de Frango Grelhado"},
    "coxa de frango": {"kcal": 180.0, "prot": 26.0, "carb": 0.0, "gord": 8.0, "nome": "Coxa de Frango Grelhada"},
    "patinho": {"kcal": 185.0, "prot": 30.0, "carb": 0.0, "gord": 6.0, "nome": "Patinho Grelhado"},
    "file de tilapia": {"kcal": 128.0, "prot": 26.0, "carb": 0.0, "gord": 2.7, "nome": "Filé de Tilápia Grelhado"},
    "tilapia": {"kcal": 128.0, "prot": 26.0, "carb": 0.0, "gord": 2.7, "nome": "Tilápia Grelhada"},
    "atum": {"kcal": 130.0, "prot": 29.0, "carb": 0.0, "gord": 1.0, "nome": "Atum em Água (escorrido)"},
    "ovo": {"kcal": 143.0, "prot": 13.0, "carb": 0.7, "gord": 9.5, "nome": "Ovo Inteiro Cozido"},
    "ovos": {"kcal": 143.0, "prot": 13.0, "carb": 0.7, "gord": 9.5, "nome": "Ovo Inteiro Cozido"},
    "clara de ovo": {"kcal": 52.0, "prot": 11.0, "carb": 0.7, "gord": 0.2, "nome": "Clara de Ovo"},
    "salmao": {"kcal": 206.0, "prot": 22.0, "carb": 0.0, "gord": 12.0, "nome": "Salmão Grelhado"},
    "salmão": {"kcal": 206.0, "prot": 22.0, "carb": 0.0, "gord": 12.0, "nome": "Salmão Grelhado"},
    "whey": {"kcal": 393.0, "prot": 80.0, "carb": 6.7, "gord": 5.0, "nome": "Whey Protein"},
    "whey protein": {"kcal": 393.0, "prot": 80.0, "carb": 6.7, "gord": 5.0, "nome": "Whey Protein"},
    "whey isolado": {"kcal": 370.0, "prot": 88.0, "carb": 3.0, "gord": 1.5, "nome": "Whey Isolado"},
    "carne moida": {"kcal": 210.0, "prot": 26.0, "carb": 0.0, "gord": 11.0, "nome": "Carne Moída Grelhada"},
    "carne moída": {"kcal": 210.0, "prot": 26.0, "carb": 0.0, "gord": 11.0, "nome": "Carne Moída Grelhada"},
    "peito de peru": {"kcal": 109.0, "prot": 23.0, "carb": 0.0, "gord": 1.5, "nome": "Peito de Peru"},
    "iogurte grego": {"kcal": 97.0, "prot": 9.0, "carb": 3.6, "gord": 5.0, "nome": "Iogurte Grego Integral"},
    "iogurte natural": {"kcal": 61.0, "prot": 3.5, "carb": 4.7, "gord": 3.3, "nome": "Iogurte Natural Integral"},
    "cottage": {"kcal": 98.0, "prot": 11.1, "carb": 3.4, "gord": 4.3, "nome": "Queijo Cottage"},
    "atum em lata": {"kcal": 130.0, "prot": 29.0, "carb": 0.0, "gord": 1.0, "nome": "Atum em Água"},

    # ── Frutas (TACO — valores por 100g, crus) ────────────────────────────────
    "maca": {"kcal": 56.0, "prot": 0.3, "carb": 15.2, "gord": 0.2, "nome": "Maçã (crua)"},
    "maçã": {"kcal": 56.0, "prot": 0.3, "carb": 15.2, "gord": 0.2, "nome": "Maçã (crua)"},
    "maca gala": {"kcal": 56.0, "prot": 0.3, "carb": 15.2, "gord": 0.2, "nome": "Maçã Gala (crua)"},
    "maca verde": {"kcal": 56.0, "prot": 0.3, "carb": 15.2, "gord": 0.2, "nome": "Maçã Verde (crua)"},
    "banana": {"kcal": 89.0, "prot": 1.1, "carb": 22.8, "gord": 0.3, "nome": "Banana"},
    "banana prata": {"kcal": 98.0, "prot": 1.3, "carb": 26.0, "gord": 0.1, "nome": "Banana Prata"},
    "banana nanica": {"kcal": 92.0, "prot": 1.4, "carb": 23.8, "gord": 0.1, "nome": "Banana Nanica"},
    "abacate": {"kcal": 160.0, "prot": 2.0, "carb": 9.0, "gord": 15.0, "nome": "Abacate"},
    "manga": {"kcal": 64.0, "prot": 0.9, "carb": 16.9, "gord": 0.3, "nome": "Manga (crua)"},
    "mamao": {"kcal": 40.0, "prot": 0.5, "carb": 10.4, "gord": 0.1, "nome": "Mamão (cru)"},
    "mamão": {"kcal": 40.0, "prot": 0.5, "carb": 10.4, "gord": 0.1, "nome": "Mamão (cru)"},
    "morango": {"kcal": 30.0, "prot": 0.7, "carb": 7.0, "gord": 0.3, "nome": "Morango (cru)"},
    "uva": {"kcal": 67.0, "prot": 0.6, "carb": 17.2, "gord": 0.2, "nome": "Uva (crua)"},
    "uva passa": {"kcal": 299.0, "prot": 3.1, "carb": 79.0, "gord": 0.5, "nome": "Uva Passa"},
    "laranja": {"kcal": 47.0, "prot": 0.9, "carb": 11.7, "gord": 0.1, "nome": "Laranja (crua)"},
    "pera": {"kcal": 56.0, "prot": 0.4, "carb": 14.9, "gord": 0.1, "nome": "Pêra (crua)"},
    "pêra": {"kcal": 56.0, "prot": 0.4, "carb": 14.9, "gord": 0.1, "nome": "Pêra (crua)"},
    "melancia": {"kcal": 33.0, "prot": 0.6, "carb": 8.6, "gord": 0.2, "nome": "Melancia (crua)"},
    "melao": {"kcal": 31.0, "prot": 0.8, "carb": 7.6, "gord": 0.1, "nome": "Melão (cru)"},
    "melão": {"kcal": 31.0, "prot": 0.8, "carb": 7.6, "gord": 0.1, "nome": "Melão (cru)"},
    "abacaxi": {"kcal": 48.0, "prot": 0.9, "carb": 12.3, "gord": 0.1, "nome": "Abacaxi (cru)"},
    "kiwi": {"kcal": 61.0, "prot": 1.1, "carb": 14.7, "gord": 0.5, "nome": "Kiwi (cru)"},
    "limao": {"kcal": 38.0, "prot": 0.9, "carb": 9.4, "gord": 0.4, "nome": "Limão (cru)"},
    "limão": {"kcal": 38.0, "prot": 0.9, "carb": 9.4, "gord": 0.4, "nome": "Limão (cru)"},
    "mirtilo": {"kcal": 57.0, "prot": 0.7, "carb": 14.5, "gord": 0.3, "nome": "Mirtilo/Blueberry (cru)"},
    "blueberry": {"kcal": 57.0, "prot": 0.7, "carb": 14.5, "gord": 0.3, "nome": "Blueberry (cru)"},
    "goiaba": {"kcal": 54.0, "prot": 2.6, "carb": 9.9, "gord": 1.0, "nome": "Goiaba (crua)"},
    "coco": {"kcal": 354.0, "prot": 3.3, "carb": 15.2, "gord": 33.5, "nome": "Coco (cru)"},
    "acai": {"kcal": 247.0, "prot": 2.1, "carb": 6.2, "gord": 25.3, "nome": "Açaí (polpa)"},
    "açaí": {"kcal": 247.0, "prot": 2.1, "carb": 6.2, "gord": 25.3, "nome": "Açaí (polpa)"},
    "tâmara": {"kcal": 282.0, "prot": 2.5, "carb": 75.0, "gord": 0.4, "nome": "Tâmara (seca)"},
    "tamara": {"kcal": 282.0, "prot": 2.5, "carb": 75.0, "gord": 0.4, "nome": "Tâmara (seca)"},

    # ── Vegetais e Legumes (TACO) ──────────────────────────────────────────────
    "brocolis": {"kcal": 34.0, "prot": 2.8, "carb": 6.6, "gord": 0.4, "nome": "Brócolis Cozido"},
    "brócolis": {"kcal": 34.0, "prot": 2.8, "carb": 6.6, "gord": 0.4, "nome": "Brócolis Cozido"},
    "cenoura": {"kcal": 34.0, "prot": 0.9, "carb": 7.7, "gord": 0.2, "nome": "Cenoura Crua"},
    "abobrinha": {"kcal": 14.0, "prot": 0.7, "carb": 2.5, "gord": 0.1, "nome": "Abobrinha Cozida"},
    "espinafre": {"kcal": 20.0, "prot": 2.2, "carb": 1.5, "gord": 0.5, "nome": "Espinafre Cru"},
    "tomate": {"kcal": 18.0, "prot": 0.9, "carb": 3.9, "gord": 0.2, "nome": "Tomate Cru"},
    "alface": {"kcal": 11.0, "prot": 1.0, "carb": 1.7, "gord": 0.2, "nome": "Alface Crua"},
    "pepino": {"kcal": 13.0, "prot": 0.6, "carb": 2.4, "gord": 0.1, "nome": "Pepino Cru"},

    # ── Gorduras e Miscelâneas ────────────────────────────────────────────────
    "azeite": {"kcal": 884.0, "prot": 0.0, "carb": 0.0, "gord": 100.0, "nome": "Azeite de Oliva Extra Virgem"},
    "azeite de oliva": {"kcal": 884.0, "prot": 0.0, "carb": 0.0, "gord": 100.0, "nome": "Azeite de Oliva Extra Virgem"},
    "oleo de coco": {"kcal": 900.0, "prot": 0.0, "carb": 0.0, "gord": 100.0, "nome": "Óleo de Coco"},
    "manteiga": {"kcal": 717.0, "prot": 0.9, "carb": 0.1, "gord": 81.0, "nome": "Manteiga com Sal"},
    "pasta de amendoim": {"kcal": 588.0, "prot": 25.0, "carb": 20.0, "gord": 50.0, "nome": "Pasta de Amendoim"},
    "amendoim": {"kcal": 567.0, "prot": 25.8, "carb": 16.1, "gord": 49.2, "nome": "Amendoim Torrado"},
    "castanha do para": {"kcal": 656.0, "prot": 14.3, "carb": 12.3, "gord": 66.4, "nome": "Castanha-do-Pará"},
    "castanha de caju": {"kcal": 574.0, "prot": 15.3, "carb": 32.7, "gord": 46.4, "nome": "Castanha de Caju"},
    "amendo": {"kcal": 579.0, "prot": 21.2, "carb": 21.6, "gord": 49.9, "nome": "Amêndoa"},
    "nozes": {"kcal": 654.0, "prot": 15.2, "carb": 13.7, "gord": 65.2, "nome": "Nozes"},
    "queijo": {"kcal": 320.0, "prot": 23.0, "carb": 1.5, "gord": 25.0, "nome": "Queijo Muçarela/Prato"},
    "queijo prato": {"kcal": 350.0, "prot": 23.0, "carb": 1.0, "gord": 28.0, "nome": "Queijo Prato"},
    "queijo mucarela": {"kcal": 300.0, "prot": 22.0, "carb": 2.0, "gord": 22.0, "nome": "Queijo Muçarela"},
    "queijo muçarela": {"kcal": 300.0, "prot": 22.0, "carb": 2.0, "gord": 22.0, "nome": "Queijo Muçarela"},
    "queijo minas": {"kcal": 264.0, "prot": 17.4, "carb": 3.0, "gord": 20.2, "nome": "Queijo Minas Padrão"},
    "requeijao": {"kcal": 261.0, "prot": 8.7, "carb": 4.9, "gord": 23.0, "nome": "Requeijão Cremoso"},
    "leite": {"kcal": 61.0, "prot": 3.2, "carb": 4.7, "gord": 3.3, "nome": "Leite Integral"},
    "leite desnatado": {"kcal": 35.0, "prot": 3.4, "carb": 5.0, "gord": 0.1, "nome": "Leite Desnatado"},
    "mel": {"kcal": 304.0, "prot": 0.3, "carb": 82.4, "gord": 0.0, "nome": "Mel"},
    "acucar": {"kcal": 387.0, "prot": 0.0, "carb": 99.9, "gord": 0.0, "nome": "Açúcar Refinado"},
    "chocolate 70": {"kcal": 556.0, "prot": 8.3, "carb": 44.2, "gord": 42.6, "nome": "Chocolate 70% Cacau"},
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
    """
    Busca o ingrediente na tabela local de alimentos comuns.
    1. Correspondência exata após normalização (sem acento, minúsculas).
    2. Correspondência parcial: chave normalizada contida no nome ou vice-versa.
    Retorna o resultado mais específico (chave mais longa = mais precisa).
    """
    norm = normalizar_nome(nome)

    # 1. Correspondência exata da chave normalizada
    if norm in TABELA_ALIMENTOS_LOCAL:
        return TABELA_ALIMENTOS_LOCAL[norm]

    # 2. Pré-computa chaves normalizadas uma única vez
    normed_keys = [(normalizar_nome(k), v) for k, v in TABELA_ALIMENTOS_LOCAL.items()]

    # 3. Correspondência exata após normalizar a chave (ex: "feijão" → "feijao")
    for nk, values in normed_keys:
        if nk == norm:
            return values

    # 4. Correspondência parcial — prefere chave mais longa (mais específica)
    matches = []
    for nk, values in normed_keys:
        if nk and (nk in norm or norm in nk):
            matches.append((len(nk), values))
    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[0][1]

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
        f"Decomponha a seguinte refeição em seus ingredientes e pesos individuais: '{descricao}'.\n\n"
        "REGRAS OBRIGATÓRIAS:\n"
        "1. Converta medidas caseiras para gramas usando esta tabela de referência:\n"
        "   - 1 maçã pequena -> 120g | 1 maçã média -> 160g | 1 maçã grande -> 200g\n"
        "   - 1 banana pequena -> 80g | 1 banana média -> 100g | 1 banana grande -> 130g\n"
        "   - 1 laranja média -> 130g | 1 pera média -> 150g | 1 manga -> 200g\n"
        "   - 1 fatia de melancia -> 300g | 1 kiwi -> 80g | 1 morango -> 12g\n"
        "   - 1 ovo inteiro -> 50g | 1 clara de ovo -> 30g\n"
        "   - 1 colher (sopa) de azeite -> 12g | 1 colher (sopa) de manteiga -> 15g\n"
        "   - 1 fatia de pão de forma -> 25g | 1 pão francês -> 50g\n"
        "   - 1 concha de feijão -> 100g | 1 colher (sopa) de arroz -> 25g\n"
        "   - 1 scoop de whey (30g) -> 30g | 1 copo de leite (200ml) -> 200g\n"
        "2. 'ingrediente_en' deve ser a tradução EXATA do alimento cru/básico para inglês,\n"
        "   SEM processos (ex: 'apple raw', 'grilled chicken breast', 'cooked white rice').\n"
        "   NUNCA traduza como preparação processada (ex: apple pie, apple sauce).\n"
        "3. Se não tiver certeza do peso exato, use o peso médio típico para a unidade mencionada.\n\n"
        "Retorne APENAS um JSON no seguinte formato de array (sem markdown, sem bloco de código ```json):\n"
        "[\n"
        "  {\n"
        '    "ingrediente": "<nome do ingrediente em portugues>",\n'
        '    "ingrediente_en": "<traducao para ingles — alimento basico/cru>",\n'
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

        # 1. Tabela local (TACO/USDA pré-verificados — sempre preferir)
        dados = lookup_local(nome)
        fonte = "LOCAL"

        # 2. USDA fallback — só usa se local não encontrou
        if not dados and nome_en:
            dados_usda = buscar_usda(nome_en)
            if dados_usda:
                # Verificação de plausibilidade: valores extremamente altos para
                # alimentos integrais indicam item errado no banco (ex: "apple strudel"
                # ao invés de "apple raw"). Limite conservador: 500 kcal/100g só para
                # óleos e nuts é esperado; para frutas/carnes, max ~250 kcal.
                kcal_usda = dados_usda.get("kcal", 0)
                nome_lower = normalizar_nome(nome)
                _frutas_kw = {"maca", "banana", "manga", "mamao", "morango", "uva",
                              "laranja", "pera", "melancia", "melao", "abacaxi", "kiwi",
                              "goiaba", "mirtilo", "blueberry"}
                _is_fruta = any(kw in nome_lower for kw in _frutas_kw)
                _limite = 150.0 if _is_fruta else 500.0
                if kcal_usda > _limite:
                    # USDA retornou item suspeito — descarta e usa IA
                    dados_usda = None
                else:
                    dados_usda["nome"] = nome.strip().capitalize()
                    dados = dados_usda
                    fonte = "USDA"

        # 3. IA fallback (densidade 100g) — último recurso
        if not dados:
            dados = estimar_densidade_ia(model, nome)
            fonte = "IA"

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
