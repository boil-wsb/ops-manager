import api from './api';

export interface TerminalMetricSummary {
  totalCount: number;
  onlineCount: number;
  offlineCount: number;
  alertCount: number;
  avgCpuUsage: number;
  avgMemoryUsage: number;
  avgDiskUsage: number;
}

export interface TerminalMetric {
  id: number;
  assetId: number;
  hostname: string;
  ipAddress: string | null;
  cpuUsage: number | null;
  memoryUsage: number | null;
  diskUsage: number | null;
  memoryTotalGb: number | null;
  diskTotalGb: number | null;
  networkIn: number | null;
  networkOut: number | null;
  uptimeHours: number | null;
  currentStatus: 'online' | 'offline' | 'unknown';
  alertCount: number;
  alertSeverity: string | null;
  monitorName: string | null;
  lastHeartbeat: string | null;
}

export interface MyTerminalMetricsResponse {
  summary: TerminalMetricSummary;
  terminals: TerminalMetric[];
  lastSyncTime: string | null;
}

export const dashboardApi = {
  getMyTerminalMetrics: async (): Promise<MyTerminalMetricsResponse> => {
    const response = await api.get<MyTerminalMetricsResponse>('/dashboard/my-terminal-metrics');
    return response.data;
  },
};
