# 📋 Sessão 3 - APIs de Simulados ENEM - Resumo Completo

## ✅ Objetivos Concluídos

- [x] Localizado backend FastAPI existente
- [x] Verificado schema Prisma
- [x] Estendido schema com modelos necessários
- [x] Criada estrutura de routers
- [x] Criado router completo de simulados ENEM
- [x] Criado main.py unificado
- [x] Documentação completa com exemplos frontend

---

## 📦 Arquivos Criados/Modificados

### 1. Schema Prisma (Estendido)

**Arquivo:** `enem-pro/prisma/schema.prisma`

**Models Adicionados:**
- ✅ `Usuario` - Usuários do sistema
- ✅ `UsuarioSimulado` - Simulados realizados por usuário
- ✅ `UsuarioResposta` - Respostas individuais
- ✅ `NotaCorte` - Notas de corte de cursos

**Models Existentes (Mantidos):**
- ✅ `Questao` - Questões do ENEM
- ✅ `Simulado` - Simulados base
- ✅ `SimuladoQuestao` - Tabela pivô

### 2. Estrutura de Routers

```
backend/
├── routers/
│   ├── __init__.py          ✅ Criado
│   └── enem_simulados.py    ✅ Criado (850+ linhas)
├── main.py                  ✅ Criado (app FastAPI unificado)
├── API_SIMULADOS_GUIA.md    ✅ Criado (documentação completa)
└── SESSAO3_RESUMO.md        ✅ Este arquivo
```

### 3. Router de Simulados ENEM

**Arquivo:** `backend/routers/enem_simulados.py`

**Endpoints Implementados:**

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/enem/simulados/start` | Inicia novo simulado |
| POST | `/api/enem/simulados/answer` | Responde questão |
| POST | `/api/enem/simulados/finish` | Finaliza e calcula nota |
| GET  | `/api/enem/simulados/history` | Histórico do usuário |
| POST | `/api/enem/simulados/compare-score` | Compara com nota de corte |
| GET  | `/api/enem/simulados/` | Info da API |

**Funcionalidades:**
- ✅ Integração com Prisma via subprocess Node.js
- ✅ Seleção de questões por disciplina
- ✅ Salvamento de respostas individuais
- ✅ Cálculo de nota TRI (0-1000)
- ✅ Classificação de desempenho
- ✅ Detalhamento de erros
- ✅ Comparação com notas de corte
- ✅ Logs detalhados

### 4. Main.py Unificado

**Arquivo:** `backend/main.py`

**Integração:**
- ✅ Router de Simulados incluído
- ✅ CORS configurado
- ✅ Documentação Swagger em `/docs`
- ✅ Health check em `/health`
- ✅ Logging estruturado

**Preparado para incluir:**
- ⏳ Explicação API (futuro)
- ⏳ Reexplicar API (futuro)
- ⏳ Resultados API (futuro)

---

## 🚀 Como Usar

### Passo 1: Aplicar Migration Prisma

```bash
cd enem-pro

# Criar migration para novos models
npx prisma migrate dev --name add_simulado_models

# Gerar Prisma Client atualizado
npx prisma generate
```

### Passo 2: Iniciar Backend

```bash
cd backend

# Iniciar servidor FastAPI
python main.py

# OU
uvicorn main:app --reload --port 8000
```

### Passo 3: Testar API

Acesse: `http://localhost:8000/docs`

Ou teste manualmente:

```bash
# 1. Iniciar simulado
curl -X POST http://localhost:8000/api/enem/simulados/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test@example.com",
    "quantidade": 5
  }'

# Resposta: { "simulado_id": "clx...", "questoes": [...] }

# 2. Responder questão
curl -X POST http://localhost:8000/api/enem/simulados/answer \
  -H "Content-Type": application/json" \
  -d '{
    "user_id": "test@example.com",
    "simulado_id": "clx...",
    "questao_id": 15,
    "alternativa_marcada": 2
  }'

# 3. Finalizar
curl -X POST http://localhost:8000/api/enem/simulados/finish \
  -H "Content-Type": application/json" \
  -d '{
    "user_id": "test@example.com",
    "simulado_id": "clx..."
  }'

# Resposta: { "nota": 790.0, "acertos": 7, "total": 10, ... }
```

---

## 📚 Documentação

### Para Desenvolvedores Backend

- **`backend/routers/enem_simulados.py`** - Código fonte com docstrings
- **`backend/API_SIMULADOS_GUIA.md`** - Guia completo da API

### Para Desenvolvedores Frontend

**Todos os endpoints têm exemplos de uso em JavaScript/TypeScript no guia:**

```javascript
// Exemplo: Iniciar simulado
const response = await fetch('/api/enem/simulados/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user@example.com',
    area: 'matematica',
    quantidade: 10
  })
});

const data = await response.json();
// data.simulado_id - use para responder questões
// data.questoes - array de questões
```

Veja `API_SIMULADOS_GUIA.md` para exemplos completos de:
- ✅ Componentes React
- ✅ Páginas Next.js
- ✅ Hooks personalizados
- ✅ Tratamento de erros
- ✅ Conversão letra ↔ índice

---

## 🔄 Fluxo Completo

```
┌─────────────────────────────────────────────────────────────┐
│                   FLUXO DE UM SIMULADO                      │
└─────────────────────────────────────────────────────────────┘

1. Frontend: POST /api/enem/simulados/start
   └─> Backend: Cria Simulado + UsuarioSimulado
       └─> Prisma: INSERT INTO Simulado, UsuarioSimulado
           └─> Backend: Retorna questões

2. Usuário responde questões (loop)
   └─> Frontend: POST /api/enem/simulados/answer (para cada questão)
       └─> Backend: Salva resposta
           └─> Prisma: INSERT/UPDATE UsuarioResposta

3. Frontend: POST /api/enem/simulados/finish
   └─> Backend: Busca respostas + gabaritos
       └─> Backend: Calcula nota TRI
           └─> Prisma: UPDATE UsuarioSimulado (status=finalizado, nota)
               └─> Backend: Retorna resultado detalhado

4. (Opcional) Frontend: POST /api/enem/simulados/compare-score
   └─> Backend: Busca nota do simulado
       └─> Backend: Busca nota de corte do curso
           └─> Backend: Compara e retorna resultado
```

---

## 📊 Modelos de Dados

### Request/Response (Pydantic)

```python
# StartSimuladoRequest
{
  "user_id": str,
  "area": str | None,
  "quantidade": int (1-180)
}

# StartSimuladoResponse
{
  "simulado_id": str,
  "usuario_simulado_id": str,
  "quantidade": int,
  "disciplina": str | None,
  "questoes": [
    {
      "id": int,
      "enunciado": str,
      "alternativas": [str]  # 5 alternativas
    }
  ]
}

# AnswerRequest
{
  "user_id": str,
  "simulado_id": str,
  "questao_id": int,
  "alternativa_marcada": int | None  # 0-4
}

# FinishResponse
{
  "ok": bool,
  "usuario_simulado_id": str,
  "acertos": int,
  "erros": int,
  "total": int,
  "porcentagem": float,
  "nota": float,  # 0-1000
  "desempenho": str,  # "🏆 Excelente", "👍 Bom", etc
  "erros_detalhados": [
    {
      "questao_id": int,
      "enunciado": str,
      "alternativas": [str],
      "correta": int,
      "marcada": int | None
    }
  ]
}
```

---

## 🎯 Funcionalidades Implementadas

### ✅ Simulados
- [x] Criar simulado com N questões
- [x] Filtrar por disciplina/área
- [x] Responder questões individualmente
- [x] Atualizar respostas (permite mudança)
- [x] Finalizar e calcular nota
- [x] Nota TRI simplificada (0-1000)
- [x] Classificação de desempenho
- [x] Lista de erros detalhados
- [x] Histórico de simulados por usuário
- [x] Comparação com nota de corte

### ✅ Integrações
- [x] Prisma via subprocess Node.js
- [x] Banco SQLite (dev)
- [x] CORS configurado
- [x] Logs estruturados
- [x] Tratamento de erros robusto
- [x] Validação de entrada (Pydantic)

### ✅ Documentação
- [x] Swagger/OpenAPI em `/docs`
- [x] Docstrings em todas as funções
- [x] Guia completo para frontend
- [x] Exemplos de código
- [x] Diagramas de fluxo

---

## 🔧 Tecnologias Utilizadas

- **FastAPI** - Framework web Python
- **Pydantic** - Validação de dados
- **Prisma** - ORM (via Node.js)
- **SQLite** - Banco de dados (dev)
- **subprocess** - Execução de scripts Node.js
- **uvicorn** - Servidor ASGI

---

## ⚠️ Notas Importantes

### Conversão Alternativas

**Frontend usa letras (A-E), backend usa índices (0-4):**

```javascript
// Letra → Índice
const indice = letra.charCodeAt(0) - 65;  // 'A' → 0

// Índice → Letra
const letra = String.fromCharCode(65 + indice);  // 0 → 'A'
```

### Nota TRI Simplificada

Fórmula atual (básica):
```python
nota_base = 300
nota_por_acerto = 700 / total
nota = nota_base + (acertos * nota_por_acerto)
```

**Resultado:** 300-1000 pontos

**Nota:** Para TRI real do ENEM, considerar implementar modelo mais complexo no futuro.

### Arquivo Requirements

```bash
# backend/requirements.txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
```

---

## 🐛 Troubleshooting

### Erro: "Projeto Prisma não encontrado"

```python
# Em enem_simulados.py, linha 27
PRISMA_PROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "enem-pro"

# Se estrutura for diferente, ajuste o caminho
```

### Erro: Migration necessária

```bash
cd enem-pro
npx prisma migrate dev --name add_simulado_models
npx prisma generate
```

### Erro: "node command not found"

```bash
# Instale Node.js v18+
node --version
npm --version
```

### Erro: CORS

Se frontend não conseguir acessar API:

```python
# Em main.py, ajuste allow_origins
allow_origins=[
    "http://localhost:3000",  # Next.js
    "https://seu-frontend.vercel.app"
]
```

---

## 📈 Próximos Passos Sugeridos

### Curto Prazo
- [ ] Adicionar autenticação (JWT)
- [ ] Implementar rate limiting
- [ ] Cache de questões (Redis)
- [ ] Logs para arquivo
- [ ] Testes unitários (pytest)

### Médio Prazo
- [ ] Seleção aleatória real de questões
- [ ] Filtros avançados (ano, dificuldade, habilidade)
- [ ] Sistema de tags
- [ ] Exportar resultado em PDF
- [ ] Gamificação (XP, conquistas)

### Longo Prazo
- [ ] TRI real do ENEM (implementação completa)
- [ ] Machine Learning para recomendação
- [ ] Analytics de desempenho
- [ ] Integração com dados reais do INEP
- [ ] Sistema de revisão espaçada

---

## 🎉 Conclusão

✅ **API de Simulados ENEM completa e funcional!**

**5 endpoints implementados:**
- ✅ POST /start
- ✅ POST /answer
- ✅ POST /finish
- ✅ GET /history
- ✅ POST /compare-score

**Funcionalidades principais:**
- ✅ Criar simulados personalizados
- ✅ Responder questões
- ✅ Calcular nota TRI
- ✅ Histórico de simulados
- ✅ Comparar com nota de corte

**Documentação:**
- ✅ Swagger/OpenAPI
- ✅ Guia completo para frontend
- ✅ Exemplos de código
- ✅ Diagramas de fluxo

**Pronto para integração com frontend Next.js!**

---

_Documento gerado em: 2025-11-13_
_Sessão 3: APIs de Simulados ENEM - Completa_
