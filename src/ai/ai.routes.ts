/**
 * AI Routes
 * Rotas para endpoints de análise inteligente
 */

import { Router } from 'express';
import { aiController } from './ai.controller';

// TODO: Importar middlewares de autenticação e autorização quando disponíveis
// import { authenticate } from '../middleware/auth.middleware';
// import { authorize } from '../middleware/roles.middleware';

const router = Router();

/**
 * Middleware temporário de autenticação
 * TODO: Substituir pelo middleware real de autenticação
 */
const mockAuthenticate = (req: any, res: any, next: any) => {
  // Mock: Simular usuário autenticado
  req.user = {
    id: 'user-123',
    role: 'PATIENT', // ou 'CAREGIVER', 'PROFESSIONAL', 'ADMIN'
  };
  next();
};

/**
 * Middleware temporário de autorização
 * TODO: Substituir pelo middleware real de autorização
 */
const mockAuthorize = (...roles: string[]) => {
  return (req: any, res: any, next: any) => {
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

// ==================== PUBLIC ROUTES ====================

/**
 * GET /api/v1/ai/health
 * Health check do módulo AI
 * Público - não requer autenticação
 */
router.get('/health', aiController.healthCheck.bind(aiController));

// ==================== PROTECTED ROUTES ====================

/**
 * GET /api/v1/ai/patient/:patientId/summary
 * Retorna resumo inteligente da situação do paciente
 *
 * Permissões:
 * - PATIENT: Apenas para o próprio ID
 * - CAREGIVER: Para pacientes sob sua responsabilidade
 * - PROFESSIONAL: Para pacientes que atende
 * - ADMIN: Acesso total
 *
 * @param {string} patientId - ID do paciente
 * @returns {AIAnalysisResponse} Resumo da análise AI
 */
router.get(
  '/patient/:patientId/summary',
  mockAuthenticate, // TODO: Substituir por authenticate
  mockAuthorize('PATIENT', 'CAREGIVER', 'PROFESSIONAL', 'ADMIN'), // TODO: Substituir por authorize
  aiController.getPatientSummary.bind(aiController)
);

// ==================== FUTURE ROUTES ====================

/**
 * Rotas futuras que podem ser implementadas:
 *
 * POST /api/v1/ai/batch-analysis
 * - Análise em lote para múltiplos pacientes (ADMIN, PROFESSIONAL)
 *
 * GET /api/v1/ai/patient/:patientId/trends
 * - Análise de tendências ao longo do tempo
 *
 * GET /api/v1/ai/patient/:patientId/predictions
 * - Predições baseadas em histórico (quando LLM for integrado)
 *
 * POST /api/v1/ai/patient/:patientId/intervention-suggestions
 * - Sugestões de intervenções personalizadas
 *
 * GET /api/v1/ai/dashboard/statistics
 * - Estatísticas agregadas para dashboard administrativo
 */

export default router;
