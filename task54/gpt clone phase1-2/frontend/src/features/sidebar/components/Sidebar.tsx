import React, { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@chatline/design-system/components/Button";
import { useConversationsStore } from "@/store/conversationsStore";
import { useChatStore } from "@/store/chatStore";
import { useElementSize } from "@/hooks/useElementSize";
import { buildSidebarRows, SidebarRow } from "../lib/groupConversations";
import { SidebarSearchBox } from "./SidebarSearchBox";
import { VirtualizedConversationList } from "./VirtualizedConversationList";
import { ShareDialog } from "./ShareDialog";
import { CreateFolderDialog } from "./CreateFolderDialog";

const COLLAPSED_WIDTH = 56;
const EXPANDED_WIDTH = 272;

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [shareTargetId, setShareTargetId] = useState<string | null>(null);
  const [showCreateFolder, setShowCreateFolder] = useState(false);

  const {
    items,
    searchResults,
    searchQuery,
    isLoadingInitial,
    nextCursor,
    fetchInitial,
    fetchMore,
    folders,
    fetchFolders,
    activeFolderId,
    setActiveFolder,
    showArchived,
    setShowArchived,
  } = useConversationsStore();
  const { conversationId, startNewChat } = useChatStore();

  useEffect(() => {
    void fetchInitial();
    void fetchFolders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isSearching = searchQuery.trim().length > 0;
  const displayedItems = isSearching ? searchResults ?? [] : items;
  const rows: SidebarRow[] = useMemo(
    () => (isSearching ? searchResults?.map((c) => ({ kind: "item" as const, key: c.id, conversation: c })) ?? [] : buildSidebarRows(items)),
    [isSearching, searchResults, items]
  );

  const { ref: listContainerRef, height: listHeight } = useElementSize<HTMLDivElement>();

  const handleItemsRendered = ({ visibleStopIndex }: { visibleStopIndex: number }) => {
    if (!isSearching && nextCursor && visibleStopIndex >= rows.length - 10) {
      void fetchMore();
    }
  };

  if (collapsed) {
    return (
      <div
        className="flex h-full flex-col items-center gap-3 border-r border-border dark:border-border-dark bg-canvas-panel dark:bg-canvas-dark-panel py-3"
        style={{ width: COLLAPSED_WIDTH }}
      >
        <button
          type="button"
          aria-label="Expand sidebar"
          onClick={() => setCollapsed(false)}
          className="flex h-8 w-8 items-center justify-center rounded-control text-ink/60 dark:text-ink-dark/60 hover:bg-canvas dark:hover:bg-canvas-dark-alt"
        >
          <ExpandIcon />
        </button>
        <button
          type="button"
          aria-label="New chat"
          onClick={startNewChat}
          className="flex h-8 w-8 items-center justify-center rounded-control text-accent-600 dark:text-accent-400 hover:bg-canvas dark:hover:bg-canvas-dark-alt"
        >
          <PlusIcon />
        </button>
      </div>
    );
  }

  return (
    <div
      className="flex h-full flex-col border-r border-border dark:border-border-dark bg-canvas-panel dark:bg-canvas-dark-panel"
      style={{ width: EXPANDED_WIDTH }}
    >
      {/* New Chat — pinned at top */}
      <div className="flex items-center gap-2 p-2.5">
        <Button variant="primary" size="sm" className="flex-1 justify-start" onClick={startNewChat}>
          <PlusIcon /> New chat
        </Button>
        <button
          type="button"
          aria-label="Collapse sidebar"
          onClick={() => setCollapsed(true)}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink/50 dark:text-ink-dark/50 hover:bg-canvas dark:hover:bg-canvas-dark-alt"
        >
          <CollapseIcon />
        </button>
      </div>

      <div className="pb-2">
        <SidebarSearchBox />
      </div>

      {/* Folder quick filters */}
      {folders.length > 0 && (
        <div className="border-t border-border dark:border-border-dark px-2 py-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-meta font-medium text-ink/60 dark:text-ink-dark/60 ml-1.5">
              Folders
            </span>
            <button
              type="button"
              onClick={() => setShowCreateFolder(true)}
              aria-label="Create new folder"
              className="h-6 w-6 rounded transition-colors text-ink/40 dark:text-ink-dark/40 hover:bg-canvas dark:hover:bg-canvas-dark-alt hover:text-ink dark:hover:text-ink-dark flex items-center justify-center"
            >
              <PlusIcon />
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            <FolderChip
              label="All"
              active={activeFolderId === null}
              onClick={() => setActiveFolder(null)}
            />
            {folders.map((folder) => (
              <FolderChip
                key={folder.id}
                label={folder.name}
                active={activeFolderId === folder.id}
                onClick={() => setActiveFolder(folder.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Archive button */}
      <div className="border-t border-border dark:border-border-dark px-2 py-2">
        <button
          type="button"
          onClick={() => setShowArchived(!showArchived)}
          className={cn(
            "w-full text-left px-2 py-1.5 rounded-control text-meta font-medium transition-colors",
            showArchived
              ? "bg-accent-600/10 text-accent-600 dark:text-accent-400"
              : "text-ink/70 dark:text-ink-dark/70 hover:bg-canvas dark:hover:bg-canvas-dark-alt"
          )}
        >
          <span className="flex items-center gap-2">
            <ArchiveIcon className={showArchived ? "text-accent-600 dark:text-accent-400" : "text-ink/50 dark:text-ink-dark/50"} />
            Archived
          </span>
        </button>
      </div>

      {/* Conversation list */}
      <div ref={listContainerRef} className="min-h-0 flex-1 overflow-hidden">
        {isLoadingInitial && items.length === 0 ? (
          <SidebarSkeleton />
        ) : rows.length === 0 ? (
          <div className="flex h-full items-center justify-center px-2">
            <p className="text-center text-meta text-ink/50 dark:text-ink-dark/50">
              {isSearching ? "No conversations match your search." : "No conversations yet."}
            </p>
          </div>
        ) : listHeight > 0 ? (
          <VirtualizedConversationList
            rows={rows}
            height={listHeight}
            width={EXPANDED_WIDTH - 16} // 16px = 2 * 8px padding
            isActive={(id) => id === conversationId}
            onShare={setShareTargetId}
            onItemsRendered={handleItemsRendered}
          />
        ) : null}
      </div>

      <ShareDialog conversationId={shareTargetId} onClose={() => setShareTargetId(null)} />
      <CreateFolderDialog open={showCreateFolder} onClose={() => setShowCreateFolder(false)} />
    </div>
  );
}

function FolderChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-2.5 py-1 text-meta font-medium transition-all text-nowrap",
        active
          ? "border-accent-600 dark:border-accent-400 text-accent-600 dark:text-accent-400 bg-accent-600/10"
          : "border-border dark:border-border-dark text-ink/60 dark:text-ink-dark/60 hover:border-accent-600/50 dark:hover:border-accent-400/50 hover:text-ink/80 dark:hover:text-ink-dark/80"
      )}
    >
      <FolderIconSmall /> {label}
    </button>
  );
}

function SidebarSkeleton() {
  return (
    <div className="flex flex-col gap-2 py-1">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="h-[30px] animate-pulse rounded-control bg-canvas dark:bg-canvas-dark-alt"
          style={{ opacity: 1 - i * 0.08 }}
        />
      ))}
    </div>
  );
}

function PlusIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="mr-0.5 inline-block">
      <path d="M8 2.5v11M2.5 8h11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function CollapseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2" y="3" width="12" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M6.5 3v10" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

function ExpandIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2" y="3" width="12" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
      <path d="M9.5 3v10" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}


function ArchiveIcon({ className }: { className?: string }) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true" className={className}>
      <path d="M2 5V3h12v2M6 9V13M10 9V13M3 5h10l-1 7H4L3 5Z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FolderIconSmall() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M2 4H14V12H2V4Z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M6.5 3.5L4.5 5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}
