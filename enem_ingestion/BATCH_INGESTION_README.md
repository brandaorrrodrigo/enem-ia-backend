# 📚 Pipeline Massivo ENEM-IA

Sistema completo para gerar um dataset massivo de questões ENEM.

**Pipeline:** PDFs reais → Questões adaptadas → Questões simuladas → JSON MASSIVO → Banco de dados

---

## 📋 Overview

Este pipeline permite gerar até **17.000+ questões** ENEM:
- ✅ Questões **REAIS** extraídas de PDFs (2009-2024)
- ✅ **7.000 questões ADAPTADAS** geradas automaticamente
- ✅ **10.000 questões SIMULADAS** geradas automaticamente
- ✅ **Merge automático** em um único JSON
- ✅ **Deduplicação** inteligente
- ✅ **Seed do Prisma** pronto para uso

---

## 📂 Estrutura de Arquivos

```
backend/enem_ingestion/
├── pdfs_enem_real/                      ← Coloque seus PDFs ENEM aqui
│   ├── enem_2023_matematica.pdf
│   ├── enem_2022_linguagens.pdf
│   └── enem_2021_ciencias.pdf
│
├── ingest_real_questoes.py              ← [PASSO 1] Processa PDFs → JSON reais (NOVO!)
├── enem_parser_real.py                  ← Parser robusto para PDFs ENEM
├── enem_validator_relaxed.py            ← Validador relaxado para questões reais
├── gerar_questoes_adaptadas.py          ← [PASSO 2] Gera 7.000 adaptadas
├── gerar_questoes_sinteticas_10000.py   ← [PASSO 3] Gera 10.000 simuladas
├── merge_massivo.py                     ← [PASSO 4] Merge tudo em 1 JSON
│
├── real_enem_questoes.json              ← Output PASSO 1 (questões reais)
├── questoes_adaptadas_7000.json         ← Output PASSO 2 (adaptadas)
├── questoes_simuladas_10000.json        ← Output PASSO 3 (simuladas)
└── todas_questoes_enem_massivo.json     ← Output PASSO 4 (JSON MASSIVO FINAL)
```

---

## 🚀 PASSO A PASSO COMPLETO

Assumindo que você está em: `D:\enem-ia`

### PASSO 0: Instalar Dependências

```powershell
# Ir para pasta de ingestão
cd D:\enem-ia\backend\enem_ingestion

# Instalar biblioteca de PDF (escolha uma)
pip install PyPDF2          # Opção 1 (recomendado)
# ou
pip install pdfplumber      # Opção 2 (mais preciso)
# ou
pip install pypdf           # Opção 3 (leve)
```

### PASSO 1: Colocar PDFs e Processar Questões Reais

```powershell
# Colocar PDFs do ENEM na pasta
# Pasta: D:\enem-ia\backend\enem_ingestion\pdfs_enem_real\
# Exemplo: enem_2023_matematica.pdf, enem_2022_linguagens.pdf, etc.

# Processar todos os PDFs de uma vez usando o NOVO SCRIPT ROBUSTO
cd D:\enem-ia\backend\enem_ingestion
python ingest_real_questoes.py

# OU com logs detalhados de debug:
python ingest_real_questoes.py --debug

# OU com arquivo de saída customizado:
python ingest_real_questoes.py --output meu_arquivo.json
```

**Output:** `real_enem_questoes.json` (questões reais extraídas dos PDFs)

**⚠️ IMPORTANTE:** Use o novo script `ingest_real_questoes.py` ao invés do `batch_ingest.py` antigo!

**Melhorias do novo script:**
- ✅ Parser robusto que detecta múltiplos formatos de numeração
- ✅ Validador relaxado que aceita mais questões reais
- ✅ Ignora automaticamente PDFs de gabarito/apostilas
- ✅ Logs detalhados com motivos de descarte
- ✅ Extração multi-biblioteca (PyPDF2, pdfplumber, pypdf)
- ✅ Deduplicação inteligente

---

### PASSO 2: Gerar 7.000 Questões Adaptadas

```powershell
# Mesmo diretório
python gerar_questoes_adaptadas.py
```

**Output:** `questoes_adaptadas_7000.json`

Tempo estimado: ~2-5 minutos

---

### PASSO 3: Gerar 10.000 Questões Simuladas

```powershell
# Mesmo diretório
python gerar_questoes_sinteticas_10000.py
```

**Output:** `questoes_simuladas_10000.json`

Tempo estimado: ~3-8 minutos

---

### PASSO 4: Fazer Merge MASSIVO

```powershell
# Mesmo diretório
python merge_massivo.py
```

**Output:** `todas_questoes_enem_massivo.json` (JSON FINAL com TUDO)

Este arquivo contém:
- ✅ Todas as questões reais dos PDFs
- ✅ 7.000 questões adaptadas
- ✅ 10.000 questões simuladas
- ✅ Campo `tipo` em cada questão: "real", "adaptada" ou "simulada"
- ✅ Deduplicação automática

---

### PASSO 5: Seed do Banco Prisma

```powershell
# Ir para pasta do Next.js
cd D:\enem-ia\enem-pro

# Instalar dependências (se ainda não instalou)
npm install

# Aplicar migrations (se necessário)
npx prisma migrate deploy

# Rodar seed (vai detectar automaticamente o JSON MASSIVO)
npx prisma db seed
```

O seed vai:
- ✅ Detectar automaticamente `todas_questoes_enem_massivo.json`
- ✅ Inserir todas as questões no banco
- ✅ Pular duplicadas
- ✅ Mostrar estatísticas por tipo (real/adaptada/simulada)

**Expected output:**
```
================================================================================
🚀 BATCH ENEM INGESTION
================================================================================
📂 Pasta de PDFs: D:\enem-ia\backend\enem_ingestion\pdfs_enem
💾 Arquivo de saída: D:\enem-ia\backend\enem_ingestion\todas_questoes_enem.json
================================================================================

📚 Encontrados 3 PDFs

================================================================================
PROCESSANDO PDFs
================================================================================

[1/3] 📄 enem_2023_matematica.pdf
------------------------------------------------------------
   🔍 Extraindo texto do PDF...
   ✅ Extraído com PyPDF2 (45823 caracteres)
   📝 Parseando questões...
   ✅ 45 questões parseadas
   ✅ Validando questões...
   ✅ 43 questões válidas

[2/3] 📄 enem_2022_linguagens.pdf
------------------------------------------------------------
   🔍 Extraindo texto do PDF...
   ✅ Extraído com PyPDF2 (52341 caracteres)
   📝 Parseando questões...
   ✅ 50 questões parseadas
   ✅ Validando questões...
   ✅ 48 questões válidas

[3/3] 📄 enem_2021_ciencias.pdf
------------------------------------------------------------
   🔍 Extraindo texto do PDF...
   ✅ Extraído com PyPDF2 (48192 caracteres)
   📝 Parseando questões...
   ✅ 45 questões parseadas
   ✅ Validando questões...
   ✅ 44 questões válidas

================================================================================
DEDUPLICAÇÃO
================================================================================

🔍 Deduplicação:
   📝 Total de questões: 135
   ✅ Únicas: 130
   ⏭️  Duplicadas removidas: 5

================================================================================
SALVANDO JSON
================================================================================

✅ JSON salvo: todas_questoes_enem.json
   📦 Tamanho: 245.67 KB

================================================================================
📊 RESUMO FINAL
================================================================================
📚 PDFs encontrados: 3
✅ PDFs processados com sucesso: 3
❌ PDFs com erro: 0

📝 Questões parseadas: 140
✅ Questões válidas: 135
🔍 Questões únicas (após dedup): 130

💾 Arquivo de saída: todas_questoes_enem.json
================================================================================
✅ BATCH INGESTION CONCLUÍDO
================================================================================
```

### Step 4: Use the Generated JSON

The output file `todas_questoes_enem.json` can be used to:

1. **Seed the database:**
   ```bash
   cd ../../enem-pro
   # Update prisma/seed.ts to use todas_questoes_enem.json
   npx prisma db seed
   ```

2. **Import to Prisma directly:**
   ```bash
   cd backend/enem_ingestion
   python pipeline_completo.py todas_questoes_enem.json
   ```

3. **Analyze or edit manually:**
   - Open in a JSON editor
   - Review questions
   - Fix any issues

---

## ⚡ COMANDOS RÁPIDOS (copiar e colar)

Se você já tem tudo configurado:

```powershell
# Do zero ao banco cheio em 5 comandos
cd D:\enem-ia\backend\enem_ingestion

python ingest_real_questoes.py              # PASSO 1: PDFs → reais (NOVO SCRIPT!)
python gerar_questoes_adaptadas.py          # PASSO 2: gerar adaptadas
python gerar_questoes_sinteticas_10000.py   # PASSO 3: gerar simuladas
python merge_massivo.py                     # PASSO 4: merge massivo

cd D:\enem-ia\enem-pro
npx prisma db seed                          # PASSO 5: seed do banco
```

---

## 📋 NOMES DOS ARQUIVOS (referência)

| Tipo | Script | Output JSON |
|------|--------|-------------|
| **Reais** | `ingest_real_questoes.py` | `real_enem_questoes.json` |
| **Adaptadas** | `gerar_questoes_adaptadas.py` | `questoes_adaptadas_7000.json` |
| **Simuladas** | `gerar_questoes_sinteticas_10000.py` | `questoes_simuladas_10000.json` |
| **MASSIVO** | `merge_massivo.py` | `todas_questoes_enem_massivo.json` |

**JSON FINAL para o seed:** `todas_questoes_enem_massivo.json`

**Localização:** `D:\enem-ia\backend\enem_ingestion\todas_questoes_enem_massivo.json`

---

## 📊 ENTENDENDO OS LOGS

### Exemplo de Log de Sucesso

```
📄 Processando: enem_2023_matematica.pdf
------------------------------------------------------------
   🔍 Extraindo texto do PDF...
   ✅ PyPDF2: 45823 caracteres
   📅 Ano detectado: 2023
   📚 Disciplina inferida: matematica
   📝 Parseando questões...
   📊 Dividido em 45 blocos de questões
   ✅ 45 questões parseadas
   ✅ Validando questões...
   ✅ 43 questões VÁLIDAS
   ❌ 2 questões DESCARTADAS
```

**O que significa:**
- **45 parseadas**: Parser encontrou 45 blocos que parecem ser questões
- **43 válidas**: 43 questões passaram na validação (têm enunciado + 5 alternativas)
- **2 descartadas**: 2 questões não passaram na validação

### Por Que Questões São Descartadas?

Os motivos mais comuns são:

1. **Enunciado muito curto** (< 10 caracteres)
   - Exemplo: Apenas números ou fragmentos
   - Solução: Normal, ignorar esses casos

2. **Alternativas incompletas** (< 5 alternativas)
   - Exemplo: Parser detectou apenas A, B, C
   - Solução: Pode ser quebra de página ou formatação ruim no PDF

3. **Texto vazio**
   - Exemplo: Página em branco ou imagem sem texto
   - Solução: Normal para PDFs com gráficos/imagens

### Exemplo de Resumo Final

```
📊 RESUMO FINAL
================================================================================
📚 PDFs encontrados: 5
✅ PDFs processados: 4
⏭️  PDFs ignorados: 1  (gabarito_oficial.pdf)
❌ PDFs com erro: 0

📝 Questões parseadas: 198
✅ Questões válidas: 156
❌ Questões descartadas: 42
⏭️  Duplicatas removidas: 8
🎯 QUESTÕES ÚNICAS FINAIS: 148
```

**Interpretação:**
- **198 parseadas**: Parser encontrou 198 possíveis questões nos PDFs
- **156 válidas**: 156 passaram na validação
- **42 descartadas**: 42 foram rejeitadas (enunciado curto, alternativas faltando, etc.)
- **8 duplicatas**: 8 questões eram repetidas (detectadas por hash)
- **148 FINAIS**: Resultado final após todas as filtragens

### PDFs Ignorados Automaticamente

O script ignora PDFs que contêm no nome:
- `gabarito_oficial`
- `respostas`
- `instrucoes`
- `folha_resposta`
- `apostila`
- `resumo`
- `revisao`

**Isso é normal e esperado!**

---

## 📊 Formato do JSON MASSIVO

Cada questão no JSON MASSIVO tem este formato:

```json
{
  "numero": 145,
  "ano": 2024,
  "disciplina": "matematica",
  "enunciado": "Uma função quadrática f(x)...",
  "alternativas": {
    "A": "a = -1",
    "B": "a = 0",
    "C": "a = 1",
    "D": "a = 2",
    "E": "a = 3"
  },
  "correta": "C",
  "tipo": "real",           ← Campo IMPORTANTE: "real" | "adaptada" | "simulada"
  "habilidade": "H19",
  "competencia": 5,
  "explicacao": "Usando a forma de vértice...",
  "source": "real",
  "area": "matematica",
  "difficulty": 3
}
```

---

## 🔧 Advanced Usage

### Custom Output File

```bash
python batch_ingest.py --output meu_arquivo.json
```

### Custom Input Folder

```bash
python batch_ingest.py --input /path/to/my/pdfs
```

### Skip Validation (Allow Warnings)

```bash
python batch_ingest.py --skip-validation
```

This will accept questions even if they have validation warnings.

### Full Custom

```bash
python batch_ingest.py \
  --input /caminho/para/pdfs \
  --output /caminho/para/saida.json \
  --skip-validation
```

---

## 📊 Output JSON Format

The generated `todas_questoes_enem.json` has this structure:

```json
{
  "versao": "1.0",
  "total_questoes": 130,
  "gerado_em": "2025-11-14T15:30:00",
  "fonte": "Batch ingestion de PDFs",
  "questoes": [
    {
      "numero": 145,
      "ano": 2024,
      "disciplina": "matematica",
      "enunciado": "Uma função quadrática...",
      "alternativas": {
        "A": "a = -1",
        "B": "a = 0",
        "C": "a = 1",
        "D": "a = 2",
        "E": "a = 3"
      },
      "correta": "C",
      "habilidade": "H19",
      "competencia": 5,
      "explicacao": "Usando a forma de vértice..."
    }
  ],
  "estatisticas": {
    "pdfs_processados": 3,
    "pdfs_falhados": 0,
    "total_questoes_parseadas": 140,
    "total_questoes_validas": 135,
    "duplicadas_removidas": 5
  }
}
```

**Compatible with:**
- `pipeline_completo.py` (can import directly)
- `prisma/seed.ts` (just update the file path)
- Any JSON parser

---

## 🔍 Deduplication Logic

The script uses **three methods** to detect duplicates (in priority order):

### Method 1: Official ENEM Code
If questions have `numero` + `ano`:
```python
chave = f"{ano}-{numero}"  # Example: "2023-145"
```

### Method 2: Content Hash
If no official code, uses MD5 hash of:
```python
hash = MD5(enunciado + alternativa_A + alternativa_B + ... + alternativa_E)
```

### Method 3: First Win
If duplicate detected, **keeps the first occurrence** and skips subsequent ones.

**Example:**
```
PDF 1: Question 2023-145 → KEPT
PDF 2: Question 2023-145 → SKIPPED (duplicate)
PDF 3: Same enunciado/alternativas → SKIPPED (duplicate hash)
```

---

## 🐛 Error Handling

The batch script is **robust** and continues processing even if individual PDFs fail.

### Common Errors

**Error: "Nenhuma biblioteca de PDF disponível"**

Solution:
```bash
pip install PyPDF2
```

**Error: "PDF vazio ou texto insuficiente"**

Possible causes:
- PDF is scanned images (not text-based)
- PDF is encrypted/protected
- PDF has no extractable text

Solution:
- Use OCR tools first (Tesseract)
- Or manually convert to text

**Error: "Nenhuma questão parseada"**

Possible causes:
- PDF format doesn't match expected pattern
- Questions are in images, not text
- Text extraction failed

Solution:
- Check PDF manually
- Ensure questions follow ENEM format
- Check `enem_parser.py` regex patterns

**Error: "Todas as questões são inválidas"**

Possible causes:
- Missing alternativas (A-E)
- Missing gabarito (correta)
- Enunciado too short

Solution:
- Use `--skip-validation` to see warnings
- Check validation rules in `enem_validator.py`

### Skipping Failed PDFs

The script will:
1. Log the error
2. Add to `pdfs_com_erro` list
3. Continue with next PDF
4. Show summary at the end

**Example output:**
```
⚠️  PDFs com erro (2):
   • enem_corrupted.pdf: Texto vazio ou insuficiente
   • enem_invalid.pdf: Parsing: Nenhuma questão encontrada
```

---

## 🔄 Workflow Integration

### Full Pipeline: PDFs → Database

```bash
# Step 1: Batch process PDFs
cd backend/enem_ingestion
python batch_ingest.py

# Step 2: Import to Prisma (optional validation)
python pipeline_completo.py todas_questoes_enem.json --skip-import

# Step 3: Seed database
cd ../../enem-pro
# Edit prisma/seed.ts to add todas_questoes_enem.json
npx prisma db seed
```

### Incremental Updates

If you get new PDFs:

```bash
# Add new PDFs to pdfs_enem/
cp ~/Downloads/enem_2024.pdf backend/enem_ingestion/pdfs_enem/

# Re-run batch (it will merge old + new)
cd backend/enem_ingestion
python batch_ingest.py

# Deduplication will handle duplicates automatically
```

---

## 📈 Performance

**Processing time** (approximate):

| PDFs | Questions | Time |
|------|-----------|------|
| 1    | 45        | ~5s  |
| 10   | 450       | ~30s |
| 50   | 2,250     | ~2min|
| 100  | 4,500     | ~5min|

**Factors affecting speed:**
- PDF size and complexity
- Text extraction library used
- Number of questions per PDF
- Validation strictness

---

## 🧪 Testing

### Test with Example File

Use the existing example file to test:

```bash
cd backend/enem_ingestion

# Create test folder with example
mkdir -p pdfs_enem_test
cp exemplo_questoes_enem.json pdfs_enem_test/

# Note: This won't work because batch expects PDFs, not JSON
# But you can test the pipeline directly:
python pipeline_completo.py exemplo_questoes_enem.json --output teste.json
```

### Create Test PDF

To test PDF extraction:

1. Create a text file with ENEM questions
2. Convert to PDF (Word, LibreOffice, online tools)
3. Place in `pdfs_enem/`
4. Run batch script

**Minimal test content:**
```
Questão 1

Uma questão teste do ENEM.

A) Opção A
B) Opção B
C) Opção C
D) Opção D
E) Opção E

Gabarito: C
```

---

## 📚 Related Documentation

- **Single file pipeline:** `pipeline_completo.py`
- **Parser logic:** `enem_parser.py`
- **Validation rules:** `enem_validator.py`
- **Prisma import:** `import_to_prisma.py`
- **Database seeding:** `../../enem-pro/prisma/SEED_README.md`

---

## 🔮 Future Enhancements

### Planned Features

- [ ] **OCR support** for scanned PDFs (Tesseract integration)
- [ ] **Parallel processing** (process multiple PDFs concurrently)
- [ ] **Progress bar** (tqdm integration)
- [ ] **Resume capability** (skip already processed PDFs)
- [ ] **Direct Prisma import** (skip JSON intermediate step)
- [ ] **Web interface** (upload PDFs via browser)
- [ ] **Cloud storage** (S3, Google Drive integration)

### Contributing

To add new features:
1. Keep `pipeline_completo.py` unchanged (import and reuse)
2. Add new logic to `batch_ingest.py`
3. Update this README

---

## 🐛 Troubleshooting

### Erro: "Nenhum arquivo de questões encontrado"

Se o arquivo intermediário não foi gerado:

```powershell
# Verificar se o arquivo existe
cd D:\enem-ia\backend\enem_ingestion
dir todas_questoes_enem.json
dir questoes_adaptadas_7000.json
dir questoes_simuladas_10000.json

# Se algum estiver faltando, rode o script correspondente novamente
```

### Erro: "ModuleNotFoundError: No module named 'PyPDF2'"

```powershell
pip install PyPDF2
```

### Erro: "No module named 'pipeline_completo'"

Certifique-se de estar no diretório correto:

```powershell
cd D:\enem-ia\backend\enem_ingestion
```

### Seed falha: "Arquivo não encontrado"

Verifique o caminho:

```powershell
# O seed espera o JSON em:
D:\enem-ia\backend\enem_ingestion\todas_questoes_enem_massivo.json

# Confirmar que existe:
cd D:\enem-ia\backend\enem_ingestion
dir todas_questoes_enem_massivo.json
```

### Questões não aparecem no banco

```powershell
# Limpar banco e rodar seed novamente
cd D:\enem-ia\enem-pro

# Resetar banco (CUIDADO: apaga tudo!)
npx prisma migrate reset

# Rodar seed
npx prisma db seed
```

---

## ✅ CHECKLIST FINAL

Ao completar todos os passos, você deve ter:

- [x] `todas_questoes_enem.json` - Questões reais extraídas dos PDFs
- [x] `questoes_adaptadas_7000.json` - 7.000 questões adaptadas geradas
- [x] `questoes_simuladas_10000.json` - 10.000 questões simuladas geradas
- [x] `todas_questoes_enem_massivo.json` - JSON MASSIVO final (17.000+ questões)
- [x] Banco de dados Prisma populado com todas as questões
- [x] Estatísticas por tipo (real/adaptada/simulada) exibidas no seed

**Formato JSON unificado:**
- ✅ `numero`, `ano`, `disciplina`, `enunciado`, `alternativas`, `correta`
- ✅ Campo `tipo`: "real" | "adaptada" | "simulada"
- ✅ Campos opcionais: `habilidade`, `competencia`, `explicacao`, `source`, `area`, `difficulty`

**Nomes dos arquivos:**
- ✅ JSON Reais: `todas_questoes_enem.json`
- ✅ JSON Adaptadas: `questoes_adaptadas_7000.json`
- ✅ JSON Simuladas: `questoes_simuladas_10000.json`
- ✅ JSON MASSIVO: `todas_questoes_enem_massivo.json`

**Comandos prontos para rodar:**
```powershell
cd D:\enem-ia\backend\enem_ingestion
python ingest_real_questoes.py
python gerar_questoes_adaptadas.py
python gerar_questoes_sinteticas_10000.py
python merge_massivo.py
cd D:\enem-ia\enem-pro
npx prisma db seed
```

---

_Atualizado: 2025-11-14_
_Parte do projeto ENEM-IA_
_Pipeline Massivo: PDFs → Real + Adaptadas + Simuladas → Banco de Dados_
