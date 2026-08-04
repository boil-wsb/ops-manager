import type { Permission } from '../services/permissions';

export interface MenuItemConfig {
  key: string;
  label: string;
  icon?: string;
  permission?: string;
  children?: MenuItemConfig[];
}

export interface FlattenedPermission {
  permission: string;
  parentPermission: string | null;
  menuItem: MenuItemConfig;
}

export const menuPermissionConfig: MenuItemConfig[] = [
  {
    key: '/dashboard',
    label: '仪表盘',
    icon: 'DashboardOutlined',
  },
  {
    key: '/assets',
    label: '资产管理',
    icon: 'DatabaseOutlined',
    permission: 'asset:read',
  },
  {
    key: '/alerts',
    label: '告警中心',
    icon: 'AlertOutlined',
    permission: 'alert:read',
    children: [
      { key: '/alerts/alertmanager', label: '告警中心' },
      { key: '/alerts/alertmanager/silences', label: '抑制规则', permission: 'alert:manage_silence' },
      { key: '/alerts/alertmanager/templates', label: '模板配置', permission: 'alert:manage_template' },
      { key: '/alerts/alertmanager/history', label: '告警历史' },
    ],
  },
  {
    key: '/ops',
    label: '运维管理',
    icon: 'DeploymentUnitOutlined',
    permission: 'deployment:read',
    children: [
      { key: '/ops/deployments', label: '部署管理', permission: 'deployment:read' },
      { key: '/ops/it-management', label: 'IT管理', permission: 'it:read' },
      { key: '/ops/domains', label: '域名管理', permission: 'certificate:read' },
      { key: '/ops/scheduled-tasks', label: '定时任务', permission: 'ops:read' },
      { key: '/ops/health-check', label: '每日巡检', permission: 'health-check:read' },
    ],
  },
  {
    key: '/suggestions',
    label: '建议中心',
    icon: 'BulbOutlined',
    children: [
      { key: '/suggestions/submit', label: '匿名建议填写' },
      { key: '/suggestions/manage', label: '建议管理', permission: 'suggestion:read' },
      { key: '/suggestions/track', label: '进度查询' },
    ],
  },
  {
    key: '/system',
    label: '系统管理',
    icon: 'SettingOutlined',
    permission: 'setting:read',
    children: [
      { key: '/system/users', label: '用户管理', permission: 'user:read' },
      { key: '/system/roles', label: '角色管理', permission: 'role:read' },
      { key: '/system/navigation', label: '导航管理', permission: 'navigation:read' },
      { key: '/system/notification-groups', label: '通知组管理', permission: 'notification_group:read' },
      { key: '/system/notification-records', label: '通知记录', permission: 'notification_group:read' },
    ],
  },
];

export function extractAllPermissions(): string[] {
  const permissions = new Set<string>();

  function traverse(items: MenuItemConfig[]) {
    for (const item of items) {
      if (item.permission) {
        permissions.add(item.permission);
      }
      if (item.children) {
        traverse(item.children);
      }
    }
  }

  traverse(menuPermissionConfig);
  return Array.from(permissions);
}

export function flattenMenuPermissions(): Map<string, FlattenedPermission> {
  const flatMap = new Map<string, FlattenedPermission>();

  function traverse(items: MenuItemConfig[], parentPermission: string | null = null) {
    for (const item of items) {
      if (item.permission) {
        flatMap.set(item.permission, {
          permission: item.permission,
          parentPermission,
          menuItem: item,
        });
      }
      if (item.children) {
        traverse(item.children, item.permission || parentPermission);
      }
    }
  }

  traverse(menuPermissionConfig);
  return flatMap;
}

export type PermissionStatus = 'enabled' | 'disabled' | 'available' | 'locked';

export interface PermissionWithStatus {
  permission: Permission;
  status: PermissionStatus;
  parentPermission: string | null;
  missingParentPermission?: string;
}

export function getPermissionStatus(
  permission: Permission,
  selectedPermissionCodes: string[],
  flattenedPermissions: Map<string, FlattenedPermission>
): PermissionWithStatus {
  const code = permission.code;
  const flatInfo = flattenedPermissions.get(code);
  const parentPermission = flatInfo?.parentPermission || null;

  const isSelected = selectedPermissionCodes.includes(code);

  if (isSelected) {
    if (parentPermission && !selectedPermissionCodes.includes(parentPermission)) {
      return {
        permission,
        status: 'disabled',
        parentPermission,
        missingParentPermission: parentPermission,
      };
    }
    return {
      permission,
      status: 'enabled',
      parentPermission,
    };
  }

  if (parentPermission && !selectedPermissionCodes.includes(parentPermission)) {
    return {
      permission,
      status: 'locked',
      parentPermission,
      missingParentPermission: parentPermission,
    };
  }

  return {
    permission,
    status: 'available',
    parentPermission,
  };
}

export interface MenuItemWithStatus {
  key: string;
  label: string;
  icon?: string;
  permission?: string;
  status: PermissionStatus;
  effectivePermission?: string;
  children?: MenuItemWithStatus[];
}

export function getMenuItemStatus(
  item: MenuItemConfig,
  selectedPermissionCodes: string[]
): MenuItemWithStatus {
  const hasPermission = item.permission
    ? selectedPermissionCodes.includes(item.permission)
    : true;

  const status: PermissionStatus = hasPermission ? 'enabled' : 'locked';

  const result: MenuItemWithStatus = {
    key: item.key,
    label: item.label,
    icon: item.icon,
    permission: item.permission,
    status,
    effectivePermission: item.permission,
  };

  if (item.children) {
    result.children = item.children.map((child) =>
      getMenuItemStatus(child, selectedPermissionCodes)
    );
  }

  return result;
}
