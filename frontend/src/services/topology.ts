import api from './api';

// ====== Types ======

export type TopologyRelationType = 'CONNECTED' | 'LOCATED_IN' | 'CUSTOM';

export interface TopologyMetrics {
  cpu?: number | null;
  mem?: number | null;
  disk?: number | null;
  load1?: number | null;
  memoryTotalMb?: number | null;
  diskTotalGb?: number | null;
  hostStatus?: string | null;
  checkedAt?: string | null;
}

export interface TopologyLabel {
  id: number;
  name: string;
  color: string;
}

export interface TopologyNode {
  id: string;
  name: string;
  type: 'SERVER' | 'VM' | 'NETWORK' | 'STORAGE' | 'TERMINAL';
  status: string;
  ipAddress?: string | null;
  ownerName?: string | null;
  osType?: string | null;
  osVersion?: string | null;
  cpuCores?: number | null;
  memoryGb?: number | null;
  diskGb?: number | null;
  labels: TopologyLabel[];
  metrics: TopologyMetrics;
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  relationType: TopologyRelationType;
  autoInferred: boolean;
  label?: string | null;
  labelColor?: string | null;
}

export interface TopologyGroup {
  type: string;
  count: number;
}

export interface TopologyResponse {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  groups: TopologyGroup[];
}

// ====== API ======

export const topologyApi = {
  getTopology: async (params?: {
    assetType?: string;
    status?: string;
    refresh?: boolean;
  }): Promise<TopologyResponse> => {
    const response = await api.get<TopologyResponse>('/assets/topology', { params });
    return response.data;
  },
};
