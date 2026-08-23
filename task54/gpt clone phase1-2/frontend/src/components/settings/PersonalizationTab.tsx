/**
 * Personalization Settings Tab
 * Custom instructions for the assistant
 */

import React, { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { useSettingsStore } from "@/store/settingsStore";

interface PersonalizationTabProps {
  onClose?: () => void;
}

export function PersonalizationTab({ onClose }: PersonalizationTabProps) {
  const {
    preferences,
    fetchPreferences,
    setAssistantContext,
    setResponsePreferences,
    isLoadingPreferences,
  } = useSettingsStore();

  const [assistantContext, setContextLocal] = useState<string>("");
  const [responsePrefs, setResponsePrefsLocal] = useState<string>("");
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  useEffect(() => {
    if (preferences) {
      setContextLocal(preferences.assistant_context || "");
      setResponsePrefsLocal(preferences.response_preferences || "");
    }
  }, [preferences]);

  const handleSaveContext = async () => {
    await setAssistantContext(assistantContext);
    setIsDirty(false);
  };

  const handleSaveResponsePrefs = async () => {
    await setResponsePreferences(responsePrefs);
    setIsDirty(false);
  };

  const handleContextChange = (text: string) => {
    setContextLocal(text);
    setIsDirty(true);
  };

  const handleResponsePrefsChange = (text: string) => {
    setResponsePrefsLocal(text);
    setIsDirty(true);
  };

  return (
    <div className="space-y-6 pb-6">
      {/* About You */}
      <div>
        <label htmlFor="context" className="block text-body font-medium text-ink dark:text-ink-dark mb-2">
          What should the assistant know about you?
        </label>
        <p className="text-meta text-ink/60 dark:text-ink-dark/60 mb-2">
          Share any relevant background, preferences, or context that helps the assistant serve you better.
        </p>
        <textarea
          id="context"
          value={assistantContext}
          onChange={(e) => handleContextChange(e.target.value)}
          placeholder="e.g., I'm a Python developer learning machine learning. I prefer concise explanations with code examples."
          disabled={isLoadingPreferences}
          className={cn(
            "w-full px-3 py-2 rounded-control border text-body font-mono text-sm",
            "bg-canvas dark:bg-canvas-dark",
            "border-border dark:border-border-dark",
            "text-ink dark:text-ink-dark placeholder:text-ink/40 dark:placeholder:text-ink-dark/40",
            "focus:outline-none focus:ring-2 focus:ring-accent-600 dark:focus:ring-accent-400",
            "transition-colors resize-none",
            "disabled:opacity-50"
          )}
          rows={4}
        />
        <div className="flex justify-between items-center mt-2">
          <span className="text-meta text-ink/40 dark:text-ink-dark/40">
            {assistantContext.length} characters
          </span>
          {isDirty && (
            <button
              onClick={handleSaveContext}
              disabled={isLoadingPreferences}
              className={cn(
                "px-3 py-1 rounded-control text-meta font-medium transition-colors",
                "bg-accent-600 text-white hover:bg-accent-700",
                "dark:bg-accent-500 dark:hover:bg-accent-600",
                "disabled:opacity-50"
              )}
            >
              Save
            </button>
          )}
        </div>
      </div>

      {/* Response Style */}
      <div>
        <label htmlFor="response" className="block text-body font-medium text-ink dark:text-ink-dark mb-2">
          How should the assistant respond?
        </label>
        <p className="text-meta text-ink/60 dark:text-ink-dark/60 mb-2">
          Describe your preferred tone, verbosity, format, and any other style preferences.
        </p>
        <textarea
          id="response"
          value={responsePrefs}
          onChange={(e) => handleResponsePrefsChange(e.target.value)}
          placeholder="e.g., Be concise but thorough. Use bullet points for lists. Provide practical examples. Ask clarifying questions if needed."
          disabled={isLoadingPreferences}
          className={cn(
            "w-full px-3 py-2 rounded-control border text-body font-mono text-sm",
            "bg-canvas dark:bg-canvas-dark",
            "border-border dark:border-border-dark",
            "text-ink dark:text-ink-dark placeholder:text-ink/40 dark:placeholder:text-ink-dark/40",
            "focus:outline-none focus:ring-2 focus:ring-accent-600 dark:focus:ring-accent-400",
            "transition-colors resize-none",
            "disabled:opacity-50"
          )}
          rows={4}
        />
        <div className="flex justify-between items-center mt-2">
          <span className="text-meta text-ink/40 dark:text-ink-dark/40">
            {responsePrefs.length} characters
          </span>
          {isDirty && (
            <button
              onClick={handleSaveResponsePrefs}
              disabled={isLoadingPreferences}
              className={cn(
                "px-3 py-1 rounded-control text-meta font-medium transition-colors",
                "bg-accent-600 text-white hover:bg-accent-700",
                "dark:bg-accent-500 dark:hover:bg-accent-600",
                "disabled:opacity-50"
              )}
            >
              Save
            </button>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="p-3 rounded-control bg-canvas-panel dark:bg-canvas-dark-panel border border-border/50 dark:border-border-dark/50">
        <p className="text-meta text-ink/60 dark:text-ink-dark/60">
          These preferences are included in every request as system-level context to personalize the assistant's responses.
        </p>
      </div>
    </div>
  );
}
