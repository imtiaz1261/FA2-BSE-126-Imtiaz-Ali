import { apiRequest } from "@/lib/api";

export type DateGroup = "today" | "yesterday" | "previous_7_days" | "older";

export interface ConversationSummary {
  id: string;
  title: string;
  pinned: boolean;
  archived: boolean;
  folder_id: string | null;
  is_shared: boolean;
  last_message_at: string;
  created_at: string;
  date_group: DateGroup;
}

export interface SearchResultItem extends ConversationSummary {
  snippet: string;
}

export interface ConversationListResponse {
  items: ConversationSummary[];
  next_cursor: string | null;
}

export interface SearchResponse {
  items: SearchResultItem[];
  next_cursor: string | null;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  pinned: boolean;
  archived: boolean;
  folder_id: string | null;
  is_shared: boolean;
  messages: ConversationMessage[];
}

export interface Folder {
  id: string;
  name: string;
  created_at: string;
}

export interface ShareResponse {
  share_token: string;
  share_url: string;
  shared_at: string;
}

export interface SharedConversation {
  title: string;
  created_at: string;
  messages: { role: "user" | "assistant"; content: string; created_at: string }[];
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const str = search.toString();
  return str ? `?${str}` : "";
}

export const conversationsApi = {
  list: (params: { cursor?: string; folderId?: string; archived?: boolean } = {}) =>
    apiRequest<ConversationListResponse>(
      `/conversations${qs({
        cursor: params.cursor,
        folder_id: params.folderId,
        archived: params.archived,
      })}`
    ),

  search: (q: string, params: { offset?: number; archived?: boolean } = {}) =>
    apiRequest<SearchResponse>(
      `/conversations/search${qs({ q, offset: params.offset, archived: params.archived })}`
    ),

  get: (id: string) => apiRequest<ConversationDetail>(`/conversations/${id}`),

  create: (data: { title?: string; folder_id?: string } = {}) =>
    apiRequest<ConversationSummary>("/conversations", { method: "POST", body: data }),

  patch: (
    id: string,
    data: {
      title?: string;
      pinned?: boolean;
      archived?: boolean;
      folder_id?: string;
      clear_folder?: boolean;
    }
  ) => apiRequest<ConversationSummary>(`/conversations/${id}`, { method: "PATCH", body: data }),

  delete: (id: string) => apiRequest<void>(`/conversations/${id}`, { method: "DELETE" }),

  share: (id: string) =>
    apiRequest<ShareResponse>(`/conversations/${id}/share`, { method: "POST" }),

  revokeShare: (id: string) =>
    apiRequest<void>(`/conversations/${id}/share`, { method: "DELETE" }),

  folders: {
    list: () => apiRequest<Folder[]>("/folders"),
    create: (name: string) => apiRequest<Folder>("/folders", { method: "POST", body: { name } }),
    delete: (id: string) => apiRequest<void>(`/folders/${id}`, { method: "DELETE" }),
  },
};

/** Public — no auth header needed, but harmless to include if present. */
export const sharedConversationApi = {
  get: (token: string) => apiRequest<SharedConversation>(`/share/${token}`),
};
