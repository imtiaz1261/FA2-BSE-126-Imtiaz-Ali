import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from "@/lib/cn";
export function Card({ className, children, ...props }) {
    return (_jsx("div", { className: cn("rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark-panel text-ink dark:text-ink-dark p-4", className), ...props, children: children }));
}
