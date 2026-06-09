'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getMe, UserResponse, clearTokens } from './api';

interface AuthContextType {
  user: UserResponse | null;
  isLoading: boolean;
  checkAuth: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const checkAuth = async () => {
    setIsLoading(true);
    try {
      const userData = await getMe();
      setUser(userData);
      
      // If we are on login or register, redirect to home
      if (pathname === '/login' || pathname === '/register') {
        router.push('/');
      }
    } catch (e) {
      setUser(null);
      // If we are not on login or register, redirect to login
      if (pathname !== '/login' && pathname !== '/register') {
        router.push('/login');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
      router.push('/login');
    }
  };

  useEffect(() => {
    checkAuth();
    
    // Listen for auth expiration events from api.ts
    const handleAuthExpired = () => {
      logout();
    };
    
    window.addEventListener('auth_expired', handleAuthExpired);
    return () => {
      window.removeEventListener('auth_expired', handleAuthExpired);
    };
  }, [pathname]); // Re-check when path changes

  return (
    <AuthContext.Provider value={{ user, isLoading, checkAuth, logout }}>
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
