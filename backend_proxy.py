from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ENEM-IA Result API", 
    version="1.0",
    description="API para correção de simulados do ENEM Pro"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Memória simples (em produção, use banco de dados)
RESULTADOS: Dict[str, Dict] = {}

# ============================================================================
# MODELOS
# ============================================================================

class Resp(BaseModel):
    id: int = Field(..., description="ID da questão")
    marcada: Optional[str] = Field(None, description="Alternativa marcada (A-E)")
    enunciado: str = Field(..., min_length=10, description="Texto da questão")
    alternativas: List[str] = Field(..., min_items=4, max_items=5, description="Lista de alternativas")
    gabarito: Optional[str] = Field(None, description="Resposta correta (A-E)")
    
    @validator('marcada')
    def validar_marcada(cls, v):
        if v is not None and v.upper() not in ['A', 'B', 'C', 'D', 'E', '']:
            raise ValueError("Alternativa deve ser A, B, C, D ou E")
        return v.upper() if v else None
    
    @validator('gabarito')
    def validar_gabarito(cls, v):
        if v is not None and v.upper() not in ['A', 'B', 'C', 'D', 'E']:
            raise ValueError("Gabarito deve ser A, B, C, D ou E")
        return v.upper() if v else None


class CorrigirReq(BaseModel):
    simulado_id: str = Field(..., min_length=1, description="ID do simulado")
    respostas: List[Resp] = Field(..., min_items=1, description="Lista de respostas")
    disciplina: Optional[str] = Field(None, description="Disciplina do simulado")


class ErroDetalhado(BaseModel):
    id: int
    enunciado: str
    alternativas: List[str]
    correta: str
    marcada: str
    explicacao: Optional[str] = None


class ResultadoResponse(BaseModel):
    resultado_id: str
    simulado_id: str
    acertos: int
    erros_count: int
    total: int
    porcentagem: float
    nota: float
    desempenho: str
    erros: List[ErroDetalhado]
    data_hora: str
    disciplina: Optional[str] = None

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def calcular_nota(acertos: int, total: int) -> float:
    """Calcula nota baseada no modelo TRI simplificado (0-1000)"""
    if total == 0:
        return 0.0
    porcentagem = (acertos / total) * 100
    # Fórmula simplificada: nota base + bonus por acerto
    nota_base = 300
    nota_por_acerto = 700 / total
    nota = nota_base + (acertos * nota_por_acerto)
    return round(nota, 2)


def classificar_desempenho(porcentagem: float) -> str:
    """Classifica o desempenho com base na porcentagem de acertos"""
    if porcentagem >= 90:
        return "🏆 Excelente"
    elif porcentagem >= 75:
        return "🌟 Muito Bom"
    elif porcentagem >= 60:
        return "👍 Bom"
    elif porcentagem >= 50:
        return "📚 Regular"
    else:
        return "💪 Precisa Melhorar"


def obter_gabarito(questao: Resp) -> str:
    """
    Obtém o gabarito da questão.
    
    IMPORTANTE: Esta é uma versão simplificada.
    Em produção, busque o gabarito real do banco de dados.
    """
    # Se o gabarito vier na requisição, use-o
    if questao.gabarito:
        return questao.gabarito
    
    # ⚠️ MOCK: Em produção, busque do banco de dados pelo questao.id
    # Aqui estamos retornando "C" como exemplo
    logger.warning(f"Gabarito não fornecido para questão {questao.id}, usando mock")
    return "C"

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "ENEM-IA Result API",
        "version": "1.0",
        "endpoints": ["/responder", "/resultado/{id}", "/resultados"]
    }


@app.post("/responder", response_model=ResultadoResponse)
def corrigir(req: CorrigirReq):
    """
    Corrige um simulado e retorna o resultado detalhado.
    
    - **simulado_id**: ID único do simulado
    - **respostas**: Lista de respostas do aluno
    - **disciplina**: (Opcional) Disciplina do simulado
    """
    try:
        logger.info(f"Corrigindo simulado {req.simulado_id} com {len(req.respostas)} questões")
        
        acertos = 0
        erros: List[ErroDetalhado] = []
        
        for r in req.respostas:
            # Obtém o gabarito correto
            correta = obter_gabarito(r)
            marcada = str(r.marcada or "").upper()
            
            # Verifica se acertou
            is_certo = (marcada == correta)
            
            if is_certo:
                acertos += 1
            else:
                erros.append(ErroDetalhado(
                    id=r.id,
                    enunciado=r.enunciado,
                    alternativas=r.alternativas,
                    correta=correta,
                    marcada=marcada if marcada else "Não respondida",
                    explicacao=None  # Pode ser preenchido com IA posteriormente
                ))
        
        # Cálculos
        total = len(req.respostas)
        porcentagem = round((acertos / total) * 100, 2) if total > 0 else 0
        nota = calcular_nota(acertos, total)
        desempenho = classificar_desempenho(porcentagem)
        
        # Gera ID único para o resultado
        rid = str(uuid.uuid4())[:8]
        
        # Monta resultado completo
        resultado = {
            "resultado_id": rid,
            "simulado_id": req.simulado_id,
            "acertos": acertos,
            "erros_count": len(erros),
            "total": total,
            "porcentagem": porcentagem,
            "nota": nota,
            "desempenho": desempenho,
            "erros": erros,
            "data_hora": datetime.now().isoformat(),
            "disciplina": req.disciplina
        }
        
        # Salva em memória
        RESULTADOS[rid] = resultado
        
        logger.info(f"Resultado {rid} criado: {acertos}/{total} acertos ({porcentagem}%)")
        
        return resultado
    
    except Exception as e:
        logger.error(f"Erro ao corrigir simulado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar correção: {str(e)}")


@app.get("/resultado/{resultado_id}", response_model=ResultadoResponse)
def get_resultado(resultado_id: str = Path(..., description="ID do resultado a buscar")):
    """
    Busca um resultado específico pelo ID.
    
    - **resultado_id**: ID único do resultado gerado após a correção
    """
    logger.info(f"Buscando resultado {resultado_id}")
    
    if resultado_id not in RESULTADOS:
        logger.warning(f"Resultado {resultado_id} não encontrado")
        raise HTTPException(
            status_code=404, 
            detail=f"Resultado '{resultado_id}' não encontrado. Verifique o ID."
        )
    
    return RESULTADOS[resultado_id]


@app.get("/resultados")
def listar_resultados(
    limite: int = Query(10, ge=1, le=100, description="Quantidade de resultados a retornar"),
    offset: int = Query(0, ge=0, description="Offset para paginação")
):
    """
    Lista todos os resultados disponíveis (paginado).
    
    - **limite**: Quantidade máxima de resultados (1-100)
    - **offset**: Número de resultados a pular
    """
    logger.info(f"Listando resultados (limite={limite}, offset={offset})")
    
    resultados_lista = list(RESULTADOS.values())
    total = len(resultados_lista)
    
    # Ordenar por data (mais recente primeiro)
    resultados_ordenados = sorted(
        resultados_lista, 
        key=lambda x: x.get('data_hora', ''), 
        reverse=True
    )
    
    # Aplicar paginação
    resultados_pagina = resultados_ordenados[offset:offset + limite]
    
    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "resultados": resultados_pagina
    }


@app.delete("/resultado/{resultado_id}")
def deletar_resultado(resultado_id: str = Path(..., description="ID do resultado a deletar")):
    """
    Deleta um resultado específico.
    
    - **resultado_id**: ID do resultado a ser removido
    """
    logger.info(f"Deletando resultado {resultado_id}")
    
    if resultado_id not in RESULTADOS:
        raise HTTPException(status_code=404, detail="Resultado não encontrado")
    
    del RESULTADOS[resultado_id]
    
    return {"message": f"Resultado {resultado_id} deletado com sucesso"}


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 ENEM-IA Result API iniciada")
    logger.info(f"📊 Documentação disponível em: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 ENEM-IA Result API encerrada")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")