import { useMemo } from 'react';
import { useAuthStore } from '../stores/authStore';

export function usePermission() {
  const permissions = useAuthStore((state) => state.permissions);
  const isSuperuser = useAuthStore((state) => state.user?.isSuperuser);

  const hasPermission = useMemo(() => {
    return (permission: string): boolean => {
      if (isSuperuser) return true;
      if (!permissions || permissions.length === 0) return false;
      if (permissions.includes('*')) return true;
      return permissions.includes(permission);
    };
  }, [permissions, isSuperuser]);

  const hasAnyPermission = useMemo(() => {
    return (permissionList: string[]): boolean => {
      if (isSuperuser) return true;
      if (!permissions || permissions.length === 0) return false;
      if (permissions.includes('*')) return true;
      return permissionList.some((p) => permissions.includes(p));
    };
  }, [permissions, isSuperuser]);

  const hasAllPermissions = useMemo(() => {
    return (permissionList: string[]): boolean => {
      if (isSuperuser) return true;
      if (!permissions || permissions.length === 0) return false;
      if (permissions.includes('*')) return true;
      return permissionList.every((p) => permissions.includes(p));
    };
  }, [permissions, isSuperuser]);

  return {
    permissions,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
  };
}
