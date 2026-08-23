/**
 * Example Integration of Settings and Model Selector Components
 * 
 * This file shows how to integrate the ModelSelector, SettingsPanel, and UsageMeter
 * components into your app header and chat interface.
 */

import React, { useEffect, useState } from "react";
import { ModelSelector } from "../ModelSelector";
import { SettingsPanel } from "../SettingsPanel";
import { UsageMeter } from "../UsageMeter";
import { useChatStore } from "@/store/chatStore";
import { useSettingsStore } from "@/store/settingsStore";
import { Button } from "@chatline/design-system/components/Button";

/**
 * Example: Chat Header with Model Selector
 * 
 * Place this in your chat area header to show the current model
 * and allow switching between available models.
 */
export function ChatHeaderWithModelSelector() {
  const { conversationId } = useChatStore();
  const { selectedModelId, setSelectedModelId } = useSettingsStore();

  if (!conversationId) {
    return <div>Start a conversation to select a model</div>;
  }

  return (
    <div className="flex items-center gap-4 p-4 border-b border-border dark:border-border-dark">
      <div className="flex-1">
        <h1 className="text-heading font-semibold">Chat</h1>
      </div>
      <div className="w-64">
        <ModelSelector
          conversationId={conversationId}
          currentModelId={selectedModelId || undefined}
          onModelSelect={(modelId) => setSelectedModelId(modelId)}
        />
      </div>
    </div>
  );
}

/**
 * Example: Settings Button in Header
 * 
 * Place a settings button in your navigation that opens the SettingsPanel
 */
export function SettingsButton() {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setSettingsOpen(true)}
        aria-label="Open settings"
        className="p-2 rounded-control hover:bg-canvas dark:hover:bg-canvas-dark transition-colors"
        title="Settings"
      >
        <SettingsIcon />
      </button>
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </>
  );
}

/**
 * Example: Free-tier Usage Display
 * 
 * Show usage meter in a sidebar or info panel
 */
export function UsagePanel() {
  const { usage, fetchUsage } = useSettingsStore();

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  if (!usage) return null;

  return (
    <div className="p-4 border-t border-border dark:border-border-dark">
      <UsageMeter compact={false} showLabel={true} />
    </div>
  );
}

/**
 * Example: Full App Layout
 * 
 * Shows where to place all components
 */
export function AppLayout() {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="flex h-screen bg-canvas dark:bg-canvas-dark">
      {/* Sidebar */}
      <div className="w-72 border-r border-border dark:border-border-dark flex flex-col">
        {/* Usage meter at bottom for free-tier */}
        <UsagePanel />
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header with model selector and settings button */}
        <div className="flex items-center justify-between p-4 border-b border-border dark:border-border-dark">
          <div className="flex-1">
            <ChatHeaderWithModelSelector />
          </div>
          <SettingsButton />
        </div>

        {/* Chat messages */}
        <div className="flex-1 overflow-y-auto">
          {/* Your chat messages here */}
        </div>

        {/* Chat input */}
        <div className="p-4 border-t border-border dark:border-border-dark">
          {/* Your input component here */}
        </div>
      </div>

      {/* Settings panel modal */}
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

function SettingsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="1.5" stroke="currentColor" strokeWidth="2" />
      <circle cx="12" cy="19" r="1.5" stroke="currentColor" strokeWidth="2" />
      <circle cx="12" cy="5" r="1.5" stroke="currentColor" strokeWidth="2" />
      <path d="M15 12H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M3 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M15 19H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M3 19H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M15 5H21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M3 5H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
