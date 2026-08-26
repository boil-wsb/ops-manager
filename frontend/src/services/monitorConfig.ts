import api from './api';

export interface MonitorHost {
  file: 'linux' | 'windows';
  filename: string;
  index: number;
  ip: string;
  port: string;
  env: string;
  job: string;
  instance: string;
  raw?: Record<string, unknown>;
}

export interface GitRepoStatus {
  cloned: boolean;
  branch?: string;
  head?: string;
  dirty?: boolean;
}

export interface GitSyncStatus {
  cloned?: boolean;
  branch?: string | null;
  ahead?: number;
  behind?: number;
  local_newer?: boolean;
  remote_newer?: boolean;
  is_synced?: boolean;
  dirty?: boolean;
  checked_at?: string;
}

export interface HostPayload {
  file: 'linux' | 'windows';
  index?: number;
  ip: string;
  port: string;
  env?: string;
  job?: string;
  instance?: string;
  labels?: Record<string, string>;
}

export interface OperationResult {
  message?: string;
}

export interface PendingOp {
  type: string;
  file: string;
  addr: string;
}

export const monitorConfigApi = {
  getHosts: async (): Promise<MonitorHost[]> => {
    const response = await api.get<{ data: MonitorHost[] }>('/monitor-config/hosts');
    return response.data.data;
  },

  getPending: async (): Promise<PendingOp[]> => {
    const response = await api.get<{ data: PendingOp[] }>('/monitor-config/pending');
    return response.data.data;
  },

  addHost: async (payload: HostPayload): Promise<OperationResult> => {
    const response = await api.post<{ data: OperationResult }>('/monitor-config/hosts', payload);
    return response.data.data;
  },

  updateHost: async (payload: HostPayload): Promise<OperationResult> => {
    const response = await api.put<{ data: OperationResult }>('/monitor-config/hosts', payload);
    return response.data.data;
  },

  commit: async (message?: string): Promise<OperationResult> => {
    const response = await api.post<{ data: OperationResult }>('/monitor-config/commit', {
      message: message || '',
    });
    return response.data.data;
  },

  push: async (): Promise<OperationResult> => {
    const response = await api.post<{ data: OperationResult }>('/monitor-config/push');
    return response.data.data;
  },

  getGitStatus: async (): Promise<GitRepoStatus> => {
    const response = await api.get<{ data: GitRepoStatus }>('/git-repos/status');
    return response.data.data;
  },

  getSync: async (): Promise<GitSyncStatus> => {
    const response = await api.get<{ data: GitSyncStatus }>('/git-repos/sync');
    return response.data.data;
  },
};