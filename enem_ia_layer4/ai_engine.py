
import os
import json
import http.client
from typing import Dict, Optional, Any

# Tenta usar Ollama local (http://localhost:11434). Se não estiver disponível, cai em fallback determinístico.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

def _ollama_generate(prompt: str, temperature: float = 0.3, max_tokens: int = 512) -> Optional[str]:
    try:
        conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=10)
        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        })
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/generate", payload, headers)
        res = conn.getresponse()
        if res.status != 200:
            return None
        data = res.read().decode("utf-8")
        obj = json.loads(data)
        return obj.get("response")
    except Exception:
        return None

# ---------------------- Explicação Base ----------------------

def explain_with_ai(enunciado: str,
                    alternativas: Dict[str, str],
                    resposta_usuario: Optional[int],
                    correta: Optional[int]) -> str:
    """Gera explicação detalhada. Usa Ollama se houver; caso contrário retorna template didático."""
    # Monta um prompt claro
    alt_text = "\n".join([f"{k}) {v}" for k, v in alternativas.items()]) if alternativas else ""
    user_choice = f"Resposta do aluno: alternativa índice {resposta_usuario}" if resposta_usuario is not None else "Sem resposta do aluno."
    correct_info = f"Alternativa correta (índice): {correta}" if correta is not None else "Gabarito não informado."

    prompt = f"""
Você é um tutor paciente e claro. Explique a questão abaixo em detalhes, com passos e justificativas.
Questão:
{enunciado}

Alternativas:
{alt_text}

{user_choice}
{correct_info}

Formato da resposta:
1) Releitura do enunciado em linguagem simples
2) Identificação das informações importantes
3) Passo a passo para chegar à resposta
4) Onde o aluno possivelmente errou (se aplicável)
5) Dica prática para memorizar
6) Resumo em 2 linhas
"""

    gen = _ollama_generate(prompt)
    if gen:
        return gen.strip()

    # Fallback determinístico (sem Ollama)
    base = [
        "1) Em outras palavras, a questão pede que identifiquemos as informações-chave e apliquemos o conceito correto.",
        "2) O que importa: variáveis, relações entre grandezas e o que se quer descobrir.",
        "3) Passo a passo: isolar dados, escolher a fórmula/ideia central, aplicar de forma sequencial.",
        "4) Erros comuns: confundir unidades, pular etapas, não verificar se o resultado faz sentido.",
        "5) Dica: imagine um exemplo simples da vida real e compare com a lógica da questão.",
        "6) Em resumo: foque no que a questão pede, use o conceito certo e valide o resultado."
    ]
    return "\n".join(base)

# ---------------------- Simplificação Progressiva ----------------------

def simplify_explanation_with_ai(base_explication: str,
                                 enunciado: str,
                                 alternativas: Dict[str, str],
                                 nivel: int) -> str:
    """
    Simplifica a explicação: nível 2 (mais simples), nível 3 (analogias), nível 4 (exemplo da vida real).
    Usa Ollama se disponível; caso contrário, usa templates.
    """
    nivel = max(2, min(nivel, 4))

    prompt = f"""
Simplifique a explicação a seguir para o NÍVEL {nivel}.
- Nível 2: linguagem mais simples e frases curtas.
- Nível 3: inclua uma analogia intuitiva para leigos.
- Nível 4: inclua um exemplo prático do cotidiano com números fáceis.

Explicação original:
{base_explication}

Reescreva agora a explicação no NÍVEL {nivel}, objetivo e didático.
"""

    gen = _ollama_generate(prompt, temperature=0.2, max_tokens=400)
    if gen:
        return gen.strip()

    # Fallback templates
    if nivel == 2:
        return "Versão simples: pense em etapas curtas. Identifique o que a questão pede, escolha a ideia central e aplique de forma direta."
    if nivel == 3:
        return "Usando analogia: é como seguir uma receita — separar ingredientes (dados), escolher a panela certa (fórmula/ideia) e cozinhar passo a passo até o resultado."
    # nivel 4
    return "Exemplo do dia a dia: imagine medir a distância percorrida caminhando a um ritmo constante. Some os passos (dados), multiplique pelo comprimento médio de cada passo e compare com a resposta esperada."

# ---------------------- Plano de Estudo ----------------------

def build_study_plan(usuario: str,
                     horas_por_dia: float,
                     objetivo: str,
                     forcas: list[str],
                     fraquezas: list[str],
                     historico: list[dict]) -> dict:
    """
    Gera um plano de 7 dias com foco em fraquezas, revisões espaçadas,
    blocos de prática e sessões curtas com descanso. Ajuste simples baseado em horas_por_dia.
    """
    # Distribuição simples por disciplina (pode evoluir para algoritmo mais robusto)
    base_disciplinas = ["matematica", "fisica", "quimica", "biologia", "portugues", "historia", "geografia"]
    foco = fraquezas if fraquezas else ["matematica", "fisica"]
    reforco = forcas if forcas else ["portugues", "historia"]

    blocos = max(1, int(horas_por_dia // 0.5))  # blocos de 30 min
    plano = {
        "usuario": usuario,
        "objetivo": objetivo,
        "horas_por_dia": horas_por_dia,
        "duracao": "7 dias",
        "metodologia": [
            "Revisão espaçada (24h, 72h, 7 dias)",
            "Prática ativa (questões com feedback imediato)",
            "Ciclo de foco: 25min estudo + 5min descanso",
            "Ajuste dinâmico com base nos erros cometidos"
        ],
        "cronograma": []
    }

    for dia in range(1, 8):
        atividades = []

        # Dia 1 dá mais peso às fraquezas
        for b in range(blocos):
            if b % 2 == 0 and foco:
                atividades.append({
                    "tipo": "pratica",
                    "disciplina": foco[(dia + b) % len(foco)],
                    "meta": "Resolver 10 questões nível fácil→médio",
                    "revisar": "Revisão em 24h"
                })
            else:
                atividades.append({
                    "tipo": "teoria",
                    "disciplina": reforco[(dia + b) % len(reforco)] if reforco else base_disciplinas[(dia + b) % len(base_disciplinas)],
                    "meta": "Resumo de 1 tópico + 5 questões",
                    "revisar": "Revisão em 72h"
                })

        plano["cronograma"].append({
            "dia": dia,
            "atividades": atividades
        })

    # Checkpoints
    plano["checkpoints"] = [
        {"dia": 3, "avaliacao": "Mini simulado (30 questões)", "acao": "Recalibrar fraquezas"},
        {"dia": 7, "avaliacao": "Simulado completo", "acao": "Gerar relatório e novo plano"}
    ]

    return plano
