from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
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
# MODELOS PYDANTIC - EXPLICAR
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
# REEXPLICAÇÃO - MODELOS E ESTRUTURAS
# ============================================================================


class NivelSimplificacao(str, Enum):
    """Níveis de simplificação para reexplicações"""
    NORMAL = "normal"
    SIMPLES = "simples"
    MUITO_SIMPLES = "muito_simples"
    ELI5 = "eli5"  # Explain Like I'm 5


# Contador de tentativas de reexplicação (em produção, use banco de dados)
tentativas_reexplicacao: Dict[str, int] = defaultdict(int)


class ReexplicarReq(BaseModel):
    questao_id: int = Field(..., ge=1, description="ID da questão")
    resposta_usuario: str = Field(..., min_length=1, max_length=1, description="Alternativa marcada (A-E)")
    resposta_correta: Optional[str] = Field(None, min_length=1, max_length=1, description="Gabarito correto")
    explicacao_anterior: Optional[str] = Field(None, max_length=10000, description="Explicação que não foi entendida")
    duvida_especifica: Optional[str] = Field(None, max_length=500, description="Ponto específico que não entendeu")
    tentativa_numero: Optional[int] = Field(1, ge=1, le=5, description="Número da tentativa (1-5)")
    nivel_escolar: Optional[str] = Field("medio", description="Nível escolar do aluno")

    @validator('resposta_usuario', 'resposta_correta')
    def validar_alternativa(cls, v):
        if v and v.upper() not in ['A', 'B', 'C', 'D', 'E']:
            raise ValueError("Alternativa deve ser A, B, C, D ou E")
        return v.upper() if v else None

    @validator('nivel_escolar')
    def validar_nivel(cls, v):
        niveis = ['fundamental', 'medio', 'superior']
        if v and v.lower() not in niveis:
            raise ValueError(f"Nível escolar deve ser: {', '.join(niveis)}")
        return v.lower() if v else 'medio'


class ReexplicacaoResponse(BaseModel):
    ok: bool = True
    explicacao: str
    questao_id: int
    nivel_simplificacao: str
    tentativa_numero: int
    sugestoes_estudo: List[str]
    recursos_adicionais: List[str]
    tempo_processamento: float
    modelo_usado: str
    timestamp: str

# ============================================================================
# FUNÇÕES AUXILIARES GERAIS
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
                await asyncio.sleep(2)
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
# FUNÇÕES AUXILIARES - REEXPLICAÇÃO
# ============================================================================


def determinar_nivel_simplificacao(tentativa: int) -> NivelSimplificacao:
    """
    Determina o nível de simplificação baseado no número de tentativas.
    Cada tentativa usa uma estratégia mais simples.
    """
    if tentativa == 1:
        return NivelSimplificacao.SIMPLES
    elif tentativa == 2:
        return NivelSimplificacao.MUITO_SIMPLES
    else:
        return NivelSimplificacao.ELI5


def _get_estrutura_por_nivel(nivel: NivelSimplificacao) -> str:
    """Retorna a estrutura de resposta adequada ao nível"""

    if nivel == NivelSimplificacao.ELI5:
        return """**1. 🎯 A Ideia Principal (em 1 frase)**
Explique o conceito principal como se fosse um desenho animado

**2. 🎪 A História/Analogia**
Conte uma mini-história usando personagens ou situações muito familiares

**3. 🎨 Como Fazer (3 passos)**
① Passo 1 (com emoji)
② Passo 2 (com emoji)  
③ Passo 3 (com emoji)

**4. 🌟 Por que dá certo?**
Uma frase explicando a "mágica"

**5. 🎁 Dica Final**
Um truque super simples para lembrar"""

    elif nivel == NivelSimplificacao.MUITO_SIMPLES:
        return """**1. 🎯 O Que É Isso?**
Defina o conceito usando comparação com algo do dia a dia

**2. 🎪 Vamos Ver Na Prática**
Exemplo concreto passo a passo, como fazer um miojo

**3. 💡 Jeito Fácil de Lembrar**
Um macete visual ou frase que gruda na cabeça

**4. ✅ Testando Se Entendeu**
Uma pergunta super simples para auto-verificação

**5. 🚀 Próximo Passo**
O que estudar depois de dominar isso"""

    else:  # SIMPLES
        return """**1. 📌 Resumo em 2 Linhas**
Qual é a ideia central desta questão?

**2. 🎯 Por Que Errou**
Explique o erro de forma gentil e construtiva

**3. 🛠️ Passo a Passo Correto**
Mostre o caminho certo de forma bem organizada

**4. 🌟 Exemplo do Cotidiano**
Analogia concreta e memorável

**5. 💡 Dica Prática**
Um atalho mental para não errar novamente

**6. 🔗 Conexão**
Como isso se relaciona com outros assuntos do ENEM

**7. ❓ O que ainda ficou confuso?**
Pergunte especificamente sobre pontos que podem gerar dúvida"""


def construir_prompt_reexplicacao(
    req: ReexplicarReq,
    nivel: NivelSimplificacao
) -> str:
    """
    Constrói prompt de reexplicação adaptado ao nível de simplificação.
    """

    # Informações sobre a dúvida
    contexto_duvida = ""
    if req.duvida_especifica:
        contexto_duvida = f"\n\n🤔 **O aluno especificamente não entendeu:**\n{req.duvida_especifica}"

    if req.explicacao_anterior:
        contexto_duvida += f"\n\n📚 **Explicação anterior (que ele não entendeu):**\n{req.explicacao_anterior[:500]}..."

    estrategias = {
        NivelSimplificacao.SIMPLES: {
            "objetivo": "Simplifique a explicação, usando frases mais curtas e vocabulário mais básico",
            "exemplo": "Use analogias do cotidiano como: futebol, cozinha, celular, redes sociais",
            "linguagem": "Evite termos técnicos. Se usar, explique imediatamente entre parênteses",
            "estrutura": "5 seções curtas"
        },
        NivelSimplificacao.MUITO_SIMPLES: {
            "objetivo": "Explique como se o aluno tivesse 12 anos, usando comparações muito concretas",
            "exemplo": "Use apenas situações que uma criança vivencia: brincar, assistir TV, ir ao parque",
            "linguagem": "Use ZERO termos técnicos. Substitua tudo por linguagem coloquial",
            "estrutura": "3 seções muito curtas com muitos emojis"
        },
        NivelSimplificacao.ELI5: {
            "objetivo": "Explique de forma extremamente simples, como se fosse para uma criança de 5 anos",
            "exemplo": "Use apenas: brinquedos, animais, frutas, cores, formas",
            "linguagem": "Frases curtíssimas. Uma ideia por frase. Vocabulário de criança",
            "estrutura": "História curta e visual com desenho em ASCII se possível"
        }
    }

    estrategia = estrategias.get(nivel, estrategias[NivelSimplificacao.SIMPLES])

    prompt = f"""Você é um professor EXCEPCIONAL do ENEM, famoso por conseguir explicar qualquer conceito de forma que TODOS entendam.

🆘 **SITUAÇÃO:**
Um aluno está com dificuldade na Questão #{req.questao_id}.
- Ele marcou: **{req.resposta_usuario}**
{f'- A resposta correta é: **{req.resposta_correta}**' if req.resposta_correta else ''}
- Esta é a **TENTATIVA #{req.tentativa_numero}** de explicação
- Nível do aluno: **{req.nivel_escolar}**{contexto_duvida}

🎯 **NÍVEL DE SIMPLIFICAÇÃO: {nivel.value.upper().replace('_', ' ')}**

📋 **SUA ESTRATÉGIA:**
- **Objetivo:** {estrategia['objetivo']}
- **Exemplos:** {estrategia['exemplo']}
- **Linguagem:** {estrategia['linguagem']}
- **Estrutura:** {estrategia['estrutura']}

{"**🎈 VAMOS ENTENDER BRINCANDO!**" if nivel == NivelSimplificacao.ELI5 else "**💡 VAMOS SIMPLIFICAR!**"}

{_get_estrutura_por_nivel(nivel)}

⚠️ **REGRAS CRÍTICAS:**
1. {"Use linguagem de criança pequena" if nivel == NivelSimplificacao.ELI5 else "Seja ainda mais simples que a explicação anterior"}
2. UMA analogia super concreta e visual por seção
3. Frases curtas (máximo 15 palavras)
4. MUITOS emojis para tornar visual
5. Se usar número/fórmula, explique cada parte separadamente
6. Termine perguntando o que especificamente ainda está confuso

💚 **ATITUDE:**
- Seja paciente e encorajador
- Nunca diga "é simples" ou "é fácil"
- Celebre cada pequena compreensão
- Mostre que a dúvida é normal e saudável

{"🎨 **BÔNUS:** Use ASCII art se ajudar a visualizar!" if nivel in [NivelSimplificacao.MUITO_SIMPLES, NivelSimplificacao.ELI5] else ""}"""

    return prompt


def gerar_sugestoes_estudo(questao_id: int, nivel: NivelSimplificacao) -> List[str]:
    """Gera sugestões personalizadas de estudo baseadas no nível de dificuldade"""

    sugestoes_base = [
        "📺 Assista vídeos curtos (5-10 min) sobre o tema no YouTube",
        "📝 Faça resumos com suas próprias palavras",
        "👥 Explique o conceito para um amigo ou familiar",
        "🎯 Pratique com questões mais fáceis primeiro",
        "📱 Use apps de flashcards para memorização"
    ]

    if nivel == NivelSimplificacao.ELI5:
        sugestoes_base.extend([
            "🎨 Desenhe o conceito (não precisa ser bonito!)",
            "🎭 Crie uma história ou música sobre o tema",
            "🧩 Divida o problema em partes bem pequenas"
        ])

    return sugestoes_base[:5]


def gerar_recursos_adicionais(nivel: NivelSimplificacao) -> List[str]:
    """Sugere recursos externos baseados no nível"""

    recursos = {
        NivelSimplificacao.SIMPLES: [
            "Khan Academy Brasil (explicações em português)",
            "Brasil Escola (resumos didáticos)",
            "Descomplica (videoaulas)",
        ],
        NivelSimplificacao.MUITO_SIMPLES: [
            "Canal 'Me Salva!' no YouTube",
            "Prof. Ferreto (Química/Física simples)",
            "Gis com Giz (Matemática básica)",
        ],
        NivelSimplificacao.ELI5: [
            "Mundo Bita (conceitos básicos animados)",
            "Manual do Mundo (experimentos práticos)",
            "TED-Ed (animações educativas legendadas)",
        ]
    }

    return recursos.get(nivel, recursos[NivelSimplificacao.SIMPLES])


def limpar_tentativas_antigas():
    """
    Remove tentativas antigas do contador (mais de 24h).
    Em produção, isso deveria ser gerenciado por TTL no Redis.
    """
    # Por simplicidade, limpa tudo periodicamente
    if len(tentativas_reexplicacao) > 1000:
        tentativas_reexplicacao.clear()
        logger.info("🧹 Contador de tentativas limpo")

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
            "reexplicar_reset": "/reexplicar/reset/{questao_id} (DELETE)",
            "reexplicar_stats": "/reexplicar/stats (GET)",
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

# ============================================================================
# ENDPOINTS DE REEXPLICAÇÃO
# ============================================================================


@app.post("/reexplicar", response_model=ReexplicacaoResponse)
async def reexplicar(
    req: ReexplicarReq,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Gera uma **reexplicação simplificada** quando o aluno não entendeu a primeira explicação.
    """
    inicio = datetime.now()
    ip_cliente = request.client.host if request.client else "unknown"

    # Verificar rate limit
    if not verificar_rate_limit(ip_cliente):
        logger.warning(f"⚠️ Rate limit excedido para IP: {ip_cliente}")
        raise HTTPException(
            status_code=429,
            detail="Limite de requisições excedido. Aguarde um momento."
        )

    # Atualizar contador de tentativas
    key_tentativa = f"{ip_cliente}:{req.questao_id}"
    tentativas_reexplicacao[key_tentativa] += 1
    tentativa_atual = tentativas_reexplicacao[key_tentativa]

    # Se passou de 5 tentativas, sugere ajuda personalizada
    if tentativa_atual > 5:
        logger.warning(f"⚠️ Questão #{req.questao_id} já teve {tentativa_atual} reexplicações")
        raise HTTPException(
            status_code=429,
            detail=(
                "Esta questão já foi explicada 5 vezes de formas diferentes. "
                "Recomendamos:\n"
                "1. Descansar um pouco e voltar depois\n"
                "2. Estudar o conteúdo base antes\n"
                "3. Buscar ajuda de um professor particular\n"
                "4. Assistir videoaulas sobre o tema"
            )
        )

    logger.info(
        f"🔄 Reexplicação solicitada - Questão #{req.questao_id} - "
        f"Tentativa #{tentativa_atual} - IP: {ip_cliente}"
    )

    # Determinar nível de simplificação
    nivel = determinar_nivel_simplificacao(req.tentativa_numero or tentativa_atual)
    logger.info(f"📊 Nível de simplificação: {nivel.value}")

    try:
        # Construir prompt específico para reexplicação
        prompt = construir_prompt_reexplicacao(req, nivel)

        # Chamar Ollama com timeout maior (reexplicações podem ser mais elaboradas)
        explicacao = await chamar_ollama_com_retry(prompt, max_tentativas=2)

        # Gerar sugestões e recursos
        sugestoes = gerar_sugestoes_estudo(req.questao_id, nivel)
        recursos = gerar_recursos_adicionais(nivel)

        # Calcular tempo de processamento
        tempo_processamento = (datetime.now() - inicio).total_seconds()

        logger.info(
            f"✅ Reexplicação gerada - Nível: {nivel.value} - "
            f"Tempo: {tempo_processamento:.2f}s"
        )

        # Agendar limpeza de tentativas antigas em background
        background_tasks.add_task(limpar_tentativas_antigas)

        return ReexplicacaoResponse(
            ok=True,
            explicacao=explicacao,
            questao_id=req.questao_id,
            nivel_simplificacao=nivel.value,
            tentativa_numero=tentativa_atual,
            sugestoes_estudo=sugestoes,
            recursos_adicionais=recursos,
            tempo_processamento=tempo_processamento,
            modelo_usado=OLLAMA_MODEL,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao gerar reexplicação: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar reexplicação: {str(e)}"
        )


@app.delete("/reexplicar/reset/{questao_id}")
async def resetar_tentativas(
    questao_id: int,
    request: Request
):
    """
    Reseta o contador de tentativas de reexplicação para uma questão específica.
    Útil quando o aluno quer recomeçar o processo de aprendizado.
    """
    ip_cliente = request.client.host if request.client else "unknown"
    key_tentativa = f"{ip_cliente}:{questao_id}"

    if key_tentativa in tentativas_reexplicacao:
        tentativas_antigas = tentativas_reexplicacao[key_tentativa]
        del tentativas_reexplicacao[key_tentativa]
        logger.info(f"🔄 Tentativas resetadas para questão #{questao_id} (eram {tentativas_antigas})")

        return {
            "message": f"Contador de tentativas resetado para questão #{questao_id}",
            "tentativas_anteriores": tentativas_antigas,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "message": f"Nenhuma tentativa registrada para questão #{questao_id}",
            "timestamp": datetime.now().isoformat()
        }


@app.get("/reexplicar/stats")
async def stats_reexplicacoes():
    """
    Retorna estatísticas sobre reexplicações.
    Útil para análise de quais questões são mais difíceis.
    """
    if not tentativas_reexplicacao:
        return {
            "total_questoes": 0,
            "total_tentativas": 0,
            "questoes_dificeis": [],
            "timestamp": datetime.now().isoformat()
        }

    # Agrupa por questão
    stats_por_questao = defaultdict(int)
    for key, tentativas in tentativas_reexplicacao.items():
        questao_id = key.split(':')[-1]
        stats_por_questao[questao_id] += tentativas

    # Top 10 questões mais difíceis
    questoes_dificeis = sorted(
        stats_por_questao.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    return {
        "total_questoes": len(stats_por_questao),
        "total_tentativas": sum(tentativas_reexplicacao.values()),
        "media_tentativas": sum(tentativas_reexplicacao.values()) / len(tentativas_reexplicacao),
        "questoes_mais_dificeis": [
            {"questao_id": q_id, "tentativas": tent}
            for q_id, tent in questoes_dificeis
        ],
        "timestamp": datetime.now().isoformat()
    }

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
