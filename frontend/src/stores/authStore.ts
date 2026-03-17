import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  permissions: string[];
  isAuthenticated: boolean;
  setAuth: (user: User, token: string, refreshToken: string, permissions?: string[]) => void;
  setUser: (user: User) => void;
  updateToken: (token: string, refreshToken: string) => void;
  setPermissions: (permissions: string[]) => void;
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
      isAuthenticated: false,
      setAuth: (user, token, refreshToken, permissions = []) =>
        set({
          user,
          token,
          refreshToken,
          permissions,
          isAuthenticated: true,
        }),
      setUser: (user) =>
        set({
          user,
        }),
      updateToken: (token, refreshToken) =>
        set({
          token,
          refreshToken,
        }),
      setPermissions: (permissions) =>
        set({
          permissions,
        }),
      clearAuth: () =>
        set({
          user: null,
          token: null,
          refreshToken: null,
          permissions: [],
          isAuthenticated: false,
        }),
      logout: () =>
        set({
          user: null,
          token: null,
          refreshToken: null,
          permissions: [],
          isAuthenticated: false,
        }),
    }),
    {
      name: 'auth-storage',
    }
  )
);
