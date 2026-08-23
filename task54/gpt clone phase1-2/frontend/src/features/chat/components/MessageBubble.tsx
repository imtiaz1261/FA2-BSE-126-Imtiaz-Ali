import React, { useState } from "react";
import { cn } from "@/lib/cn";
import { Avatar } from "@chatline/design-system/components/Avatar";
import { Button } from "@chatline/design-system/components/Button";
import { Textarea } from "@chatline/design-system/components/Textarea";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { TypingCursor } from "./TypingCursor";
import { MessageToolbar } from "./MessageToolbar";
import { useChatStore, type ChatMessage } from "@/store/chatStore";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming: boolean;
  /** Any message is currently streaming (used to disable regenerate/edit on other messages). */
  someStreamActive: boolean;
  userName: string;
}

export function MessageBubble({
  message,
  isStreaming,
  someStreamActive,
  userName,
}: MessageBubbleProps) {
  const { regenerate, editAndResend, setFeedback } = useChatStore();
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);

  const isUser = message.role === "user";

  const submitEdit = () => {
    const trimmed = draft.trim();
    if (!trimmed) return;
    setIsEditing(false);
    void editAndResend(message.id, trimmed);
  };

  return (
    <div className={cn("group flex gap-3", isUser && "flex-row-reverse")}>
      <Avatar
        name={isUser ? userName : "Assistant"}
        tone={isUser ? "neutral" : "accent"}
        size="sm"
        className="mt-0.5 shrink-0"
      />

      <div className={cn("flex max-w-[75%] flex-col gap-1.5", isUser && "items-end")}>
        {isEditing ? (
          <div className="w-full min-w-[280px]">
            <Textarea
              autoGrow
              maxRows={10}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submitEdit();
                }
                if (e.key === "Escape") {
                  setDraft(message.content);
                  setIsEditing(false);
                }
              }}
              autoFocus
            />
            <div className="mt-2 flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setDraft(message.content);
                  setIsEditing(false);
                }}
              >
                Cancel
              </Button>
              <Button variant="primary" size="sm" onClick={submitEdit}>
                Save & submit
              </Button>
            </div>
          </div>
        ) : (
          <div
            className={cn(
              "rounded-bubble px-4 py-2.5",
              isUser
                ? "bg-accent-600/10 text-ink dark:text-ink-dark"
                : "bg-canvas-panel dark:bg-canvas-dark-panel text-ink dark:text-ink-dark"
            )}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap text-body">{message.content}</p>
            ) : message.content ? (
              <>
                <MarkdownRenderer content={message.content} />
                {isStreaming && <TypingCursor />}
              </>
            ) : (
              isStreaming && <TypingCursor />
            )}

            {message.status === "error" && (
              <p className="mt-2 text-meta text-danger">
                Something went wrong generating this response.
              </p>
            )}
            {message.status === "stopped" && (
              <p className="mt-2 text-meta text-ink/50 dark:text-ink-dark/50">
                Generation stopped.
              </p>
            )}
          </div>
        )}

        {!isEditing && !isStreaming && (
          <MessageToolbar
            role={message.role}
            content={message.content}
            feedback={message.feedback}
            disabled={someStreamActive}
            onEdit={isUser ? () => setIsEditing(true) : undefined}
            onRegenerate={!isUser ? () => regenerate(message.id) : undefined}
            onFeedback={!isUser ? (fb) => setFeedback(message.id, fb) : undefined}
          />
        )}
      </div>
    </div>
  );
}
