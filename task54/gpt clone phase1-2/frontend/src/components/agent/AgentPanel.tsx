import React, { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { AgentReasoningPanel } from "./AgentReasoningPanel";
import { DiffReviewPanel } from "./DiffReviewPanel";

export interface ProposedChange {
  id: string;
  file: string;
  operation: "create" | "update" | "delete";
  diff: string;
  status: "staged" | "approved" | "rejected";
}

export interface AgentEvent {
  type: string;
  [key: string]: any;
}

export interface AgentPanelProps {
  conversationId: string;
  onClose?: () => void;
}

export const AgentPanel: React.FC<AgentPanelProps> = ({ conversationId, onClose }) => {
  const [isOpen, setIsOpen] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [phase, setPhase] = useState("planning");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [changes, setChanges] = useState<ProposedChange[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [task, setTask] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [error, setError] = useState<string | null>(null);
  const eventLogRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest event
  useEffect(() => {
    if (eventLogRef.current) {
      eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight;
    }
  }, [events]);

  const startAgent = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!task.trim() || !repoPath.trim()) {
      setError("Please fill in both task and repo path");
      return;
    }

    setIsStreaming(true);
    setError(null);
    setEvents([]);
    setChanges([]);

    try {
      const params = new URLSearchParams({
        task,
        repo_path: repoPath,
        conversation_id: conversationId,
      });

      const response = await fetch(`/api/agent/chat/agent?${params}`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(`Agent error: ${response.statusText}`);
      }

      // Read streaming response
      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event = JSON.parse(line.slice(6));
              setEvents((prev) => [...prev, event]);

              if (event.type === "phase_change") {
                setPhase(event.phase);
              } else if (event.type === "change_proposed") {
                setChanges((prev) => [
                  ...prev,
                  {
                    id: Math.random().toString(),
                    file: event.file,
                    operation: event.operation,
                    diff: event.diff,
                    status: "staged",
                  },
                ]);
              }
            } catch (e) {
              console.error("Failed to parse event", e);
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsStreaming(false);
    }
  };

  const handleApproveChange = async (changeId: string) => {
    try {
      const response = await fetch(`/api/agent/changes/${changeId}/approve`, {
        method: "POST",
      });

      if (!response.ok) throw new Error("Failed to approve change");

      setChanges((prev) =>
        prev.map((c) =>
          c.id === changeId ? { ...c, status: "approved" } : c
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve");
    }
  };

  const handleRejectChange = async (changeId: string, reason?: string) => {
    try {
      const params = new URLSearchParams({ reason: reason || "" });
      const response = await fetch(
        `/api/agent/changes/${changeId}/reject?${params}`,
        { method: "POST" }
      );

      if (!response.ok) throw new Error("Failed to reject change");

      setChanges((prev) =>
        prev.map((c) =>
          c.id === changeId ? { ...c, status: "rejected" } : c
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject");
    }
  };

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        variant="secondary"
        className="fixed bottom-4 right-4"
      >
        Show Agent
      </Button>
    );
  }

  return (
    <div className="flex h-screen flex-col gap-0 bg-canvas dark:bg-canvas-dark">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border dark:border-border-dark bg-canvas-panel dark:bg-canvas-dark-panel px-4 py-3">
        <h2 className="text-heading-sm font-semibold text-ink dark:text-ink-dark">
          Coding Agent
        </h2>
        <div className="flex gap-2">
          <Button
            onClick={() => setIsOpen(false)}
            variant="ghost"
            size="sm"
          >
            ✕
          </Button>
        </div>
      </div>

      {/* Main content split view */}
      <div className="flex flex-1 overflow-hidden gap-0">
        {/* Left: Reasoning + Input */}
        <div className="flex flex-1 flex-col min-w-0 border-r border-border dark:border-border-dark">
          {/* Input form */}
          <div className="flex-shrink-0 border-b border-border dark:border-border-dark p-4">
            <form onSubmit={startAgent} className="space-y-3">
              <div>
                <label className="block text-meta text-ink-secondary dark:text-ink-secondary-dark mb-1">
                  Task Description
                </label>
                <input
                  type="text"
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  placeholder="e.g., Add error handling to auth endpoints"
                  disabled={isStreaming}
                  className="w-full px-3 py-2 rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark placeholder-ink-secondary dark:placeholder-ink-secondary-dark focus:outline-none focus:border-accent-600"
                />
              </div>
              <div>
                <label className="block text-meta text-ink-secondary dark:text-ink-secondary-dark mb-1">
                  Repository Path
                </label>
                <input
                  type="text"
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  placeholder="e.g., /home/user/my-project"
                  disabled={isStreaming}
                  className="w-full px-3 py-2 rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark placeholder-ink-secondary dark:placeholder-ink-secondary-dark focus:outline-none focus:border-accent-600"
                />
              </div>
              <Button
                type="submit"
                disabled={isStreaming || !task.trim() || !repoPath.trim()}
                loading={isStreaming}
                className="w-full"
              >
                {isStreaming ? "Running..." : "Start Agent"}
              </Button>
            </form>
          </div>

          {/* Reasoning panel */}
          <AgentReasoningPanel
            events={events}
            phase={phase}
            isStreaming={isStreaming}
            error={error}
            ref={eventLogRef}
          />
        </div>

        {/* Right: Diff reviewer */}
        <div className="flex-1 min-w-0 overflow-hidden flex flex-col">
          <DiffReviewPanel
            changes={changes}
            onApprove={handleApproveChange}
            onReject={handleRejectChange}
          />
        </div>
      </div>
    </div>
  );
};
