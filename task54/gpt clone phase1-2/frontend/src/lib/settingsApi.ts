/**
 * Settings and Model API client
 * Handles all communication with backend settings, model selection, and usage endpoints
 */

import { apiRequest } from "./api";

export interface SettingsPreferences {
  theme: "light" | "dark" | "system";
  font_size: "small" | "medium" | "large";
  language: string;
  assistant_context: string;
  response_preferences: string;
}

export interface SettingsResponse {
  preferences: SettingsPreferences;
}

export interface AvailableModel {
  id: string;
  name: string;
  display_name: string;
  description: string;
  tier: string;
}

export interface ModelSelectorResponse {
  conversation_id: string;
  selected_model_id: string | null;
  selected_model: AvailableModel | null;
  available_models: AvailableModel[];
}

export interface UsageResponse {
  used: number;
  limit: number;
  remaining: number;
}

export interface ExportJobResponse {
  job_id: string;
  status: string;
  download_url: string | null;
  expires_at: string | null;
}

export interface DataExportJob {
  job_id: string;
  status: string;
  download_url: string | null;
  expires_at: string | null;
}

export const settingsApi = {
  // Settings endpoints
  getSettings: async (): Promise<SettingsResponse> => {
    return apiRequest<SettingsResponse>("/settings");
  },

  updateSettings: async (preferences: Partial<SettingsPreferences>): Promise<SettingsResponse> => {
    return apiRequest<SettingsResponse>("/settings", {
      method: "PATCH",
      body: { preferences },
    });
  },

  // Model endpoints
  listModels: async (): Promise<AvailableModel[]> => {
    return apiRequest<AvailableModel[]>("/models");
  },

  // Conversation model selection
  getConversationModel: async (conversationId: string): Promise<ModelSelectorResponse> => {
    return apiRequest<ModelSelectorResponse>(`/conversations/${conversationId}/model`);
  },

  selectConversationModel: async (
    conversationId: string,
    modelId: string
  ): Promise<ModelSelectorResponse> => {
    return apiRequest<ModelSelectorResponse>(`/conversations/${conversationId}/model`, {
      method: "PATCH",
      body: { model_id: modelId },
    });
  },

  // Usage tracking
  getUsage: async (): Promise<UsageResponse> => {
    return apiRequest<UsageResponse>("/usage");
  },

  // Data export
  initiateExport: async (): Promise<ExportJobResponse> => {
    return apiRequest<ExportJobResponse>("/settings/export", {
      method: "POST",
      body: {},
    });
  },

  getExportStatus: async (jobId: string): Promise<ExportJobResponse> => {
    return apiRequest<ExportJobResponse>(`/settings/export/${jobId}`);
  },

  // Conversation management
  clearAllConversations: async (confirmation: string): Promise<void> => {
    return apiRequest<void>("/conversations", {
      method: "DELETE",
      body: { confirmation },
    });
  },

  // Account management
  deleteAccount: async (
    confirmation: string,
    password?: string
  ): Promise<void> => {
    return apiRequest<void>("/settings/account", {
      method: "DELETE",
      body: { confirmation, password },
    });
  },
};
