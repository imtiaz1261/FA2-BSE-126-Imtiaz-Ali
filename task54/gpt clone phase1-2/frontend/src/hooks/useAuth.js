import { jsx as _jsx } from "react/jsx-runtime";
import { createContext, useCallback, useContext, useEffect, useState, } from "react";
import { ApiError, authApi, setAccessToken } from "@/lib/api";
const AuthContext = createContext(undefined);
export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
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
            }
            catch {
                setAccessToken(null);
                setUser(null);
            }
            finally {
                setIsLoading(false);
            }
        })();
    }, []);
    const login = useCallback(async (email, password) => {
        const result = await authApi.login({ email, password });
        setAccessToken(result.access_token);
        setUser(result.user);
    }, []);
    const signup = useCallback(async (email, password, name) => {
        const result = await authApi.signup({ email, password, name });
        setAccessToken(result.access_token);
        setUser(result.user);
    }, []);
    const logout = useCallback(async () => {
        try {
            await authApi.logout();
        }
        finally {
            setAccessToken(null);
            setUser(null);
        }
    }, []);
    const refreshUser = useCallback(async () => {
        const me = await authApi.me();
        setUser(me);
    }, []);
    const setSessionFromOAuth = useCallback(async (token) => {
        setAccessToken(token);
        const me = await authApi.me();
        setUser(me);
    }, []);
    return (_jsx(AuthContext.Provider, { value: { user, isLoading, login, signup, logout, refreshUser, setSessionFromOAuth }, children: children }));
}
export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx)
        throw new Error("useAuth must be used within an AuthProvider");
    return ctx;
}
/** Narrow an ApiError's message for display, with a generic fallback. */
export function authErrorMessage(err) {
    if (err instanceof ApiError)
        return err.message;
    return "Something went wrong. Please try again.";
}
