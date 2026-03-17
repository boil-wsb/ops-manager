import { Tag } from 'antd';
import type { TagProps } from 'antd';

type StatusType = 'asset' | 'terminal' | 'user' | 'monitor' | 'alert' | 'alertSeverity' | 'deployment' | 'certificate';

interface StatusConfig {
  color: string;
  label: string;
}

type StatusConfigMap = {
  [K in StatusType]: Record<string, StatusConfig>;
};

const statusConfigs: StatusConfigMap = {
  asset: {
    ACTIVE: { color: 'green', label: '运行中' },
    OFFLINE: { color: 'red', label: '离线' },
    MAINTENANCE: { color: 'orange', label: '维护中' },
    RETIRED: { color: 'default', label: '已退役' },
  },
  terminal: {
    ACTIVE: { color: 'green', label: '在线' },
    OFFLINE: { color: 'red', label: '离线' },
    MAINTENANCE: { color: 'orange', label: '维护中' },
    RETIRED: { color: 'default', label: '已退役' },
  },
  user: {
    active: { color: 'green', label: '启用' },
    inactive: { color: 'red', label: '禁用' },
  },
  monitor: {
    up: { color: 'green', label: 'UP' },
    down: { color: 'red', label: 'DOWN' },
    unknown: { color: 'default', label: 'UNKNOWN' },
    paused: { color: 'orange', label: 'PAUSED' },
  },
  alert: {
    firing: { color: 'red', label: '触发中' },
    acknowledged: { color: 'blue', label: '已确认' },
    resolved: { color: 'green', label: '已解决' },
    suppressed: { color: 'default', label: '已抑制' },
  },
  alertSeverity: {
    info: { color: 'blue', label: '信息' },
    warning: { color: 'orange', label: '警告' },
    critical: { color: 'red', label: '严重' },
  },
  deployment: {
    pending: { color: 'default', label: '等待中' },
    running: { color: 'processing', label: '发布中' },
    success: { color: 'success', label: '成功' },
    failed: { color: 'error', label: '失败' },
    rollback: { color: 'warning', label: '已回滚' },
  },
  certificate: {
    active: { color: 'green', label: '有效' },
    expired: { color: 'red', label: '已过期' },
    expiring: { color: 'orange', label: '即将过期' },
    unknown: { color: 'default', label: '未知' },
  },
};

interface StatusTagProps extends Omit<TagProps, 'color'> {
  status: string;
  type: StatusType;
}

const StatusTag: React.FC<StatusTagProps> = ({ status, type, ...rest }) => {
  const typeConfig = statusConfigs[type];
  const config = typeConfig[status];

  if (config) {
    return (
      <Tag color={config.color} {...rest}>
        {config.label}
      </Tag>
    );
  }

  return <Tag {...rest}>{status}</Tag>;
};

export default StatusTag;
