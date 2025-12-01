# 📚 API de Simulados ENEM - Guia Completo

## 🎯 Visão Geral

API completa para criação, execução e avaliação de simulados do ENEM integrada com banco Prisma.

**Base URL:** `http://localhost:8000` (desenvolvimento)

**Documentação Interativa:** `http://localhost:8000/docs`

---

## 🚀 Como Iniciar o Backend

### 1. Preparar Prisma (Frontend)

```bash
cd enem-pro

# Instalar dependências
npm install

# Gerar migration para novos models
npx prisma migrate dev --name add_simulado_models

# Gerar Prisma Client
npx prisma generate
```

### 2. Iniciar Servidor FastAPI (Backend)

```bash
cd backend

# Instalar dependências (se necessário)
pip install fastapi uvicorn pydantic

# Iniciar servidor
python main.py

# OU usando uvicorn diretamente
uvicorn main:app --reload --port 8000
```

O servidor estará disponível em `http://localhost:8000`

---

## 📝 Fluxo Completo de um Simulado

```
1. START     → Usuário inicia simulado
2. ANSWER    → Usuário responde questões (uma por vez ou múltiplas)
3. FINISH    → Usuário finaliza e recebe nota
4. HISTORY   → Consulta histórico de simulados
5. COMPARE   → Compara nota com nota de corte
```

---

## 🔗 Endpoints

### 1. POST `/api/enem/simulados/start` - Iniciar Simulado

Cria novo simulado e retorna questões para o usuário responder.

#### Request

```javascript
const response = await fetch('http://localhost:8000/api/enem/simulados/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: "user@example.com",  // Email do usuário (obrigatório)
    area: "matematica",            // Opcional: filtrar por disciplina
    quantidade: 10                 // Número de questões (1-180)
  })
});

const data = await response.json();
```

#### Response

```json
{
  "simulado_id": "clx123abc...",
  "usuario_simulado_id": "clx456def...",
  "quantidade": 10,
  "disciplina": "matematica",
  "questoes": [
    {
      "id": 15,
      "enunciado": "Uma função quadrática f(x) = ax² + bx + c...",
      "alternativas": [
        "a = -1",
        "a = 0",
        "a = 1",
        "a = 2",
        "a = 3"
      ]
    },
    // ... mais 9 questões
  ]
}
```

#### Uso no Frontend (React/Next.js)

```typescript
// app/simulado/iniciar/page.tsx
'use client';

import { useState } from 'react';

export default function IniciarSimulado() {
  const [simulado, setSimulado] = useState(null);

  async function iniciarSimulado() {
    const res = await fetch('http://localhost:8000/api/enem/simulados/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user@example.com',
        area: 'matematica',
        quantidade: 10
      })
    });

    const data = await res.json();
    setSimulado(data);

    // Redireciona para página de responder
    window.location.href = `/simulado/${data.usuario_simulado_id}`;
  }

  return (
    <button onClick={iniciarSimulado}>
      Iniciar Simulado de Matemática
    </button>
  );
}
```

---

### 2. POST `/api/enem/simulados/answer` - Responder Questão

Grava resposta do usuário para uma questão específica.

#### Request

```javascript
await fetch('http://localhost:8000/api/enem/simulados/answer', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: "user@example.com",
    simulado_id: "clx456def...",  // ID recebido do /start
    questao_id: 15,
    alternativa_marcada: 2         // 0=A, 1=B, 2=C, 3=D, 4=E, null=não respondeu
  })
});
```

#### Response

```json
{
  "ok": true,
  "resposta_id": 42,
  "questao_id": 15,
  "alternativa_marcada": 2
}
```

#### Uso no Frontend

```typescript
// components/QuestaoCard.tsx
'use client';

import { useState } from 'react';

interface Props {
  questao: any;
  simuladoId: string;
  userId: string;
}

export function QuestaoCard({ questao, simuladoId, userId }: Props) {
  const [selected, setSelected] = useState<number | null>(null);

  async function handleResposta(alternativaIndex: number) {
    setSelected(alternativaIndex);

    // Salva resposta no backend
    await fetch('http://localhost:8000/api/enem/simulados/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        simulado_id: simuladoId,
        questao_id: questao.id,
        alternativa_marcada: alternativaIndex
      })
    });
  }

  return (
    <div className="questao-card">
      <h3>Questão {questao.id}</h3>
      <p>{questao.enunciado}</p>

      <div className="alternativas">
        {questao.alternativas.map((texto, index) => {
          const letra = String.fromCharCode(65 + index); // A, B, C, D, E

          return (
            <button
              key={index}
              onClick={() => handleResposta(index)}
              className={selected === index ? 'selected' : ''}
            >
              {letra}) {texto}
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

---

### 3. POST `/api/enem/simulados/finish` - Finalizar Simulado

Calcula nota final do simulado baseado nas respostas.

#### Request

```javascript
const response = await fetch('http://localhost:8000/api/enem/simulados/finish', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: "user@example.com",
    simulado_id: "clx456def..."
  })
});

const resultado = await response.json();
```

#### Response

```json
{
  "ok": true,
  "usuario_simulado_id": "clx456def...",
  "acertos": 7,
  "erros": 3,
  "total": 10,
  "porcentagem": 70.0,
  "nota": 790.0,
  "desempenho": "👍 Bom",
  "erros_detalhados": [
    {
      "questao_id": 18,
      "enunciado": "Uma função...",
      "alternativas": ["...", "...", "...", "...", "..."],
      "correta": 2,
      "marcada": 3
    },
    // ... mais erros
  ]
}
```

#### Uso no Frontend

```typescript
// app/simulado/[id]/finalizar/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function FinalizarSimulado({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [resultado, setResultado] = useState(null);

  async function finalizarSimulado() {
    const res = await fetch('http://localhost:8000/api/enem/simulados/finish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user@example.com',
        simulado_id: params.id
      })
    });

    const data = await res.json();
    setResultado(data);
  }

  if (!resultado) {
    return (
      <button onClick={finalizarSimulado}>
        Finalizar Simulado
      </button>
    );
  }

  return (
    <div className="resultado">
      <h1>{resultado.desempenho}</h1>
      <p>Nota: <strong>{resultado.nota}</strong> / 1000</p>
      <p>Acertos: {resultado.acertos} / {resultado.total}</p>
      <p>Porcentagem: {resultado.porcentagem}%</p>

      <h2>Questões Erradas:</h2>
      <ul>
        {resultado.erros_detalhados.map(erro => (
          <li key={erro.questao_id}>
            <p>{erro.enunciado}</p>
            <p>Você marcou: {String.fromCharCode(65 + erro.marcada)}</p>
            <p>Correta: {String.fromCharCode(65 + erro.correta)}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

---

### 4. GET `/api/enem/simulados/history` - Histórico

Busca histórico de simulados do usuário.

#### Request

```javascript
const response = await fetch(
  'http://localhost:8000/api/enem/simulados/history?user_id=user@example.com'
);

const data = await response.json();
```

#### Response

```json
{
  "simulados": [
    {
      "id": "clx456def...",
      "disciplina": "matematica",
      "nota": 790.0,
      "acertos": 7,
      "total": 10,
      "porcentagem": "70.00",
      "data": "2025-11-13T10:30:00.000Z"
    },
    // ... mais simulados
  ]
}
```

#### Uso no Frontend

```typescript
// app/dashboard/page.tsx
'use client';

import { useEffect, useState } from 'react';

export default function Dashboard() {
  const [historico, setHistorico] = useState([]);

  useEffect(() => {
    async function fetchHistorico() {
      const res = await fetch(
        'http://localhost:8000/api/enem/simulados/history?user_id=user@example.com'
      );
      const data = await res.json();
      setHistorico(data.simulados);
    }

    fetchHistorico();
  }, []);

  return (
    <div className="dashboard">
      <h1>Meus Simulados</h1>

      <table>
        <thead>
          <tr>
            <th>Disciplina</th>
            <th>Nota</th>
            <th>Acertos</th>
            <th>Data</th>
          </tr>
        </thead>
        <tbody>
          {historico.map(sim => (
            <tr key={sim.id}>
              <td>{sim.disciplina}</td>
              <td>{sim.nota}</td>
              <td>{sim.acertos}/{sim.total} ({sim.porcentagem}%)</td>
              <td>{new Date(sim.data).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

### 5. POST `/api/enem/simulados/compare-score` - Comparar Nota de Corte

Compara nota do simulado com nota de corte de um curso.

#### Request

```javascript
const response = await fetch('http://localhost:8000/api/enem/simulados/compare-score', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: "user@example.com",
    simulado_id: "clx456def...",
    curso: "Medicina",
    universidade: "USP",
    ano: 2024
  })
});

const comparacao = await response.json();
```

#### Response

```json
{
  "passou": false,
  "nota_usuario": 790.0,
  "nota_corte": 850.0,
  "diferenca": -60.0,
  "mensagem": "📚 Continue estudando! Você precisa de 60.0 pontos a mais..."
}
```

#### Uso no Frontend

```typescript
// components/ComparadorNotaCorte.tsx
'use client';

import { useState } from 'react';

export function ComparadorNotaCorte({ simuladoId, userId, nota }: any) {
  const [curso, setCurso] = useState('');
  const [universidade, setUniversidade] = useState('');
  const [resultado, setResultado] = useState(null);

  async function comparar() {
    const res = await fetch('http://localhost:8000/api/enem/simulados/compare-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        simulado_id: simuladoId,
        curso: curso,
        universidade: universidade,
        ano: 2024
      })
    });

    const data = await res.json();
    setResultado(data);
  }

  return (
    <div>
      <h2>Comparar com Nota de Corte</h2>
      <p>Sua nota: {nota}</p>

      <input
        placeholder="Curso (ex: Medicina)"
        value={curso}
        onChange={e => setCurso(e.target.value)}
      />
      <input
        placeholder="Universidade (ex: USP)"
        value={universidade}
        onChange={e => setUniversidade(e.target.value)}
      />

      <button onClick={comparar}>Comparar</button>

      {resultado && (
        <div className={resultado.passou ? 'passou' : 'nao-passou'}>
          <p>{resultado.mensagem}</p>
          <p>Nota de corte: {resultado.nota_corte}</p>
          <p>Diferença: {resultado.diferenca} pontos</p>
        </div>
      )}
    </div>
  );
}
```

---

## 🗄️ Modelos Prisma

```prisma
// Questão do ENEM
model Questao {
  id           Int      @id @default(autoincrement())
  enunciado    String
  alternativas Json     // Array: ["texto A", "texto B", ...]
  correta      Int      // 0-4 (A-E)
}

// Simulado base
model Simulado {
  id         String   @id @default(cuid())
  disciplina String
  createdAt  DateTime @default(now())
}

// Simulado do usuário (em andamento ou finalizado)
model UsuarioSimulado {
  id         String    @id @default(cuid())
  usuarioId  String
  simuladoId String
  status     String    @default("em_andamento")
  nota       Float?
  acertos    Int?
  total      Int?
  createdAt  DateTime  @default(now())
  finishedAt DateTime?
}

// Resposta individual
model UsuarioResposta {
  id                Int      @id @default(autoincrement())
  usuarioSimuladoId String
  questaoId         Int
  alternativaMarcada Int?    // 0-4 ou null
}

// Nota de corte
model NotaCorte {
  id           Int      @id @default(autoincrement())
  curso        String
  universidade String
  ano          Int
  semestre     Int
  notaMinima   Float
  modalidade   String   @default("ampla_concorrencia")
}
```

---

## ⚠️ Importante

### Conversão de Alternativas

- **Frontend:** Usa letras (A, B, C, D, E)
- **Backend:** Usa índices (0, 1, 2, 3, 4)

Conversão:
```javascript
// Letra → Índice
const indice = alternativa.charCodeAt(0) - 65;  // 'A' → 0, 'B' → 1, ...

// Índice → Letra
const letra = String.fromCharCode(65 + indice);  // 0 → 'A', 1 → 'B', ...
```

### Fluxo de Estados

```
┌─────────────────┐
│  em_andamento   │ ← Simulado criado (/start)
└────────┬────────┘
         │
         ↓ Usuário responde questões (/answer)
         │
         ↓ Usuário finaliza (/finish)
┌────────┴────────┐
│   finalizado    │ ← Nota calculada
└─────────────────┘
```

---

## 🐛 Troubleshooting

### Erro: "Projeto Prisma não encontrado"

```bash
# Verifique se o caminho está correto
ls ../enem-pro/prisma/schema.prisma

# Se não existir, ajuste PRISMA_PROJECT_PATH em enem_simulados.py
```

### Erro: "node command not found"

```bash
# Instale Node.js
node --version  # Deve retornar v18+
npm --version
```

### Erro: Migration necessária

```bash
cd enem-pro
npx prisma migrate dev --name add_simulado_models
npx prisma generate
```

---

## 📊 Exemplo Completo de Fluxo

```javascript
// 1. Iniciar simulado
const start = await fetch('/api/enem/simulados/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'aluno@example.com',
    area: 'matematica',
    quantidade: 5
  })
});

const { usuario_simulado_id, questoes } = await start.json();

// 2. Responder questões
for (let i = 0; i < questoes.length; i++) {
  const questao = questoes[i];

  // Usuário marca alternativa (simulando escolha aleatória)
  const alternativa = Math.floor(Math.random() * 5);

  await fetch('/api/enem/simulados/answer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: 'aluno@example.com',
      simulado_id: usuario_simulado_id,
      questao_id: questao.id,
      alternativa_marcada: alternativa
    })
  });
}

// 3. Finalizar
const finish = await fetch('/api/enem/simulados/finish', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'aluno@example.com',
    simulado_id: usuario_simulado_id
  })
});

const resultado = await finish.json();
console.log(`Nota: ${resultado.nota}, Acertos: ${resultado.acertos}/${resultado.total}`);

// 4. Comparar com nota de corte
const compare = await fetch('/api/enem/simulados/compare-score', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'aluno@example.com',
    simulado_id: usuario_simulado_id,
    curso: 'Medicina',
    universidade: 'USP',
    ano: 2024
  })
});

const comparacao = await compare.json();
console.log(comparacao.mensagem);
```

---

_Documentação gerada em: 2025-11-13_
_Versão da API: 2.0.0_
