import api from './api';

export interface Permission {
  id: number;
  code: string;
  name: string;
  module: string;
  action: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PermissionModule {
  code: string;
  name: string;
}

export interface PermissionGroup {
  module: string;
  module_name: string;
  permissions: Permission[];
}

export interface PermissionsResponse {
  items: PermissionGroup[];
  total: number;
  page: number;
  page_size: number;
}

export interface Role {
  id: number;
  name: string;
  description: string;
  is_system: boolean;
  is_active: boolean;
  permission_count: number;
  user_count: number;
  created_at: string;
  updated_at: string;
  isSystem?: boolean;
  isActive?: boolean;
  userCount?: number;
  permissionCount?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface RoleDetail extends Role {
  permissions: Permission[];
}

export interface RolesResponse {
  items: Role[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateRoleRequest {
  name: string;
  description?: string;
  permission_ids: number[];
}

export interface UpdateRoleRequest {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export interface UpdateRolePermissionsRequest {
  permission_ids: number[];
}

// Permission APIs
export const permissionApi = {
  // Get permission list with module grouping
  getPermissions: (params?: { module?: string; is_active?: boolean; page?: number; page_size?: number }) =>
    api.get<PermissionsResponse>('/permissions', { params }),

  // Get all permission modules
  getModules: () =>
    api.get<PermissionModule[]>('/permissions/modules'),

  // Get permission by ID
  getPermission: (id: number) =>
    api.get<Permission>(`/permissions/${id}`),
};

// Role APIs
export const roleApi = {
  // Get role list
  getRoles: (params?: { is_active?: boolean; page?: number; page_size?: number }) =>
    api.get<RolesResponse>('/roles', { params }),

  // Get role by ID
  getRole: (id: number) =>
    api.get<RoleDetail>(`/roles/${id}`),

  // Create role
  createRole: (data: CreateRoleRequest) =>
    api.post<Role>('/roles', data),

  // Update role
  updateRole: (id: number, data: UpdateRoleRequest) =>
    api.put<Role>(`/roles/${id}`, data),

  // Delete role
  deleteRole: (id: number) =>
    api.delete(`/roles/${id}`),

  // Get role permissions
  getRolePermissions: (id: number) =>
    api.get<{ role_id: number; permissions: Permission[]; permission_count: number }>(`/roles/${id}/permissions`),

  // Update role permissions
  updateRolePermissions: (id: number, data: UpdateRolePermissionsRequest) =>
    api.put<{ role_id: number; permissions: Permission[]; permission_count: number }>(`/roles/${id}/permissions`, data),
};
