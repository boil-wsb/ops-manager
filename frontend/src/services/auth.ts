import api from './api';
import type { ApiResponse, LoginCredentials, TokenResponse, User } from '../types';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const response = await api.post<ApiResponse<TokenResponse>>('/auth/login', credentials);
    return response.data.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },

  refreshToken: async (): Promise<TokenResponse> => {
    const response = await api.post<ApiResponse<TokenResponse>>('/auth/refresh');
    return response.data.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<ApiResponse<User>>('/auth/me');
    return response.data.data;
  },
};
