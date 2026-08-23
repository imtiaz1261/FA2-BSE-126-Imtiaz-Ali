import React, { useCallback, useMemo } from "react";
const { FixedSizeList } = require("react-window");
import { cn } from "@/lib/cn";
import type { SidebarRow } from "../lib/groupConversations";
import { ConversationRow } from "./ConversationRow";

interface VirtualizedConversationListProps {
  rows: SidebarRow[];
  height: number;
  width: number;
  isActive: (conversationId: string) => boolean;
  onShare: (id: string) => void;
  onItemsRendered?: (args: { visibleStopIndex: number }) => void;
}

// Height constants (must match ConversationRow and header row styles)
const ROW_HEIGHT = 36; // conversation item
const HEADER_HEIGHT = 32; // header row

/**
 * Row renderer component for react-window
 */
function Row({
  index,
  style,
  data,
}: any) {
  const { rows, isActive, onShare } = data;
  const row = rows[index];

  if (!row) return null;

  return (
    <div style={style}>
      {row.kind === "header" ? (
        <div className="flex items-end px-1.5 pb-1 pt-2 first:pt-0 h-full">
          <span className="text-meta font-medium text-ink/40 dark:text-ink-dark/40">
            {row.label}
          </span>
        </div>
      ) : (
        <div className="px-0.5 h-full flex items-center py-0.5">
          <ConversationRow
            conversation={row.conversation}
            isActive={isActive(row.conversation.id)}
            onShare={onShare}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Virtualized conversation list using react-window FixedSizeList
 * Supports 1000+ conversations with smooth scrolling
 */
export function VirtualizedConversationList({
  rows,
  height,
  width,
  isActive,
  onShare,
  onItemsRendered,
}: VirtualizedConversationListProps) {
  const itemData = useMemo(
    () => ({
      rows,
      isActive,
      onShare,
    }),
    [rows, isActive, onShare]
  );

  const handleItemsRendered = useCallback(
    (args: any) => {
      onItemsRendered?.(args);
    },
    [onItemsRendered]
  );

  // Fallback for when height is not yet measured
  if (height <= 0 || width <= 0) {
    return null;
  }

  return (
    <FixedSizeList
      height={height}
      itemCount={rows.length}
      itemData={itemData}
      itemSize={ROW_HEIGHT}
      width={width}
      onItemsRendered={handleItemsRendered}
    >
      {Row}
    </FixedSizeList>
  );
}
