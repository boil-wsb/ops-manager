export const routePermissions: Record<string, string | string[]> = {
  '/': [],
  '/assets': 'asset:read',
  '/assets/*': 'asset:read',
  '/monitor/list': 'monitor:read',
  '/monitor/alerts': 'alert:read',
  '/monitor/domains': 'certificate:read',
  '/ops/deployments': 'deployment:read',
  '/ops/it-management': 'it:read',
  '/system/users': 'user:read',
  '/system/roles': 'role:read',
  '/system/navigation': 'navigation:read',
  '/profile': [],
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
    module: 'alert',
    moduleName: '告警管理',
    permissions: [
      { code: 'alert:read', name: '查看告警' },
      { code: 'alert:acknowledge', name: '确认告警' },
      { code: 'alert:resolve', name: '解决告警' },
      { code: 'alert:delete', name: '删除告警' },
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
];
