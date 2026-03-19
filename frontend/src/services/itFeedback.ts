import api from './api';

export interface ITFeedback {
  id: number;
  computerType: string;
  usageYears: string;
  lagLevel: string;
  lagScenarios?: string;
  description?: string;
  contact?: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
  notes?: string;
  clientIp?: string;
}

export interface ITFeedbackListResponse {
  total: number;
  items: ITFeedback[];
}

export interface ITFeedbackCreate {
  computerType: string;
  usageYears: string;
  lagLevel: string;
  lagScenarios?: string;
  description?: string;
  contact?: string;
  clientIp?: string;
}

export const itFeedbackApi = {
  getITFeedbackList: (params?: { status?: string; lagLevel?: string; page?: number; page_size?: number }) =>
    api.get<ITFeedbackListResponse>('/it-feedback', { params }),

  getITFeedback: (id: number) =>
    api.get<ITFeedback>(`/it-feedback/${id}`),

  createITFeedback: (data: ITFeedbackCreate) =>
    api.post<ITFeedback>('/it-feedback', data),

  resolveITFeedback: (id: number, resolvedBy: string, notes?: string) =>
    api.put<ITFeedback>(`/it-feedback/${id}/resolve`, { resolved_by: resolvedBy, notes }),

  deleteITFeedback: (id: number) =>
    api.delete(`/it-feedback/${id}`),
};
