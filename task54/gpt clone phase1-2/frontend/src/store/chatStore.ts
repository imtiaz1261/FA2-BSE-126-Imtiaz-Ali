import { create } from "zustand";
import { conversationsApi } from "@/lib/conversationsApi";
import { streamChat, stopGeneration as stopGenerationRequest, ChatStreamEvent } from "../lib/chatStream";

export type MessageRole = "user" | "assistant";
export type MessageStatus = "complete" | "streaming" | "stopped" | "error";
export type Feedback = "up" | "down" | null;

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  feedback: Feedback;
  createdAt: number;
}

interface ChatState {
  messages: ChatMessage[];
  conversationId: string | null;
  /** id of the assistant message currently streaming, if any (frontend-local id) */
  streamingMessageId: string | null;
  /** the backend's own id for the in-flight generation, from the "start" SSE event —
   * this is what /chat/stream/{id}/stop actually expects, and differs from the
   * frontend-local id above. */
  streamingBackendMessageId: string | null;
  abortController: AbortController | null;

  sendMessage: (content: string) => Promise<void>;
  loadConversation: (conversationId: string) => Promise<void>;
  startNewChat: () => void;
  regenerate: (assistantMessageId: string) => Promise<void>;
  editAndResend: (userMessageId: string, newContent: string) => Promise<void>;
  stopGeneration: () => void;
  setFeedback: (messageId: string, feedback: Feedback) => void;
}

function newId() {
  return crypto.randomUUID();
}

/** Runs the shared streaming flow: appends a placeholder assistant message,
 * streams tokens into it, and settles its final status. `historyMessages`
 * is what actually gets sent to the backend as conversation context.
 */
async function runAssistantStream(
  set: (fn: (state: ChatState) => Partial<ChatState>) => void,
  get: () => ChatState,
  conversationId: string | null,
  historyMessages: { role: MessageRole; content: string }[]
) {
  const assistantId = newId();
  const controller = new AbortController();

  set((state) => ({
    messages: [
      ...state.messages,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        status: "streaming",
        feedback: null,
        createdAt: Date.now(),
      },
    ],
    streamingMessageId: assistantId,
    abortController: controller,
  }));

  const onEvent = (event: ChatStreamEvent) => {
    switch (event.type) {
      case "start":
        set(() => ({ streamingBackendMessageId: event.message_id }));
        break;
      case "token":
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + event.content } : m
          ),
        }));
        break;
      case "done":
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === assistantId ? { ...m, status: "complete" } : m
          ),
          streamingMessageId: null,
          streamingBackendMessageId: null,
          abortController: null,
        }));
        break;
      case "stopped":
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === assistantId ? { ...m, status: "stopped" } : m
          ),
          streamingMessageId: null,
          streamingBackendMessageId: null,
          abortController: null,
        }));
        break;
      case "error":
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === assistantId
              ? { ...m, status: "error", content: m.content || event.message }
              : m
          ),
          streamingMessageId: null,
          streamingBackendMessageId: null,
          abortController: null,
        }));
        break;
    }
  };

  await streamChat({ messages: historyMessages, onEvent, signal: controller.signal });

  // Covers the case where the stream ends without an explicit "done"/"stopped"
  // frame (e.g. the fetch itself was aborted client-side via the Stop button).
  const stillStreaming = get().messages.find((m) => m.id === assistantId)?.status === "streaming";
  if (stillStreaming) {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === assistantId ? { ...m, status: "stopped" } : m
      ),
      streamingMessageId: null,
      streamingBackendMessageId: null,
      abortController: null,
    }));
  }
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  conversationId: null,
  streamingMessageId: null,
  streamingBackendMessageId: null,
  abortController: null,

  sendMessage: async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || get().streamingMessageId) return;

    const userMessage: ChatMessage = {
      id: newId(),
      role: "user",
      content: trimmed,
      status: "complete",
      feedback: null,
      createdAt: Date.now(),
    };
    set((state) => ({ messages: [...state.messages, userMessage] }));

    let conversationId = get().conversationId;
    if (!conversationId) {
      const conversation = await conversationsApi.create();
      conversationId = conversation.id;
      set({ conversationId });
    }

    const history = [...get().messages].map(({ role, content }) => ({ role, content }));
    await runAssistantStream(set, get, conversationId, history);
  },

  loadConversation: async (conversationId: string) => {
    if (get().streamingMessageId) return;
    const conversation = await conversationsApi.get(conversationId);
    set({
      conversationId,
      messages: conversation.messages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        status: "complete",
        feedback: null,
        createdAt: new Date(message.created_at).getTime(),
      })),
    });
  },

  startNewChat: () => {
    const { abortController } = get();
    abortController?.abort();
    set({
      conversationId: null,
      messages: [],
      streamingMessageId: null,
      streamingBackendMessageId: null,
      abortController: null,
    });
  },

  regenerate: async (assistantMessageId: string) => {
    if (get().streamingMessageId) return;
    const { messages } = get();
    const index = messages.findIndex((m) => m.id === assistantMessageId);
    if (index === -1) return;

    // Drop the old assistant message and everything after it, then re-run
    // the stream from the conversation history up to that point.
    const history = messages.slice(0, index).map(({ role, content }) => ({ role, content }));
    set({ messages: messages.slice(0, index) });
    await runAssistantStream(set, get, get().conversationId, history);
  },

  editAndResend: async (userMessageId: string, newContent: string) => {
    if (get().streamingMessageId) return;
    const trimmed = newContent.trim();
    if (!trimmed) return;

    const { messages } = get();
    const index = messages.findIndex((m) => m.id === userMessageId);
    if (index === -1) return;

    // Replace the edited message and drop everything after it (the old
    // assistant reply no longer corresponds to the edited question).
    const editedMessage: ChatMessage = { ...messages[index], content: trimmed };
    const truncated = [...messages.slice(0, index), editedMessage];
    set({ messages: truncated });

    const history = truncated.map(({ role, content }) => ({ role, content }));
    await runAssistantStream(set, get, get().conversationId, history);
  },

  stopGeneration: () => {
    const { streamingBackendMessageId, abortController } = get();
    if (streamingBackendMessageId) {
      // Tell the backend to cancel the LLM call server-side, using ITS id
      // (from the "start" event) — not the frontend-local message id, which
      // the backend's cancel registry doesn't know about.
      void stopGenerationRequest(streamingBackendMessageId);
    }
    // ...and abort the client-side fetch immediately so the UI stops
    // waiting without needing to wait for a round trip.
    abortController?.abort();
  },

  setFeedback: (messageId: string, feedback: Feedback) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, feedback: m.feedback === feedback ? null : feedback } : m
      ),
    }));
  },
}));
