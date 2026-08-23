import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { AuthCard } from "./AuthCard";
import { OAuthButtons } from "./OAuthButtons";
import { loginSchema } from "@/lib/schemas";
import { authErrorMessage, useAuth } from "@/hooks/useAuth";
export function LoginForm({ onSwitchToSignup, onForgotPassword, }) {
    const { login } = useAuth();
    const [formError, setFormError] = useState(null);
    const { register, handleSubmit, formState: { errors, isSubmitting }, } = useForm({ resolver: zodResolver(loginSchema) });
    const onSubmit = async (values) => {
        setFormError(null);
        try {
            await login(values.email, values.password);
        }
        catch (err) {
            // Backend intentionally returns the same message for "no such user"
            // and "wrong password" to avoid leaking which emails are registered.
            setFormError(authErrorMessage(err));
        }
    };
    return (_jsxs(AuthCard, { title: "Welcome back", subtitle: "Log in to continue your conversations.", footer: _jsxs(_Fragment, { children: ["Don't have an account?", " ", _jsx("button", { type: "button", onClick: onSwitchToSignup, className: "font-medium text-accent-600 dark:text-accent-400 hover:underline", children: "Sign up" })] }), children: [_jsxs("form", { onSubmit: handleSubmit(onSubmit), noValidate: true, className: "flex flex-col gap-4", children: [_jsx(Input, { label: "Email", type: "email", placeholder: "you@example.com", autoComplete: "email", ...register("email"), errorText: errors.email?.message }), _jsxs("div", { className: "flex flex-col gap-1.5", children: [_jsx(Input, { label: "Password", type: "password", placeholder: "Your password", autoComplete: "current-password", ...register("password"), errorText: errors.password?.message }), _jsx("button", { type: "button", onClick: onForgotPassword, className: "self-end text-meta font-medium text-accent-600 dark:text-accent-400 hover:underline", children: "Forgot password?" })] }), formError && (_jsx("p", { role: "alert", className: "text-meta text-danger", children: formError })), _jsx(Button, { type: "submit", variant: "primary", className: "w-full", loading: isSubmitting, children: "Log in" })] }), _jsxs("div", { className: "my-4 flex items-center gap-3", children: [_jsx("div", { className: "h-px flex-1 bg-border dark:bg-border-dark" }), _jsx("span", { className: "text-meta text-ink/50 dark:text-ink-dark/50", children: "or" }), _jsx("div", { className: "h-px flex-1 bg-border dark:bg-border-dark" })] }), _jsx(OAuthButtons, {})] }));
}
