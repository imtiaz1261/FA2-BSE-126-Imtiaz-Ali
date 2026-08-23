import { create } from "zustand";
import { conversationsApi, } from "@/lib/conversationsApi";
export const useConversationsStore = create((set, get) => ({
    items: [],
    nextCursor: null,
    isLoadingInitial: false,
    isLoadingMore: false,
    searchQuery: "",
    searchResults: null,
    isSearching: false,
    folders: [],
    activeFolderId: null,
    showArchived: false,
    fetchInitial: async () => {
        set({ isLoadingInitial: true });
        try {
            const { activeFolderId, showArchived } = get();
            const res = await conversationsApi.list({
                folderId: activeFolderId ?? undefined,
                archived: showArchived,
            });
            set({ items: res.items, nextCursor: res.next_cursor });
        }
        finally {
            set({ isLoadingInitial: false });
        }
    },
    fetchMore: async () => {
        const { nextCursor, isLoadingMore, activeFolderId, showArchived } = get();
        if (!nextCursor || isLoadingMore)
            return;
        set({ isLoadingMore: true });
        try {
            const res = await conversationsApi.list({
                cursor: nextCursor,
                folderId: activeFolderId ?? undefined,
                archived: showArchived,
            });
            set((state) => ({
                items: [...state.items, ...res.items],
                nextCursor: res.next_cursor,
            }));
        }
        finally {
            set({ isLoadingMore: false });
        }
    },
    refreshFirstPage: async () => {
        const { activeFolderId, showArchived } = get();
        const res = await conversationsApi.list({
            folderId: activeFolderId ?? undefined,
            archived: showArchived,
        });
        // Merge rather than blindly replace: keep any already-loaded items
        // past the first page that the refresh wouldn't have re-fetched.
        set((state) => {
            const freshIds = new Set(res.items.map((c) => c.id));
            const rest = state.items.filter((c) => !freshIds.has(c.id) && !res.items.find((f) => f.id === c.id));
            return { items: [...res.items, ...rest] };
        });
    },
    setSearchQuery: (q) => set({ searchQuery: q }),
    runSearch: async (q) => {
        const trimmed = q.trim();
        if (!trimmed) {
            set({ searchResults: null, isSearching: false });
            return;
        }
        set({ isSearching: true });
        try {
            const res = await conversationsApi.search(trimmed, { archived: get().showArchived });
            // Guard against out-of-order responses: only apply if this is still
            // the current query (the caller debounces, but a slow request could
            // still resolve after a newer, faster one).
            if (get().searchQuery.trim() === trimmed) {
                set({ searchResults: res.items });
            }
        }
        finally {
            if (get().searchQuery.trim() === trimmed)
                set({ isSearching: false });
        }
    },
    clearSearch: () => set({ searchQuery: "", searchResults: null, isSearching: false }),
    setActiveFolder: (folderId) => {
        set({ activeFolderId: folderId });
        void get().fetchInitial();
    },
    setShowArchived: (show) => {
        set({ showArchived: show });
        void get().fetchInitial();
    },
    fetchFolders: async () => {
        const folders = await conversationsApi.folders.list();
        set({ folders });
    },
    createFolder: async (name) => {
        const folder = await conversationsApi.folders.create(name);
        set((state) => ({ folders: [...state.folders, folder].sort((a, b) => a.name.localeCompare(b.name)) }));
        return folder;
    },
    deleteFolder: async (id) => {
        await conversationsApi.folders.delete(id);
        set((state) => ({
            folders: state.folders.filter((f) => f.id !== id),
            activeFolderId: state.activeFolderId === id ? null : state.activeFolderId,
            // Conversations inside fall back to unfiled server-side (FK ON DELETE
            // SET NULL) — reflect that locally instead of refetching.
            items: state.items.map((c) => (c.folder_id === id ? { ...c, folder_id: null } : c)),
        }));
    },
    renameConversation: async (id, title) => {
        const trimmed = title.trim();
        if (!trimmed)
            return;
        set((state) => ({
            items: state.items.map((c) => (c.id === id ? { ...c, title: trimmed } : c)),
        }));
        await conversationsApi.patch(id, { title: trimmed });
    },
    togglePin: async (id, pinned) => {
        set((state) => ({
            items: state.items.map((c) => (c.id === id ? { ...c, pinned } : c)),
        }));
        await conversationsApi.patch(id, { pinned });
        // Pin state changes ordering (pinned items float to the top) —
        // re-fetch rather than try to re-sort the paginated list client-side.
        void get().refreshFirstPage();
    },
    toggleArchive: async (id, archived) => {
        // Archiving removes it from the current (non-archived) view entirely.
        set((state) => ({ items: state.items.filter((c) => c.id !== id) }));
        await conversationsApi.patch(id, { archived });
    },
    moveToFolder: async (id, folderId) => {
        set((state) => ({
            items: state.items.map((c) => (c.id === id ? { ...c, folder_id: folderId } : c)),
        }));
        await conversationsApi.patch(id, folderId ? { folder_id: folderId } : { clear_folder: true });
    },
    deleteConversation: async (id) => {
        const previous = get().items;
        set((state) => ({ items: state.items.filter((c) => c.id !== id) }));
        try {
            await conversationsApi.delete(id);
        }
        catch (err) {
            set({ items: previous }); // roll back on failure
            throw err;
        }
    },
    setShared: (id, isShared) => {
        set((state) => ({
            items: state.items.map((c) => (c.id === id ? { ...c, is_shared: isShared } : c)),
        }));
    },
}));
