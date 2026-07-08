import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  clearAuth,
  fetchMe,
  getToken,
  googleLogin,
  login,
  register,
  setAuth,
} from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await fetchMe();
      setUser(me);
    } catch {
      clearAuth();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const signIn = async (email, password) => {
    await login(email, password);
    await loadUser();
  };

  const signUp = async (email, password, fullName) => {
    await register(email, password, fullName);
    await loadUser();
  };

  const signInWithGoogle = async (idToken) => {
    const data = await googleLogin(idToken);
    setAuth(data.access_token, '');
    const profile = await fetchMe();
    setAuth(data.access_token, profile.email);
    setUser(profile);
  };

  const signOut = () => {
    clearAuth();
    setUser(null);
    window.location.href = '/';
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, signIn, signUp, signInWithGoogle, signOut, refreshUser: loadUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
