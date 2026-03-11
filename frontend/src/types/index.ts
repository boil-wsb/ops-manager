// Common types

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
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
export type AssetType = 'server' | 'vm' | 'network' | 'storage';
export type AssetStatus = 'active' | 'offline' | 'maintenance' | 'retired';

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
  idc?: string;
  region?: string;
  rack?: string;
  labels: Label[];
  description?: string;
  ownerId?: number;
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
  serialNumber: string;
  validFrom: string;
  validUntil: string;
  daysUntilExpiry: number;
  alertThresholdDays: number;
  isAutoRenewal: boolean;
  status: string;
  assetIds: number[];
  createdAt: string;
  updatedAt: string;
}
