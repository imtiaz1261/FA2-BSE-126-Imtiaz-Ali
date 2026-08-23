import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@chatline/design-system/components/Button";
import { Input } from "@chatline/design-system/components/Input";
import { Modal } from "@/components/ui/Modal";
import { onboardingSchema } from "@/lib/schemas";
import { authApi } from "@/lib/api";
import { authErrorMessage, useAuth } from "@/hooks/useAuth";
const USE_CASES = [
    { value: "work", label: "Work & productivity" },
    { value: "learning", label: "Learning & research" },
    { value: "coding", label: "Coding & development" },
    { value: "creative", label: "Creative writing" },
    { value: "personal", label: "Personal use" },
];
const THEMES = [
    { value: "light", label: "Light" },
    { value: "dark", label: "Dark" },
    { value: "system", label: "Match system" },
];
const STEP_LABELS = ["About you", "What you're here for", "Look & feel"];
/**
 * Shown once, right after signup/first login, when `user.onboarding_completed`
 * is false. Not dismissible (see Modal's `dismissible={false}`) — the person
 * completes all 3 steps, matching the "first-run onboarding modal" spec.
 */
export function OnboardingModal({ open, onComplete }) {
    const { user, refreshUser } = useAuth();
    const [step, setStep] = useState(0);
    const [submitError, setSubmitError] = useState(null);
    const { register, handleSubmit, watch, setValue, trigger, formState: { errors, isSubmitting }, } = useForm({
        resolver: zodResolver(onboardingSchema),
        defaultValues: {
            name: user?.name ?? "",
            useCase: "",
            themePreference: "system",
            dataUsageOptIn: false,
        },
    });
    const values = watch();
    const goNext = async () => {
        const fieldsByStep = [["name"], ["useCase"], ["themePreference"]];
        const valid = await trigger(fieldsByStep[step]);
        if (valid)
            setStep((s) => Math.min(s + 1, STEP_LABELS.length - 1));
    };
    const goBack = () => setStep((s) => Math.max(s - 1, 0));
    const onSubmit = async (data) => {
        setSubmitError(null);
        try {
            await authApi.completeOnboarding({
                name: data.name,
                use_case: data.useCase,
                theme_preference: data.themePreference,
                data_usage_opt_in: data.dataUsageOptIn,
            });
            await refreshUser();
            onComplete();
        }
        catch (err) {
            setSubmitError(authErrorMessage(err));
        }
    };
    return (_jsxs(Modal, { open: open, dismissible: false, title: "Set up your account", children: [_jsx("div", { className: "mb-5 flex items-center gap-2", children: STEP_LABELS.map((label, i) => (_jsx("div", { className: "flex flex-1 items-center gap-2", children: _jsx("div", { className: `h-1.5 flex-1 rounded-full ${i <= step ? "bg-accent-600 dark:bg-accent-400" : "bg-border dark:bg-border-dark"}` }) }, label))) }), _jsxs("p", { className: "mb-4 text-meta text-ink/60 dark:text-ink-dark/60", children: ["Step ", step + 1, " of ", STEP_LABELS.length, ": ", STEP_LABELS[step]] }), _jsxs("form", { onSubmit: handleSubmit(onSubmit), noValidate: true, children: [step === 0 && (_jsx("div", { className: "flex flex-col gap-4", children: _jsx(Input, { label: "What should we call you?", placeholder: "Ada Lovelace", ...register("name"), errorText: errors.name?.message }) })), step === 1 && (_jsxs("fieldset", { className: "flex flex-col gap-2", children: [_jsx("legend", { className: "mb-1 text-meta font-medium text-ink dark:text-ink-dark", children: "What will you mostly use Chatline for?" }), USE_CASES.map((option) => (_jsxs("label", { className: `flex cursor-pointer items-center gap-3 rounded-control border px-3 py-2.5 text-body transition-colors ${values.useCase === option.value
                                    ? "border-accent-600 dark:border-accent-400 bg-accent-600/5"
                                    : "border-border dark:border-border-dark hover:border-accent-600/50"}`, children: [_jsx("input", { type: "radio", value: option.value, className: "accent-accent-600", ...register("useCase") }), option.label] }, option.value))), errors.useCase && _jsx("p", { className: "text-meta text-danger", children: errors.useCase.message })] })), step === 2 && (_jsxs("div", { className: "flex flex-col gap-5", children: [_jsxs("fieldset", { className: "flex flex-col gap-2", children: [_jsx("legend", { className: "mb-1 text-meta font-medium text-ink dark:text-ink-dark", children: "Choose a theme" }), _jsx("div", { className: "flex gap-2", children: THEMES.map((option) => (_jsx("button", { type: "button", onClick: () => setValue("themePreference", option.value, { shouldValidate: true }), className: `flex-1 rounded-control border px-3 py-2 text-meta font-medium transition-colors ${values.themePreference === option.value
                                                ? "border-accent-600 dark:border-accent-400 text-accent-600 dark:text-accent-400"
                                                : "border-border dark:border-border-dark text-ink/70 dark:text-ink-dark/70"}`, children: option.label }, option.value))) })] }), _jsxs("label", { className: "flex items-start gap-3 text-body", children: [_jsx("input", { type: "checkbox", className: "mt-1 accent-accent-600", ...register("dataUsageOptIn") }), _jsx("span", { className: "text-ink/80 dark:text-ink-dark/80", children: "Help improve Chatline by allowing my conversations to be used for model improvement. You can change this anytime in Settings." })] })] })), submitError && (_jsx("p", { role: "alert", className: "mt-4 text-meta text-danger", children: submitError })), _jsxs("div", { className: "mt-6 flex justify-between gap-2", children: [_jsx(Button, { type: "button", variant: "ghost", onClick: goBack, disabled: step === 0, children: "Back" }), step < STEP_LABELS.length - 1 ? (_jsx(Button, { type: "button", variant: "primary", onClick: goNext, children: "Continue" })) : (_jsx(Button, { type: "submit", variant: "primary", loading: isSubmitting, children: "Finish setup" }))] })] })] }));
}
