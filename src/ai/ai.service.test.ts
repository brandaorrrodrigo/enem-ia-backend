/**
 * AI Service Tests
 * Testes unitários para o serviço de análise AI
 */

import { AIService } from './ai.service';
import { ReminderRecord, VitalRecord, ExamRecord } from './ai.types';

describe('AIService', () => {
  let aiService: AIService;

  beforeEach(() => {
    aiService = new AIService();
  });

  describe('generatePatientSummary', () => {
    it('should generate a complete patient summary', async () => {
      const patientId = 'patient-123';
      const reminders: ReminderRecord[] = createMockReminders();
      const vitals: VitalRecord[] = createMockVitals();
      const exams: ExamRecord[] = createMockExams();

      const summary = await aiService.generatePatientSummary(
        patientId,
        reminders,
        vitals,
        exams
      );

      expect(summary).toBeDefined();
      expect(summary.patientId).toBe(patientId);
      expect(summary.adherence).toBeDefined();
      expect(summary.vitals).toBeDefined();
      expect(summary.exams).toBeDefined();
      expect(summary.riskScore).toBeDefined();
      expect(summary.recommendations).toBeDefined();
      expect(Array.isArray(summary.recommendations)).toBe(true);
    });
  });

  describe('Adherence Analysis', () => {
    it('should classify good adherence (>= 90%)', async () => {
      const reminders = createRemindersWithAdherence(95); // 95% adherence
      const summary = await aiService.generatePatientSummary(
        'patient-123',
        reminders,
        [],
        []
      );

      expect(summary.adherence.adherenceStatus).toBe('good');
      expect(summary.adherence.adherenceRate).toBeGreaterThanOrEqual(90);
    });

    it('should classify medium adherence (75-89%)', async () => {
      const reminders = createRemindersWithAdherence(80); // 80% adherence
      const summary = await aiService.generatePatientSummary(
        'patient-123',
        reminders,
        [],
        []
      );

      expect(summary.adherence.adherenceStatus).toBe('medium');
      expect(summary.adherence.adherenceRate).toBeGreaterThanOrEqual(75);
      expect(summary.adherence.adherenceRate).toBeLessThan(90);
    });

    it('should classify bad adherence (< 75%)', async () => {
      const reminders = createRemindersWithAdherence(60); // 60% adherence
      const summary = await aiService.generatePatientSummary(
        'patient-123',
        reminders,
        [],
        []
      );

      expect(summary.adherence.adherenceStatus).toBe('bad');
      expect(summary.adherence.adherenceRate).toBeLessThan(75);
    });
  });

  describe('Vitals Analysis', () => {
    it('should detect high blood pressure', async () => {
      const vitals: VitalRecord[] = [
        createVital('blood_pressure', '145/92', { systolic: 145, diastolic: 92 }),
        createVital('blood_pressure', '142/90', { systolic: 142, diastolic: 90 }),
      ];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        [],
        vitals,
        []
      );

      expect(summary.vitals.flags).toContain('PRESSURE_HIGH');
    });

    it('should detect high glucose', async () => {
      const vitals: VitalRecord[] = [
        createVital('glucose', '190', { numericValue: 190 }),
        createVital('glucose', '185', { numericValue: 185 }),
      ];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        [],
        vitals,
        []
      );

      expect(summary.vitals.flags).toContain('GLUCOSE_HIGH');
    });

    it('should detect low glucose (hypoglycemia)', async () => {
      const vitals: VitalRecord[] = [
        createVital('glucose', '65', { numericValue: 65 }),
      ];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        [],
        vitals,
        []
      );

      expect(summary.vitals.flags).toContain('GLUCOSE_LOW');
    });

    it('should detect low oxygen saturation', async () => {
      const vitals: VitalRecord[] = [
        createVital('oxygen_saturation', '88', { numericValue: 88 }),
      ];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        [],
        vitals,
        []
      );

      expect(summary.vitals.flags).toContain('OXYGEN_LOW');
    });
  });

  describe('Exams Analysis', () => {
    it('should count pending exams', async () => {
      const exams: ExamRecord[] = [
        createExam('Hemograma', 'scheduled'),
        createExam('Glicemia', 'pending_results'),
        createExam('ECG', 'completed'),
      ];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        [],
        [],
        exams
      );

      expect(summary.exams.pendingExams).toBe(2);
      expect(summary.exams.completedExams).toBe(1);
    });

    it('should detect overdue exams', async () => {
      const fortyDaysAgo = new Date();
      fortyDaysAgo.setDate(fortyDaysAgo.getDate() - 40);

      const exams: ExamRecord[] = [
        createExam('Hemograma', 'scheduled', fortyDaysAgo),
      ];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        [],
        [],
        exams
      );

      expect(summary.exams.overdueExams).toBe(1);
    });
  });

  describe('Risk Score Calculation', () => {
    it('should calculate low risk for healthy patient', async () => {
      const reminders = createRemindersWithAdherence(95);
      const vitals = [
        createVital('blood_pressure', '120/80', { systolic: 120, diastolic: 80 }),
        createVital('glucose', '100', { numericValue: 100 }),
      ];
      const exams = [createExam('Hemograma', 'completed')];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        reminders,
        vitals,
        exams
      );

      expect(summary.riskScore.level).toBe('low');
      expect(summary.riskScore.value).toBeLessThan(30);
    });

    it('should calculate moderate risk', async () => {
      const reminders = createRemindersWithAdherence(80);
      const vitals = [
        createVital('blood_pressure', '145/92', { systolic: 145, diastolic: 92 }),
        createVital('blood_pressure', '142/90', { systolic: 142, diastolic: 90 }),
      ];
      const exams = [createExam('Hemograma', 'scheduled')];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        reminders,
        vitals,
        exams
      );

      expect(summary.riskScore.level).toBe('moderate');
      expect(summary.riskScore.value).toBeGreaterThanOrEqual(30);
      expect(summary.riskScore.value).toBeLessThan(60);
    });

    it('should calculate high risk', async () => {
      const reminders = createRemindersWithAdherence(60); // Bad adherence
      const vitals = [
        createVital('blood_pressure', '160/100', { systolic: 160, diastolic: 100 }),
        createVital('blood_pressure', '165/105', { systolic: 165, diastolic: 105 }),
        createVital('glucose', '250', { numericValue: 250 }),
        createVital('glucose', '240', { numericValue: 240 }),
        createVital('oxygen_saturation', '88', { numericValue: 88 }),
      ];

      const fortyDaysAgo = new Date();
      fortyDaysAgo.setDate(fortyDaysAgo.getDate() - 40);
      const exams = [
        createExam('Hemograma', 'scheduled', fortyDaysAgo),
        createExam('ECG', 'scheduled', fortyDaysAgo),
      ];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        reminders,
        vitals,
        exams
      );

      expect(summary.riskScore.level).toBe('high');
      expect(summary.riskScore.value).toBeGreaterThanOrEqual(60);
    });
  });

  describe('Recommendations', () => {
    it('should recommend adherence improvement for bad adherence', async () => {
      const reminders = createRemindersWithAdherence(60);

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        reminders,
        [],
        []
      );

      const hasAdherenceRecommendation = summary.recommendations.some((rec) =>
        rec.toLowerCase().includes('adesão')
      );
      expect(hasAdherenceRecommendation).toBe(true);
    });

    it('should recommend pressure management for high BP', async () => {
      const vitals = [
        createVital('blood_pressure', '165/105', { systolic: 165, diastolic: 105 }),
        createVital('blood_pressure', '160/100', { systolic: 160, diastolic: 100 }),
      ];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        [],
        vitals,
        []
      );

      const hasPressureRecommendation = summary.recommendations.some((rec) =>
        rec.toLowerCase().includes('pressão') || rec.toLowerCase().includes('urgente')
      );
      expect(hasPressureRecommendation).toBe(true);
    });

    it('should recommend exam rescheduling for overdue exams', async () => {
      const fortyDaysAgo = new Date();
      fortyDaysAgo.setDate(fortyDaysAgo.getDate() - 40);

      const exams = [createExam('Hemograma', 'scheduled', fortyDaysAgo)];

      const summary = await aiService.generatePatientSummary(
        'patient-123',
        [],
        [],
        exams
      );

      const hasExamRecommendation = summary.recommendations.some((rec) =>
        rec.toLowerCase().includes('exame')
      );
      expect(hasExamRecommendation).toBe(true);
    });
  });
});

// ==================== HELPER FUNCTIONS ====================

function createMockReminders(): ReminderRecord[] {
  const reminders: ReminderRecord[] = [];
  const now = new Date();

  for (let i = 0; i < 30; i++) {
    const scheduledAt = new Date(now);
    scheduledAt.setDate(scheduledAt.getDate() - i);

    reminders.push({
      id: `reminder-${i}`,
      patientId: 'patient-123',
      medicationId: `med-${i % 3}`,
      scheduledAt,
      status: i % 10 === 0 ? 'missed' : 'taken',
      takenAt: i % 10 === 0 ? undefined : new Date(scheduledAt.getTime() + 3600000),
      createdAt: scheduledAt,
    });
  }

  return reminders;
}

function createRemindersWithAdherence(targetPercentage: number): ReminderRecord[] {
  const total = 100;
  const taken = Math.floor((total * targetPercentage) / 100);
  const missed = total - taken;

  const reminders: ReminderRecord[] = [];
  const now = new Date();

  for (let i = 0; i < total; i++) {
    const scheduledAt = new Date(now);
    scheduledAt.setDate(scheduledAt.getDate() - i);

    reminders.push({
      id: `reminder-${i}`,
      patientId: 'patient-123',
      medicationId: 'med-1',
      scheduledAt,
      status: i < taken ? 'taken' : 'missed',
      takenAt: i < taken ? new Date(scheduledAt.getTime() + 3600000) : undefined,
      createdAt: scheduledAt,
    });
  }

  return reminders;
}

function createMockVitals(): VitalRecord[] {
  return [
    createVital('blood_pressure', '130/85', { systolic: 130, diastolic: 85 }),
    createVital('glucose', '110', { numericValue: 110 }),
    createVital('heart_rate', '75', { numericValue: 75 }),
    createVital('temperature', '36.5', { numericValue: 36.5 }),
    createVital('oxygen_saturation', '97', { numericValue: 97 }),
  ];
}

function createVital(
  type: VitalRecord['type'],
  value: string,
  extras: Partial<VitalRecord> = {}
): VitalRecord {
  return {
    id: `vital-${Date.now()}-${Math.random()}`,
    patientId: 'patient-123',
    type,
    value,
    recordedAt: new Date(Date.now() - 86400000), // 1 day ago
    createdAt: new Date(Date.now() - 86400000),
    ...extras,
  };
}

function createMockExams(): ExamRecord[] {
  return [
    createExam('Hemograma', 'completed'),
    createExam('Glicemia de jejum', 'scheduled'),
    createExam('ECG', 'pending_results'),
  ];
}

function createExam(
  type: string,
  status: ExamRecord['status'],
  scheduledAt?: Date
): ExamRecord {
  return {
    id: `exam-${Date.now()}-${Math.random()}`,
    patientId: 'patient-123',
    type,
    status,
    scheduledAt: scheduledAt || new Date(Date.now() + 86400000 * 7),
    completedAt: status === 'completed' ? new Date() : undefined,
    resultAt: status === 'completed' ? new Date() : undefined,
    result: status === 'completed' ? 'Normal - sem alterações' : undefined,
    createdAt: new Date(Date.now() - 86400000 * 30),
  };
}
