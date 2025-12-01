"""
ENEM-IA Backend - Servidor FastAPI Unificado

Agrega todas as APIs do projeto:
- Explicação IA
- Reexplicar
- Resultados
- Simulados ENEM (novo)
- ENEM IA Layer 4

Uso:
    uvicorn main:app --reload --port 8000
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import dos routers
from routers.enem_simulados import router as simulados_router
from routers.auth import router as auth_router
from routers.enem_usuario import router as usuario_router
from routers.enem_stats import router as stats_router
from routers.enem_rewards import router as rewards_router
from routers.enem_challenges import router as challenges_router
from routers.enem_cursos import router as cursos_router

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# APLICAÇÃO FASTAPI PRINCIPAL
# ============================================================================

app = FastAPI(
    title="ENEM-IA Backend Unificado",
    description="API completa para plataforma ENEM-IA (Simulados, Explicações, Resultados)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================================
# CORS - Permite acesso do frontend Next.js
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:5500",  # Live Server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
        "https://enem-pro.vercel.app",  # Produção
        "*"  # Dev (remova em produção!)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

# 1. Router de Autenticação (Login/Register)
app.include_router(auth_router)
logger.info("✅ Router de Autenticação incluído")

# 2. Router de Simulados ENEM
app.include_router(simulados_router)
logger.info("✅ Router de Simulados ENEM incluído")

# 3. Router de Usuário (Stats, Profile, FP, Nível, Streak)
app.include_router(usuario_router, prefix="/api/enem/usuario", tags=["Usuario"])
logger.info("✅ Router de Usuário incluído")

# 4. Router de Estatísticas (Desempenho por área, Evolução)
app.include_router(stats_router, prefix="/api/enem/stats", tags=["Estatisticas"])
logger.info("✅ Router de Estatísticas incluído")

# 5. Router de Recompensas (Loja, Resgatar)
app.include_router(rewards_router, prefix="/api/enem/rewards", tags=["Recompensas"])
logger.info("✅ Router de Recompensas incluído")

# 6. Router de Desafios Semanais
app.include_router(challenges_router, prefix="/api/enem/challenges", tags=["Desafios"])
logger.info("✅ Router de Desafios incluído")

# 7. Router de Cursos e Notas de Corte
app.include_router(cursos_router, prefix="/api/enem/cursos", tags=["Cursos"])
logger.info("✅ Router de Cursos incluído")

# 8. Outros routers serão incluídos aqui no futuro:
# app.include_router(explicacao_router, prefix="/api/explicar")
# app.include_router(reexplicar_router, prefix="/api/reexplicar")
# app.include_router(resultados_router, prefix="/api/resultados")

# ============================================================================
# ENDPOINTS ROOT
# ============================================================================

@app.get("/")
async def root():
    """
    Endpoint raiz - Informações sobre a API

    Retorna:
        Status da API e lista de endpoints disponíveis
    """
    return {
        "status": "online",
        "service": "ENEM-IA Backend Unificado",
        "version": "2.0.0",
        "description": "API completa para plataforma ENEM-IA",
        "endpoints": {
            "auth": {
                "register": "POST /api/auth/register",
                "login": "POST /api/auth/login",
                "me": "GET /api/auth/me"
            },
            "simulados": {
                "start": "POST /api/enem/simulados/start",
                "answer": "POST /api/enem/simulados/answer",
                "finish": "POST /api/enem/simulados/finish",
                "history": "GET /api/enem/simulados/history",
                "compare": "POST /api/enem/simulados/compare-score"
            },
            "usuario": {
                "stats": "GET /api/enem/usuario/stats",
                "profile": "GET /api/enem/usuario/profile"
            },
            "stats": {
                "por_area": "GET /api/enem/stats/por-area",
                "evolucao": "GET /api/enem/stats/evolucao"
            },
            "rewards": {
                "loja": "GET /api/enem/rewards/loja",
                "resgatar": "POST /api/enem/rewards/resgatar"
            },
            "challenges": {
                "semana": "GET /api/enem/challenges/semana",
                "progresso": "POST /api/enem/challenges/progresso"
            },
            "docs": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        },
        "health_check": "/health"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint

    Verifica se a API está funcionando

    Retorna:
        Status de saúde da aplicação
    """
    from datetime import datetime

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ENEM-IA Backend",
        "version": "2.0.0"
    }

# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar o servidor"""
    logger.info("="*70)
    logger.info("🚀 ENEM-IA Backend Unificado")
    logger.info("="*70)
    logger.info("📦 Versão: 2.0.0")
    logger.info("📚 Documentação: http://localhost:8000/docs")
    logger.info("🔗 Routers carregados:")
    logger.info("   • Autenticação: /api/auth")
    logger.info("   • Simulados ENEM: /api/enem/simulados")
    logger.info("   • Usuário: /api/enem/usuario")
    logger.info("   • Estatísticas: /api/enem/stats")
    logger.info("   • Recompensas: /api/enem/rewards")
    logger.info("   • Desafios: /api/enem/challenges")
    logger.info("="*70)

@app.on_event("shutdown")
async def shutdown_event():
    """Executado ao encerrar o servidor"""
    logger.info("🛑 ENEM-IA Backend encerrado")

# ============================================================================
# EXECUÇÃO DIRETA (para desenvolvimento)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Iniciando servidor em modo desenvolvimento...")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload em desenvolvimento
        log_level="info"
    )
