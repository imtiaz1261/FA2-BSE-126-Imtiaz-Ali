import { jsx as _jsx } from "react/jsx-runtime";
import React from "react";
import { cn } from "@/lib/cn";
const sizeStyles = {
    sm: "h-8 w-8 text-meta",
    md: "h-10 w-10 text-body",
};
const toneStyles = {
    neutral: "bg-canvas-panel dark:bg-canvas-dark-panel text-ink dark:text-ink-dark",
    accent: "bg-accent-600/10 text-accent-600 dark:text-accent-400",
};
function getInitials(name) {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0)
        return "?";
    if (parts.length === 1)
        return parts[0].slice(0, 2).toUpperCase();
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}
export const Avatar = React.forwardRef(({ className, name, tone = "neutral", size = "sm", ...props }, ref) => (_jsx("div", { ref: ref, "aria-label": name, className: cn("inline-flex shrink-0 items-center justify-center rounded-full font-semibold", sizeStyles[size], toneStyles[tone], className), ...props, children: getInitials(name) })));
Avatar.displayName = "Avatar";
