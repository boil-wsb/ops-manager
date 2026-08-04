// Alertmanager Webhook types

// 告警接收配置
export interface AlertReceiver {
  id: number;
  name: string;
  webhookUrl: string;
  authType: 'none' | 'secret' | 'token';
  authSecret?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AlertReceiverCreate {
  name: string;
  webhookUrl: string;
  authType: 'none' | 'secret' | 'token';
  authSecret?: string;
  isActive: boolean;
}

export interface AlertReceiverUpdate {
  name?: string;
  webhookUrl?: string;
  authType?: 'none' | 'secret' | 'token';
  authSecret?: string;
  isActive?: boolean;
}

// 抑制规则
export interface AlertSilence {
  id: number;
  name: string;
  matchLabels: Record<string, string>;
  matchPattern?: string;
  startsAt: string;
  endsAt: string;
  createdBy: string;
  isActive: boolean;
  createdAt: string;
}

export interface AlertSilenceCreate {
  name: string;
  matchLabels: Record<string, string>;
  matchPattern?: string;
  startsAt: string;
  endsAt: string;
  isActive: boolean;
}

export interface AlertSilenceUpdate {
  name?: string;
  matchLabels?: Record<string, string>;
  matchPattern?: string;
  startsAt?: string;
  endsAt?: string;
  isActive?: boolean;
}

// 告警模板
export type AlertTemplateType = 'email' | 'feishu';

export interface AlertTemplate {
  id: number;
  name: string;
  templateType: AlertTemplateType;
  subjectTemplate?: string;
  bodyTemplate?: string;
  cardConfig?: Record<string, unknown>;
  isDefault: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AlertTemplateCreate {
  name: string;
  templateType: AlertTemplateType;
  subjectTemplate?: string;
  bodyTemplate?: string;
  cardConfig?: Record<string, unknown>;
  isDefault: boolean;
  isActive: boolean;
}

export interface AlertTemplateUpdate {
  name?: string;
  templateType?: AlertTemplateType;
  subjectTemplate?: string;
  bodyTemplate?: string;
  cardConfig?: Record<string, unknown>;
  isDefault?: boolean;
  isActive?: boolean;
}

export interface AlertTemplatePreview {
  labels: Record<string, string>;
  annotations: Record<string, string>;
}

// 告警历史
export type AlertHistoryStatus = 'firing' | 'resolved' | 'suppressed';
export type AlertHistorySeverity = 'info' | 'warning' | 'critical' | 'high' | 'middle' | 'low';

export interface AlertHistory {
  id: number;
  alertname: string;
  status: AlertHistoryStatus;
  severity: AlertHistorySeverity;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  startsAt: string;
  endsAt?: string;
  isSuppressed: boolean;
  silenceId?: number;
  notificationSent: boolean;
  createdAt: string;
}

export interface AlertHistoryListParams {
  page: number;
  pageSize: number;
  skip?: number;
  limit?: number;
  status?: AlertHistoryStatus;
  severity?: AlertHistorySeverity;
  startTime?: string;
  endTime?: string;
  alertname?: string;
}

// 分页参数
export interface PaginationParams {
  page: number;
  pageSize: number;
}
