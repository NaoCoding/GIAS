import axios, { AxiosInstance } from 'axios';

export interface PatchInfo {
  patch_file?: string;
  patch_content?: string;
  metadata_file?: string;
  commit_message?: string;
  files_changed: string[];
  status: string; // 'success', 'failed', 'not_generated', 'warning'
}

export interface AnalysisResponse {
  issue_url: string;
  issue_title: string;
  issue_body: string;
  analysis: string;
  status: string;
  patch?: PatchInfo; // NEW: Include patch information
}

export interface QueryResponse {
  result: string;
  status: string;
  patch?: PatchInfo; // NEW: Include patch information
}

interface HealthResponse {
  status: string;
  agent_initialized: boolean;
  vectorstore_initialized: boolean;
  patch_agent_initialized?: boolean;
  current_repo?: string;
}

const API_BASE_URL = 'http://localhost:8000/api';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

api.interceptors.request.use(
  (config) => {
    console.log('Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.status, error.response?.statusText);
    return Promise.reject(error);
  }
);

export const queryAgent = async (query: string): Promise<QueryResponse> => {
  try {
    const response = await api.post<QueryResponse>('/query', { query });
    return response.data;
  } catch (error: unknown) {
    const err = error as any;
    throw err.response?.data || { detail: 'Failed to query agent' };
  }
};

export const analyzeIssue = async (
  owner: string,
  repo: string,
  issueId: number,
  query: string | null = null
): Promise<AnalysisResponse> => {
  try {
    const response = await api.post<AnalysisResponse>('/analyze-issue', {
      owner,
      repo,
      issue_id: issueId,
      query,
    });
    return response.data;
  } catch (error: unknown) {
    const err = error as any;
    throw err.response?.data || { detail: 'Failed to analyze issue' };
  }
};

export const buildRag = async (
  owner: string,
  repo: string,
  save_code: boolean = true
): Promise<{ status: string; message: string; document_count: number; saved_repo_path?: string }> => {
  try {
    const response = await api.post('/build-rag', {
      owner,
      repo,
      save_code,
    });
    return response.data;
  } catch (error: unknown) {
    const err = error as any;
    throw err.response?.data || { detail: 'Failed to build RAG' };
  }
};

export const healthCheck = async (): Promise<HealthResponse> => {
  try {
    const response = await api.get<HealthResponse>('/health');
    return response.data;
  } catch (error) {
    throw error;
  }
};

// NEW: Download patch file
export const downloadPatch = async (patchFile: string): Promise<Blob> => {
  try {
    const response = await axios.get(patchFile, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error: unknown) {
    const err = error as any;
    throw err.response?.data || { detail: 'Failed to download patch' };
  }
};

// NEW: Helper to trigger patch file download in browser
export const triggerPatchDownload = (patchContent: string, patchName: string = 'fix.patch'): void => {
  const element = document.createElement('a');
  const file = new Blob([patchContent], { type: 'text/plain' });
  element.href = URL.createObjectURL(file);
  element.download = patchName;
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
};
