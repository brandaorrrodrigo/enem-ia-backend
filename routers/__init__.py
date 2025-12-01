"""
Routers do Backend ENEM-IA

Estrutura modular de rotas FastAPI
"""

from .enem_simulados import router as simulados_router

__all__ = ['simulados_router']
