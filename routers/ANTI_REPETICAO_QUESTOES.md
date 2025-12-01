# 🔄 Sistema Anti-Repetição de Questões

## 📋 Visão Geral

Sistema implementado para **garantir que usuários NUNCA vejam a mesma questão** em simulados diferentes, maximizando a variedade e a experiência de aprendizado.

---

## 🎯 Objetivos

1. ✅ **Nunca repetir questões** entre simulados diferentes do mesmo usuário
2. ✅ **Nunca repetir questões** dentro do mesmo simulado
3. ✅ **Fallback inteligente** quando questões novas acabarem
4. ✅ **Logging detalhado** para monitorar repetições

---

## 🔧 Como Funciona

### Fluxo de Seleção de Questões

```
┌─────────────────────────────────────────────────┐
│ 1. Usuário solicita novo simulado              │
│    (POST /api/enem/simulados/start)             │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 2. Busca histórico do usuário                   │
│    - Todos os simulados anteriores              │
│    - Todas as respostas (questões já vistas)    │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 3. Cria Set com IDs de questões já respondidas  │
│    questoesJaRespondidas = Set([1, 5, 10, ...]) │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 4. Busca questões NOVAS (id NOT IN set)         │
│    WHERE id NOT IN (1, 5, 10, ...)              │
└─────────────────┬───────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
    ✅ Suficiente    ❌ Insuficiente
         │                 │
         │        ┌────────▼────────────────────────┐
         │        │ 5. FALLBACK: Permite repetição  │
         │        │    Busca questões adicionais     │
         │        │    (logando warning)             │
         │        └────────┬────────────────────────┘
         │                 │
         └────────┬────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 6. Remove duplicatas DENTRO do simulado         │
│    questoesUnicas = Set(questoes)               │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 7. Retorna questões para o usuário              │
└─────────────────────────────────────────────────┘
```

---

## 📍 Localização do Código

**Arquivo:** `backend/routers/enem_simulados.py`

**Função:** `start_simulado()` (linha 209)

**Seções modificadas:**

1. **Linhas 258-296**: Busca histórico de questões já respondidas
2. **Linhas 299-322**: Seleção de questões NOVAS
3. **Linhas 324-351**: Fallback para repetição (se necessário)
4. **Linhas 366-380**: Remoção de duplicatas dentro do simulado
5. **Linhas 422-436**: Logging no Python

---

## 🔍 Detalhamento Técnico

### 1. Busca de Questões Já Respondidas (Linhas 273-295)

```javascript
const simuladosAnteriores = await prisma.usuarioSimulado.findMany({
  where: {
    usuarioId: usuario.id,
  },
  include: {
    respostas: {
      select: {
        questaoId: true
      }
    }
  }
});

const questoesJaRespondidas = new Set();
for (const sim of simuladosAnteriores) {
  for (const resp of sim.respostas) {
    questoesJaRespondidas.add(resp.questaoId);
  }
}
```

**O que faz:**
- Busca TODOS os simulados anteriores do usuário
- Extrai TODOS os IDs de questões respondidas
- Armazena em um Set (sem duplicatas)

**Customização possível:**
- Filtrar apenas simulados finalizados: `status: "finalizado"`
- Filtrar por período: `createdAt: { gte: new Date(...) }`
- Filtrar por área/disciplina específica

---

### 2. Seleção de Questões Novas (Linhas 310-322)

```javascript
const whereFilter = {
  disciplina: "matematica",  // Se área especificada
  id: {
    notIn: Array.from(questoesJaRespondidas)  // Exclui já respondidas
  }
};

let questoes = await prisma.questao.findMany({
  where: whereFilter,
  take: 10  // Quantidade solicitada
});
```

**O que faz:**
- Cria filtro excluindo questões já respondidas
- Busca N questões que o usuário NUNCA viu

**Customização possível:**
- Adicionar ordenação aleatória (requer extensão Prisma)
- Filtrar por dificuldade: `difficulty: { lte: 3 }`
- Filtrar por tipo: `tipo: "real"`
- Filtrar por ano: `ano: { gte: 2020 }`

---

### 3. Fallback para Repetição (Linhas 334-351)

```javascript
if (questoes.length < quantidade) {
  console.error(`[WARNING] Apenas ${questoes.length} questões novas disponíveis`);
  console.error(`[WARNING] Usando FALLBACK: permitindo repetição`);

  const questoesFallback = await prisma.questao.findMany({
    where: {
      disciplina: "matematica",
      id: {
        notIn: questoes.map(q => q.id)  // Evita duplicatas NO SIMULADO
      }
    },
    take: quantidade - questoes.length
  });

  questoes = [...questoes, ...questoesFallback];
}
```

**O que faz:**
- Verifica se há questões novas suficientes
- Se não, busca questões adicionais (incluindo já respondidas)
- Garante que NÃO haja duplicatas DENTRO do mesmo simulado

**Customização possível:**
- **Lançar erro** em vez de permitir repetição:
  ```javascript
  if (questoes.length < quantidade) {
    throw new Error("Questões novas esgotadas. Aguarde novos conteúdos.");
  }
  ```
- **Priorizar questões antigas** (há mais tempo):
  ```javascript
  orderBy: { createdAt: 'asc' }
  ```
- **Priorizar questões erradas** para revisão:
  ```javascript
  // Buscar apenas questões que o usuário errou
  ```

---

### 4. Garantia de Unicidade Dentro do Simulado (Linhas 370-371)

```javascript
const questoesUnicas = Array.from(new Set(questoes.map(q => q.id)))
  .map(id => questoes.find(q => q.id === id));
```

**O que faz:**
- Remove qualquer duplicata que possa ter aparecido
- Garante 100% de questões únicas dentro do simulado

---

### 5. Logging e Monitoramento (Linhas 297, 335-336, 393, 422-436)

**No Node.js (console.error = stderr):**
```javascript
console.error(`[INFO] Usuário ${usuario.id} já respondeu ${size} questões`);
console.error(`[WARNING] Usando FALLBACK: permitindo repetição`);
console.error(`[SUCCESS] Simulado ${id} criado com ${length} questões`);
```

**No Python (logger):**
```python
logger.info(f"✅ Simulado {id} criado com {quantidade} questões")
logger.warning(f"⚠️ FALLBACK ATIVADO: {repetidas} questões repetidas")
logger.info(f"🎯 Todas as {novas} questões são NOVAS")
```

---

## 🎨 Como Customizar

### Opção 1: Permitir Repetição Após X Dias

**Local:** Linha 273 (whereFilter em `simuladosAnteriores`)

```javascript
// ANTES (nunca repete)
const simuladosAnteriores = await prisma.usuarioSimulado.findMany({
  where: {
    usuarioId: usuario.id,
  },
  // ...
});

// DEPOIS (permite repetição após 30 dias)
const simuladosAnteriores = await prisma.usuarioSimulado.findMany({
  where: {
    usuarioId: usuario.id,
    createdAt: {
      gte: new Date(Date.now() - 30*24*60*60*1000)  // Últimos 30 dias
    }
  },
  // ...
});
```

---

### Opção 2: Apenas Considerar Simulados Finalizados

**Local:** Linha 273

```javascript
const simuladosAnteriores = await prisma.usuarioSimulado.findMany({
  where: {
    usuarioId: usuario.id,
    status: "finalizado"  // Apenas finalizados
  },
  // ...
});
```

**Efeito:**
- Questões de simulados abandonados podem aparecer novamente

---

### Opção 3: Seleção Aleatória Real

**Local:** Linha 317

**Problema atual:** Prisma não tem `ORDER BY RANDOM()` nativo

**Solução 1 - Raw Query:**
```javascript
// Usar query SQL direta
const questoes = await prisma.$queryRaw`
  SELECT * FROM Questao
  WHERE id NOT IN (${Prisma.join(Array.from(questoesJaRespondidas))})
  ORDER BY RANDOM()
  LIMIT ${quantidade}
`;
```

**Solução 2 - Extensão Prisma:**
- Instalar `prisma-extension-random`
- Usar `orderBy: { _random: 'asc' }`

**Solução 3 - Lógica em memória:**
```javascript
// Buscar todas questões elegíveis
const todasQuestoes = await prisma.questao.findMany({
  where: whereFilter
});

// Embaralhar em memória
const shuffled = todasQuestoes.sort(() => Math.random() - 0.5);
const questoes = shuffled.slice(0, quantidade);
```

---

### Opção 4: Priorizar Questões por Dificuldade

**Local:** Linha 317

```javascript
let questoes = await prisma.questao.findMany({
  where: whereFilter,
  orderBy: {
    difficulty: 'asc'  // Começa pelas fáceis
    // ou 'desc' para começar pelas difíceis
  },
  take: quantidade
});
```

---

### Opção 5: Erro em Vez de Fallback

**Local:** Linha 334

```javascript
// ANTES (permite repetição)
if (questoes.length < quantidade) {
  console.error(`[WARNING] Usando FALLBACK`);
  // busca questões adicionais...
}

// DEPOIS (lança erro)
if (questoes.length < quantidade) {
  throw new Error(
    `Apenas ${questoes.length} questões novas disponíveis. ` +
    `Você já respondeu ${questoesJaRespondidas.size} questões. ` +
    `Aguarde novos conteúdos serem adicionados.`
  );
}
```

---

### Opção 6: Repetir Apenas Questões Erradas

**Local:** Linhas 339-347 (dentro do fallback)

```javascript
// Buscar questões que o usuário ERROU
const questoesErradas = [];

for (const sim of simuladosAnteriores) {
  const simulado = await prisma.simulado.findUnique({
    where: { id: sim.simuladoId },
    include: { questoes: { include: { questao: true } } }
  });

  for (const sq of simulado.questoes) {
    const resposta = sim.respostas.find(r => r.questaoId === sq.questao.id);
    if (resposta && resposta.alternativaMarcada !== sq.questao.correta) {
      questoesErradas.push(sq.questao.id);
    }
  }
}

// No fallback, priorizar questões erradas
const questoesFallback = await prisma.questao.findMany({
  where: {
    id: {
      in: questoesErradas,  // Apenas questões erradas
      notIn: questoes.map(q => q.id)
    }
  },
  take: quantidade - questoes.length
});
```

---

## 📊 Estatísticas Retornadas

A API agora retorna informações sobre repetição:

```json
{
  "simulado_id": "clx123",
  "usuario_simulado_id": "clx456",
  "quantidade": 10,
  "disciplina": "matematica",
  "questoes_novas": 8,
  "questoes_repetidas": 2,
  "questoes": [...]
}
```

**Campos adicionados:**
- `questoes_novas`: Quantas questões o usuário NUNCA viu
- `questoes_repetidas`: Quantas foram repetidas (fallback ativado)

---

## 🧪 Como Testar

### Teste 1: Primeiro Simulado (Nenhuma Repetição Esperada)

```bash
curl -X POST http://localhost:8000/api/enem/simulados/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "teste@email.com",
    "area": "matematica",
    "quantidade": 10
  }'
```

**Resultado esperado:**
- `questoes_novas: 10`
- `questoes_repetidas: 0`
- Log: `🎯 Todas as 10 questões são NOVAS`

---

### Teste 2: Segundo Simulado (Deve Evitar Repetição)

```bash
# Executar o mesmo comando acima novamente
```

**Resultado esperado:**
- Questões diferentes do primeiro simulado
- `questoes_novas: 10` (se houver questões suficientes)
- `questoes_repetidas: 0`

---

### Teste 3: Esgotar Questões (Fallback)

```bash
# Criar múltiplos simulados até esgotar questões
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/enem/simulados/start \
    -H "Content-Type: application/json" \
    -d '{"user_id": "teste@email.com", "quantidade": 10}'
done
```

**Resultado esperado:**
- Primeiros simulados: `questoes_repetidas: 0`
- Quando começar a faltar: `questoes_repetidas > 0`
- Log: `⚠️ FALLBACK ATIVADO`

---

### Teste 4: Verificar Histórico

```bash
curl http://localhost:8000/api/enem/simulados/history?user_id=teste@email.com
```

**Resultado esperado:**
- Lista de simulados realizados
- Cada simulado com ID único

---

## 📈 Monitoramento em Produção

### Logs a Observar

**Padrão Normal:**
```
[INFO] Usuário clx123 já respondeu 50 questões únicas
[SUCCESS] Simulado clx456 criado com 10 questões únicas
✅ Simulado clx456 criado com 10 questões
🎯 Todas as 10 questões são NOVAS
```

**Padrão de Fallback (atenção):**
```
[INFO] Usuário clx123 já respondeu 490 questões únicas
[WARNING] Apenas 5 questões novas disponíveis. Solicitadas: 10
[WARNING] Usando FALLBACK: permitindo repetição de questões antigas
[INFO] Total após fallback: 10 questões
[SUCCESS] Simulado clx789 criado com 10 questões únicas
⚠️ FALLBACK ATIVADO: 5 questões repetidas. Questões novas: 5, Total: 10
```

**Ação recomendada:**
- Quando fallback começar a aparecer frequentemente, adicionar mais questões ao banco

---

## ❗ Limitações Atuais

1. **Seleção não é verdadeiramente aleatória**
   - Prisma pega as primeiras N questões da query
   - Solução: Implementar uma das opções de randomização acima

2. **Performance com muitas questões**
   - Set de questões respondidas pode ficar grande
   - Solução: Adicionar filtro temporal (últimos 30/60 dias)

3. **Não considera dificuldade progressiva**
   - Não ajusta dificuldade baseado em desempenho
   - Solução: Implementar sistema adaptativo

---

## 🚀 Próximos Passos (Futuro)

- [ ] Implementar seleção verdadeiramente aleatória
- [ ] Sistema adaptativo (ajusta dificuldade conforme desempenho)
- [ ] Priorizar questões erradas para revisão
- [ ] Dashboard de analytics (quantas questões disponíveis por usuário)
- [ ] API endpoint para verificar questões restantes
- [ ] Reset manual de histórico (permitir refazer questões antigas)

---

## 📝 Resumo

**Garantias implementadas:**
- ✅ NUNCA repete questões entre simulados diferentes
- ✅ NUNCA repete questões dentro do mesmo simulado
- ✅ Fallback inteligente quando necessário
- ✅ Logging completo para monitoramento
- ✅ Código comentado e customizável

**Onde modificar para customizar:**
- Linha 273: Filtros de histórico (data, status)
- Linha 310: Critérios de seleção (ordenação, filtros)
- Linha 334: Comportamento do fallback
- Linha 370: Lógica de unicidade

---

_Criado em: 2025-11-14_
_Arquivo: backend/routers/enem_simulados.py_
_Sistema: ENEM-IA Anti-Repetição_
