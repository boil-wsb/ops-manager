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
  sortOrder: number;
  isActive: boolean;
  roles: RoleBrief[];
  createdAt: string;
  updatedAt: string;
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
  sortOrder?: number;
  isActive?: boolean;
  restrictToCurrentRole?: boolean;
}

export interface NavigationLinkUpdate {
  category?: string;
  name?: string;
  url?: string;
  icon?: string;
  description?: string;
  sortOrder?: number;
  isActive?: boolean;
  restrictToCurrentRole?: boolean;
}

export interface NavigationLinkImportResult {
  success: boolean;
  name: string;
  message: string;
}

export interface NavigationImportResponse {
  total: number;
  success_count: number;
  failed_count: number;
  results: NavigationLinkImportResult[];
}

export interface NavigationLinkImport {
  category: string;
  name: string;
  url: string;
  icon?: string;
  description?: string;
  sortOrder?: number;
  isActive?: boolean;
  roleNames?: string;
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

  exportLinks: async (): Promise<void> => {
    const response = await api.get('/navigation/export', {
      responseType: 'blob',
    });
    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'navigation_export.csv';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename=(.+)/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  importLinks: async (data: NavigationLinkImport[]): Promise<NavigationImportResponse> => {
    const response = await api.post('/navigation/import', data);
    return response.data;
  },
};
