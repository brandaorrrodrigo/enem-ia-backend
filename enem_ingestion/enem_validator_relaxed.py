"""
ENEM Validator Relaxed - Validador RELAXADO para questões REAIS de PDFs

Diferenças do validador padrão:
- Aceita enunciados mais curtos (min 10 chars)
- Aceita alternativas curtas (min 1 char)
- Não exige gabarito (questões podem não ter resposta explícita no PDF)
- Não exige disciplina/ano/número
- Ignora problemas de encoding
- Foca apenas em estrutura mínima: enunciado + 5 alternativas

Usado para: Ingestão de questões REAIS de PDFs do ENEM
"""

import re
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnemValidatorRelaxed:
    """Validador RELAXADO de questões do ENEM (para PDFs reais)"""

    # Alternativas válidas
    ALTERNATIVAS_VALIDAS = ['A', 'B', 'C', 'D', 'E']

    # Comprimentos mínimos RELAXADOS
    MIN_LENGTH_ENUNCIADO = 10  # Era 20
    MIN_LENGTH_ALTERNATIVA = 1  # Era 3

    def __init__(self):
        """Inicializa o validador relaxado"""
        self.erros_encontrados = []
        self.avisos_encontrados = []

    def validar_questao(self, questao: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Valida uma questão com regras RELAXADAS

        Args:
            questao: Dicionário com dados da questão

        Returns:
            Tupla (is_valid, erros, avisos)
        """
        self.erros_encontrados = []
        self.avisos_encontrados = []

        # APENAS validações críticas
        self._validar_enunciado(questao)
        self._validar_alternativas(questao)

        # Gabarito é OPCIONAL (muitos PDFs não têm)
        self._validar_gabarito_opcional(questao)

        # Avisos não invalidam
        is_valid = len(self.erros_encontrados) == 0

        return is_valid, self.erros_encontrados, self.avisos_encontrados

    def _validar_enunciado(self, questao: Dict):
        """Valida enunciado (RELAXADO)"""
        enunciado = questao.get('enunciado', '').strip()

        if not enunciado:
            self.erros_encontrados.append("Enunciado está vazio")
            return

        # Comprimento mínimo REDUZIDO
        if len(enunciado) < self.MIN_LENGTH_ENUNCIADO:
            self.erros_encontrados.append(
                f"Enunciado muito curto ({len(enunciado)} chars, mínimo {self.MIN_LENGTH_ENUNCIADO})"
            )

    def _validar_alternativas(self, questao: Dict):
        """Valida alternativas (RELAXADO)"""
        alternativas = questao.get('alternativas', {})

        # Deve ser dict
        if not isinstance(alternativas, dict):
            self.erros_encontrados.append(f"Alternativas deve ser dict, recebeu {type(alternativas)}")
            return

        # Deve ter exatamente 5 alternativas (A-E)
        if len(alternativas) != 5:
            self.erros_encontrados.append(
                f"Deve ter exatamente 5 alternativas, tem {len(alternativas)}"
            )
            return

        # Verifica se todas as letras A-E existem
        for letra in self.ALTERNATIVAS_VALIDAS:
            if letra not in alternativas:
                self.erros_encontrados.append(f"Falta alternativa {letra}")
                continue

            texto_alt = str(alternativas[letra]).strip()

            # Comprimento mínimo MUITO RELAXADO
            if len(texto_alt) < self.MIN_LENGTH_ALTERNATIVA:
                self.avisos_encontrados.append(
                    f"Alternativa {letra} vazia"
                )

    def _validar_gabarito_opcional(self, questao: Dict):
        """Valida gabarito (OPCIONAL)"""
        correta = questao.get('correta')

        if not correta:
            # Não é erro, apenas aviso
            self.avisos_encontrados.append("Gabarito não especificado (normal em PDFs)")
            # Define gabarito padrão
            questao['correta'] = 'A'
            return

        correta = str(correta).upper().strip()

        if correta not in self.ALTERNATIVAS_VALIDAS:
            # Corrige para 'A' ao invés de rejeitar
            self.avisos_encontrados.append(
                f"Gabarito inválido '{correta}', usando 'A' como padrão"
            )
            questao['correta'] = 'A'

    def validar_lote(self, questoes: List[Dict]) -> Dict:
        """
        Valida um lote de questões

        Args:
            questoes: Lista de questões

        Returns:
            Estatísticas de validação
        """
        if not questoes:
            logger.warning("Lista de questões vazia")
            return {
                'total': 0,
                'validas': 0,
                'invalidas': 0,
                'com_avisos': 0
            }

        validas = 0
        invalidas = 0
        com_avisos = 0

        questoes_invalidas = []
        questoes_com_avisos = []

        for i, questao in enumerate(questoes):
            is_valid, erros, avisos = self.validar_questao(questao)

            if is_valid:
                validas += 1
                if avisos:
                    com_avisos += 1
                    questoes_com_avisos.append({
                        'indice': i,
                        'numero': questao.get('numero', '?'),
                        'avisos': avisos
                    })
            else:
                invalidas += 1
                questoes_invalidas.append({
                    'indice': i,
                    'numero': questao.get('numero', '?'),
                    'erros': erros,
                    'avisos': avisos
                })

        # Log resumo
        logger.info("="*70)
        logger.info("VALIDAÇÃO RELAXADA (PDFs REAIS)")
        logger.info("="*70)
        logger.info(f"Total de questões: {len(questoes)}")
        logger.info(f"✅ Válidas: {validas} ({validas/len(questoes)*100:.1f}%)")
        logger.info(f"❌ Inválidas: {invalidas} ({invalidas/len(questoes)*100:.1f}%)")
        logger.info(f"⚠️  Com avisos: {com_avisos}")

        # Detalha inválidas (primeiras 3)
        if questoes_invalidas:
            logger.info("\n❌ EXEMPLOS DE QUESTÕES INVÁLIDAS:")
            for q in questoes_invalidas[:3]:
                logger.info(f"\n  Questão #{q['numero']} (índice {q['indice']}):")
                for erro in q['erros']:
                    logger.info(f"    • {erro}")

        return {
            'total': len(questoes),
            'validas': validas,
            'invalidas': invalidas,
            'com_avisos': com_avisos,
            'questoes_invalidas': questoes_invalidas,
            'questoes_com_avisos': questoes_com_avisos
        }


# Função helper para uso direto
def validar_questao_relaxed(questao: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Helper function para validar uma questão com regras relaxadas

    Args:
        questao: Dicionário com dados da questão

    Returns:
        Tupla (is_valid, erros, avisos)
    """
    validator = EnemValidatorRelaxed()
    return validator.validar_questao(questao)
