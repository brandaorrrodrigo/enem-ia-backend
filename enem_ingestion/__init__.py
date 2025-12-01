"""
Módulo de Ingestão de Questões do ENEM

Pipeline completo: PDF → Texto → JSON → Prisma

Componentes:
- enem_parser.py: Extração e parsing de questões
- enem_validator.py: Validação de dados
- import_to_prisma.py: Importação para banco Prisma
"""

from .enem_parser import EnemParser, parse_questao_from_text
from .enem_validator import EnemValidator, validar_questao
from .import_to_prisma import PrismaImporter, import_questoes_to_prisma

__all__ = [
    'EnemParser',
    'parse_questao_from_text',
    'EnemValidator',
    'validar_questao',
    'PrismaImporter',
    'import_questoes_to_prisma'
]

__version__ = '1.0.0'
