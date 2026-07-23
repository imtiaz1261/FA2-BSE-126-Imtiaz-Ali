const shell = document.getElementById("shell");
const sidebar = document.getElementById("sidebar");
const scrim = document.getElementById("scrim");
const menuBtn = document.getElementById("menuBtn");
const newChatBtn = document.getElementById("newChatBtn");
const conversationList = document.getElementById("conversationList");
const themeToggle = document.getElementById("themeToggle");
const statusPill = document.getElementById("statusPill");
const statusText = document.getElementById("statusText");
const chatForm = document.getElementById("chatForm");
const promptInput = document.getElementById("promptInput");
const sendBtn = document.getElementById("sendBtn");
const sendBtnText = document.getElementById("sendBtnText");
const sendBtnIcon = document.getElementById("sendBtnIcon");
const chatStage = document.getElementById("chatStageInner");
const messageList = document.getElementById("messageList");
const emptyState = document.getElementById("emptyState");
const statusDot = document.getElementById("statusDot");
const hljsDarkTheme = document.getElementById("hljs-dark-theme");
const hljsLightTheme = document.getElementById("hljs-light-theme");

const STORAGE_KEYS = {
  conversations: "llm-streaming-conversations",
  activeConversation: "llm-streaming-active-conversation",
  theme: "llm-streaming-theme",
};

const state = {
  conversations: [],
  activeConversationId: null,
  currentStream: null,
  autoScrollLocked: false,
  sidebarOpen: false,
};

function uuid(prefix = "chat") {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return `${prefix}-${window.crypto.randomUUID()}`;
  }
  return `${prefix}-${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`;
}

function nowLabel(value) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(value);
  } catch (error) {
    return "";
  }
}

function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    return fallback;
  }
}

function saveJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    // Ignore storage failures in private mode or quota exhaustion.
  }
}

function currentTheme() {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(STORAGE_KEYS.theme, theme);
  } catch (error) {
    // ignore
  }
  if (hljsDarkTheme && hljsLightTheme) {
    hljsDarkTheme.disabled = theme !== "dark";
    hljsLightTheme.disabled = theme !== "light";
  }
}

function getActiveConversation() {
  return state.conversations.find((conversation) => conversation.id === state.activeConversationId) || null;
}

function getConversationById(conversationId) {
  return state.conversations.find((conversation) => conversation.id === conversationId) || null;
}

function createConversation() {
  return {
    id: uuid("conv"),
    title: "New chat",
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [],
  };
}

function touchConversation(conversation) {
  conversation.updatedAt = Date.now();
  if (!conversation.title || conversation.title === "New chat") {
    const firstUserMessage = conversation.messages.find((message) => message.role === "user" && message.content.trim());
    if (firstUserMessage) {
      conversation.title = firstUserMessage.content.trim().replace(/\s+/g, " ").slice(0, 46);
    }
  }
}

function ensureConversation() {
  if (!state.conversations.length) {
    state.conversations = [createConversation()];
    state.activeConversationId = state.conversations[0].id;
  }
  if (!state.activeConversationId || !getActiveConversation()) {
    state.activeConversationId = state.conversations[0].id;
  }
}

function persistConversations() {
  saveJSON(STORAGE_KEYS.conversations, state.conversations);
  try {
    localStorage.setItem(STORAGE_KEYS.activeConversation, state.activeConversationId || "");
  } catch (error) {
    // ignore
  }
}

function setStatus(stateName, label) {
  statusPill.dataset.state = stateName;
  statusText.textContent = label;
  statusDot.className = "status-pill__dot";
}

function scrollChatToBottom(force = false) {
  if (force || !state.autoScrollLocked) {
    chatStage.scrollTop = chatStage.scrollHeight;
  }
}

function syncAutoScrollLock() {
  const threshold = 96;
  const remaining = chatStage.scrollHeight - (chatStage.scrollTop + chatStage.clientHeight);
  state.autoScrollLocked = remaining > threshold;
}

function formatTokenUsage(usage) {
  if (!usage) {
    return "";
  }
  const prompt = usage.prompt_tokens ?? "?";
  const completion = usage.completion_tokens ?? "?";
  const total = usage.total_tokens ?? "?";
  return `${prompt} prompt · ${completion} completion · ${total} total tokens`;
}

function buildMarkdown(htmlSource) {
  if (!window.marked) {
    return htmlSource
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br />");
  }
  return window.marked.parse(htmlSource || "");
}

function normalizeMarkdownRenderer() {
  if (!window.marked || normalizeMarkdownRenderer.initialized) {
    return;
  }
  window.marked.setOptions({
    breaks: true,
    gfm: true,
    mangle: false,
    headerIds: false,
  });
  normalizeMarkdownRenderer.initialized = true;
}

function decorateCodeBlocks(container) {
  const blocks = container.querySelectorAll("pre");
  blocks.forEach((pre) => {
    if (pre.parentElement && pre.parentElement.classList.contains("code-shell")) {
      return;
    }

    const code = pre.querySelector("code");
    const languageClass = code ? Array.from(code.classList).find((className) => className.startsWith("language-")) : null;
    const languageLabel = languageClass ? languageClass.replace("language-", "") : "code";
    const wrapper = document.createElement("div");
    wrapper.className = "code-shell";

    const bar = document.createElement("div");
    bar.className = "code-shell__bar";

    const lang = document.createElement("div");
    lang.className = "code-shell__lang";
    lang.textContent = languageLabel;

    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "copy-code-btn";
    copy.textContent = "Copy code";
    copy.addEventListener("click", async () => {
      const raw = code ? code.textContent || "" : pre.textContent || "";
      try {
        await navigator.clipboard.writeText(raw);
        const previous = copy.textContent;
        copy.textContent = "Copied";
        setTimeout(() => {
          copy.textContent = previous;
        }, 1300);
      } catch (error) {
        copy.textContent = "Copy failed";
        setTimeout(() => {
          copy.textContent = "Copy code";
        }, 1300);
      }
    });

    bar.append(lang, copy);
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.append(bar, pre);

    if (window.hljs && code) {
      try {
        window.hljs.highlightElement(code);
      } catch (error) {
        // Leave the code block readable if syntax highlighting fails.
      }
    }
  });
}

function renderMarkdownInto(container, text) {
  container.innerHTML = `<div class="markdown-body">${buildMarkdown(text)}</div>`;
  decorateCodeBlocks(container);
}

function createTypingIndicator() {
  const wrapper = document.createElement("div");
  wrapper.className = "assistant-stream-state";
  wrapper.innerHTML = `
    <span class="typing-dots" aria-hidden="true"><span></span><span></span><span></span></span>
    <span>Thinking…</span>
  `;
  return wrapper;
}

function createCursor() {
  const cursor = document.createElement("span");
  cursor.className = "stream-cursor";
  cursor.setAttribute("aria-hidden", "true");
  return cursor;
}

function createMessageNode(message) {
  const row = document.createElement("article");
  row.className = `message message--${message.role}`;
  row.dataset.messageId = message.id;

  const inner = document.createElement("div");
  inner.className = "message__inner";

  if (message.role === "user") {
    const bubble = document.createElement("div");
    bubble.className = "message__bubble";
    bubble.textContent = message.content;
    inner.appendChild(bubble);
  } else {
    const bubble = document.createElement("div");
    bubble.className = "message__bubble";

    const body = document.createElement("div");
    body.className = "assistant-message-body";
    if (message.content) {
      renderMarkdownInto(body, message.content);
    } else if (message.status === "streaming") {
      body.appendChild(createTypingIndicator());
    }

    bubble.appendChild(body);

    if (message.status === "streaming") {
      bubble.appendChild(createCursor());
    }

    const meta = document.createElement("div");
    meta.className = "message-meta";
    if (message.usage) {
      const pill = document.createElement("span");
      pill.className = "message-meta__pill";
      pill.title = formatTokenUsage(message.usage);
      pill.textContent = formatTokenUsage(message.usage);
      meta.appendChild(pill);
    }
    if (message.completedAt) {
      const stamp = document.createElement("span");
      stamp.className = "message-meta__pill";
      stamp.textContent = nowLabel(message.completedAt);
      meta.appendChild(stamp);
    }
    if (meta.childElementCount) {
      bubble.appendChild(meta);
    }

    if (message.notice) {
      const notice = document.createElement("div");
      notice.className = `message-notice message-notice--${message.notice.kind}`;
      notice.textContent = message.notice.text;
      bubble.appendChild(notice);
    }

    inner.appendChild(bubble);
  }

  row.appendChild(inner);
  return row;
}

function getConversationPreview(conversation) {
  const lastRelevantMessage = [...conversation.messages].reverse().find((message) => message.content && message.content.trim());
  if (!lastRelevantMessage) {
    return "Start a new conversation.";
  }
  return lastRelevantMessage.content.replace(/\s+/g, " ").slice(0, 80);
}

function renderConversationList() {
  conversationList.innerHTML = "";
  const conversations = [...state.conversations].sort((a, b) => b.updatedAt - a.updatedAt);

  conversations.forEach((conversation) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "conversation-item";
    item.dataset.conversationId = conversation.id;
    item.setAttribute("aria-current", conversation.id === state.activeConversationId ? "true" : "false");

    const title = document.createElement("div");
    title.className = "conversation-item__title";
    title.textContent = conversation.title || "New chat";

    const preview = document.createElement("div");
    preview.className = "conversation-item__preview";
    preview.textContent = getConversationPreview(conversation);

    const meta = document.createElement("div");
    meta.className = "conversation-item__meta";
    const countLabel = conversation.messages.length ? `${conversation.messages.length} messages` : "Empty";
    meta.textContent = `${countLabel} · ${nowLabel(conversation.updatedAt)}`;

    item.append(title, preview, meta);
    item.addEventListener("click", () => {
      selectConversation(conversation.id);
      closeSidebarOnMobile();
    });

    conversationList.appendChild(item);
  });
}

function renderMessages() {
  const conversation = getActiveConversation();
  messageList.innerHTML = "";

  if (!conversation || !conversation.messages.length) {
    emptyState.hidden = false;
    messageList.hidden = true;
  } else {
    emptyState.hidden = true;
    messageList.hidden = false;
    conversation.messages.forEach((message) => {
      messageList.appendChild(createMessageNode(message));
    });
  }

  messageList.setAttribute("aria-busy", state.currentStream ? "true" : "false");
  renderConversationList();
  scrollChatToBottom(true);
}

function selectConversation(conversationId) {
  state.activeConversationId = conversationId;
  persistConversations();
  renderMessages();
}

function startNewConversation() {
  if (state.currentStream) {
    cancelCurrentStream(true);
  }

  const conversation = createConversation();
  state.conversations.unshift(conversation);
  state.activeConversationId = conversation.id;
  persistConversations();
  renderMessages();
  promptInput.value = "";
  resizeTextarea();
  focusPrompt();
}

function closeSidebarOnMobile() {
  if (window.matchMedia("(max-width: 960px)").matches) {
    shell.classList.remove("sidebar-open");
    scrim.hidden = true;
    state.sidebarOpen = false;
  }
}

function openSidebar() {
  shell.classList.add("sidebar-open");
  scrim.hidden = false;
  state.sidebarOpen = true;
}

function toggleSidebar() {
  if (state.sidebarOpen) {
    closeSidebarOnMobile();
    return;
  }
  openSidebar();
}

function resizeTextarea() {
  promptInput.style.height = "auto";
  const nextHeight = Math.min(promptInput.scrollHeight, 156);
  promptInput.style.height = `${nextHeight}px`;
}

function focusPrompt() {
  window.requestAnimationFrame(() => {
    promptInput.focus({ preventScroll: true });
  });
}

function setSendButtonMode(mode) {
  sendBtn.dataset.mode = mode;
  if (mode === "stop") {
    sendBtnText.textContent = "Stop";
    sendBtnIcon.textContent = "■";
  } else {
    sendBtnText.textContent = "Send";
    sendBtnIcon.textContent = "↑";
  }
}

function buildRequestMessages(conversation, assistantMessageId) {
  return conversation.messages
    .filter((message) => message.id !== assistantMessageId)
    .map((message) => ({ role: message.role, content: message.content }));
}

function parseSseEventBlock(rawBlock) {
  const lines = rawBlock.split("\n");
  const event = { type: "message", data: [] };

  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }

    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    const value = separator === -1 ? "" : line.slice(separator + 1).replace(/^ /, "");

    if (field === "event") {
      event.type = value.trim() || event.type;
    } else if (field === "data") {
      event.data.push(value);
    }
  }

  const payload = event.data.join("\n").trim();
  let parsed = null;
  if (payload) {
    try {
      parsed = JSON.parse(payload);
    } catch (error) {
      parsed = { message: payload };
    }
  }

  return { type: event.type, data: parsed };
}

function finalizeStream(messageId, outcome, messageText) {
  const conversationId = state.currentStream ? state.currentStream.conversationId : state.activeConversationId;
  const conversation = getConversationById(conversationId);
  if (!conversation) {
    return;
  }

  const message = conversation.messages.find((entry) => entry.id === messageId);
  if (!message) {
    return;
  }

  if (outcome === "done") {
    message.status = "done";
    message.completedAt = Date.now();
    message.notice = null;
    if (messageText !== undefined) {
      message.content = messageText;
    }
  } else if (outcome === "cancelled") {
    message.status = "cancelled";
    message.notice = {
      kind: "muted",
      text: messageText || "Generation cancelled.",
    };
    message.completedAt = Date.now();
  } else if (outcome === "timeout") {
    message.status = "timeout";
    message.notice = {
      kind: "warning",
      text: messageText || "Generation timed out.",
    };
    message.completedAt = Date.now();
  } else if (outcome === "error") {
    message.status = "error";
    message.notice = {
      kind: "error",
      text: messageText || "Something went wrong while streaming the response.",
    };
    message.completedAt = Date.now();
  }

  touchConversation(conversation);
  persistConversations();
  state.currentStream = null;
  setSendButtonMode("send");
  promptInput.disabled = false;
  renderMessages();
  if (outcome === "done") {
    setStatus("done", "done");
  } else if (outcome === "cancelled") {
    setStatus("error", "cancelled");
  } else if (outcome === "timeout") {
    setStatus("error", "timed out");
  } else {
    setStatus("error", "error");
  }
  focusPrompt();
}

function updateAssistantStream(messageId, text, options = {}) {
  const conversationId = state.currentStream ? state.currentStream.conversationId : state.activeConversationId;
  const conversation = getConversationById(conversationId);
  if (!conversation) {
    return;
  }

  const message = conversation.messages.find((entry) => entry.id === messageId);
  if (!message) {
    return;
  }

  message.content = text;
  if (options.usage) {
    message.usage = options.usage;
  }
  if (options.started) {
    message.status = "streaming";
  }
  touchConversation(conversation);
  persistConversations();
  renderMessages();
}

async function cancelCurrentStream(fromNewChat = false) {
  if (!state.currentStream) {
    return;
  }

  const { requestId, assistantMessageId } = state.currentStream;
  setSendButtonMode("stop");
  setStatus("cancelling", fromNewChat ? "switching chats…" : "stopping…");

  try {
    await fetch(`/chat/cancel/${encodeURIComponent(requestId)}`, { method: "POST" });
  } catch (error) {
    // The stream will still terminate if the backend sees the disconnect.
  }

  finalizeStream(assistantMessageId, "cancelled", fromNewChat ? "Conversation interrupted while starting a new chat." : "Generation cancelled.");
}

async function streamChat(userText) {
  const conversation = getActiveConversation();
  if (!conversation || state.currentStream) {
    return;
  }

  const userMessage = {
    id: uuid("msg"),
    role: "user",
    content: userText,
    createdAt: Date.now(),
  };
  conversation.messages.push(userMessage);

  const requestId = uuid("req");
  const assistantMessage = {
    id: uuid("msg"),
    role: "assistant",
    content: "",
    createdAt: Date.now(),
    status: "streaming",
    requestId,
    usage: null,
    notice: null,
  };
  conversation.messages.push(assistantMessage);

  touchConversation(conversation);
  persistConversations();
  renderMessages();

  const requestPayload = {
    messages: buildRequestMessages(conversation, assistantMessage.id),
    request_id: requestId,
  };

  const controller = new AbortController();
  state.currentStream = {
    requestId,
    conversationId: conversation.id,
    assistantMessageId: assistantMessage.id,
    controller,
    startedAt: performance.now(),
    text: "",
    hasToken: false,
    done: false,
  };
  state.autoScrollLocked = false;
  setStatus("streaming", "connecting…");
  setSendButtonMode("stop");
  promptInput.disabled = true;

  try {
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload),
      signal: controller.signal,
    });

    const responseRequestId = response.headers.get("x-request-id");
    if (responseRequestId) {
      state.currentStream.requestId = responseRequestId;
    }

    if (!response.ok || !response.body) {
      let detail = `HTTP ${response.status}`;
      try {
        const payload = await response.json();
        detail = payload.detail || payload.message || detail;
      } catch (error) {
        // Non-JSON error response, keep HTTP status.
      }
      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const { type, data } = parseSseEventBlock(block);
        handleStreamEvent(type, data, assistantMessage.id);
        boundary = buffer.indexOf("\n\n");
      }
    }

    if (state.currentStream && state.currentStream.assistantMessageId === assistantMessage.id && !state.currentStream.done) {
      finalizeStream(assistantMessage.id, "error", "The server closed the stream before completion.");
    }
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }

    finalizeStream(assistantMessage.id, "error", error.message || "Unable to stream response.");
  }
}

function handleStreamEvent(type, data, assistantMessageId) {
  const stream = state.currentStream;
  if (!stream || stream.assistantMessageId !== assistantMessageId) {
    return;
  }

  switch (type) {
    case "start": {
      setStatus("streaming", data?.model ? `streaming · ${data.model}` : "streaming");
      updateAssistantStream(assistantMessageId, stream.text, { started: true });
      break;
    }
    case "token": {
      const chunk = data?.text || "";
      if (!stream.hasToken) {
        stream.hasToken = true;
      }
      stream.text += chunk;
      updateAssistantStream(assistantMessageId, stream.text, { started: true });
      break;
    }
    case "heartbeat":
      break;
    case "usage": {
      updateAssistantStream(assistantMessageId, stream.text, { usage: data });
      break;
    }
    case "done": {
      stream.done = true;
      state.currentStream = null;
      const elapsed = ((performance.now() - stream.startedAt) / 1000).toFixed(1);
      finalizeStream(assistantMessageId, "done", stream.text);
      setStatus("done", `done in ${elapsed}s`);
      break;
    }
    case "cancelled": {
      stream.done = true;
      state.currentStream = null;
      finalizeStream(assistantMessageId, "cancelled", data?.message || "Generation cancelled.");
      break;
    }
    case "timeout": {
      stream.done = true;
      state.currentStream = null;
      finalizeStream(assistantMessageId, "timeout", data?.message || "Generation timed out.");
      break;
    }
    case "error": {
      stream.done = true;
      state.currentStream = null;
      finalizeStream(assistantMessageId, "error", data?.message || "The backend reported an error.");
      break;
    }
    default:
      break;
  }
}

function handleSubmit(event) {
  event.preventDefault();

  if (state.currentStream) {
    cancelCurrentStream(false);
    return;
  }

  const text = promptInput.value.trim();
  if (!text) {
    return;
  }

  promptInput.value = "";
  resizeTextarea();
  streamChat(text);
}

function handleInput() {
  resizeTextarea();
}

function hydrateState() {
  const storedTheme = localStorage.getItem(STORAGE_KEYS.theme) || document.documentElement.dataset.theme || "dark";
  applyTheme(storedTheme === "light" ? "light" : "dark");

  state.conversations = loadJSON(STORAGE_KEYS.conversations, []);
  state.activeConversationId = localStorage.getItem(STORAGE_KEYS.activeConversation) || null;

  if (!Array.isArray(state.conversations)) {
    state.conversations = [];
  }

  state.conversations = state.conversations
    .filter((conversation) => conversation && Array.isArray(conversation.messages))
    .map((conversation) => ({
      ...createConversation(),
      ...conversation,
      title: conversation.title || "New chat",
    }));

  ensureConversation();
}

function bindEvents() {
  window.addEventListener("resize", () => {
    if (!window.matchMedia("(max-width: 960px)").matches) {
      closeSidebarOnMobile();
    }
  });

  chatStage.addEventListener("scroll", syncAutoScrollLock, { passive: true });
  chatForm.addEventListener("submit", handleSubmit);
  promptInput.addEventListener("input", handleInput);
  promptInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      chatForm.requestSubmit();
    }
  });

  newChatBtn.addEventListener("click", startNewConversation);
  menuBtn.addEventListener("click", toggleSidebar);
  scrim.addEventListener("click", closeSidebarOnMobile);

  themeToggle.addEventListener("click", () => {
    applyTheme(currentTheme() === "dark" ? "light" : "dark");
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (state.sidebarOpen) {
        closeSidebarOnMobile();
      } else if (state.currentStream) {
        cancelCurrentStream(false);
      }
    }
  });
}

function boot() {
  normalizeMarkdownRenderer();
  hydrateState();
  bindEvents();
  renderMessages();
  resizeTextarea();
  setSendButtonMode("send");
  setStatus("idle", "idle");
  scrollChatToBottom(true);
  focusPrompt();

  if (window.matchMedia("(max-width: 960px)").matches) {
    closeSidebarOnMobile();
  }
}

boot();
