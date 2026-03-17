import React from 'react';
import { usePermission } from '../hooks/usePermission';

interface PermissionGuardProps {
  permissions?: string | string[];
  mode?: 'any' | 'all';
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permissions,
  mode = 'any',
  fallback = null,
  children,
}) => {
  const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermission();

  if (!permissions) {
    return <>{children}</>;
  }

  const permissionList = Array.isArray(permissions) ? permissions : [permissions];

  let hasAccess = false;

  if (permissionList.length === 1) {
    hasAccess = hasPermission(permissionList[0]);
  } else {
    hasAccess = mode === 'all'
      ? hasAllPermissions(permissionList)
      : hasAnyPermission(permissionList);
  }

  if (!hasAccess) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

export default PermissionGuard;
