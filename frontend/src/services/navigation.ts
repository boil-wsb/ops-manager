import api from './api';

export interface RoleBrief {
  id: number;
  name: string;
}

export interface NavigationLink {
  id: number;
  category: string;
  name: string;
  url: string;
  icon?: string;
  description?: string;
  sort_order: number;
  is_active: boolean;
  roles: RoleBrief[];
  created_at: string;
  updated_at: string;
}

export interface NavigationGroup {
  category: string;
  links: NavigationLink[];
}

export interface NavigationLinkListResponse {
  items: NavigationLink[];
  total: number;
  page: number;
  page_size: number;
}

export interface NavigationLinkCreate {
  category: string;
  name: string;
  url: string;
  icon?: string;
  description?: string;
  sort_order?: number;
  is_active?: boolean;
  restrict_to_current_role?: boolean;
}

export interface NavigationLinkUpdate {
  category?: string;
  name?: string;
  url?: string;
  icon?: string;
  description?: string;
  sort_order?: number;
  is_active?: boolean;
  restrict_to_current_role?: boolean;
}

export const navigationApi = {
  getPublicLinks: async (): Promise<{ groups: NavigationGroup[] }> => {
    const response = await api.get('/navigation/public');
    return response.data;
  },

  getLinks: async (params?: {
    category?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<NavigationLinkListResponse> => {
    const response = await api.get('/navigation', { params });
    return response.data;
  },

  getLink: async (id: number): Promise<NavigationLink> => {
    const response = await api.get(`/navigation/${id}`);
    return response.data;
  },

  createLink: async (data: NavigationLinkCreate): Promise<NavigationLink> => {
    const response = await api.post('/navigation', data);
    return response.data;
  },

  updateLink: async (id: number, data: NavigationLinkUpdate): Promise<NavigationLink> => {
    const response = await api.put(`/navigation/${id}`, data);
    return response.data;
  },

  deleteLink: async (id: number): Promise<void> => {
    await api.delete(`/navigation/${id}`);
  },
};
