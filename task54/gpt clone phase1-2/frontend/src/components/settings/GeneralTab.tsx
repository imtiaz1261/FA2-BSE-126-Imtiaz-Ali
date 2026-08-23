/**
 * General Settings Tab
 * Theme, font size, language
 */

import React, { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { useSettingsStore } from "@/store/settingsStore";

interface GeneralTabProps {
  onClose?: () => void;
}

export function GeneralTab({ onClose }: GeneralTabProps) {
  const { preferences, fetchPreferences, setTheme, setFontSize, setLanguage, isLoadingPreferences } =
    useSettingsStore();

  const [theme, setThemeLocal] = useState<string>(preferences?.theme || "system");
  const [fontSize, setFontSizeLocal] = useState<string>(preferences?.font_size || "medium");
  const [language, setLanguageLocal] = useState<string>(preferences?.language || "en");

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  useEffect(() => {
    if (preferences) {
      setThemeLocal(preferences.theme);
      setFontSizeLocal(preferences.font_size);
      setLanguageLocal(preferences.language);
    }
  }, [preferences]);

  const handleThemeChange = async (newTheme: string) => {
    setThemeLocal(newTheme);
    await setTheme(newTheme as any);
  };

  const handleFontSizeChange = async (newSize: string) => {
    setFontSizeLocal(newSize);
    await setFontSize(newSize as any);
  };

  const handleLanguageChange = async (newLang: string) => {
    setLanguageLocal(newLang);
    await setLanguage(newLang);
  };

  const languages = [
    { code: "en", name: "English" },
    { code: "es", name: "Español" },
    { code: "fr", name: "Français" },
    { code: "de", name: "Deutsch" },
    { code: "ja", name: "日本語" },
    { code: "zh", name: "中文" },
  ];

  return (
    <div className="space-y-6 pb-6">
      {/* Theme */}
      <div>
        <label className="block text-body font-medium text-ink dark:text-ink-dark mb-3">
          Theme
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "light", label: "Light" },
            { value: "dark", label: "Dark" },
            { value: "system", label: "System" },
          ].map(({ value, label }) => (
            <button
              key={value}
              onClick={() => handleThemeChange(value)}
              className={cn(
                "px-3 py-2 rounded-control border text-meta font-medium transition-all",
                theme === value
                  ? "border-accent-600 dark:border-accent-400 bg-accent-600/10 text-accent-600 dark:text-accent-400"
                  : "border-border dark:border-border-dark text-ink/70 dark:text-ink-dark/70 hover:border-border-dark dark:hover:border-border-light"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Font Size */}
      <div>
        <label className="block text-body font-medium text-ink dark:text-ink-dark mb-3">
          Font Size
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "small", label: "Small" },
            { value: "medium", label: "Medium" },
            { value: "large", label: "Large" },
          ].map(({ value, label }) => (
            <button
              key={value}
              onClick={() => handleFontSizeChange(value)}
              className={cn(
                "px-3 py-2 rounded-control border text-meta font-medium transition-all",
                fontSize === value
                  ? "border-accent-600 dark:border-accent-400 bg-accent-600/10 text-accent-600 dark:text-accent-400"
                  : "border-border dark:border-border-dark text-ink/70 dark:text-ink-dark/70 hover:border-border-dark dark:hover:border-border-light"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Language */}
      <div>
        <label htmlFor="language" className="block text-body font-medium text-ink dark:text-ink-dark mb-3">
          Language
        </label>
        <select
          id="language"
          value={language}
          onChange={(e) => handleLanguageChange(e.target.value)}
          disabled={isLoadingPreferences}
          className={cn(
            "w-full px-3 py-2 rounded-control border text-body",
            "bg-canvas dark:bg-canvas-dark",
            "border-border dark:border-border-dark",
            "text-ink dark:text-ink-dark",
            "focus:outline-none focus:ring-2 focus:ring-accent-600 dark:focus:ring-accent-400",
            "transition-colors",
            "disabled:opacity-50"
          )}
        >
          {languages.map(({ code, name }) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {/* Info */}
      <div className="p-3 rounded-control bg-canvas-panel dark:bg-canvas-dark-panel border border-border/50 dark:border-border-dark/50">
        <p className="text-meta text-ink/60 dark:text-ink-dark/60">
          Your preferences are saved automatically and applied across all conversations.
        </p>
      </div>
    </div>
  );
}
