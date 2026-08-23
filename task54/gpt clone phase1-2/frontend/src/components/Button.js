import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React from "react";
import { cn } from "@/lib/cn";
const sizeStyles = {
    sm: "h-8 px-3 text-meta gap-1.5",
    md: "h-10 px-4 text-body gap-2",
    lg: "h-12 px-5 text-body gap-2",
};
const variantStyles = {
    primary: "bg-accent-600 text-white hover:bg-accent-700 active:bg-accent-700 disabled:bg-accent-600/50",
    secondary: "bg-transparent text-ink dark:text-ink-dark border border-border dark:border-border-dark hover:border-accent-600 dark:hover:border-accent-400",
    ghost: "bg-transparent text-ink dark:text-ink-dark hover:bg-canvas-panel dark:hover:bg-canvas-dark-panel",
};
export const Button = React.forwardRef(({ className, variant = "primary", size = "md", loading = false, disabled, leftIcon, rightIcon, children, ...props }, ref) => (_jsxs("button", { ref: ref, type: "button", disabled: disabled || loading, "aria-busy": loading || undefined, className: cn("inline-flex items-center justify-center rounded-control font-medium transition-colors duration-150 select-none disabled:cursor-not-allowed disabled:opacity-60", sizeStyles[size], variantStyles[variant], className), ...props, children: [loading ? (_jsxs("svg", { className: "h-4 w-4 animate-spin", viewBox: "0 0 24 24", fill: "none", "aria-hidden": "true", children: [_jsx("circle", { className: "opacity-25", cx: "12", cy: "12", r: "10", stroke: "currentColor", strokeWidth: "4" }), _jsx("path", { className: "opacity-75", fill: "currentColor", d: "M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" })] })) : (leftIcon), children, !loading && rightIcon] })));
Button.displayName = "Button";
