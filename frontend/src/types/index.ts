// Common types

export interface ApiResponse<T> {
  code?: number;
  message: string;
  data: T;
  success?: boolean;
}

export interface PaginationParams {
  page: number;
  pageSize: number;
}

export interface PaginationData<T> {
  total: number;
  items: T[];
}

// User types
export interface User {
  id: number;
  username: string;
  email?: string;
  fullName?: string;
  isActive: boolean;
  isSuperuser: boolean;
  lastLogin?: string;
  createdAt: string;
  updatedAt: string;
  permissions?: string[];
  roles?: { id: number; name: string }[];
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

// Asset types
export type AssetType = 'SERVER' | 'VM' | 'NETWORK' | 'STORAGE' | 'TERMINAL';
export type AssetStatus = 'ACTIVE' | 'OFFLINE' | 'MAINTENANCE' | 'RETIRED';
export type AssetSource = 'MANUAL' | 'PROMETHEUS' | 'IMPORTED';
export type SyncStatus = 'PENDING' | 'SYNCED' | 'ERROR';

export interface Label {
  id: number;
  name: string;
  color: string;
  description?: string;
  createdAt: string;
}

export interface Asset {
  id: number;
  assetId: string;
  name: string;
  assetType: AssetType;
  status: AssetStatus;
  ipAddress?: string;
  privateIp?: string;
  macAddress?: string;
  cpuCores?: number;
  memoryGb?: number;
  diskGb?: number;
  osType?: string;
  osVersion?: string;
  arch?: string;
  idc?: string;
  region?: string;
  rack?: string;
  labels: Label[];
  description?: string;
  ownerId?: number;
  owner?: {
    id: number;
    username: string;
    name?: string;
  };
  source?: string;
  prometheusInstance?: string;
  lastSyncTime?: string;
  syncStatus?: string;
  // Terminal specific fields
  hostname?: string;
  serialNumber?: string;
  uuid?: string;
  customer?: string;
  // All pc_info labels
  labelsData?: Record<string, string | number | boolean>;
  createdAt: string;
  updatedAt: string;
}

// Monitor types
export type MonitorType = 'ping' | 'http' | 'tcp' | 'udp';
export type MonitorStatus = 'up' | 'down' | 'unknown' | 'paused';

export interface Monitor {
  id: number;
  name: string;
  monitorType: MonitorType;
  target: string;
  intervalSeconds: number;
  timeoutSeconds: number;
  retryCount: number;
  httpMethod?: string;
  httpHeaders?: Record<string, string>;
  expectedStatusCode?: number;
  expectedResponseContent?: string;
  thresholdWarning?: number;
  thresholdCritical?: number;
  isEnabled: boolean;
  currentStatus: MonitorStatus;
  lastCheckAt?: string;
  lastCheckResult?: string;
  lastCheckDurationMs?: number;
  assetId?: number;
  createdAt: string;
  updatedAt: string;
}

// Alert types
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertStatus = 'firing' | 'acknowledged' | 'resolved' | 'suppressed';

export interface Alert {
  id: number;
  monitorId: number;
  monitorName: string;
  alertRuleId?: number;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  message?: string;
  metricName?: string;
  metricValue?: number;
  thresholdValue?: number;
  startedAt: string;
  acknowledgedAt?: string;
  acknowledgedBy?: number;
  resolvedAt?: string;
  resolvedBy?: number;
  notificationSent: boolean;
}

export interface AlertRule {
  id: number;
  name: string;
  monitorId: number;
  metricName: string;
  condition: string;
  threshold: number;
  duration: number;
  severity: AlertSeverity;
  isEnabled: boolean;
  notificationChannels?: number[];
  createdAt: string;
  updatedAt: string;
}

export interface NotificationChannel {
  id: number;
  name: string;
  type: 'email' | 'webhook' | 'dingtalk' | 'wechat';
  config: Record<string, string | number | boolean>;
  isEnabled: boolean;
  createdAt: string;
  updatedAt: string;
}

// Ops types
export type DeploymentStatus = 'pending' | 'running' | 'success' | 'failed' | 'rollback';

export interface Deployment {
  id: number;
  projectName: string;
  version: string;
  environment: string;
  status: DeploymentStatus;
  deployerId?: number;
  deployerName?: string;
  approverId?: number;
  approverName?: string;
  deployTime?: string;
  durationSeconds?: number;
  logOutput?: string;
  rollbackReason?: string;
  createdAt: string;
}

export interface Certificate {
  id: number;
  domain: string;
  issuer: string;
  subject: string;
  serial_number: string;
  valid_from: string;
  valid_until: string;
  days_until_expiry: number;
  alert_threshold_days: number;
  is_auto_renewal: boolean;
  status: string;
  asset_ids: number[];
  created_at: string;
  updated_at: string;
}

export interface DNSRecord {
  id: number;
  domain: string;
  name: string;
  type: string;
  value: string;
  ttl: number;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface InspectionTask {
  id: number;
  name: string;
  type: string;
  target: string;
  schedule: string;
  isEnabled: boolean;
  lastRunAt?: string;
  nextRunAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface InspectionReport {
  id: number;
  taskId: number;
  status: string;
  startedAt: string;
  finishedAt?: string;
  summary: string;
  details?: Record<string, unknown>;
  createdAt: string;
}
