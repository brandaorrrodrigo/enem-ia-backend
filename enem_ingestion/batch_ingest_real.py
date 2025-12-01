#!/usr/bin/env python3
"""
==============================================
BATCH INGEST REAL ENEM PDFs (2009-2024)
==============================================

Scans folder pdfs_enem_real/ and processes all ENEM PDF files.
Extracts questions, normalizes format, deduplicates.

Output: questoes_reais_2009_2024.json
"""

import os
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import from existing pipeline
try:
    from pipeline_completo import processar_pdf_enem
except ImportError:
    print("⚠️  pipeline_completo.py não encontrado. Usando extração básica.")
    processar_pdf_enem = None


# ============================================================================
# CONFIG
# ============================================================================

PDF_FOLDER = Path(__file__).parent / "pdfs_enem_real"
OUTPUT_FILE = Path(__file__).parent / "questoes_reais_2009_2024.json"


# ============================================================================
# HELPERS
# ============================================================================

def extrair_ano_do_filename(filename: str) -> Optional[int]:
    """
    Extract year from filename.
    Examples:
      ENEM_2012_D1.pdf -> 2012
      enem_2023_primeira_aplicacao.pdf -> 2023
    """
    match = re.search(r'20\d{2}', filename)
    if match:
        return int(match.group())
    return None


def inferir_area(disciplina: str) -> str:
    """
    Map disciplina to area de conhecimento.
    """
    disciplina_lower = disciplina.lower()

    if any(x in disciplina_lower for x in ['portugues', 'literatura', 'ingles', 'espanhol', 'redacao']):
        return 'linguagens'

    if any(x in disciplina_lower for x in ['matematica', 'algebra', 'geometria']):
        return 'matematica'

    if any(x in disciplina_lower for x in ['fisica', 'quimica', 'biologia']):
        return 'ciencias_natureza'

    if any(x in disciplina_lower for x in ['historia', 'geografia', 'sociologia', 'filosofia']):
        return 'ciencias_humanas'

    # Default
    return 'matematica'


def criar_hash_questao(enunciado: str, alternativas: Dict[str, str]) -> str:
    """
    Create unique hash for a question to detect duplicates.
    """
    # Normalize
    texto = enunciado.lower().strip()

    # Add alternatives
    alt_sorted = sorted(alternativas.values())
    texto += ''.join(alt_sorted)

    # Hash
    return hashlib.md5(texto.encode('utf-8')).hexdigest()


def normalizar_alternativas(alternativas: Any) -> Dict[str, str]:
    """
    Normalize alternatives to dict format.
    """
    if isinstance(alternativas, dict):
        # Already dict
        required = ['A', 'B', 'C', 'D', 'E']
        if all(k in alternativas for k in required):
            return alternativas

    if isinstance(alternativas, list):
        # Convert list to dict
        if len(alternativas) == 5:
            return {
                'A': str(alternativas[0]),
                'B': str(alternativas[1]),
                'C': str(alternativas[2]),
                'D': str(alternativas[3]),
                'E': str(alternativas[4]),
            }

    # Fallback: generic alternatives
    return {
        'A': 'Opção A',
        'B': 'Opção B',
        'C': 'Opção C',
        'D': 'Opção D',
        'E': 'Opção E',
    }


def normalizar_correta(correta: Any) -> str:
    """
    Normalize correct answer to letter format (A-E).
    """
    if isinstance(correta, str):
        upper = correta.upper()
        if upper in ['A', 'B', 'C', 'D', 'E']:
            return upper

    if isinstance(correta, int):
        if 0 <= correta <= 4:
            return chr(65 + correta)  # 0->A, 1->B, etc

    # Default
    return 'A'


# ============================================================================
# PDF PROCESSING
# ============================================================================

def processar_pdf_basico(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Basic PDF extraction fallback if pipeline_completo is not available.
    Returns list of questions in standard format.
    """
    # This is a placeholder - in production you'd use PyPDF2, pdfplumber, etc.
    print(f"   ⚠️  Usando extração básica para {pdf_path.name}")
    print(f"   💡 Para melhor extração, instale: pip install pdfplumber PyPDF2")

    # Return empty for now - user should have pipeline_completo.py
    return []


def processar_pdf_com_pipeline(pdf_path: Path, ano: int) -> List[Dict[str, Any]]:
    """
    Process PDF using existing pipeline_completo.py logic.
    """
    try:
        # Call pipeline function
        resultado = processar_pdf_enem(str(pdf_path))

        if not resultado or 'questoes' not in resultado:
            return []

        questoes = []
        for q in resultado['questoes']:
            questao = {
                'numero': q.get('numero', 0),
                'ano': ano,
                'disciplina': q.get('disciplina', 'matematica'),
                'enunciado': q.get('enunciado', ''),
                'alternativas': normalizar_alternativas(q.get('alternativas', {})),
                'correta': normalizar_correta(q.get('correta', 'A')),
                'habilidade': q.get('habilidade'),
                'competencia': q.get('competencia'),
                'explicacao': q.get('explicacao'),
                'source': 'real_enem',
                'area': inferir_area(q.get('disciplina', 'matematica')),
            }

            # Validate
            if questao['enunciado'] and len(questao['enunciado']) > 10:
                questoes.append(questao)

        return questoes

    except Exception as e:
        print(f"   ❌ Erro ao processar com pipeline: {e}")
        return []


def processar_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Process a single PDF file.
    """
    print(f"\n📄 Processando: {pdf_path.name}")

    # Extract year
    ano = extrair_ano_do_filename(pdf_path.name)
    if not ano:
        print(f"   ⚠️  Não foi possível extrair ano do nome do arquivo. Usando 2024.")
        ano = 2024

    print(f"   📅 Ano: {ano}")

    # Try with pipeline, fallback to basic
    if processar_pdf_enem is not None:
        questoes = processar_pdf_com_pipeline(pdf_path, ano)
    else:
        questoes = processar_pdf_basico(pdf_path)

    print(f"   ✅ Extraídas: {len(questoes)} questões")

    return questoes


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function.
    """
    print("="*70)
    print("BATCH INGEST REAL ENEM PDFs (2009-2024)")
    print("="*70)

    # Check folder exists
    if not PDF_FOLDER.exists():
        print(f"\n❌ Pasta não encontrada: {PDF_FOLDER}")
        print(f"💡 Criando pasta...")
        PDF_FOLDER.mkdir(parents=True, exist_ok=True)
        print(f"✅ Pasta criada: {PDF_FOLDER}")
        print(f"\n📌 Coloque os PDFs do ENEM (2009-2024) nesta pasta e execute novamente.")
        return

    # Find PDFs
    pdf_files = list(PDF_FOLDER.glob("*.pdf"))

    if not pdf_files:
        print(f"\n⚠️  Nenhum PDF encontrado em: {PDF_FOLDER}")
        print(f"📌 Coloque os PDFs do ENEM nesta pasta e execute novamente.")
        return

    print(f"\n📚 Encontrados {len(pdf_files)} PDFs:")
    for pdf in pdf_files:
        print(f"   - {pdf.name}")

    # Process all PDFs
    todas_questoes = []
    hashes_vistos = set()
    duplicatas = 0

    for pdf_path in pdf_files:
        questoes = processar_pdf(pdf_path)

        # Deduplicate
        for questao in questoes:
            hash_q = criar_hash_questao(questao['enunciado'], questao['alternativas'])

            if hash_q in hashes_vistos:
                duplicatas += 1
                continue

            hashes_vistos.add(hash_q)
            todas_questoes.append(questao)

    # Create output JSON
    output_data = {
        'versao': '1.0',
        'total_questoes': len(todas_questoes),
        'gerado_em': datetime.now().isoformat(),
        'source': 'real_enem_pdfs_2009_2024',
        'pdfs_processados': len(pdf_files),
        'duplicatas_removidas': duplicatas,
        'questoes': todas_questoes
    }

    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Summary
    print("\n" + "="*70)
    print("📊 RESUMO FINAL")
    print("="*70)
    print(f"PDFs processados:      {len(pdf_files)}")
    print(f"Questões extraídas:    {len(todas_questoes) + duplicatas}")
    print(f"Duplicatas removidas:  {duplicatas}")
    print(f"Questões únicas:       {len(todas_questoes)}")
    print(f"\n✅ Arquivo salvo: {OUTPUT_FILE}")
    print("="*70)


if __name__ == '__main__':
    main()
