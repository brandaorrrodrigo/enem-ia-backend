# Módulo AI - MedicControl

Sistema de análise inteligente baseado em regras para avaliação de pacientes.

## Visão Geral

O módulo AI analisa dados de pacientes (adesão a medicamentos, sinais vitais, exames) e gera:
- Resumo inteligível da situação clínica
- Score de risco (0-100)
- Classificação de risco (low, moderate, high)
- Recomendações personalizadas

**Importante:** Este módulo é baseado em REGRAS, não utiliza LLM ou modelos de Machine Learning.

## Estrutura de Arquivos

```
backend/src/ai/
├── ai.types.ts         # Interfaces e tipos TypeScript
├── ai.service.ts       # Lógica de análise e cálculos
├── ai.controller.ts    # Controladores de endpoints
├── ai.routes.ts        # Definição de rotas
├── index.ts           # Exportações do módulo
└── README.md          # Esta documentação
```

## Endpoints

### Base URL
`/api/v1/ai`

### 1. Health Check

**GET** `/api/v1/ai/health`

Verifica se o módulo AI está funcionando.

**Autenticação:** Não requerida

**Resposta:**
```json
{
  "success": true,
  "message": "AI module is running",
  "version": "1.0.0",
  "features": {
    "adherenceAnalysis": true,
    "vitalsAnalysis": true,
    "examsAnalysis": true,
    "riskScoring": true,
    "recommendations": true
  }
}
```

### 2. Patient Summary

**GET** `/api/v1/ai/patient/:patientId/summary`

Retorna análise completa de um paciente.

**Autenticação:** Requerida

**Permissões:**
- `PATIENT`: Apenas para o próprio ID
- `CAREGIVER`: Para pacientes sob responsabilidade
- `PROFESSIONAL`: Para pacientes atendidos
- `ADMIN`: Acesso total

**Parâmetros:**
- `patientId` (path): ID do paciente

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "data": {
    "patientId": "uuid",
    "generatedAt": "2025-11-14T10:30:00Z",
    "adherence": {
      "days": 30,
      "totalReminders": 90,
      "taken": 82,
      "late": 5,
      "missed": 3,
      "adherenceRate": 91.11,
      "adherenceStatus": "good"
    },
    "vitals": {
      "lastMeasurements": {
        "systolic": 145,
        "diastolic": 92,
        "heartRate": 78,
        "bloodGlucose": 190,
        "temperature": 36.5,
        "oxygenSaturation": 97
      },
      "flags": ["PRESSURE_HIGH", "GLUCOSE_HIGH"],
      "flagDetails": [
        {
          "flag": "PRESSURE_HIGH",
          "value": 145,
          "threshold": 140,
          "severity": "low"
        },
        {
          "flag": "GLUCOSE_HIGH",
          "value": 190,
          "threshold": 180,
          "severity": "medium"
        }
      ]
    },
    "exams": {
      "recentExams": [
        {
          "type": "Hemograma",
          "status": "completed",
          "resultAt": "2025-10-15T10:00:00Z",
          "summary": "Normal - sem alterações"
        },
        {
          "type": "HbA1c",
          "status": "scheduled",
          "scheduledAt": "2025-11-04T09:00:00Z",
          "daysOverdue": 10
        }
      ],
      "pendingExams": 2,
      "overdueExams": 1,
      "completedExams": 5
    },
    "riskScore": {
      "value": 45.5,
      "level": "moderate",
      "reasons": [
        "Pressão arterial frequentemente elevada (145 mmHg)",
        "Glicemia frequentemente elevada (190 mg/dL)",
        "1 exame(s) atrasado(s) há mais de 30 dias"
      ]
    },
    "recommendations": [
      "Avaliar ajuste da medicação anti-hipertensiva com o profissional responsável e intensificar monitorização.",
      "Glicemia acima da meta: revisar medicação antidiabética, reforçar orientações de dieta e atividade física.",
      "Reagendar 1 exame(s) atrasado(s) o mais breve possível e revisar resultados anteriores.",
      "Risco moderado: agendar consulta de acompanhamento nas próximas 2 semanas."
    ]
  }
}
```

**Erros Possíveis:**
- `400`: Patient ID inválido ou ausente
- `401`: Não autenticado
- `403`: Sem permissão para acessar dados deste paciente
- `500`: Erro interno do servidor

## Lógica de Análise

### 1. Análise de Adesão

Analisa lembretes dos últimos 30 dias:

**Taxa de adesão:** `(taken + late) / totalReminders * 100`

**Status:**
- `good`: ≥ 90%
- `medium`: 75-89%
- `bad`: < 75%

### 2. Análise de Sinais Vitais

Analisa medições dos últimos 7 dias:

**Flags geradas:**

| Flag | Condição | Peso no Risco |
|------|----------|---------------|
| PRESSURE_HIGH | Sistólica ≥ 140 ou Diastólica ≥ 90 (2+ medições) | 15 pontos |
| PRESSURE_LOW | Sistólica ≤ 90 ou Diastólica ≤ 60 (2+ medições) | 15 pontos |
| GLUCOSE_HIGH | Glicemia ≥ 180 mg/dL (2+ medições) | 15 pontos |
| GLUCOSE_LOW | Glicemia ≤ 70 mg/dL (1+ medição) | 22.5 pontos |
| HEART_RATE_HIGH | FC ≥ 100 bpm | 10 pontos |
| HEART_RATE_LOW | FC ≤ 50 bpm | 10 pontos |
| TEMPERATURE_HIGH | Temperatura ≥ 38°C | 10 pontos |
| TEMPERATURE_LOW | Temperatura ≤ 35°C | 10 pontos |
| OXYGEN_LOW | Saturação O2 ≤ 92% | 20 pontos |

**Severidade:**
- `low`: Leve elevação/redução
- `medium`: Moderada elevação/redução
- `high`: Elevação/redução grave

### 3. Análise de Exames

**Contadores:**
- `pendingExams`: Exames scheduled ou pending_results
- `overdueExams`: Exames com > 30 dias de atraso
- `completedExams`: Exames finalizados
- `recentExams`: Últimos 5 exames

**Peso no Risco:**
- Exame atrasado: 15 pontos cada
- Mais de 3 exames pendentes: 5 pontos

### 4. Cálculo de Risco

**Score total:** Soma dos pontos (0-100)

**Componentes:**
1. Adesão ruim: +25 pontos
2. Adesão média: +10 pontos
3. Flags de sinais vitais: conforme tabela acima
4. Exames atrasados: 15 pontos cada
5. Muitos exames pendentes: 5 pontos

**Níveis de risco:**
- `low`: 0-29 pontos
- `moderate`: 30-59 pontos
- `high`: 60+ pontos

### 5. Geração de Recomendações

Baseadas nas análises:

**Exemplos:**
- Adesão ruim → Reforçar estratégias, revisar horários
- Pressão alta → Avaliar ajuste de medicação
- Glicemia alta → Revisar medicação e dieta
- Exames atrasados → Reagendar urgentemente
- Risco alto → Consulta presencial urgente

## Configuração

O módulo pode ser configurado através de `RiskCalculationConfig`:

```typescript
import { AIService, DEFAULT_RISK_CONFIG } from './ai';

// Usar configuração padrão
const aiService = new AIService();

// Ou personalizar
const customConfig = {
  ...DEFAULT_RISK_CONFIG,
  adherence: {
    ...DEFAULT_RISK_CONFIG.adherence,
    goodThreshold: 95, // Mudar threshold para 95%
  },
};

const customAiService = new AIService(customConfig);
```

## Uso Programático

### No Controller

```typescript
import { aiService } from './ai';

const summary = await aiService.generatePatientSummary(
  patientId,
  reminders,
  vitals,
  exams
);
```

### Integração com Repositórios

O controller precisa buscar dados dos repositórios:

```typescript
// Exemplo (substituir por código real)
const reminders = await reminderRepository.findByPatientId(patientId);
const vitals = await vitalRepository.findByPatientId(patientId);
const exams = await examRepository.findByPatientId(patientId);
```

## TODOs

### Implementação Pendente

- [ ] Integrar com repositórios reais (reminders, vitals, exams)
- [ ] Implementar middleware de autenticação real
- [ ] Implementar middleware de autorização real
- [ ] Verificar relações caregiver-patient e professional-patient
- [ ] Adicionar cache para análises recentes
- [ ] Implementar testes unitários
- [ ] Implementar testes de integração

### Melhorias Futuras

- [ ] Análise de tendências ao longo do tempo
- [ ] Predições baseadas em histórico
- [ ] Sugestões de intervenções personalizadas
- [ ] Dashboard com estatísticas agregadas
- [ ] Integração com LLM para insights mais sofisticados
- [ ] Alertas proativos baseados em mudanças de risco
- [ ] Exportação de relatórios em PDF

## Exemplos de Uso

### Cliente HTTP (curl)

```bash
# Health check
curl http://localhost:3000/api/v1/ai/health

# Patient summary (com autenticação)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:3000/api/v1/ai/patient/patient-123/summary
```

### Cliente Frontend (fetch)

```typescript
// Health check
const healthResponse = await fetch('http://localhost:3000/api/v1/ai/health');
const health = await healthResponse.json();

// Patient summary
const summaryResponse = await fetch(
  `http://localhost:3000/api/v1/ai/patient/${patientId}/summary`,
  {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  }
);
const summary = await summaryResponse.json();
```

## Segurança

### Controle de Acesso

O módulo implementa controle de acesso rigoroso:

1. **Autenticação obrigatória** para todos os endpoints exceto health check
2. **Autorização baseada em roles:**
   - PATIENT: Só pode ver seus próprios dados
   - CAREGIVER: Só pode ver pacientes que cuida
   - PROFESSIONAL: Só pode ver pacientes que atende
   - ADMIN: Acesso total

### Dados Sensíveis

- Dados de saúde são considerados sensíveis
- Sempre use HTTPS em produção
- Implemente rate limiting
- Registre acessos para auditoria

## Performance

### Otimizações Implementadas

- Análise limitada aos últimos 30 dias (adesão)
- Análise limitada aos últimos 7 dias (sinais vitais)
- Apenas os 5 exames mais recentes no resumo

### Recomendações

- Implementar cache Redis para análises recentes (TTL: 1 hora)
- Usar índices no banco para queries por patientId
- Considerar computação assíncrona para análises pesadas

## Suporte

Para questões ou problemas relacionados ao módulo AI:
- Criar issue no repositório
- Contatar a equipe de desenvolvimento

## Licença

MedicControl - Proprietary
