import React, { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { useConversationsStore } from "@/store/conversationsStore";
import { useChatStore } from "@/store/chatStore";
import { useElementSize } from "@/hooks/useElementSize";
import { buildSidebarRows } from "../lib/groupConversations";
import { VirtualizedConversationList } from "./VirtualizedConversationList";
import { ShareDialog } from "./ShareDialog";

const COLLAPSED_WIDTH = 56;
const EXPANDED_WIDTH = 272;

export function ArchiveView() {
  const [collapsed, setCollapsed] = useState(false);
  const [shareTargetId, setShareTargetId] = useState<string | null>(null);

  const {
    items,
    isLoadingInitial,
    nextCursor,
    fetchMore,
    showArchived,
    setShowArchived,
    activeFolderId,
    setActiveFolder,
    folders,
  } = useConversationsStore();
  const { conversationId } = useChatStore();

  // Fetch archived items
  useEffect(() => {
    if (!showArchived) {
      setShowArchived(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rows = useMemo(() => buildSidebarRows(items), [items]);
  const { ref: listContainerRef, height: listHeight } = useElementSize<HTMLDivElement>();

  const handleItemsRendered = ({ visibleStopIndex }: { visibleStopIndex: number }) => {
    if (nextCursor && visibleStopIndex >= rows.length - 10) {
      void fetchMore();
    }
  };

  const handleBack = () => {
    setShowArchived(false);
  };

  if (collapsed) {
    return (
      <div
        className="flex h-full flex-col items-center gap-3 border-r border-border dark:border-border-dark bg-canvas-panel dark:bg-canvas-dark-panel py-3"
        style={{ width: COLLAPSED_WIDTH }}
      >
        <button
          type="button"
          aria-label="Expand archive"
          onClick={() => setCollapsed(false)}
          className="flex h-8 w-8 items-center justify-center rounded-control text-ink/60 dark:text-ink-dark/60 hover:bg-canvas dark:hover:bg-canvas-dark-alt"
        >
          <ExpandIcon />
        </button>
      </div>
    );
  }

  return (
    <div
      className="flex h-full flex-col border-r border-border dark:border-border-dark bg-canvas-panel dark:bg-canvas-dark-panel"
      style={{ width: EXPANDED_WIDTH }}
    >
      {/* Header with back button */}
      <div className="flex items-center gap-2 p-2.5 border-b border-border dark:border-border-dark">
        <button
          type="button"
          aria-label="Back to conversations"
          onClick={handleBack}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink/60 dark:text-ink-dark/60 hover:bg-canvas dark:hover:bg-canvas-dark-alt hover:text-ink dark:hover:text-ink-dark"
        >
          <BackIcon />
        </button>
        <h2 className="flex-1 font-semibold text-body text-ink dark:text-ink-dark">Archived</h2>
        <button
          type="button"
          aria-label="Collapse archive"
          onClick={() => setCollapsed(true)}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink/50 dark:text-ink-dark/50 hover:bg-canvas dark:hover:bg-canvas-dark-alt"
        >
          <CollapseIcon />
        </button>
      </div>

      {/* Archive list */}
      <div ref={listContainerRef} className="min-h-0 flex-1 overflow-hidden">
        {isLoadingInitial && items.length === 0 ? (
          <div className="flex flex-col gap-2 py-1 px-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="h-[30px] animate-pulse rounded-control bg-canvas dark:bg-canvas-dark-alt"
                style={{ opacity: 1 - i * 0.08 }}
              />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="flex h-full items-center justify-center px-2">
            <p className="text-center text-meta text-ink/50 dark:text-ink-dark/50">
              No archived conversations.
            </p>
          </div>
        ) : listHeight > 0 ? (
          <VirtualizedConversationList
            rows={rows}
            height={listHeight}
            width={EXPANDED_WIDTH - 16}
            isActive={(id) => id === conversationId}
            onShare={setShareTargetId}
            onItemsRendered={handleItemsRendered}
          />
        ) : null}
      </div>

      <ShareDialog conversationId={shareTargetId} onClose={() => setShareTargetId(null)} />
    </div>
  );
}

function BackIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M10 3L5 8L10 13"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
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
