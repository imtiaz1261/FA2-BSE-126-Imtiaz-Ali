import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { Avatar } from "@chatline/design-system/components/Avatar";
import { Button } from "@chatline/design-system/components/Button";
import { Textarea } from "@chatline/design-system/components/Textarea";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { TypingCursor } from "./TypingCursor";
import { MessageToolbar } from "./MessageToolbar";
import { useChatStore } from "@/store/chatStore";
export function MessageBubble({ message, isStreaming, someStreamActive, userName, }) {
    const { regenerate, editAndResend, setFeedback } = useChatStore();
    const [isEditing, setIsEditing] = useState(false);
    const [draft, setDraft] = useState(message.content);
    const isUser = message.role === "user";
    const submitEdit = () => {
        const trimmed = draft.trim();
        if (!trimmed)
            return;
        setIsEditing(false);
        void editAndResend(message.id, trimmed);
    };
    return (_jsxs("div", { className: cn("group flex gap-3", isUser && "flex-row-reverse"), children: [_jsx(Avatar, { name: isUser ? userName : "Assistant", tone: isUser ? "neutral" : "accent", size: "sm", className: "mt-0.5 shrink-0" }), _jsxs("div", { className: cn("flex max-w-[75%] flex-col gap-1.5", isUser && "items-end"), children: [isEditing ? (_jsxs("div", { className: "w-full min-w-[280px]", children: [_jsx(Textarea, { autoGrow: true, maxRows: 10, value: draft, onChange: (e) => setDraft(e.target.value), onKeyDown: (e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        submitEdit();
                                    }
                                    if (e.key === "Escape") {
                                        setDraft(message.content);
                                        setIsEditing(false);
                                    }
                                }, autoFocus: true }), _jsxs("div", { className: "mt-2 flex justify-end gap-2", children: [_jsx(Button, { variant: "ghost", size: "sm", onClick: () => {
                                            setDraft(message.content);
                                            setIsEditing(false);
                                        }, children: "Cancel" }), _jsx(Button, { variant: "primary", size: "sm", onClick: submitEdit, children: "Save & submit" })] })] })) : (_jsxs("div", { className: cn("rounded-bubble px-4 py-2.5", isUser
                            ? "bg-accent-600/10 text-ink dark:text-ink-dark"
                            : "bg-canvas-panel dark:bg-canvas-dark-panel text-ink dark:text-ink-dark"), children: [isUser ? (_jsx("p", { className: "whitespace-pre-wrap text-body", children: message.content })) : message.content ? (_jsxs(_Fragment, { children: [_jsx(MarkdownRenderer, { content: message.content }), isStreaming && _jsx(TypingCursor, {})] })) : (isStreaming && _jsx(TypingCursor, {})), message.status === "error" && (_jsx("p", { className: "mt-2 text-meta text-danger", children: "Something went wrong generating this response." })), message.status === "stopped" && (_jsx("p", { className: "mt-2 text-meta text-ink/50 dark:text-ink-dark/50", children: "Generation stopped." }))] })), !isEditing && !isStreaming && (_jsx(MessageToolbar, { role: message.role, content: message.content, feedback: message.feedback, disabled: someStreamActive, onEdit: isUser ? () => setIsEditing(true) : undefined, onRegenerate: !isUser ? () => regenerate(message.id) : undefined, onFeedback: !isUser ? (fb) => setFeedback(message.id, fb) : undefined }))] })] }));
}
