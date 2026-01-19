import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api, User } from '../api/client';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (provider: 'google' | 'github') => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = async () => {
    try {
      const userData = await api.auth.getMe();
      setUser(userData);
      setError(null);
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
  }, []);

  const login = (provider: 'google' | 'github') => {
    const url = provider === 'google'
      ? api.auth.getGoogleLoginUrl()
      : api.auth.getGithubLoginUrl();
    window.location.href = url;
  };

  const logout = async () => {
    try {
      await api.auth.logout();
      setUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Logout failed');
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
