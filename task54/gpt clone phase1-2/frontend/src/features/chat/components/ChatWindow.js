import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { useChatStore } from "@/store/chatStore";
import { useAuth } from "@/hooks/useAuth";
import { ThemeToggle } from "@chatline/design-system/theme/ThemeToggle";
import { Button } from "@chatline/design-system/components/Button";
import { MessageBubble } from "./MessageBubble";
import { Composer } from "./Composer";
/** Px from the bottom within which we still consider the user "at the
 * bottom" — small buffer so sub-pixel scroll rounding doesn't false-trigger
 * the "jump to latest" button. */
const BOTTOM_THRESHOLD_PX = 80;
export function ChatWindow({ userName }) {
    const { messages, streamingMessageId } = useChatStore();
    const { logout } = useAuth();
    const scrollRef = useRef(null);
    const [autoScroll, setAutoScroll] = useState(true);
    const isNearBottom = () => {
        const el = scrollRef.current;
        if (!el)
            return true;
        return el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD_PX;
    };
    // Re-enable auto-scroll when the user scrolls back down themselves;
    // disable it the moment they scroll up, away from the bottom.
    const handleScroll = () => {
        setAutoScroll(isNearBottom());
    };
    // Follow new content (new messages, or streaming tokens) only while
    // auto-scroll is enabled — this is what "pauses if the user manually
    // scrolls up" in practice.
    useEffect(() => {
        if (autoScroll && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, autoScroll]);
    const jumpToLatest = () => {
        setAutoScroll(true);
        if (scrollRef.current) {
            scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
        }
    };
    return (_jsxs("div", { className: "flex h-full min-h-0 flex-col bg-canvas dark:bg-canvas-dark", children: [_jsxs("header", { className: "flex shrink-0 items-center justify-between border-b border-border dark:border-border-dark px-4 py-2.5", children: [_jsx("p", { className: "text-body font-semibold text-ink dark:text-ink-dark", children: "Chatline" }), _jsxs("div", { className: "flex items-center gap-2", children: [_jsx("span", { className: "text-meta text-ink/50 dark:text-ink-dark/50", children: userName }), _jsx(ThemeToggle, {}), _jsx(Button, { variant: "ghost", size: "sm", onClick: () => void logout(), children: "Log out" })] })] }), _jsxs("div", { className: "relative flex-1 min-h-0", children: [_jsx("div", { ref: scrollRef, onScroll: handleScroll, className: "h-full overflow-y-auto px-4 py-6", children: _jsx("div", { className: "mx-auto flex max-w-3xl flex-col gap-6", children: messages.length === 0 ? (_jsx(EmptyState, {})) : (messages.map((message) => (_jsx(MessageBubble, { message: message, isStreaming: message.id === streamingMessageId, someStreamActive: streamingMessageId !== null, userName: userName }, message.id)))) }) }), !autoScroll && messages.length > 0 && (_jsxs("button", { type: "button", onClick: jumpToLatest, className: "absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5 rounded-full border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark-panel px-3.5 py-1.5 text-meta font-medium text-ink dark:text-ink-dark shadow-modal transition-colors hover:border-accent-600 dark:hover:border-accent-400", children: [_jsx(DownArrowIcon, {}), "Jump to latest"] }))] }), _jsx(Composer, {})] }));
}
function EmptyState() {
    return (_jsxs("div", { className: "flex flex-col items-center justify-center py-20 text-center", children: [_jsx("p", { className: "text-heading font-semibold text-ink dark:text-ink-dark", children: "Start a conversation" }), _jsx("p", { className: "mt-1.5 max-w-sm text-body text-ink/60 dark:text-ink-dark/60", children: "Ask a question, paste some code, or just say hello." })] }));
}
function DownArrowIcon() {
    return (_jsx("svg", { width: "12", height: "12", viewBox: "0 0 16 16", fill: "none", "aria-hidden": "true", children: _jsx("path", { d: "M8 2.5v10M3.5 8.5 8 13l4.5-4.5", stroke: "currentColor", strokeWidth: "1.4", strokeLinecap: "round", strokeLinejoin: "round" }) }));
}
