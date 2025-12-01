"""
Autenticação - Schemas Pydantic

Modelos de validação para requisições e respostas de autenticação
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# SCHEMAS DE REQUISIÇÃO
# ============================================================================

class RegisterRequest(BaseModel):
    """
    Schema para registro de novo usuário

    Exemplo:
        {
            "nome": "João Silva",
            "email": "joao@email.com",
            "senha": "senha123"
        }
    """
    nome: Optional[str] = Field(None, description="Nome completo do usuário")
    email: EmailStr = Field(..., description="Email único do usuário")
    senha: str = Field(..., min_length=6, description="Senha com mínimo 6 caracteres")

    class Config:
        json_schema_extra = {
            "example": {
                "nome": "João Silva",
                "email": "joao@email.com",
                "senha": "senha123"
            }
        }


class LoginRequest(BaseModel):
    """
    Schema para login de usuário

    Exemplo:
        {
            "email": "joao@email.com",
            "senha": "senha123"
        }
    """
    email: EmailStr = Field(..., description="Email do usuário")
    senha: str = Field(..., description="Senha do usuário")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "joao@email.com",
                "senha": "senha123"
            }
        }


# ============================================================================
# SCHEMAS DE RESPOSTA
# ============================================================================

class UsuarioResponse(BaseModel):
    """
    Schema de resposta com dados públicos do usuário

    Exemplo:
        {
            "id": "clx123abc",
            "nome": "João Silva",
            "email": "joao@email.com",
            "createdAt": "2025-11-14T10:30:00Z"
        }
    """
    id: str
    nome: Optional[str]
    email: str
    createdAt: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """
    Schema de resposta com token JWT

    Exemplo:
        {
            "access_token": "eyJhbGci...",
            "token_type": "bearer",
            "usuario": {
                "id": "clx123abc",
                "nome": "João Silva",
                "email": "joao@email.com"
            }
        }
    """
    access_token: str = Field(..., description="Token JWT de autenticação")
    token_type: str = Field(default="bearer", description="Tipo do token (sempre bearer)")
    usuario: UsuarioResponse = Field(..., description="Dados do usuário autenticado")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "usuario": {
                    "id": "clx123abc",
                    "nome": "João Silva",
                    "email": "joao@email.com",
                    "createdAt": "2025-11-14T10:30:00Z"
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Schema padrão de erro

    Exemplo:
        {
            "detail": "Email já cadastrado"
        }
    """
    detail: str = Field(..., description="Mensagem de erro")
