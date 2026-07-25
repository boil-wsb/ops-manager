// Common types

export interface ApiResponse<T> {
  code?: number;
  message: string;
  data: T;
  success?: boolean;
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
  feishuOpenId?: string;
  createdAt: string;
  updatedAt: string;
  permissions?: string[];
  roles?: { id: number; name: string }[];
}

export interface UserIpBinding {
  id: number;
  userId: number;
  username?: string;
  fullName?: string;
  ipAddress: string;
  boundAt: string;
}

export interface IpBindingListResponse {
  items: UserIpBinding[];
  total: number;
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
  ownerName?: string;
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
  daysUntilExpiry: number;
  alertThresholdDays: number;
  isAutoRenewal: boolean;
  status: string;
  assetIds: number[];
  createdAt: string;
  updatedAt: string;
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

export interface ScheduledTask {
  id: number;
  taskId: string;
  name: string;
  taskFunction: string;
  triggerType: string;
  triggerConfig: Record<string, unknown>;
  isEnabled: boolean;
  description: string | null;
  category: string;
  lastRunAt: string | null;
  lastRunStatus: string | null;
  lastRunDuration: number | null;
  nextRunTime: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TaskExecutionLog {
  id: number;
  taskId: string;
  status: string;
  startedAt: string;
  finishedAt: string | null;
  duration: number | null;
  errorMessage: string | null;
  resultSummary: string | null;
  triggerType: string;
  triggeredBy: string | null;
}

// Alert types (re-export from alert.ts)
export type {
  AlertReceiver,
  AlertReceiverCreate,
  AlertReceiverUpdate,
  AlertSilence,
  AlertSilenceCreate,
  AlertSilenceUpdate,
  AlertTemplate,
  AlertTemplateType,
  AlertTemplateCreate,
  AlertTemplateUpdate,
  AlertTemplatePreview,
  AlertHistory,
  AlertHistoryStatus,
  AlertHistorySeverity,
  AlertHistoryListParams,
  PaginationParams,
} from './alert';
