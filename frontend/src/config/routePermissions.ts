export const routePermissions: Record<string, string | string[]> = {
  '/': [],
  '/assets': 'asset:read',
  '/assets/*': 'asset:read',
  '/monitor/list': 'monitor:read',
  '/monitor/alerts': 'alert:read',
  '/monitor/domains': 'certificate:read',
  '/ops/deployments': 'deployment:read',
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
