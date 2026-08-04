export const routePermissions: Record<string, string | string[]> = {
  '/': [],
  '/assets': 'asset:read',
  '/assets/*': 'asset:read',
  '/ops/deployments': 'deployment:read',
  '/ops/it-management': 'it:read',
  '/ops/domains': 'certificate:read',
  '/ops/health-check': 'health-check:read',
  '/ops/health-check/*': 'health-check:read',
  '/system/users': 'user:read',
  '/system/roles': 'role:read',
  '/system/navigation': 'navigation:read',
  '/system/notification-groups': 'notification_group:read',
  '/system/notification-records': 'notification_group:read',
  '/profile': [],
  '/alerts/alertmanager': 'alert:read',
  '/alerts/alertmanager/silences': 'alert:manage_silence',
  '/alerts/alertmanager/templates': 'alert:manage_template',
  '/alerts/alertmanager/history': 'alert:read',
  '/suggestions/submit': 'suggestion:submit',
  '/suggestions/manage': 'suggestion:read',
  '/suggestions/manage/*': 'suggestion:read',
  '/suggestions/track': 'suggestion:submit',
};

export function getRoutePermission(path: string): string | string[] | undefined {
  if (routePermissions[path]) {
    return routePermissions[path];
  }

  const wildcardPaths = Object.keys(routePermissions).filter((p) => p.includes('*'));
  for (const wildcardPath of wildcardPaths) {
    const pattern = wildcardPath.replace('*', '');
    if (path.startsWith(pattern)) {
      return routePermissions[wildcardPath];
    }
  }

  return undefined;
}

export const PERMISSION_MODULES = [
  {
    module: 'user',
    moduleName: '用户管理',
    permissions: [
      { code: 'user:read', name: '查看用户' },
      { code: 'user:create', name: '创建用户' },
      { code: 'user:update', name: '编辑用户' },
      { code: 'user:delete', name: '删除用户' },
      { code: 'user:assign_role', name: '分配角色' },
    ],
  },
  {
    module: 'role',
    moduleName: '角色管理',
    permissions: [
      { code: 'role:read', name: '查看角色' },
      { code: 'role:create', name: '创建角色' },
      { code: 'role:update', name: '编辑角色' },
      { code: 'role:delete', name: '删除角色' },
    ],
  },
  {
    module: 'asset',
    moduleName: '资产管理',
    permissions: [
      { code: 'asset:read', name: '查看资产' },
      { code: 'asset:create', name: '创建资产' },
      { code: 'asset:update', name: '编辑资产' },
      { code: 'asset:delete', name: '删除资产' },
      { code: 'asset:import', name: '导入资产' },
      { code: 'asset:export', name: '导出资产' },
      { code: 'asset:admin', name: '资产管理员' },
    ],
  },
  {
    module: 'alert',
    moduleName: '告警中心',
    permissions: [
      { code: 'alert:read', name: '查看告警' },
      { code: 'alert:acknowledge', name: '确认告警' },
      { code: 'alert:resolve', name: '解决告警' },
      { code: 'alert:delete', name: '删除告警' },
      { code: 'alert:manage_silence', name: '管理抑制规则' },
      { code: 'alert:manage_template', name: '管理模板' },
      { code: 'alert:manage_receiver', name: '管理接收配置' },
    ],
  },
  {
    module: 'deployment',
    moduleName: '部署管理',
    permissions: [
      { code: 'deployment:read', name: '查看部署' },
      { code: 'deployment:create', name: '创建部署' },
      { code: 'deployment:approve', name: '审批部署' },
      { code: 'deployment:execute', name: '执行部署' },
    ],
  },
  {
    module: 'certificate',
    moduleName: '证书管理',
    permissions: [
      { code: 'certificate:read', name: '查看证书' },
      { code: 'certificate:create', name: '创建证书' },
      { code: 'certificate:update', name: '编辑证书' },
      { code: 'certificate:delete', name: '删除证书' },
      { code: 'certificate:renew', name: '续期证书' },
    ],
  },
  {
    module: 'setting',
    moduleName: '系统设置',
    permissions: [
      { code: 'setting:read', name: '查看设置' },
      { code: 'setting:update', name: '修改设置' },
    ],
  },
  {
    module: 'navigation',
    moduleName: '导航管理',
    permissions: [
      { code: 'navigation:read', name: '查看导航' },
      { code: 'navigation:create', name: '创建导航' },
      { code: 'navigation:update', name: '编辑导航' },
      { code: 'navigation:delete', name: '删除导航' },
    ],
  },
  {
    module: 'notification_group',
    moduleName: '通知组管理',
    permissions: [
      { code: 'notification_group:read', name: '查看通知组' },
      { code: 'notification_group:create', name: '创建通知组' },
      { code: 'notification_group:update', name: '编辑通知组' },
      { code: 'notification_group:delete', name: '删除通知组' },
    ],
  },
  {
    module: 'suggestion',
    moduleName: '建议中心',
    permissions: [
      { code: 'suggestion:submit', name: '提交建议' },
      { code: 'suggestion:read', name: '查看建议列表' },
      { code: 'suggestion:archive', name: '市场部存档' },
    ],
  },
  {
    module: 'it',
    moduleName: 'IT管理',
    permissions: [
      { code: 'it:read', name: '查看IT管理' },
      { code: 'it:resolve', name: '处理IT反馈' },
      { code: 'it:delete', name: '删除IT反馈' },
    ],
  },
  {
    module: 'monitor',
    moduleName: '监控管理',
    permissions: [
      { code: 'monitor:read', name: '查看监控' },
      { code: 'monitor:create', name: '创建监控' },
      { code: 'monitor:update', name: '编辑监控' },
      { code: 'monitor:delete', name: '删除监控' },
      { code: 'monitor:test', name: '测试监控' },
    ],
  },
  {
    module: 'ops',
    moduleName: '运维管理',
    permissions: [
      { code: 'ops:read', name: '查看运维' },
      { code: 'ops:write', name: '编辑运维' },
      { code: 'ops:delete', name: '删除运维' },
    ],
  },
  {
    module: 'health-check',
    moduleName: '每日巡检',
    permissions: [
      { code: 'health-check:read', name: '查看巡检' },
      { code: 'health-check:write', name: '管理巡检' },
    ],
  },
];
