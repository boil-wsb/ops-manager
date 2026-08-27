import api from './api';
import type { LoginCredentials, User } from '../types';

interface TokenResponseBackend {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  permissions: string[];
  permissionVersion: string;
  user?: {
    id: number;
    username: string;
    email?: string;
    fullName?: string;
    isActive: boolean;
    isSuperuser: boolean;
    lastLogin?: string;
    createdAt: string;
    updatedAt: string;
    permissions: string[];
    roles: { id: number; name: string }[];
  };
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  permissions: string[];
  permissionVersion: string;
  user?: User;
}

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
    return {
      accessToken: data.accessToken,
      refreshToken: data.refreshToken,
      tokenType: data.tokenType,
      expiresIn: data.expiresIn,
      permissions: data.permissions || [],
      permissionVersion: data.permissionVersion || '',
      user: data.user ? {
        id: data.user.id,
        username: data.user.username,
        email: data.user.email,
        fullName: data.user.fullName,
        isActive: data.user.isActive,
        isSuperuser: data.user.isSuperuser,
        lastLogin: data.user.lastLogin,
        createdAt: data.user.createdAt,
        updatedAt: data.user.updatedAt,
        permissions: data.user.permissions || [],
        permissionVersion: data.permissionVersion || '',
        roles: data.user.roles || [],
      } : undefined,
    };
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },

  refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await api.post<TokenResponseBackend>('/auth/refresh', null, {
      params: { refresh_token: refreshToken },
    });
    const data = response.data;
    return {
      accessToken: data.accessToken,
      refreshToken: data.refreshToken,
      tokenType: data.tokenType,
      expiresIn: data.expiresIn,
      permissions: data.permissions || [],
      permissionVersion: data.permissionVersion || '',
    };
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<UserResponseBackend>('/auth/me');
    const data = response.data as unknown as {
      id: number;
      username: string;
      email?: string;
      fullName?: string;
      isActive: boolean;
      isSuperuser: boolean;
      lastLogin?: string;
      createdAt: string;
      updatedAt: string;
      permissions?: string[];
      permissionVersion?: string;
    };
    return {
      id: data.id,
      username: data.username,
      email: data.email,
      fullName: data.fullName,
      isActive: data.isActive,
      isSuperuser: data.isSuperuser,
      lastLogin: data.lastLogin,
      createdAt: data.createdAt,
      updatedAt: data.updatedAt,
      permissions: data.permissions || [],
      permissionVersion: data.permissionVersion || '',
    };
  },
};
