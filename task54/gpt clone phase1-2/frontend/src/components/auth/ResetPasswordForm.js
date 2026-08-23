import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { AuthCard } from "./AuthCard";
import { resetPasswordSchema } from "@/lib/schemas";
import { authErrorMessage } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
/** `token` comes from the ?token= query param on the /reset-password page. */
export function ResetPasswordForm({ token, onDone }) {
    const [done, setDone] = useState(false);
    const [formError, setFormError] = useState(null);
    const { register, handleSubmit, formState: { errors, isSubmitting }, } = useForm({ resolver: zodResolver(resetPasswordSchema) });
    const onSubmit = async (values) => {
        setFormError(null);
        try {
            await authApi.resetPassword(token, values.password);
            setDone(true);
        }
        catch (err) {
            setFormError(authErrorMessage(err));
        }
    };
    if (done) {
        return (_jsx(AuthCard, { title: "Password updated", subtitle: "Log in with your new password.", children: _jsx(Button, { variant: "primary", className: "w-full", onClick: onDone, children: "Continue to log in" }) }));
    }
    return (_jsx(AuthCard, { title: "Choose a new password", children: _jsxs("form", { onSubmit: handleSubmit(onSubmit), noValidate: true, className: "flex flex-col gap-4", children: [_jsx(Input, { label: "New password", type: "password", autoComplete: "new-password", helperText: !errors.password ? "Use 8+ characters with a mix of case and a number." : undefined, ...register("password"), errorText: errors.password?.message }), _jsx(Input, { label: "Confirm new password", type: "password", autoComplete: "new-password", ...register("confirmPassword"), errorText: errors.confirmPassword?.message }), formError && (_jsx("p", { role: "alert", className: "text-meta text-danger", children: formError })), _jsx(Button, { type: "submit", variant: "primary", className: "w-full", loading: isSubmitting, children: "Reset password" })] }) }));
}
