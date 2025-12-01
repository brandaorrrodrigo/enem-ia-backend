"""
ENEM Validator - Valida integridade e qualidade de questões parseadas

Verifica:
- Campos obrigatórios
- Formato correto de alternativas
- Gabarito válido
- Consistência de dados
- Qualidade mínima do texto
"""

import re
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnemValidator:
    """Validador de questões do ENEM"""

    # Disciplinas válidas
    DISCIPLINAS_VALIDAS = [
        'matematica', 'fisica', 'quimica', 'biologia',
        'historia', 'geografia', 'filosofia', 'sociologia',
        'portugues', 'literatura', 'redacao',
        'ingles', 'espanhol', 'artes'
    ]

    # Alternativas válidas
    ALTERNATIVAS_VALIDAS = ['A', 'B', 'C', 'D', 'E']

    # Comprimentos mínimos (em caracteres)
    MIN_LENGTH_ENUNCIADO = 20
    MIN_LENGTH_ALTERNATIVA = 3

    def __init__(self, strict_mode: bool = False):
        """
        Inicializa o validador

        Args:
            strict_mode: Se True, valida campos opcionais também
        """
        self.strict_mode = strict_mode
        self.erros_encontrados = []
        self.avisos_encontrados = []

    def validar_questao(self, questao: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Valida uma questão completa

        Args:
            questao: Dicionário com dados da questão

        Returns:
            Tupla (is_valid, erros, avisos)
        """
        self.erros_encontrados = []
        self.avisos_encontrados = []

        # Validações obrigatórias
        self._validar_enunciado(questao)
        self._validar_alternativas(questao)
        self._validar_gabarito(questao)

        # Validações opcionais (warnings)
        self._validar_disciplina(questao)
        self._validar_numero(questao)
        self._validar_ano(questao)

        # Validações de qualidade
        self._validar_qualidade_texto(questao)

        # Em strict mode, avisos também invalidam
        is_valid = len(self.erros_encontrados) == 0
        if self.strict_mode and self.avisos_encontrados:
            is_valid = False

        return is_valid, self.erros_encontrados, self.avisos_encontrados

    def _validar_enunciado(self, questao: Dict):
        """Valida enunciado"""
        enunciado = questao.get('enunciado', '').strip()

        if not enunciado:
            self.erros_encontrados.append("Enunciado está vazio")
            return

        if len(enunciado) < self.MIN_LENGTH_ENUNCIADO:
            self.erros_encontrados.append(
                f"Enunciado muito curto ({len(enunciado)} chars, mínimo {self.MIN_LENGTH_ENUNCIADO})"
            )

        # Verifica se tem caracteres especiais inválidos
        if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', enunciado):
            self.avisos_encontrados.append("Enunciado contém caracteres de controle inválidos")

    def _validar_alternativas(self, questao: Dict):
        """Valida alternativas"""
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

            texto_alt = alternativas[letra].strip()

            # Verifica comprimento mínimo
            if len(texto_alt) < self.MIN_LENGTH_ALTERNATIVA:
                self.avisos_encontrados.append(
                    f"Alternativa {letra} muito curta ({len(texto_alt)} chars)"
                )

            # Verifica placeholders
            if '[' in texto_alt and ']' in texto_alt:
                self.avisos_encontrados.append(
                    f"Alternativa {letra} parece conter placeholder: {texto_alt[:50]}"
                )

    def _validar_gabarito(self, questao: Dict):
        """Valida gabarito/resposta correta"""
        correta = questao.get('correta')

        if not correta:
            self.erros_encontrados.append("Gabarito (correta) não especificado")
            return

        correta = str(correta).upper().strip()

        if correta not in self.ALTERNATIVAS_VALIDAS:
            self.erros_encontrados.append(
                f"Gabarito inválido '{correta}', deve ser A, B, C, D ou E"
            )

        # Verifica se a alternativa correta existe
        alternativas = questao.get('alternativas', {})
        if correta not in alternativas:
            self.erros_encontrados.append(
                f"Gabarito '{correta}' não existe nas alternativas"
            )

    def _validar_disciplina(self, questao: Dict):
        """Valida disciplina (warning)"""
        disciplina = questao.get('disciplina')

        if not disciplina:
            self.avisos_encontrados.append("Disciplina não especificada")
            return

        disciplina = disciplina.lower().strip()

        # Tenta normalizar variações comuns
        normalizacoes = {
            'mat': 'matematica',
            'port': 'portugues',
            'fis': 'fisica',
            'quim': 'quimica',
            'bio': 'biologia',
            'hist': 'historia',
            'geo': 'geografia',
            'filo': 'filosofia',
            'socio': 'sociologia',
            'lit': 'literatura',
            'ing': 'ingles',
            'esp': 'espanhol'
        }

        for abrev, nome_completo in normalizacoes.items():
            if abrev in disciplina:
                disciplina = nome_completo
                questao['disciplina'] = disciplina  # Atualiza
                break

        if disciplina not in self.DISCIPLINAS_VALIDAS:
            self.avisos_encontrados.append(
                f"Disciplina '{disciplina}' não reconhecida. "
                f"Válidas: {', '.join(self.DISCIPLINAS_VALIDAS)}"
            )

    def _validar_numero(self, questao: Dict):
        """Valida número da questão (warning)"""
        numero = questao.get('numero')

        if numero is None:
            self.avisos_encontrados.append("Número da questão não especificado")
            return

        # Converte para int se for string
        try:
            numero = int(numero)
            questao['numero'] = numero  # Atualiza
        except (ValueError, TypeError):
            self.avisos_encontrados.append(f"Número da questão inválido: {numero}")
            return

        # Número deve estar em range válido (1-180 para ENEM completo)
        if numero < 1 or numero > 200:
            self.avisos_encontrados.append(
                f"Número da questão {numero} fora do range esperado (1-200)"
            )

    def _validar_ano(self, questao: Dict):
        """Valida ano do ENEM (warning)"""
        ano = questao.get('ano')

        if ano is None:
            self.avisos_encontrados.append("Ano do ENEM não especificado")
            return

        # Converte para int se for string
        try:
            ano = int(ano)
            questao['ano'] = ano  # Atualiza
        except (ValueError, TypeError):
            self.avisos_encontrados.append(f"Ano inválido: {ano}")
            return

        # Ano deve estar no range válido (ENEM começou em 1998)
        ano_atual = __import__('datetime').datetime.now().year
        if ano < 1998 or ano > ano_atual + 1:
            self.avisos_encontrados.append(
                f"Ano {ano} fora do range esperado (1998-{ano_atual})"
            )

    def _validar_qualidade_texto(self, questao: Dict):
        """Valida qualidade do texto (detecta problemas)"""
        enunciado = questao.get('enunciado', '')
        alternativas = questao.get('alternativas', {})

        # Verifica encoding ruim (caracteres estranhos)
        textos = [enunciado] + list(alternativas.values())

        for texto in textos:
            # Caracteres de encoding ruins comuns
            if any(char in texto for char in ['Ã', '�', 'â€™', 'Â']):
                self.avisos_encontrados.append(
                    "Possível problema de encoding detectado (ex: Ã, â€™)"
                )
                break

        # Verifica se tem muito placeholder
        texto_completo = ' '.join(textos)
        if texto_completo.count('[') > 2 or texto_completo.count('...') > 5:
            self.avisos_encontrados.append(
                "Texto parece conter muitos placeholders ou trechos incompletos"
            )

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
        logger.info("VALIDAÇÃO DE LOTE")
        logger.info("="*70)
        logger.info(f"Total de questões: {len(questoes)}")
        logger.info(f"✅ Válidas: {validas} ({validas/len(questoes)*100:.1f}%)")
        logger.info(f"❌ Inválidas: {invalidas} ({invalidas/len(questoes)*100:.1f}%)")
        logger.info(f"⚠️  Com avisos: {com_avisos}")

        # Detalha inválidas
        if questoes_invalidas:
            logger.info("\n❌ QUESTÕES INVÁLIDAS:")
            for q in questoes_invalidas[:5]:  # Mostra primeiras 5
                logger.info(f"\n  Questão #{q['numero']} (índice {q['indice']}):")
                for erro in q['erros']:
                    logger.info(f"    • {erro}")

        # Detalha avisos
        if questoes_com_avisos:
            logger.info("\n⚠️  QUESTÕES COM AVISOS:")
            for q in questoes_com_avisos[:5]:  # Mostra primeiras 5
                logger.info(f"\n  Questão #{q['numero']} (índice {q['indice']}):")
                for aviso in q['avisos']:
                    logger.info(f"    • {aviso}")

        return {
            'total': len(questoes),
            'validas': validas,
            'invalidas': invalidas,
            'com_avisos': com_avisos,
            'questoes_invalidas': questoes_invalidas,
            'questoes_com_avisos': questoes_com_avisos
        }


# Função helper para uso direto
def validar_questao(questao: Dict, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Helper function para validar uma questão

    Args:
        questao: Dicionário com dados da questão
        strict: Modo estrito (avisos também invalidam)

    Returns:
        Tupla (is_valid, erros, avisos)

    Example:
        >>> questao = {
        ...     'enunciado': 'Qual é...?',
        ...     'alternativas': {'A': 'Opção A', ..., 'E': 'Opção E'},
        ...     'correta': 'C'
        ... }
        >>> is_valid, erros, avisos = validar_questao(questao)
    """
    validator = EnemValidator(strict_mode=strict)
    return validator.validar_questao(questao)


# ============================================================================
# MAIN - Testes
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("ENEM VALIDATOR - Testes")
    print("="*70)

    # Questão válida
    questao_valida = {
        'numero': 145,
        'ano': 2024,
        'disciplina': 'matematica',
        'enunciado': 'Uma função f(x) = ax² + bx + c tem vértice em (2, -1) e passa por (0, 3). Qual o valor de a?',
        'alternativas': {
            'A': '-1',
            'B': '0',
            'C': '1',
            'D': '2',
            'E': '3'
        },
        'correta': 'C',
        'habilidade': 'H19',
        'competencia': 5
    }

    validator = EnemValidator()
    is_valid, erros, avisos = validator.validar_questao(questao_valida)

    print(f"\n✅ Questão válida: {is_valid}")
    if erros:
        print("Erros:", erros)
    if avisos:
        print("Avisos:", avisos)

    # Questão inválida
    print("\n" + "="*70)
    print("Testando questão inválida")
    print("="*70)

    questao_invalida = {
        'enunciado': 'Texto muito curto',
        'alternativas': {
            'A': 'A',
            'B': 'B',
            'C': 'C'  # Falta D e E
        },
        'correta': 'Z'  # Gabarito inválido
    }

    is_valid, erros, avisos = validator.validar_questao(questao_invalida)

    print(f"\n❌ Questão válida: {is_valid}")
    print(f"Erros encontrados: {len(erros)}")
    for erro in erros:
        print(f"  • {erro}")
    if avisos:
        print(f"Avisos: {len(avisos)}")
        for aviso in avisos:
            print(f"  • {aviso}")
