from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict
import httpx
import os
import logging
import hashlib
import asyncio

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "90"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "24"))

# ============================================================================
# INICIALIZAÇÃO DA APP
# ============================================================================

app = FastAPI(
    title="ENEM-IA API",
    version="2.0",
    description="API avançada para explicações pedagógicas de questões do ENEM",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique domínios permitidos
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ============================================================================
# SISTEMA DE CACHE E RATE LIMITING
# ============================================================================

# Cache simples em memória (em produção, use Redis)
cache_explicacoes: Dict[str, Dict] = {}

# Rate limiting simples
rate_limit_store: Dict[str, List[datetime]] = defaultdict(list)
RATE_LIMIT_MAX = 10  # requisições
RATE_LIMIT_WINDOW = 60  # segundos


def limpar_cache_expirado():
    """Remove entradas expiradas do cache"""
    agora = datetime.now()
    keys_para_remover = []
    
    for key, valor in cache_explicacoes.items():
        if agora > valor["expira_em"]:
            keys_para_remover.append(key)
    
    for key in keys_para_remover:
        del cache_explicacoes[key]
        logger.info(f"🗑️ Cache expirado removido: {key[:8]}...")


def gerar_cache_key(questao_id: int, resposta: str, contexto: Optional[str]) -> str:
    """Gera chave única para cache baseada nos parâmetros"""
    dados = f"{questao_id}:{resposta}:{contexto or ''}"
    return hashlib.sha256(dados.encode()).hexdigest()


def verificar_rate_limit(ip: str) -> bool:
    """Verifica se IP excedeu o rate limit"""
    agora = datetime.now()
    janela_inicio = agora - timedelta(seconds=RATE_LIMIT_WINDOW)
    
    # Remove requisições antigas
    rate_limit_store[ip] = [
        timestamp for timestamp in rate_limit_store[ip]
        if timestamp > janela_inicio
    ]
    
    # Verifica limite
    if len(rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        return False
    
    # Adiciona nova requisição
    rate_limit_store[ip].append(agora)
    return True

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class ExplicarReq(BaseModel):
    questao_id: int = Field(..., ge=1, description="ID da questão (maior que 0)")
    resposta_usuario: str = Field(..., min_length=1, max_length=1, description="Alternativa marcada (A-E)")
    resposta_correta: Optional[str] = Field(None, min_length=1, max_length=1, description="Gabarito correto (A-E)")
    enunciado: Optional[str] = Field(None, max_length=5000, description="Texto da questão (opcional)")
    disciplina: Optional[str] = Field(None, description="Disciplina da questão")
    assunto: Optional[str] = Field(None, description="Assunto específico")
    dificuldade: Optional[str] = Field(None, description="Nível de dificuldade")
    contexto_adicional: Optional[str] = Field(None, max_length=1000, description="Informações extras")
    
    @validator('resposta_usuario', 'resposta_correta')
    def validar_alternativa(cls, v):
        if v and v.upper() not in ['A', 'B', 'C', 'D', 'E']:
            raise ValueError("Alternativa deve ser A, B, C, D ou E")
        return v.upper() if v else None
    
    @validator('disciplina')
    def validar_disciplina(cls, v):
        disciplinas_validas = [
            'matematica', 'fisica', 'quimica', 'biologia',
            'historia', 'geografia', 'portugues', 'literatura',
            'filosofia', 'sociologia', 'ingles', 'espanhol'
        ]
        if v and v.lower() not in disciplinas_validas:
            raise ValueError(f"Disciplina deve ser uma de: {', '.join(disciplinas_validas)}")
        return v.lower() if v else None


class ExplicacaoResponse(BaseModel):
    ok: bool = True
    explicacao: str
    questao_id: int
    cached: bool = False
    tempo_processamento: float
    modelo_usado: str
    timestamp: str
    resposta_era_correta: Optional[bool] = None
    nivel_confianca: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    ollama_disponivel: bool
    ollama_url: str
    modelo: str
    cache_entries: int
    timestamp: str

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

async def verificar_ollama_disponivel() -> bool:
    """Verifica se o Ollama está acessível"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Ollama não disponível: {str(e)}")
        return False


def construir_prompt_detalhado(req: ExplicarReq) -> str:
    """Constrói prompt pedagógico personalizado"""
    
    # Informações contextuais
    contexto = ""
    if req.disciplina:
        contexto += f"\n📚 Disciplina: {req.disciplina.title()}"
    if req.assunto:
        contexto += f"\n📖 Assunto: {req.assunto}"
    if req.dificuldade:
        contexto += f"\n⭐ Dificuldade: {req.dificuldade}"
    
    # Informação sobre acerto/erro
    resultado = ""
    if req.resposta_correta:
        acertou = req.resposta_usuario == req.resposta_correta
        resultado = f"\n✅ O aluno {'ACERTOU' if acertou else 'ERROU'} a questão."
        resultado += f"\n🎯 Resposta correta: {req.resposta_correta}"
        resultado += f"\n❌ Resposta do aluno: {req.resposta_usuario}"
    
    # Enunciado
    enunciado_texto = ""
    if req.enunciado:
        enunciado_texto = f"\n\n📝 **Enunciado da questão:**\n{req.enunciado}"
    
    # Contexto adicional
    adicional = ""
    if req.contexto_adicional:
        adicional = f"\n\n💡 **Informações adicionais:**\n{req.contexto_adicional}"
    
    prompt = f"""Você é um professor EXPERIENTE e EMPÁTICO do ENEM, especializado em explicações pedagógicas claras e motivadoras.

📋 **INFORMAÇÕES DA QUESTÃO:**
🆔 Questão #{req.questao_id}{contexto}{resultado}{enunciado_texto}{adicional}

🎯 **SUA MISSÃO:**
Gerar uma explicação COMPLETA, DIDÁTICA e MOTIVADORA que ajude o aluno a:
1. Entender onde errou (se errou) ou por que acertou
2. Compreender o conceito fundamental
3. Fixar o conhecimento para não errar novamente
4. Conectar com outros tópicos do ENEM

📝 **ESTRUTURA OBRIGATÓRIA DA RESPOSTA:**

**1️⃣ ANÁLISE DA RESPOSTA** {'(🎉 Parabéns!)' if req.resposta_correta and req.resposta_usuario == req.resposta_correta else ''}
{f'- O aluno marcou: {req.resposta_usuario}' if req.resposta_usuario else ''}
{f'- A resposta correta é: {req.resposta_correta}' if req.resposta_correta else ''}
- Explique de forma gentil e motivadora o que aconteceu

**2️⃣ CONCEITO FUNDAMENTAL**
- Qual é o conceito/teoria/regra principal dessa questão?
- Explique com clareza, usando linguagem acessível
- Use NEGRITO para destacar termos importantes

**3️⃣ PASSO A PASSO DA RESOLUÇÃO**
- Detalhe o raciocínio completo que leva à resposta correta
- Use números ou marcadores para organizar
- Seja progressivo: do mais simples ao mais complexo

**4️⃣ EXEMPLO PRÁTICO DO DIA A DIA** 🌟
- SEMPRE crie uma analogia com situação cotidiana
- Exemplos: compras no mercado, preparar comida, usar celular, dirigir, esportes, corpo humano, natureza
- Faça a conexão ser ÓBVIA e MEMORÁVEL

**5️⃣ CONEXÕES COM OUTROS TÓPICOS** 🔗
- Cite 2-3 outros assuntos/questões do ENEM que usam raciocínio similar
- Mostre como esse conhecimento se conecta com outras disciplinas

**6️⃣ DICA DE MEMORIZAÇÃO** 💡
- Ensine um MACETE para lembrar desse conceito
- Pode ser: sigla, frase curta, rima, imagem mental, regra prática
- Faça ser SIMPLES e INESQUECÍVEL

**7️⃣ EXERCÍCIO MENTAL RÁPIDO** 🧠
- Proponha UMA pergunta simples para o aluno se auto-testar
- Deve reforçar o conceito aprendido

**8️⃣ MENSAGEM MOTIVACIONAL** 💪
- Finalize com incentivo genuíno e personalizado
- Mostre que errar faz parte do aprendizado
- Encoraje o aluno a continuar estudando

**9️⃣ VERIFICAÇÃO DE ENTENDIMENTO**
- Pergunte: "Ficou claro? Quer que eu explique de outra forma?"

⚠️ **REGRAS IMPORTANTES:**
- Use linguagem acessível (nível ensino médio)
- Seja empático e motivador, NUNCA punitivo
- Use emojis para tornar a leitura agradável
- Seja conciso mas completo (não seja prolixo)
- Adapte exemplos à disciplina da questão
- SEMPRE termine com pergunta de verificação

💚 Lembre-se: você está ajudando um jovem a conquistar seu sonho de entrar na universidade!"""

    return prompt


async def chamar_ollama_com_retry(
    prompt: str,
    max_tentativas: int = MAX_RETRIES
) -> str:
    """
    Chama Ollama com sistema de retry em caso de falha
    """
    ultima_excecao = None
    
    for tentativa in range(max_tentativas):
        try:
            logger.info(f"🤖 Tentativa {tentativa + 1}/{max_tentativas} - Chamando Ollama")
            
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                        }
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Extrai o texto da resposta
                texto = data.get("response") or data.get("text") or ""
                
                if not texto or len(texto.strip()) < 50:
                    raise ValueError("Resposta muito curta ou vazia da IA")
                
                logger.info(f"✅ Ollama respondeu com sucesso ({len(texto)} chars)")
                return texto.strip()
                
        except httpx.TimeoutException as e:
            ultima_excecao = e
            logger.warning(f"⏱️ Timeout na tentativa {tentativa + 1}")
            if tentativa < max_tentativas - 1:
                await asyncio.sleep(2)  # Aguarda antes de tentar novamente
                continue
                
        except httpx.HTTPStatusError as e:
            ultima_excecao = e
            logger.error(f"❌ Erro HTTP {e.response.status_code}")
            if tentativa < max_tentativas - 1:
                await asyncio.sleep(2)
                continue
                
        except Exception as e:
            ultima_excecao = e
            logger.error(f"💥 Erro inesperado: {str(e)}")
            if tentativa < max_tentativas - 1:
                await asyncio.sleep(2)
                continue
    
    # Se chegou aqui, todas tentativas falharam
    erro_msg = f"Falha após {max_tentativas} tentativas. Último erro: {str(ultima_excecao)}"
    logger.error(f"💥 {erro_msg}")
    raise HTTPException(status_code=503, detail=erro_msg)

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_model=Dict)
async def root():
    """Informações básicas da API"""
    return {
        "service": "ENEM-IA API",
        "version": "2.0",
        "status": "online",
        "endpoints": {
            "explicar": "/explicar (POST)",
            "reexplicar": "/reexplicar (POST)",
            "health": "/health (GET)",
            "cache_stats": "/cache/stats (GET)",
            "docs": "/docs",
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica saúde da API e disponibilidade do Ollama"""
    ollama_ok = await verificar_ollama_disponivel()
    
    return HealthResponse(
        status="healthy" if ollama_ok else "degraded",
        ollama_disponivel=ollama_ok,
        ollama_url=OLLAMA_URL,
        modelo=OLLAMA_MODEL,
        cache_entries=len(cache_explicacoes),
        timestamp=datetime.now().isoformat()
    )


@app.get("/cache/stats")
async def cache_stats(background_tasks: BackgroundTasks):
    """Estatísticas do cache"""
    background_tasks.add_task(limpar_cache_expirado)
    
    return {
        "cache_enabled": CACHE_ENABLED,
        "total_entries": len(cache_explicacoes),
        "ttl_hours": CACHE_TTL_HOURS,
        "timestamp": datetime.now().isoformat()
    }


@app.delete("/cache/clear")
async def limpar_cache():
    """Limpa todo o cache (útil para desenvolvimento)"""
    cache_explicacoes.clear()
    logger.info("🗑️ Cache limpo manualmente")
    return {"message": "Cache limpo com sucesso", "timestamp": datetime.now().isoformat()}


@app.post("/explicar", response_model=ExplicacaoResponse)
async def explicar(
    req: ExplicarReq,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Gera explicação pedagógica detalhada e personalizada para uma questão do ENEM.
    """
    inicio = datetime.now()
    ip_cliente = request.client.host if request.client else "unknown"
    
    # Verificar rate limit
    if not verificar_rate_limit(ip_cliente):
        logger.warning(f"⚠️ Rate limit excedido para IP: {ip_cliente}")
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {RATE_LIMIT_MAX} requisições por {RATE_LIMIT_WINDOW}s excedido. Aguarde um momento."
        )
    
    logger.info(f"📨 Nova requisição de explicação - Questão #{req.questao_id} - IP: {ip_cliente}")
    
    # Limpar cache expirado em background
    background_tasks.add_task(limpar_cache_expirado)
    
    # Verificar cache
    cache_key = gerar_cache_key(
        req.questao_id,
        req.resposta_usuario,
        req.contexto_adicional
    )
    
    if CACHE_ENABLED and cache_key in cache_explicacoes:
        cache_entry = cache_explicacoes[cache_key]
        if datetime.now() < cache_entry["expira_em"]:
            tempo_processamento = (datetime.now() - inicio).total_seconds()
            logger.info(f"💾 Cache HIT para questão #{req.questao_id}")
            
            return ExplicacaoResponse(
                ok=True,
                explicacao=cache_entry["explicacao"],
                questao_id=req.questao_id,
                cached=True,
                tempo_processamento=tempo_processamento,
                modelo_usado=OLLAMA_MODEL,
                timestamp=datetime.now().isoformat(),
                resposta_era_correta=(
                    req.resposta_usuario == req.resposta_correta
                    if req.resposta_correta else None
                )
            )
    
    # Cache miss - gerar nova explicação
    logger.info(f"🔄 Cache MISS - Gerando nova explicação")
    
    try:
        # Construir prompt
        prompt = construir_prompt_detalhado(req)
        
        # Chamar Ollama
        explicacao = await chamar_ollama_com_retry(prompt)
        
        # Calcular tempo de processamento
        tempo_processamento = (datetime.now() - inicio).total_seconds()
        
        # Salvar no cache se habilitado
        if CACHE_ENABLED:
            cache_explicacoes[cache_key] = {
                "explicacao": explicacao,
                "expira_em": datetime.now() + timedelta(hours=CACHE_TTL_HOURS),
                "criado_em": datetime.now().isoformat()
            }
            logger.info(f"💾 Explicação salva no cache")
        
        logger.info(f"✅ Explicação gerada com sucesso em {tempo_processamento:.2f}s")
        
        return ExplicacaoResponse(
            ok=True,
            explicacao=explicacao,
            questao_id=req.questao_id,
            cached=False,
            tempo_processamento=tempo_processamento,
            modelo_usado=OLLAMA_MODEL,
            timestamp=datetime.now().isoformat(),
            resposta_era_correta=(
                req.resposta_usuario == req.resposta_correta
                if req.resposta_correta else None
            ),
            nivel_confianca="alto"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao gerar explicação: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar explicação: {str(e)}"
        )


@app.post("/reexplicar", response_model=ExplicacaoResponse)
async def reexplicar(
    req: ExplicarReq,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Segunda explicação, mais simples, com exemplos ainda mais práticos.
    """
    inicio = datetime.now()
    ip_cliente = request.client.host if request.client else "unknown"
    
    if not verificar_rate_limit(ip_cliente):
        logger.warning(f"⚠️ Rate limit excedido para IP: {ip_cliente}")
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {RATE_LIMIT_MAX} requisições por {RATE_LIMIT_WINDOW}s excedido. Aguarde um momento."
        )

    logger.info(f"📨 Nova requisição de REEXPLICAÇÃO - Questão #{req.questao_id} - IP: {ip_cliente}")
    background_tasks.add_task(limpar_cache_expirado)

    # Prompt especial pra reexplicação
    contexto_disc = f"Disciplina: {req.disciplina}" if req.disciplina else ""
    prompt = f"""
Você é um professor extremamente didático explicando de NOVO uma questão do ENEM para um aluno que não entendeu ainda.

Questão #{req.questao_id}
{contexto_disc}

Enunciado (resumido, se disponível):
{req.enunciado or "[enunciado não enviado]"}

O aluno marcou a alternativa: {req.resposta_usuario}
Gabarito oficial: {req.resposta_correta or "não informado"}

Ele já recebeu uma explicação antes, mas NÃO ENTENDEU.
Agora você vai explicar de um jeito AINDA MAIS SIMPLES, seguindo este formato:

1) REEXPLICAÇÃO BEM SIMPLES
- Explique como se estivesse falando com um amigo usando exemplos do dia a dia
- Frases curtas, diretas, sem jargão técnico desnecessário

2) ANALOGIA DO COTIDIANO
- Crie pelo menos UMA analogia forte (mercado, esporte, trânsito, redes sociais, celular, etc)
- Ela tem que ser tão simples que até alguém cansado conseguiria entender

3) OUTRO EXEMPLO DE QUESTÃO
- Invente um exemplo parecido com a mesma base de conhecimento
- Mostre como resolver esse exemplo passo a passo

4) ONDE AS PESSOAS COSTUMAM ERRAR
- Liste 2 ou 3 erros comuns nessa ideia/conteúdo
- Explique como evitar esses erros

5) RESUMÃO FINAL EM 3 LINHAS
- Faça um micro-resumo em até 3 frases
- Como se fosse um post curto para lembrar antes da prova

6) PERGUNTA DE CHECAGEM
- Termine perguntando: "Agora ficou mais claro? Quer tentar um desafio comigo?"

Use linguagem brasileira, próxima da realidade do aluno do ensino médio.
Use emoji com moderação, só para deixar mais leve.
"""

    try:
        explicacao = await chamar_ollama_com_retry(prompt)
        tempo_processamento = (datetime.now() - inicio).total_seconds()

        return ExplicacaoResponse(
            ok=True,
            explicacao=explicacao,
            questao_id=req.questao_id,
            cached=False,
            tempo_processamento=tempo_processamento,
            modelo_usado=OLLAMA_MODEL,
            timestamp=datetime.now().isoformat(),
            resposta_era_correta=(
                req.resposta_usuario == req.resposta_correta
                if req.resposta_correta else None
            ),
            nivel_confianca="alto"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao gerar REEXPLICAÇÃO: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar REEXPLICAÇÃO: {str(e)}"
        )

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler customizado para HTTPException"""
    logger.error(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handler genérico para exceções não tratadas"""
    logger.error(f"Exceção não tratada: {type(exc).__name__} - {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "Erro interno do servidor",
            "details": str(exc) if os.getenv("DEBUG") else None,
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar a aplicação"""
    logger.info("=" * 70)
    logger.info("🚀 ENEM-IA API v2.0 INICIADA")
    logger.info("=" * 70)
    logger.info(f"🤖 Ollama URL: {OLLAMA_URL}")
    logger.info(f"🧠 Modelo: {OLLAMA_MODEL}")
    logger.info(f"⏱️  Timeout: {TIMEOUT_SECONDS}s")
    logger.info(f"🔄 Max Retries: {MAX_RETRIES}")
    logger.info(f"💾 Cache: {'Habilitado' if CACHE_ENABLED else 'Desabilitado'}")
    if CACHE_ENABLED:
        logger.info(f"⏰ Cache TTL: {CACHE_TTL_HOURS}h")
    logger.info(f"🚦 Rate Limit: {RATE_LIMIT_MAX} req/{RATE_LIMIT_WINDOW}s")
    logger.info(f"📖 Docs: http://localhost:8000/docs")
    logger.info("=" * 70)
    
    # Verificar disponibilidade do Ollama
    ollama_ok = await verificar_ollama_disponivel()
    if ollama_ok:
        logger.info("✅ Ollama está disponível e funcionando")
    else:
        logger.warning("⚠️ Ollama não está disponível - verifique a configuração")


@app.on_event("shutdown")
async def shutdown_event():
    """Executado ao encerrar a aplicação"""
    logger.info("🛑 ENEM-IA API encerrada")
    logger.info(f"📊 Estatísticas finais: {len(cache_explicacoes)} entradas no cache")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
