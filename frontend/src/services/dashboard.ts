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

export interface AlertStats {
  firingCount: number;
  resolvedCount: number;
  recentAlerts: RecentAlert[];
}

export interface RecentAlert {
  alertname: string;
  severity: string;
  status: string;
  startsAt: string | null;
  instance: string | null;
}

export interface ItFeedbackStats {
  pendingCount: number;
  handlingCount: number;
  resolvedCount: number;
}

export interface AssetStats {
  totalCount: number;
  serverCount: number;
  domainCount: number;
  terminalCount: number;
}

export interface CertStats {
  totalCount: number;
  validCount: number;
  expiringCount: number;
  expiredCount: number;
}

export interface RecentDeployment {
  projectName: string;
  environment: string;
  status: string;
  createdAt: string | null;
}

export interface DashboardOverview {
  alertStats: AlertStats;
  itFeedbackStats: ItFeedbackStats;
  assetStats: AssetStats;
  certStats: CertStats;
  recentDeployments: RecentDeployment[];
}

export const dashboardApi = {
  getMyTerminalMetrics: async (): Promise<MyTerminalMetricsResponse> => {
    const response = await api.get<MyTerminalMetricsResponse>('/dashboard/my-terminal-metrics');
    return response.data;
  },
  getOverview: async (): Promise<DashboardOverview> => {
    const response = await api.get<DashboardOverview>('/dashboard/overview');
    return response.data;
  },
};
