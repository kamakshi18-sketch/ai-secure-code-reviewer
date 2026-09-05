import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User } from '../types';
import { authApi } from '../services/api';
import { getAuthToken, setAuthToken, setRefreshToken, setUser, clearAuth, isTokenExpired } from '../utils/auth';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; role?: string }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateUser: (data: Partial<User>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function extractUser(data: any): User {
  if (data?.user) return data.user;
  const { access_token, refresh_token, token_type, ...userData } = data || {};
  return userData as User;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const token = getAuthToken();
      if (!token || isTokenExpired(token)) {
        setUserState(null);
        return;
      }
      const response = await authApi.me();
      const currentUser = extractUser(response);
      setUserState(currentUser);
      setUser(currentUser);
    } catch (error) {
      console.error('Failed to refresh user:', error);
      setUserState(null);
      clearAuth();
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const response = await authApi.login(email, password);
      setAuthToken(response.access_token);
      setRefreshToken(response.refresh_token);
      const currentUser = extractUser(response);
      setUser(currentUser);
      setUserState(currentUser);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: { email: string; password: string; full_name: string; role?: string }) => {
    setIsLoading(true);
    try {
      const response = await authApi.register(data);
      setAuthToken(response.access_token);
      setRefreshToken(response.refresh_token);
      const currentUser = extractUser(response);
      setUser(currentUser);
      setUserState(currentUser);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearAuth();
      setUserState(null);
    }
  };

  const updateUser = async (data: Partial<User>) => {
    const response = await authApi.updateMe(data);
    const updated = extractUser(response);
    setUser(updated);
    setUserState(updated);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshUser, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}