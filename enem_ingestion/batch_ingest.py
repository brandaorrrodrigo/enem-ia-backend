"""
Batch ENEM Ingestion - Process multiple PDFs at once

Scans pdfs_enem/ folder, extracts questions from all PDFs,
deduplicates, and saves to a single JSON file.

Usage:
    python batch_ingest.py
    python batch_ingest.py --output custom_output.json
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional
from datetime import datetime
import sys

# Import existing pipeline components
from pipeline_completo import EnemPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# PDF TEXT EXTRACTION
# ============================================================================

def extrair_texto_pdf(pdf_path: Path) -> Optional[str]:
    """
    Extrai texto de um PDF

    Tenta múltiplas bibliotecas em ordem de preferência:
    1. PyPDF2
    2. pdfplumber
    3. pypdf (fallback)

    Args:
        pdf_path: Caminho do PDF

    Returns:
        Texto extraído ou None se falhar
    """
    try:
        # Tentativa 1: PyPDF2
        try:
            import PyPDF2

            texto = []
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)

                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    texto.append(page.extract_text())

            resultado = '\n'.join(texto)
            if resultado.strip():
                logger.info(f"   ✅ Extraído com PyPDF2 ({len(resultado)} caracteres)")
                return resultado

        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"   PyPDF2 falhou: {e}")

        # Tentativa 2: pdfplumber
        try:
            import pdfplumber

            texto = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        texto.append(page_text)

            resultado = '\n'.join(texto)
            if resultado.strip():
                logger.info(f"   ✅ Extraído com pdfplumber ({len(resultado)} caracteres)")
                return resultado

        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"   pdfplumber falhou: {e}")

        # Tentativa 3: pypdf (fallback)
        try:
            import pypdf

            texto = []
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    texto.append(page.extract_text())

            resultado = '\n'.join(texto)
            if resultado.strip():
                logger.info(f"   ✅ Extraído com pypdf ({len(resultado)} caracteres)")
                return resultado

        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"   pypdf falhou: {e}")

        logger.error(f"   ❌ Nenhuma biblioteca de PDF disponível")
        logger.error(f"   💡 Instale: pip install PyPDF2 ou pip install pdfplumber")
        return None

    except Exception as e:
        logger.error(f"   ❌ Erro ao extrair texto: {e}")
        return None


# ============================================================================
# DEDUPLICATION
# ============================================================================

def criar_hash_questao(questao: Dict) -> str:
    """
    Cria um hash único para uma questão

    Usa: enunciado + alternativas (concatenadas)

    Args:
        questao: Dicionário da questão

    Returns:
        Hash MD5 da questão
    """
    # Concatena enunciado + todas as alternativas
    conteudo = questao.get('enunciado', '').strip().lower()

    alternativas = questao.get('alternativas', {})
    if isinstance(alternativas, dict):
        for letra in ['A', 'B', 'C', 'D', 'E']:
            conteudo += alternativas.get(letra, '').strip().lower()
    elif isinstance(alternativas, list):
        for alt in alternativas:
            conteudo += str(alt).strip().lower()

    # Gera hash
    return hashlib.md5(conteudo.encode('utf-8')).hexdigest()


def deduplicate_questoes(questoes: List[Dict]) -> List[Dict]:
    """
    Remove questões duplicadas

    Critérios de deduplicação (em ordem de prioridade):
    1. Se tiver 'numero' + 'ano', usa como chave única
    2. Caso contrário, usa hash do conteúdo

    Args:
        questoes: Lista de questões

    Returns:
        Lista de questões únicas
    """
    questoes_unicas = []
    hashes_vistos: Set[str] = set()
    chaves_vistas: Set[str] = set()

    duplicadas = 0

    for questao in questoes:
        # Método 1: Chave oficial (numero + ano)
        numero = questao.get('numero')
        ano = questao.get('ano')

        if numero and ano:
            chave = f"{ano}-{numero}"
            if chave in chaves_vistas:
                duplicadas += 1
                logger.debug(f"   ⏭️  Duplicada (chave): {chave}")
                continue
            chaves_vistas.add(chave)
            questoes_unicas.append(questao)
            continue

        # Método 2: Hash do conteúdo
        hash_questao = criar_hash_questao(questao)

        if hash_questao in hashes_vistos:
            duplicadas += 1
            logger.debug(f"   ⏭️  Duplicada (hash): {hash_questao[:8]}...")
            continue

        hashes_vistos.add(hash_questao)
        questoes_unicas.append(questao)

    logger.info(f"\n🔍 Deduplicação:")
    logger.info(f"   📝 Total de questões: {len(questoes)}")
    logger.info(f"   ✅ Únicas: {len(questoes_unicas)}")
    logger.info(f"   ⏭️  Duplicadas removidas: {duplicadas}")

    return questoes_unicas


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def processar_pdfs_em_lote(
    pdfs_dir: Path,
    output_json: Path,
    skip_validation: bool = False
) -> Dict:
    """
    Processa todos os PDFs de uma pasta e gera um JSON único

    Args:
        pdfs_dir: Diretório com os PDFs
        output_json: Arquivo JSON de saída
        skip_validation: Se True, pula validação estrita

    Returns:
        Estatísticas do processamento
    """
    logger.info("="*80)
    logger.info("🚀 BATCH ENEM INGESTION")
    logger.info("="*80)
    logger.info(f"📂 Pasta de PDFs: {pdfs_dir}")
    logger.info(f"💾 Arquivo de saída: {output_json}")
    logger.info("="*80)

    # Buscar todos os PDFs
    pdf_files = sorted(pdfs_dir.glob('*.pdf'))

    if not pdf_files:
        logger.error(f"\n❌ Nenhum PDF encontrado em: {pdfs_dir}")
        logger.info(f"\n💡 Coloque seus PDFs do ENEM na pasta: {pdfs_dir}")
        return {
            'success': False,
            'error': 'Nenhum PDF encontrado'
        }

    logger.info(f"\n📚 Encontrados {len(pdf_files)} PDFs")

    # Inicializar pipeline (sem importar para Prisma)
    pipeline = EnemPipeline(
        prisma_project_path=None,
        strict_validation=not skip_validation
    )

    # Estatísticas globais
    stats = {
        'total_pdfs': len(pdf_files),
        'pdfs_processados': 0,
        'pdfs_falhados': 0,
        'total_questoes_parseadas': 0,
        'total_questoes_validas': 0,
        'total_questoes_unicas': 0,
        'pdfs_com_erro': [],
        'inicio': datetime.now().isoformat(),
    }

    # Coletar todas as questões
    todas_questoes: List[Dict] = []

    # Processar cada PDF
    logger.info("\n" + "="*80)
    logger.info("PROCESSANDO PDFs")
    logger.info("="*80 + "\n")

    for idx, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n[{idx}/{len(pdf_files)}] 📄 {pdf_path.name}")
        logger.info("-" * 60)

        try:
            # 1. Extrair texto do PDF
            logger.info("   🔍 Extraindo texto do PDF...")
            texto_pdf = extrair_texto_pdf(pdf_path)

            if not texto_pdf or len(texto_pdf.strip()) < 100:
                logger.warning(f"   ⚠️  PDF vazio ou texto insuficiente")
                stats['pdfs_falhados'] += 1
                stats['pdfs_com_erro'].append({
                    'arquivo': pdf_path.name,
                    'erro': 'Texto vazio ou insuficiente'
                })
                continue

            # 2. Parsear questões usando o pipeline existente
            logger.info(f"   📝 Parseando questões...")

            try:
                questoes = pipeline.parser.parse_from_text(
                    texto_pdf,
                    metadata={'fonte': pdf_path.name}
                )

                if not questoes:
                    logger.warning(f"   ⚠️  Nenhuma questão encontrada")
                    stats['pdfs_falhados'] += 1
                    stats['pdfs_com_erro'].append({
                        'arquivo': pdf_path.name,
                        'erro': 'Nenhuma questão parseada'
                    })
                    continue

                logger.info(f"   ✅ {len(questoes)} questões parseadas")
                stats['total_questoes_parseadas'] += len(questoes)

            except Exception as e:
                logger.error(f"   ❌ Erro no parsing: {e}")
                stats['pdfs_falhados'] += 1
                stats['pdfs_com_erro'].append({
                    'arquivo': pdf_path.name,
                    'erro': f'Parsing: {str(e)}'
                })
                continue

            # 3. Validar questões
            logger.info(f"   ✅ Validando questões...")

            questoes_validas = []
            for questao in questoes:
                is_valid, erros, avisos = pipeline.validator.validar_questao(questao)
                if is_valid:
                    questoes_validas.append(questao)

            logger.info(f"   ✅ {len(questoes_validas)} questões válidas")
            stats['total_questoes_validas'] += len(questoes_validas)

            # 4. Adicionar às questões coletadas
            todas_questoes.extend(questoes_validas)

            stats['pdfs_processados'] += 1

        except KeyboardInterrupt:
            logger.warning("\n\n⚠️  Processamento interrompido pelo usuário")
            logger.info(f"📊 Salvando questões já processadas ({len(todas_questoes)})...")
            break

        except Exception as e:
            logger.error(f"   ❌ Erro inesperado: {e}")
            stats['pdfs_falhados'] += 1
            stats['pdfs_com_erro'].append({
                'arquivo': pdf_path.name,
                'erro': f'Erro inesperado: {str(e)}'
            })
            continue

    # ========================================================================
    # DEDUPLICAÇÃO
    # ========================================================================

    logger.info("\n" + "="*80)
    logger.info("DEDUPLICAÇÃO")
    logger.info("="*80)

    questoes_unicas = deduplicate_questoes(todas_questoes)
    stats['total_questoes_unicas'] = len(questoes_unicas)

    # ========================================================================
    # SALVAR JSON
    # ========================================================================

    logger.info("\n" + "="*80)
    logger.info("SALVANDO JSON")
    logger.info("="*80)

    try:
        # Estrutura do JSON de saída (compatível com exemplo_questoes_enem.json)
        output_data = {
            'versao': '1.0',
            'total_questoes': len(questoes_unicas),
            'gerado_em': datetime.now().isoformat(),
            'fonte': 'Batch ingestion de PDFs',
            'questoes': questoes_unicas,
            'estatisticas': {
                'pdfs_processados': stats['pdfs_processados'],
                'pdfs_falhados': stats['pdfs_falhados'],
                'total_questoes_parseadas': stats['total_questoes_parseadas'],
                'total_questoes_validas': stats['total_questoes_validas'],
                'duplicadas_removidas': stats['total_questoes_validas'] - stats['total_questoes_unicas'],
            }
        }

        # Salvar JSON
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        logger.info(f"\n✅ JSON salvo: {output_json}")
        logger.info(f"   📦 Tamanho: {output_json.stat().st_size / 1024:.2f} KB")

        stats['output_file'] = str(output_json)
        stats['success'] = True

    except Exception as e:
        logger.error(f"\n❌ Erro ao salvar JSON: {e}")
        stats['success'] = False
        stats['error'] = f'Erro ao salvar: {str(e)}'
        return stats

    # ========================================================================
    # RESUMO FINAL
    # ========================================================================

    stats['fim'] = datetime.now().isoformat()

    logger.info("\n" + "="*80)
    logger.info("📊 RESUMO FINAL")
    logger.info("="*80)
    logger.info(f"📚 PDFs encontrados: {stats['total_pdfs']}")
    logger.info(f"✅ PDFs processados com sucesso: {stats['pdfs_processados']}")
    logger.info(f"❌ PDFs com erro: {stats['pdfs_falhados']}")
    logger.info("")
    logger.info(f"📝 Questões parseadas: {stats['total_questoes_parseadas']}")
    logger.info(f"✅ Questões válidas: {stats['total_questoes_validas']}")
    logger.info(f"🔍 Questões únicas (após dedup): {stats['total_questoes_unicas']}")
    logger.info("")
    logger.info(f"💾 Arquivo de saída: {output_json}")

    if stats['pdfs_com_erro']:
        logger.info(f"\n⚠️  PDFs com erro ({len(stats['pdfs_com_erro'])}):")
        for erro_info in stats['pdfs_com_erro']:
            logger.info(f"   • {erro_info['arquivo']}: {erro_info['erro']}")

    logger.info("="*80)
    logger.info("✅ BATCH INGESTION CONCLUÍDO")
    logger.info("="*80)

    return stats


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI do batch ingestion"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Batch ENEM Ingestion - Processa múltiplos PDFs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos de uso:

  # Processar todos os PDFs da pasta padrão
  python batch_ingest.py

  # Especificar arquivo de saída customizado
  python batch_ingest.py --output meu_arquivo.json

  # Processar PDFs de outra pasta
  python batch_ingest.py --input /caminho/para/pdfs

  # Pular validação estrita
  python batch_ingest.py --skip-validation
        '''
    )

    parser.add_argument(
        '--input', '-i',
        type=Path,
        default=Path(__file__).parent / 'pdfs_enem',
        help='Pasta com os PDFs (padrão: pdfs_enem/)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path(__file__).parent / 'todas_questoes_enem.json',
        help='Arquivo JSON de saída (padrão: todas_questoes_enem.json)'
    )

    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Pula validação estrita (aceita questões com avisos)'
    )

    args = parser.parse_args()

    # Validar diretório de entrada
    if not args.input.exists():
        logger.error(f"❌ Diretório não encontrado: {args.input}")
        logger.info(f"💡 Criando diretório: {args.input}")
        args.input.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Diretório criado. Coloque seus PDFs lá e execute novamente.")
        return 1

    if not args.input.is_dir():
        logger.error(f"❌ Caminho não é um diretório: {args.input}")
        return 1

    # Executar batch ingestion
    try:
        stats = processar_pdfs_em_lote(
            pdfs_dir=args.input,
            output_json=args.output,
            skip_validation=args.skip_validation
        )

        # Exit code baseado no sucesso
        if not stats.get('success'):
            return 1

        # Se processou pelo menos um PDF, considera sucesso
        if stats['pdfs_processados'] > 0:
            return 0

        return 1

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Batch ingestion interrompido pelo usuário")
        return 130

    except Exception as e:
        logger.error(f"\n💥 Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
