import React, { useRef, useState } from "react";
import { Button } from "@chatline/design-system/components/Button";
import { Textarea } from "@chatline/design-system/components/Textarea";
import { useChatStore } from "@/store/chatStore";

export function Composer() {
  const { sendMessage, stopGeneration, streamingMessageId } = useChatStore();
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const isStreaming = streamingMessageId !== null;

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    setValue("");
    void sendMessage(trimmed);
    // Auto-grow won't reset itself just because the value cleared — force
    // the height back down so the composer collapses after sending.
    requestAnimationFrame(() => {
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    // Shift+Enter falls through to the textarea's default newline behavior.
  };

  return (
    <div className="border-t border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark px-4 py-3">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="flex-1">
          <Textarea
            ref={textareaRef}
            autoGrow
            maxRows={8}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message the assistant… (Shift+Enter for a new line)"
            aria-label="Message"
            disabled={isStreaming}
          />
        </div>

        {isStreaming ? (
          <Button variant="secondary" onClick={stopGeneration} aria-label="Stop generating">
            <StopIcon /> Stop
          </Button>
        ) : (
          <Button variant="primary" onClick={handleSend} disabled={!value.trim()} aria-label="Send message">
            <SendIcon />
          </Button>
        )}
      </div>
      <p className="mx-auto mt-1.5 max-w-3xl text-center text-meta text-ink/40 dark:text-ink-dark/40">
        Chatline can make mistakes. Check important info.
      </p>
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M14.5 1.5 7.5 8.5M14.5 1.5 10 14.5l-2.5-6L1.5 6l13-4.5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" className="mr-0.5 inline-block">
      <rect x="3" y="3" width="10" height="10" rx="1.5" />
    </svg>
  );
}
