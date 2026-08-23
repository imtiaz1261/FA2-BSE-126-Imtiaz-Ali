import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Card } from "@chatline/design-system/components/Card";
export function AuthCard({ title, subtitle, children, footer, }) {
    return (_jsx("div", { className: "flex min-h-screen items-center justify-center bg-canvas-panel dark:bg-canvas-dark px-4", children: _jsxs("div", { className: "w-full max-w-sm", children: [_jsxs("div", { className: "mb-6 text-center", children: [_jsx("h1", { className: "text-display font-semibold text-ink dark:text-ink-dark", children: title }), subtitle && (_jsx("p", { className: "mt-1 text-body text-ink/60 dark:text-ink-dark/60", children: subtitle }))] }), _jsx(Card, { className: "p-6", children: children }), footer && (_jsx("p", { className: "mt-4 text-center text-meta text-ink/60 dark:text-ink-dark/60", children: footer }))] }) }));
}
