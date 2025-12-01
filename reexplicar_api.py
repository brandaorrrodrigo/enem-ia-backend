# Adicione estes imports no topo do arquivo (se ainda não existirem)
from enum import Enum

# ============================================================================
# ADICIONAR APÓS OS IMPORTS E ANTES DOS MODELOS
# ============================================================================

class NivelSimplificacao(str, Enum):
    """Níveis de simplificação para reexplicações"""
    NORMAL = "normal"
    SIMPLES = "simples"
    MUITO_SIMPLES = "muito_simples"
    ELI5 = "eli5"  # Explain Like I'm 5


# Contador de tentativas de reexplicação (em produção, use banco de dados)
tentativas_reexplicacao: Dict[str, int] = defaultdict(int)

# ============================================================================
# ADICIONAR APÓS ExplicarReq
# ============================================================================

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
# FUNÇÕES AUXILIARES PARA REEXPLICAÇÃO
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
    
    # Estratégias específicas por nível
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

✨ **FORMATO DA REEXPLICAÇÃO:**

{"**🎈 VAMOS ENTENDER BRINCANDO!**" if nivel == NivelSimplificacao.ELI5 else "**💡 VAMOS SIMPLIFICAR!**"}

{self._get_estrutura_por_nivel(nivel)}

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

# ============================================================================
# ENDPOINT DE REEXPLICAÇÃO
# ============================================================================

@app.post("/reexplicar", response_model=ReexplicacaoResponse)
async def reexplicar(
    req: ReexplicarReq,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Gera uma **reexplicação simplificada** quando o aluno não entendeu a primeira explicação.
    
    **Recursos especiais:**
    - 📊 Escala automática de simplicidade (3 níveis)
    - 🎯 Adaptação ao número de tentativas
    - 🎨 Analogias cada vez mais concretas
    - 💡 Sugestões personalizadas de estudo
    - 🔄 Abordagens diferentes em cada tentativa
    
    **Níveis de simplificação:**
    - **Tentativa 1**: Simplificado (vocabulário básico, frases curtas)
    - **Tentativa 2**: Muito simples (como para 12 anos)
    - **Tentativa 3+**: ELI5 - Explain Like I'm 5 (como para criança)
    
    **Parâmetros:**
    - **questao_id**: ID da questão
    - **resposta_usuario**: Alternativa marcada
    - **duvida_especifica**: (Opcional) O que especificamente não entendeu
    - **explicacao_anterior**: (Opcional) Texto da explicação original
    - **tentativa_numero**: Número desta tentativa (1-5)
    """
    inicio = datetime.now()
    ip_cliente = request.client.host if request.client else "unknown"
    
    # Verificar rate limit
    if not verificar_rate_limit(ip_cliente):
        logger.warning(f"⚠️ Rate limit excedido para IP: {ip_cliente}")
        raise HTTPException(
            status_code=429,
            detail=f"Limite de requisições excedido. Aguarde um momento."
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


def limpar_tentativas_antigas():
    """
    Remove tentativas antigas do contador (mais de 24h).
    Em produção, isso deveria ser gerenciado por TTL no Redis.
    """
    # Por simplicidade, limpa tudo periodicamente
    # Em produção, implemente TTL por chave
    if len(tentativas_reexplicacao) > 1000:
        tentativas_reexplicacao.clear()
        logger.info("🧹 Contador de tentativas limpo")


# ============================================================================
# ENDPOINT AUXILIAR: RESETAR TENTATIVAS
# ============================================================================

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


# ============================================================================
# ENDPOINT AUXILIAR: ESTATÍSTICAS DE REEXPLICAÇÕES
# ============================================================================

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