import api from './api';
import type { ApiResponse, IpBindingListResponse, PaginationData, User } from '../types';

export interface UserListParams {
  page?: number;
  page_size?: number;
  keyword?: string;
  is_active?: boolean;
}

export const userApi = {
  getUsers: async (params?: UserListParams): Promise<PaginationData<User>> => {
    const response = await api.get<PaginationData<User>>('/users', { params });
    return response.data;
  },

  getUser: async (id: number): Promise<User> => {
    const response = await api.get<ApiResponse<User>>(`/users/${id}`);
    return response.data.data;
  },

  createUser: async (data: Partial<User> & { password: string }): Promise<User> => {
    const response = await api.post<ApiResponse<User>>('/users', data);
    return response.data.data;
  },

  updateUser: async (id: number, data: Partial<User>): Promise<User> => {
    const response = await api.put<ApiResponse<User>>(`/users/${id}`, data);
    return response.data.data;
  },

  deleteUser: async (id: number): Promise<void> => {
    await api.delete(`/users/${id}`);
  },

  resetPassword: async (id: number, newPassword: string): Promise<void> => {
    await api.post(`/users/${id}/reset-password`, { new_password: newPassword });
  },

  assignRoles: async (id: number, roleIds: number[]): Promise<void> => {
    await api.post(`/users/${id}/roles`, roleIds);
  },

  sendMessage: async (id: number, message: string): Promise<{ success: boolean; message_id?: string }> => {
    const response = await api.post<ApiResponse<{ success: boolean; message_id?: string }>>(`/users/${id}/send-message`, { message });
    return response.data.data;
  },

  getIpBindings: async (): Promise<IpBindingListResponse> => {
    const response = await api.get<IpBindingListResponse>('/users/ip-bindings');
    return response.data;
  },

  unbindIp: async (userId: number): Promise<{ message: string; userId: number }> => {
    const response = await api.delete<{ message: string; userId: number }>(`/users/${userId}/ip-binding`);
    return response.data;
  },
};
