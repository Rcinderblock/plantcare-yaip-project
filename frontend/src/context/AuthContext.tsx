import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiRequest, login, logout, registerUser } from "../api/client";
import type { User } from "../types/api";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signUp: (username: string, email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    try {
      const profile = await apiRequest<User>("/auth/me/");
      setUser(profile);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  const signIn = useCallback(
    async (username: string, password: string) => {
      const result = await login(username, password);
      setUser(result.user);
      setLoading(false);
    },
    [],
  );

  const signUp = useCallback(
    async (username: string, email: string, password: string) => {
      await registerUser(username, email, password);
      await signIn(username, password);
    },
    [signIn],
  );

  const signOut = useCallback(async () => {
    try {
      await logout();
    } finally {
      setUser(null);
      setLoading(false);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      loading,
      signIn,
      signUp,
      signOut,
    }),
    [loading, signIn, signOut, signUp, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
