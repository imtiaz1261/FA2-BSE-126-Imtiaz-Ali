import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { AuthProvider, useAuth } from "@/hooks/useAuth";
import { LoginForm } from "@/components/auth/LoginForm";
import { SignupForm } from "@/components/auth/SignupForm";
import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";
import { VerifyEmailNotice } from "@/components/auth/VerifyEmailNotice";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";
import { ChatWindow } from "@/features/chat/components/ChatWindow";
import { ThemeProvider } from "@chatline/design-system/theme/ThemeProvider";
function getInitialScreen() {
    const path = window.location.pathname;
    if (path === "/signup")
        return "signup";
    if (path === "/forgot-password")
        return "forgot-password";
    if (path === "/reset-password")
        return "reset-password";
    if (path === "/verify-email")
        return "verify-email";
    return "login";
}
function AuthGate() {
    const { user, isLoading, setSessionFromOAuth } = useAuth();
    const [screen, setScreen] = useState(getInitialScreen);
    const [showOnboarding, setShowOnboarding] = useState(false);
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token") ?? undefined;
    useEffect(() => {
        // Handle the OAuth callback: the access token arrives as a URL fragment
        // (see backend/app/routers/oauth.py) rather than a query param, since
        // fragments are never sent to the server or logged.
        if (window.location.pathname === "/oauth/complete") {
            const fragment = new URLSearchParams(window.location.hash.slice(1));
            const accessToken = fragment.get("access_token");
            // Strip the fragment from the URL immediately so the token never lingers
            // in browser history, regardless of whether setSessionFromOAuth succeeds.
            window.history.replaceState({}, "", "/");
            if (accessToken) {
                setSessionFromOAuth(accessToken).catch(() => {
                    // Session couldn't be established (e.g. expired token) — the user
                    // simply lands back on the login screen since `user` stays null.
                });
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    useEffect(() => {
        if (user && !user.onboarding_completed)
            setShowOnboarding(true);
    }, [user]);
    if (isLoading) {
        return (_jsx("div", { className: "flex min-h-screen items-center justify-center bg-canvas dark:bg-canvas-dark", children: _jsx("p", { className: "text-body text-ink/60 dark:text-ink-dark/60", children: "Loading\u2026" }) }));
    }
    if (user) {
        return (_jsxs(_Fragment, { children: [_jsx("div", { className: "h-screen", children: _jsx(ChatWindow, { userName: user.name || user.email }) }), _jsx(OnboardingModal, { open: showOnboarding, onComplete: () => setShowOnboarding(false) })] }));
    }
    switch (screen) {
        case "signup":
            return _jsx(SignupForm, { onSwitchToLogin: () => setScreen("login") });
        case "forgot-password":
            return _jsx(ForgotPasswordForm, { onBackToLogin: () => setScreen("login") });
        case "reset-password":
            return token ? (_jsx(ResetPasswordForm, { token: token, onDone: () => setScreen("login") })) : (_jsx(ForgotPasswordForm, { onBackToLogin: () => setScreen("login") }));
        case "verify-email":
            return _jsx(VerifyEmailNotice, { token: token });
        default:
            return (_jsx(LoginForm, { onSwitchToSignup: () => setScreen("signup"), onForgotPassword: () => setScreen("forgot-password") }));
    }
}
export default function App() {
    return (_jsx(ThemeProvider, { children: _jsx(AuthProvider, { children: _jsx(AuthGate, {}) }) }));
}
