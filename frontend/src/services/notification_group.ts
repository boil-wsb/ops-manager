import api from './api';

export interface UserBrief {
  id: number;
  username: string;
  fullName?: string;
  feishuOpenId?: string;
}

export interface NotificationGroup {
  id: number;
  name: string;
  description?: string;
  notificationType: string;
  isActive: boolean;
  members: UserBrief[];
  createdAt: string;
  updatedAt: string;
}

export interface NotificationGroupListResponse {
  items: NotificationGroup[];
  total: number;
}

export interface NotificationGroupCreate {
  name: string;
  description?: string;
  notificationType: string;
  isActive?: boolean;
}

export interface NotificationGroupUpdate {
  name?: string;
  description?: string;
  notificationType?: string;
  isActive?: boolean;
}

export const notificationGroupApi = {
  getGroups: async (params?: {
    notificationType?: string;
    isActive?: boolean;
    page?: number;
    pageSize?: number;
  }): Promise<NotificationGroupListResponse> => {
    const response = await api.get('/notification-groups', { params });
    return response.data;
  },

  getGroup: async (id: number): Promise<NotificationGroup> => {
    const response = await api.get(`/notification-groups/${id}`);
    return response.data;
  },

  createGroup: async (data: NotificationGroupCreate): Promise<NotificationGroup> => {
    const response = await api.post('/notification-groups', data);
    return response.data;
  },

  updateGroup: async (id: number, data: NotificationGroupUpdate): Promise<NotificationGroup> => {
    const response = await api.put(`/notification-groups/${id}`, data);
    return response.data;
  },

  deleteGroup: async (id: number): Promise<void> => {
    await api.delete(`/notification-groups/${id}`);
  },

  addMember: async (groupId: number, userId: number): Promise<NotificationGroup> => {
    const response = await api.post(`/notification-groups/${groupId}/members/${userId}`);
    return response.data;
  },

  removeMember: async (groupId: number, userId: number): Promise<NotificationGroup> => {
    const response = await api.delete(`/notification-groups/${groupId}/members/${userId}`);
    return response.data;
  },
};