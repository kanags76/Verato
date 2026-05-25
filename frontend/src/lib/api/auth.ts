import axios from 'axios';
import { apiClient } from './client';

const API_URL = (import.meta.env.VITE_API_URL || 'https://api.verato.twocents.ai/api/v1').replace(/\/$/, '');

export interface TokenResponse {
  access: string;
  refresh: string;
}

export interface RegisterData {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  org_name: string;
  plan: string;
}

export interface RegisterResponse {
  session_token: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  is_org_admin: boolean;
  organisation: {
    id: string;
    name: string;
    slug: string;
    plan: string;
  };
}

export const authService = {
  getProfile: async (): Promise<UserProfile> => {
    const response = await apiClient.get<any>('auth/me/');
    const data = response.data;
    // Handle both direct and wrapped response
    if (data && data.data && !data.id) return data.data;
    return data;
  },
  login: async (credentials: Record<string, string>): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>('auth/token/', credentials);
    return data;
  },
  register: async (details: RegisterData): Promise<RegisterResponse> => {
    const { data } = await apiClient.post<RegisterResponse>('auth/register/', details);
    return data;
  },
  verifyEmail: async (session_token: string, code: string): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>('auth/verify-email/', { session_token, code });
    return data;
  },
  resendVerification: async (credentials: Record<string, string>): Promise<{ session_token: string }> => {
    const { data } = await apiClient.post<{ session_token: string }>('auth/resend-verification/', credentials);
    return data;
  },
  refresh: async (refresh: string): Promise<TokenResponse> => {
    // Call refresh endpoint without Authorization header to avoid potential issues with expired tokens
    const { data } = await axios.post<TokenResponse>(`${API_URL}/auth/token/refresh/`, { refresh });
    return data;
  },
  logout: async (refresh: string): Promise<void> => {
    await apiClient.post('auth/logout/', { refresh });
  },
};
