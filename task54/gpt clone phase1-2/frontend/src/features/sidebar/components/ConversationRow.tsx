import React, { useState } from "react";
import { cn } from "@/lib/cn";
import type { ConversationSummary } from "@/lib/conversationsApi";
import { useConversationsStore } from "@/store/conversationsStore";
import { useChatStore } from "@/store/chatStore";
import { ConversationActionsMenu } from "./ConversationActionsMenu";

function formatTime(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const daysDiff = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (daysDiff === 0) {
    const hours = d.getHours();
    const minutes = d.getMinutes().toString().padStart(2, "0");
    return `${hours}:${minutes}`;
  }
  if (daysDiff === 1) return "Yesterday";
  if (daysDiff < 7) return `${daysDiff}d ago`;
  if (daysDiff < 30) return `${Math.floor(daysDiff / 7)}w ago`;
  return `${Math.floor(daysDiff / 30)}mo ago`;
}

export function ConversationRow({
  conversation,
  isActive,
  onShare,
}: {
  conversation: ConversationSummary;
  isActive: boolean;
  onShare: (id: string) => void;
}) {
  const { renameConversation, togglePin, toggleArchive, deleteConversation } =
    useConversationsStore();
  const { loadConversation, conversationId: currentConversationId, startNewChat } = useChatStore();
  const [isRenaming, setIsRenaming] = useState(false);
  const [draft, setDraft] = useState(conversation.title);

  const submitRename = () => {
    setIsRenaming(false);
    if (draft.trim() && draft.trim() !== conversation.title) {
      void renameConversation(conversation.id, draft.trim());
    } else {
      setDraft(conversation.title);
    }
  };

  const handleOpen = () => {
    if (isRenaming) return;
    if (conversation.id !== currentConversationId) {
      void loadConversation(conversation.id);
    }
  };

  const handleDelete = () => {
    const wasActive = conversation.id === currentConversationId;
    void deleteConversation(conversation.id);
    if (wasActive) startNewChat();
  };

  return (
    <div
      onClick={handleOpen}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && handleOpen()}
      className={cn(
        "group relative flex h-full w-full items-center gap-2 rounded-control px-2.5 py-1 cursor-pointer transition-all duration-150",
        isActive
          ? "bg-accent-600/10 text-ink dark:text-ink-dark shadow-sm"
          : "text-ink/80 dark:text-ink-dark/80 hover:bg-canvas dark:hover:bg-canvas-dark hover:shadow-sm"
      )}
    >
      {conversation.pinned && (
        <span className="shrink-0 flex items-center justify-center w-4 h-4 text-accent-600 dark:text-accent-400" title="Pinned">
          <PinIcon />
        </span>
      )}

      {conversation.is_shared && !conversation.pinned && (
        <span className="shrink-0 flex items-center justify-center w-4 h-4 text-accent-500/70 dark:text-accent-500/70" title="Shared">
          <ShareIconSmall />
        </span>
      )}

      {isRenaming ? (
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          onBlur={submitRename}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitRename();
            if (e.key === "Escape") {
              setDraft(conversation.title);
              setIsRenaming(false);
            }
          }}
          className={cn(
            "min-w-0 flex-1 rounded-control border-2 px-2 py-0.5 text-meta outline-none",
            "border-accent-600 dark:border-accent-400 bg-canvas dark:bg-canvas-dark",
            "focus:ring-2 focus:ring-accent-600/30 dark:focus:ring-accent-400/30 focus:ring-offset-0",
            "text-ink dark:text-ink-dark placeholder:text-ink/40 dark:placeholder:text-ink-dark/40"
          )}
        />
      ) : (
        <>
          <span className="min-w-0 flex-1 truncate text-meta font-medium">{conversation.title}</span>
          <span className="text-meta text-ink/40 dark:text-ink-dark/40 text-xs shrink-0">
            {formatTime(conversation.last_message_at)}
          </span>
        </>
      )}

      {!isRenaming && (
        <div className="shrink-0 ml-1 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-150">
          <ConversationActionsMenu
            actions={[
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
            ]}
          />
        </div>
      )}
    </div>
  );
}

function PinIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M9.5 1.5 8 3l-1 4-3 1.5L9.5 14l1.5-3 4-1L14 8.5 9.5 1.5Zm-3 9.5L2 15" stroke="currentColor" strokeWidth="0.5" />
    </svg>
  );
}


function ShareIconSmall() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M11 8.5a2 2 0 100-4 2 2 0 000 4ZM2 5a2 2 0 100-4 2 2 0 000 4Zm9 6a2 2 0 100-4 2 2 0 000 4Z"
        stroke="currentColor"
        strokeWidth="1.2"
      />
      <path d="M5 6.5l5 2.5M5 9.5l5-2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}
