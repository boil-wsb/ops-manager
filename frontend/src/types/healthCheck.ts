export interface HealthCheckReport {
  id: number;
  reportTime: string | null;
  source: string;
  totalHosts: number;
  okCount: number;
  warningCount: number;
  criticalCount: number;
  notificationSent: boolean;
  createdAt: string | null;
  details?: HealthCheckDetail[];
}

export interface HealthCheckDetail {
  id: number;
  instance: string;
  assetType: string;
  hostStatus: string;
  env: string | null;
  osInfo: string | null;
  kernelVersion: string | null;
  cpuCount: number | null;
  cpuUsage: number | null;
  load1: number | null;
  load5: number | null;
  load15: number | null;
  memoryUsage: number | null;
  memoryTotalMb: number | null;
  memoryUsedMb: number | null;
  diskUsage: number | null;
  diskTotalGb: number | null;
  isOnline: boolean;
  checkDetails: Record<string, unknown> | null;
  checkedAt: string | null;
}

export interface HealthCheckThresholds {
  cpuLoadPerCoreWarning: number;
  cpuLoadPerCoreCritical: number;
  memoryUsageWarning: number;
  memoryUsageCritical: number;
  diskUsageWarning: number;
  diskUsageCritical: number;
}

export interface HealthCheckHistoryParams {
  days?: number;
  page?: number;
  pageSize?: number;
}
