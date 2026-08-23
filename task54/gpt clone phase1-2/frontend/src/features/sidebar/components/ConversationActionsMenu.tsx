import React, { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

interface MenuAction {
  label: string;
  onClick: () => void;
  destructive?: boolean;
}

export function ConversationActionsMenu({ actions }: { actions: MenuAction[] }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-label="Conversation actions"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className={cn(
          "flex h-6 w-6 items-center justify-center rounded transition-colors",
          "text-ink/50 dark:text-ink-dark/50 hover:bg-canvas dark:hover:bg-canvas-dark-alt hover:text-ink dark:hover:text-ink-dark",
          open && "bg-canvas dark:bg-canvas-dark-alt text-ink dark:text-ink-dark"
        )}
      >
        <DotsIcon />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-7 z-20 min-w-[160px] rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark-panel py-1 shadow-modal"
        >
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              role="menuitem"
              onClick={(e) => {
                e.stopPropagation();
                setOpen(false);
                action.onClick();
              }}
              className={cn(
                "block w-full px-3 py-1.5 text-left text-meta transition-colors",
                action.destructive
                  ? "text-danger hover:bg-danger/10"
                  : "text-ink dark:text-ink-dark hover:bg-canvas-panel dark:hover:bg-canvas-dark-alt"
              )}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function DotsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <circle cx="3" cy="8" r="1.3" />
      <circle cx="8" cy="8" r="1.3" />
      <circle cx="13" cy="8" r="1.3" />
    </svg>
  );
}
