# 🎓 Gerador de Questões ENEM com IA - Guia Completo

Sistema completo para gerar milhares de questões estilo ENEM usando Claude (Anthropic) e importar para o banco de dados do ENEM-IA.

---

## 📋 Índice

1. [Instalação](#instalação)
2. [Configuração](#configuração)
3. [Como Usar](#como-usar)
4. [Fluxo Completo](#fluxo-completo)
5. [Estrutura das Questões](#estrutura-das-questões)
6. [Troubleshooting](#troubleshooting)

---

## 📦 Instalação

### 1. Instalar dependências Python

```bash
cd D:\enem-ia\backend
pip install anthropic python-dotenv tqdm
```

### 2. Verificar Node.js (para importação)

O script de importação já usa as dependências do projeto `enem-pro`:

```bash
cd D:\enem-ia\enem-pro
npm install  # Se ainda não instalou
```

---

## ⚙️ Configuração

### 1. Obter API Key do Claude (Anthropic)

1. Acesse: https://console.anthropic.com/
2. Crie uma conta ou faça login
3. Vá em **API Keys** e crie uma nova chave
4. Copie a chave (começa com `sk-ant-...`)

### 2. Configurar variável de ambiente

**Opção A: Arquivo .env (recomendado)**

Crie um arquivo `.env` em `D:\enem-ia\backend`:

```env
ANTHROPIC_API_KEY=sk-ant-api03-sua-chave-aqui
```

**Opção B: Variável de ambiente do sistema**

Windows PowerShell:
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-sua-chave-aqui"
```

Windows CMD:
```cmd
set ANTHROPIC_API_KEY=sk-ant-api03-sua-chave-aqui
```

Linux/Mac:
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-sua-chave-aqui
```

---

## 🚀 Como Usar

### Passo 1: Configurar quantidade de questões

Edite o arquivo `generate_questions.py` nas últimas linhas:

```python
if __name__ == "__main__":
    QUESTOES_POR_LOTE = 10   # Questões por chamada à API
    TOTAL_DE_LOTES = 100     # Número de chamadas

    # TOTAL = 10 x 100 = 1000 questões
```

**Recomendações:**
- `QUESTOES_POR_LOTE`: 5-10 (mais questões = resposta mais lenta)
- `TOTAL_DE_LOTES`: quantas vezes você quer chamar a API
- Total de questões = `QUESTOES_POR_LOTE × TOTAL_DE_LOTES`

### Passo 2: Gerar questões

```bash
cd D:\enem-ia\backend
python generate_questions.py
```

O script irá:
1. ✅ Validar API key
2. 📊 Mostrar configuração (quantidade, arquivo de saída)
3. 🚀 Gerar questões em lotes
4. 💾 Salvar em `questoes_enem_ia.jsonl`
5. 📈 Mostrar estatísticas ao final

**Saída esperada:**
```
================================================================================
🎓 GERADOR DE QUESTÕES ENEM COM IA - CLAUDE ANTHROPIC
================================================================================

📋 Configuração:
   - Questões por lote: 10
   - Total de lotes: 100
   - Total de questões: 1000
   - Arquivo de saída: questoes_enem_ia.jsonl

🚀 Iniciando geração...

Progresso: 100%|██████████████████████████| 100/100 [15:30<00:00, 0.11it/s]

================================================================================
✅ GERAÇÃO CONCLUÍDA!
================================================================================
📊 Estatísticas:
   - Lotes processados: 100
   - Questões válidas geradas: 985
   - Taxa de sucesso: 98.5%
   - Arquivo salvo em: D:\enem-ia\backend\questoes_enem_ia.jsonl
```

### Passo 3: Importar para o banco de dados

```bash
cd D:\enem-ia\enem-pro
node scripts/import-questions-from-jsonl.mjs ../backend/questoes_enem_ia.jsonl
```

O script irá:
1. ✅ Validar todas as questões
2. 🔍 Verificar duplicatas (pelo enunciado)
3. 💾 Inserir questões no banco via Prisma
4. 📊 Mostrar relatório detalhado

**Saída esperada:**
```
================================================================================
📚 IMPORTADOR DE QUESTÕES JSONL PARA BANCO DE DADOS
================================================================================

📂 Arquivo: D:\enem-ia\backend\questoes_enem_ia.jsonl

📊 Total de linhas no arquivo: 985

✅ Questões válidas: 985
⚠️  Questões com erro: 0

🔄 Preparando para importar 985 questões...

📦 Processando lote 1/20 (50 questões)...
   ✅ Importada: Matemática - Função afim
   ✅ Importada: Física - Cinemática
   ...

================================================================================
✅ IMPORTAÇÃO CONCLUÍDA
================================================================================

📊 Estatísticas:
   - Total de questões no arquivo: 985
   - Questões válidas: 985
   - Questões importadas: 985
   - Questões duplicadas (puladas): 0
   - Questões com erro: 0

📚 Total de questões agora no banco: 11285
```

---

## 🔄 Fluxo Completo (Resumo)

```mermaid
graph LR
    A[1. Configurar API Key] --> B[2. Editar quantidade]
    B --> C[3. Gerar questões]
    C --> D[4. Arquivo JSONL criado]
    D --> E[5. Importar para banco]
    E --> F[6. Questões disponíveis no app]
```

**Comandos resumidos:**
```bash
# 1. Gerar questões
cd D:\enem-ia\backend
python generate_questions.py

# 2. Importar para banco
cd D:\enem-ia\enem-pro
node scripts/import-questions-from-jsonl.mjs ../backend/questoes_enem_ia.jsonl
```

---

## 📝 Estrutura das Questões

### Formato JSONL (arquivo gerado)

Cada linha do arquivo é um JSON válido:

```json
{"area":"Matemática","disciplina":"Matemática","assunto":"Função quadrática","dificuldade":"média","enunciado":"Uma empresa de taxi cobra uma taxa fixa de R$ 5,00 mais R$ 2,50 por quilômetro rodado. Qual é o custo de uma corrida de 8 km?","texto_apoio":"","alternativas":{"A":"R$ 20,00","B":"R$ 25,00","C":"R$ 30,00","D":"R$ 35,00","E":"R$ 40,00"},"correta":"B","explicacao":"Custo = taxa fixa + (preço por km × distância). Custo = 5 + (2,50 × 8) = 5 + 20 = 25 reais.","fonte":"IA_ENEMIA","ano_referencia":null}
```

### Formato no Banco de Dados (Prisma)

Após importação, as questões ficam assim na tabela `Questao`:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Int | ID auto-incremento |
| `area` | String | Matemática, Ciências Humanas, etc |
| `disciplina` | String | Matemática, Física, História, etc |
| `assunto` | String | Função afim, Cinemática, etc |
| `dificuldade` | String | fácil, média, difícil |
| `enunciado` | String (Text) | Pergunta completa |
| `textoApoio` | String (Text) | Texto de contexto (opcional) |
| `alternativas` | String (JSON) | Array: ["alternativa A", "B", "C", "D", "E"] |
| `correta` | Int | 0-4 (A=0, B=1, C=2, D=3, E=4) |
| `explicacao` | String (Text) | Explicação detalhada |
| `fonte` | String | "IA_ENEMIA" |
| `anoReferencia` | Int? | null para questões geradas por IA |

---

## 🎯 Diversidade e Qualidade

### O que o gerador faz automaticamente:

1. **Sorteia aleatoriamente** para cada questão:
   - Área de conhecimento
   - Disciplina compatível com a área
   - Assunto da lista pré-definida
   - Nível de dificuldade

2. **Taxonomia completa**:
   - 4 áreas: Matemática, Ciências Humanas, Ciências da Natureza, Linguagens
   - 11 disciplinas: Matemática, Física, Química, Biologia, História, Geografia, Sociologia, Filosofia, Português, Inglês, Artes
   - 150+ assuntos distribuídos entre as disciplinas

3. **Qualidade ENEM**:
   - Texto de apoio contextualizado
   - Situações do cotidiano
   - Português formal
   - 5 alternativas plausíveis
   - Explicação pedagógica detalhada

---

## 🐛 Troubleshooting

### Erro: "ANTHROPIC_API_KEY não encontrada"

**Solução:**
1. Verifique se criou o arquivo `.env` em `D:\enem-ia\backend`
2. Verifique se a chave está correta (começa com `sk-ant-`)
3. Tente exportar como variável de ambiente temporária

### Erro: "Rate limit atingido"

**Solução:**
- A API do Claude tem limite de requisições por minuto
- O script tem retry automático com delay progressivo
- Se persistir, aguarde alguns minutos ou reduza `QUESTOES_POR_LOTE`

### Erro: "Questão inválida ignorada"

**Solução:**
- Algumas questões geradas pela IA podem vir malformadas
- O script já ignora automaticamente e continua
- A taxa de sucesso normal é 95-100%

### Erro ao importar: "JSON inválido"

**Solução:**
1. Abra o arquivo `questoes_enem_ia.jsonl` em um editor
2. Verifique se há linhas vazias ou texto extra
3. Cada linha deve ser um JSON válido e completo
4. Use um validador JSON online se necessário

### Questões duplicadas

**Solução:**
- O importador detecta automaticamente pelo enunciado
- Questões duplicadas são puladas com mensagem `⏭️  Questão já existe`
- Não há problema em rodar o importador múltiplas vezes

---

## 💡 Dicas e Boas Práticas

### 1. Comece com um teste pequeno

Antes de gerar milhares de questões, teste com:
```python
QUESTOES_POR_LOTE = 5
TOTAL_DE_LOTES = 2  # = 10 questões apenas
```

### 2. Gere em etapas

Em vez de gerar 10.000 de uma vez:
- Gere 1.000 por dia
- Revise a qualidade periodicamente
- Ajuste o prompt se necessário

### 3. Monitore custos da API

- Claude cobra por tokens (entrada + saída)
- ~1000 questões = ~$2-5 USD (aproximado)
- Confira seu saldo em: https://console.anthropic.com/

### 4. Backup do arquivo JSONL

```bash
cp questoes_enem_ia.jsonl questoes_enem_ia_backup_$(date +%Y%m%d).jsonl
```

### 5. Versionamento

Se quiser gerar questões de um assunto específico, edite a função `get_random_subject()` para fixar área/disciplina.

---

## 📊 Métricas Esperadas

Com configuração padrão (`QUESTOES_POR_LOTE=10`, `TOTAL_DE_LOTES=100`):

| Métrica | Valor |
|---------|-------|
| Tempo total | ~15-20 minutos |
| Questões geradas | 950-1000 |
| Taxa de sucesso | 95-100% |
| Tamanho do arquivo | ~2-3 MB |
| Custo API (aprox.) | $2-4 USD |

---

## 🔧 Personalização Avançada

### Modificar áreas/disciplinas/assuntos

Edite o dicionário `TAXONOMIA` em `generate_questions.py`:

```python
TAXONOMIA = {
    "Matemática": {
        "disciplina": "Matemática",
        "assuntos": [
            "Novo assunto aqui",
            # ...
        ]
    },
    # ...
}
```

### Mudar modelo do Claude

Edite a linha em `generate_questions_batch()`:

```python
model="claude-3-5-sonnet-20241022",  # Modelo atual
# Opções: claude-3-opus-20240229, claude-3-haiku-20240307
```

### Ajustar temperatura

Mais criativo = temperatura maior:

```python
temperature=1.0,  # 0.0 = mais determinístico, 2.0 = mais criativo
```

---

## 📞 Suporte

Se encontrar problemas:

1. ✅ Confira este README novamente
2. 🔍 Veja os logs de erro detalhados
3. 📝 Verifique se a API key está correta
4. 💬 Consulte a documentação do Claude: https://docs.anthropic.com/

---

**Sistema de Geração de Questões ENEM-IA v1.0**
Powered by Claude (Anthropic) 🚀
