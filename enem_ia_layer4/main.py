
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime

from ai_engine import explain_with_ai, simplify_explanation_with_ai, build_study_plan

app = FastAPI(title="ENEM-IA • Camada 4 – IA Integrada", version="1.0.0")

# CORS aberto para facilitar o dev local (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------- Schemas -------------------------

class ExplicacaoInput(BaseModel):
    questao_id: Optional[int] = None
    enunciado: str
    alternativas: Optional[Dict[str, str]] = None
    resposta_usuario: Optional[int] = None
    correta: Optional[int] = None
    usuario: str = "Aluno"

class FeedbackInput(BaseModel):
    session_id: str
    entendeu: bool
    usuario: str = "Aluno"

class PlanoInput(BaseModel):
    usuario: str = "Aluno"
    horas_por_dia: float = Field(ge=0.5, le=12)
    objetivo: str = "ENEM 2025"
    forcas: List[str] = []
    fraquezas: List[str] = []
    historico: Optional[List[Dict[str, Any]]] = None  # [{disciplina, acertos, erros, tempo_medio, ...}]

# ------------------------- Memória simples em RAM -------------------------

SESSOES: Dict[str, Dict[str, Any]] = {}

# ------------------------- Rotas IA Explicação -------------------------

@app.post("/ia/explicacao")
def gerar_explicacao(data: ExplicacaoInput):
    """
    Gera explicação detalhada + pergunta de confirmação ao usuário.
    Retorna também um session_id para continuar o diálogo (feedback).
    """
    try:
        explicacao = explain_with_ai(
            enunciado=data.enunciado,
            alternativas=data.alternativas or {},
            resposta_usuario=data.resposta_usuario,
            correta=data.correta
        )

        session_id = str(uuid4())
        SESSOES[session_id] = {
            "created_at": datetime.utcnow().isoformat(),
            "usuario": data.usuario,
            "ultimo_nivel": 1,
            "contexto": {
                "enunciado": data.enunciado,
                "alternativas": data.alternativas or {},
                "resposta_usuario": data.resposta_usuario,
                "correta": data.correta,
                "explicacao_base": explicacao
            }
        }

        return {
            "session_id": session_id,
            "usuario": data.usuario,
            "explicacao": explicacao,
            "followup": f"{data.usuario}, fez sentido? Responda 'Sim' ou 'Não'.",
            "proxima_acao": "POST /ia/explicacao/feedback com { session_id, entendeu: true|false }"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao gerar explicação: {e}")

@app.post("/ia/explicacao/feedback")
def feedback_explicacao(data: FeedbackInput):
    """
    Se o usuário NÃO entendeu, gera explicação mais simples (nível 2, 3, ...),
    usando analogias e passo-a-passo. Se entendeu, encerra a sessão com reforço positivo.
    """
    sess = SESSOES.get(data.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    usuario = data.usuario or sess.get("usuario", "Aluno")

    if data.entendeu:
        # encerra sessão com mensagem de reforço
        SESSOES.pop(data.session_id, None)
        return {
            "ok": True,
            "mensagem": f"Excelente, {usuario}! Vamos em frente. Quer praticar outra questão sobre o mesmo tema?",
            "sugestoes": [
                "Resolver 3 questões similares (nível fácil→médio)",
                "Gerar um resumo do conteúdo em 5 tópicos",
                "Agendar revisão em 48 horas (revisão espaçada)"
            ]
        }

    # não entendeu → simplificar mais um nível
    nivel_atual = int(sess.get("ultimo_nivel", 1))
    proximo_nivel = min(nivel_atual + 1, 4)

    contexto = sess["contexto"]
    explicacao_simplificada = simplify_explanation_with_ai(
        base_explication=contexto["explicacao_base"],
        enunciado=contexto["enunciado"],
        alternativas=contexto["alternativas"],
        nivel=proximo_nivel
    )

    sess["ultimo_nivel"] = proximo_nivel
    sess["contexto"]["explicacao_base"] = explicacao_simplificada  # atualiza para poder simplificar ainda mais depois

    terminou = (proximo_nivel >= 4)

    return {
        "session_id": data.session_id,
        "nivel": proximo_nivel,
        "explicacao": explicacao_simplificada,
        "pergunta": f"{usuario}, agora fez sentido? (Sim/Não)",
        "encerrar_se_nao_entender": terminou,
        "nota": "Se ainda não entender no próximo passo, vamos propor vídeo/áudio e exemplos concretos."
    }

# ------------------------- Plano de Estudo Personalizado -------------------------

@app.post("/ia/plano")
def plano_estudo(data: PlanoInput):
    try:
        plano = build_study_plan(
            usuario=data.usuario,
            horas_por_dia=data.horas_por_dia,
            objetivo=data.objetivo,
            forcas=data.forcas,
            fraquezas=data.fraquezas,
            historico=data.historico or []
        )
        return plano
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao montar plano: {e}")

@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}
