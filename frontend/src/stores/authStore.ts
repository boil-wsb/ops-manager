import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  permissions: string[];
  permissionVersion: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string, refreshToken: string, permissions?: string[], permissionVersion?: string | null) => void;
  setUser: (user: User) => void;
  updateToken: (token: string, refreshToken: string, permissions?: string[], permissionVersion?: string | null) => void;
  setPermissions: (permissions: string[], permissionVersion?: string | null) => void;
  clearAuth: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      refreshToken: null,
      permissions: [],
      permissionVersion: null,
      isAuthenticated: false,
      setAuth: (user, token, refreshToken, permissions = [], permissionVersion = null) =>
        set({
          user,
          token,
          refreshToken,
          permissions,
          permissionVersion,
          isAuthenticated: true,
        }),
      setUser: (user) =>
        set({
          user,
        }),
      updateToken: (token, refreshToken, permissions, permissionVersion) =>
        set((state) => ({
          token,
          refreshToken,
          permissions: permissions !== undefined ? permissions : state.permissions,
          permissionVersion: permissionVersion !== undefined ? permissionVersion : state.permissionVersion,
        })),
      setPermissions: (permissions, permissionVersion = null) =>
        set({
          permissions,
          permissionVersion,
        }),
      clearAuth: () =>
        set({
          user: null,
          token: null,
          refreshToken: null,
          permissions: [],
          permissionVersion: null,
          isAuthenticated: false,
        }),
      logout: () =>
        set({
          user: null,
          token: null,
          refreshToken: null,
          permissions: [],
          permissionVersion: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'auth-storage',
    }
  )
);
