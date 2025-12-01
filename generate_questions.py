"""
=============================================================================
GERADOR DE QUESTÕES ENEM COM IA - CLAUDE ANTHROPIC
=============================================================================

INSTALAÇÃO:
-----------
pip install anthropic python-dotenv tqdm

CONFIGURAÇÃO:
------------
1. Crie um arquivo .env na mesma pasta deste script com:
   ANTHROPIC_API_KEY=sua_chave_aqui

2. Ou exporte a variável de ambiente:
   export ANTHROPIC_API_KEY=sua_chave_aqui

COMO USAR:
----------
python generate_questions.py

CONFIGURAÇÃO DE QUANTIDADE:
---------------------------
Edite as variáveis no final do script:
- QUESTOES_POR_LOTE: quantas questões gerar por chamada à API (5-10 recomendado)
- TOTAL_DE_LOTES: quantas vezes chamar a API (100 = 1000 questões se lote=10)

EXEMPLO:
--------
QUESTOES_POR_LOTE = 10
TOTAL_DE_LOTES = 100
= 1000 questões geradas

SAÍDA:
------
Arquivo: questoes_enem_ia.jsonl
Formato: Uma questão JSON por linha (JSONL)

=============================================================================
"""

import os
import json
import time
import random
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

try:
    import anthropic
    from dotenv import load_dotenv
    from tqdm import tqdm
except ImportError as e:
    print("❌ ERRO: Dependências não instaladas.")
    print("Execute: pip install anthropic python-dotenv tqdm")
    exit(1)

# Carregar variáveis de ambiente
load_dotenv()

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ERRO: ANTHROPIC_API_KEY não encontrada!")
    print("Configure no arquivo .env ou como variável de ambiente.")
    exit(1)

OUTPUT_FILE = "questoes_enem_ia.jsonl"
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos

# =============================================================================
# TAXONOMIA: ÁREAS, DISCIPLINAS E ASSUNTOS
# =============================================================================

TAXONOMIA = {
    "Matemática": {
        "disciplina": "Matemática",
        "assuntos": [
            "Função afim", "Função quadrática", "Função exponencial", "Função logarítmica",
            "Progressão aritmética", "Progressão geométrica", "Porcentagem", "Razão e proporção",
            "Regra de três", "Análise combinatória", "Probabilidade", "Estatística básica",
            "Geometria plana", "Geometria espacial", "Trigonometria", "Áreas e volumes",
            "Equações do 1º grau", "Equações do 2º grau", "Sistemas lineares", "Matrizes",
        ]
    },
    "Ciências da Natureza": {
        "Física": [
            "Cinemática", "Dinâmica", "Energia mecânica", "Trabalho e potência",
            "Hidrostática", "Termodinâmica", "Óptica geométrica", "Ondulatória",
            "Eletrostática", "Eletrodinâmica", "Magnetismo", "Física moderna",
        ],
        "Química": [
            "Estrutura atômica", "Tabela periódica", "Ligações químicas", "Funções inorgânicas",
            "Reações químicas", "Estequiometria", "Soluções", "Termoquímica",
            "Cinética química", "Equilíbrio químico", "Eletroquímica", "Química orgânica",
            "pH e pOH", "Oxidação e redução",
        ],
        "Biologia": [
            "Citologia", "Genética", "Evolução", "Ecologia",
            "Fisiologia humana", "Botânica", "Zoologia", "Microbiologia",
            "Biotecnologia", "Imunologia", "Parasitologia", "Taxonomia",
        ]
    },
    "Ciências Humanas": {
        "História": [
            "Brasil colonial", "Brasil império", "República velha", "Era Vargas",
            "Ditadura militar", "Redemocratização", "Idade média", "Renascimento",
            "Iluminismo", "Revoluções industriais", "Primeira Guerra", "Segunda Guerra",
            "Guerra Fria", "Descolonização africana",
        ],
        "Geografia": [
            "Geologia", "Relevo", "Clima", "Hidrografia",
            "Biomas brasileiros", "Urbanização", "Industrialização", "Agropecuária",
            "Globalização", "Geopolítica", "Demografia", "Cartografia",
            "Impactos ambientais", "Desenvolvimento sustentável",
        ],
        "Sociologia": [
            "Cultura", "Diversidade cultural", "Movimentos sociais", "Cidadania",
            "Direitos humanos", "Desigualdade social", "Classes sociais", "Política",
            "Estado e governo", "Democracia", "Ideologias políticas", "Trabalho",
        ],
        "Filosofia": [
            "Ética", "Moral", "Política", "Epistemologia",
            "Filosofia antiga", "Filosofia medieval", "Filosofia moderna", "Filosofia contemporânea",
            "Lógica", "Estética", "Metafísica", "Teoria do conhecimento",
        ]
    },
    "Linguagens": {
        "Português": [
            "Interpretação de texto", "Gêneros textuais", "Figuras de linguagem", "Funções da linguagem",
            "Variação linguística", "Sintaxe", "Concordância verbal", "Concordância nominal",
            "Regência verbal", "Regência nominal", "Crase", "Pontuação",
            "Ortografia", "Semântica", "Literatura brasileira", "Escolas literárias",
        ],
        "Inglês": [
            "Interpretação de texto", "Vocabulário", "Gramática básica", "Tempos verbais",
            "Phrasal verbs", "Linking words", "Comparative", "Superlative",
        ],
        "Artes": [
            "Arte brasileira", "Movimentos artísticos", "Arte contemporânea", "Arte africana",
            "Arte indígena", "Arquitetura", "Música", "Teatro",
        ]
    }
}

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def get_random_subject() -> Dict[str, str]:
    """Sorteia área, disciplina e assunto aleatoriamente"""
    area = random.choice(list(TAXONOMIA.keys()))

    if area == "Matemática":
        disciplina = "Matemática"
        assunto = random.choice(TAXONOMIA[area]["assuntos"])
    else:
        disciplinas_dict = {k: v for k, v in TAXONOMIA[area].items() if k != "disciplina"}
        disciplina = random.choice(list(disciplinas_dict.keys()))
        assunto = random.choice(disciplinas_dict[disciplina])

    dificuldade = random.choice(["fácil", "média", "difícil"])

    return {
        "area": area,
        "disciplina": disciplina,
        "assunto": assunto,
        "dificuldade": dificuldade
    }

def create_prompt(questoes_por_lote: int) -> str:
    """Cria o prompt para o Claude gerar as questões"""

    specs = [get_random_subject() for _ in range(questoes_por_lote)]

    especificacoes = "\n".join([
        f"{i+1}. Área: {s['area']}, Disciplina: {s['disciplina']}, Assunto: {s['assunto']}, Dificuldade: {s['dificuldade']}"
        for i, s in enumerate(specs)
    ])

    prompt = f"""Você é um especialista em criar questões estilo ENEM (Exame Nacional do Ensino Médio do Brasil).

GERE EXATAMENTE {questoes_por_lote} QUESTÕES seguindo estas especificações:

{especificacoes}

REGRAS OBRIGATÓRIAS:

1. ESTILO ENEM:
   - Texto de apoio contextualizado (notícia, gráfico descrito, situação do cotidiano)
   - Enunciado claro perguntando o que deve ser resolvido
   - 5 alternativas (A, B, C, D, E)
   - Apenas 1 correta
   - Português formal e culto

2. ESTRUTURA JSON DE CADA QUESTÃO:
{{
  "area": "string",
  "disciplina": "string",
  "assunto": "string",
  "dificuldade": "fácil|média|difícil",
  "enunciado": "Texto completo da pergunta",
  "texto_apoio": "Texto de contexto (se houver, senão vazio)",
  "alternativas": {{
    "A": "texto alternativa A",
    "B": "texto alternativa B",
    "C": "texto alternativa C",
    "D": "texto alternativa D",
    "E": "texto alternativa E"
  }},
  "correta": "A|B|C|D|E",
  "explicacao": "Explicação detalhada passo a passo de como resolver e por que a correta está certa",
  "fonte": "IA_ENEMIA",
  "ano_referencia": null
}}

3. QUALIDADE:
   - Questões INÉDITAS, apenas inspiradas no estilo ENEM
   - Alternativas plausíveis (não óbvias demais)
   - Explicação pedagógica e detalhada
   - Contexto realista e atual

4. FORMATO DE SAÍDA:
   - APENAS JSON PURO, um objeto por linha (JSONL)
   - SEM markdown, SEM ```json, SEM explicações extras
   - CADA LINHA = UM OBJETO JSON VÁLIDO
   - {questoes_por_lote} linhas no total

RETORNE AGORA AS {questoes_por_lote} QUESTÕES EM JSONL:"""

    return prompt

def validate_question(q: Dict) -> bool:
    """Valida se a questão tem todos os campos necessários"""
    required_fields = [
        "area", "disciplina", "assunto", "dificuldade",
        "enunciado", "texto_apoio", "alternativas", "correta",
        "explicacao", "fonte", "ano_referencia"
    ]

    if not all(field in q for field in required_fields):
        return False

    if not isinstance(q["alternativas"], dict):
        return False

    if set(q["alternativas"].keys()) != {"A", "B", "C", "D", "E"}:
        return False

    if q["correta"] not in ["A", "B", "C", "D", "E"]:
        return False

    return True

# =============================================================================
# FUNÇÃO PRINCIPAL DE GERAÇÃO
# =============================================================================

def generate_questions_batch(
    client: anthropic.Anthropic,
    questoes_por_lote: int,
    retry: int = 0
) -> List[Dict]:
    """Gera um lote de questões usando a API do Claude"""

    try:
        prompt = create_prompt(questoes_por_lote)

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            temperature=1.0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text.strip()

        # Parse JSONL
        questoes = []
        for line in response_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Remover markdown se existir
            if line.startswith('```'):
                continue

            try:
                q = json.loads(line)
                if validate_question(q):
                    questoes.append(q)
                else:
                    print(f"⚠️  Questão inválida ignorada (faltam campos)")
            except json.JSONDecodeError:
                print(f"⚠️  Linha JSON inválida ignorada")
                continue

        return questoes

    except anthropic.RateLimitError:
        if retry < MAX_RETRIES:
            print(f"⏳ Rate limit atingido. Aguardando {RETRY_DELAY * (retry + 1)}s...")
            time.sleep(RETRY_DELAY * (retry + 1))
            return generate_questions_batch(client, questoes_por_lote, retry + 1)
        else:
            print(f"❌ Rate limit - máximo de tentativas atingido")
            return []

    except anthropic.APIError as e:
        if retry < MAX_RETRIES:
            print(f"⚠️  Erro na API (tentativa {retry + 1}/{MAX_RETRIES}): {e}")
            time.sleep(RETRY_DELAY)
            return generate_questions_batch(client, questoes_por_lote, retry + 1)
        else:
            print(f"❌ Erro na API após {MAX_RETRIES} tentativas: {e}")
            return []

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return []

# =============================================================================
# EXECUÇÃO PRINCIPAL
# =============================================================================

def main(questoes_por_lote: int, total_de_lotes: int):
    """Função principal que orquestra a geração de todas as questões"""

    print("=" * 80)
    print("🎓 GERADOR DE QUESTÕES ENEM COM IA - CLAUDE ANTHROPIC")
    print("=" * 80)
    print(f"\n📋 Configuração:")
    print(f"   - Questões por lote: {questoes_por_lote}")
    print(f"   - Total de lotes: {total_de_lotes}")
    print(f"   - Total de questões: {questoes_por_lote * total_de_lotes}")
    print(f"   - Arquivo de saída: {OUTPUT_FILE}")
    print()

    # Inicializar cliente
    client = anthropic.Anthropic(api_key=API_KEY)

    # Criar ou limpar arquivo de saída
    output_path = Path(OUTPUT_FILE)
    if output_path.exists():
        resposta = input(f"⚠️  O arquivo {OUTPUT_FILE} já existe. Deseja:\n"
                        f"  [1] Sobrescrever\n"
                        f"  [2] Adicionar no final\n"
                        f"  [3] Cancelar\n"
                        f"Escolha (1/2/3): ")
        if resposta == "3":
            print("❌ Operação cancelada.")
            return
        elif resposta == "1":
            output_path.unlink()
            print("✅ Arquivo será sobrescrito.")
        else:
            print("✅ Novas questões serão adicionadas ao final.")

    # Gerar questões em lotes
    total_geradas = 0
    total_validas = 0

    print(f"\n🚀 Iniciando geração...\n")

    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        for lote_num in tqdm(range(1, total_de_lotes + 1), desc="Progresso"):
            questoes = generate_questions_batch(client, questoes_por_lote)

            total_geradas += len(questoes)

            for q in questoes:
                f.write(json.dumps(q, ensure_ascii=False) + '\n')
                total_validas += 1

            # Pequeno delay entre chamadas
            if lote_num < total_de_lotes:
                time.sleep(1)

    print(f"\n{'=' * 80}")
    print(f"✅ GERAÇÃO CONCLUÍDA!")
    print(f"{'=' * 80}")
    print(f"📊 Estatísticas:")
    print(f"   - Lotes processados: {total_de_lotes}")
    print(f"   - Questões válidas geradas: {total_validas}")
    print(f"   - Taxa de sucesso: {(total_validas / (questoes_por_lote * total_de_lotes)) * 100:.1f}%")
    print(f"   - Arquivo salvo em: {output_path.absolute()}")
    print()
    print(f"💡 Próximo passo: Importar para o banco de dados")
    print(f"   Use o script de importação do Prisma para carregar o JSONL no banco.")
    print()

# =============================================================================
# CONFIGURAÇÃO DE EXECUÇÃO
# =============================================================================

if __name__ == "__main__":
    # =========================================================================
    # 🎯 CONFIGURE AQUI A QUANTIDADE DE QUESTÕES
    # =========================================================================

    QUESTOES_POR_LOTE = 5    # Quantas questões por chamada à API (5-10 recomendado)
    TOTAL_DE_LOTES = 2       # Quantas vezes chamar a API

    # TOTAL DE QUESTÕES = QUESTOES_POR_LOTE x TOTAL_DE_LOTES
    # Exemplo: 10 x 100 = 1000 questões

    # =========================================================================

    main(QUESTOES_POR_LOTE, TOTAL_DE_LOTES)
