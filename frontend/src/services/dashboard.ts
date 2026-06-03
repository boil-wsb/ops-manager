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
  firing_count: number;
  resolved_count: number;
  recent_alerts: RecentAlert[];
}

export interface RecentAlert {
  alertname: string;
  severity: string;
  status: string;
  starts_at: string | null;
  instance: string | null;
}

export interface ItFeedbackStats {
  pending_count: number;
  handling_count: number;
  resolved_count: number;
}

export interface AssetStats {
  total_count: number;
  server_count: number;
  domain_count: number;
  terminal_count: number;
}

export interface CertStats {
  total_count: number;
  valid_count: number;
  expiring_count: number;
  expired_count: number;
}

export interface RecentDeployment {
  project_name: string;
  environment: string;
  status: string;
  created_at: string | null;
}

export interface DashboardOverview {
  alert_stats: AlertStats;
  it_feedback_stats: ItFeedbackStats;
  asset_stats: AssetStats;
  cert_stats: CertStats;
  recent_deployments: RecentDeployment[];
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
