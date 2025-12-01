"""
Pipeline Completo ENEM: PDF → Texto → JSON → Prisma

Orquestra todo o processo de ingestão de questões do ENEM
"""

import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional

from enem_parser import EnemParser
from enem_validator import EnemValidator
from import_to_prisma import PrismaImporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnemPipeline:
    """Pipeline completo de ingestão de questões ENEM"""

    def __init__(
        self,
        prisma_project_path: Optional[Path] = None,
        strict_validation: bool = False
    ):
        """
        Inicializa o pipeline

        Args:
            prisma_project_path: Caminho do projeto Prisma (opcional)
            strict_validation: Modo estrito de validação
        """
        self.parser = EnemParser()
        self.validator = EnemValidator(strict_mode=strict_validation)
        self.importer = PrismaImporter(prisma_project_path)
        self.strict_validation = strict_validation

    def executar(
        self,
        input_source: Path,
        output_json: Optional[Path] = None,
        skip_import: bool = False
    ) -> Dict:
        """
        Executa pipeline completo

        Args:
            input_source: Arquivo JSON ou texto com questões
            output_json: Salva JSON padronizado (opcional)
            skip_import: Se True, não importa para Prisma

        Returns:
            Estatísticas da execução
        """
        logger.info("="*70)
        logger.info("🚀 PIPELINE ENEM - INÍCIO")
        logger.info("="*70)

        stats = {
            'input_file': str(input_source),
            'total_parseadas': 0,
            'total_validas': 0,
            'total_invalidas': 0,
            'total_importadas': 0,
            'erros': []
        }

        # ========================================================================
        # PASSO 1: PARSING
        # ========================================================================

        logger.info(f"\n📝 PASSO 1: Parsing de {input_source.name}")
        logger.info("-"*70)

        try:
            if input_source.suffix == '.json':
                questoes = self.parser.parse_from_json_file(input_source)
            else:
                # Assume texto plano
                with open(input_source, 'r', encoding='utf-8') as f:
                    texto = f.read()
                questoes = self.parser.parse_from_text(texto)

            stats['total_parseadas'] = len(questoes)
            logger.info(f"✅ {len(questoes)} questões parseadas")

            if not questoes:
                logger.error("❌ Nenhuma questão encontrada no arquivo")
                stats['erros'].append("Nenhuma questão parseada")
                return stats

        except Exception as e:
            logger.error(f"❌ Erro no parsing: {e}")
            stats['erros'].append(f"Parsing: {str(e)}")
            return stats

        # ========================================================================
        # PASSO 2: VALIDAÇÃO
        # ========================================================================

        logger.info(f"\n✅ PASSO 2: Validação de questões")
        logger.info("-"*70)

        validation_stats = self.validator.validar_lote(questoes)

        stats['total_validas'] = validation_stats['validas']
        stats['total_invalidas'] = validation_stats['invalidas']

        # Filtra apenas questões válidas
        questoes_validas = []
        for questao in questoes:
            is_valid, erros, avisos = self.validator.validar_questao(questao)
            if is_valid:
                questoes_validas.append(questao)

        logger.info(f"\n✅ {len(questoes_validas)} questões válidas para importação")

        if not questoes_validas:
            logger.error("❌ Nenhuma questão válida para importar")
            stats['erros'].append("Todas as questões são inválidas")
            return stats

        # ========================================================================
        # PASSO 3: EXPORTAÇÃO JSON (Opcional)
        # ========================================================================

        if output_json:
            logger.info(f"\n💾 PASSO 3: Exportando JSON padronizado")
            logger.info("-"*70)

            try:
                self.parser.export_to_json(output_json, questoes_validas)
                logger.info(f"✅ JSON exportado: {output_json}")
            except Exception as e:
                logger.error(f"❌ Erro ao exportar JSON: {e}")
                stats['erros'].append(f"Export JSON: {str(e)}")

        # ========================================================================
        # PASSO 4: IMPORTAÇÃO PRISMA
        # ========================================================================

        if not skip_import:
            logger.info(f"\n🗄️  PASSO 4: Importação para Prisma")
            logger.info("-"*70)

            try:
                result = self.importer.importar_questoes(questoes_validas)

                if result['success']:
                    stats['total_importadas'] = result['importadas']
                    logger.info(f"✅ {result['importadas']} questões importadas")
                else:
                    logger.error(f"❌ Importação falhou: {result['mensagem']}")
                    stats['erros'].append(f"Import: {result['mensagem']}")

            except Exception as e:
                logger.error(f"❌ Erro na importação: {e}")
                stats['erros'].append(f"Import: {str(e)}")
        else:
            logger.info("\n⏭️  Importação pulada (--skip-import)")

        # ========================================================================
        # RESUMO FINAL
        # ========================================================================

        logger.info("\n" + "="*70)
        logger.info("📊 RESUMO DA EXECUÇÃO")
        logger.info("="*70)
        logger.info(f"📝 Questões parseadas: {stats['total_parseadas']}")
        logger.info(f"✅ Questões válidas: {stats['total_validas']}")
        logger.info(f"❌ Questões inválidas: {stats['total_invalidas']}")

        if not skip_import:
            logger.info(f"🗄️  Questões importadas: {stats['total_importadas']}")

        if stats['erros']:
            logger.info(f"⚠️  Erros: {len(stats['erros'])}")
            for erro in stats['erros']:
                logger.info(f"   • {erro}")

        logger.info("="*70)

        return stats


def main():
    """CLI do pipeline"""
    parser = argparse.ArgumentParser(
        description='Pipeline ENEM: PDF → JSON → Prisma',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos de uso:

  # Importar de JSON
  python pipeline_completo.py questoes.json

  # Exportar JSON padronizado antes de importar
  python pipeline_completo.py questoes.json --output questoes_padrao.json

  # Validar sem importar
  python pipeline_completo.py questoes.json --skip-import

  # Validação estrita
  python pipeline_completo.py questoes.json --strict
        '''
    )

    parser.add_argument(
        'input',
        type=Path,
        help='Arquivo de entrada (JSON ou TXT)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Salva JSON padronizado antes de importar'
    )

    parser.add_argument(
        '--skip-import',
        action='store_true',
        help='Apenas parseia e valida, não importa para Prisma'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Validação estrita (avisos também invalidam)'
    )

    parser.add_argument(
        '--prisma-path',
        type=Path,
        help='Caminho do projeto Prisma (auto-detecta se omitido)'
    )

    args = parser.parse_args()

    # Valida input
    if not args.input.exists():
        print(f"❌ Arquivo não encontrado: {args.input}")
        return 1

    # Executa pipeline
    try:
        pipeline = EnemPipeline(
            prisma_project_path=args.prisma_path,
            strict_validation=args.strict
        )

        stats = pipeline.executar(
            input_source=args.input,
            output_json=args.output,
            skip_import=args.skip_import
        )

        # Exit code baseado no sucesso
        if stats['erros']:
            return 1
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrompido pelo usuário")
        return 130

    except Exception as e:
        print(f"\n💥 Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
