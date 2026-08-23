import React from "react";
import { cn } from "@/lib/cn";

export interface AgentReasoningPanelProps {
  events: Array<{ type: string; [key: string]: any }>;
  phase: string;
  isStreaming: boolean;
  error: string | null;
  ref?: React.RefObject<HTMLDivElement>;
}

const phaseLabels: Record<string, string> = {
  planning: "📋 Planning",
  reading_files: "📖 Reading Files",
  proposing_changes: "✏️ Proposing Changes",
  awaiting_approval: "⏸️ Awaiting Approval",
  executing: "⚙️ Executing",
  testing: "🧪 Testing",
  self_correcting: "🔄 Self-Correcting",
  complete: "✅ Complete",
  failed: "❌ Failed",
};

export const AgentReasoningPanel = React.forwardRef<
  HTMLDivElement,
  AgentReasoningPanelProps
>(({ events, phase, isStreaming, error }, ref) => {
  return (
    <div
      ref={ref}
      className="flex-1 overflow-y-auto flex flex-col gap-2 p-4 bg-canvas dark:bg-canvas-dark"
    >
      {/* Phase indicator */}
      <div className="sticky top-0 flex items-center gap-2 mb-2">
        <div className="flex items-center gap-2 px-3 py-2 rounded-control bg-canvas-panel dark:bg-canvas-dark-panel border border-border dark:border-border-dark">
          {isStreaming && (
            <div className="w-2 h-2 rounded-full bg-accent-600 animate-pulse" />
          )}
          <span className="text-meta font-medium text-ink dark:text-ink-dark">
            {phaseLabels[phase] || phase}
          </span>
        </div>
      </div>

      {/* Event log */}
      {events.length === 0 && !error && (
        <div className="text-center text-ink-secondary dark:text-ink-secondary-dark text-meta py-8">
          Awaiting agent input...
        </div>
      )}

      {events.map((event, idx) => (
        <EventItem key={idx} event={event} />
      ))}

      {/* Error display */}
      {error && (
        <div className="p-3 rounded-control bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
          <p className="text-meta font-semibold text-red-600 dark:text-red-400">
            Error
          </p>
          <p className="text-body text-red-600 dark:text-red-400 mt-1">
            {error}
          </p>
        </div>
      )}

      {/* Streaming indicator */}
      {isStreaming && events.length > 0 && (
        <div className="flex items-center gap-2 text-meta text-ink-secondary dark:text-ink-secondary-dark">
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-600 animate-bounce" />
            <div
              className="w-1.5 h-1.5 rounded-full bg-accent-600 animate-bounce"
              style={{ animationDelay: "0.2s" }}
            />
            <div
              className="w-1.5 h-1.5 rounded-full bg-accent-600 animate-bounce"
              style={{ animationDelay: "0.4s" }}
            />
          </div>
          <span>Agent thinking...</span>
        </div>
      )}
    </div>
  );
});

AgentReasoningPanel.displayName = "AgentReasoningPanel";

// Event item renderer
interface EventItemProps {
  event: { type: string; [key: string]: any };
}

const EventItem: React.FC<EventItemProps> = ({ event }) => {
  const getEventIcon = (type: string): string => {
    const icons: Record<string, string> = {
      phase_change: "🔄",
      reasoning: "💭",
      tool_call: "🔧",
      tool_result: "✓",
      change_proposed: "✏️",
      test_result: "🧪",
      complete: "✅",
      error: "❌",
      iteration: "🔁",
    };
    return icons[type] || "•";
  };

  const renderContent = (): React.ReactNode => {
    switch (event.type) {
      case "reasoning":
        return (
          <div className="space-y-1">
            <div className="text-meta font-semibold text-ink dark:text-ink-dark">
              {event.step === "thought" ? "Thought" : "Observation"}
            </div>
            <pre className="text-body text-ink-secondary dark:text-ink-secondary-dark whitespace-pre-wrap break-words font-mono text-xs bg-canvas-panel dark:bg-canvas-dark-panel p-2 rounded">
              {event.content}
            </pre>
          </div>
        );

      case "tool_call":
        return (
          <div className="space-y-1">
            <div className="text-meta font-semibold text-ink dark:text-ink-dark">
              Calling tool: <code className="font-mono">{event.tool}</code>
            </div>
            <pre className="text-body text-ink-secondary dark:text-ink-secondary-dark whitespace-pre-wrap break-words font-mono text-xs bg-canvas-panel dark:bg-canvas-dark-panel p-2 rounded">
              {JSON.stringify(event.input, null, 2)}
            </pre>
          </div>
        );

      case "tool_result":
        return (
          <div className="space-y-1">
            <div className={cn("text-meta font-semibold", 
              event.success ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
            )}>
              {event.success ? "✓" : "✗"} {event.tool}
            </div>
            {event.output && (
              <pre className="text-body text-ink-secondary dark:text-ink-secondary-dark whitespace-pre-wrap break-words font-mono text-xs bg-canvas-panel dark:bg-canvas-dark-panel p-2 rounded">
                {event.output.slice(0, 500)}
                {event.output.length > 500 ? "..." : ""}
              </pre>
            )}
            {event.error && (
              <pre className="text-body text-red-600 dark:text-red-400 whitespace-pre-wrap break-words font-mono text-xs bg-red-50 dark:bg-red-900/20 p-2 rounded">
                {event.error}
              </pre>
            )}
          </div>
        );

      case "test_result":
        return (
          <div className={cn(
            "p-2 rounded-control",
            event.passed
              ? "bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
              : "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
          )}>
            <div className={cn(
              "text-meta font-semibold mb-1",
              event.passed ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
            )}>
              {event.passed ? "✓ Tests Passed" : "✗ Tests Failed"}
            </div>
            <pre className="text-body text-ink-secondary dark:text-ink-secondary-dark font-mono text-xs whitespace-pre-wrap break-words">
              {event.output.slice(0, 300)}
              {event.output.length > 300 ? "..." : ""}
            </pre>
          </div>
        );

      case "change_proposed":
        return (
          <div className="p-2 rounded-control bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <div className="text-meta font-semibold text-blue-600 dark:text-blue-400">
              📄 {event.operation}: {event.file}
            </div>
          </div>
        );

      case "complete":
        return (
          <div className="p-2 rounded-control bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
            <div className="text-meta font-semibold text-green-600 dark:text-green-400">
              ✅ {event.summary}
            </div>
          </div>
        );

      case "error":
        return (
          <div className="p-2 rounded-control bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
            <div className="text-meta font-semibold text-red-600 dark:text-red-400">
              ❌ {event.message}
            </div>
          </div>
        );

      case "iteration":
        return (
          <div className="text-meta text-ink-secondary dark:text-ink-secondary-dark text-center py-2">
            — Iteration {event.iteration} —
          </div>
        );

      default:
        return (
          <div className="text-meta text-ink-secondary dark:text-ink-secondary-dark">
            {JSON.stringify(event, null, 2)}
          </div>
        );
    }
  };

  return (
    <div className="flex gap-2 p-2 rounded-control bg-canvas-panel dark:bg-canvas-dark-panel border border-border dark:border-border-dark">
      <span className="flex-shrink-0 text-lg">{getEventIcon(event.type)}</span>
      <div className="flex-1 min-w-0">{renderContent()}</div>
    </div>
  );
};
