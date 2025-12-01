"""
ENEM Parser REAL - Parser ROBUSTO para questões REAIS de PDFs do ENEM

Melhorias sobre o parser padrão:
- Detecta múltiplos formatos de numeração (91., Questão 91, Q91, apenas 91)
- Extrai alternativas mesmo sem pontuação consistente
- Tolera quebras de linha e formatação inconsistente
- Ignora seções não-questão (instruções, cabeçalhos)
- Detecta fim de questão por próxima questão ou mudança de seção

Usado para: PDFs oficiais do ENEM (2009-2024)
"""

import re
from typing import Dict, List, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnemParserReal:
    """Parser ROBUSTO para questões REAIS de PDFs do ENEM"""

    # Padrões regex MAIS FLEXÍVEIS
    PATTERNS = {
        # Número da questão: aceita múltiplos formatos
        'numero': r'(?:QUESTÃO|Questão|QUESTAO|Questao|Quest\.|Q\.?|Num\.?)\s*(\d{1,3})|^(\d{1,3})\s*[\.\-\)]|^(\d{1,3})$',

        # Alternativas: aceita múltiplos formatos
        # A) texto, (A) texto, A. texto, A - texto, [A] texto
        'alternativa': r'^[\(\[]?([A-E])[\)\]\.\-\:\s]+(.+)$',

        # Gabarito (múltiplos formatos)
        'gabarito': r'(?:Gabarito|GAB|Resposta|RESPOSTA|Correta|CORRETA)[\s\:]*([A-E])',

        # Indicadores de seção não-questão
        'secao_ignorar': r'^(INSTRUÇÕES|ATENÇÃO|RASCUNHO|FOLHA DE RESPOSTAS|PROVA DE|CADERNO DE)',
    }

    def __init__(self):
        """Inicializa o parser"""
        self.questoes_parseadas = []
        self.debug = False

    def parse_from_text(self, texto: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Parseia questões de texto extraído de PDF

        Args:
            texto: Texto do PDF
            metadata: Metadados (ano, fonte, etc)

        Returns:
            Lista de questões parseadas
        """
        # Limpa texto
        texto = self._limpar_texto(texto)

        # Divide em blocos por questão
        blocos = self._dividir_em_questoes(texto)

        questoes = []
        for i, bloco in enumerate(blocos):
            try:
                questao = self._parse_questao_individual(bloco, metadata)
                if questao:
                    questoes.append(questao)
                    if self.debug:
                        logger.info(f"✅ Questão {questao.get('numero', i+1)} parseada")
            except Exception as e:
                if self.debug:
                    logger.error(f"❌ Erro ao parsear bloco {i+1}: {e}")
                continue

        self.questoes_parseadas.extend(questoes)
        return questoes

    def _limpar_texto(self, texto: str) -> str:
        """Remove ruído e normaliza texto"""
        # Remove caracteres de controle
        texto = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', texto)

        # Normaliza espaços múltiplos
        texto = re.sub(r'[ \t]+', ' ', texto)

        # Remove linhas em branco excessivas
        texto = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto)

        return texto

    def _dividir_em_questoes(self, texto: str) -> List[str]:
        """
        Divide texto em blocos de questões

        Estratégia:
        1. Procura números de questão (91, 92, 93...)
        2. Assume que cada número inicia uma nova questão
        3. Questão termina quando encontra próximo número
        """
        # Padrão: linha que começa com número (possivelmente com espaços)
        padrao_numero = re.compile(
            r'^\s*(?:QUESTÃO|Questão|Quest\.|Q\.?)?\s*(\d{1,3})\s*[\.\-\)]?',
            re.MULTILINE | re.IGNORECASE
        )

        # Encontra todas as posições de números
        matches = list(padrao_numero.finditer(texto))

        if not matches:
            logger.warning("Nenhuma questão numerada encontrada no texto")
            return [texto]  # Retorna texto inteiro

        blocos = []
        for i, match in enumerate(matches):
            inicio = match.start()

            # Fim é o início da próxima questão (ou fim do texto)
            if i < len(matches) - 1:
                fim = matches[i + 1].start()
            else:
                fim = len(texto)

            bloco = texto[inicio:fim].strip()

            # Ignora blocos muito curtos (< 50 chars)
            if len(bloco) >= 50:
                blocos.append(bloco)

        logger.info(f"📊 Dividido em {len(blocos)} blocos de questões")
        return blocos

    def _parse_questao_individual(self, texto: str, metadata: Optional[Dict] = None) -> Optional[Dict]:
        """
        Parseia uma questão individual

        Args:
            texto: Texto da questão
            metadata: Metadados externos

        Returns:
            Questão parseada ou None
        """
        # Ignora seções não-questão
        if re.search(self.PATTERNS['secao_ignorar'], texto, re.IGNORECASE):
            return None

        questao = {
            'enunciado': '',
            'alternativas': {},
            'correta': None,
            'numero': None,
            'disciplina': metadata.get('disciplina') if metadata else None,
            'ano': metadata.get('ano') if metadata else None,
            'tipo': 'real',
            'fonte': metadata.get('fonte') if metadata else 'pdf_enem'
        }

        linhas = texto.split('\n')

        # Estados do parser
        enunciado_linhas = []
        modo_alternativas = False
        alternativas_temp = {}
        ultima_letra = None

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue

            # 1. Extrai número da questão (apenas primeira vez)
            if questao['numero'] is None:
                match_num = re.search(self.PATTERNS['numero'], linha, re.IGNORECASE)
                if match_num:
                    # Tenta extrair de qualquer grupo
                    for grupo in match_num.groups():
                        if grupo and grupo.isdigit():
                            questao['numero'] = int(grupo)
                            break
                    continue

            # 2. Extrai gabarito
            match_gab = re.search(self.PATTERNS['gabarito'], linha, re.IGNORECASE)
            if match_gab:
                questao['correta'] = match_gab.group(1).upper()
                continue

            # 3. Verifica se é alternativa
            match_alt = re.match(self.PATTERNS['alternativa'], linha, re.IGNORECASE)
            if match_alt:
                letra = match_alt.group(1).upper()
                texto_alt = match_alt.group(2).strip()

                alternativas_temp[letra] = texto_alt
                ultima_letra = letra
                modo_alternativas = True
                continue

            # 4. Linha de continuação
            if modo_alternativas and ultima_letra:
                # Se já temos 5 alternativas, para de adicionar
                if len(alternativas_temp) >= 5:
                    continue

                # Adiciona à última alternativa
                alternativas_temp[ultima_letra] += ' ' + linha
            else:
                # Faz parte do enunciado
                enunciado_linhas.append(linha)

        # Monta enunciado
        questao['enunciado'] = ' '.join(enunciado_linhas).strip()

        # Normaliza alternativas (deve ter exatamente 5)
        questao['alternativas'] = self._normalizar_alternativas(alternativas_temp)

        # Validação básica
        if not questao['enunciado'] or len(questao['alternativas']) != 5:
            return None

        # Define gabarito padrão se não encontrou
        if not questao['correta']:
            questao['correta'] = 'A'

        return questao

    def _normalizar_alternativas(self, alternativas_raw: Dict[str, str]) -> Dict[str, str]:
        """
        Normaliza alternativas para ter exatamente A-E

        Args:
            alternativas_raw: Dicionário bruto de alternativas

        Returns:
            Dicionário normalizado com A, B, C, D, E
        """
        alternativas = {}

        for letra in ['A', 'B', 'C', 'D', 'E']:
            if letra in alternativas_raw:
                # Remove espaços extras
                texto = alternativas_raw[letra].strip()
                # Remove quebras de linha excessivas
                texto = re.sub(r'\s+', ' ', texto)
                alternativas[letra] = texto
            else:
                # Alternativa faltando
                alternativas[letra] = f"[Alternativa {letra}]"

        return alternativas

    def extrair_ano_do_filename(self, filename: str) -> Optional[int]:
        """
        Extrai ano do nome do arquivo

        Args:
            filename: Nome do arquivo PDF

        Returns:
            Ano (2009-2024) ou None
        """
        match = re.search(r'20[0-2][0-9]', filename)
        if match:
            ano = int(match.group())
            if 2009 <= ano <= 2024:
                return ano
        return None

    def inferir_disciplina(self, filename: str, texto: str) -> str:
        """
        Infere disciplina do arquivo ou texto

        Args:
            filename: Nome do arquivo
            texto: Texto da questão

        Returns:
            Disciplina inferida
        """
        filename_lower = filename.lower()
        texto_lower = texto.lower()[:500]  # Primeiros 500 chars

        # Mapas de palavras-chave
        mapa = {
            'matematica': ['matematica', 'algebra', 'geometria', 'calculo'],
            'fisica': ['fisica', 'energia', 'movimento', 'força'],
            'quimica': ['quimica', 'molecula', 'reacao', 'elemento'],
            'biologia': ['biologia', 'celula', 'dna', 'genetica', 'organismo'],
            'historia': ['historia', 'século', 'guerra', 'revolucao'],
            'geografia': ['geografia', 'clima', 'territorio', 'populacao'],
            'portugues': ['portugues', 'texto', 'interpretacao', 'gramatica'],
            'literatura': ['literatura', 'poema', 'romance', 'autor'],
        }

        # Verifica filename primeiro
        for disciplina, palavras in mapa.items():
            for palavra in palavras:
                if palavra in filename_lower:
                    return disciplina

        # Depois verifica texto
        for disciplina, palavras in mapa.items():
            for palavra in palavras:
                if palavra in texto_lower:
                    return disciplina

        # Padrão
        return 'geral'


# Função helper para uso direto
def parse_questao_from_pdf_text(texto: str, filename: str = '') -> List[Dict]:
    """
    Helper function para parsear questões de texto de PDF

    Args:
        texto: Texto extraído do PDF
        filename: Nome do arquivo (para inferir metadados)

    Returns:
        Lista de questões parseadas
    """
    parser = EnemParserReal()

    metadata = {
        'fonte': filename or 'pdf_enem',
        'ano': parser.extrair_ano_do_filename(filename) if filename else None,
        'disciplina': parser.inferir_disciplina(filename, texto) if filename else None
    }

    return parser.parse_from_text(texto, metadata)
