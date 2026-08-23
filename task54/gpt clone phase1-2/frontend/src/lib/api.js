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
let accessToken = null;
let refreshInFlight = null;
export function setAccessToken(token) {
    accessToken = token;
}
export function getAccessToken() {
    return accessToken;
}
export class ApiError extends Error {
    constructor(status, message) {
        super(message);
        this.status = status;
    }
}
async function doRefresh() {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: "POST",
            credentials: "include",
        });
        if (!res.ok)
            return false;
        const data = await res.json();
        setAccessToken(data.access_token);
        return true;
    }
    catch {
        return false;
    }
}
function refreshOnce() {
    if (!refreshInFlight) {
        refreshInFlight = doRefresh().finally(() => {
            refreshInFlight = null;
        });
    }
    return refreshInFlight;
}
export async function apiRequest(path, options = {}) {
    const { method = "GET", body, skipAuthRetry = false } = options;
    const doFetch = async () => fetch(`${API_BASE_URL}${path}`, {
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
        }
        catch {
            /* response wasn't JSON */
        }
        throw new ApiError(res.status, message);
    }
    if (res.status === 204)
        return undefined;
    return res.json();
}
export const authApi = {
    signup: (data) => apiRequest("/auth/signup", { method: "POST", body: data }),
    login: (data) => apiRequest("/auth/login", { method: "POST", body: data, skipAuthRetry: true }),
    refresh: () => apiRequest("/auth/refresh", { method: "POST", skipAuthRetry: true }),
    logout: () => apiRequest("/auth/logout", { method: "POST" }),
    verifyEmail: (token) => apiRequest("/auth/verify-email", { method: "POST", body: { token } }),
    forgotPassword: (email) => apiRequest("/auth/forgot-password", { method: "POST", body: { email } }),
    resetPassword: (token, new_password) => apiRequest("/auth/reset-password", {
        method: "POST",
        body: { token, new_password },
    }),
    me: () => apiRequest("/auth/me"),
    completeOnboarding: (data) => apiRequest("/auth/onboarding", { method: "POST", body: data }),
    oauthLoginUrl: (provider) => `${API_BASE_URL}/auth/oauth/${provider}/login`,
};
