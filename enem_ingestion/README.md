# Módulo de Ingestão ENEM → Prisma

Pipeline completo para processar questões do ENEM e importar no banco de dados Prisma.

## 📦 Estrutura

```
enem_ingestion/
├── __init__.py                     # Módulo principal
├── enem_parser.py                  # Parser de questões (texto/JSON → dict)
├── enem_validator.py               # Validador de integridade
├── import_to_prisma.py             # Importação para banco Prisma
├── pipeline_completo.py            # Orquestrador do pipeline
├── exemplo_questoes_enem.json      # Exemplo de JSON padronizado
└── README.md                       # Esta documentação
```

## 🚀 Pipeline Completo

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   PDF/TXT   │─────▶│   PARSER    │─────▶│  VALIDATOR  │─────▶│   PRISMA    │
│  Questões   │      │   (Python)  │      │   (Python)  │      │  (Node.js)  │
└─────────────┘      └─────────────┘      └─────────────┘      └─────────────┘
       │                     │                    │                    │
       │                     │                    │                    │
    Texto               JSON Dict           Validação             SQLite DB
  do ENEM            Padronizado          Integridade           (enem-pro)
```

## 📋 Formato JSON Padronizado

```json
{
  "versao": "1.0",
  "total_questoes": 1,
  "questoes": [
    {
      "numero": 145,
      "ano": 2024,
      "disciplina": "matematica",
      "enunciado": "Uma função quadrática f(x) = ax² + bx + c...",
      "alternativas": {
        "A": "Texto da alternativa A",
        "B": "Texto da alternativa B",
        "C": "Texto da alternativa C",
        "D": "Texto da alternativa D",
        "E": "Texto da alternativa E"
      },
      "correta": "C",
      "habilidade": "H19",
      "competencia": 5,
      "explicacao": "Explicação detalhada (opcional)"
    }
  ]
}
```

### Campos Obrigatórios

- `enunciado` (string): Texto da questão (mínimo 20 caracteres)
- `alternativas` (object): Objeto com 5 alternativas (A-E)
- `correta` (string): Letra da alternativa correta (A-E)

### Campos Opcionais

- `numero` (integer): Número da questão (1-200)
- `ano` (integer): Ano do ENEM (1998-2025)
- `disciplina` (string): Área/matéria (matemática, física, etc)
- `habilidade` (string): Habilidade ENEM (H1-H30)
- `competencia` (integer): Competência ENEM (1-5)
- `explicacao` (string): Resolução detalhada

## 🛠️ Uso

### 1. Instalação de Dependências

```bash
# Backend Python
cd backend
pip install -r requirements.txt

# Frontend Prisma (necessário para importação)
cd ../enem-pro
npm install
npx prisma generate
```

### 2. Uso Básico

#### Via CLI (Recomendado)

```bash
cd backend/enem_ingestion

# Importar questões de JSON
python pipeline_completo.py questoes.json

# Exportar JSON padronizado antes de importar
python pipeline_completo.py questoes.json --output questoes_padrao.json

# Apenas validar (sem importar)
python pipeline_completo.py questoes.json --skip-import

# Validação estrita (avisos também invalidam)
python pipeline_completo.py questoes.json --strict
```

#### Via Python (Programático)

```python
from enem_ingestion import EnemParser, EnemValidator, PrismaImporter

# 1. Parse
parser = EnemParser()
questoes = parser.parse_from_json_file('questoes.json')

# 2. Valida
validator = EnemValidator()
stats = validator.validar_lote(questoes)

# Filtra apenas válidas
questoes_validas = [
    q for q in questoes
    if validator.validar_questao(q)[0]
]

# 3. Importa
importer = PrismaImporter()
result = importer.importar_questoes(questoes_validas)

print(f"✅ {result['importadas']} questões importadas!")
```

### 3. Parsing de Texto

Se você tem questões em formato texto (não JSON):

```python
from enem_ingestion import parse_questao_from_text

texto = """
Questão 145 - Matemática
ENEM 2024

Uma função quadrática...

A) Opção A
B) Opção B
C) Opção C
D) Opção D
E) Opção E

Gabarito: C
Habilidade: H19
Competência: 5
"""

questoes = parse_questao_from_text(texto, metadata={'ano': 2024})
```

## 📚 Exemplos

### Converter JSON Antigo para Novo Formato

```python
from enem_parser import EnemParser

# Parse JSON no formato antigo
parser = EnemParser()
questoes = parser.parse_from_json_file('simulado_exemplo_fisica.json')

# Exporta no formato padronizado
parser.export_to_json('questoes_padronizadas.json', questoes)
```

### Validação Detalhada

```python
from enem_validator import EnemValidator

validator = EnemValidator(strict_mode=True)

questao = {
    'enunciado': 'Qual é 2+2?',
    'alternativas': {'A': '3', 'B': '4', 'C': '5', 'D': '6', 'E': '7'},
    'correta': 'B'
}

is_valid, erros, avisos = validator.validar_questao(questao)

if is_valid:
    print("✅ Questão válida!")
else:
    print("❌ Erros:", erros)
    print("⚠️  Avisos:", avisos)
```

### Pipeline Personalizado

```python
from enem_ingestion import EnemPipeline
from pathlib import Path

pipeline = EnemPipeline(
    prisma_project_path=Path('../enem-pro'),
    strict_validation=False
)

stats = pipeline.executar(
    input_source=Path('questoes.json'),
    output_json=Path('questoes_padrao.json'),
    skip_import=False
)

print(f"📊 Parseadas: {stats['total_parseadas']}")
print(f"✅ Válidas: {stats['total_validas']}")
print(f"🗄️  Importadas: {stats['total_importadas']}")
```

## 🔧 Troubleshooting

### Erro: "Projeto Prisma não encontrado"

```bash
# Especifique o caminho manualmente
python pipeline_completo.py questoes.json --prisma-path ../enem-pro
```

### Erro: "node command not found"

Certifique-se de que Node.js está instalado:

```bash
node --version  # Deve retornar v18+
npm --version
```

### Erro de encoding (caracteres estranhos)

O parser detecta automaticamente problemas de encoding e avisa. Para corrigir:

```python
# Salve seu JSON com UTF-8
import json

with open('questoes.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### Questões duplicadas

O importador automaticamente ignora questões com enunciado duplicado:

```
⚠️  Questão duplicada (já existe no banco)
```

## 📊 Validações Realizadas

### Validações Obrigatórias (Erros)

- ✅ Enunciado não vazio (mínimo 20 caracteres)
- ✅ Exatamente 5 alternativas (A-E)
- ✅ Gabarito válido (A-E) e existente
- ✅ Alternativas não vazias (mínimo 3 caracteres)

### Validações Opcionais (Avisos)

- ⚠️ Disciplina válida (matemática, física, etc)
- ⚠️ Número da questão no range (1-200)
- ⚠️ Ano ENEM válido (1998-2025)
- ⚠️ Problemas de encoding detectados
- ⚠️ Placeholders ou trechos incompletos

## 🔗 Integração com Outros Módulos

### Com `question_generator.py` (Geração IA)

```python
from question_generator import question_gen
from enem_ingestion import import_questoes_to_prisma

# Gera questões com IA
questao_ia = question_gen.generate_question('matematica', 'medio')

# Importa diretamente
import_questoes_to_prisma([questao_ia])
```

### Com `rag_system_pdf.py` (RAG)

```python
from rag_system_pdf import rag_pdf
from enem_ingestion import parse_questao_from_text

# Busca contexto em PDFs
contexto = rag_pdf.search("função quadrática", top_k=3)

# Parse questão baseada no contexto
# ... (seu código de extração)
```

## 📝 Logs e Debug

O módulo usa `logging` do Python. Para ver mais detalhes:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Agora verá logs detalhados
from enem_ingestion import EnemParser
parser = EnemParser()
# ...
```

## 🚀 Próximos Passos

Após importar as questões:

1. **Verificar banco:**
   ```bash
   cd enem-pro
   npx prisma studio
   ```

2. **Usar nas APIs:**
   - GET /api/questoes
   - POST /api/simulados/criar
   - POST /api/simulados/{id}/responder

3. **Gerar simulados:**
   ```typescript
   // app/api/simulados/criar/route.ts
   const questoes = await prisma.questao.findMany({
     where: { disciplina: 'matematica' },
     take: 10
   });
   ```

## 📄 Licença

MIT - Projeto ENEM-IA

## 🤝 Contribuindo

Para adicionar novos formatos de parsing ou melhorias:

1. Modifique `enem_parser.py` para suportar novo formato
2. Adicione validações em `enem_validator.py`
3. Teste com `pytest tests/test_parser.py`
4. Documente o novo formato aqui

## 📞 Suporte

Em caso de problemas:

1. Veja os logs (`-v` para verbose)
2. Teste com `exemplo_questoes_enem.json`
3. Verifique que Node.js e Prisma estão instalados
4. Abra uma issue no GitHub
