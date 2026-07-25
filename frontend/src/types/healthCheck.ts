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
  /** 当前主机是否被抑制告警（true 时前端展示「已抑制」标签） */
  isSilenced?: boolean;
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

/** 健康巡检抑制规则 */
export interface HealthCheckSilence {
  id: number;
  name: string;
  instance: string;
  reason: string;
  startsAt: string | null;
  endsAt: string | null;
  isActive: boolean;
  createdBy: number | null;
  createdAt: string | null;
  updatedAt: string | null;
}

/** 创建抑制规则请求 */
export interface HealthCheckSilenceCreatePayload {
  instance: string;
  reason?: string;
  /** 持续小时数；不传或 0 表示永久抑制 */
  durationHours?: number | null;
}
