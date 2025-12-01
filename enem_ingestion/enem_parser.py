"""
ENEM Parser - Extrai questões estruturadas de texto/PDFs do ENEM

Suporta múltiplos formatos de entrada:
- Texto plano com questões formatadas
- JSON bruto
- PDFs processados (via extração de texto)
"""

import re
import json
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnemParser:
    """Parser de questões do ENEM"""

    # Padrões regex para extração
    PATTERNS = {
        # Número da questão: "Questão 135" ou "135."
        'numero': r'(?:Questão|QUESTÃO|Quest\.|Q\.?)\s*(\d{1,3})|^(\d{1,3})\s*[\.\-]',

        # Disciplina/Área
        'disciplina': r'(?:Disciplina|Área|Matéria):\s*([A-Za-záéíóúâêôãõç\s]+)',

        # Alternativas A-E com texto
        'alternativa': r'^([A-E])\s*[\)\.\-\:]?\s*(.+)$',

        # Gabarito: "Gabarito: C" ou "Resposta: C"
        'gabarito': r'(?:Gabarito|Resposta\s+Correta|Correta):\s*([A-E])',

        # Habilidade: "H12", "H1", etc
        'habilidade': r'H(\d{1,2})',

        # Competência: "C1", "C5", etc
        'competencia': r'C(\d{1})',

        # Ano ENEM: 2015-2024
        'ano': r'ENEM\s*(\d{4})|(\d{4})'
    }

    def __init__(self):
        """Inicializa o parser"""
        self.questoes_parseadas = []

    def parse_from_text(self, texto: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Parseia questões de um bloco de texto

        Args:
            texto: Texto contendo uma ou mais questões
            metadata: Metadados adicionais (ano, área, etc)

        Returns:
            Lista de questões parseadas
        """
        questoes = []

        # Divide em blocos por questão (identifica por número)
        blocos = self._dividir_em_questoes(texto)

        for i, bloco in enumerate(blocos):
            try:
                questao = self._parse_questao_individual(bloco, metadata)
                if questao:
                    questoes.append(questao)
                    logger.info(f"✅ Questão {questao.get('numero', i+1)} parseada com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao parsear questão {i+1}: {e}")
                continue

        self.questoes_parseadas.extend(questoes)
        return questoes

    def _dividir_em_questoes(self, texto: str) -> List[str]:
        """Divide texto em blocos separados por questão"""
        # Tenta identificar padrões de separação
        # Método 1: Por número de questão
        padrao_questao = re.compile(
            r'(?:Questão|QUESTÃO)\s*\d{1,3}|^\d{1,3}[\.\-]',
            re.MULTILINE | re.IGNORECASE
        )

        posicoes = [m.start() for m in padrao_questao.finditer(texto)]

        if not posicoes:
            # Se não encontrou, retorna texto inteiro
            return [texto]

        # Adiciona início e fim
        posicoes = [0] + posicoes + [len(texto)]

        blocos = []
        for i in range(len(posicoes) - 1):
            bloco = texto[posicoes[i]:posicoes[i+1]].strip()
            if bloco:
                blocos.append(bloco)

        return blocos

    def _parse_questao_individual(self, texto: str, metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Parseia uma questão individual"""
        questao = {
            'enunciado': '',
            'alternativas': {},
            'correta': None,
            'numero': None,
            'disciplina': metadata.get('disciplina') if metadata else None,
            'ano': metadata.get('ano') if metadata else None,
            'habilidade': None,
            'competencia': None
        }

        linhas = texto.split('\n')

        # Estado do parser
        enunciado_linhas = []
        modo_alternativas = False
        alternativas_temp = {}

        for linha in linhas:
            linha = linha.strip()
            if not linha:
                continue

            # Extrai número da questão
            if questao['numero'] is None:
                match_num = re.search(self.PATTERNS['numero'], linha, re.IGNORECASE)
                if match_num:
                    questao['numero'] = int(match_num.group(1) or match_num.group(2))
                    continue

            # Extrai disciplina
            match_disc = re.search(self.PATTERNS['disciplina'], linha, re.IGNORECASE)
            if match_disc and not questao['disciplina']:
                questao['disciplina'] = match_disc.group(1).strip().lower()
                continue

            # Extrai ano
            match_ano = re.search(self.PATTERNS['ano'], linha)
            if match_ano and not questao['ano']:
                questao['ano'] = int(match_ano.group(1) or match_ano.group(2))
                continue

            # Extrai gabarito
            match_gab = re.search(self.PATTERNS['gabarito'], linha, re.IGNORECASE)
            if match_gab:
                questao['correta'] = match_gab.group(1).upper()
                continue

            # Extrai habilidade
            match_hab = re.search(self.PATTERNS['habilidade'], linha)
            if match_hab and not questao['habilidade']:
                questao['habilidade'] = f"H{match_hab.group(1)}"
                continue

            # Extrai competência
            match_comp = re.search(self.PATTERNS['competencia'], linha)
            if match_comp and not questao['competencia']:
                questao['competencia'] = int(match_comp.group(1))
                continue

            # Verifica se é alternativa (A-E)
            match_alt = re.match(self.PATTERNS['alternativa'], linha, re.MULTILINE)
            if match_alt:
                letra = match_alt.group(1).upper()
                texto_alt = match_alt.group(2).strip()
                alternativas_temp[letra] = texto_alt
                modo_alternativas = True
                continue

            # Se não é alternativa e já passou por elas, é continuação do enunciado ou texto extra
            if not modo_alternativas:
                enunciado_linhas.append(linha)
            else:
                # Continuação da última alternativa
                if alternativas_temp:
                    ultima_letra = list(alternativas_temp.keys())[-1]
                    alternativas_temp[ultima_letra] += ' ' + linha

        # Monta enunciado
        questao['enunciado'] = ' '.join(enunciado_linhas).strip()

        # Valida alternativas (deve ter exatamente 5: A-E)
        if len(alternativas_temp) == 5:
            questao['alternativas'] = alternativas_temp
        else:
            # Tenta preencher alternativas faltantes com placeholder
            for letra in ['A', 'B', 'C', 'D', 'E']:
                if letra not in alternativas_temp:
                    alternativas_temp[letra] = f"[Alternativa {letra} não extraída]"
            questao['alternativas'] = alternativas_temp

        # Retorna None se questão inválida (sem enunciado ou alternativas)
        if not questao['enunciado'] or not questao['alternativas']:
            logger.warning(f"Questão inválida: enunciado ou alternativas vazias")
            return None

        return questao

    def parse_from_json_file(self, json_path: Union[str, Path]) -> List[Dict]:
        """
        Parseia questões de arquivo JSON

        Args:
            json_path: Caminho para arquivo JSON

        Returns:
            Lista de questões parseadas e padronizadas
        """
        json_path = Path(json_path)

        if not json_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Suporta múltiplos formatos
        questoes = []

        # Formato 1: {"questoes": [...]}
        if isinstance(data, dict) and 'questoes' in data:
            raw_questoes = data['questoes']
        # Formato 2: [...]
        elif isinstance(data, list):
            raw_questoes = data
        # Formato 3: {...} (questão única)
        else:
            raw_questoes = [data]

        for q in raw_questoes:
            questao_padronizada = self._padronizar_questao(q)
            if questao_padronizada:
                questoes.append(questao_padronizada)

        logger.info(f"✅ {len(questoes)} questões extraídas de {json_path.name}")
        return questoes

    def _padronizar_questao(self, questao_raw: Dict) -> Optional[Dict]:
        """
        Padroniza questão para formato unificado

        Entrada aceita múltiplos formatos, saída sempre no padrão:
        {
            "numero": 145,
            "ano": 2024,
            "disciplina": "matematica",
            "enunciado": "...",
            "alternativas": {"A": "...", "B": "...", ...},
            "correta": "C",
            "habilidade": "H19",
            "competencia": 5
        }
        """
        questao = {}

        # Número
        questao['numero'] = questao_raw.get('numero') or questao_raw.get('id') or questao_raw.get('numero_questao')

        # Ano
        questao['ano'] = questao_raw.get('ano') or questao_raw.get('ano_enem') or questao_raw.get('year')

        # Disciplina/Área
        disciplina = (
            questao_raw.get('disciplina') or
            questao_raw.get('area') or
            questao_raw.get('materia') or
            questao_raw.get('subject')
        )
        questao['disciplina'] = disciplina.lower().strip() if disciplina else None

        # Enunciado
        questao['enunciado'] = questao_raw.get('enunciado') or questao_raw.get('texto') or questao_raw.get('question')

        # Alternativas (padroniza para dict)
        alternativas_raw = questao_raw.get('alternativas') or questao_raw.get('opcoes') or questao_raw.get('options')

        if isinstance(alternativas_raw, dict):
            # Já é dict
            questao['alternativas'] = alternativas_raw
        elif isinstance(alternativas_raw, list):
            # Converte lista para dict
            if len(alternativas_raw) >= 5:
                questao['alternativas'] = {
                    'A': alternativas_raw[0],
                    'B': alternativas_raw[1],
                    'C': alternativas_raw[2],
                    'D': alternativas_raw[3],
                    'E': alternativas_raw[4]
                }
            else:
                # Lista incompleta
                questao['alternativas'] = {}
                for i, texto in enumerate(alternativas_raw):
                    letra = chr(65 + i)  # A=65, B=66, ...
                    questao['alternativas'][letra] = texto
        else:
            questao['alternativas'] = {}

        # Gabarito/Correta
        correta = (
            questao_raw.get('correta') or
            questao_raw.get('gabarito') or
            questao_raw.get('resposta_correta') or
            questao_raw.get('correct')
        )
        questao['correta'] = correta.upper() if correta else None

        # Habilidade
        habilidade = questao_raw.get('habilidade') or questao_raw.get('habilidade_enem')
        questao['habilidade'] = habilidade if habilidade else None

        # Competência
        comp = questao_raw.get('competencia') or questao_raw.get('competencia_enem')
        if comp:
            # Extrai número se for string como "C5"
            if isinstance(comp, str):
                match = re.search(r'(\d+)', comp)
                questao['competencia'] = int(match.group(1)) if match else None
            else:
                questao['competencia'] = int(comp)
        else:
            questao['competencia'] = None

        # Explicação (opcional)
        questao['explicacao'] = questao_raw.get('explicacao') or questao_raw.get('justificativa')

        # Validação mínima
        if not questao['enunciado']:
            logger.warning(f"Questão sem enunciado, pulando")
            return None

        if not questao['alternativas'] or len(questao['alternativas']) != 5:
            logger.warning(f"Questão {questao.get('numero', '?')} sem 5 alternativas, pulando")
            return None

        return questao

    def export_to_json(self, output_path: Union[str, Path], questoes: Optional[List[Dict]] = None):
        """
        Exporta questões para arquivo JSON padronizado

        Args:
            output_path: Caminho de saída
            questoes: Lista de questões (usa self.questoes_parseadas se None)
        """
        output_path = Path(output_path)
        questoes = questoes or self.questoes_parseadas

        if not questoes:
            logger.warning("Nenhuma questão para exportar")
            return

        # Cria estrutura padrão
        data = {
            "versao": "1.0",
            "total_questoes": len(questoes),
            "gerado_em": __import__('datetime').datetime.now().isoformat(),
            "questoes": questoes
        }

        # Salva com encoding UTF-8
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ {len(questoes)} questões exportadas para {output_path}")


# Função helper para uso direto
def parse_questao_from_text(texto: str, metadata: Optional[Dict] = None) -> List[Dict]:
    """
    Helper function para parsear questões diretamente de texto

    Args:
        texto: Texto com questões
        metadata: Metadados (disciplina, ano, etc)

    Returns:
        Lista de questões parseadas

    Example:
        >>> texto = '''
        ... Questão 145 - Matemática
        ... Uma empresa...
        ... A) Opção A
        ... B) Opção B
        ... ...
        ... Gabarito: C
        ... '''
        >>> questoes = parse_questao_from_text(texto, {'ano': 2024})
    """
    parser = EnemParser()
    return parser.parse_from_text(texto, metadata)


# ============================================================================
# MAIN - Exemplos de uso
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("ENEM PARSER - Testes")
    print("="*70)

    # Exemplo 1: Parse de texto
    texto_exemplo = """
    Questão 145 - Matemática
    ENEM 2024

    Uma função quadrática f(x) = ax² + bx + c tem vértice no ponto (2, -1) e
    passa pelo ponto (0, 3). Qual o valor de a?

    A) -1
    B) 0
    C) 1
    D) 2
    E) 3

    Gabarito: C
    Habilidade: H19
    Competência: C5
    """

    parser = EnemParser()
    questoes = parser.parse_from_text(texto_exemplo)

    if questoes:
        print("\n✅ Questão parseada:")
        print(json.dumps(questoes[0], indent=2, ensure_ascii=False))

    # Exemplo 2: Parse de JSON
    print("\n" + "="*70)
    print("Teste com JSON existente")
    print("="*70)

    json_teste = Path("../simulado_exemplo_fisica.json")
    if json_teste.exists():
        questoes_json = parser.parse_from_json_file(json_teste)
        print(f"✅ {len(questoes_json)} questões extraídas do JSON")

        # Exporta padronizado
        parser.export_to_json("../questoes_padronizadas.json", questoes_json)
    else:
        print(f"⚠️ Arquivo {json_teste} não encontrado")
