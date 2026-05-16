import api from './api';

export interface SystemConfig {
  id: number;
  key: string;
  value: string;
  group: string;
  description: string | null;
  isSecret: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SystemConfigListParams {
  skip?: number;
  limit?: number;
  group?: string;
  key?: string;
}

export interface SystemConfigCreateParams {
  key: string;
  value: string;
  group: string;
  description?: string;
  isSecret?: boolean;
}

export interface SystemConfigUpdateParams {
  value?: string;
  description?: string;
  isSecret?: boolean;
}

export const systemConfigApi = {
  getSystemConfigs: async (params: SystemConfigListParams = {}) => {
    const response = await api.get('/system-configs', { params });
    return response.data;
  },

  getConfigGroups: async () => {
    const response = await api.get('/system-configs/groups');
    return response.data as string[];
  },

  getSystemConfig: async (configKey: string) => {
    const response = await api.get(`/system-configs/${configKey}`);
    return response.data;
  },

  createSystemConfig: async (data: SystemConfigCreateParams) => {
    const response = await api.post('/system-configs', data);
    return response.data;
  },

  updateSystemConfig: async (configKey: string, data: SystemConfigUpdateParams) => {
    const response = await api.put(`/system-configs/${configKey}`, data);
    return response.data;
  },

  deleteSystemConfig: async (configKey: string) => {
    const response = await api.delete(`/system-configs/${configKey}`);
    return response.data;
  },
};
