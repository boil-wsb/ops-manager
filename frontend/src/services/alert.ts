import api from './api';
import type {
  AlertReceiver,
  AlertReceiverCreate,
  AlertReceiverUpdate,
  AlertSilence,
  AlertSilenceCreate,
  AlertSilenceUpdate,
  AlertTemplate,
  AlertTemplateCreate,
  AlertTemplateUpdate,
  AlertTemplatePreview,
  AlertHistory,
  AlertHistoryListParams,
  PaginationParams,
} from '../types/alert';

interface PaginatedResponse<T> {
  total: number;
  items: T[];
}

const alertApi = {
  // ============ 接收配置 ============
  getReceivers: async (params: PaginationParams): Promise<PaginatedResponse<AlertReceiver>> => {
    const skip = (params.page - 1) * params.pageSize;
    const response = await api.get('/alert/receivers', {
      params: { skip, limit: params.pageSize },
    });
    return response.data;
  },

  getReceiver: async (id: number): Promise<AlertReceiver> => {
    const response = await api.get(`/alert/receivers/${id}`);
    return response.data;
  },

  createReceiver: async (data: AlertReceiverCreate): Promise<AlertReceiver> => {
    const response = await api.post('/alert/receivers', data);
    return response.data;
  },

  updateReceiver: async (id: number, data: AlertReceiverUpdate): Promise<AlertReceiver> => {
    const response = await api.put(`/alert/receivers/${id}`, data);
    return response.data;
  },

  deleteReceiver: async (id: number): Promise<void> => {
    await api.delete(`/alert/receivers/${id}`);
  },

  testReceiver: async (id: number): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`/alert/receivers/${id}/test`);
    return response.data;
  },

  // ============ 抑制规则 ============
  getSilences: async (params: PaginationParams): Promise<PaginatedResponse<AlertSilence>> => {
    const skip = (params.page - 1) * params.pageSize;
    const response = await api.get('/alert/silences', {
      params: { skip, limit: params.pageSize },
    });
    return response.data;
  },

  getSilence: async (id: number): Promise<AlertSilence> => {
    const response = await api.get(`/alert/silences/${id}`);
    return response.data;
  },

  createSilence: async (data: AlertSilenceCreate): Promise<AlertSilence> => {
    const response = await api.post('/alert/silences', data);
    return response.data;
  },

  updateSilence: async (id: number, data: AlertSilenceUpdate): Promise<AlertSilence> => {
    const response = await api.put(`/alert/silences/${id}`, data);
    return response.data;
  },

  deleteSilence: async (id: number): Promise<void> => {
    await api.delete(`/alert/silences/${id}`);
  },

  // ============ 模板 ============
  getTemplates: async (params: PaginationParams): Promise<PaginatedResponse<AlertTemplate>> => {
    const skip = (params.page - 1) * params.pageSize;
    const response = await api.get('/alert/templates', {
      params: { skip, limit: params.pageSize },
    });
    const items = response.data;
    const total = Array.isArray(items) ? items.length : 0;
    return { total, items: items || [] };
  },

  getTemplate: async (id: number): Promise<AlertTemplate> => {
    const response = await api.get(`/alert/templates/${id}`);
    return response.data;
  },

  createTemplate: async (data: AlertTemplateCreate): Promise<AlertTemplate> => {
    const response = await api.post('/alert/templates', data);
    return response.data;
  },

  updateTemplate: async (id: number, data: AlertTemplateUpdate): Promise<AlertTemplate> => {
    const response = await api.put(`/alert/templates/${id}`, data);
    return response.data;
  },

  deleteTemplate: async (id: number): Promise<void> => {
    await api.delete(`/alert/templates/${id}`);
  },

  previewTemplate: async (
    id: number,
    data: AlertTemplatePreview
  ): Promise<{ subject?: string; body: string }> => {
    const response = await api.post(`/alert/templates/${id}/preview`, data);
    return response.data;
  },

  // ============ 告警历史 ============
  getAlertHistory: async (
    params: AlertHistoryListParams
  ): Promise<PaginatedResponse<AlertHistory>> => {
    const { page, pageSize, status, severity, startTime, endTime, alertname } = params;
    const queryParams: Record<string, unknown> = { page, page_size: pageSize };
    if (status) queryParams.status = status;
    if (severity) queryParams.severity = severity;
    if (startTime) queryParams.start_time = startTime;
    if (endTime) queryParams.end_time = endTime;
    if (alertname) queryParams.alertname = alertname;
    const response = await api.get('/alert/history', { params: queryParams });
    return response.data;
  },

  getAlertHistoryDetail: async (id: number): Promise<AlertHistory> => {
    const response = await api.get(`/alert/history/${id}`);
    return response.data;
  },

  // ============ 统计 ============
  getAlertStats: async (): Promise<{
    totalReceivers: number;
    activeReceivers: number;
    totalSilences: number;
    activeSilences: number;
    totalTemplates: number;
    activeTemplates: number;
    firingAlerts: number;
    resolvedAlerts: number;
  }> => {
    const response = await api.get('/alert/stats');
    return response.data;
  },
};

export default alertApi;
