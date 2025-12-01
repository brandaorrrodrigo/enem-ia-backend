/**
 * App.ts - Example Integration
 * Exemplo de como integrar o módulo AI no servidor Express
 */

import express, { Application } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';

// Importar rotas dos módulos
import aiRoutes from './ai/ai.routes';
// import patientRoutes from './patients/patient.routes';
// import medicationRoutes from './medications/medication.routes';
// import reminderRoutes from './reminders/reminder.routes';
// import vitalRoutes from './vitals/vital.routes';
// import examRoutes from './exams/exam.routes';
// import caregiverRoutes from './caregivers/caregiver.routes';
// import professionalRoutes from './professionals/professional.routes';
// import notificationRoutes from './notifications/notification.routes';

const app: Application = express();

// ==================== MIDDLEWARES ====================

// Security
app.use(helmet());

// CORS
app.use(
  cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true,
  })
);

// Body parsing
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Logging
if (process.env.NODE_ENV !== 'test') {
  app.use(morgan('combined'));
}

// ==================== ROUTES ====================

// Health check
app.get('/health', (req, res) => {
  res.status(200).json({
    success: true,
    message: 'MedicControl API is running',
    timestamp: new Date().toISOString(),
  });
});

// API v1 Routes
const API_PREFIX = '/api/v1';

// AI Module Routes
app.use(`${API_PREFIX}/ai`, aiRoutes);

// Other module routes (exemplo)
// app.use(`${API_PREFIX}/patients`, patientRoutes);
// app.use(`${API_PREFIX}/medications`, medicationRoutes);
// app.use(`${API_PREFIX}/reminders`, reminderRoutes);
// app.use(`${API_PREFIX}/vitals`, vitalRoutes);
// app.use(`${API_PREFIX}/exams`, examRoutes);
// app.use(`${API_PREFIX}/caregivers`, caregiverRoutes);
// app.use(`${API_PREFIX}/professionals`, professionalRoutes);
// app.use(`${API_PREFIX}/notifications`, notificationRoutes);

// ==================== ERROR HANDLING ====================

// 404 Handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: 'Route not found',
    path: req.path,
  });
});

// Global Error Handler
app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Error:', err);

  const statusCode = err.statusCode || 500;
  const message = err.message || 'Internal Server Error';

  res.status(statusCode).json({
    success: false,
    message,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  });
});

export default app;
