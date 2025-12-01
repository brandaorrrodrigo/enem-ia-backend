"""
Router de Estatísticas ENEM - Análise de Desempenho

Endpoints para estatísticas agregadas e análise de progresso

ROTAS:
- GET /api/enem/stats/por-area - Desempenho por área/disciplina
- GET /api/enem/stats/evolucao - Evolução de notas ao longo do tempo
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

PRISMA_PROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "enem-pro"

if not (PRISMA_PROJECT_PATH / "prisma" / "schema.prisma").exists():
    logger.warning(f"Projeto Prisma não encontrado em {PRISMA_PROJECT_PATH}")
    PRISMA_PROJECT_PATH = None

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class DesempenhoPorArea(BaseModel):
    area: str
    porcentagem: float
    simulados: int
    nota_media: float

class DesempenhoPorAreaResponse(BaseModel):
    desempenho: List[DesempenhoPorArea]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_prisma_script(script: str) -> dict:
    """Executa script Node.js com Prisma e retorna resultado JSON"""
    if not PRISMA_PROJECT_PATH:
        raise HTTPException(status_code=500, detail="Prisma não configurado")

    try:
        result = subprocess.run(
            ["node", "-e", script],
            cwd=str(PRISMA_PROJECT_PATH),
            capture_output=True,
            text=True,
            timeout=30,
            env={**subprocess.os.environ, "DATABASE_URL": "file:./dev.db"}
        )

        if result.returncode != 0:
            logger.error(f"Erro Prisma: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Erro no banco: {result.stderr}")

        output = result.stdout.strip()
        if not output:
            return {}

        return json.loads(output)

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout ao acessar banco")
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao parsear JSON: {result.stdout}")
        raise HTTPException(status_code=500, detail=f"Erro ao parsear resultado: {str(e)}")
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# MAPEAMENTO DE DISCIPLINAS PARA ÁREAS
# ============================================================================

AREA_MAPPING = {
    'matematica': 'Matemática',
    'math': 'Matemática',
    'linguagens': 'Linguagens',
    'portugues': 'Linguagens',
    'literatura': 'Linguagens',
    'ingles': 'Linguagens',
    'espanhol': 'Linguagens',
    'ciencias_humanas': 'Ciências Humanas',
    'historia': 'Ciências Humanas',
    'geografia': 'Ciências Humanas',
    'filosofia': 'Ciências Humanas',
    'sociologia': 'Ciências Humanas',
    'ciencias_natureza': 'Ciências da Natureza',
    'biologia': 'Ciências da Natureza',
    'fisica': 'Ciências da Natureza',
    'quimica': 'Ciências da Natureza',
    'geral': 'Geral',
}

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter()

@router.get("/por-area", response_model=DesempenhoPorAreaResponse)
async def get_stats_por_area(user_id: str = Query(..., description="Email/ID do usuário")):
    """
    DESEMPENHO POR ÁREA/DISCIPLINA

    Calcula estatísticas agregadas por área do conhecimento:
    - Matemática
    - Linguagens (Português, Literatura, Inglês/Espanhol)
    - Ciências Humanas (História, Geografia, Filosofia, Sociologia)
    - Ciências da Natureza (Biologia, Física, Química)

    Para cada área, retorna:
    - Porcentagem média de acertos
    - Número de simulados realizados
    - Nota média TRI

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/stats/por-area?user_id=user@example.com');
    const data = await response.json();

    // data.desempenho - array com:
    // [{area: "Matemática", porcentagem: 78.5, simulados: 5, nota_media: 820}]
    ```
    """
    logger.info(f"📊 Calculando desempenho por área de {user_id}")

    script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  // =========================================================================
  // 1. BUSCA USUÁRIO
  // =========================================================================
  const usuario = await prisma.usuario.findUnique({{
    where: {{ email: "{user_id}" }}
  }});

  if (!usuario) {{
    console.log(JSON.stringify({{ desempenho: [] }}));
    return;
  }}

  // =========================================================================
  // 2. BUSCA TODOS SIMULADOS FINALIZADOS COM DISCIPLINA
  // =========================================================================
  const simuladosUsuario = await prisma.usuarioSimulado.findMany({{
    where: {{
      usuarioId: usuario.id,
      status: "finalizado"
    }},
    include: {{
      respostas: true
    }}
  }});

  // =========================================================================
  // 3. BUSCA DADOS DOS SIMULADOS ORIGINAIS (disciplina)
  // =========================================================================
  const simuladosIds = simuladosUsuario.map(s => s.simuladoId);
  const simulados = await prisma.simulado.findMany({{
    where: {{
      id: {{ in: simuladosIds }}
    }}
  }});

  // Cria mapa de simuladoId -> disciplina
  const disciplinaPorSimulado = {{}};
  for (const sim of simulados) {{
    disciplinaPorSimulado[sim.id] = sim.disciplina || 'geral';
  }}

  // =========================================================================
  // 4. MAPEIA DISCIPLINAS PARA ÁREAS
  // =========================================================================
  const areaMapping = {{
    'matematica': 'Matemática',
    'math': 'Matemática',
    'linguagens': 'Linguagens',
    'portugues': 'Linguagens',
    'literatura': 'Linguagens',
    'ingles': 'Linguagens',
    'espanhol': 'Linguagens',
    'ciencias_humanas': 'Ciências Humanas',
    'historia': 'Ciências Humanas',
    'geografia': 'Ciências Humanas',
    'filosofia': 'Ciências Humanas',
    'sociologia': 'Ciências Humanas',
    'ciencias_natureza': 'Ciências da Natureza',
    'biologia': 'Ciências da Natureza',
    'fisica': 'Ciências da Natureza',
    'quimica': 'Ciências da Natureza',
    'geral': 'Geral',
  }};

  // =========================================================================
  // 5. AGRUPA SIMULADOS POR ÁREA
  // =========================================================================
  const porArea = {{}};

  for (const simUsuario of simuladosUsuario) {{
    const disciplina = disciplinaPorSimulado[simUsuario.simuladoId] || 'geral';
    const area = areaMapping[disciplina.toLowerCase()] || 'Geral';

    if (!porArea[area]) {{
      porArea[area] = {{
        area: area,
        simulados: [],
        totalAcertos: 0,
        totalQuestoes: 0,
        somaNotas: 0
      }};
    }}

    porArea[area].simulados.push(simUsuario);
    porArea[area].totalAcertos += simUsuario.acertos || 0;
    porArea[area].totalQuestoes += simUsuario.total || 0;
    porArea[area].somaNotas += simUsuario.nota || 0;
  }}

  // =========================================================================
  // 6. CALCULA ESTATÍSTICAS POR ÁREA
  // =========================================================================
  const desempenho = Object.values(porArea).map(area => {{
    const numSimulados = area.simulados.length;
    const porcentagem = area.totalQuestoes > 0
      ? (area.totalAcertos / area.totalQuestoes) * 100
      : 0;
    const notaMedia = numSimulados > 0
      ? area.somaNotas / numSimulados
      : 0;

    return {{
      area: area.area,
      porcentagem: Math.round(porcentagem * 10) / 10, // 1 decimal
      simulados: numSimulados,
      nota_media: Math.round(notaMedia)
    }};
  }});

  // Ordena por número de simulados (decrescente)
  desempenho.sort((a, b) => b.simulados - a.simulados);

  // =========================================================================
  // 7. RETORNA RESULTADO
  // =========================================================================
  console.log(JSON.stringify({{ desempenho }}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)
    logger.info(f"✅ Desempenho calculado para {len(result.get('desempenho', []))} áreas")

    return result

@router.get("/evolucao")
async def get_evolucao(
    user_id: str = Query(..., description="Email/ID do usuário"),
    limit: int = Query(10, ge=1, le=50, description="Quantidade de pontos no gráfico")
):
    """
    EVOLUÇÃO DE NOTAS AO LONGO DO TEMPO

    Retorna série temporal de notas para visualizar progresso.

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/stats/evolucao?user_id=user@example.com&limit=10');
    const data = await response.json();

    // data.evolucao - array com:
    // [{data: "2025-11-01", nota: 720, acertos: 30, total: 45}]
    ```
    """
    logger.info(f"📈 Calculando evolução de notas de {user_id}")

    script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  const usuario = await prisma.usuario.findUnique({{
    where: {{ email: "{user_id}" }}
  }});

  if (!usuario) {{
    console.log(JSON.stringify({{ evolucao: [] }}));
    return;
  }}

  const simulados = await prisma.usuarioSimulado.findMany({{
    where: {{
      usuarioId: usuario.id,
      status: "finalizado"
    }},
    orderBy: {{
      finishedAt: 'asc'
    }},
    take: {limit}
  }});

  const evolucao = simulados.map(s => ({{
    data: s.finishedAt,
    nota: s.nota || 0,
    acertos: s.acertos || 0,
    total: s.total || 0,
    porcentagem: s.total > 0 ? ((s.acertos / s.total) * 100).toFixed(1) : 0
  }}));

  console.log(JSON.stringify({{ evolucao }}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)
    logger.info(f"✅ Evolução calculada: {len(result.get('evolucao', []))} pontos")

    return result
