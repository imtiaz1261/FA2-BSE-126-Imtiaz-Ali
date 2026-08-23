import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@chatline/design-system/components/Button";
import { useConversationsStore } from "@/store/conversationsStore";
import { useChatStore } from "@/store/chatStore";
import { useElementSize } from "@/hooks/useElementSize";
import { buildSidebarRows } from "../lib/groupConversations";
import { SidebarSearchBox } from "./SidebarSearchBox";
import { ConversationRow } from "./ConversationRow";
import { ShareDialog } from "./ShareDialog";
const COLLAPSED_WIDTH = 56;
const EXPANDED_WIDTH = 272;
export function Sidebar() {
    const [collapsed, setCollapsed] = useState(false);
    const [shareTargetId, setShareTargetId] = useState(null);
    const { items, searchResults, searchQuery, isLoadingInitial, nextCursor, fetchInitial, fetchMore, folders, fetchFolders, activeFolderId, setActiveFolder, } = useConversationsStore();
    const { conversationId, startNewChat } = useChatStore();
    useEffect(() => {
        void fetchInitial();
        void fetchFolders();
        // Intentionally run once on mount — filter changes call fetchInitial
        // themselves via setActiveFolder/setShowArchived.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    const isSearching = searchQuery.trim().length > 0;
    const displayedItems = isSearching ? searchResults ?? [] : items;
    const rows = useMemo(() => (isSearching ? searchResults?.map((c) => ({ kind: "item", key: c.id, conversation: c })) ?? [] : buildSidebarRows(items)), [isSearching, searchResults, items]);
    const { ref: listContainerRef, height: listHeight } = useElementSize();
    const handleItemsRendered = ({ visibleStopIndex }) => {
        // Load the next page once the user scrolls within 10 rows of the end.
        if (!isSearching && nextCursor && visibleStopIndex >= rows.length - 10) {
            void fetchMore();
        }
    };
    if (collapsed) {
        return (_jsxs("div", { className: "flex h-full flex-col items-center gap-3 border-r border-border dark:border-border-dark bg-canvas-panel dark:bg-canvas-dark-panel py-3", style: { width: COLLAPSED_WIDTH }, children: [_jsx("button", { type: "button", "aria-label": "Expand sidebar", onClick: () => setCollapsed(false), className: "flex h-8 w-8 items-center justify-center rounded-control text-ink/60 dark:text-ink-dark/60 hover:bg-canvas dark:hover:bg-canvas-dark-alt", children: _jsx(ExpandIcon, {}) }), _jsx("button", { type: "button", "aria-label": "New chat", onClick: startNewChat, className: "flex h-8 w-8 items-center justify-center rounded-control text-accent-600 dark:text-accent-400 hover:bg-canvas dark:hover:bg-canvas-dark-alt", children: _jsx(PlusIcon, {}) })] }));
    }
    return (_jsxs("div", { className: "flex h-full flex-col border-r border-border dark:border-border-dark bg-canvas-panel dark:bg-canvas-dark-panel", style: { width: EXPANDED_WIDTH }, children: [_jsxs("div", { className: "flex items-center gap-2 p-2.5", children: [_jsxs(Button, { variant: "primary", size: "sm", className: "flex-1 justify-start", onClick: startNewChat, children: [_jsx(PlusIcon, {}), " New chat"] }), _jsx("button", { type: "button", "aria-label": "Collapse sidebar", onClick: () => setCollapsed(true), className: "flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink/50 dark:text-ink-dark/50 hover:bg-canvas dark:hover:bg-canvas-dark-alt", children: _jsx(CollapseIcon, {}) })] }), _jsx("div", { className: "pb-2", children: _jsx(SidebarSearchBox, {}) }), folders.length > 0 && (_jsxs("div", { className: "flex flex-wrap gap-1.5 px-2 pb-2", children: [_jsx(FolderChip, { label: "All", active: activeFolderId === null, onClick: () => setActiveFolder(null) }), folders.map((folder) => (_jsx(FolderChip, { label: folder.name, active: activeFolderId === folder.id, onClick: () => setActiveFolder(folder.id) }, folder.id)))] })), _jsx("div", { ref: listContainerRef, className: "min-h-0 flex-1 px-2", children: isLoadingInitial && items.length === 0 ? (_jsx(SidebarSkeleton, {})) : rows.length === 0 ? (_jsx("p", { className: "px-1 py-4 text-center text-meta text-ink/50 dark:text-ink-dark/50", children: isSearching ? "No conversations match your search." : "No conversations yet." })) : listHeight > 0 ? (_jsx("div", { className: "flex h-full flex-col gap-1 overflow-y-auto pb-2", children: rows.map((row) => row.kind === "header" ? (_jsx("div", { className: "flex items-end px-1.5 pb-1 pt-2 first:pt-0", children: _jsx("span", { className: "text-meta font-medium text-ink/40 dark:text-ink-dark/40", children: row.label }) }, row.key)) : (_jsx("div", { className: "py-0.5", children: _jsx(ConversationRow, { conversation: row.conversation, isActive: row.conversation.id === conversationId, onShare: setShareTargetId }) }, row.key))) })) : null }), _jsx(ShareDialog, { conversationId: shareTargetId, onClose: () => setShareTargetId(null) })] }));
}
function FolderChip({ label, active, onClick }) {
    return (_jsx("button", { type: "button", onClick: onClick, className: cn("rounded-full border px-2.5 py-1 text-meta font-medium transition-colors", active
            ? "border-accent-600 dark:border-accent-400 text-accent-600 dark:text-accent-400 bg-accent-600/10"
            : "border-border dark:border-border-dark text-ink/60 dark:text-ink-dark/60 hover:border-accent-600/50"), children: label }));
}
function SidebarSkeleton() {
    return (_jsx("div", { className: "flex flex-col gap-2 py-1", children: Array.from({ length: 8 }).map((_, i) => (_jsx("div", { className: "h-[30px] animate-pulse rounded-control bg-canvas dark:bg-canvas-dark-alt", style: { opacity: 1 - i * 0.08 } }, i))) }));
}
function PlusIcon() {
    return (_jsx("svg", { width: "14", height: "14", viewBox: "0 0 16 16", fill: "none", "aria-hidden": "true", className: "mr-0.5 inline-block", children: _jsx("path", { d: "M8 2.5v11M2.5 8h11", stroke: "currentColor", strokeWidth: "1.5", strokeLinecap: "round" }) }));
}
function CollapseIcon() {
    return (_jsxs("svg", { width: "16", height: "16", viewBox: "0 0 16 16", fill: "none", "aria-hidden": "true", children: [_jsx("rect", { x: "2", y: "3", width: "12", height: "10", rx: "1.5", stroke: "currentColor", strokeWidth: "1.2" }), _jsx("path", { d: "M6.5 3v10", stroke: "currentColor", strokeWidth: "1.2" })] }));
}
function ExpandIcon() {
    return (_jsxs("svg", { width: "16", height: "16", viewBox: "0 0 16 16", fill: "none", "aria-hidden": "true", children: [_jsx("rect", { x: "2", y: "3", width: "12", height: "10", rx: "1.5", stroke: "currentColor", strokeWidth: "1.2" }), _jsx("path", { d: "M9.5 3v10", stroke: "currentColor", strokeWidth: "1.2" })] }));
}
