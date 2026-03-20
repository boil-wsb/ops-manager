import api from './api';

export const roleApi = {
  getRoles: async () => {
    const response = await api.get('/roles');
    return response.data;
  },

  getRole: async (id: number) => {
    const response = await api.get(`/roles/${id}`);
    return response.data;
  },

  createRole: async (data: { name: string; description?: string; permissionIds?: number[] }) => {
    const response = await api.post('/roles', data);
    return response.data;
  },

  updateRole: async (id: number, data: { name?: string; description?: string; permissionIds?: number[] }) => {
    const response = await api.put(`/roles/${id}`, data);
    return response.data;
  },

  deleteRole: async (id: number) => {
    await api.delete(`/roles/${id}`);
  },

  getRolePermissions: async (id: number) => {
    const response = await api.get(`/roles/${id}/permissions`);
    return response.data;
  },

  updateRolePermissions: async (id: number, permissionIds: number[]) => {
    const response = await api.put(`/roles/${id}/permissions`, { permission_ids: permissionIds });
    return response.data;
  },
};
