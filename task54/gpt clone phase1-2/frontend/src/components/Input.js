import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React, { useId } from "react";
import { cn } from "@/lib/cn";
export const Input = React.forwardRef(({ className, label, helperText, errorText, leftIcon, id, ...props }, ref) => {
    const inputId = id ?? useId();
    return (_jsxs("div", { className: "flex flex-col gap-1.5", children: [label && (_jsx("label", { htmlFor: inputId, className: "text-meta font-medium text-ink dark:text-ink-dark", children: label })), _jsxs("div", { className: "relative flex items-center", children: [leftIcon && (_jsx("span", { className: "pointer-events-none absolute left-3 flex h-4 w-4 items-center justify-center text-ink/50 dark:text-ink-dark/50", children: leftIcon })), _jsx("input", { ref: ref, id: inputId, "aria-invalid": !!errorText || undefined, className: cn("h-10 w-full rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark text-body px-3 placeholder:text-ink/40 dark:placeholder:text-ink-dark/40 transition-colors focus-visible:border-accent", leftIcon && "pl-9", errorText && "border-danger focus-visible:outline-danger", "disabled:cursor-not-allowed disabled:opacity-60", className), ...props })] }), errorText ? (_jsx("p", { className: "text-meta text-danger", children: errorText })) : (helperText && _jsx("p", { className: "text-meta text-ink/60 dark:text-ink-dark/60", children: helperText }))] }));
});
Input.displayName = "Input";
