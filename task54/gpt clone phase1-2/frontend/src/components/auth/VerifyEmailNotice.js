import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { Button } from "@chatline/design-system/components/Button";
import { AuthCard } from "./AuthCard";
import { authApi } from "@/lib/api";
import { authErrorMessage, useAuth } from "@/hooks/useAuth";
/**
 * Two jobs in one component:
 * - No `token` prop: shown right after signup, telling the user to check
 *   their inbox.
 * - `token` prop present (user landed on /verify-email?token=... from the
 *   email link): automatically confirms the token with the backend.
 */
export function VerifyEmailNotice({ token }) {
    const { refreshUser, user } = useAuth();
    const [status, setStatus] = useState(token ? "verifying" : "pending");
    const [error, setError] = useState(null);
    useEffect(() => {
        if (!token)
            return;
        (async () => {
            try {
                await authApi.verifyEmail(token);
                await refreshUser();
                setStatus("success");
            }
            catch (err) {
                setError(authErrorMessage(err));
                setStatus("error");
            }
        })();
    }, [token, refreshUser]);
    if (status === "verifying") {
        return _jsx(AuthCard, { title: "Verifying your email\u2026", children: null });
    }
    if (status === "success") {
        return (_jsx(AuthCard, { title: "Email verified", subtitle: "You're all set.", children: _jsxs("p", { className: "text-body text-ink/70 dark:text-ink-dark/70", children: ["Thanks for confirming, ", user?.name ?? "there", "."] }) }));
    }
    if (status === "error") {
        return (_jsx(AuthCard, { title: "Verification failed", children: _jsx("p", { className: "text-meta text-danger", children: error }) }));
    }
    return (_jsxs(AuthCard, { title: "Check your email", subtitle: "We've sent a verification link to your inbox.", children: [_jsx("p", { className: "mb-4 text-body text-ink/70 dark:text-ink-dark/70", children: "Click the link in the email to verify your account. The link expires in 24 hours." }), _jsx(Button, { variant: "secondary", className: "w-full", onClick: () => window.location.reload(), children: "I've verified \u2014 refresh" })] }));
}
