"""
Autenticação - Router de Login e Registro

Endpoints:
- POST /api/auth/register - Registrar novo usuário
- POST /api/auth/login - Fazer login e receber token JWT
- GET /api/auth/me - Obter dados do usuário autenticado
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from auth_schemas import (
    ErrorResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UsuarioResponse,
)
from auth_utils import (
    create_user_token,
    get_current_user_id,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticação"],
)

# ============================================================================
# PRISMA CLIENT
# ============================================================================

# Importação do Prisma Client (assumindo que você usará prisma-client-py)
# Como o Prisma é usado no frontend Next.js, precisamos conectar via API
# ou usar uma biblioteca Python compatível

# Para esta implementação, vamos criar uma função auxiliar que simula
# a conexão com o banco de dados SQLite do Prisma

import sqlite3
from datetime import datetime
from pathlib import Path


def get_db_connection():
    """Conecta ao banco SQLite do Prisma"""
    db_path = Path(__file__).parent.parent / "enem_pro.db"
    return sqlite3.connect(str(db_path))


def dict_factory(cursor, row):
    """Converte resultados do SQLite em dicionários"""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário",
    responses={
        201: {"description": "Usuário criado com sucesso"},
        400: {"model": ErrorResponse, "description": "Email já cadastrado"},
    }
)
async def register(data: RegisterRequest) -> Any:
    """
    Registra um novo usuário no sistema

    - **email**: Email único do usuário (obrigatório)
    - **senha**: Senha com mínimo 6 caracteres (obrigatório)
    - **nome**: Nome completo do usuário (opcional)

    Retorna:
        Token JWT e dados do usuário criado
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Verificar se email já existe
        cursor.execute("SELECT id FROM Usuario WHERE email = ?", (data.email,))
        existing_user = cursor.fetchone()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )

        # Criar hash da senha
        hashed_password = hash_password(data.senha)

        # Gerar ID único (simulando cuid())
        import secrets
        user_id = "u_" + secrets.token_urlsafe(16)

        # Inserir novo usuário
        now = datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO Usuario (id, nome, email, senha, createdAt)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, data.nome, data.email, hashed_password, now)
        )
        conn.commit()

        # Buscar usuário criado
        cursor.execute(
            "SELECT id, nome, email, createdAt FROM Usuario WHERE id = ?",
            (user_id,)
        )
        user = cursor.fetchone()
        conn.close()

        # Criar token JWT
        token = create_user_token(user["id"], user["email"])

        logger.info(f"✅ Novo usuário registrado: {user['email']}")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            usuario=UsuarioResponse(**user)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao registrar usuário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registrar usuário: {str(e)}"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Fazer login",
    responses={
        200: {"description": "Login realizado com sucesso"},
        401: {"model": ErrorResponse, "description": "Credenciais inválidas"},
    }
)
async def login(data: LoginRequest) -> Any:
    """
    Faz login no sistema

    - **email**: Email do usuário
    - **senha**: Senha do usuário

    Retorna:
        Token JWT e dados do usuário autenticado
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Buscar usuário por email
        cursor.execute(
            "SELECT id, nome, email, senha, createdAt FROM Usuario WHERE email = ?",
            (data.email,)
        )
        user = cursor.fetchone()
        conn.close()

        # Verificar se usuário existe
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        # Verificar senha
        if not verify_password(data.senha, user["senha"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )

        # Criar token JWT
        token = create_user_token(user["id"], user["email"])

        # Remover senha da resposta
        user_response = {k: v for k, v in user.items() if k != "senha"}

        logger.info(f"✅ Login realizado: {user['email']}")

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            usuario=UsuarioResponse(**user_response)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao fazer login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer login: {str(e)}"
        )


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Obter usuário autenticado",
    responses={
        200: {"description": "Dados do usuário"},
        401: {"model": ErrorResponse, "description": "Não autenticado"},
    }
)
async def get_me(user_id: str = Depends(get_current_user_id)) -> Any:
    """
    Retorna dados do usuário autenticado

    Requer:
        Header Authorization: Bearer <token>

    Retorna:
        Dados do usuário (sem senha)
    """
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        # Buscar usuário
        cursor.execute(
            "SELECT id, nome, email, createdAt FROM Usuario WHERE id = ?",
            (user_id,)
        )
        user = cursor.fetchone()
        conn.close()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )

        return UsuarioResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar usuário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar usuário: {str(e)}"
        )
