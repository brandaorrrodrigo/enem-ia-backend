"""
Router de Usuário ENEM - Estatísticas e Perfil

Endpoints para dados do usuário, gamificação e progresso

ROTAS:
- GET /api/enem/usuario/stats - Estatísticas do usuário (FP, nível, streak)
- GET /api/enem/usuario/profile - Perfil completo
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

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

class UsuarioStatsResponse(BaseModel):
    email: str
    nome: str
    pontosFP: int
    nivel: str
    streak: int
    total_simulados: int
    media_nota: float

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

        # Parse JSON do stdout
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
# ROUTER
# ============================================================================

router = APIRouter()

@router.get("/stats", response_model=UsuarioStatsResponse)
async def get_usuario_stats(user_id: str = Query(..., description="Email/ID do usuário")):
    """
    ESTATÍSTICAS DO USUÁRIO

    Retorna dados de gamificação e progresso:
    - Focus Points (FP) acumulados
    - Nível atual (Bronze, Silver, Gold, Platinum, Diamond)
    - Streak de dias consecutivos estudando
    - Total de simulados realizados
    - Média de notas

    ## Cálculo de Streak:
    - Conta dias consecutivos com pelo menos 1 simulado
    - Quebra se passar 1 dia sem estudar
    - Considera timezone UTC

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/usuario/stats?user_id=user@example.com');
    const stats = await response.json();

    // stats.pontosFP - Focus Points totais
    // stats.nivel - Bronze, Silver, Gold, etc
    // stats.streak - Dias consecutivos
    ```
    """
    logger.info(f"📊 Buscando estatísticas de {user_id}")

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
    console.log(JSON.stringify({{
      email: "{user_id}",
      nome: "Usuário ENEM",
      pontosFP: 0,
      nivel: "Bronze",
      streak: 0,
      total_simulados: 0,
      media_nota: 0
    }}));
    return;
  }}

  // =========================================================================
  // 2. BUSCA SIMULADOS FINALIZADOS
  // =========================================================================
  const simulados = await prisma.usuarioSimulado.findMany({{
    where: {{
      usuarioId: usuario.id,
      status: "finalizado"
    }},
    orderBy: {{
      finishedAt: 'desc'
    }}
  }});

  // =========================================================================
  // 3. CALCULA STREAK (DIAS CONSECUTIVOS)
  // =========================================================================
  let streak = 0;

  if (simulados.length > 0) {{
    // Agrupa simulados por data (ignorando hora)
    const datasUnicas = [...new Set(
      simulados.map(s => {{
        const d = new Date(s.finishedAt);
        return d.toISOString().split('T')[0]; // Apenas YYYY-MM-DD
      }})
    )].sort().reverse(); // Mais recentes primeiro

    // Data de hoje (UTC)
    const hoje = new Date();
    hoje.setUTCHours(0, 0, 0, 0);
    const hojeStr = hoje.toISOString().split('T')[0];

    // Data de ontem
    const ontem = new Date(hoje);
    ontem.setUTCDate(ontem.getUTCDate() - 1);
    const ontemStr = ontem.toISOString().split('T')[0];

    // Verifica se estudou hoje ou ontem (senão streak = 0)
    const ultimaData = datasUnicas[0];

    if (ultimaData === hojeStr || ultimaData === ontemStr) {{
      streak = 1;

      // Conta dias consecutivos
      for (let i = 0; i < datasUnicas.length - 1; i++) {{
        const dataAtual = new Date(datasUnicas[i]);
        const dataAnterior = new Date(datasUnicas[i + 1]);

        const diffDias = Math.floor((dataAtual - dataAnterior) / (1000 * 60 * 60 * 24));

        if (diffDias === 1) {{
          streak++;
        }} else {{
          break; // Quebrou o streak
        }}
      }}
    }}
  }}

  // =========================================================================
  // 4. CALCULA MÉDIA DE NOTAS
  // =========================================================================
  let mediaNota = 0;
  if (simulados.length > 0) {{
    const somaNotas = simulados.reduce((acc, s) => acc + (s.nota || 0), 0);
    mediaNota = Math.round(somaNotas / simulados.length);
  }}

  // =========================================================================
  // 5. RETORNA RESULTADO
  // =========================================================================
  console.log(JSON.stringify({{
    email: usuario.email,
    nome: usuario.nome || "Usuário ENEM",
    pontosFP: usuario.pontosFP || 0,
    nivel: usuario.nivel || "Bronze",
    streak: streak,
    total_simulados: simulados.length,
    media_nota: mediaNota
  }}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)
    logger.info(f"✅ Estatísticas: {result['pontosFP']} FP, nível {result['nivel']}, streak {result['streak']}")

    return result

@router.get("/profile")
async def get_usuario_profile(user_id: str = Query(..., description="Email/ID do usuário")):
    """
    PERFIL COMPLETO DO USUÁRIO

    Retorna todos os dados do usuário incluindo histórico e conquistas.
    """
    logger.info(f"👤 Buscando perfil de {user_id}")

    script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  const usuario = await prisma.usuario.findUnique({{
    where: {{ email: "{user_id}" }},
    include: {{
      simulados: {{
        where: {{ status: "finalizado" }},
        orderBy: {{ finishedAt: 'desc' }},
        take: 10
      }},
      recompensas: {{
        include: {{
          reward: true
        }}
      }}
    }}
  }});

  if (!usuario) {{
    console.log(JSON.stringify({{ error: "Usuário não encontrado" }}));
    return;
  }}

  console.log(JSON.stringify({{
    email: usuario.email,
    nome: usuario.nome,
    pontosFP: usuario.pontosFP,
    nivel: usuario.nivel,
    createdAt: usuario.createdAt,
    total_simulados: usuario.simulados.length,
    total_recompensas: usuario.recompensas.length
  }}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)

    if result.get('error'):
        raise HTTPException(status_code=404, detail=result['error'])

    logger.info(f"✅ Perfil carregado: {result['email']}")
    return result
