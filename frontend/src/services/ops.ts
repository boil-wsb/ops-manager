import api from './api';
import type { Deployment, Certificate, DNSRecord, InspectionTask } from '../types';

export interface DeploymentListParams {
  skip?: number;
  limit?: number;
  project?: string;
  environment?: string;
  status?: string;
}

export interface CertificateListParams {
  status?: string;
  expiring_soon?: boolean;
  page?: number;
  page_size?: number;
}

export interface CertificateListResponse {
  total: number;
  items: Certificate[];
  page: number;
  pageSize: number;
  totalPages: number;
}

export const opsApi = {
  // Deployments
  getDeployments: async (params: DeploymentListParams = {}) => {
    const response = await api.get('/ops/deployments', { params });
    return response.data;
  },

  getDeployment: async (id: number) => {
    const response = await api.get(`/ops/deployments/${id}`);
    return response.data;
  },

  createDeployment: async (data: Partial<Deployment>) => {
    const response = await api.post('/ops/deployments', data);
    return response.data;
  },

  updateDeployment: async (id: number, data: Partial<Deployment>) => {
    const response = await api.put(`/ops/deployments/${id}`, data);
    return response.data;
  },

  // Certificates
  // I-19 修复：原全量返回 list，现改为服务端分页返回 {total, items, ...}
  getCertificates: async (params: CertificateListParams = {}): Promise<CertificateListResponse> => {
    const response = await api.get('/ops/certificates', { params });
    return response.data;
  },

  getCertificate: async (id: number) => {
    const response = await api.get(`/ops/certificates/${id}`);
    return response.data;
  },

  createCertificate: async (data: Partial<Certificate>) => {
    const response = await api.post('/ops/certificates', data);
    return response.data;
  },

  updateCertificate: async (id: number, data: Partial<Certificate>) => {
    const response = await api.put(`/ops/certificates/${id}`, data);
    return response.data;
  },

  deleteCertificate: async (id: number) => {
    await api.delete(`/ops/certificates/${id}`);
  },

  syncCertificates: async () => {
    const response = await api.post('/ops/certificates/sync');
    return response.data;
  },

  // DNS Records
  getDNSRecords: async (params: { skip?: number; limit?: number; domain?: string } = {}) => {
    const response = await api.get('/ops/dns', { params });
    return response.data;
  },

  getDNSRecord: async (id: number) => {
    const response = await api.get(`/ops/dns/${id}`);
    return response.data;
  },

  createDNSRecord: async (data: Partial<DNSRecord>) => {
    const response = await api.post('/ops/dns', data);
    return response.data;
  },

  updateDNSRecord: async (id: number, data: Partial<DNSRecord>) => {
    const response = await api.put(`/ops/dns/${id}`, data);
    return response.data;
  },

  deleteDNSRecord: async (id: number) => {
    await api.delete(`/ops/dns/${id}`);
  },

  // Inspection Tasks
  getInspectionTasks: async (params: { skip?: number; limit?: number } = {}) => {
    const response = await api.get('/ops/inspections/tasks', { params });
    return response.data;
  },

  getInspectionTask: async (id: number) => {
    const response = await api.get(`/ops/inspections/tasks/${id}`);
    return response.data;
  },

  createInspectionTask: async (data: Partial<InspectionTask>) => {
    const response = await api.post('/ops/inspections/tasks', data);
    return response.data;
  },

  updateInspectionTask: async (id: number, data: Partial<InspectionTask>) => {
    const response = await api.put(`/ops/inspections/tasks/${id}`, data);
    return response.data;
  },

  deleteInspectionTask: async (id: number) => {
    await api.delete(`/ops/inspections/tasks/${id}`);
  },

  // Inspection Reports
  getInspectionReports: async (params: { skip?: number; limit?: number; task_id?: number } = {}) => {
    const response = await api.get('/ops/inspections/reports', { params });
    return response.data;
  },

  getInspectionReport: async (id: number) => {
    const response = await api.get(`/ops/inspections/reports/${id}`);
    return response.data;
  },
};
