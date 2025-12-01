"""
Router de Simulados ENEM - API Completa

Endpoints para criação, execução e avaliação de simulados do ENEM
Integrado com Prisma (via subprocess Node.js)

ROTAS:
- POST /api/enem/simulados/start - Iniciar novo simulado
- POST /api/enem/simulados/answer - Responder questão
- POST /api/enem/simulados/finish - Finalizar e calcular nota
- GET  /api/enem/simulados/history - Histórico do usuário
- POST /api/enem/simulados/compare-score - Comparar com nota de corte
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# Caminho do projeto Prisma (auto-detecta)
PRISMA_PROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "enem-pro"

if not (PRISMA_PROJECT_PATH / "prisma" / "schema.prisma").exists():
    logger.warning(f"Projeto Prisma não encontrado em {PRISMA_PROJECT_PATH}")
    PRISMA_PROJECT_PATH = None

# ============================================================================
# MODELOS PYDANTIC (Request/Response)
# ============================================================================

class StartSimuladoRequest(BaseModel):
    user_id: str = Field(..., description="ID do usuário (pode ser email temporário)")
    area: Optional[str] = Field(None, description="Disciplina/área específica (opcional)")
    quantidade: int = Field(10, ge=1, le=180, description="Quantidade de questões")

class StartSimuladoResponse(BaseModel):
    simulado_id: str
    usuario_simulado_id: str
    quantidade: int
    disciplina: Optional[str]
    questoes: List[Dict]  # [{id, enunciado, alternativas}]

class AnswerRequest(BaseModel):
    user_id: str
    simulado_id: str  # ID do UsuarioSimulado
    questao_id: int
    alternativa_marcada: Optional[int] = Field(None, ge=0, le=4, description="0-4 (A-E) ou null")

class AnswerResponse(BaseModel):
    ok: bool
    resposta_id: int
    questao_id: int
    alternativa_marcada: Optional[int]

class FinishRequest(BaseModel):
    user_id: str
    simulado_id: str  # ID do UsuarioSimulado

class ErroDetalhado(BaseModel):
    questao_id: int
    enunciado: str
    alternativas: List[str]
    correta: int
    marcada: Optional[int]

class FinishResponse(BaseModel):
    ok: bool
    usuario_simulado_id: str
    acertos: int
    erros: int
    total: int
    porcentagem: float
    nota: float
    desempenho: str
    erros_detalhados: List[ErroDetalhado]

class CompareScoreRequest(BaseModel):
    user_id: str
    simulado_id: str
    curso: str
    universidade: str
    ano: int = Field(2024, ge=2015, le=2030)

class CompareScoreResponse(BaseModel):
    passou: bool
    nota_usuario: float
    nota_corte: Optional[float]
    diferenca: Optional[float]
    mensagem: str

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/api/enem/simulados",
    tags=["ENEM Simulados"]
)

# ============================================================================
# FUNÇÕES AUXILIARES - PRISMA VIA NODE.JS
# ============================================================================

def run_prisma_script(script_content: str) -> Dict:
    """
    Executa script Node.js com Prisma Client

    Args:
        script_content: Código JavaScript/TypeScript a executar

    Returns:
        Resultado parseado (JSON)
    """
    if not PRISMA_PROJECT_PATH:
        raise HTTPException(
            status_code=500,
            detail="Projeto Prisma não configurado. Verifique PRISMA_PROJECT_PATH."
        )

    # Cria script temporário
    script_path = PRISMA_PROJECT_PATH / "scripts" / "temp_api_script.mjs"
    script_path.parent.mkdir(parents=True, exist_ok=True)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    try:
        # Executa via Node.js
        result = subprocess.run(
            ['node', str(script_path)],
            cwd=str(PRISMA_PROJECT_PATH),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Remove script temp
        script_path.unlink()

        if result.returncode != 0:
            logger.error(f"Erro Prisma: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao executar operação no banco: {result.stderr[:200]}"
            )

        # Parse JSON da última linha da saída
        output_lines = result.stdout.strip().split('\n')
        for line in reversed(output_lines):
            if line.strip().startswith('{') or line.strip().startswith('['):
                return json.loads(line)

        # Se não encontrou JSON, retorna erro
        raise HTTPException(
            status_code=500,
            detail="Resposta do banco inválida (não é JSON)"
        )

    except json.JSONDecodeError as e:
        logger.error(f"Erro ao parsear JSON: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar resposta do banco: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erro ao executar script Prisma: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def calcular_nota_tri(acertos: int, total: int) -> float:
    """Calcula nota TRI simplificada (0-1000)"""
    if total == 0:
        return 0.0
    porcentagem = (acertos / total) * 100
    nota_base = 300
    nota_por_acerto = 700 / total
    nota = nota_base + (acertos * nota_por_acerto)
    return round(nota, 2)

def classificar_desempenho(porcentagem: float) -> str:
    """Classifica desempenho"""
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

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/start", response_model=StartSimuladoResponse)
async def start_simulado(req: StartSimuladoRequest):
    """
    INICIA NOVO SIMULADO

    1. Busca ou cria usuário
    2. Seleciona N questões aleatórias do banco
    3. Cria Simulado e UsuarioSimulado
    4. Retorna ID + questões

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/simulados/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user@example.com',
        area: 'matematica',  // opcional
        quantidade: 10
      })
    });
    const data = await response.json();
    // data.simulado_id - use para responder questões
    // data.questoes - array de questões para exibir
    ```
    """
    logger.info(f"📝 Iniciando simulado para usuário {req.user_id}")

    script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  // =========================================================================
  // 1. BUSCA OU CRIA USUÁRIO
  // =========================================================================
  let usuario = await prisma.usuario.findUnique({{
    where: {{ email: "{req.user_id}" }}
  }});

  if (!usuario) {{
    usuario = await prisma.usuario.create({{
      data: {{
        email: "{req.user_id}",
        nome: "Usuário ENEM",
        senha: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5R8RZJqZqI7S2" // Hash de "senha123"
      }}
    }});
  }}

  // =========================================================================
  // 2. BUSCA IDs DE QUESTÕES JÁ RESPONDIDAS PELO USUÁRIO
  // =========================================================================
  // Objetivo: NUNCA repetir questões que o usuário já viu em simulados anteriores
  //
  // Lógica:
  // - Busca todos os simulados anteriores do usuário
  // - Para cada simulado, pega todas as respostas
  // - Acumula IDs únicos de questões já respondidas
  //
  // CUSTOMIZAÇÃO: Para alterar a política de repetição, modifique esta query:
  // - Adicionar filtro por data (ex: últimos 30 dias)
  // - Adicionar filtro por área/disciplina
  // - Permitir repetição após X tempo ou Y simulados

  const simuladosAnteriores = await prisma.usuarioSimulado.findMany({{
    where: {{
      usuarioId: usuario.id,
      // OPCIONAL: Adicionar filtros aqui para customizar política
      // status: "finalizado",  // Apenas simulados finalizados
      // createdAt: {{ gte: new Date(Date.now() - 30*24*60*60*1000) }}  // Últimos 30 dias
    }},
    include: {{
      respostas: {{
        select: {{
          questaoId: true
        }}
      }}
    }}
  }});

  // Acumula IDs de questões já respondidas (SEM duplicatas)
  const questoesJaRespondidas = new Set();
  for (const sim of simuladosAnteriores) {{
    for (const resp of sim.respostas) {{
      questoesJaRespondidas.add(resp.questaoId);
    }}
  }}

  console.error(`[INFO] Usuário ${{usuario.id}} já respondeu ${{questoesJaRespondidas.size}} questões únicas`);

  // =========================================================================
  // 3. SELECIONA QUESTÕES NOVAS (NÃO RESPONDIDAS)
  // =========================================================================
  // Estratégia:
  // 1. Primeiro tenta buscar apenas questões NOVAS
  // 2. Se não houver questões suficientes, usa FALLBACK (permite repetição)
  //
  // CUSTOMIZAÇÃO: Altere o critério de seleção aqui:
  // - Mudar ordenação (random, por dificuldade, por área)
  // - Adicionar filtros (disciplina, ano, tipo)

  const whereFilter = {{
    {f'disciplina: "{req.area}",' if req.area else ''}
    id: {{
      notIn: Array.from(questoesJaRespondidas)  // Exclui questões já respondidas
    }}
  }};

  let questoes = await prisma.questao.findMany({{
    where: whereFilter,
    take: {req.quantidade}
    // NOTA: Para seleção verdadeiramente aleatória, use extensão Prisma ou raw query
    // Por ora, pega as primeiras N questões não respondidas
  }});

  // =========================================================================
  // 4. FALLBACK: Se não houver questões novas suficientes
  // =========================================================================
  // Permite repetição APENAS se não houver questões novas disponíveis
  //
  // CUSTOMIZAÇÃO: Ajuste o comportamento do fallback:
  // - Lançar erro em vez de permitir repetição
  // - Pegar questões respondidas há mais tempo
  // - Priorizar questões erradas para revisão

  if (questoes.length < {req.quantidade}) {{
    console.error(`[WARNING] Apenas ${{questoes.length}} questões novas disponíveis. Solicitadas: {req.quantidade}`);
    console.error(`[WARNING] Usando FALLBACK: permitindo repetição de questões antigas`);

    // Busca questões adicionais (incluindo já respondidas)
    const questoesFallback = await prisma.questao.findMany({{
      where: {{
        {f'disciplina: "{req.area}",' if req.area else ''}
        id: {{
          notIn: questoes.map(q => q.id)  // Evita duplicatas DENTRO deste simulado
        }}
      }},
      take: {req.quantidade} - questoes.length
    }});

    questoes = [...questoes, ...questoesFallback];
    console.error(`[INFO] Total após fallback: ${{questoes.length}} questões`);
  }}

  if (questoes.length === 0) {{
    throw new Error("Nenhuma questão disponível no banco");
  }}

  // =========================================================================
  // 5. CRIA SIMULADO
  // =========================================================================
  const simulado = await prisma.simulado.create({{
    data: {{
      disciplina: "{req.area or 'geral'}"
    }}
  }});

  // =========================================================================
  // 6. VINCULA QUESTÕES AO SIMULADO
  // =========================================================================
  // Garante que não haja duplicatas DENTRO do mesmo simulado
  const questoesUnicas = Array.from(new Set(questoes.map(q => q.id)))
    .map(id => questoes.find(q => q.id === id));

  for (const q of questoesUnicas) {{
    await prisma.simuladoQuestao.create({{
      data: {{
        simuladoId: simulado.id,
        questaoId: q.id
      }}
    }});
  }}

  // =========================================================================
  // 7. CRIA USUARIOSIMULADO (VÍNCULO USUÁRIO-SIMULADO)
  // =========================================================================
  const usuarioSimulado = await prisma.usuarioSimulado.create({{
    data: {{
      usuarioId: usuario.id,
      simuladoId: simulado.id,
      total: questoesUnicas.length
    }}
  }});

  console.error(`[SUCCESS] Simulado ${{simulado.id}} criado com ${{questoesUnicas.length}} questões únicas`);

  // =========================================================================
  // 8. RETORNA DADOS PARA API
  // =========================================================================
  const result = {{
    simulado_id: simulado.id,
    usuario_simulado_id: usuarioSimulado.id,
    quantidade: questoesUnicas.length,
    disciplina: simulado.disciplina,
    questoes_novas: questoesUnicas.length - (questoes.length - questoesUnicas.length),
    questoes_repetidas: questoes.length > questoesUnicas.length ? questoes.length - questoesUnicas.length : 0,
    questoes: questoesUnicas.map(q => ({{
      id: q.id,
      enunciado: q.enunciado,
      alternativas: JSON.parse(q.alternativas)
    }}))
  }};

  console.log(JSON.stringify(result));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)

    # Log detalhado da seleção de questões
    quantidade = result.get('quantidade', 0)
    questoes_novas = result.get('questoes_novas', quantidade)
    questoes_repetidas = result.get('questoes_repetidas', 0)

    logger.info(f"✅ Simulado {result['simulado_id']} criado com {quantidade} questões")

    if questoes_repetidas > 0:
        logger.warning(
            f"⚠️  FALLBACK ATIVADO: {questoes_repetidas} questões repetidas de simulados anteriores. "
            f"Questões novas: {questoes_novas}, Total: {quantidade}"
        )
    else:
        logger.info(f"🎯 Todas as {questoes_novas} questões são NOVAS (nunca respondidas pelo usuário)")

    return JSONResponse(content=jsonable_encoder(result))

@router.post("/answer", response_model=AnswerResponse)
async def answer_question(req: AnswerRequest):
    """
    RESPONDE UMA QUESTÃO

    Grava ou atualiza resposta do usuário.
    Não calcula nota ainda.

    ## Exemplo de uso (Frontend):
    ```javascript
    // Quando usuário marca alternativa
    await fetch('/api/enem/simulados/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user@example.com',
        simulado_id: 'clx...', // recebido do /start
        questao_id: 15,
        alternativa_marcada: 2  // C (0=A, 1=B, 2=C, 3=D, 4=E)
      })
    });
    ```
    """
    logger.info(f"💬 Resposta: usuário {req.user_id}, questão {req.questao_id}, alternativa {req.alternativa_marcada}")

    alt_value = req.alternativa_marcada if req.alternativa_marcada is not None else 'null'

    script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  // Verifica se já existe resposta
  const existente = await prisma.usuarioResposta.findFirst({{
    where: {{
      usuarioSimuladoId: "{req.simulado_id}",
      questaoId: {req.questao_id}
    }}
  }});

  let resposta;

  if (existente) {{
    // Atualiza
    resposta = await prisma.usuarioResposta.update({{
      where: {{ id: existente.id }},
      data: {{
        alternativaMarcada: {alt_value}
      }}
    }});
  }} else {{
    // Cria nova
    resposta = await prisma.usuarioResposta.create({{
      data: {{
        usuarioSimuladoId: "{req.simulado_id}",
        questaoId: {req.questao_id},
        alternativaMarcada: {alt_value}
      }}
    }});
  }}

  const result = {{
    ok: true,
    resposta_id: resposta.id,
    questao_id: resposta.questaoId,
    alternativa_marcada: resposta.alternativaMarcada
  }};

  console.log(JSON.stringify(result));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)
    logger.info(f"✅ Resposta salva (ID {result['resposta_id']})")

    return JSONResponse(content=jsonable_encoder(result))

@router.post("/finish", response_model=FinishResponse)
async def finish_simulado(req: FinishRequest):
    """
    FINALIZA SIMULADO E CALCULA NOTA

    1. Busca todas as respostas do usuário
    2. Busca gabaritos corretos
    3. Calcula acertos/erros
    4. Calcula nota TRI
    5. Atualiza UsuarioSimulado com status=finalizado

    ## Exemplo de uso (Frontend):
    ```javascript
    // Quando usuário clica "Finalizar Simulado"
    const response = await fetch('/api/enem/simulados/finish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user@example.com',
        simulado_id: 'clx...'
      })
    });

    const resultado = await response.json();
    // resultado.nota - nota TRI (0-1000)
    // resultado.acertos - número de acertos
    // resultado.porcentagem - % de acertos
    // resultado.erros_detalhados - lista de questões erradas
    ```
    """
    logger.info(f"🏁 Finalizando simulado {req.simulado_id}")

    script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  // 1. Busca UsuarioSimulado
  const usuarioSimulado = await prisma.usuarioSimulado.findUnique({{
    where: {{ id: "{req.simulado_id}" }},
    include: {{
      respostas: true
    }}
  }});

  if (!usuarioSimulado) {{
    throw new Error("Simulado não encontrado");
  }}

  // 2. Busca simulado e questões
  const simulado = await prisma.simulado.findUnique({{
    where: {{ id: usuarioSimulado.simuladoId }},
    include: {{
      questoes: {{
        include: {{
          questao: true
        }}
      }}
    }}
  }});

  // 3. Calcula acertos
  let acertos = 0;
  let total = simulado.questoes.length;
  const errosDetalhados = [];

  for (const sq of simulado.questoes) {{
    const questao = sq.questao;
    const resposta = usuarioSimulado.respostas.find(r => r.questaoId === questao.id);

    const marcada = resposta?.alternativaMarcada ?? null;
    const correta = questao.correta;
    const isCorreto = marcada === correta;

    if (isCorreto) {{
      acertos++;
    }} else {{
      errosDetalhados.push({{
        questao_id: questao.id,
        enunciado: questao.enunciado,
        alternativas: JSON.parse(questao.alternativas),
        correta: correta,
        marcada: marcada
      }});
    }}
  }}

  // 4. Calcula porcentagem
  const porcentagem = total > 0 ? (acertos / total) * 100 : 0;

  // Resultado
  const result = {{
    ok: true,
    usuario_simulado_id: usuarioSimulado.id,
    acertos: acertos,
    erros: total - acertos,
    total: total,
    porcentagem: parseFloat(porcentagem.toFixed(2)),
    erros_detalhados: errosDetalhados
  }};

  console.log(JSON.stringify(result));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)

    # Calcula nota TRI
    nota = calcular_nota_tri(result['acertos'], result['total'])
    desempenho = classificar_desempenho(result['porcentagem'])

    result['nota'] = nota
    result['desempenho'] = desempenho

    # Busca curso alvo do usuário e compara
    curso_script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  const usuario = await prisma.usuario.findUnique({{
    where: {{ id: "{req.user_id}" }},
    include: {{ cursoAlvo: true }}
  }});

  console.log(JSON.stringify(usuario?.cursoAlvo || null));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    curso_result = run_prisma_script(curso_script)
    curso_alvo = curso_result if curso_result and isinstance(curso_result, dict) else None

    # Comparar nota com curso alvo
    atingiu_nota_corte = False
    diferenca_nota = None

    if curso_alvo and 'notaCorte' in curso_alvo:
        diferenca_nota = nota - curso_alvo['notaCorte']
        atingiu_nota_corte = diferenca_nota >= 0
        logger.info(f"📊 Comparação com curso: {curso_alvo['nome']} - {curso_alvo['ies']} (Nota de corte: {curso_alvo['notaCorte']})")
        logger.info(f"{'✅' if atingiu_nota_corte else '⚠️'} Diferença: {diferenca_nota:+.1f} pontos")

    result['curso_alvo'] = curso_alvo
    result['atingiu_nota_corte'] = atingiu_nota_corte
    result['diferenca_nota'] = diferenca_nota

    # Atualiza banco com nota final
    update_script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  await prisma.usuarioSimulado.update({{
    where: {{ id: "{req.simulado_id}" }},
    data: {{
      status: "finalizado",
      nota: {nota},
      acertos: {result['acertos']},
      finishedAt: new Date()
    }}
  }});
  console.log(JSON.stringify({{ok: true}}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    run_prisma_script(update_script)

    logger.info(f"✅ Simulado finalizado: {result['acertos']}/{result['total']} acertos, nota {nota}")

    return JSONResponse(content=jsonable_encoder(result))

@router.get("/history")
async def get_history(user_id: str = Query(..., description="Email/ID do usuário")):
    """
    HISTÓRICO DE SIMULADOS DO USUÁRIO

    Retorna últimos simulados realizados com notas e datas.

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/simulados/history?user_id=user@example.com');
    const historico = await response.json();

    // historico.simulados - array com:
    // [{id, disciplina, nota, acertos, total, porcentagem, data}]
    ```
    """
    logger.info(f"📊 Buscando histórico de {user_id}")

    script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  // Busca usuário
  const usuario = await prisma.usuario.findUnique({{
    where: {{ email: "{user_id}" }}
  }});

  if (!usuario) {{
    console.log(JSON.stringify({{simulados: []}}));
    return;
  }}

  // Busca simulados finalizados
  const simulados = await prisma.usuarioSimulado.findMany({{
    where: {{
      usuarioId: usuario.id,
      status: "finalizado"
    }},
    orderBy: {{
      finishedAt: 'desc'
    }},
    take: 20,
    include: {{
      usuario: true
    }}
  }});

  // Busca dados do simulado original
  const result = [];
  for (const us of simulados) {{
    const sim = await prisma.simulado.findUnique({{
      where: {{ id: us.simuladoId }}
    }});

    result.push({{
      id: us.id,
      disciplina: sim?.disciplina || 'geral',
      nota: us.nota,
      acertos: us.acertos,
      total: us.total,
      porcentagem: us.total > 0 ? ((us.acertos / us.total) * 100).toFixed(2) : 0,
      data: us.finishedAt
    }});
  }}

  console.log(JSON.stringify({{simulados: result}}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)
    logger.info(f"✅ Encontrados {len(result.get('simulados', []))} simulados")

    return JSONResponse(content=jsonable_encoder(result))

@router.post("/compare-score", response_model=CompareScoreResponse)
async def compare_score(req: CompareScoreRequest):
    """
    COMPARA NOTA DO SIMULADO COM NOTA DE CORTE

    Verifica se nota do usuário seria suficiente para passar no curso.

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/simulados/compare-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user@example.com',
        simulado_id: 'clx...',
        curso: 'Medicina',
        universidade: 'USP',
        ano: 2024
      })
    });

    const comparacao = await response.json();
    // comparacao.passou - true/false
    // comparacao.nota_usuario - sua nota
    // comparacao.nota_corte - nota mínima do curso
    // comparacao.diferenca - pontos de diferença
    ```
    """
    logger.info(f"📈 Comparando nota: {req.curso} - {req.universidade}")

    # 1. Busca nota do simulado
    script_nota = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  const us = await prisma.usuarioSimulado.findUnique({{
    where: {{ id: "{req.simulado_id}" }}
  }});

  if (!us || us.status !== "finalizado") {{
    throw new Error("Simulado não finalizado ou não encontrado");
  }}

  console.log(JSON.stringify({{nota: us.nota}}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    nota_result = run_prisma_script(script_nota)
    nota_usuario = nota_result['nota']

    # 2. Busca nota de corte
    script_corte = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  const notaCorte = await prisma.notaCorte.findFirst({{
    where: {{
      curso: "{req.curso}",
      universidade: "{req.universidade}",
      ano: {req.ano}
    }},
    orderBy: {{
      semestre: 'desc'
    }}
  }});

  const result = notaCorte ? {{nota_minima: notaCorte.notaMinima}} : {{nota_minima: null}};
  console.log(JSON.stringify(result));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    corte_result = run_prisma_script(script_corte)
    nota_corte = corte_result.get('nota_minima')

    # 3. Compara
    if nota_corte is None:
        return JSONResponse(content=jsonable_encoder({
            "passou": False,
            "nota_usuario": nota_usuario,
            "nota_corte": None,
            "diferenca": None,
            "mensagem": f"Nota de corte não disponível para {req.curso} - {req.universidade} ({req.ano})"
        }))

    passou = nota_usuario >= nota_corte
    diferenca = round(nota_usuario - nota_corte, 2)

    if passou:
        mensagem = f"🎉 Parabéns! Sua nota ({nota_usuario}) está {abs(diferenca)} pontos acima da nota de corte ({nota_corte})."
    else:
        mensagem = f"📚 Continue estudando! Você precisa de {abs(diferenca)} pontos a mais. Nota de corte: {nota_corte}, sua nota: {nota_usuario}."

    logger.info(f"✅ Comparação: passou={passou}, diferença={diferenca}")

    return JSONResponse(content=jsonable_encoder({
        "passou": passou,
        "nota_usuario": nota_usuario,
        "nota_corte": nota_corte,
        "diferenca": diferenca,
        "mensagem": mensagem
    }))

@router.get("/")
async def simulados_root():
    """Info sobre API de simulados"""
    return JSONResponse(content=jsonable_encoder({
        "status": "online",
        "service": "ENEM Simulados API",
        "version": "1.0",
        "endpoints": [
            "POST /api/enem/simulados/start - Iniciar simulado",
            "POST /api/enem/simulados/answer - Responder questão",
            "POST /api/enem/simulados/finish - Finalizar e calcular nota",
            "GET  /api/enem/simulados/history?user_id=... - Histórico",
            "POST /api/enem/simulados/compare-score - Comparar com nota de corte"
        ]
    }))
