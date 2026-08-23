import React, { useEffect } from "react";
import { cn } from "@/lib/cn";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useConversationsStore } from "@/store/conversationsStore";

const DEBOUNCE_MS = 300;

export function SidebarSearchBox() {
  const { searchQuery, setSearchQuery, runSearch, clearSearch } = useConversationsStore();
  const debouncedQuery = useDebouncedValue(searchQuery, DEBOUNCE_MS);

  useEffect(() => {
    if (debouncedQuery.trim()) {
      void runSearch(debouncedQuery);
    } else {
      clearSearch();
    }
    // runSearch/clearSearch are stable Zustand actions; only the debounced
    // value should re-trigger this.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery]);

  const handleClear = () => {
    setSearchQuery("");
    clearSearch();
  };

  return (
    <div className="px-2">
      <div className="relative flex items-center">
        <SearchIcon className="absolute left-2.5 text-ink/40 dark:text-ink-dark/40 pointer-events-none" />
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search conversations…"
          aria-label="Search conversations"
          className={cn(
            "w-full h-9 pl-8 pr-8 rounded-control border border-border dark:border-border-dark",
            "bg-canvas dark:bg-canvas-dark text-body text-ink dark:text-ink-dark",
            "placeholder:text-ink/40 dark:placeholder:text-ink-dark/40",
            "focus:outline-none focus:ring-2 focus:ring-accent-600 dark:focus:ring-accent-400 focus:ring-offset-0",
            "transition-colors"
          )}
        />
        {searchQuery && (
          <button
            type="button"
            onClick={handleClear}
            aria-label="Clear search"
            className="absolute right-2 p-0.5 rounded transition-colors text-ink/40 dark:text-ink-dark/40 hover:text-ink dark:hover:text-ink-dark hover:bg-canvas-panel dark:hover:bg-canvas-dark-alt"
          >
            <ClearIcon />
          </button>
        )}
      </div>
    </div>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M11 11 14.5 14.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function ClearIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M12 4L4 12M4 4L12 12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

