import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

api.interceptors.request.use(
  (config) => {
    console.log('Request:', config.method.toUpperCase(), config.url);
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

export const queryAgent = async (query) => {
  try {
    const response = await api.post('/query', { query });
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to query agent' };
  }
};

export const analyzeIssue = async (owner, repo, issueId, query = null) => {
  try {
    const response = await api.post('/analyze-issue', {
      owner,
      repo,
      issue_id: issueId,
      query,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to analyze issue' };
  }
};

export const buildRag = async (owner, repo) => {
  try {
    const response = await api.post('/build-rag', {
      owner,
      repo,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to build RAG' };
  }
};

export const healthCheck = async () => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    throw error;
  }
};
