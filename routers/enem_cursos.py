"""
Router para gerenciamento de cursos e notas de corte.
Permite que usuários escolham curso alvo e comparem suas notas.
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
import subprocess
import json
from typing import Optional

router = APIRouter()

# ========================================
#  MODELOS DE RESPOSTA
# ========================================

class CourseResponse(BaseModel):
    id: str
    nome: str
    ies: str
    campus: Optional[str]
    turno: Optional[str]
    notaCorte: float
    anoReferencia: int

class UserCourseResponse(BaseModel):
    has_curso: bool
    curso: Optional[CourseResponse]

class SetCourseRequest(BaseModel):
    user_id: str
    course_id: Optional[str]  # null = remover curso alvo

class SetCourseResponse(BaseModel):
    success: bool
    curso: Optional[CourseResponse]
    mensagem: str

# ========================================
#  ENDPOINTS
# ========================================

@router.get("/user/curso", response_model=UserCourseResponse)
async def get_user_curso(user_id: str = Query(..., description="ID do usuário")):
    """
    Retorna o curso alvo do usuário.
    Se não tiver curso escolhido, retorna has_curso=false.
    """
    script = f"""
    import {{ PrismaClient }} from '@prisma/client';
    const prisma = new PrismaClient();

    try {{
      const usuario = await prisma.usuario.findUnique({{
        where: {{ id: "{user_id}" }},
        include: {{ cursoAlvo: true }}
      }});

      if (!usuario || !usuario.cursoAlvo) {{
        console.log(JSON.stringify({{ has_curso: false, curso: null }}));
      }} else {{
        console.log(JSON.stringify({{
          has_curso: true,
          curso: usuario.cursoAlvo
        }}));
      }}
    }} catch (error) {{
      console.error(JSON.stringify({{ error: error.message }}));
      process.exit(1);
    }} finally {{
      await prisma.$disconnect();
    }}
    """

    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd="../enem-pro"
    )

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar curso: {result.stderr}")

    data = json.loads(result.stdout.strip())
    return data


@router.get("/cursos", response_model=list[CourseResponse])
async def list_cursos(
    search: Optional[str] = Query(None, description="Busca por nome do curso ou IES"),
    limit: int = Query(50, description="Limite de resultados")
):
    """
    Lista cursos disponíveis com busca opcional.
    Retorna cursos ativos ordenados por IES e nome.
    """
    # Construir cláusula WHERE dinamicamente
    # NOTA: SQLite não suporta mode:'insensitive', então removemos
    where_clause = ""
    if search:
        # Escapar aspas na busca
        search_escaped = search.replace('"', '\\"').replace("'", "\\'")
        where_clause = f"""
        where: {{
          ativo: true,
          OR: [
            {{ nome: {{ contains: "{search_escaped}" }} }},
            {{ ies: {{ contains: "{search_escaped}" }} }},
            {{ campus: {{ contains: "{search_escaped}" }} }}
          ]
        }},
        """
    else:
        where_clause = "where: { ativo: true },"

    script = f"""
    import {{ PrismaClient }} from '@prisma/client';
    const prisma = new PrismaClient();

    try {{
      const cursos = await prisma.course.findMany({{
        {where_clause}
        orderBy: [
          {{ ies: 'asc' }},
          {{ nome: 'asc' }}
        ],
        take: {limit}
      }});

      console.log(JSON.stringify(cursos));
    }} catch (error) {{
      console.error(JSON.stringify({{ error: error.message }}));
      process.exit(1);
    }} finally {{
      await prisma.$disconnect();
    }}
    """

    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd="../enem-pro"
    )

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Erro ao listar cursos: {result.stderr}")

    cursos = json.loads(result.stdout.strip())
    return cursos


@router.post("/user/curso", response_model=SetCourseResponse)
async def set_user_curso(req: SetCourseRequest):
    """
    Define ou remove curso alvo do usuário.
    Se course_id for null, remove o curso alvo.
    """
    # Construir valor para cursoAlvoId
    curso_id_value = f'"{req.course_id}"' if req.course_id else 'null'

    script = f"""
    import {{ PrismaClient }} from '@prisma/client';
    const prisma = new PrismaClient();

    try {{
      const usuario = await prisma.usuario.update({{
        where: {{ id: "{req.user_id}" }},
        data: {{ cursoAlvoId: {curso_id_value} }},
        include: {{ cursoAlvo: true }}
      }});

      const mensagem = usuario.cursoAlvo
        ? `Curso alvo definido: ${{usuario.cursoAlvo.nome}} - ${{usuario.cursoAlvo.ies}}`
        : 'Curso alvo removido';

      console.log(JSON.stringify({{
        success: true,
        curso: usuario.cursoAlvo,
        mensagem: mensagem
      }}));
    }} catch (error) {{
      console.error(JSON.stringify({{
        success: false,
        curso: null,
        mensagem: `Erro ao definir curso: ${{error.message}}`
      }}));
      process.exit(1);
    }} finally {{
      await prisma.$disconnect();
    }}
    """

    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd="../enem-pro"
    )

    if result.returncode != 0:
        # Tentar parsear mensagem de erro
        try:
            error_data = json.loads(result.stdout.strip())
            return error_data
        except:
            raise HTTPException(status_code=500, detail=f"Erro ao definir curso: {result.stderr}")

    data = json.loads(result.stdout.strip())
    return data
