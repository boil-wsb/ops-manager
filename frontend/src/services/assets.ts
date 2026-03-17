import api from './api';
import type { PaginationData, Asset, Label } from '../types';

export const assetApi = {
  getAssets: async (params?: {
    skip?: number;
    limit?: number;
    assetType?: string;
    status?: string;
    idc?: string;
    keyword?: string;
  }): Promise<PaginationData<Asset>> => {
    const response = await api.get<{data: PaginationData<Asset>}>('/assets', { params });
    return response.data.data;
  },

  getAsset: async (id: number): Promise<Asset> => {
    const response = await api.get<Asset>(`/assets/${id}`);
    return response.data;
  },

  createAsset: async (data: Partial<Asset>): Promise<Asset> => {
    const response = await api.post<Asset>('/assets', data);
    return response.data;
  },

  updateAsset: async (id: number, data: Partial<Asset>): Promise<Asset> => {
    const response = await api.put<Asset>(`/assets/${id}`, data);
    return response.data;
  },

  deleteAsset: async (id: number): Promise<void> => {
    await api.delete(`/assets/${id}`);
  },

  // Labels
  getLabels: async (): Promise<Label[]> => {
    const response = await api.get<Label[]>('/labels');
    return response.data;
  },

  createLabel: async (data: Partial<Label>): Promise<Label> => {
    const response = await api.post<Label>('/labels', data);
    return response.data;
  },

  deleteLabel: async (id: number): Promise<void> => {
    await api.delete(`/labels/${id}`);
  },

  // Prometheus Sync
  syncAssetsFromPrometheus: async (): Promise<{ message: string; taskId: string; status: string }> => {
    const response = await api.post<{ message: string; task_id: string; status: string }>('/assets/sync');
    const data = response.data;
    return {
      message: data.message,
      taskId: data.task_id,
      status: data.status,
    };
  },

  discoverPrometheusAssets: async (): Promise<{
    total: number;
    discovered: number;
    existing: number;
    nodes: Array<{
      instance: string;
      ipAddress: string;
      nodename: string;
      sysname: string;
      release: string;
      machine: string;
      job: string;
      env: string;
    }>;
  }> => {
    const response = await api.get<{
      total: number;
      discovered: number;
      existing: number;
      nodes: Array<{
        instance: string;
        ip_address: string;
        nodename: string;
        sysname: string;
        release: string;
        machine: string;
        job: string;
        env: string;
      }>;
    }>('/assets/discovery');
    const data = response.data;
    return {
      total: data.total,
      discovered: data.discovered,
      existing: data.existing,
      nodes: data.nodes.map((node) => ({
        instance: node.instance,
        ipAddress: node.ip_address,
        nodename: node.nodename,
        sysname: node.sysname,
        release: node.release,
        machine: node.machine,
        job: node.job,
        env: node.env,
      })),
    };
  },

  importPrometheusAsset: async (instance: string): Promise<{ message: string; action: string; asset: Asset }> => {
    const encodedInstance = encodeURIComponent(instance);
    const response = await api.post<{ message: string; action: string; asset: Asset }>(`/assets/discovery/${encodedInstance}/import`);
    return response.data;
  },

  getAssetMetrics: async (id: number): Promise<{
    assetId: number;
    assetName: string;
    ipAddress: string;
    metrics: {
      cpu?: {
        usagePercent: number;
        cores: number;
      };
      memory?: {
        totalGB: number;
        usedGB: number;
        usagePercent: number;
      };
      disk?: {
        totalGB: number;
        usedGB: number;
        usagePercent: number;
      };
      network?: {
        receiveRate: number;
        transmitRate: number;
      };
    };
    timestamp: string;
  }> => {
    const response = await api.get<{
      asset_id: number;
      asset_name: string;
      ip_address: string;
      metrics: {
        cpu?: {
          usage_percent: number;
          cores: number;
        };
        memory?: {
          total_gb: number;
          used_gb: number;
          usage_percent: number;
        };
        disk?: {
          total_gb: number;
          used_gb: number;
          usage_percent: number;
        };
        network?: {
          receive_rate: number;
          transmit_rate: number;
        };
      };
      timestamp: string;
    }>(`/assets/${id}/metrics`);
    const data = response.data;
    return {
      assetId: data.asset_id,
      assetName: data.asset_name,
      ipAddress: data.ip_address,
      metrics: {
        cpu: data.metrics.cpu ? {
          usagePercent: data.metrics.cpu.usage_percent,
          cores: data.metrics.cpu.cores,
        } : undefined,
        memory: data.metrics.memory ? {
          totalGB: data.metrics.memory.total_gb,
          usedGB: data.metrics.memory.used_gb,
          usagePercent: data.metrics.memory.usage_percent,
        } : undefined,
        disk: data.metrics.disk ? {
          totalGB: data.metrics.disk.total_gb,
          usedGB: data.metrics.disk.usage_percent,
        } : undefined,
        network: data.metrics.network ? {
          receiveRate: data.metrics.network.receive_rate,
          transmitRate: data.metrics.network.transmit_rate,
        } : undefined,
      },
      timestamp: data.timestamp,
    };
  },

  // Terminal Assets
  getTerminals: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    keyword?: string;
  }): Promise<PaginationData<Asset>> => {
    const response = await api.get<{data: PaginationData<Asset>}>('/assets/terminals', { params });
    return response.data.data;
  },

  syncTerminalsFromPcInfo: async (): Promise<{
    message: string;
    totalDiscovered: number;
    synced: number;
    created: number;
    updated: number;
    errors: Array<{ hostname: string; error: string }>;
  }> => {
    const response = await api.post<{
      message: string;
      total_discovered: number;
      synced: number;
      created: number;
      updated: number;
      errors: Array<{ hostname: string; error: string }>;
    }>('/assets/sync-terminals');
    const data = response.data;
    return {
      message: data.message,
      totalDiscovered: data.total_discovered,
      synced: data.synced,
      created: data.created,
      updated: data.updated,
      errors: data.errors,
    };
  },
};
