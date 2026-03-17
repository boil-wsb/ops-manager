import api from './api';
import type { ApiResponse, PaginationData, User } from '../types';

export interface UserListParams {
  page?: number;
  page_size?: number;
  keyword?: string;
  is_active?: boolean;
}

export const userApi = {
  getUsers: async (params?: UserListParams): Promise<PaginationData<User>> => {
    const response = await api.get<PaginationData<User>>('/users', { params });
    // 后端直接返回 { items, total, page, page_size } 格式
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
    await api.post(`/users/${id}/roles`, { role_ids: roleIds });
  },
};
