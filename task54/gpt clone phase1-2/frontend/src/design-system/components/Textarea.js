import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React, { useEffect, useId, useRef } from "react";
import { cn } from "@/lib/cn";
export const Textarea = React.forwardRef(({ className, label, helperText, errorText, autoGrow = false, maxRows = 6, id, onChange, style, ...props }, ref) => {
    const textareaId = id ?? useId();
    const innerRef = useRef(null);
    useEffect(() => {
        if (!autoGrow || !innerRef.current)
            return;
        const el = innerRef.current;
        el.style.height = "auto";
        const lineHeight = Number.parseFloat(getComputedStyle(el).lineHeight || "20") || 20;
        const maxHeight = lineHeight * maxRows;
        el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
    }, [autoGrow, maxRows, props.value]);
    return (_jsxs("div", { className: "flex flex-col gap-1.5", children: [label && (_jsx("label", { htmlFor: textareaId, className: "text-meta font-medium text-ink dark:text-ink-dark", children: label })), _jsx("textarea", { ref: (node) => {
                    innerRef.current = node;
                    if (typeof ref === "function") {
                        ref(node);
                    }
                    else if (ref) {
                        ref.current = node;
                    }
                }, id: textareaId, "aria-invalid": !!errorText || undefined, onChange: onChange, className: cn("min-h-20 w-full resize-none rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark text-body px-3 py-2 placeholder:text-ink/40 dark:placeholder:text-ink-dark/40 transition-colors focus-visible:border-accent-600 disabled:cursor-not-allowed disabled:opacity-60", errorText && "border-danger focus-visible:outline-danger", className), style: style, ...props }), errorText ? (_jsx("p", { className: "text-meta text-danger", children: errorText })) : (helperText && _jsx("p", { className: "text-meta text-ink/60 dark:text-ink-dark/60", children: helperText }))] }));
});
Textarea.displayName = "Textarea";
