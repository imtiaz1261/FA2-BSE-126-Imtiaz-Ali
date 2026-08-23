/**
 * Zustand store for user settings and model selection
 */

import { create } from "zustand";
import { settingsApi, SettingsPreferences, AvailableModel, UsageResponse } from "@/lib/settingsApi";

interface SettingsState {
  // Preferences
  preferences: SettingsPreferences | null;
  isLoadingPreferences: boolean;
  preferencesError: string | null;

  // Models
  availableModels: AvailableModel[] | null;
  selectedModelId: string | null; // For current conversation
  isLoadingModels: boolean;
  modelsError: string | null;

  // Usage tracking
  usage: UsageResponse | null;
  isLoadingUsage: boolean;
  usageError: string | null;

  // Actions
  fetchPreferences: () => Promise<void>;
  updatePreferences: (prefs: Partial<SettingsPreferences>) => Promise<void>;
  setTheme: (theme: "light" | "dark" | "system") => Promise<void>;
  setFontSize: (size: "small" | "medium" | "large") => Promise<void>;
  setLanguage: (lang: string) => Promise<void>;
  setAssistantContext: (context: string) => Promise<void>;
  setResponsePreferences: (prefs: string) => Promise<void>;

  fetchModels: () => Promise<void>;
  selectModel: (conversationId: string, modelId: string) => Promise<void>;
  setSelectedModelId: (modelId: string | null) => void;

  fetchUsage: () => Promise<void>;

  initiateDataExport: () => Promise<string>; // Returns job ID
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  preferences: null,
  isLoadingPreferences: false,
  preferencesError: null,

  availableModels: null,
  selectedModelId: null,
  isLoadingModels: false,
  modelsError: null,

  usage: null,
  isLoadingUsage: false,
  usageError: null,

  fetchPreferences: async () => {
    set({ isLoadingPreferences: true, preferencesError: null });
    try {
      const res = await settingsApi.getSettings();
      set({ preferences: res.preferences });
    } catch (err) {
      set({
        preferencesError: err instanceof Error ? err.message : "Failed to fetch preferences",
      });
    } finally {
      set({ isLoadingPreferences: false });
    }
  },

  updatePreferences: async (prefs: Partial<SettingsPreferences>) => {
    set({ isLoadingPreferences: true, preferencesError: null });
    try {
      const currentPrefs = get().preferences || {
        theme: "system",
        font_size: "medium",
        language: "en",
        assistant_context: "",
        response_preferences: "",
      };
      const updated = { ...currentPrefs, ...prefs };
      const res = await settingsApi.updateSettings(updated);
      set({ preferences: res.preferences });
    } catch (err) {
      set({
        preferencesError: err instanceof Error ? err.message : "Failed to update preferences",
      });
    } finally {
      set({ isLoadingPreferences: false });
    }
  },

  setTheme: async (theme: "light" | "dark" | "system") => {
    await get().updatePreferences({ theme });
  },

  setFontSize: async (size: "small" | "medium" | "large") => {
    await get().updatePreferences({ font_size: size });
  },

  setLanguage: async (lang: string) => {
    await get().updatePreferences({ language: lang });
  },

  setAssistantContext: async (context: string) => {
    await get().updatePreferences({ assistant_context: context });
  },

  setResponsePreferences: async (prefs: string) => {
    await get().updatePreferences({ response_preferences: prefs });
  },

  fetchModels: async () => {
    set({ isLoadingModels: true, modelsError: null });
    try {
      const models = await settingsApi.listModels();
      set({ availableModels: models });
    } catch (err) {
      set({
        modelsError: err instanceof Error ? err.message : "Failed to fetch models",
      });
    } finally {
      set({ isLoadingModels: false });
    }
  },

  selectModel: async (conversationId: string, modelId: string) => {
    try {
      await settingsApi.selectConversationModel(conversationId, modelId);
      set({ selectedModelId: modelId });
    } catch (err) {
      set({
        modelsError: err instanceof Error ? err.message : "Failed to select model",
      });
    }
  },

  setSelectedModelId: (modelId: string | null) => {
    set({ selectedModelId: modelId });
  },

  fetchUsage: async () => {
    set({ isLoadingUsage: true, usageError: null });
    try {
      const usage = await settingsApi.getUsage();
      set({ usage });
    } catch (err) {
      set({
        usageError: err instanceof Error ? err.message : "Failed to fetch usage",
      });
    } finally {
      set({ isLoadingUsage: false });
    }
  },

  initiateDataExport: async () => {
    try {
      const result = await settingsApi.initiateExport();
      return result.job_id;
    } catch (err) {
      throw err;
    }
  },
}));
