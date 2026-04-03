import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../stores/authStore';
import { toSnakeCaseObj, toCamelCaseObj } from '../utils/transform';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

interface JwtPayload {
  exp: number;
  iat: number;
  sub: string;
  type: 'access' | 'refresh';
}

function parseJwt(token: string): JwtPayload | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

function isTokenExpiringSoon(token: string, thresholdMinutes: number = 5): boolean {
  const payload = parseJwt(token);
  if (!payload || !payload.exp) {
    return true;
  }
  const expirationTime = payload.exp * 1000;
  const currentTime = Date.now();
  const thresholdMs = thresholdMinutes * 60 * 1000;
  return expirationTime - currentTime < thresholdMs;
}

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

function processQueue(error: Error | null, token: string | null = null): void {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
}

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, updateToken } = useAuthStore.getState();

  if (!refreshToken) {
    processQueue(new Error('No refresh token') as AxiosError, null);
    return null;
  }

  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_URL || '/api/v1'}/auth/refresh`,
      null,
      {
        params: { refresh_token: refreshToken },
      }
    );

    const accessToken = response.data.access_token;
    const newRefreshToken = response.data.refresh_token;
    updateToken(accessToken, newRefreshToken);
    processQueue(null, accessToken);
    return accessToken;
  } catch (err) {
    processQueue(err as AxiosError, null);
    return null;
  }
}

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const { token, refreshToken } = useAuthStore.getState();

    if (config.url?.includes('/auth/refresh')) {
      return config;
    }

    if (token) {
      if (isTokenExpiringSoon(token, 5) && refreshToken) {
        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const newToken = await refreshAccessToken();
            if (newToken) {
              config.headers.Authorization = `Bearer ${newToken}`;
            } else {
              config.headers.Authorization = `Bearer ${token}`;
            }
          } finally {
            isRefreshing = false;
          }
        } else {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              if (token) {
                config.headers.Authorization = `Bearer ${token}`;
              }
              return config;
            })
            .catch(() => {
              return config;
            });
        }
      } else {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    if (config.data && typeof config.data === 'object') {
      config.data = toSnakeCaseObj(config.data as Record<string, unknown>);
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    if (response.data && typeof response.data === 'object' && !(response.data instanceof Blob)) {
      response.data = toCamelCaseObj(response.data as Record<string, unknown>);
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && originalRequest) {
      if (originalRequest._retry) {
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const newToken = await refreshAccessToken();

        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        } else {
          useAuthStore.getState().clearAuth();
          window.location.href = '/login';
          return Promise.reject(error);
        }
      } catch (refreshError) {
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
