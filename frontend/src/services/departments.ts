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
  orgName?: string | null;
  memberCount: number;
  isRoot: boolean;
  leaderId?: number | null;
  leaderUsername?: string | null;
  leaderFullName?: string | null;
  children: DepartmentNode[];
  users: DepartmentUser[];
}

export interface DepartmentLeaderInfo {
  id: number;
  name: string;
  leaderId: number | null;
  leaderUsername: string | null;
  leaderFullName: string | null;
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

  setLeader: async (deptId: number, leaderId: number | null): Promise<DepartmentLeaderInfo> => {
    const response = await api.put<DepartmentLeaderInfo>(`/departments/${deptId}/leader`, { leaderId });
    return response.data;
  },
};
