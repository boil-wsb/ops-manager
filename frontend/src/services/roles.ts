import api from './api';

export interface Role {
  id: number;
  name: string;
  description?: string;
  permissions: string[];
  isSystem?: boolean;
  isActive?: boolean;
  userCount?: number;
  permissionCount?: number;
  createdAt?: string;
  updatedAt?: string;
}

export const roleApi = {
  getRoles: async () => {
    const response = await api.get('/roles');
    return response.data;
  },

  getRole: async (id: number) => {
    const response = await api.get(`/roles/${id}`);
    return response.data;
  },

  createRole: async (data: Partial<Role>) => {
    const response = await api.post('/roles', data);
    return response.data;
  },

  updateRole: async (id: number, data: Partial<Role>) => {
    const response = await api.put(`/roles/${id}`, data);
    return response.data;
  },

  deleteRole: async (id: number) => {
    await api.delete(`/roles/${id}`);
  },
};
