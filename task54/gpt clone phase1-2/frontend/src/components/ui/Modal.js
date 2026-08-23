import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";
export function Modal({ open, onClose, dismissible = true, title, children, className, }) {
    const dialogRef = useRef(null);
    useEffect(() => {
        if (!open)
            return;
        const previouslyFocused = document.activeElement;
        dialogRef.current?.focus();
        const handleKeyDown = (e) => {
            if (e.key === "Escape" && dismissible)
                onClose?.();
            if (e.key === "Tab") {
                // Basic focus trap
                const focusable = dialogRef.current?.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (!focusable || focusable.length === 0)
                    return;
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                }
                else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        };
        document.addEventListener("keydown", handleKeyDown);
        document.body.style.overflow = "hidden";
        return () => {
            document.removeEventListener("keydown", handleKeyDown);
            document.body.style.overflow = "";
            previouslyFocused?.focus();
        };
    }, [open, dismissible, onClose]);
    if (!open)
        return null;
    return (_jsxs("div", { className: "fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in", "aria-hidden": false, children: [_jsx("div", { className: "absolute inset-0 bg-black/40", onClick: dismissible ? onClose : undefined, "aria-hidden": "true" }), _jsxs("div", { ref: dialogRef, role: "dialog", "aria-modal": "true", "aria-label": title, tabIndex: -1, className: cn("relative w-full max-w-md rounded-control border border-border dark:border-border-dark", "bg-canvas dark:bg-canvas-dark-panel text-ink dark:text-ink-dark", "p-6 shadow-modal animate-scale-in focus:outline-none", className), children: [title && _jsx("h2", { className: "mb-4 text-heading font-semibold", children: title }), children] })] }));
}
