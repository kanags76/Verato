import axios from 'axios';
import { globalSetError } from '@/src/components/ErrorProvider';

const API_URL = (import.meta.env.VITE_API_URL || 'https://api.verato.twocents.ai/api/v1').replace(/\/$/, '');

export const apiClient = axios.create({
  baseURL: API_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If the error is 401 and not already a retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refreshToken');
      
      if (refreshToken) {
        try {
          // Use a fresh axios instance to avoid interceptor loop
          const response = await axios.post(`${API_URL}/auth/token/refresh/`, {
            refresh: refreshToken
          });
          
          const { access } = response.data;
          localStorage.setItem('accessToken', access);
          
          isRefreshing = false;
          processQueue(null, access);
          
          // Retry the original request with the new token
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return apiClient(originalRequest);
        } catch (refreshError: any) {
          isRefreshing = false;
          processQueue(refreshError, null);
          
          if (refreshError.response?.status === 401 || refreshError.response?.status === 403) {
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('loginTimestamp');
            localStorage.removeItem('lastRefreshTimestamp');
            window.location.href = '/login';
          }
          return Promise.reject(refreshError);
        }
      }
    }
    
    globalSetError(error.response?.data?.detail || 'Something went wrong');
    return Promise.reject(error);
  }
);
