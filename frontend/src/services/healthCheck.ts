import api from './api';
import type { HealthCheckReport, HealthCheckThresholds, HealthCheckHistoryParams } from '../types/healthCheck';

export const healthCheckApi = {
  runHealthCheck: async (): Promise<HealthCheckReport> => {
    const response = await api.post('/health-check/run');
    return response.data;
  },

  getLatestReport: async (): Promise<HealthCheckReport | null> => {
    const response = await api.get('/health-check/latest');
    return response.data;
  },

  getReportHistory: async (params: HealthCheckHistoryParams = {}): Promise<{ items: HealthCheckReport[]; total: number; page: number; pageSize: number }> => {
    const response = await api.get('/health-check/history', { params });
    return response.data;
  },

  getReportById: async (reportId: number): Promise<HealthCheckReport> => {
    const response = await api.get(`/health-check/reports/${reportId}`);
    return response.data;
  },

  exportHtmlReport: async (reportId: number): Promise<string> => {
    const response = await api.get(`/health-check/reports/${reportId}/export/html`, { responseType: 'text' });
    return response.data;
  },

  exportExcelReport: async (reportId: number): Promise<Blob> => {
    const response = await api.get(`/health-check/reports/${reportId}/export/excel`, { responseType: 'blob' });
    return response.data;
  },

  getThresholds: async (): Promise<HealthCheckThresholds> => {
    const response = await api.get('/health-check/thresholds');
    return response.data;
  },

  updateThresholds: async (thresholds: Partial<HealthCheckThresholds>): Promise<HealthCheckThresholds> => {
    const response = await api.put('/health-check/thresholds', thresholds);
    return response.data;
  },
};
