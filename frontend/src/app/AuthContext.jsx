import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, getStoredToken, setStoredToken, clearStoredToken } from '../services/api';
import { useRouter } from './RouterContext';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(getStoredToken);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);
  const { navigate } = useRouter();

  const getDefaultRouteForRole = (role) => {
    switch (role) {
      case 'AUTHORITY':
        return '/authority/directives';
      case 'RECIPIENT':
        return '/recipient/inbox';
      case 'INVESTIGATOR':
        return '/investigator/intake';
      case 'AUDITOR':
        return '/auditor/ledger';
      default:
        return '/login';
    }
  };

  // Verify existing token on initial application mount
  useEffect(() => {
    let isMounted = true;
    const checkSession = async () => {
      const stored = getStoredToken();
      if (!stored) {
        if (isMounted) {
          setUser(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const principal = await authApi.me();
        if (isMounted) {
          setUser(principal);
          setToken(stored);
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          console.warn('Session verification failed, logging out:', err.message);
          clearStoredToken();
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
      }
    };

    checkSession();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (principalId, passphrase) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const res = await authApi.login(principalId, passphrase);
      setStoredToken(res.token);
      setToken(res.token);
      const profile = {
        principal_id: res.principal_id,
        role: res.role,
        name: res.name,
      };
      setUser(profile);
      setIsLoading(false);
      navigate(getDefaultRouteForRole(res.role));
      return { success: true, profile };
    } catch (err) {
      setIsLoading(false);
      setAuthError(err.message || 'Authentication failed. Please verify credentials.');
      return { success: false, error: err.message };
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } catch (e) {
      console.warn('Server logout error:', e);
    } finally {
      clearStoredToken();
      setToken(null);
      setUser(null);
      setIsLoading(false);
      navigate('/login');
    }
  };

  const clearError = useCallback(() => {
    setAuthError(null);
  }, []);

  const switchStation = async (principalId, passphrase) => {
    return login(principalId, passphrase);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        authError,
        login,
        logout,
        switchStation,
        clearError,
        getDefaultRouteForRole,
      }}
    >
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
