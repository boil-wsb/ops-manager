import api from './api';
import type { LoginCredentials, User } from '../types';

// Backend returns snake_case, we need to transform to camelCase
interface TokenResponseBackend {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

// User response from backend (snake_case)
interface UserResponseBackend {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  last_login?: string;
  created_at: string;
  updated_at: string;
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const response = await api.post<TokenResponseBackend>('/auth/login', credentials);
    const data = response.data;
    // Transform snake_case to camelCase
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      tokenType: data.token_type,
      expiresIn: data.expires_in,
    };
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },

  refreshToken: async (): Promise<TokenResponse> => {
    const response = await api.post<TokenResponseBackend>('/auth/refresh');
    const data = response.data;
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      tokenType: data.token_type,
      expiresIn: data.expires_in,
    };
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<UserResponseBackend>('/auth/me');
    const data = response.data;
    // Transform snake_case to camelCase
    return {
      id: data.id,
      username: data.username,
      email: data.email,
      fullName: data.full_name,
      isActive: data.is_active,
      isSuperuser: data.is_superuser,
      lastLogin: data.last_login,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
    };
  },
};
