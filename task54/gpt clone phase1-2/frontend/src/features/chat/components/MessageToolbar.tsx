import React, { useState } from "react";
import { cn } from "@/lib/cn";
import type { MessageRole, Feedback } from "@/store/chatStore";

interface MessageToolbarProps {
  role: MessageRole;
  content: string;
  feedback: Feedback;
  /** Assistant messages only — hidden mid-stream and disabled while any message is streaming. */
  onRegenerate?: () => void;
  /** User messages only. */
  onEdit?: () => void;
  onFeedback?: (feedback: Feedback) => void;
  disabled?: boolean;
}

/**
 * Appears on hover (and on focus, for keyboard users) beneath a message.
 * Copy is available on every message; Regenerate is assistant-only, Edit is
 * user-only, and thumbs up/down are assistant-only.
 */
export function MessageToolbar({
  role,
  content,
  feedback,
  onRegenerate,
  onEdit,
  onFeedback,
  disabled,
}: MessageToolbarProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API can fail without permission/HTTPS — fail silently.
    }
  };

  return (
    <div
      className={cn(
        "flex items-center gap-1 opacity-0 transition-opacity",
        "group-hover:opacity-100 group-focus-within:opacity-100",
        role === "user" && "justify-end"
      )}
    >
      <ToolbarButton label={copied ? "Copied" : "Copy"} onClick={handleCopy}>
        {copied ? <CheckIcon /> : <CopyIcon />}
      </ToolbarButton>

      {role === "user" && onEdit && (
        <ToolbarButton label="Edit" onClick={onEdit} disabled={disabled}>
          <EditIcon />
        </ToolbarButton>
      )}

      {role === "assistant" && onRegenerate && (
        <ToolbarButton label="Regenerate" onClick={onRegenerate} disabled={disabled}>
          <RegenerateIcon />
        </ToolbarButton>
      )}

      {role === "assistant" && onFeedback && (
        <>
          <ToolbarButton
            label="Good response"
            onClick={() => onFeedback("up")}
            active={feedback === "up"}
          >
            <ThumbUpIcon />
          </ToolbarButton>
          <ToolbarButton
            label="Bad response"
            onClick={() => onFeedback("down")}
            active={feedback === "down"}
          >
            <ThumbDownIcon />
          </ToolbarButton>
        </>
      )}
    </div>
  );
}

function ToolbarButton({
  label,
  onClick,
  children,
  disabled,
  active,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
  disabled?: boolean;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "flex h-6 w-6 items-center justify-center rounded transition-colors",
        "text-ink/50 dark:text-ink-dark/50 hover:bg-canvas-panel dark:hover:bg-canvas-dark-alt hover:text-ink dark:hover:text-ink-dark",
        "disabled:pointer-events-none disabled:opacity-40",
        active && "text-accent-600 dark:text-accent-400"
      )}
    >
      {children}
    </button>
  );
}

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M3 10.5V3a1 1 0 0 1 1-1h7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3.5 8.5 6.5 11.5 12.5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function EditIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M11.3 2.3a1.5 1.5 0 0 1 2.1 2.1L5 12.8l-2.8.7.7-2.8 8.4-8.4Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function RegenerateIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2v3h-3"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ThumbUpIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M6 6.5 8.5 2c.8 0 1.5.7 1.5 1.5V6h3a1.5 1.5 0 0 1 1.4 2.1l-1.6 4A1.5 1.5 0 0 1 11.4 13H6V6.5ZM6 13H3.5A1.5 1.5 0 0 1 2 11.5V8a1.5 1.5 0 0 1 1.5-1.5H6"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ThumbDownIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M10 9.5 7.5 14c-.8 0-1.5-.7-1.5-1.5V10h-3a1.5 1.5 0 0 1-1.4-2.1l1.6-4A1.5 1.5 0 0 1 4.6 3H10v6.5ZM10 3h2.5A1.5 1.5 0 0 1 14 4.5V8a1.5 1.5 0 0 1-1.5 1.5H10"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}
