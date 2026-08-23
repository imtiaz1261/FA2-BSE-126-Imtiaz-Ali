import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { AuthCard } from "./AuthCard";
import { OAuthButtons } from "./OAuthButtons";
import { signupSchema } from "@/lib/schemas";
import { authErrorMessage, useAuth } from "@/hooks/useAuth";
export function SignupForm({ onSwitchToLogin }) {
    const { signup } = useAuth();
    const [formError, setFormError] = useState(null);
    const { register, handleSubmit, formState: { errors, isSubmitting }, } = useForm({ resolver: zodResolver(signupSchema) });
    const onSubmit = async (values) => {
        setFormError(null);
        try {
            await signup(values.email, values.password, values.name || undefined);
            // Successful signup logs the user in immediately (see backend
            // /auth/signup); the caller can now show the "verify your email" /
            // onboarding flow based on `user.is_verified` / `onboarding_completed`.
        }
        catch (err) {
            setFormError(authErrorMessage(err));
        }
    };
    return (_jsxs(AuthCard, { title: "Create your account", subtitle: "Start chatting in under a minute.", footer: _jsxs(_Fragment, { children: ["Already have an account?", " ", _jsx("button", { type: "button", onClick: onSwitchToLogin, className: "font-medium text-accent-600 dark:text-accent-400 hover:underline", children: "Log in" })] }), children: [_jsxs("form", { onSubmit: handleSubmit(onSubmit), noValidate: true, className: "flex flex-col gap-4", children: [_jsx(Input, { label: "Name", placeholder: "Ada Lovelace", ...register("name"), errorText: errors.name?.message }), _jsx(Input, { label: "Email", type: "email", placeholder: "you@example.com", autoComplete: "email", ...register("email"), errorText: errors.email?.message }), _jsx(Input, { label: "Password", type: "password", placeholder: "At least 8 characters", autoComplete: "new-password", helperText: !errors.password ? "Use 8+ characters with a mix of case and a number." : undefined, ...register("password"), errorText: errors.password?.message }), formError && (_jsx("p", { role: "alert", className: "text-meta text-danger", children: formError })), _jsx(Button, { type: "submit", variant: "primary", className: "w-full", loading: isSubmitting, children: "Create account" })] }), _jsxs("div", { className: "my-4 flex items-center gap-3", children: [_jsx("div", { className: "h-px flex-1 bg-border dark:bg-border-dark" }), _jsx("span", { className: "text-meta text-ink/50 dark:text-ink-dark/50", children: "or" }), _jsx("div", { className: "h-px flex-1 bg-border dark:bg-border-dark" })] }), _jsx(OAuthButtons, {}), _jsx("p", { className: "mt-4 text-center text-meta text-ink/50 dark:text-ink-dark/50", children: "By continuing you agree to our Terms and Privacy Policy." })] }));
}
