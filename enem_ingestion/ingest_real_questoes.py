#!/usr/bin/env python3
"""
=============================================================================
INGESTÃO ROBUSTA DE QUESTÕES REAIS DO ENEM
=============================================================================

Script otimizado para extrair questões REAIS de PDFs oficiais do ENEM.

Melhorias:
- Parser robusto (enem_parser_real.py)
- Validador relaxado (enem_validator_relaxed.py)
- Extração multi-biblioteca (PyPDF2, pdfplumber, pypdf)
- Logs detalhados com motivos de descarte
- Deduplicação inteligente
- Metadados automáticos (ano, disciplina)

Uso:
    python ingest_real_questoes.py
    python ingest_real_questoes.py --debug
    python ingest_real_questoes.py --output meu_arquivo.json

Output: real_enem_questoes.json
"""

import os
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import sys

# Import dos novos parsers/validadores
from enem_parser_real import EnemParserReal
from enem_validator_relaxed import EnemValidatorRelaxed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

PDF_FOLDER = Path(__file__).parent / "pdfs_enem_real"
OUTPUT_FILE = Path(__file__).parent / "real_enem_questoes.json"

# Palavras-chave que indicam que NÃO é caderno de questões
IGNORAR_SE_CONTEM = [
    'gabarito_oficial',
    'respostas',
    'instrucoes',
    'folha_resposta',
    'apostila',
    'resumo',
    'revisao'
]


# ============================================================================
# EXTRAÇÃO DE TEXTO DE PDFs
# ============================================================================

def extrair_texto_pdf(pdf_path: Path) -> Optional[str]:
    """
    Extrai texto de um PDF usando múltiplas bibliotecas

    Ordem de tentativa:
    1. PyPDF2
    2. pdfplumber
    3. pypdf

    Args:
        pdf_path: Caminho do PDF

    Returns:
        Texto extraído ou None se falhar
    """
    # Tentativa 1: PyPDF2
    try:
        import PyPDF2
        texto = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                texto.append(page.extract_text())

        resultado = '\n'.join(texto)
        if resultado.strip():
            logger.info(f"   ✅ PyPDF2: {len(resultado)} caracteres")
            return resultado
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"   ⚠️  PyPDF2 falhou: {e}")

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
            logger.info(f"   ✅ pdfplumber: {len(resultado)} caracteres")
            return resultado
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"   ⚠️  pdfplumber falhou: {e}")

    # Tentativa 3: pypdf
    try:
        import pypdf
        texto = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            for page in pdf_reader.pages:
                texto.append(page.extract_text())

        resultado = '\n'.join(texto)
        if resultado.strip():
            logger.info(f"   ✅ pypdf: {len(resultado)} caracteres")
            return resultado
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"   ⚠️  pypdf falhou: {e}")

    logger.error(f"   ❌ Nenhuma biblioteca de PDF funcionou")
    logger.error(f"   💡 Instale: pip install PyPDF2 pdfplumber")
    return None


# ============================================================================
# PROCESSAMENTO DE PDFs
# ============================================================================

def deve_ignorar_pdf(pdf_name: str) -> bool:
    """
    Verifica se o PDF deve ser ignorado

    Args:
        pdf_name: Nome do arquivo PDF

    Returns:
        True se deve ignorar
    """
    pdf_lower = pdf_name.lower()

    for palavra in IGNORAR_SE_CONTEM:
        if palavra in pdf_lower:
            return True

    return False


def processar_pdf(pdf_path: Path, parser: EnemParserReal, validator: EnemValidatorRelaxed) -> Dict[str, Any]:
    """
    Processa um único PDF

    Args:
        pdf_path: Caminho do PDF
        parser: Parser de questões
        validator: Validador de questões

    Returns:
        Resultado do processamento
    """
    resultado = {
        'arquivo': pdf_path.name,
        'questoes_parseadas': 0,
        'questoes_validas': 0,
        'questoes_invalidas': 0,
        'questoes': [],
        'motivos_descarte': [],
        'erro': None
    }

    logger.info(f"\n📄 Processando: {pdf_path.name}")
    logger.info("-" * 60)

    # Verifica se deve ignorar
    if deve_ignorar_pdf(pdf_path.name):
        logger.info(f"   ⏭️  IGNORADO: Não parece ser caderno de questões")
        resultado['erro'] = 'Ignorado (não é caderno de questões)'
        return resultado

    # Extrai texto
    logger.info("   🔍 Extraindo texto do PDF...")
    texto = extrair_texto_pdf(pdf_path)

    if not texto or len(texto.strip()) < 200:
        logger.warning(f"   ⚠️  PDF vazio ou texto insuficiente")
        resultado['erro'] = 'Texto vazio ou insuficiente'
        return resultado

    # Extrai metadados do filename
    ano = parser.extrair_ano_do_filename(pdf_path.name)
    disciplina = parser.inferir_disciplina(pdf_path.name, texto)

    metadata = {
        'fonte': pdf_path.name,
        'ano': ano,
        'disciplina': disciplina
    }

    logger.info(f"   📅 Ano detectado: {ano or 'N/A'}")
    logger.info(f"   📚 Disciplina inferida: {disciplina or 'N/A'}")

    # Parseia questões
    logger.info("   📝 Parseando questões...")
    try:
        questoes = parser.parse_from_text(texto, metadata)
        resultado['questoes_parseadas'] = len(questoes)
        logger.info(f"   ✅ {len(questoes)} questões parseadas")
    except Exception as e:
        logger.error(f"   ❌ Erro no parsing: {e}")
        resultado['erro'] = f'Parsing: {str(e)}'
        return resultado

    if not questoes:
        logger.warning(f"   ⚠️  Nenhuma questão encontrada no PDF")
        resultado['erro'] = 'Nenhuma questão parseada'
        return resultado

    # Valida questões
    logger.info("   ✅ Validando questões...")
    questoes_validas = []

    for questao in questoes:
        is_valid, erros, avisos = validator.validar_questao(questao)

        if is_valid:
            questoes_validas.append(questao)
        else:
            resultado['questoes_invalidas'] += 1
            # Registra motivo de descarte
            numero = questao.get('numero', '?')
            motivo = ', '.join(erros[:2])  # Primeiros 2 erros
            resultado['motivos_descarte'].append(f"Q{numero}: {motivo}")

    resultado['questoes_validas'] = len(questoes_validas)
    resultado['questoes'] = questoes_validas

    logger.info(f"   ✅ {len(questoes_validas)} questões VÁLIDAS")

    if resultado['questoes_invalidas'] > 0:
        logger.info(f"   ❌ {resultado['questoes_invalidas']} questões DESCARTADAS")

    return resultado


# ============================================================================
# DEDUPLICAÇÃO
# ============================================================================

def criar_hash_questao(questao: Dict) -> str:
    """
    Cria hash único para detectar duplicatas

    Args:
        questao: Questão

    Returns:
        Hash MD5
    """
    # Usa enunciado + alternativas
    texto = questao.get('enunciado', '').lower().strip()

    alternativas = questao.get('alternativas', {})
    for letra in ['A', 'B', 'C', 'D', 'E']:
        texto += str(alternativas.get(letra, '')).lower().strip()

    return hashlib.md5(texto.encode('utf-8')).hexdigest()


def deduplicate_questoes(todas_questoes: List[Dict]) -> tuple[List[Dict], int]:
    """
    Remove questões duplicadas

    Args:
        todas_questoes: Lista de todas as questões

    Returns:
        (questoes_unicas, num_duplicatas)
    """
    questoes_unicas = []
    hashes_vistos = set()
    duplicatas = 0

    for questao in todas_questoes:
        hash_q = criar_hash_questao(questao)

        if hash_q in hashes_vistos:
            duplicatas += 1
            continue

        hashes_vistos.add(hash_q)
        questoes_unicas.append(questao)

    return questoes_unicas, duplicatas


# ============================================================================
# MAIN
# ============================================================================

def main(debug: bool = False, output_file: Optional[Path] = None):
    """
    Função principal

    Args:
        debug: Ativa logs debug
        output_file: Arquivo de saída customizado
    """
    if debug:
        logger.setLevel(logging.DEBUG)

    logger.info("=" * 80)
    logger.info("INGESTÃO ROBUSTA DE QUESTÕES REAIS DO ENEM")
    logger.info("=" * 80)
    logger.info(f"📂 Pasta de PDFs: {PDF_FOLDER}")
    logger.info(f"💾 Arquivo de saída: {output_file or OUTPUT_FILE}")
    logger.info("=" * 80)

    # Verifica pasta
    if not PDF_FOLDER.exists():
        logger.error(f"\n❌ Pasta não encontrada: {PDF_FOLDER}")
        logger.info(f"💡 Criando pasta...")
        PDF_FOLDER.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Pasta criada. Coloque os PDFs do ENEM lá e execute novamente.")
        return 1

    # Busca PDFs
    pdf_files = sorted(PDF_FOLDER.glob("*.pdf"))

    if not pdf_files:
        logger.error(f"\n⚠️  Nenhum PDF encontrado em: {PDF_FOLDER}")
        logger.info(f"📌 Coloque os PDFs do ENEM (2009-2024) nesta pasta e execute novamente.")
        return 1

    logger.info(f"\n📚 Encontrados {len(pdf_files)} PDFs")

    # Inicializa parser e validator
    parser = EnemParserReal()
    validator = EnemValidatorRelaxed()

    # Estatísticas globais
    stats = {
        'total_pdfs': len(pdf_files),
        'pdfs_processados': 0,
        'pdfs_ignorados': 0,
        'pdfs_com_erro': 0,
        'total_parseadas': 0,
        'total_validas': 0,
        'total_invalidas': 0,
        'total_duplicatas': 0,
        'total_unicas': 0,
        'arquivos_ignorados': [],
        'arquivos_com_erro': [],
        'motivos_descarte': []
    }

    # Processa cada PDF
    todas_questoes = []

    for pdf_path in pdf_files:
        try:
            resultado = processar_pdf(pdf_path, parser, validator)

            if resultado['erro']:
                if 'Ignorado' in resultado['erro']:
                    stats['pdfs_ignorados'] += 1
                    stats['arquivos_ignorados'].append(resultado['arquivo'])
                else:
                    stats['pdfs_com_erro'] += 1
                    stats['arquivos_com_erro'].append({
                        'arquivo': resultado['arquivo'],
                        'erro': resultado['erro']
                    })
            else:
                stats['pdfs_processados'] += 1
                stats['total_parseadas'] += resultado['questoes_parseadas']
                stats['total_validas'] += resultado['questoes_validas']
                stats['total_invalidas'] += resultado['questoes_invalidas']

                # Adiciona questões válidas
                todas_questoes.extend(resultado['questoes'])

                # Registra motivos de descarte
                stats['motivos_descarte'].extend(resultado['motivos_descarte'])

        except Exception as e:
            logger.error(f"   ❌ Erro inesperado: {e}")
            stats['pdfs_com_erro'] += 1
            stats['arquivos_com_erro'].append({
                'arquivo': pdf_path.name,
                'erro': f'Erro inesperado: {str(e)}'
            })

    # Deduplicação
    logger.info("\n" + "=" * 80)
    logger.info("DEDUPLICAÇÃO")
    logger.info("=" * 80)

    questoes_unicas, duplicatas = deduplicate_questoes(todas_questoes)
    stats['total_duplicatas'] = duplicatas
    stats['total_unicas'] = len(questoes_unicas)

    logger.info(f"📝 Total de questões válidas: {len(todas_questoes)}")
    logger.info(f"⏭️  Duplicatas removidas: {duplicatas}")
    logger.info(f"✅ Questões únicas: {len(questoes_unicas)}")

    # Salva JSON
    logger.info("\n" + "=" * 80)
    logger.info("SALVANDO JSON")
    logger.info("=" * 80)

    output_path = output_file or OUTPUT_FILE

    output_data = {
        'versao': '2.0',
        'tipo': 'questoes_reais_enem',
        'total_questoes': len(questoes_unicas),
        'gerado_em': datetime.now().isoformat(),
        'fonte': 'PDFs oficiais ENEM (2009-2024)',
        'parser': 'enem_parser_real.py',
        'validator': 'enem_validator_relaxed.py',
        'estatisticas': {
            'pdfs_encontrados': stats['total_pdfs'],
            'pdfs_processados': stats['pdfs_processados'],
            'pdfs_ignorados': stats['pdfs_ignorados'],
            'pdfs_com_erro': stats['pdfs_com_erro'],
            'questoes_parseadas': stats['total_parseadas'],
            'questoes_validas': stats['total_validas'],
            'questoes_invalidas': stats['total_invalidas'],
            'duplicatas_removidas': stats['total_duplicatas'],
        },
        'questoes': questoes_unicas
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ JSON salvo: {output_path}")
    logger.info(f"   📦 Tamanho: {output_path.stat().st_size / 1024:.2f} KB")

    # Resumo final
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESUMO FINAL")
    logger.info("=" * 80)
    logger.info(f"📚 PDFs encontrados: {stats['total_pdfs']}")
    logger.info(f"✅ PDFs processados: {stats['pdfs_processados']}")
    logger.info(f"⏭️  PDFs ignorados: {stats['pdfs_ignorados']}")
    logger.info(f"❌ PDFs com erro: {stats['pdfs_com_erro']}")
    logger.info("")
    logger.info(f"📝 Questões parseadas: {stats['total_parseadas']}")
    logger.info(f"✅ Questões válidas: {stats['total_validas']}")
    logger.info(f"❌ Questões descartadas: {stats['total_invalidas']}")
    logger.info(f"⏭️  Duplicatas removidas: {stats['total_duplicatas']}")
    logger.info(f"🎯 QUESTÕES ÚNICAS FINAIS: {stats['total_unicas']}")
    logger.info("")
    logger.info(f"💾 Arquivo: {output_path}")

    # Detalha arquivos ignorados
    if stats['arquivos_ignorados']:
        logger.info(f"\n⏭️  Arquivos ignorados ({len(stats['arquivos_ignorados'])}):")
        for arquivo in stats['arquivos_ignorados'][:5]:
            logger.info(f"   • {arquivo}")

    # Detalha erros
    if stats['arquivos_com_erro']:
        logger.info(f"\n❌ Arquivos com erro ({len(stats['arquivos_com_erro'])}):")
        for info in stats['arquivos_com_erro'][:5]:
            logger.info(f"   • {info['arquivo']}: {info['erro']}")

    # Amostra de motivos de descarte
    if stats['motivos_descarte']:
        logger.info(f"\n❌ Exemplos de descartes ({len(stats['motivos_descarte'])} total):")
        for motivo in stats['motivos_descarte'][:10]:
            logger.info(f"   • {motivo}")

    logger.info("=" * 80)
    logger.info("✅ INGESTÃO CONCLUÍDA")
    logger.info("=" * 80)

    return 0


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Ingestão robusta de questões reais do ENEM',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Ativa logs debug'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Arquivo de saída customizado'
    )

    args = parser.parse_args()

    sys.exit(main(debug=args.debug, output_file=args.output))
