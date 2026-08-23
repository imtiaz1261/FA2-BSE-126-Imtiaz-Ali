/**
 * Model Selector Dropdown Component
 * 
 * Shows available LLM models with descriptions
 * Selection persists per-conversation
 * Keyboard navigable (arrow keys, Enter, Escape)
 */

import React, { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { useSettingsStore } from "@/store/settingsStore";
import type { AvailableModel } from "@/lib/settingsApi";

interface ModelSelectorProps {
  conversationId: string;
  currentModelId?: string;
  onModelSelect?: (modelId: string) => void;
}

export function ModelSelector({
  conversationId,
  currentModelId,
  onModelSelect,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const {
    availableModels,
    selectedModelId,
    isLoadingModels,
    selectModel,
    setSelectedModelId,
  } = useSettingsStore();

  // Load models on mount
  useEffect(() => {
    if (!availableModels) {
      useSettingsStore.getState().fetchModels();
    }
  }, [availableModels]);

  // Update selected model when conversationId changes
  useEffect(() => {
    if (currentModelId) {
      setSelectedModelId(currentModelId);
    }
  }, [currentModelId, conversationId, setSelectedModelId]);

  const currentModel = availableModels?.find((m) => m.id === (selectedModelId || currentModelId));

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setOpen(true);
      }
      return;
    }

    if (!availableModels) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((i) => (i + 1) % availableModels.length);
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((i) => (i - 1 + availableModels.length) % availableModels.length);
        break;
      case "Enter":
        e.preventDefault();
        handleSelectModel(availableModels[highlightedIndex]);
        break;
      case "Escape":
        e.preventDefault();
        setOpen(false);
        break;
      default:
        break;
    }
  };

  const handleSelectModel = async (model: AvailableModel) => {
    setSelectedModelId(model.id);
    await selectModel(conversationId, model.id);
    setOpen(false);
    onModelSelect?.(model.id);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!open) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div ref={containerRef} className="relative inline-block w-full">
      {/* Trigger Button */}
      <button
        onClick={() => setOpen(!open)}
        onKeyDown={handleKeyDown}
        aria-label="Select model"
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          "w-full flex items-center justify-between gap-2 rounded-control border px-3 py-2",
          "bg-canvas dark:bg-canvas-dark text-body text-ink dark:text-ink-dark",
          "border-border dark:border-border-dark",
          "hover:border-accent-600 dark:hover:border-accent-400",
          "focus:outline-none focus:ring-2 focus:ring-accent-600 dark:focus:ring-accent-400",
          "transition-colors"
        )}
      >
        <div className="min-w-0 flex-1 text-left">
          {isLoadingModels ? (
            <span className="text-ink/50 dark:text-ink-dark/50">Loading models...</span>
          ) : currentModel ? (
            <>
              <div className="font-medium truncate">{currentModel.display_name}</div>
              <div className="text-meta text-ink/60 dark:text-ink-dark/60 truncate">
                {currentModel.description}
              </div>
            </>
          ) : (
            <span className="text-ink/50 dark:text-ink-dark/50">Select a model</span>
          )}
        </div>
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          className={cn(
            "shrink-0 text-ink/60 dark:text-ink-dark/60 transition-transform",
            open && "rotate-180"
          )}
          aria-hidden="true"
        >
          <path
            d="M4 6L8 10L12 6"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {open && availableModels && (
        <div
          ref={listRef}
          role="listbox"
          className={cn(
            "absolute top-full left-0 right-0 mt-2 z-50",
            "rounded-control border border-border dark:border-border-dark",
            "bg-canvas dark:bg-canvas-dark",
            "shadow-modal",
            "max-h-96 overflow-y-auto"
          )}
        >
          {availableModels.map((model, index) => (
            <button
              key={model.id}
              role="option"
              aria-selected={selectedModelId === model.id}
              onClick={() => handleSelectModel(model)}
              onMouseEnter={() => setHighlightedIndex(index)}
              className={cn(
                "w-full px-3 py-2.5 text-left border-b border-border/50 dark:border-border-dark/50 last:border-b-0",
                "hover:bg-canvas-panel dark:hover:bg-canvas-dark-alt",
                "focus:outline-none focus:bg-canvas-panel dark:focus:bg-canvas-dark-alt",
                "transition-colors",
                highlightedIndex === index &&
                  "bg-canvas-panel dark:bg-canvas-dark-alt",
                selectedModelId === model.id &&
                  "bg-accent-600/10 dark:bg-accent-600/10"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-body text-ink dark:text-ink-dark">
                    {model.display_name}
                    {selectedModelId === model.id && (
                      <span className="ml-2 text-accent-600 dark:text-accent-400">✓</span>
                    )}
                  </div>
                  <div className="text-meta text-ink/60 dark:text-ink-dark/60">
                    {model.description}
                  </div>
                  <div className="text-meta text-ink/40 dark:text-ink-dark/40 mt-1">
                    Tier: {model.tier}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
