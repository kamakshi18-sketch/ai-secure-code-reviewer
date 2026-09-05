import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getAuthToken, clearAuth } from '../utils/auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = getAuthToken();
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          clearAuth();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async get<T>(url: string, params?: Record<string, any>): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<T>(url, data);
    return response.data;
  }

  async patch<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.patch<T>(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }
}

export const api = new ApiClient();

export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; refresh_token: string; user?: any; [key: string]: any }>('/auth/login', { email, password }),
  register: (data: { email: string; password: string; full_name: string; role?: string }) =>
    api.post<{ access_token: string; refresh_token: string; user?: any; [key: string]: any }>('/auth/register', data),
  refresh: (refresh_token: string) =>
    api.post<{ access_token: string; refresh_token: string }>('/auth/refresh', { refresh_token }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get<any>('/auth/me'),
  updateMe: (data: any) => api.put<any>('/auth/me', data),
  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/change-password', { current_password, new_password }),
};

export const usersApi = {
  list: (params?: { page?: number; page_size?: number; role?: string; is_active?: boolean; search?: string }) =>
    api.get<any>('/users', { params }),
  get: (id: string) => api.get<any>(`/users/${id}`),
  create: (data: any) => api.post<any>('/users', data),
  update: (id: string, data: any) => api.put<any>(`/users/${id}`, data),
  delete: (id: string) => api.delete(`/users/${id}`),
};

export const repositoriesApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; language?: string; search?: string }) =>
    api.get<any>('/repositories', { params }),
  get: (id: string) => api.get<any>(`/repositories/${id}`),
  create: (data: { github_url: string; github_token?: string }) =>
    api.post<any>('/repositories', data),
  update: (id: string, data: any) => api.put<any>(`/repositories/${id}`, data),
  delete: (id: string) => api.delete(`/repositories/${id}`),
  clone: (id: string) => api.post(`/repositories/${id}/clone`),
  detectLanguage: (id: string) => api.post(`/repositories/${id}/detect-language`),
};

export const scansApi = {
  list: (params?: { page?: number; page_size?: number; repository_id?: string; status?: string; scan_type?: string }) =>
    api.get<any>('/scans', { params }),
  get: (id: string) => api.get<any>(`/scans/${id}`),
  create: (data: { repository_id: string; scan_type?: string; commit_sha?: string; branch?: string; scanners?: string[] }) =>
    api.post<any>('/scans', data),
  cancel: (id: string) => api.post(`/scans/${id}/cancel`),
  retry: (id: string) => api.post(`/scans/${id}/retry`),
  summary: (id: string) => api.get<any>(`/scans/${id}/summary`),
};

export const findingsApi = {
  list: (params?: { 
    page?: number; 
    page_size?: number; 
    scan_id?: string; 
    repository_id?: string; 
    severity?: string; 
    status?: string; 
    scanner?: string; 
    cwe_id?: string; 
    file_path?: string; 
    search?: string 
  }) => api.get<any>('/findings', { params }),
  get: (id: string) => api.get<any>(`/findings/${id}`),
  update: (id: string, data: any) => api.put<any>(`/findings/${id}`, data),
  explain: (id: string) => api.post(`/findings/${id}/explain`),
  stats: (params?: { repository_id?: string; scan_id?: string }) =>
    api.get<any>('/findings/stats/summary', { params }),
};

export const patchesApi = {
  list: (params?: { page?: number; page_size?: number; scan_id?: string; finding_id?: string; status?: string }) =>
    api.get<any>('/patches', { params }),
  get: (id: string) => api.get<any>(`/patches/${id}`),
  create: (scan_id: string, finding_id: string) =>
    api.post<any>('/patches', { scan_id, finding_id }),
  apply: (id: string) => api.post(`/patches/${id}/apply`),
  update: (id: string, data: any) => api.put<any>(`/patches/${id}`, data),
  regenerate: (id: string) => api.post(`/patches/${id}/regenerate`),
};

export const reportsApi = {
  list: (params?: { page?: number; page_size?: number; scan_id?: string; format?: string }) =>
    api.get<any>('/reports', { params }),
  get: (id: string) => api.get<any>(`/reports/${id}`),
  create: (data: { scan_id: string; format?: string; title: string }) =>
    api.post<any>('/reports', data),
  download: (id: string) => api.get(`/reports/${id}/download`, { responseType: 'blob' }),
  delete: (id: string) => api.delete(`/reports/${id}`),
};

export const pullRequestsApi = {
  list: (params?: { page?: number; page_size?: number; repository_id?: string; scan_id?: string; status?: string }) =>
    api.get<any>('/pull-requests', { params }),
  get: (id: string) => api.get<any>(`/pull-requests/${id}`),
  create: (data: { 
    repository_id: string; 
    scan_id?: string; 
    title: string; 
    body: string; 
    head_branch: string; 
    base_branch?: string; 
    patch_ids: string[] 
  }) => api.post<any>('/pull-requests', data),
  update: (id: string, data: any) => api.put<any>(`/pull-requests/${id}`, data),
  sync: (id: string) => api.post(`/pull-requests/${id}/sync`),
};

export const chatApi = {
  send: (data: { messages: any[]; repository_id?: string; scan_id?: string; finding_id?: string; context?: any }) =>
    api.post<any>('/chat', data),
  explainFinding: (finding_id: string, question: string) =>
    api.post<any>(`/chat/explain-finding/${finding_id}`, { question }),
};