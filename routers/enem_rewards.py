"""
Router de Recompensas ENEM - Sistema de Loja e Resgate

Endpoints para gerenciar recompensas (rewards) e sistema de troca de FP

ROTAS:
- GET /api/enem/rewards/loja - Lista recompensas disponíveis
- POST /api/enem/rewards/resgatar - Resgata recompensa com FP
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import List, Optional

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

class Recompensa(BaseModel):
    id: str
    titulo: str
    descricao: str
    custoFP: int
    emoji: str
    categoria: str
    disponivel: bool

class LojaResponse(BaseModel):
    recompensas: List[Recompensa]

class ResgatarRequest(BaseModel):
    user_id: str
    reward_id: str

class ResgatarResponse(BaseModel):
    success: bool
    mensagem: str
    fp_restante: int
    recompensa: Optional[Recompensa] = None

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
# ROUTER
# ============================================================================

router = APIRouter()

@router.get("/loja", response_model=LojaResponse)
async def get_loja():
    """
    LISTA DE RECOMPENSAS DISPONÍVEIS NA LOJA

    Retorna todas as recompensas cadastradas no sistema com:
    - Título e descrição
    - Custo em Focus Points (FP)
    - Emoji e categoria
    - Status de disponibilidade

    ## Categorias:
    - **motivacao**: Frases e emojis motivacionais
    - **acesso**: Conteúdos premium ou funcionalidades
    - **fisico**: Produtos físicos (ex: canetas, livros)

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/rewards/loja');
    const data = await response.json();

    // data.recompensas - array com:
    // [{id: "clx1", titulo: "Emoji Exclusivo", custoFP: 100, emoji: "🌟"}]
    ```
    """
    logger.info("🏪 Buscando recompensas disponíveis na loja")

    script = '''
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  // =========================================================================
  // BUSCA TODAS AS RECOMPENSAS
  // =========================================================================
  const rewards = await prisma.reward.findMany({
    orderBy: {
      custoFP: 'asc' // Ordena por custo crescente
    }
  });

  // =========================================================================
  // FORMATA RESPOSTA
  // =========================================================================
  const recompensas = rewards.map(r => ({
    id: r.id,
    titulo: r.titulo,
    descricao: r.descricao,
    custoFP: r.custoFP,
    emoji: r.emoji,
    categoria: r.categoria,
    disponivel: r.disponivel
  }));

  console.log(JSON.stringify({ recompensas }));
}

main()
  .catch(e => { console.error(e); process.exit(1); })
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)
    logger.info(f"✅ Encontradas {len(result.get('recompensas', []))} recompensas")

    return result

@router.post("/resgatar", response_model=ResgatarResponse)
async def resgatar_recompensa(request: ResgatarRequest):
    """
    RESGATAR RECOMPENSA COM FOCUS POINTS

    Permite que o usuário troque seus FP por uma recompensa.

    ## Validações:
    1. Usuário existe e possui FP suficientes
    2. Recompensa existe e está disponível
    3. FP >= custoFP da recompensa

    ## Ações:
    1. Deduz FP do usuário
    2. Cria registro em UsuarioReward
    3. Retorna FP restante

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/rewards/resgatar', {
      method: 'POST',
      body: JSON.stringify({
        user_id: 'user@example.com',
        reward_id: 'clx123'
      })
    });
    const data = await response.json();

    // data.success - true/false
    // data.mensagem - mensagem de sucesso ou erro
    // data.fp_restante - FP após o resgate
    ```
    """
    logger.info(f"🎁 Tentando resgatar recompensa {request.reward_id} para {request.user_id}")

    script = f'''
import {{ PrismaClient }} from '@prisma/client';
const prisma = new PrismaClient();

async function main() {{
  // =========================================================================
  // 1. BUSCA USUÁRIO
  // =========================================================================
  const usuario = await prisma.usuario.findUnique({{
    where: {{ email: "{request.user_id}" }}
  }});

  if (!usuario) {{
    console.log(JSON.stringify({{
      success: false,
      mensagem: "Usuário não encontrado",
      fp_restante: 0
    }}));
    return;
  }}

  // =========================================================================
  // 2. BUSCA RECOMPENSA
  // =========================================================================
  const reward = await prisma.reward.findUnique({{
    where: {{ id: "{request.reward_id}" }}
  }});

  if (!reward) {{
    console.log(JSON.stringify({{
      success: false,
      mensagem: "Recompensa não encontrada",
      fp_restante: usuario.pontosFP || 0
    }}));
    return;
  }}

  if (!reward.disponivel) {{
    console.log(JSON.stringify({{
      success: false,
      mensagem: "Recompensa não está disponível no momento",
      fp_restante: usuario.pontosFP || 0
    }}));
    return;
  }}

  // =========================================================================
  // 3. VALIDA FP SUFICIENTE
  // =========================================================================
  const fpAtual = usuario.pontosFP || 0;

  if (fpAtual < reward.custoFP) {{
    console.log(JSON.stringify({{
      success: false,
      mensagem: `FP insuficiente. Você tem ${{fpAtual}} FP, mas precisa de ${{reward.custoFP}} FP`,
      fp_restante: fpAtual
    }}));
    return;
  }}

  // =========================================================================
  // 4. REALIZA RESGATE (TRANSAÇÃO)
  // =========================================================================
  const fpRestante = fpAtual - reward.custoFP;

  // Atualiza FP do usuário
  await prisma.usuario.update({{
    where: {{ id: usuario.id }},
    data: {{ pontosFP: fpRestante }}
  }});

  // Cria registro de resgate
  await prisma.usuarioReward.create({{
    data: {{
      usuarioId: usuario.id,
      rewardId: reward.id
    }}
  }});

  // =========================================================================
  // 5. RETORNA SUCESSO
  // =========================================================================
  console.log(JSON.stringify({{
    success: true,
    mensagem: `Recompensa "${{reward.titulo}}" resgatada com sucesso! 🎉`,
    fp_restante: fpRestante,
    recompensa: {{
      id: reward.id,
      titulo: reward.titulo,
      descricao: reward.descricao,
      custoFP: reward.custoFP,
      emoji: reward.emoji,
      categoria: reward.categoria,
      disponivel: reward.disponivel
    }}
  }}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)

    if result.get('success'):
        logger.info(f"✅ Resgate realizado: {result['mensagem']}")
    else:
        logger.warning(f"❌ Resgate falhou: {result['mensagem']}")

    return result
