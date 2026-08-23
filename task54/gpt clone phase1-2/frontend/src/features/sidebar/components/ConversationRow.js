import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { useConversationsStore } from "@/store/conversationsStore";
import { useChatStore } from "@/store/chatStore";
import { ConversationActionsMenu } from "./ConversationActionsMenu";
export function ConversationRow({ conversation, isActive, onShare, }) {
    const { renameConversation, togglePin, toggleArchive, deleteConversation } = useConversationsStore();
    const { loadConversation, conversationId: currentConversationId, startNewChat } = useChatStore();
    const [isRenaming, setIsRenaming] = useState(false);
    const [draft, setDraft] = useState(conversation.title);
    const submitRename = () => {
        setIsRenaming(false);
        if (draft.trim() && draft.trim() !== conversation.title) {
            void renameConversation(conversation.id, draft.trim());
        }
        else {
            setDraft(conversation.title);
        }
    };
    const handleOpen = () => {
        if (isRenaming)
            return;
        if (conversation.id !== currentConversationId) {
            void loadConversation(conversation.id);
        }
    };
    const handleDelete = () => {
        const wasActive = conversation.id === currentConversationId;
        void deleteConversation(conversation.id);
        if (wasActive)
            startNewChat();
    };
    return (_jsxs("div", { onClick: handleOpen, role: "button", tabIndex: 0, onKeyDown: (e) => e.key === "Enter" && handleOpen(), className: cn("group flex h-full items-center gap-2 rounded-control px-2.5 cursor-pointer transition-colors", isActive
            ? "bg-accent-600/10 text-ink dark:text-ink-dark"
            : "text-ink/80 dark:text-ink-dark/80 hover:bg-canvas-panel dark:hover:bg-canvas-dark-alt"), children: [conversation.pinned && (_jsx("span", { className: "shrink-0 text-accent-600 dark:text-accent-400", children: _jsx(PinIcon, {}) })), isRenaming ? (_jsx("input", { autoFocus: true, value: draft, onChange: (e) => setDraft(e.target.value), onClick: (e) => e.stopPropagation(), onBlur: submitRename, onKeyDown: (e) => {
                    if (e.key === "Enter")
                        submitRename();
                    if (e.key === "Escape") {
                        setDraft(conversation.title);
                        setIsRenaming(false);
                    }
                }, className: "min-w-0 flex-1 rounded border border-accent-600 dark:border-accent-400 bg-canvas dark:bg-canvas-dark px-1.5 py-0.5 text-meta outline-none" })) : (_jsx("span", { className: "min-w-0 flex-1 truncate text-meta", children: conversation.title })), !isRenaming && (_jsx("div", { className: "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100", children: _jsx(ConversationActionsMenu, { actions: [
                        { label: "Rename", onClick: () => setIsRenaming(true) },
                        {
                            label: conversation.pinned ? "Unpin" : "Pin",
                            onClick: () => void togglePin(conversation.id, !conversation.pinned),
                        },
                        { label: "Share", onClick: () => onShare(conversation.id) },
                        {
                            label: conversation.archived ? "Unarchive" : "Archive",
                            onClick: () => void toggleArchive(conversation.id, !conversation.archived),
                        },
                        { label: "Delete", onClick: handleDelete, destructive: true },
                    ] }) }))] }));
}
function PinIcon() {
    return (_jsx("svg", { width: "12", height: "12", viewBox: "0 0 16 16", fill: "currentColor", "aria-hidden": "true", children: _jsx("path", { d: "M9.5 1.5 8 3l-1 4-3 1.5L9.5 14l1.5-3 4-1L14 8.5 9.5 1.5Zm-3 9.5L2 15", stroke: "currentColor", strokeWidth: "0.5" }) }));
}
