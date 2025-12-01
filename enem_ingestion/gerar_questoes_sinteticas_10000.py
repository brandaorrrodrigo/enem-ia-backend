#!/usr/bin/env python3
"""
==============================================
GERAR 10,000 QUESTÕES SINTÉTICAS/SIMULADAS
==============================================

Generates 10,000 fully synthetic ENEM-style questions using
template-based generation with extensive randomization.

Output: questoes_simuladas_10000.json
"""

import json
import random
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


# ============================================================================
# CONFIG
# ============================================================================

TARGET_QUESTIONS = 10000
OUTPUT_FILE = Path(__file__).parent / "questoes_simuladas_10000.json"


# ============================================================================
# DATA BANKS
# ============================================================================

NOMES = [
    "João", "Maria", "Pedro", "Ana", "Carlos", "Juliana", "Lucas", "Fernanda",
    "Rafael", "Camila", "Thiago", "Beatriz", "Gabriel", "Larissa", "Felipe"
]

CIDADES = [
    "São Paulo", "Rio de Janeiro", "Brasília", "Salvador", "Fortaleza",
    "Belo Horizonte", "Manaus", "Curitiba", "Recife", "Porto Alegre"
]

PRODUTOS = [
    "computadores", "celulares", "tablets", "televisores", "geladeiras",
    "carros", "motos", "bicicletas", "livros", "roupas"
]

ANIMAIS = [
    "gatos", "cachorros", "aves", "peixes", "cavalos", "vacas", "ovelhas"
]

PLANTAS = [
    "árvores", "flores", "arbustos", "gramíneas", "cactos", "samambaias"
]


# ============================================================================
# GENERATORS - MATEMÁTICA
# ============================================================================

def gerar_matematica_basica() -> Dict[str, Any]:
    """Generate basic math question."""
    a = random.randint(10, 100)
    b = random.randint(5, 50)
    op = random.choice(['+', '-', '*'])

    if op == '+':
        resultado = a + b
        enunciado = f"Calcule: {a} + {b}"
    elif op == '-':
        resultado = a - b
        enunciado = f"Calcule: {a} - {b}"
    else:
        resultado = a * b
        enunciado = f"Calcule: {a} × {b}"

    # Generate wrong alternatives
    alternativas_valores = [
        resultado,
        resultado + random.randint(1, 10),
        resultado - random.randint(1, 10),
        resultado + random.randint(11, 20),
        resultado - random.randint(11, 20),
    ]
    random.shuffle(alternativas_valores)

    alternativas = {
        'A': str(alternativas_valores[0]),
        'B': str(alternativas_valores[1]),
        'C': str(alternativas_valores[2]),
        'D': str(alternativas_valores[3]),
        'E': str(alternativas_valores[4]),
    }

    # Find correct answer
    correta = None
    for letra, valor in alternativas.items():
        if int(valor) == resultado:
            correta = letra
            break

    return {
        'enunciado': enunciado,
        'alternativas': alternativas,
        'correta': correta or 'A',
    }


def gerar_matematica_porcentagem() -> Dict[str, Any]:
    """Generate percentage question."""
    valor = random.randint(100, 1000)
    percentual = random.choice([10, 15, 20, 25, 30, 40, 50])
    tipo = random.choice(['desconto', 'aumento'])

    if tipo == 'desconto':
        resultado = valor * (1 - percentual/100)
        enunciado = f"Um produto custa R$ {valor},00. Com {percentual}% de desconto, qual será o novo preço?"
    else:
        resultado = valor * (1 + percentual/100)
        enunciado = f"Um produto custa R$ {valor},00. Com aumento de {percentual}%, qual será o novo preço?"

    alternativas_valores = [
        resultado,
        resultado + random.uniform(10, 50),
        resultado - random.uniform(10, 50),
        valor,  # Pegadinha: valor original
        valor * percentual / 100,  # Pegadinha: apenas o desconto
    ]
    random.shuffle(alternativas_valores)

    alternativas = {letra: f"R$ {valor:.2f}" for letra, valor in zip(['A','B','C','D','E'], alternativas_valores)}

    correta = None
    for letra, valor_str in alternativas.items():
        valor_num = float(valor_str.replace('R$ ', '').replace(',', '.'))
        if abs(valor_num - resultado) < 0.1:
            correta = letra
            break

    return {
        'enunciado': enunciado,
        'alternativas': alternativas,
        'correta': correta or 'A',
    }


def gerar_matematica_geometria() -> Dict[str, Any]:
    """Generate geometry question."""
    tipo = random.choice(['triangulo', 'retangulo', 'circulo'])

    if tipo == 'triangulo':
        base = random.randint(5, 20)
        altura = random.randint(5, 20)
        area = (base * altura) / 2
        enunciado = f"Um triângulo possui base de {base} cm e altura de {altura} cm. Qual é sua área?"
        unidade = "cm²"

    elif tipo == 'retangulo':
        largura = random.randint(5, 20)
        comprimento = random.randint(10, 30)
        area = largura * comprimento
        enunciado = f"Um retângulo possui largura de {largura} m e comprimento de {comprimento} m. Qual é sua área?"
        unidade = "m²"

    else:  # circulo
        raio = random.randint(3, 15)
        area = 3.14 * raio ** 2
        enunciado = f"Um círculo possui raio de {raio} cm. Qual é sua área aproximada? (use π = 3,14)"
        unidade = "cm²"

    alternativas_valores = [
        area,
        area * 2,
        area / 2,
        area + random.uniform(10, 30),
        area - random.uniform(10, 30),
    ]
    random.shuffle(alternativas_valores)

    alternativas = {letra: f"{valor:.1f} {unidade}" for letra, valor in zip(['A','B','C','D','E'], alternativas_valores)}

    correta = None
    for letra, valor_str in alternativas.items():
        valor_num = float(valor_str.split()[0])
        if abs(valor_num - area) < 1:
            correta = letra
            break

    return {
        'enunciado': enunciado,
        'alternativas': alternativas,
        'correta': correta or 'A',
    }


# ============================================================================
# GENERATORS - FÍSICA
# ============================================================================

def gerar_fisica_mru() -> Dict[str, Any]:
    """Generate MRU question."""
    distancia = random.randint(100, 500)
    tempo = random.randint(2, 10)
    velocidade = distancia / tempo

    enunciado = f"Um veículo percorre {distancia} km em {tempo} horas. Qual é sua velocidade média?"

    alternativas_valores = [
        velocidade,
        velocidade + random.uniform(5, 15),
        velocidade - random.uniform(5, 15),
        distancia,  # Pegadinha
        tempo,  # Pegadinha
    ]
    random.shuffle(alternativas_valores)

    alternativas = {letra: f"{valor:.1f} km/h" for letra, valor in zip(['A','B','C','D','E'], alternativas_valores)}

    correta = None
    for letra, valor_str in alternativas.items():
        valor_num = float(valor_str.split()[0])
        if abs(valor_num - velocidade) < 0.5:
            correta = letra
            break

    return {
        'enunciado': enunciado,
        'alternativas': alternativas,
        'correta': correta or 'A',
    }


def gerar_fisica_energia() -> Dict[str, Any]:
    """Generate energy question."""
    massa = random.randint(2, 50)
    altura = random.randint(5, 100)
    g = 10
    energia = massa * g * altura

    enunciado = f"Um objeto de {massa} kg está a {altura} m de altura. Qual é sua energia potencial gravitacional? (g = 10 m/s²)"

    alternativas_valores = [
        energia,
        energia * 2,
        energia / 2,
        massa * altura,  # Pegadinha: esqueceu g
        massa * g,  # Pegadinha: esqueceu altura
    ]
    random.shuffle(alternativas_valores)

    alternativas = {letra: f"{int(valor)} J" for letra, valor in zip(['A','B','C','D','E'], alternativas_valores)}

    correta = None
    for letra, valor_str in alternativas.items():
        valor_num = int(valor_str.split()[0])
        if valor_num == energia:
            correta = letra
            break

    return {
        'enunciado': enunciado,
        'alternativas': alternativas,
        'correta': correta or 'A',
    }


# ============================================================================
# GENERATORS - QUÍMICA
# ============================================================================

def gerar_quimica_mol() -> Dict[str, Any]:
    """Generate mol question."""
    massa = random.randint(10, 200)
    massa_molar = random.choice([12, 16, 1, 14, 32])  # C, O, H, N, S
    elemento = {12: 'Carbono (C)', 16: 'Oxigênio (O)', 1: 'Hidrogênio (H)', 14: 'Nitrogênio (N)', 32: 'Enxofre (S)'}[massa_molar]

    mols = massa / massa_molar

    enunciado = f"Quantos mols existem em {massa} g de {elemento}? (Massa molar: {massa_molar} g/mol)"

    alternativas_valores = [
        mols,
        mols * 2,
        mols / 2,
        massa,  # Pegadinha
        massa_molar,  # Pegadinha
    ]
    random.shuffle(alternativas_valores)

    alternativas = {letra: f"{valor:.2f} mol" for letra, valor in zip(['A','B','C','D','E'], alternativas_valores)}

    correta = None
    for letra, valor_str in alternativas.items():
        valor_num = float(valor_str.split()[0])
        if abs(valor_num - mols) < 0.1:
            correta = letra
            break

    return {
        'enunciado': enunciado,
        'alternativas': alternativas,
        'correta': correta or 'A',
    }


# ============================================================================
# GENERATORS - PORTUGUÊS
# ============================================================================

def gerar_portugues_interpretacao() -> Dict[str, Any]:
    """Generate interpretation question."""
    conjuncao = random.choice([
        ('porém', 'Adversidade'),
        ('e', 'Adição'),
        ('portanto', 'Conclusão'),
        ('porque', 'Causa'),
        ('como', 'Comparação'),
    ])

    enunciado = f"Na frase: 'A tecnologia avançou muito, {conjuncao[0]} trouxe novos desafios.' A palavra '{conjuncao[0]}' expressa:"

    alternativas = {
        'A': "Adição",
        'B': "Adversidade",
        'C': "Causa",
        'D': "Conclusão",
        'E': "Comparação",
    }

    correta = None
    for letra, valor in alternativas.items():
        if valor == conjuncao[1]:
            correta = letra
            break

    return {
        'enunciado': enunciado,
        'alternativas': alternativas,
        'correta': correta or 'B',
    }


# ============================================================================
# MAIN GENERATOR
# ============================================================================

GENERATORS = {
    'matematica': [
        gerar_matematica_basica,
        gerar_matematica_porcentagem,
        gerar_matematica_geometria,
    ],
    'fisica': [
        gerar_fisica_mru,
        gerar_fisica_energia,
    ],
    'quimica': [
        gerar_quimica_mol,
    ],
    'portugues': [
        gerar_portugues_interpretacao,
    ],
}


def criar_hash_questao(enunciado: str, alternativas: Dict[str, str]) -> str:
    """Create unique hash."""
    texto = enunciado.lower().strip()
    alt_sorted = sorted(alternativas.values())
    texto += ''.join(alt_sorted)
    return hashlib.md5(texto.encode('utf-8')).hexdigest()


def inferir_area(disciplina: str) -> str:
    """Map discipline to area."""
    if disciplina in ['matematica']:
        return 'matematica'
    if disciplina in ['fisica', 'quimica', 'biologia']:
        return 'ciencias_natureza'
    if disciplina in ['portugues', 'literatura', 'ingles']:
        return 'linguagens'
    return 'ciencias_humanas'


def gerar_questoes_sinteticas(target: int = TARGET_QUESTIONS) -> List[Dict[str, Any]]:
    """Generate synthetic questions."""
    print(f"\n🔄 Gerando {target} questões sintéticas...")

    questoes = []
    hashes_vistos = set()
    duplicatas = 0

    disciplinas = list(GENERATORS.keys())

    tentativas = 0
    while len(questoes) < target and tentativas < target * 2:
        tentativas += 1

        # Random discipline
        disciplina = random.choice(disciplinas)
        generator_func = random.choice(GENERATORS[disciplina])

        try:
            data = generator_func()

            questao = {
                'numero': random.randint(1, 300),
                'ano': random.randint(2023, 2025),
                'disciplina': disciplina,
                'enunciado': data['enunciado'],
                'alternativas': data['alternativas'],
                'correta': data['correta'],
                'habilidade': f"H{random.randint(1,30)}",
                'competencia': random.randint(1,7),
                'explicacao': f"Questão simulada de {disciplina}",
                'source': 'simulada',
                'area': inferir_area(disciplina),
                'difficulty': random.randint(1, 5),
            }

            # Check duplicates
            hash_q = criar_hash_questao(questao['enunciado'], questao['alternativas'])

            if hash_q in hashes_vistos:
                duplicatas += 1
                continue

            hashes_vistos.add(hash_q)
            questoes.append(questao)

            if len(questoes) % 500 == 0:
                print(f"   ✅ {len(questoes)}/{target} geradas")

        except Exception as e:
            print(f"   ⚠️  Erro: {e}")
            continue

    return questoes


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main function."""
    print("="*70)
    print("GERADOR DE 10,000 QUESTÕES SINTÉTICAS/SIMULADAS")
    print("="*70)

    # Generate
    questoes = gerar_questoes_sinteticas(TARGET_QUESTIONS)

    # Create output
    output_data = {
        'versao': '1.0',
        'total_questoes': len(questoes),
        'gerado_em': datetime.now().isoformat(),
        'source': 'questoes_simuladas',
        'target': TARGET_QUESTIONS,
        'questoes': questoes
    }

    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Summary
    print("\n" + "="*70)
    print("📊 RESUMO FINAL")
    print("="*70)
    print(f"Target:                {TARGET_QUESTIONS}")
    print(f"Questões geradas:      {len(questoes)}")
    print(f"\n✅ Arquivo salvo: {OUTPUT_FILE}")
    print("="*70)


if __name__ == '__main__':
    main()
