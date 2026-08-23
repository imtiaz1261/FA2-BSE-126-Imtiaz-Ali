/**
 * Settings Panel Modal
 * 
 * Tabbed interface for:
 * - General: theme, font size, language
 * - Personalization: custom instructions
 * - Data Controls: export, clear, delete account
 */

import React, { useState } from "react";
import { cn } from "@/lib/cn";
import { Modal } from "@/components/ui/Modal";
import { GeneralTab } from "./settings/GeneralTab";
import { PersonalizationTab } from "./settings/PersonalizationTab";
import { DataControlsTab } from "./settings/DataControlsTab";

interface SettingsPanelProps {
  open: boolean;
  onClose: () => void;
}

type TabType = "general" | "personalization" | "data-controls";

export function SettingsPanel({ open, onClose }: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>("general");

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    {
      id: "general",
      label: "General",
      icon: <GeneralIcon />,
    },
    {
      id: "personalization",
      label: "Personalization",
      icon: <PersonalizationIcon />,
    },
    {
      id: "data-controls",
      label: "Data Controls",
      icon: <DataIcon />,
    },
  ];

  return (
    <Modal open={open} onClose={onClose} title="Settings" className="max-w-2xl max-h-96 overflow-hidden flex flex-col">
      <div className="flex flex-col h-full">
        {/* Tab Navigation */}
        <div className="flex gap-1 border-b border-border dark:border-border-dark pb-0 mb-6 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-t-control text-meta font-medium transition-colors whitespace-nowrap",
                activeTab === tab.id
                  ? "bg-canvas dark:bg-canvas-dark text-accent-600 dark:text-accent-400 border-b-2 border-accent-600 dark:border-accent-400"
                  : "text-ink/60 dark:text-ink-dark/60 hover:text-ink dark:hover:text-ink-dark"
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "general" && <GeneralTab onClose={onClose} />}
          {activeTab === "personalization" && <PersonalizationTab onClose={onClose} />}
          {activeTab === "data-controls" && <DataControlsTab onClose={onClose} />}
        </div>
      </div>
    </Modal>
  );
}

function GeneralIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.2" />
      <path
        d="M8 4.5V8L10.5 9.5"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PersonalizationIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.2" />
      <path
        d="M3 13C3 10.6 5.2 8.5 8 8.5C10.8 8.5 13 10.6 13 13"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DataIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="12" height="12" rx="1" stroke="currentColor" strokeWidth="1.2" />
      <path d="M5 6H11M5 10H11" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}
