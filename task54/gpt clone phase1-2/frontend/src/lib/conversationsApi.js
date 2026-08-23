import { apiRequest } from "@/lib/api";
function qs(params) {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
        if (value !== undefined)
            search.set(key, String(value));
    }
    const str = search.toString();
    return str ? `?${str}` : "";
}
export const conversationsApi = {
    list: (params = {}) => apiRequest(`/conversations${qs({
        cursor: params.cursor,
        folder_id: params.folderId,
        archived: params.archived,
    })}`),
    search: (q, params = {}) => apiRequest(`/conversations/search${qs({ q, offset: params.offset, archived: params.archived })}`),
    get: (id) => apiRequest(`/conversations/${id}`),
    create: (data = {}) => apiRequest("/conversations", { method: "POST", body: data }),
    patch: (id, data) => apiRequest(`/conversations/${id}`, { method: "PATCH", body: data }),
    delete: (id) => apiRequest(`/conversations/${id}`, { method: "DELETE" }),
    share: (id) => apiRequest(`/conversations/${id}/share`, { method: "POST" }),
    revokeShare: (id) => apiRequest(`/conversations/${id}/share`, { method: "DELETE" }),
    folders: {
        list: () => apiRequest("/folders"),
        create: (name) => apiRequest("/folders", { method: "POST", body: { name } }),
        delete: (id) => apiRequest(`/folders/${id}`, { method: "DELETE" }),
    },
};
/** Public — no auth header needed, but harmless to include if present. */
export const sharedConversationApi = {
    get: (token) => apiRequest(`/share/${token}`),
};
