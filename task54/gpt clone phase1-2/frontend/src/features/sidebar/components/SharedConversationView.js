import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { Avatar } from "@chatline/design-system/components/Avatar";
import { MarkdownRenderer } from "@/features/chat/components/MarkdownRenderer";
import { sharedConversationApi } from "@/lib/conversationsApi";
import { ApiError } from "@/lib/api";
/** Rendered at /share/{token} — no auth, no sidebar, read-only. */
export function SharedConversationView({ token }) {
    const [conversation, setConversation] = useState(null);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    useEffect(() => {
        sharedConversationApi
            .get(token)
            .then(setConversation)
            .catch((err) => {
            setError(err instanceof ApiError && err.status === 404
                ? "This share link is invalid or has been revoked."
                : "Couldn't load this conversation.");
        })
            .finally(() => setIsLoading(false));
    }, [token]);
    if (isLoading) {
        return (_jsx("div", { className: "flex min-h-screen items-center justify-center bg-canvas dark:bg-canvas-dark", children: _jsx("p", { className: "text-body text-ink/60 dark:text-ink-dark/60", children: "Loading\u2026" }) }));
    }
    if (error || !conversation) {
        return (_jsxs("div", { className: "flex min-h-screen flex-col items-center justify-center gap-2 bg-canvas dark:bg-canvas-dark px-4 text-center", children: [_jsx("p", { className: "text-heading font-semibold text-ink dark:text-ink-dark", children: "Link unavailable" }), _jsx("p", { className: "text-body text-ink/60 dark:text-ink-dark/60", children: error })] }));
    }
    return (_jsxs("div", { className: "min-h-screen bg-canvas dark:bg-canvas-dark", children: [_jsx("header", { className: "border-b border-border dark:border-border-dark px-4 py-3", children: _jsxs("div", { className: "mx-auto flex max-w-3xl items-center justify-between", children: [_jsx("p", { className: "text-body font-semibold text-ink dark:text-ink-dark", children: conversation.title }), _jsx("span", { className: "rounded-full bg-canvas-panel dark:bg-canvas-dark-panel px-2.5 py-0.5 text-meta font-medium text-ink/50 dark:text-ink-dark/50", children: "Read-only" })] }) }), _jsx("div", { className: "mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6", children: conversation.messages.map((message, i) => (_jsxs("div", { className: `flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`, children: [_jsx(Avatar, { name: message.role === "user" ? "You" : "Assistant", tone: message.role === "user" ? "neutral" : "accent", size: "sm", className: "mt-0.5 shrink-0" }), _jsx("div", { className: `max-w-[75%] rounded-bubble px-4 py-2.5 ${message.role === "user"
                                ? "bg-accent-600/10 text-ink dark:text-ink-dark"
                                : "bg-canvas-panel dark:bg-canvas-dark-panel text-ink dark:text-ink-dark"}`, children: message.role === "user" ? (_jsx("p", { className: "whitespace-pre-wrap text-body", children: message.content })) : (_jsx(MarkdownRenderer, { content: message.content })) })] }, i))) })] }));
}
