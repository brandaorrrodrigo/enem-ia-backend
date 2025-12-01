/**
 * AI Service
 * Serviço de análise inteligente baseado em regras para MedicControl
 */

import {
  PatientAISummary,
  AdherenceAnalysis,
  VitalsAnalysis,
  ExamsAnalysis,
  RiskScore,
  AdherenceStatus,
  VitalFlag,
  RiskLevel,
  ReminderRecord,
  VitalRecord,
  ExamRecord,
  LastMeasurements,
  DEFAULT_RISK_CONFIG,
  RiskCalculationConfig,
} from './ai.types';

export class AIService {
  private config: RiskCalculationConfig;

  constructor(config?: Partial<RiskCalculationConfig>) {
    this.config = {
      ...DEFAULT_RISK_CONFIG,
      ...config,
    };
  }

  /**
   * Gera um resumo completo de análise AI para um paciente
   */
  async generatePatientSummary(
    patientId: string,
    reminders: ReminderRecord[],
    vitals: VitalRecord[],
    exams: ExamRecord[]
  ): Promise<PatientAISummary> {
    // Análise de adesão
    const adherence = this.analyzeAdherence(reminders);

    // Análise de sinais vitais
    const vitalsAnalysis = this.analyzeVitals(vitals);

    // Análise de exames
    const examsAnalysis = this.analyzeExams(exams);

    // Cálculo de score de risco
    const riskScore = this.calculateRiskScore(adherence, vitalsAnalysis, examsAnalysis);

    // Geração de recomendações
    const recommendations = this.generateRecommendations(
      adherence,
      vitalsAnalysis,
      examsAnalysis,
      riskScore
    );

    return {
      patientId,
      generatedAt: new Date().toISOString(),
      adherence,
      vitals: vitalsAnalysis,
      exams: examsAnalysis,
      riskScore,
      recommendations,
    };
  }

  /**
   * Analisa a adesão aos medicamentos nos últimos 30 dias
   */
  private analyzeAdherence(reminders: ReminderRecord[]): AdherenceAnalysis {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    // Filtrar lembretes dos últimos 30 dias
    const recentReminders = reminders.filter(
      (r) => new Date(r.scheduledAt) >= thirtyDaysAgo
    );

    const totalReminders = recentReminders.length;
    const taken = recentReminders.filter((r) => r.status === 'taken').length;
    const late = recentReminders.filter((r) => r.status === 'late').length;
    const missed = recentReminders.filter((r) => r.status === 'missed').length;

    // Calcular taxa de adesão (taken + late são considerados tomados)
    const adherenceRate =
      totalReminders > 0
        ? Math.round(((taken + late) / totalReminders) * 10000) / 100
        : 100;

    // Classificar status de adesão
    let adherenceStatus: AdherenceStatus;
    if (adherenceRate >= this.config.adherence.goodThreshold) {
      adherenceStatus = 'good';
    } else if (adherenceRate >= this.config.adherence.mediumThreshold) {
      adherenceStatus = 'medium';
    } else {
      adherenceStatus = 'bad';
    }

    return {
      days: 30,
      totalReminders,
      taken,
      late,
      missed,
      adherenceRate,
      adherenceStatus,
    };
  }

  /**
   * Analisa os sinais vitais recentes
   */
  private analyzeVitals(vitals: VitalRecord[]): VitalsAnalysis {
    // Pegar as últimas medições (últimos 7 dias)
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const recentVitals = vitals.filter(
      (v) => new Date(v.recordedAt) >= sevenDaysAgo
    );

    // Extrair últimas medições de cada tipo
    const lastMeasurements: LastMeasurements = {};
    const flags: VitalFlag[] = [];
    const flagDetails: VitalsAnalysis['flagDetails'] = [];

    // Agrupar por tipo e pegar o mais recente
    const vitalsByType = this.groupVitalsByType(recentVitals);

    // Pressão arterial
    if (vitalsByType.blood_pressure && vitalsByType.blood_pressure.length > 0) {
      const latest = vitalsByType.blood_pressure[0];
      if (latest.systolic !== undefined && latest.diastolic !== undefined) {
        lastMeasurements.systolic = latest.systolic;
        lastMeasurements.diastolic = latest.diastolic;

        // Verificar múltiplas medições para confirmar padrão
        const highPressureCount = vitalsByType.blood_pressure.filter(
          (v) =>
            v.systolic! >= this.config.vitals.pressure.systolicHigh ||
            v.diastolic! >= this.config.vitals.pressure.diastolicHigh
        ).length;

        const lowPressureCount = vitalsByType.blood_pressure.filter(
          (v) =>
            v.systolic! <= this.config.vitals.pressure.systolicLow ||
            v.diastolic! <= this.config.vitals.pressure.diastolicLow
        ).length;

        if (highPressureCount >= 2) {
          flags.push('PRESSURE_HIGH');
          flagDetails.push({
            flag: 'PRESSURE_HIGH',
            value: latest.systolic,
            threshold: this.config.vitals.pressure.systolicHigh,
            severity: latest.systolic >= 160 ? 'high' : latest.systolic >= 150 ? 'medium' : 'low',
          });
        }

        if (lowPressureCount >= 2) {
          flags.push('PRESSURE_LOW');
          flagDetails.push({
            flag: 'PRESSURE_LOW',
            value: latest.systolic,
            threshold: this.config.vitals.pressure.systolicLow,
            severity: latest.systolic <= 80 ? 'high' : latest.systolic <= 85 ? 'medium' : 'low',
          });
        }
      }
    }

    // Glicemia
    if (vitalsByType.glucose && vitalsByType.glucose.length > 0) {
      const latest = vitalsByType.glucose[0];
      if (latest.numericValue !== undefined) {
        lastMeasurements.bloodGlucose = latest.numericValue;

        const highGlucoseCount = vitalsByType.glucose.filter(
          (v) => v.numericValue! >= this.config.vitals.glucose.high
        ).length;

        const lowGlucoseCount = vitalsByType.glucose.filter(
          (v) => v.numericValue! <= this.config.vitals.glucose.low
        ).length;

        if (highGlucoseCount >= 2) {
          flags.push('GLUCOSE_HIGH');
          flagDetails.push({
            flag: 'GLUCOSE_HIGH',
            value: latest.numericValue,
            threshold: this.config.vitals.glucose.high,
            severity: latest.numericValue >= 250 ? 'high' : latest.numericValue >= 200 ? 'medium' : 'low',
          });
        }

        if (lowGlucoseCount >= 1) {
          // Hipoglicemia é mais grave, 1 ocorrência já é alerta
          flags.push('GLUCOSE_LOW');
          flagDetails.push({
            flag: 'GLUCOSE_LOW',
            value: latest.numericValue,
            threshold: this.config.vitals.glucose.low,
            severity: latest.numericValue <= 50 ? 'high' : latest.numericValue <= 60 ? 'medium' : 'low',
          });
        }
      }
    }

    // Frequência cardíaca
    if (vitalsByType.heart_rate && vitalsByType.heart_rate.length > 0) {
      const latest = vitalsByType.heart_rate[0];
      if (latest.numericValue !== undefined) {
        lastMeasurements.heartRate = latest.numericValue;

        if (latest.numericValue >= this.config.vitals.heartRate.high) {
          flags.push('HEART_RATE_HIGH');
          flagDetails.push({
            flag: 'HEART_RATE_HIGH',
            value: latest.numericValue,
            threshold: this.config.vitals.heartRate.high,
            severity: latest.numericValue >= 120 ? 'high' : latest.numericValue >= 110 ? 'medium' : 'low',
          });
        }

        if (latest.numericValue <= this.config.vitals.heartRate.low) {
          flags.push('HEART_RATE_LOW');
          flagDetails.push({
            flag: 'HEART_RATE_LOW',
            value: latest.numericValue,
            threshold: this.config.vitals.heartRate.low,
            severity: latest.numericValue <= 40 ? 'high' : latest.numericValue <= 45 ? 'medium' : 'low',
          });
        }
      }
    }

    // Temperatura
    if (vitalsByType.temperature && vitalsByType.temperature.length > 0) {
      const latest = vitalsByType.temperature[0];
      if (latest.numericValue !== undefined) {
        lastMeasurements.temperature = latest.numericValue;

        if (latest.numericValue >= this.config.vitals.temperature.high) {
          flags.push('TEMPERATURE_HIGH');
          flagDetails.push({
            flag: 'TEMPERATURE_HIGH',
            value: latest.numericValue,
            threshold: this.config.vitals.temperature.high,
            severity: latest.numericValue >= 39 ? 'high' : latest.numericValue >= 38.5 ? 'medium' : 'low',
          });
        }

        if (latest.numericValue <= this.config.vitals.temperature.low) {
          flags.push('TEMPERATURE_LOW');
          flagDetails.push({
            flag: 'TEMPERATURE_LOW',
            value: latest.numericValue,
            threshold: this.config.vitals.temperature.low,
            severity: latest.numericValue <= 34 ? 'high' : latest.numericValue <= 34.5 ? 'medium' : 'low',
          });
        }
      }
    }

    // Saturação de oxigênio
    if (vitalsByType.oxygen_saturation && vitalsByType.oxygen_saturation.length > 0) {
      const latest = vitalsByType.oxygen_saturation[0];
      if (latest.numericValue !== undefined) {
        lastMeasurements.oxygenSaturation = latest.numericValue;

        if (latest.numericValue <= this.config.vitals.oxygen.low) {
          flags.push('OXYGEN_LOW');
          flagDetails.push({
            flag: 'OXYGEN_LOW',
            value: latest.numericValue,
            threshold: this.config.vitals.oxygen.low,
            severity: latest.numericValue <= 88 ? 'high' : latest.numericValue <= 90 ? 'medium' : 'low',
          });
        }
      }
    }

    return {
      lastMeasurements,
      flags,
      flagDetails,
    };
  }

  /**
   * Analisa os exames
   */
  private analyzeExams(exams: ExamRecord[]): ExamsAnalysis {
    const now = new Date();
    const recentExams: ExamsAnalysis['recentExams'] = [];
    let pendingExams = 0;
    let overdueExams = 0;
    let completedExams = 0;

    // Ordenar por data (mais recentes primeiro)
    const sortedExams = [...exams].sort((a, b) => {
      const dateA = a.completedAt || a.scheduledAt || a.createdAt;
      const dateB = b.completedAt || b.scheduledAt || b.createdAt;
      return new Date(dateB).getTime() - new Date(dateA).getTime();
    });

    // Pegar os 5 mais recentes
    const recentCount = Math.min(5, sortedExams.length);

    for (let i = 0; i < recentCount; i++) {
      const exam = sortedExams[i];
      const summary: ExamsAnalysis['recentExams'][0] = {
        type: exam.type,
        status: exam.status,
      };

      if (exam.resultAt) {
        summary.resultAt = exam.resultAt.toISOString();
      }

      if (exam.result) {
        summary.summary = exam.result.substring(0, 100); // Limitar tamanho
      }

      if (exam.scheduledAt) {
        summary.scheduledAt = exam.scheduledAt.toISOString();

        // Calcular atraso
        if (exam.status === 'scheduled' || exam.status === 'pending_results') {
          const daysDiff = Math.floor(
            (now.getTime() - new Date(exam.scheduledAt).getTime()) / (1000 * 60 * 60 * 24)
          );

          if (daysDiff > 0) {
            summary.daysOverdue = daysDiff;
          }
        }
      }

      recentExams.push(summary);
    }

    // Contar exames por status
    for (const exam of exams) {
      if (exam.status === 'completed') {
        completedExams++;
      } else if (exam.status === 'scheduled' || exam.status === 'pending_results') {
        pendingExams++;

        // Verificar se está atrasado
        if (exam.scheduledAt) {
          const daysDiff = Math.floor(
            (now.getTime() - new Date(exam.scheduledAt).getTime()) / (1000 * 60 * 60 * 24)
          );

          if (daysDiff > this.config.exams.overdueDays) {
            overdueExams++;
          }
        }
      }
    }

    return {
      recentExams,
      pendingExams,
      overdueExams,
      completedExams,
    };
  }

  /**
   * Calcula o score de risco baseado nas análises
   */
  private calculateRiskScore(
    adherence: AdherenceAnalysis,
    vitals: VitalsAnalysis,
    exams: ExamsAnalysis
  ): RiskScore {
    let score = 0;
    const reasons: string[] = [];

    // Adesão
    if (adherence.adherenceStatus === 'bad') {
      score += this.config.adherence.badWeight;
      reasons.push(
        `Baixa adesão aos medicamentos (${adherence.adherenceRate.toFixed(1)}%) nos últimos 30 dias`
      );
    } else if (adherence.adherenceStatus === 'medium') {
      score += this.config.adherence.mediumWeight;
      reasons.push(
        `Adesão aos medicamentos pode melhorar (${adherence.adherenceRate.toFixed(1)}%)`
      );
    }

    // Sinais vitais
    for (const detail of vitals.flagDetails) {
      switch (detail.flag) {
        case 'PRESSURE_HIGH':
          score += this.config.vitals.pressure.weight * (detail.severity === 'high' ? 1.5 : 1);
          reasons.push(`Pressão arterial frequentemente elevada (${detail.value} mmHg)`);
          break;
        case 'PRESSURE_LOW':
          score += this.config.vitals.pressure.weight;
          reasons.push(`Pressão arterial frequentemente baixa (${detail.value} mmHg)`);
          break;
        case 'GLUCOSE_HIGH':
          score += this.config.vitals.glucose.weight * (detail.severity === 'high' ? 1.5 : 1);
          reasons.push(`Glicemia frequentemente elevada (${detail.value} mg/dL)`);
          break;
        case 'GLUCOSE_LOW':
          score += this.config.vitals.glucose.weight * 1.5; // Hipoglicemia é mais grave
          reasons.push(`Episódios de hipoglicemia detectados (${detail.value} mg/dL)`);
          break;
        case 'HEART_RATE_HIGH':
          score += this.config.vitals.heartRate.weight;
          reasons.push(`Frequência cardíaca elevada (${detail.value} bpm)`);
          break;
        case 'HEART_RATE_LOW':
          score += this.config.vitals.heartRate.weight;
          reasons.push(`Frequência cardíaca baixa (${detail.value} bpm)`);
          break;
        case 'TEMPERATURE_HIGH':
          score += this.config.vitals.temperature.weight;
          reasons.push(`Febre detectada (${detail.value}°C)`);
          break;
        case 'TEMPERATURE_LOW':
          score += this.config.vitals.temperature.weight;
          reasons.push(`Hipotermia detectada (${detail.value}°C)`);
          break;
        case 'OXYGEN_LOW':
          score += this.config.vitals.oxygen.weight * (detail.severity === 'high' ? 1.5 : 1);
          reasons.push(`Saturação de oxigênio baixa (${detail.value}%)`);
          break;
      }
    }

    // Exames
    if (exams.overdueExams > 0) {
      score += this.config.exams.overdueWeight * exams.overdueExams;
      reasons.push(
        `${exams.overdueExams} exame(s) atrasado(s) há mais de ${this.config.exams.overdueDays} dias`
      );
    }

    if (exams.pendingExams > 3) {
      score += this.config.exams.pendingWeight;
      reasons.push(`${exams.pendingExams} exames pendentes requerem atenção`);
    }

    // Limitar score entre 0 e 100
    score = Math.min(100, Math.max(0, score));

    // Determinar nível de risco
    let level: RiskLevel;
    if (score <= this.config.riskLevels.lowMax) {
      level = 'low';
    } else if (score <= this.config.riskLevels.moderateMax) {
      level = 'moderate';
    } else {
      level = 'high';
    }

    return {
      value: Math.round(score * 100) / 100,
      level,
      reasons,
    };
  }

  /**
   * Gera recomendações baseadas nas análises
   */
  private generateRecommendations(
    adherence: AdherenceAnalysis,
    vitals: VitalsAnalysis,
    exams: ExamsAnalysis,
    riskScore: RiskScore
  ): string[] {
    const recommendations: string[] = [];

    // Recomendações de adesão
    if (adherence.adherenceStatus === 'bad') {
      recommendations.push(
        'Refoccar estratégias de adesão: revisar horários de medicação, verificar suporte do cuidador e avaliar possíveis barreiras.'
      );
      recommendations.push(
        'Configurar lembretes mais frequentes para o paciente e notificar o cuidador sobre medicações perdidas.'
      );
    } else if (adherence.adherenceStatus === 'medium') {
      recommendations.push(
        'Reforçar a importância da adesão ao tratamento com o paciente e cuidador.'
      );
    }

    // Recomendações de sinais vitais
    const hasHighPressure = vitals.flags.includes('PRESSURE_HIGH');
    const hasLowPressure = vitals.flags.includes('PRESSURE_LOW');
    const hasHighGlucose = vitals.flags.includes('GLUCOSE_HIGH');
    const hasLowGlucose = vitals.flags.includes('GLUCOSE_LOW');
    const hasOxygenIssue = vitals.flags.includes('OXYGEN_LOW');

    if (hasHighPressure) {
      const detail = vitals.flagDetails.find((d) => d.flag === 'PRESSURE_HIGH');
      if (detail && detail.severity === 'high') {
        recommendations.push(
          'URGENTE: Pressão arterial muito elevada. Avaliar necessidade de ajuste imediato da medicação anti-hipertensiva com o médico responsável.'
        );
      } else {
        recommendations.push(
          'Avaliar ajuste da medicação anti-hipertensiva com o profissional responsável e intensificar monitorização.'
        );
      }
    }

    if (hasLowPressure) {
      recommendations.push(
        'Investigar causas de hipotensão: verificar hidratação, ajustar medicação se necessário.'
      );
    }

    if (hasHighGlucose) {
      recommendations.push(
        'Glicemia acima da meta: revisar medicação antidiabética, reforçar orientações de dieta e atividade física.'
      );
      recommendations.push(
        'Intensificar frequência de monitorização glicêmica e considerar consulta com endocrinologista.'
      );
    }

    if (hasLowGlucose) {
      const detail = vitals.flagDetails.find((d) => d.flag === 'GLUCOSE_LOW');
      if (detail && detail.severity === 'high') {
        recommendations.push(
          'URGENTE: Episódios de hipoglicemia grave detectados. Revisar imediatamente doses de medicação e horários de alimentação.'
        );
      } else {
        recommendations.push(
          'Atenção aos episódios de hipoglicemia: ajustar doses de medicação e revisar padrão alimentar.'
        );
      }
    }

    if (hasOxygenIssue) {
      recommendations.push(
        'Saturação de oxigênio baixa: avaliar necessidade de oxigenioterapia e investigar causas respiratórias ou cardíacas.'
      );
    }

    // Recomendações de exames
    if (exams.overdueExams > 0) {
      recommendations.push(
        `Reagendar ${exams.overdueExams} exame(s) atrasado(s) o mais breve possível e revisar resultados anteriores.`
      );
    }

    if (exams.pendingExams > 3) {
      recommendations.push(
        'Organizar agenda de exames pendentes para melhor acompanhamento clínico.'
      );
    }

    // Recomendações baseadas no score de risco
    if (riskScore.level === 'high') {
      recommendations.push(
        'RISCO ALTO: Agendar consulta presencial urgente para reavaliação completa do quadro clínico.'
      );
      recommendations.push(
        'Considerar intensificar acompanhamento com visitas domiciliares ou telemedicina mais frequentes.'
      );
    } else if (riskScore.level === 'moderate') {
      recommendations.push(
        'Risco moderado: agendar consulta de acompanhamento nas próximas 2 semanas.'
      );
    }

    // Se não houver problemas significativos
    if (recommendations.length === 0) {
      recommendations.push(
        'Paciente apresenta boa adesão e sinais vitais dentro dos parâmetros. Manter acompanhamento de rotina.'
      );
    }

    return recommendations;
  }

  /**
   * Agrupa sinais vitais por tipo
   */
  private groupVitalsByType(vitals: VitalRecord[]): Record<string, VitalRecord[]> {
    const grouped: Record<string, VitalRecord[]> = {};

    for (const vital of vitals) {
      if (!grouped[vital.type]) {
        grouped[vital.type] = [];
      }
      grouped[vital.type].push(vital);
    }

    // Ordenar cada grupo por data (mais recentes primeiro)
    for (const type in grouped) {
      grouped[type].sort(
        (a, b) => new Date(b.recordedAt).getTime() - new Date(a.recordedAt).getTime()
      );
    }

    return grouped;
  }
}

// Exportar instância singleton
export const aiService = new AIService();
