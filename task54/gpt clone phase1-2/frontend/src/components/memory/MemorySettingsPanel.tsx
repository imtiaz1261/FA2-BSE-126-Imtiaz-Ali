import React, { useState } from "react";
import { cn } from "@/lib/cn";
import { Card } from "@/components/Card";

export interface MemorySettingsProps {
  memory_enabled: boolean;
  auto_extract_enabled: boolean;
  max_memory_items: number;
  context_injection_count: number;
  retrieval_threshold: number;
  retention_days: number;
}

interface MemorySettingsPanelProps {
  settings: MemorySettingsProps | null;
  onUpdate: (updates: Partial<MemorySettingsProps>) => Promise<void>;
  isLoading?: boolean;
}

const Toggle: React.FC<{
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label: string;
  description?: string;
}> = ({ checked, onChange, disabled, label, description }) => {
  return (
    <div className="flex items-start justify-between">
      <div className="flex-1">
        <label className="text-body font-medium text-ink dark:text-ink-dark cursor-pointer">
          {label}
        </label>
        {description && (
          <p className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
            {description}
          </p>
        )}
      </div>
      <button
        onClick={() => onChange(!checked)}
        disabled={disabled}
        className={cn(
          "relative inline-flex h-8 w-14 items-center rounded-full transition-colors flex-shrink-0 ml-4",
          checked
            ? "bg-accent-600"
            : "bg-canvas-panel dark:bg-canvas-dark-panel border border-border dark:border-border-dark",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <span
          className={cn(
            "inline-block h-6 w-6 transform rounded-full bg-white transition-transform",
            checked ? "translate-x-7" : "translate-x-1"
          )}
        />
      </button>
    </div>
  );
};

const Slider: React.FC<{
  label: string;
  description?: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  format?: (value: number) => string;
}> = ({
  label,
  description,
  value,
  min,
  max,
  step = 1,
  onChange,
  disabled,
  format,
}) => {
  return (
    <div className="space-y-2">
      <div>
        <div className="flex items-center justify-between">
          <label className="text-body font-medium text-ink dark:text-ink-dark">
            {label}
          </label>
          <span className="text-heading-sm font-bold text-accent-600 dark:text-accent-400">
            {format ? format(value) : value}
          </span>
        </div>
        {description && (
          <p className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
            {description}
          </p>
        )}
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
        className={cn(
          "w-full h-2 rounded-full bg-canvas-panel dark:bg-canvas-dark-panel appearance-none cursor-pointer",
          "accent-accent-600 disabled:opacity-50 disabled:cursor-not-allowed"
        )}
      />
      <div className="flex justify-between text-xs text-ink-secondary dark:text-ink-secondary-dark">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
};

export const MemorySettingsPanel: React.FC<MemorySettingsPanelProps> = ({
  settings,
  onUpdate,
  isLoading,
}) => {
  const [isSaving, setIsSaving] = useState(false);

  if (!settings) {
    return (
      <Card className="p-8 text-center">
        <p className="text-ink-secondary dark:text-ink-secondary-dark">
          Loading memory settings...
        </p>
      </Card>
    );
  }

  const handleUpdate = async (updates: Partial<MemorySettingsProps>) => {
    setIsSaving(true);
    try {
      await onUpdate(updates);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Master toggle */}
      <Card className="p-6 space-y-4">
        <Toggle
          checked={settings.memory_enabled}
          onChange={(checked) =>
            handleUpdate({ memory_enabled: checked })
          }
          disabled={isSaving}
          label="Enable Memory System"
          description="Remember facts, preferences, and context across conversations"
        />
      </Card>

      {/* Auto-extraction settings */}
      {settings.memory_enabled && (
        <Card className="p-6 space-y-6 border-l-4 border-accent-600 dark:border-accent-400">
          <div>
            <h3 className="text-heading-sm font-semibold text-ink dark:text-ink-dark mb-4">
              Extraction & Learning
            </h3>
            <div className="space-y-4">
              <Toggle
                checked={settings.auto_extract_enabled}
                onChange={(checked) =>
                  handleUpdate({ auto_extract_enabled: checked })
                }
                disabled={isSaving}
                label="Auto-extract Facts"
                description="Automatically extract durable facts from your conversations"
              />

              {settings.auto_extract_enabled && (
                <div className="mt-4 p-3 bg-accent-600/10 dark:bg-accent-600/20 rounded-control">
                  <p className="text-xs text-accent-600 dark:text-accent-400">
                    💡 Facts are extracted after each conversation completes
                    and reviewed for accuracy before storage.
                  </p>
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Context injection settings */}
      {settings.memory_enabled && (
        <Card className="p-6 space-y-6 border-l-4 border-blue-600 dark:border-blue-400">
          <div>
            <h3 className="text-heading-sm font-semibold text-ink dark:text-ink-dark mb-4">
              Context Injection
            </h3>
            <div className="space-y-6">
              <Slider
                label="Maximum Memories to Include"
                description="Number of most relevant memories injected into each conversation"
                value={settings.context_injection_count}
                min={0}
                max={20}
                onChange={(value) =>
                  handleUpdate({ context_injection_count: value })
                }
                disabled={isSaving}
              />

              <Slider
                label="Relevance Threshold"
                description="Minimum relevance score (0-100%) required to include a memory"
                value={settings.retrieval_threshold}
                min={0}
                max={1}
                step={0.05}
                onChange={(value) =>
                  handleUpdate({ retrieval_threshold: value })
                }
                disabled={isSaving}
                format={(value) => `${(value * 100).toFixed(0)}%`}
              />

              <div className="p-3 bg-blue-600/10 dark:bg-blue-600/20 rounded-control">
                <p className="text-xs text-blue-600 dark:text-blue-400">
                  🎯 Only the most contextually relevant memories are included
                  in your conversations to maintain focus and clarity.
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Storage settings */}
      {settings.memory_enabled && (
        <Card className="p-6 space-y-6 border-l-4 border-purple-600 dark:border-purple-400">
          <div>
            <h3 className="text-heading-sm font-semibold text-ink dark:text-ink-dark mb-4">
              Storage & Retention
            </h3>
            <div className="space-y-6">
              <Slider
                label="Maximum Memory Items"
                description="Maximum number of facts to store before oldest ones are removed"
                value={settings.max_memory_items}
                min={10}
                max={500}
                step={10}
                onChange={(value) =>
                  handleUpdate({ max_memory_items: value })
                }
                disabled={isSaving}
              />

              <Slider
                label="Retention Period"
                description="Days to keep memories (0 = keep forever)"
                value={settings.retention_days}
                min={0}
                max={730}
                step={30}
                onChange={(value) =>
                  handleUpdate({ retention_days: value })
                }
                disabled={isSaving}
                format={(value) =>
                  value === 0
                    ? "Forever"
                    : `${value} day${value !== 1 ? "s" : ""}`
                }
              />

              <div className="p-3 bg-purple-600/10 dark:bg-purple-600/20 rounded-control">
                <p className="text-xs text-purple-600 dark:text-purple-400">
                  📦 Memory system is optimized for efficient storage. Old
                  memories are automatically cleaned up based on your settings.
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Memory disabled notice */}
      {!settings.memory_enabled && (
        <Card className="p-6 bg-yellow-600/10 dark:bg-yellow-600/20 border border-yellow-600 dark:border-yellow-600">
          <div className="space-y-3">
            <p className="text-body font-medium text-yellow-600 dark:text-yellow-400">
              ⚠️ Memory System Disabled
            </p>
            <p className="text-meta text-yellow-600/80 dark:text-yellow-400/80">
              When memory is disabled, the assistant will not retain any
              information about you across conversations. Enable it above to
              benefit from personalized interactions.
            </p>
          </div>
        </Card>
      )}

      {/* Info section */}
      <Card className="p-6 bg-canvas-panel dark:bg-canvas-dark-panel">
        <div className="space-y-3">
          <h4 className="text-body font-medium text-ink dark:text-ink-dark">
            ℹ️ How Memory Works
          </h4>
          <ul className="text-meta text-ink-secondary dark:text-ink-secondary-dark space-y-2">
            <li className="flex gap-2">
              <span className="flex-shrink-0">1.</span>
              <span>
                At the end of each conversation, relevant facts are extracted
              </span>
            </li>
            <li className="flex gap-2">
              <span className="flex-shrink-0">2.</span>
              <span>
                These facts are stored and categorized with confidence scores
              </span>
            </li>
            <li className="flex gap-2">
              <span className="flex-shrink-0">3.</span>
              <span>
                When starting new conversations, relevant memories are retrieved
              </span>
            </li>
            <li className="flex gap-2">
              <span className="flex-shrink-0">4.</span>
              <span>
                Memories are injected as hidden context to personalize responses
              </span>
            </li>
            <li className="flex gap-2">
              <span className="flex-shrink-0">5.</span>
              <span>You can manually edit or delete memories anytime</span>
            </li>
          </ul>
        </div>
      </Card>
    </div>
  );
};
