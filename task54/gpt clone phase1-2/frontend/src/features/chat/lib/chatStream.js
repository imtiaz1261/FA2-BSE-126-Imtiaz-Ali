/**
 * `EventSource` can't send a POST body or an `Authorization` header, and
 * this endpoint needs both — so we parse the `text/event-stream` format
 * ourselves off a regular `fetch` response body reader. That also gives us
 * a real `AbortController` to wire up to the composer's Stop button.
 */
import { getAccessToken } from "@/lib/api";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
/**
 * Streams a chat completion. Resolves once the stream ends (naturally,
 * stopped, or aborted) — errors are reported via the "error" event rather
 * than a rejected promise, since a mid-stream failure still has partial
 * content the caller wants to keep.
 */
export async function streamChat({ conversationId, messages, onEvent, signal, }) {
    let res;
    try {
        res = await fetch(`${API_BASE_URL}/chat/stream`, {
            method: "POST",
            credentials: "include",
            signal,
            headers: {
                "Content-Type": "application/json",
                ...(getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {}),
            },
            body: JSON.stringify({ conversation_id: conversationId, messages }),
        });
    }
    catch (err) {
        if (err.name === "AbortError")
            return;
        onEvent({ type: "error", message: "Couldn't reach the server. Check your connection." });
        return;
    }
    if (!res.ok || !res.body) {
        onEvent({ type: "error", message: `Request failed (${res.status}).` });
        return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done)
                break;
            buffer += decoder.decode(value, { stream: true });
            // SSE frames are separated by a blank line; a frame may itself be
            // split across multiple reads, so we only consume complete frames
            // and keep the remainder in `buffer` for the next chunk.
            const frames = buffer.split("\n\n");
            buffer = frames.pop() ?? "";
            for (const frame of frames) {
                const line = frame.split("\n").find((l) => l.startsWith("data: "));
                if (!line)
                    continue;
                try {
                    const event = JSON.parse(line.slice("data: ".length));
                    onEvent(event);
                }
                catch {
                    // Ignore a malformed frame rather than killing the whole stream.
                }
            }
        }
    }
    catch (err) {
        if (err.name !== "AbortError") {
            onEvent({ type: "error", message: "The connection was interrupted." });
        }
    }
    finally {
        reader.releaseLock();
    }
}
/** Tells the backend to cancel a specific in-flight generation. */
export async function stopGeneration(messageId) {
    await fetch(`${API_BASE_URL}/chat/stream/${messageId}/stop`, {
        method: "POST",
        credentials: "include",
        headers: getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : {},
    });
}
