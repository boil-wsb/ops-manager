import api from './api';

export interface SuggestionCreate {
  content: string;
  highlights?: string;
  innovationIdeas?: string;
  departmentId?: number | null;
  assigneeUserId?: number | null;
}

export interface SuggestionSubmitResponse {
  queryCode: string;
  message: string;
}

export interface AssignmentInfo {
  id: number;
  suggestionId: number;
  departmentId: number | null;
  departmentName: string | null;
  assigneeUserId: number | null;
  assigneeName: string | null;
  assigneeOpenId: string | null;
  openMessageId: string | null;
  status: string;
  reviewedAt: string | null;
  reviewComment: string | null;
}

export interface SuggestionInfo {
  id: number;
  content: string;
  highlights: string | null;
  innovationIdeas: string | null;
  status: string;
  queryCode: string;
  marketResult: string | null;
  archivedAt: string | null;
  rejectReason: string | null;
  rejectedAt: string | null;
  createdAt: string;
  assignments: AssignmentInfo[];
}

export interface SuggestionListResponse {
  total: number;
  items: SuggestionInfo[];
}

export interface SuggestionTrackResponse {
  status: string;
  statusText: string;
  createdAt: string;
  archivedAt: string | null;
  marketResult: string | null;
  rejectReason: string | null;
}

export interface MySuggestionCode {
  id: number;
  queryCode: string;
  status: string;
  createdAt: string;
  contentPreview: string;
}

export const suggestionApi = {
  submit: async (data: SuggestionCreate): Promise<SuggestionSubmitResponse> => {
    const response = await api.post<SuggestionSubmitResponse>('/suggestions', data);
    return response.data;
  },

  track: async (queryCode: string): Promise<SuggestionTrackResponse> => {
    const response = await api.get<SuggestionTrackResponse>(`/suggestions/track/${queryCode}`);
    return response.data;
  },

  getMyCodes: async (): Promise<{ items: MySuggestionCode[] }> => {
    const response = await api.get<{ items: MySuggestionCode[] }>('/suggestions/my-codes/list');
    return response.data;
  },

  getList: async (params?: {
    page?: number;
    pageSize?: number;
    status?: string;
  }): Promise<SuggestionListResponse> => {
    const response = await api.get<SuggestionListResponse>('/suggestions', { params });
    return response.data;
  },

  getDetail: async (id: number): Promise<SuggestionInfo> => {
    const response = await api.get<SuggestionInfo>(`/suggestions/${id}`);
    return response.data;
  },

  archive: async (id: number, marketResult: string): Promise<SuggestionInfo> => {
    const response = await api.put<SuggestionInfo>(`/suggestions/${id}/archive`, { marketResult });
    return response.data;
  },
};
