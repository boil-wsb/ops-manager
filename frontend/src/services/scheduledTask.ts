import api from './api';

export interface ScheduledTaskListParams {
  skip?: number;
  limit?: number;
  name?: string;
  category?: string;
  isEnabled?: boolean;
  triggerType?: string;
}

export interface ScheduledTaskUpdateParams {
  name?: string;
  triggerConfig?: Record<string, unknown>;
  isEnabled?: boolean;
  description?: string;
}

export interface TaskExecutionLogListParams {
  skip?: number;
  limit?: number;
  status?: string;
}

export const scheduledTaskApi = {
  getScheduledTasks: async (params: ScheduledTaskListParams = {}) => {
    const response = await api.get('/scheduled-tasks', { params });
    return response.data;
  },

  getTaskNames: async () => {
    const response = await api.get('/scheduled-tasks/task-names');
    return response.data;
  },

  getScheduledTask: async (taskId: string) => {
    const response = await api.get(`/scheduled-tasks/${taskId}`);
    return response.data;
  },

  updateScheduledTask: async (taskId: string, data: ScheduledTaskUpdateParams) => {
    const response = await api.put(`/scheduled-tasks/${taskId}`, data);
    return response.data;
  },

  runScheduledTask: async (taskId: string) => {
    const response = await api.post(`/scheduled-tasks/${taskId}/run`);
    return response.data;
  },

  getTaskExecutionLogs: async (taskId: string, params: TaskExecutionLogListParams = {}) => {
    const response = await api.get(`/scheduled-tasks/${taskId}/logs`, { params });
    return response.data;
  },
};
