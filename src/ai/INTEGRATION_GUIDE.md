# Guia de Integração - Módulo AI

Este guia mostra como integrar o módulo AI no backend do MedicControl.

## Passo 1: Instalar Dependências

```bash
cd backend
npm install express cors helmet morgan
npm install --save-dev @types/express @types/cors @types/node typescript jest @types/jest ts-jest
```

## Passo 2: Configurar TypeScript

Criar ou atualizar `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "**/*.test.ts"]
}
```

## Passo 3: Integrar Rotas no App Principal

Editar `src/app.ts` (ou criar se não existir):

```typescript
import express from 'express';
import aiRoutes from './ai/ai.routes';

const app = express();

// Middlewares
app.use(express.json());

// Rotas
app.use('/api/v1/ai', aiRoutes);

export default app;
```

## Passo 4: Criar Servidor

Criar `src/server.ts`:

```typescript
import app from './app';

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`AI endpoints available at http://localhost:${PORT}/api/v1/ai`);
});
```

## Passo 5: Configurar Scripts no package.json

```json
{
  "scripts": {
    "dev": "ts-node-dev --respawn src/server.ts",
    "build": "tsc",
    "start": "node dist/server.js",
    "test": "jest",
    "test:watch": "jest --watch"
  }
}
```

## Passo 6: Integrar com Repositórios

### Exemplo: Reminders Repository

Criar interface no `ai.controller.ts`:

```typescript
// Importar repository real
import { reminderRepository } from '../reminders/reminder.repository';

// No método getPatientReminders do controller
private async getPatientReminders(patientId: string): Promise<ReminderRecord[]> {
  return await reminderRepository.findByPatientId(patientId);
}
```

### Repetir para Vitals e Exams

```typescript
import { vitalRepository } from '../vitals/vital.repository';
import { examRepository } from '../exams/exam.repository';

private async getPatientVitals(patientId: string): Promise<VitalRecord[]> {
  return await vitalRepository.findByPatientId(patientId);
}

private async getPatientExams(patientId: string): Promise<ExamRecord[]> {
  return await examRepository.findByPatientId(patientId);
}
```

## Passo 7: Implementar Autenticação

### Criar Middleware de Autenticação

`src/middleware/auth.middleware.ts`:

```typescript
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';

export interface AuthRequest extends Request {
  user?: {
    id: string;
    role: 'PATIENT' | 'CAREGIVER' | 'PROFESSIONAL' | 'ADMIN';
  };
}

export const authenticate = (
  req: AuthRequest,
  res: Response,
  next: NextFunction
) => {
  const token = req.headers.authorization?.replace('Bearer ', '');

  if (!token) {
    return res.status(401).json({
      success: false,
      message: 'Authentication required',
    });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET!) as any;
    req.user = {
      id: decoded.userId,
      role: decoded.role,
    };
    next();
  } catch (error) {
    res.status(401).json({
      success: false,
      message: 'Invalid token',
    });
  }
};
```

### Criar Middleware de Autorização

`src/middleware/roles.middleware.ts`:

```typescript
import { Response, NextFunction } from 'express';
import { AuthRequest } from './auth.middleware';

export const authorize = (...roles: string[]) => {
  return (req: AuthRequest, res: Response, next: NextFunction) => {
    const userRole = req.user?.role;

    if (!userRole || !roles.includes(userRole)) {
      return res.status(403).json({
        success: false,
        message: 'Access denied: Insufficient permissions',
      });
    }

    next();
  };
};
```

### Atualizar Rotas AI

`src/ai/ai.routes.ts`:

```typescript
import { authenticate } from '../middleware/auth.middleware';
import { authorize } from '../middleware/roles.middleware';

// Substituir mockAuthenticate e mockAuthorize
router.get(
  '/patient/:patientId/summary',
  authenticate,
  authorize('PATIENT', 'CAREGIVER', 'PROFESSIONAL', 'ADMIN'),
  aiController.getPatientSummary.bind(aiController)
);
```

## Passo 8: Implementar Verificação de Permissões

### No Controller

Atualizar método `checkPatientAccess`:

```typescript
private async checkPatientAccess(
  userId: string,
  userRole: string,
  patientId: string
): Promise<boolean> {
  if (userRole === 'ADMIN') {
    return true;
  }

  if (userRole === 'PATIENT') {
    return userId === patientId;
  }

  if (userRole === 'CAREGIVER') {
    const relationship = await caregiverPatientRepository.findRelationship(
      userId,
      patientId
    );
    return relationship !== null;
  }

  if (userRole === 'PROFESSIONAL') {
    const relationship = await professionalPatientRepository.findRelationship(
      userId,
      patientId
    );
    return relationship !== null;
  }

  return false;
}
```

## Passo 9: Configurar Variáveis de Ambiente

Criar `.env`:

```bash
# Server
PORT=3000
NODE_ENV=development

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/mediccontrol

# JWT
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_EXPIRES_IN=7d

# Frontend
FRONTEND_URL=http://localhost:3000

# AI Module (opcional)
AI_CACHE_TTL=3600
```

## Passo 10: Testar o Módulo

### Rodar Servidor

```bash
npm run dev
```

### Testar Health Check

```bash
curl http://localhost:3000/api/v1/ai/health
```

Resposta esperada:
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

### Testar Patient Summary (requer autenticação)

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:3000/api/v1/ai/patient/patient-123/summary
```

### Rodar Testes

```bash
npm test
```

## Passo 11: Deploy

### Build para Produção

```bash
npm run build
```

### Configurar PM2 (opcional)

```bash
npm install -g pm2
pm2 start dist/server.js --name mediccontrol-api
pm2 save
pm2 startup
```

## Troubleshooting

### Erro: "Cannot find module"

Verifique se todas as dependências estão instaladas:
```bash
npm install
```

### Erro: "TypeScript compilation failed"

Verifique `tsconfig.json` e corrija erros de sintaxe.

### Erro: "Port already in use"

Mude a porta no `.env` ou mate o processo:
```bash
lsof -ti:3000 | xargs kill
```

### Mock data em vez de dados reais

Substitua os métodos mock nos controllers pelos repositórios reais.

## Próximos Passos

1. ✅ Módulo AI implementado
2. ⬜ Integrar com frontend
3. ⬜ Adicionar cache Redis
4. ⬜ Implementar WebSocket para alertas em tempo real
5. ⬜ Adicionar exportação de relatórios PDF
6. ⬜ Integrar LLM para insights avançados

## Suporte

Dúvidas? Consulte:
- README.md - Documentação completa
- ai.service.test.ts - Exemplos de uso
- API docs (Swagger) - Em desenvolvimento
