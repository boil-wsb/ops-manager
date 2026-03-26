import { useMemo } from 'react';
import { Tree, Tooltip, Typography } from 'antd';
import {
  DashboardOutlined,
  DatabaseOutlined,
  MonitorOutlined,
  DeploymentUnitOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  LockOutlined,
  StopOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import {
  menuPermissionConfig,
  getMenuItemStatus,
  type MenuItemWithStatus,
  type PermissionStatus,
} from '../config/menuPermissionConfig';
import { useThemeStore } from '../stores/themeStore';

const { Text } = Typography;

const iconMap: Record<string, React.ReactNode> = {
  DashboardOutlined: <DashboardOutlined />,
  DatabaseOutlined: <DatabaseOutlined />,
  MonitorOutlined: <MonitorOutlined />,
  DeploymentUnitOutlined: <DeploymentUnitOutlined />,
  SettingOutlined: <SettingOutlined />,
  AppstoreOutlined: <AppstoreOutlined />,
};

const statusConfig: Record<
  PermissionStatus,
  { icon: React.ReactNode; color: string; text: string }
> = {
  enabled: {
    icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
    color: '#52c41a',
    text: '可访问',
  },
  disabled: {
    icon: <StopOutlined style={{ color: '#ff4d4f' }} />,
    color: '#ff4d4f',
    text: '父权限缺失',
  },
  available: {
    icon: <CheckCircleOutlined style={{ color: '#1890ff' }} />,
    color: '#1890ff',
    text: '可勾选',
  },
  locked: {
    icon: <LockOutlined style={{ color: '#faad14' }} />,
    color: '#faad14',
    text: '需父权限',
  },
};

interface MenuPreviewProps {
  selectedPermissions: string[];
}

function renderMenuItem(item: MenuItemWithStatus, isDark: boolean): React.ReactNode {
  const config = statusConfig[item.status];
  const icon = item.icon ? iconMap[item.icon] : <AppstoreOutlined />;
  const isAccessible = item.status === 'enabled';

  const label = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ color: isAccessible ? undefined : (isDark ? '#666' : '#999') }}>{icon}</span>
      <Text style={{ color: isAccessible ? undefined : (isDark ? '#666' : '#999') }}>{item.label}</Text>
      <Tooltip title={config.text}>
        <span style={{ color: config.color, fontSize: 12 }}>{config.icon}</span>
      </Tooltip>
    </div>
  );

  return label;
}

function buildTreeData(items: MenuItemWithStatus[], isDark: boolean): DataNode[] {
  return items.map((item) => {
    const node: DataNode = {
      key: item.key,
      title: renderMenuItem(item, isDark),
      children: item.children ? buildTreeData(item.children, isDark) : undefined,
    };
    return node;
  });
}

export function MenuPreview({ selectedPermissions }: MenuPreviewProps) {
  const { mode: themeMode } = useThemeStore();
  const isDark = themeMode === 'dark';

  const menuWithStatus = useMemo(() => {
    return menuPermissionConfig.map((item) =>
      getMenuItemStatus(item, selectedPermissions)
    );
  }, [selectedPermissions]);

  const treeData = useMemo(() => buildTreeData(menuWithStatus, isDark), [menuWithStatus, isDark]);

  const lockedCount = useMemo(() => {
    let count = 0;
    function countLocked(items: MenuItemWithStatus[]) {
      for (const item of items) {
        if (item.status === 'locked' || item.status === 'disabled') {
          count++;
        }
        if (item.children) {
          countLocked(item.children);
        }
      }
    }
    countLocked(menuWithStatus);
    return count;
  }, [menuWithStatus]);

  const enabledCount = useMemo(() => {
    let count = 0;
    function countEnabled(items: MenuItemWithStatus[]) {
      for (const item of items) {
        if (item.status === 'enabled') {
          count++;
        }
        if (item.children) {
          countEnabled(item.children);
        }
      }
    }
    countEnabled(menuWithStatus);
    return count;
  }, [menuWithStatus]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 12, display: 'flex', gap: 16 }}>
        <Text type="secondary">
          <CheckCircleOutlined style={{ color: '#52c41a' }} /> 可访问{' '}
          <Text strong style={{ color: '#52c41a' }}>
            {enabledCount}
          </Text>
        </Text>
        <Text type="secondary">
          <LockOutlined style={{ color: '#faad14' }} /> 需权限{' '}
          <Text strong style={{ color: '#faad14' }}>
            {lockedCount}
          </Text>
        </Text>
      </div>
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          border: `1px solid ${isDark ? '#303030' : '#f0f0f0'}`,
          borderRadius: 8,
          padding: 12,
          background: isDark ? '#1a1a1a' : '#fafafa',
        }}
      >
        <Tree
          showIcon
          defaultExpandAll
          treeData={treeData}
          blockNode
        />
      </div>
      {lockedCount > 0 && (
        <div
          style={{
            marginTop: 12,
            padding: '8px 12px',
            background: isDark ? '#2a2418' : '#fffbe6',
            border: `1px solid ${isDark ? '#5c4f29' : '#ffe58f'}`,
            borderRadius: 6,
            fontSize: 12,
          }}
        >
          <Text type="warning">
            <LockOutlined /> 部分菜单需要先勾选父权限才能访问
          </Text>
        </div>
      )}
    </div>
  );
}
