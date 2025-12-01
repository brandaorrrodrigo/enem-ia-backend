/**
 * AI Module Entry Point
 * Ponto de entrada do módulo de análise inteligente
 */

export { aiService, AIService } from './ai.service';
export { aiController, AIController } from './ai.controller';
export { default as aiRoutes } from './ai.routes';

export {
  // Types
  PatientAISummary,
  AdherenceAnalysis,
  VitalsAnalysis,
  ExamsAnalysis,
  RiskScore,
  AIAnalysisResponse,
  // Enums
  AdherenceStatus,
  VitalFlag,
  RiskLevel,
  // Config
  RiskCalculationConfig,
  DEFAULT_RISK_CONFIG,
} from './ai.types';
