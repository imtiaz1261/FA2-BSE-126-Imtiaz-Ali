import React, { useEffect, useState } from "react";
import { Avatar } from "@chatline/design-system/components/Avatar";
import { MarkdownRenderer } from "@/features/chat/components/MarkdownRenderer";
import { sharedConversationApi, SharedConversation } from "@/lib/conversationsApi";
import { ApiError } from "@/lib/api";

/** Rendered at /share/{token} — no auth, no sidebar, read-only. */
export function SharedConversationView({ token }: { token: string }) {
  const [conversation, setConversation] = useState<SharedConversation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    sharedConversationApi
      .get(token)
      .then(setConversation)
      .catch((err) => {
        setError(
          err instanceof ApiError && err.status === 404
            ? "This share link is invalid or has been revoked."
            : "Couldn't load this conversation."
        );
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas dark:bg-canvas-dark">
        <p className="text-body text-ink/60 dark:text-ink-dark/60">Loading…</p>
      </div>
    );
  }

  if (error || !conversation) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-canvas dark:bg-canvas-dark px-4 text-center">
        <p className="text-heading font-semibold text-ink dark:text-ink-dark">Link unavailable</p>
        <p className="text-body text-ink/60 dark:text-ink-dark/60">{error}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas dark:bg-canvas-dark">
      <header className="border-b border-border dark:border-border-dark px-4 py-3">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <p className="text-body font-semibold text-ink dark:text-ink-dark">{conversation.title}</p>
          <span className="rounded-full bg-canvas-panel dark:bg-canvas-dark-panel px-2.5 py-0.5 text-meta font-medium text-ink/50 dark:text-ink-dark/50">
            Read-only
          </span>
        </div>
      </header>

      <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
        {conversation.messages.map((message, i) => (
          <div key={i} className={`flex gap-3 ${message.role === "user" ? "flex-row-reverse" : ""}`}>
            <Avatar
              name={message.role === "user" ? "You" : "Assistant"}
              tone={message.role === "user" ? "neutral" : "accent"}
              size="sm"
              className="mt-0.5 shrink-0"
            />
            <div
              className={`max-w-[75%] rounded-bubble px-4 py-2.5 ${
                message.role === "user"
                  ? "bg-accent-600/10 text-ink dark:text-ink-dark"
                  : "bg-canvas-panel dark:bg-canvas-dark-panel text-ink dark:text-ink-dark"
              }`}
            >
              {message.role === "user" ? (
                <p className="whitespace-pre-wrap text-body">{message.content}</p>
              ) : (
                <MarkdownRenderer content={message.content} />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
