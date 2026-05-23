import React, { createContext, useContext, useState } from 'react';
import { authService, TokenResponse, RegisterData } from '../lib/api/auth';

interface AuthContextType {
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: Record<string, string>) => Promise<void>;
  register: (details: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('accessToken'));
  const [refreshToken, setRefreshToken] = useState<string | null>(localStorage.getItem('refreshToken'));
  const [lastRefreshTimestamp, setLastRefreshTimestamp] = useState<number | null>(() => {
    const saved = localStorage.getItem('lastRefreshTimestamp');
    return saved ? parseInt(saved, 10) : null;
  });
  const [loginTimestamp, setLoginTimestamp] = useState<number | null>(() => {
    const saved = localStorage.getItem('loginTimestamp');
    return saved ? parseInt(saved, 10) : null;
  });

  const logout = async () => {
    try {
      const rt = localStorage.getItem('refreshToken');
      if (rt) {
        await authService.logout(rt);
      }
    } catch (e) {
      console.error("Logout failed", e);
    } finally {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('loginTimestamp');
      localStorage.removeItem('lastRefreshTimestamp');
      setToken(null);
      setRefreshToken(null);
      setLoginTimestamp(null);
      setLastRefreshTimestamp(null);
    }
  };

  React.useEffect(() => {
    if (!token || !refreshToken) return;

    // 58-minute access token refresh rule
    const REFRESH_INTERVAL_MS = 58 * 60 * 1000;
    
    // Use lastRefreshTimestamp or fallback to loginTimestamp
    const baseTime = lastRefreshTimestamp || loginTimestamp || Date.now();
    const timeSinceLastRefresh = Date.now() - baseTime;
    const timeUntilNextRefresh = Math.max(1000, REFRESH_INTERVAL_MS - timeSinceLastRefresh);
    
    const refreshTimeout = setTimeout(async () => {
      try {
        const data = await authService.refresh(refreshToken);
        setTokens(data, false); // Update tokens but preserve login timestamp
      } catch (e: any) {
        console.error("Session refresh failed", e);
        if (e.response?.status === 401 || e.response?.status === 403) {
          logout();
        }
      }
    }, timeUntilNextRefresh);

    return () => {
      clearTimeout(refreshTimeout);
    };
  }, [token, refreshToken, lastRefreshTimestamp, loginTimestamp]);

  const setTokens = (data: TokenResponse, isNewLogin: boolean = true) => {
    localStorage.setItem('accessToken', data.access);
    localStorage.setItem('refreshToken', data.refresh);
    setToken(data.access);
    setRefreshToken(data.refresh);
    
    const now = Date.now();
    localStorage.setItem('lastRefreshTimestamp', now.toString());
    setLastRefreshTimestamp(now);
    
    if (isNewLogin) {
      localStorage.setItem('loginTimestamp', now.toString());
      setLoginTimestamp(now);
    }
  };

  const login = async (credentials: Record<string, string>) => {
    const data = await authService.login(credentials);
    setTokens(data);
  };

  const register = async (details: RegisterData) => {
    const data = await authService.register(details);
    setTokens(data);
  };

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
