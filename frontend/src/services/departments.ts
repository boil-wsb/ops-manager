import api from './api';

export interface DepartmentUser {
  id: number;
  username: string;
  fullName?: string;
  email?: string;
  feishuOpenId?: string;
  isActive: boolean;
}

export interface DepartmentNode {
  id: number;
  name: string;
  feishuDepartmentId: string;
  memberCount: number;
  isRoot: boolean;
  children: DepartmentNode[];
  users: DepartmentUser[];
}

export const departmentApi = {
  getTree: async (): Promise<DepartmentNode[]> => {
    const response = await api.get<DepartmentNode[]>('/departments/tree');
    return response.data;
  },

  syncFromFeishu: async (): Promise<{ message: string; status: string }> => {
    const response = await api.post<{ message: string; status: string }>('/departments/sync');
    return response.data;
  },
};
