import api from './api';
import type { ApiResponse, PaginationData, Asset, Label } from '../types';

export const assetApi = {
  getAssets: async (params?: {
    skip?: number;
    limit?: number;
    assetType?: string;
    status?: string;
    idc?: string;
    keyword?: string;
  }): Promise<PaginationData<Asset>> => {
    const response = await api.get<ApiResponse<PaginationData<Asset>>>('/assets', { params });
    return response.data.data;
  },

  getAsset: async (id: number): Promise<Asset> => {
    const response = await api.get<ApiResponse<Asset>>(`/assets/${id}`);
    return response.data.data;
  },

  createAsset: async (data: Partial<Asset>): Promise<Asset> => {
    const response = await api.post<ApiResponse<Asset>>('/assets', data);
    return response.data.data;
  },

  updateAsset: async (id: number, data: Partial<Asset>): Promise<Asset> => {
    const response = await api.put<ApiResponse<Asset>>(`/assets/${id}`, data);
    return response.data.data;
  },

  deleteAsset: async (id: number): Promise<void> => {
    await api.delete(`/assets/${id}`);
  },

  getAssetTree: async (): Promise<any[]> => {
    const response = await api.get<ApiResponse<any[]>>('/assets/tree');
    return response.data.data;
  },

  // Labels
  getLabels: async (): Promise<Label[]> => {
    const response = await api.get<ApiResponse<Label[]>>('/labels');
    return response.data.data;
  },

  createLabel: async (data: Partial<Label>): Promise<Label> => {
    const response = await api.post<ApiResponse<Label>>('/labels', data);
    return response.data.data;
  },

  deleteLabel: async (id: number): Promise<void> => {
    await api.delete(`/labels/${id}`);
  },
};
