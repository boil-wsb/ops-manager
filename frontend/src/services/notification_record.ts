import api from './api';

export interface NotificationRecord {
  id: number;
  user: string;
  matchedUser?: string;
  feishuOpenId?: string;
  chatId?: string;
  receiveType: string;
  callbackId?: string;
  cardContent?: Record<string, unknown>;
  messageId?: string;
  success: boolean;
  error?: string;
  createdAt: string;
}

export interface NotificationRecordListResponse {
  total: number;
  items: NotificationRecord[];
}

export const notificationRecordApi = {
  getNotificationRecords: (params?: {
    user?: string;
    success?: boolean;
    page?: number;
    page_size?: number;
  }) => api.get<NotificationRecordListResponse>('/notification-records', { params }),

  getNotificationRecord: (id: number) =>
    api.get<NotificationRecord>(`/notification-records/${id}`),

  deleteNotificationRecord: (id: number) =>
    api.delete(`/notification-records/${id}`),
};
