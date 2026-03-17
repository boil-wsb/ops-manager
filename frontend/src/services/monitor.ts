import api from './api';
import type { Monitor, Alert, AlertRule, NotificationChannel } from '../types';

export interface MonitorListParams {
  skip?: number;
  limit?: number;
  monitor_type?: string;
  status?: string;
  is_enabled?: boolean;
}

export interface AlertListParams {
  skip?: number;
  limit?: number;
  status?: string;
  severity?: string;
  monitor_id?: number;
}

export const monitorApi = {
  getMonitors: async (params: MonitorListParams = {}) => {
    const response = await api.get('/monitor/monitors', { params });
    return response.data;
  },

  getMonitor: async (id: number) => {
    const response = await api.get(`/monitor/monitors/${id}`);
    return response.data;
  },

  createMonitor: async (data: Partial<Monitor>) => {
    const response = await api.post('/monitor/monitors', data);
    return response.data;
  },

  updateMonitor: async (id: number, data: Partial<Monitor>) => {
    const response = await api.put(`/monitor/monitors/${id}`, data);
    return response.data;
  },

  deleteMonitor: async (id: number) => {
    await api.delete(`/monitor/monitors/${id}`);
  },

  toggleMonitor: async (id: number) => {
    const response = await api.post(`/monitor/monitors/${id}/toggle`);
    return response.data;
  },

  getAlerts: async (params: AlertListParams = {}) => {
    const response = await api.get('/monitor/alerts', { params });
    return response.data;
  },

  getAlert: async (id: number) => {
    const response = await api.get(`/monitor/alerts/${id}`);
    return response.data;
  },

  alertAction: async (id: number, action: 'acknowledge' | 'resolve' | 'suppress') => {
    const response = await api.post(`/monitor/alerts/${id}/action`, { action });
    return response.data;
  },

  getAlertRules: async (params: { skip?: number; limit?: number; is_enabled?: boolean } = {}) => {
    const response = await api.get('/monitor/alert-rules', { params });
    return response.data;
  },

  createAlertRule: async (data: Partial<AlertRule>) => {
    const response = await api.post('/monitor/alert-rules', data);
    return response.data;
  },

  updateAlertRule: async (id: number, data: Partial<AlertRule>) => {
    const response = await api.put(`/monitor/alert-rules/${id}`, data);
    return response.data;
  },

  deleteAlertRule: async (id: number) => {
    await api.delete(`/monitor/alert-rules/${id}`);
  },

  getNotificationChannels: async (params: { skip?: number; limit?: number } = {}) => {
    const response = await api.get('/monitor/notification-channels', { params });
    return response.data;
  },

  createNotificationChannel: async (data: Partial<NotificationChannel>) => {
    const response = await api.post('/monitor/notification-channels', data);
    return response.data;
  },

  updateNotificationChannel: async (id: number, data: Partial<NotificationChannel>) => {
    const response = await api.put(`/monitor/notification-channels/${id}`, data);
    return response.data;
  },

  deleteNotificationChannel: async (id: number) => {
    await api.delete(`/monitor/notification-channels/${id}`);
  },

  testNotificationChannel: async (id: number) => {
    const response = await api.post(`/monitor/notification-channels/${id}/test`);
    return response.data;
  },
};
