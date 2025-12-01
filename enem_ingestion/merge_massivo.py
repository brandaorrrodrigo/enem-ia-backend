#!/usr/bin/env python3
"""
==============================================
MERGE MASSIVO - TODAS AS QUESTÕES ENEM
==============================================

Merges all question sources into one massive dataset:
1. Real ENEM PDFs (2009-2024)
2. Adapted questions (7,000)
3. Simulated/synthetic questions (10,000)

Output: todas_questoes_enem_massivo.json
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set


# ============================================================================
# CONFIG
# ============================================================================

BACKEND_DIR = Path(__file__).parent

INPUT_FILES = {
    'real': BACKEND_DIR / 'real_enem_questoes.json',
    'adaptada': BACKEND_DIR / 'questoes_adaptadas_7000.json',
    'simulada': BACKEND_DIR / 'questoes_simuladas_10000.json',
}

OUTPUT_FILE = BACKEND_DIR / 'todas_questoes_enem_massivo.json'


# ============================================================================
# HELPERS
# ============================================================================

def criar_hash_questao(questao: Dict[str, Any]) -> str:
    """
    Create stable hash for a question.
    Uses enunciado + sorted alternatives.
    """
    enunciado = questao.get('enunciado', '').lower().strip()

    alternativas = questao.get('alternativas', {})

    if isinstance(alternativas, dict):
        alt_sorted = sorted(alternativas.values())
    elif isinstance(alternativas, list):
        alt_sorted = sorted(alternativas)
    else:
        alt_sorted = []

    texto = enunciado + ''.join(alt_sorted)

    return hashlib.md5(texto.encode('utf-8')).hexdigest()


def carregar_json(filepath: Path) -> Dict[str, Any]:
    """Load JSON file safely."""
    if not filepath.exists():
        print(f"   ⚠️  Arquivo não encontrado: {filepath.name}")
        return {'questoes': []}

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"   ❌ Erro ao carregar {filepath.name}: {e}")
        return {'questoes': []}


def validar_questao(questao: Dict[str, Any]) -> bool:
    """
    Validate that question has required fields.
    """
    # Required fields
    if not questao.get('enunciado'):
        return False

    if not questao.get('alternativas'):
        return False

    if not questao.get('correta'):
        return False

    # Enunciado must be at least 10 chars
    if len(questao['enunciado'].strip()) < 10:
        return False

    return True


def normalizar_questao(questao: Dict[str, Any], source_type: str) -> Dict[str, Any]:
    """
    Normalize question format to standard.

    Args:
        questao: Question data
        source_type: 'real', 'adaptada', or 'simulada'
    """
    # Ensure all required fields exist
    normalized = {
        'numero': questao.get('numero', 0),
        'ano': questao.get('ano', 2024),
        'disciplina': questao.get('disciplina', 'matematica'),
        'enunciado': questao['enunciado'].strip(),
        'alternativas': questao['alternativas'],
        'correta': questao['correta'],
        'tipo': source_type,  # ADICIONAR tipo baseado na fonte
        'habilidade': questao.get('habilidade', 'H1'),
        'competencia': questao.get('competencia', 1),
        'explicacao': questao.get('explicacao', ''),
    }

    # Add metadata if exists
    if 'source' in questao:
        normalized['source'] = questao['source']
    else:
        normalized['source'] = source_type

    if 'area' in questao:
        normalized['area'] = questao['area']

    if 'difficulty' in questao:
        normalized['difficulty'] = questao['difficulty']

    return normalized


# ============================================================================
# MERGE LOGIC
# ============================================================================

def merge_all_sources() -> List[Dict[str, Any]]:
    """
    Merge all question sources with deduplication.
    """
    print("\n🔄 Iniciando merge de todas as fontes...")

    todas_questoes: List[Dict[str, Any]] = []
    hashes_vistos: Set[str] = set()

    stats = {
        'real': {'loaded': 0, 'inserted': 0, 'duplicates': 0},
        'adaptada': {'loaded': 0, 'inserted': 0, 'duplicates': 0},
        'simulada': {'loaded': 0, 'inserted': 0, 'duplicates': 0},
    }

    # Process each source
    for source_name, filepath in INPUT_FILES.items():
        print(f"\n📂 Processando: {filepath.name}")

        data = carregar_json(filepath)
        questoes = data.get('questoes', [])

        print(f"   📊 Questões no arquivo: {len(questoes)}")

        stats[source_name]['loaded'] = len(questoes)

        for questao in questoes:
            # Validate
            if not validar_questao(questao):
                continue

            # Normalize (passing source_type)
            questao_norm = normalizar_questao(questao, source_name)

            # Check duplicate
            hash_q = criar_hash_questao(questao_norm)

            if hash_q in hashes_vistos:
                stats[source_name]['duplicates'] += 1
                continue

            # Add
            hashes_vistos.add(hash_q)
            todas_questoes.append(questao_norm)
            stats[source_name]['inserted'] += 1

        print(f"   ✅ Inseridas: {stats[source_name]['inserted']}")
        print(f"   ⏭️  Duplicadas: {stats[source_name]['duplicates']}")

    return todas_questoes, stats


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main function."""
    print("="*70)
    print("MERGE MASSIVO - TODAS AS QUESTÕES ENEM")
    print("="*70)

    # Merge
    todas_questoes, stats = merge_all_sources()

    # Create output
    output_data = {
        'versao': '2.0',
        'total_questoes': len(todas_questoes),
        'gerado_em': datetime.now().isoformat(),
        'description': 'Dataset massivo ENEM - Real + Adaptadas + Simuladas',
        'sources': {
            'real_enem_2009_2024': {
                'loaded': stats['real']['loaded'],
                'inserted': stats['real']['inserted'],
                'duplicates': stats['real']['duplicates'],
            },
            'questoes_adaptadas': {
                'loaded': stats['adaptada']['loaded'],
                'inserted': stats['adaptada']['inserted'],
                'duplicates': stats['adaptada']['duplicates'],
            },
            'questoes_simuladas': {
                'loaded': stats['simulada']['loaded'],
                'inserted': stats['simulada']['inserted'],
                'duplicates': stats['simulada']['duplicates'],
            },
        },
        'questoes': todas_questoes
    }

    # Save
    print(f"\n💾 Salvando dataset massivo...")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Final summary
    total_loaded = sum(s['loaded'] for s in stats.values())
    total_duplicates = sum(s['duplicates'] for s in stats.values())

    print("\n" + "="*70)
    print("📊 RESUMO FINAL - DATASET MASSIVO")
    print("="*70)
    print(f"\n📚 POR FONTE:")
    print(f"   Real ENEM (2009-2024):  {stats['real']['inserted']:,} questões")
    print(f"   Adaptadas:              {stats['adaptada']['inserted']:,} questões")
    print(f"   Simuladas:              {stats['simulada']['inserted']:,} questões")
    print(f"\n📈 TOTAIS:")
    print(f"   Questões carregadas:    {total_loaded:,}")
    print(f"   Duplicatas removidas:   {total_duplicates:,}")
    print(f"   Questões únicas finais: {len(todas_questoes):,}")
    print(f"\n✅ Arquivo salvo: {OUTPUT_FILE}")
    print(f"   Tamanho: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")
    print("="*70)


if __name__ == '__main__':
    main()
