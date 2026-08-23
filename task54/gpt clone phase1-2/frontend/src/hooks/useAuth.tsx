import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { ApiError, AuthUser, authApi, setAccessToken } from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  /** True while the initial silent-refresh-on-load check is running. */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  /** Used by the OAuth callback page once it has an access token from the URL fragment. */
  setSessionFromOAuth: (accessToken: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On first load there's no access token in memory (it's not persisted), so
  // we attempt a silent refresh using the httpOnly cookie. If it succeeds,
  // the user is still logged in from a previous visit.
  useEffect(() => {
    (async () => {
      try {
        const result = await authApi.refresh();
        setAccessToken(result.access_token);
        setUser(result.user);
      } catch {
        setAccessToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await authApi.login({ email, password });
    setAccessToken(result.access_token);
    setUser(result.user);
  }, []);

  const signup = useCallback(async (email: string, password: string, name?: string) => {
    const result = await authApi.signup({ email, password, name });
    setAccessToken(result.access_token);
    setUser(result.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await authApi.me();
    setUser(me);
  }, []);

  const setSessionFromOAuth = useCallback(async (token: string) => {
    setAccessToken(token);
    const me = await authApi.me();
    setUser(me);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, login, signup, logout, refreshUser, setSessionFromOAuth }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

/** Narrow an ApiError's message for display, with a generic fallback. */
export function authErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Something went wrong. Please try again.";
}
