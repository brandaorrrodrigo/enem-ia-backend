/**
 * AI Module Types
 * Sistema de análise inteligente baseado em regras para MedicControl
 */

// ==================== ADHERENCE TYPES ====================

export type AdherenceStatus = 'good' | 'medium' | 'bad';

export interface AdherenceAnalysis {
  days: number;
  totalReminders: number;
  taken: number;
  late: number;
  missed: number;
  adherenceRate: number;
  adherenceStatus: AdherenceStatus;
}

// ==================== VITALS TYPES ====================

export type VitalFlag =
  | 'PRESSURE_HIGH'
  | 'PRESSURE_LOW'
  | 'GLUCOSE_HIGH'
  | 'GLUCOSE_LOW'
  | 'HEART_RATE_HIGH'
  | 'HEART_RATE_LOW'
  | 'TEMPERATURE_HIGH'
  | 'TEMPERATURE_LOW'
  | 'OXYGEN_LOW';

export interface LastMeasurements {
  systolic?: number;
  diastolic?: number;
  heartRate?: number;
  bloodGlucose?: number;
  temperature?: number;
  oxygenSaturation?: number;
}

export interface VitalsAnalysis {
  lastMeasurements: LastMeasurements;
  flags: VitalFlag[];
  flagDetails: Array<{
    flag: VitalFlag;
    value: number;
    threshold: number;
    severity: 'low' | 'medium' | 'high';
  }>;
}

// ==================== EXAMS TYPES ====================

export interface ExamSummary {
  type: string;
  status: 'scheduled' | 'completed' | 'pending_results' | 'cancelled';
  resultAt?: string;
  summary?: string;
  scheduledAt?: string;
  daysOverdue?: number;
}

export interface ExamsAnalysis {
  recentExams: ExamSummary[];
  pendingExams: number;
  overdueExams: number;
  completedExams: number;
}

// ==================== RISK SCORE TYPES ====================

export type RiskLevel = 'low' | 'moderate' | 'high';

export interface RiskScore {
  value: number; // 0-100
  level: RiskLevel;
  reasons: string[];
}

// ==================== PATIENT SUMMARY TYPES ====================

export interface PatientAISummary {
  patientId: string;
  generatedAt: string;
  adherence: AdherenceAnalysis;
  vitals: VitalsAnalysis;
  exams: ExamsAnalysis;
  riskScore: RiskScore;
  recommendations: string[];
}

// ==================== API RESPONSE TYPE ====================

export interface AIAnalysisResponse {
  success: boolean;
  data: PatientAISummary;
  message?: string;
}

// ==================== CALCULATION CONFIG ====================

export interface RiskCalculationConfig {
  adherence: {
    goodThreshold: number; // >= 90
    mediumThreshold: number; // >= 75
    badWeight: number; // pontos adicionados ao risco
    mediumWeight: number;
  };
  vitals: {
    pressure: {
      systolicHigh: number; // >= 140
      systolicLow: number; // <= 90
      diastolicHigh: number; // >= 90
      diastolicLow: number; // <= 60
      weight: number;
    };
    glucose: {
      high: number; // >= 180
      low: number; // <= 70
      weight: number;
    };
    heartRate: {
      high: number; // >= 100
      low: number; // <= 50
      weight: number;
    };
    temperature: {
      high: number; // >= 38
      low: number; // <= 35
      weight: number;
    };
    oxygen: {
      low: number; // <= 92
      weight: number;
    };
  };
  exams: {
    overdueDays: number; // > 30 dias
    overdueWeight: number;
    pendingWeight: number;
  };
  riskLevels: {
    lowMax: number; // 0-29
    moderateMax: number; // 30-59
    // high: 60+
  };
}

// ==================== DEFAULT CONFIG ====================

export const DEFAULT_RISK_CONFIG: RiskCalculationConfig = {
  adherence: {
    goodThreshold: 90,
    mediumThreshold: 75,
    badWeight: 25,
    mediumWeight: 10,
  },
  vitals: {
    pressure: {
      systolicHigh: 140,
      systolicLow: 90,
      diastolicHigh: 90,
      diastolicLow: 60,
      weight: 15,
    },
    glucose: {
      high: 180,
      low: 70,
      weight: 15,
    },
    heartRate: {
      high: 100,
      low: 50,
      weight: 10,
    },
    temperature: {
      high: 38,
      low: 35,
      weight: 10,
    },
    oxygen: {
      low: 92,
      weight: 20,
    },
  },
  exams: {
    overdueDays: 30,
    overdueWeight: 15,
    pendingWeight: 5,
  },
  riskLevels: {
    lowMax: 29,
    moderateMax: 59,
  },
};

// ==================== DATABASE MODELS INTERFACES ====================
// Interfaces esperadas dos outros módulos

export interface ReminderRecord {
  id: string;
  patientId: string;
  medicationId: string;
  scheduledAt: Date;
  status: 'pending' | 'taken' | 'missed' | 'skipped' | 'late';
  takenAt?: Date;
  createdAt: Date;
}

export interface VitalRecord {
  id: string;
  patientId: string;
  type: 'blood_pressure' | 'heart_rate' | 'temperature' | 'glucose' | 'weight' | 'oxygen_saturation';
  value: string;
  systolic?: number;
  diastolic?: number;
  numericValue?: number;
  recordedAt: Date;
  createdAt: Date;
}

export interface ExamRecord {
  id: string;
  patientId: string;
  type: string;
  status: 'scheduled' | 'completed' | 'pending_results' | 'cancelled';
  scheduledAt?: Date;
  completedAt?: Date;
  resultAt?: Date;
  result?: string;
  notes?: string;
  createdAt: Date;
}
