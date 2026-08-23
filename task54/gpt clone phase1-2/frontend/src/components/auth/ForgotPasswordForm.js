import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { AuthCard } from "./AuthCard";
import { forgotPasswordSchema } from "@/lib/schemas";
import { authErrorMessage } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
export function ForgotPasswordForm({ onBackToLogin }) {
    const [sent, setSent] = useState(false);
    const [formError, setFormError] = useState(null);
    const { register, handleSubmit, formState: { errors, isSubmitting }, } = useForm({ resolver: zodResolver(forgotPasswordSchema) });
    const onSubmit = async (values) => {
        setFormError(null);
        try {
            await authApi.forgotPassword(values.email);
            setSent(true); // backend always returns the same neutral message
        }
        catch (err) {
            setFormError(authErrorMessage(err));
        }
    };
    if (sent) {
        return (_jsx(AuthCard, { title: "Check your email", subtitle: "We've sent a password reset link if that account exists.", children: _jsx(Button, { variant: "secondary", className: "w-full", onClick: onBackToLogin, children: "Back to log in" }) }));
    }
    return (_jsx(AuthCard, { title: "Reset your password", subtitle: "Enter your email and we'll send you a reset link.", footer: _jsx("button", { type: "button", onClick: onBackToLogin, className: "font-medium text-accent-600 dark:text-accent-400 hover:underline", children: "Back to log in" }), children: _jsxs("form", { onSubmit: handleSubmit(onSubmit), noValidate: true, className: "flex flex-col gap-4", children: [_jsx(Input, { label: "Email", type: "email", placeholder: "you@example.com", autoComplete: "email", ...register("email"), errorText: errors.email?.message }), formError && (_jsx("p", { role: "alert", className: "text-meta text-danger", children: formError })), _jsx(Button, { type: "submit", variant: "primary", className: "w-full", loading: isSubmitting, children: "Send reset link" })] }) }));
}
