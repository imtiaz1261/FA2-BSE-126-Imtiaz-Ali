import React, { useEffect, useRef, useState } from "react";
import { useChatStore } from "@/store/chatStore";
import { useAuth } from "@/hooks/useAuth";
import { ThemeToggle } from "@chatline/design-system/theme/ThemeToggle";
import { Button } from "@chatline/design-system/components/Button";
import { MessageBubble } from "./MessageBubble";
import { Composer } from "./Composer";

/** Px from the bottom within which we still consider the user "at the
 * bottom" — small buffer so sub-pixel scroll rounding doesn't false-trigger
 * the "jump to latest" button. */
const BOTTOM_THRESHOLD_PX = 80;

export function ChatWindow({ userName }: { userName: string }) {
  const { messages, streamingMessageId } = useChatStore();
  const { logout } = useAuth();
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const isNearBottom = () => {
    const el = scrollRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < BOTTOM_THRESHOLD_PX;
  };

  // Re-enable auto-scroll when the user scrolls back down themselves;
  // disable it the moment they scroll up, away from the bottom.
  const handleScroll = () => {
    setAutoScroll(isNearBottom());
  };

  // Follow new content (new messages, or streaming tokens) only while
  // auto-scroll is enabled — this is what "pauses if the user manually
  // scrolls up" in practice.
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  const jumpToLatest = () => {
    setAutoScroll(true);
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-canvas dark:bg-canvas-dark">
      <header className="flex shrink-0 items-center justify-between border-b border-border dark:border-border-dark px-4 py-2.5">
        <p className="text-body font-semibold text-ink dark:text-ink-dark">Chatline</p>
        <div className="flex items-center gap-2">
          <span className="text-meta text-ink/50 dark:text-ink-dark/50">{userName}</span>
          <ThemeToggle />
          <Button variant="ghost" size="sm" onClick={() => void logout()}>
            Log out
          </Button>
        </div>
      </header>

      <div className="relative flex-1 min-h-0">
        <div ref={scrollRef} onScroll={handleScroll} className="h-full overflow-y-auto px-4 py-6">
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            {messages.length === 0 ? (
              <EmptyState />
            ) : (
              messages.map((message) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  isStreaming={message.id === streamingMessageId}
                  someStreamActive={streamingMessageId !== null}
                  userName={userName}
                />
              ))
            )}
          </div>
        </div>

        {!autoScroll && messages.length > 0 && (
          <button
            type="button"
            onClick={jumpToLatest}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1.5 rounded-full border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark-panel px-3.5 py-1.5 text-meta font-medium text-ink dark:text-ink-dark shadow-modal transition-colors hover:border-accent-600 dark:hover:border-accent-400"
          >
            <DownArrowIcon />
            Jump to latest
          </button>
        )}
      </div>

      <Composer />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <p className="text-heading font-semibold text-ink dark:text-ink-dark">
        Start a conversation
      </p>
      <p className="mt-1.5 max-w-sm text-body text-ink/60 dark:text-ink-dark/60">
        Ask a question, paste some code, or just say hello.
      </p>
    </div>
  );
}

function DownArrowIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 2.5v10M3.5 8.5 8 13l4.5-4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
