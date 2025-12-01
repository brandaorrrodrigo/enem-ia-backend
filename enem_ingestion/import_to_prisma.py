"""
Import to Prisma - Importa questões validadas para banco Prisma (SQLite)

Usa subprocess para executar comandos Node.js/Prisma CLI
"""

import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PrismaImporter:
    """Importador de questões para banco Prisma"""

    def __init__(self, prisma_project_path: Optional[Union[str, Path]] = None):
        """
        Inicializa o importador

        Args:
            prisma_project_path: Caminho para o projeto Next.js com Prisma
                                 (default: busca automaticamente)
        """
        if prisma_project_path:
            self.prisma_path = Path(prisma_project_path)
        else:
            # Tenta encontrar automaticamente
            self.prisma_path = self._find_prisma_project()

        if not self.prisma_path:
            raise FileNotFoundError(
                "Projeto Prisma não encontrado. "
                "Especifique prisma_project_path manualmente."
            )

        self.schema_path = self.prisma_path / "prisma" / "schema.prisma"
        self.db_path = self.prisma_path / "prisma" / "dev.db"

        logger.info(f"📂 Projeto Prisma: {self.prisma_path}")
        logger.info(f"📄 Schema: {self.schema_path}")
        logger.info(f"💾 Database: {self.db_path}")

    def _find_prisma_project(self) -> Optional[Path]:
        """Encontra projeto Prisma automaticamente"""
        # Tenta encontrar em locais comuns
        current_dir = Path(__file__).resolve().parent
        possible_paths = [
            current_dir / "../../enem-pro",  # Relativo ao backend
            Path.cwd() / "enem-pro",
            Path.cwd().parent / "enem-pro",
        ]

        for path in possible_paths:
            schema = path / "prisma" / "schema.prisma"
            if schema.exists():
                return path.resolve()

        return None

    def _run_node_command(self, command: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """
        Executa comando Node.js

        Args:
            command: Comando como lista ['node', 'script.js']
            cwd: Diretório de trabalho

        Returns:
            CompletedProcess
        """
        cwd = cwd or self.prisma_path

        logger.debug(f"Executando: {' '.join(command)}")
        logger.debug(f"CWD: {cwd}")

        try:
            result = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            return result
        except FileNotFoundError as e:
            logger.error(f"Comando não encontrado: {command[0]}")
            logger.error(f"Certifique-se de que Node.js está instalado: node --version")
            raise

    def criar_script_importacao(self, questoes: List[Dict], output_path: Optional[Path] = None) -> Path:
        """
        Cria script Node.js para importar questões via Prisma Client

        Args:
            questoes: Lista de questões a importar
            output_path: Caminho de saída do script

        Returns:
            Path do script criado
        """
        if not output_path:
            output_path = self.prisma_path / "scripts" / "import_questoes_temp.mjs"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepara dados para o script
        questoes_json = json.dumps(questoes, ensure_ascii=False, indent=2)

        # Script Node.js/TypeScript
        script_content = f'''// Script de importação automática - Gerado por Python
// NÃO EDITE MANUALMENTE

import {{ PrismaClient }} from '@prisma/client';

const prisma = new PrismaClient();

const questoes = {questoes_json};

async function main() {{
  console.log('🚀 Iniciando importação de questões...');
  console.log(`📊 Total de questões: ${{questoes.length}}`);

  let importadas = 0;
  let duplicadas = 0;
  let erros = 0;

  for (const [index, questao] of questoes.entries()) {{
    try {{
      // Verifica se já existe (por enunciado)
      const existente = await prisma.questao.findFirst({{
        where: {{
          enunciado: questao.enunciado
        }}
      }});

      if (existente) {{
        console.log(`⚠️  [${{index + 1}}] Questão duplicada (já existe no banco)`);
        duplicadas++;
        continue;
      }}

      // Prepara alternativas em formato JSON
      const alternativasArray = [
        questao.alternativas.A || '',
        questao.alternativas.B || '',
        questao.alternativas.C || '',
        questao.alternativas.D || '',
        questao.alternativas.E || ''
      ];

      // Converte letra correta para índice (0-4)
      const letraParaIndice = {{ 'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4 }};
      const corretaIndice = letraParaIndice[questao.correta] || 0;

      // Insere no banco
      const created = await prisma.questao.create({{
        data: {{
          enunciado: questao.enunciado,
          alternativas: alternativasArray,
          correta: corretaIndice
        }}
      }});

      console.log(`✅ [${{index + 1}}/${{questoes.length}}] Questão #${{created.id}} importada`);
      importadas++;

    }} catch (error) {{
      console.error(`❌ [${{index + 1}}] Erro ao importar:`, error.message);
      erros++;
    }}
  }}

  console.log('\\n' + '='.repeat(70));
  console.log('📊 RESUMO DA IMPORTAÇÃO');
  console.log('='.repeat(70));
  console.log(`✅ Importadas: ${{importadas}}`);
  console.log(`⚠️  Duplicadas (ignoradas): ${{duplicadas}}`);
  console.log(`❌ Erros: ${{erros}}`);
  console.log('='.repeat(70));
}}

main()
  .catch((e) => {{
    console.error('💥 Erro fatal:', e);
    process.exit(1);
  }})
  .finally(async () => {{
    await prisma.$disconnect();
  }});
'''

        # Salva script
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        logger.info(f"📝 Script de importação criado: {output_path}")
        return output_path

    def importar_questoes(self, questoes: List[Dict]) -> Dict:
        """
        Importa questões para o banco Prisma

        Args:
            questoes: Lista de questões validadas

        Returns:
            Estatísticas da importação
        """
        if not questoes:
            logger.warning("Lista de questões vazia")
            return {
                'success': False,
                'importadas': 0,
                'erros': 0,
                'mensagem': 'Nenhuma questão para importar'
            }

        logger.info(f"📦 Preparando importação de {len(questoes)} questões...")

        # 1. Cria script de importação
        script_path = self.criar_script_importacao(questoes)

        # 2. Executa script via Node.js
        logger.info("🚀 Executando importação...")

        try:
            result = self._run_node_command(['node', str(script_path)])

            # Mostra output
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logger.info(line)

            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip() and 'warn' not in line.lower():
                        logger.error(line)

            # Verifica sucesso
            if result.returncode == 0:
                logger.info("✅ Importação concluída com sucesso!")

                # Remove script temporário
                if script_path.name == 'import_questoes_temp.mjs':
                    script_path.unlink()

                return {
                    'success': True,
                    'importadas': len(questoes),
                    'erros': 0,
                    'mensagem': 'Importação bem-sucedida'
                }
            else:
                logger.error(f"❌ Importação falhou (código {result.returncode})")
                return {
                    'success': False,
                    'importadas': 0,
                    'erros': len(questoes),
                    'mensagem': f'Erro na execução: {result.stderr[:200]}'
                }

        except Exception as e:
            logger.error(f"💥 Erro ao executar importação: {e}")
            return {
                'success': False,
                'importadas': 0,
                'erros': len(questoes),
                'mensagem': str(e)
            }

    def verificar_banco(self) -> Dict:
        """
        Verifica estatísticas do banco de dados

        Returns:
            Estatísticas (total de questões, etc)
        """
        logger.info("📊 Verificando banco de dados...")

        # Script para contar questões
        count_script = self.prisma_path / "scripts" / "count_temp.mjs"

        script_content = '''
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

async function main() {
  const count = await prisma.questao.count();
  console.log(JSON.stringify({ total: count }));
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(async () => { await prisma.$disconnect(); });
'''

        count_script.parent.mkdir(parents=True, exist_ok=True)
        with open(count_script, 'w', encoding='utf-8') as f:
            f.write(script_content)

        try:
            result = self._run_node_command(['node', str(count_script)])

            if result.returncode == 0:
                # Parse JSON output
                for line in result.stdout.split('\n'):
                    if line.strip().startswith('{'):
                        stats = json.loads(line)
                        logger.info(f"✅ Total de questões no banco: {stats['total']}")
                        count_script.unlink()  # Remove temp
                        return stats

            logger.error("❌ Erro ao verificar banco")
            return {'total': 0, 'error': result.stderr}

        except Exception as e:
            logger.error(f"💥 Erro: {e}")
            return {'total': 0, 'error': str(e)}


# Função helper para uso direto
def import_questoes_to_prisma(
    questoes: List[Dict],
    prisma_project_path: Optional[Union[str, Path]] = None
) -> Dict:
    """
    Helper function para importar questões diretamente

    Args:
        questoes: Lista de questões validadas
        prisma_project_path: Caminho do projeto Prisma (opcional)

    Returns:
        Estatísticas da importação

    Example:
        >>> from enem_parser import EnemParser
        >>> from enem_validator import EnemValidator
        >>> from import_to_prisma import import_questoes_to_prisma
        >>>
        >>> # 1. Parse
        >>> parser = EnemParser()
        >>> questoes = parser.parse_from_json_file('questoes.json')
        >>>
        >>> # 2. Valida
        >>> validator = EnemValidator()
        >>> stats = validator.validar_lote(questoes)
        >>>
        >>> # 3. Importa apenas as válidas
        >>> questoes_validas = [q for q in questoes if validator.validar_questao(q)[0]]
        >>> result = import_questoes_to_prisma(questoes_validas)
    """
    importer = PrismaImporter(prisma_project_path)
    return importer.importar_questoes(questoes)


# ============================================================================
# MAIN - Testes
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("PRISMA IMPORTER - Testes")
    print("="*70)

    # Testa inicialização
    try:
        importer = PrismaImporter()
        print("\n✅ Importer inicializado")

        # Verifica banco
        stats = importer.verificar_banco()
        print(f"📊 Questões no banco: {stats.get('total', 0)}")

        # Questão de teste
        questao_teste = {
            'numero': 1,
            'ano': 2024,
            'disciplina': 'matematica',
            'enunciado': 'Teste de importação: Quanto é 2 + 2?',
            'alternativas': {
                'A': '3',
                'B': '4',
                'C': '5',
                'D': '6',
                'E': '7'
            },
            'correta': 'B'
        }

        print("\n🧪 Deseja testar importação de 1 questão? (s/n): ", end='')
        resposta = input().strip().lower()

        if resposta == 's':
            result = importer.importar_questoes([questao_teste])
            print(f"\n✅ Resultado: {result}")

    except FileNotFoundError as e:
        print(f"\n❌ Erro: {e}")
        print("\n💡 Dica: Certifique-se de que o projeto Next.js está em ../enem-pro")
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
