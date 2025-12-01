"""
Router de Desafios Semanais ENEM - Sistema de Missões

Endpoints para gerenciar desafios semanais e progresso

ROTAS:
- GET /api/enem/challenges/semana - Desafio da semana atual
- POST /api/enem/challenges/progresso - Atualiza progresso do usuário
"""

import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

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

class DesafioSemana(BaseModel):
    id: str
    titulo: str
    descricao: str
    meta: int
    recompensaFP: int
    emoji: str
    inicio: str
    fim: str
    progresso_atual: int
    concluido: bool

class DesafioSemanaResponse(BaseModel):
    desafio: Optional[DesafioSemana]
    mensagem: Optional[str] = None

class ProgressoRequest(BaseModel):
    user_id: str
    challenge_id: str
    incremento: int = 1

class ProgressoResponse(BaseModel):
    success: bool
    mensagem: str
    progresso_atual: int
    meta: int
    concluido: bool
    fp_ganhos: int

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

@router.get("/semana", response_model=DesafioSemanaResponse)
async def get_desafio_semana(user_id: str = Query(..., description="Email/ID do usuário")):
    """
    DESAFIO DA SEMANA ATUAL

    Retorna o desafio ativo da semana com progresso do usuário.

    ## Critérios:
    - Busca desafio onde data atual está entre inicio e fim
    - Retorna progresso do usuário para esse desafio
    - Se não houver desafio ativo, retorna null

    ## Exemplo de Desafios:
    - 📚 Faça 5 simulados esta semana (+200 FP)
    - 🎯 Acerte 80% em um simulado (+150 FP)
    - 🔥 Estude 7 dias consecutivos (+300 FP)

    ## Exemplo de uso (Frontend):
    ```javascript
    const response = await fetch('/api/enem/challenges/semana?user_id=user@example.com');
    const data = await response.json();

    // data.desafio - objeto com:
    // {id: "clx1", titulo: "5 Simulados", meta: 5, progresso_atual: 2, concluido: false}
    ```
    """
    logger.info(f"🎯 Buscando desafio da semana para {user_id}")

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
      desafio: null,
      mensagem: "Usuário não encontrado"
    }}));
    return;
  }}

  // =========================================================================
  // 2. BUSCA DESAFIO ATIVO DA SEMANA
  // =========================================================================
  const agora = new Date();

  const desafioAtivo = await prisma.weeklyChallenge.findFirst({{
    where: {{
      inicio: {{ lte: agora }},
      fim: {{ gte: agora }}
    }}
  }});

  if (!desafioAtivo) {{
    console.log(JSON.stringify({{
      desafio: null,
      mensagem: "Nenhum desafio ativo no momento"
    }}));
    return;
  }}

  // =========================================================================
  // 3. BUSCA PROGRESSO DO USUÁRIO
  // =========================================================================
  let progressoRegistro = await prisma.usuarioChallenge.findFirst({{
    where: {{
      usuarioId: usuario.id,
      challengeId: desafioAtivo.id
    }}
  }});

  // Se não existe, cria com progresso 0
  if (!progressoRegistro) {{
    progressoRegistro = await prisma.usuarioChallenge.create({{
      data: {{
        usuarioId: usuario.id,
        challengeId: desafioAtivo.id,
        progresso: 0,
        concluido: false
      }}
    }});
  }}

  // =========================================================================
  // 4. RETORNA DESAFIO COM PROGRESSO
  // =========================================================================
  const concluido = progressoRegistro.progresso >= desafioAtivo.meta;

  console.log(JSON.stringify({{
    desafio: {{
      id: desafioAtivo.id,
      titulo: desafioAtivo.titulo,
      descricao: desafioAtivo.descricao,
      meta: desafioAtivo.meta,
      recompensaFP: desafioAtivo.recompensaFP,
      emoji: desafioAtivo.emoji,
      inicio: desafioAtivo.inicio,
      fim: desafioAtivo.fim,
      progresso_atual: progressoRegistro.progresso,
      concluido: concluido
    }}
  }}));
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)

    if result.get('desafio'):
        logger.info(f"✅ Desafio encontrado: {result['desafio']['titulo']}")
    else:
        logger.info(f"ℹ️ {result.get('mensagem', 'Sem desafio ativo')}")

    return result

@router.post("/progresso", response_model=ProgressoResponse)
async def atualizar_progresso(request: ProgressoRequest):
    """
    ATUALIZAR PROGRESSO DO DESAFIO

    Incrementa o progresso do usuário em um desafio.

    ## Casos de Uso:
    - Usuário finalizou simulado → incremento = 1
    - Usuário atingiu meta de acertos → incremento = 1
    - Sistema detecta dia consecutivo → incremento = 1

    ## Lógica:
    1. Incrementa progresso
    2. Verifica se atingiu a meta
    3. Se completou, marca como concluído e adiciona FP

    ## Exemplo de uso (Frontend):
    ```javascript
    // Após finalizar simulado
    const response = await fetch('/api/enem/challenges/progresso', {
      method: 'POST',
      body: JSON.stringify({
        user_id: 'user@example.com',
        challenge_id: 'clx123',
        incremento: 1
      })
    });
    const data = await response.json();

    // data.concluido - true se completou desafio
    // data.fp_ganhos - FP ganhos (se completou)
    ```
    """
    logger.info(f"⚡ Atualizando progresso do desafio {request.challenge_id} para {request.user_id}")

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
      progresso_atual: 0,
      meta: 0,
      concluido: false,
      fp_ganhos: 0
    }}));
    return;
  }}

  // =========================================================================
  // 2. BUSCA DESAFIO
  // =========================================================================
  const desafio = await prisma.weeklyChallenge.findUnique({{
    where: {{ id: "{request.challenge_id}" }}
  }});

  if (!desafio) {{
    console.log(JSON.stringify({{
      success: false,
      mensagem: "Desafio não encontrado",
      progresso_atual: 0,
      meta: 0,
      concluido: false,
      fp_ganhos: 0
    }}));
    return;
  }}

  // =========================================================================
  // 3. BUSCA OU CRIA PROGRESSO DO USUÁRIO
  // =========================================================================
  let progressoRegistro = await prisma.usuarioChallenge.findFirst({{
    where: {{
      usuarioId: usuario.id,
      challengeId: desafio.id
    }}
  }});

  if (!progressoRegistro) {{
    progressoRegistro = await prisma.usuarioChallenge.create({{
      data: {{
        usuarioId: usuario.id,
        challengeId: desafio.id,
        progresso: 0,
        concluido: false
      }}
    }});
  }}

  // =========================================================================
  // 4. INCREMENTA PROGRESSO
  // =========================================================================
  const novoProgresso = progressoRegistro.progresso + {request.incremento};
  const atingiuMeta = novoProgresso >= desafio.meta;
  const jaConcluido = progressoRegistro.concluido;

  let fpGanhos = 0;

  // Se completou agora (não estava concluído antes)
  if (atingiuMeta && !jaConcluido) {{
    // Atualiza progresso e marca como concluído
    await prisma.usuarioChallenge.update({{
      where: {{ id: progressoRegistro.id }},
      data: {{
        progresso: novoProgresso,
        concluido: true
      }}
    }});

    // Adiciona FP ao usuário
    const fpAtual = usuario.pontosFP || 0;
    await prisma.usuario.update({{
      where: {{ id: usuario.id }},
      data: {{ pontosFP: fpAtual + desafio.recompensaFP }}
    }});

    fpGanhos = desafio.recompensaFP;

    console.log(JSON.stringify({{
      success: true,
      mensagem: `🎉 Desafio "${{desafio.titulo}}" concluído! +${{fpGanhos}} FP`,
      progresso_atual: novoProgresso,
      meta: desafio.meta,
      concluido: true,
      fp_ganhos: fpGanhos
    }}));
  }} else {{
    // Apenas atualiza progresso
    await prisma.usuarioChallenge.update({{
      where: {{ id: progressoRegistro.id }},
      data: {{ progresso: novoProgresso }}
    }});

    console.log(JSON.stringify({{
      success: true,
      mensagem: jaConcluido
        ? "Desafio já foi concluído anteriormente"
        : `Progresso atualizado: ${{novoProgresso}}/${{desafio.meta}}`,
      progresso_atual: novoProgresso,
      meta: desafio.meta,
      concluido: atingiuMeta,
      fp_ganhos: 0
    }}));
  }}
}}

main()
  .catch(e => {{ console.error(e); process.exit(1); }})
  .finally(() => prisma.$disconnect());
'''

    result = run_prisma_script(script)

    if result.get('success'):
        logger.info(f"✅ {result['mensagem']}")
    else:
        logger.warning(f"❌ {result.get('mensagem', 'Erro desconhecido')}")

    return result
