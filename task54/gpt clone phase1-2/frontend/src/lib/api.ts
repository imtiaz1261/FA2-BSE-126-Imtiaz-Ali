/**
 * Thin fetch wrapper around the FastAPI auth endpoints.
 *
 * - The access token lives in memory only (module-level variable), never in
 *   localStorage — that keeps it out of reach of a XSS-injected script that
 *   reads storage. It's lost on full page reload, which is why we call
 *   `refresh()` once on app boot (see hooks/useAuth.tsx).
 * - The refresh token is an httpOnly cookie the browser sends automatically
 *   (`credentials: "include"`); JS never touches it.
 * - On any 401, we transparently try one refresh and replay the original
 *   request; concurrent 401s share a single in-flight refresh call.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

let accessToken: string | null = null;
let refreshInFlight: Promise<boolean> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function doRefresh(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) return false;
    const data = await res.json();
    setAccessToken(data.access_token);
    return true;
  } catch {
    return false;
  }
}

function refreshOnce(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Skip the automatic refresh-and-retry (used by the refresh call itself). */
  skipAuthRetry?: boolean;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, skipAuthRetry = false } = options;

  const doFetch = async () =>
    fetch(`${API_BASE_URL}${path}`, {
      method,
      credentials: "include", // send the httpOnly refresh cookie when relevant
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

  let res = await doFetch();

  if (res.status === 401 && !skipAuthRetry) {
    const refreshed = await refreshOnce();
    if (refreshed) {
      res = await doFetch();
    }
  }

  if (!res.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const data = await res.json();
      message = data.detail ?? message;
    } catch {
      /* response wasn't JSON */
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---- Typed endpoint helpers ---------------------------------------------------

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  is_verified: boolean;
  theme_preference: "light" | "dark" | "system";
  data_usage_opt_in: boolean;
  onboarding_completed: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export const authApi = {
  signup: (data: { email: string; password: string; name?: string }) =>
    apiRequest<TokenResponse>("/auth/signup", { method: "POST", body: data }),

  login: (data: { email: string; password: string }) =>
    apiRequest<TokenResponse>("/auth/login", { method: "POST", body: data, skipAuthRetry: true }),

  refresh: () =>
    apiRequest<TokenResponse>("/auth/refresh", { method: "POST", skipAuthRetry: true }),

  logout: () => apiRequest<{ message: string }>("/auth/logout", { method: "POST" }),

  verifyEmail: (token: string) =>
    apiRequest<{ message: string }>("/auth/verify-email", { method: "POST", body: { token } }),

  forgotPassword: (email: string) =>
    apiRequest<{ message: string }>("/auth/forgot-password", { method: "POST", body: { email } }),

  resetPassword: (token: string, new_password: string) =>
    apiRequest<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: { token, new_password },
    }),

  me: () => apiRequest<AuthUser>("/auth/me"),

  completeOnboarding: (data: {
    name: string;
    use_case: string;
    theme_preference: "light" | "dark" | "system";
    data_usage_opt_in: boolean;
  }) => apiRequest<AuthUser>("/auth/onboarding", { method: "POST", body: data }),

  oauthLoginUrl: (provider: "google" | "github" | "microsoft") =>
    `${API_BASE_URL}/auth/oauth/${provider}/login`,
};
