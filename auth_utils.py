"""
Autenticação - Utilitários JWT e Hashing de Senhas

Funções para gerenciar autenticação de usuários:
- Hashing e verificação de senhas com bcrypt
- Criação e validação de tokens JWT
- Dependências FastAPI para proteção de rotas
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

# Chave secreta para JWT (em produção, use variável de ambiente)
SECRET_KEY = "sua-chave-secreta-super-segura-aqui-mude-em-producao"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias

# Contexto de criptografia para senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de segurança Bearer
security = HTTPBearer()

# ============================================================================
# FUNÇÕES DE HASHING DE SENHA
# ============================================================================

def hash_password(password: str) -> str:
    """
    Gera hash bcrypt de uma senha

    Args:
        password: Senha em texto plano

    Returns:
        Hash bcrypt da senha
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se senha corresponde ao hash

    Args:
        plain_password: Senha em texto plano
        hashed_password: Hash bcrypt armazenado

    Returns:
        True se a senha está correta
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# FUNÇÕES DE JWT
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT

    Args:
        data: Dados a codificar no token (ex: {"sub": "user_id"})
        expires_delta: Tempo de expiração customizado

    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decodifica e valida um token JWT

    Args:
        token: Token JWT a decodificar

    Returns:
        Payload do token

    Raises:
        HTTPException: Se token inválido ou expirado
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# DEPENDÊNCIAS FASTAPI
# ============================================================================

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Dependência FastAPI: Extrai user_id do token JWT

    Uso:
        @app.get("/protected")
        async def protected_route(user_id: str = Depends(get_current_user_id)):
            return {"user_id": user_id}

    Args:
        credentials: Credenciais Bearer extraídas do header Authorization

    Returns:
        ID do usuário autenticado

    Raises:
        HTTPException 401: Se token inválido ou sem subject
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: sem subject",
        )

    return user_id


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def create_user_token(user_id: str, email: str) -> str:
    """
    Cria token JWT para um usuário

    Args:
        user_id: ID do usuário
        email: Email do usuário

    Returns:
        Token JWT
    """
    return create_access_token(
        data={"sub": user_id, "email": email}
    )
