import React, { useState } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

export interface ProposedChange {
  id: string;
  file: string;
  operation: "create" | "update" | "delete";
  diff: string;
  status: "staged" | "approved" | "rejected";
}

export interface DiffReviewPanelProps {
  changes: ProposedChange[];
  onApprove: (changeId: string) => void;
  onReject: (changeId: string, reason?: string) => void;
}

export const DiffReviewPanel: React.FC<DiffReviewPanelProps> = ({
  changes,
  onApprove,
  onReject,
}) => {
  const [selectedChangeId, setSelectedChangeId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectForm, setShowRejectForm] = useState<string | null>(null);

  const selectedChange = changes.find((c) => c.id === selectedChangeId);

  const handleRejectSubmit = (changeId: string) => {
    onReject(changeId, rejectReason);
    setShowRejectForm(null);
    setRejectReason("");
  };

  return (
    <div className="flex flex-col h-full bg-canvas dark:bg-canvas-dark">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-border dark:border-border-dark px-4 py-3 bg-canvas-panel dark:bg-canvas-dark-panel">
        <h3 className="text-heading-sm font-semibold text-ink dark:text-ink-dark">
          Proposed Changes ({changes.length})
        </h3>
      </div>

      <div className="flex flex-1 overflow-hidden gap-0">
        {/* Change list */}
        <div className="w-48 border-r border-border dark:border-border-dark overflow-y-auto flex-shrink-0">
          {changes.length === 0 ? (
            <div className="p-4 text-center text-ink-secondary dark:text-ink-secondary-dark text-meta">
              No changes proposed yet
            </div>
          ) : (
            <div className="divide-y divide-border dark:divide-border-dark">
              {changes.map((change) => (
                <button
                  key={change.id}
                  onClick={() => setSelectedChangeId(change.id)}
                  className={cn(
                    "w-full text-left px-3 py-2 text-meta hover:bg-canvas-panel dark:hover:bg-canvas-dark-panel transition-colors",
                    selectedChangeId === change.id
                      ? "bg-accent-600/10 border-l-2 border-accent-600"
                      : ""
                  )}
                >
                  <div className="flex items-start gap-2">
                    <span className="flex-shrink-0 mt-0.5">
                      {change.operation === "create" && "➕"}
                      {change.operation === "update" && "✏️"}
                      {change.operation === "delete" && "🗑️"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="truncate font-medium text-ink dark:text-ink-dark">
                        {change.file}
                      </div>
                      <div
                        className={cn(
                          "text-xs mt-1 inline-block px-1.5 py-0.5 rounded",
                          change.status === "approved"
                            ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300"
                            : change.status === "rejected"
                            ? "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300"
                            : "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300"
                        )}
                      >
                        {change.status}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Diff viewer */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {selectedChange ? (
            <>
              {/* File header */}
              <div className="flex-shrink-0 border-b border-border dark:border-border-dark px-4 py-3 bg-canvas-panel dark:bg-canvas-dark-panel flex items-center justify-between">
                <div>
                  <div className="text-heading-sm font-semibold text-ink dark:text-ink-dark">
                    {selectedChange.file}
                  </div>
                  <div className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
                    {selectedChange.operation === "create" && "New file"}
                    {selectedChange.operation === "update" && "Modified"}
                    {selectedChange.operation === "delete" && "Deleted"}
                  </div>
                </div>
              </div>

              {/* Diff content */}
              <div className="flex-1 overflow-auto p-4">
                <DiffViewer diff={selectedChange.diff} />
              </div>

              {/* Action buttons */}
              {selectedChange.status === "staged" && (
                <div className="flex-shrink-0 border-t border-border dark:border-border-dark px-4 py-3 flex gap-2">
                  <Button
                    onClick={() => onApprove(selectedChange.id)}
                    variant="primary"
                    size="sm"
                    className="flex-1"
                  >
                    ✓ Approve
                  </Button>
                  <Button
                    onClick={() => setShowRejectForm(selectedChange.id)}
                    variant="secondary"
                    size="sm"
                    className="flex-1"
                  >
                    ✗ Reject
                  </Button>
                </div>
              )}

              {/* Reject form */}
              {showRejectForm === selectedChange.id && (
                <div className="flex-shrink-0 border-t border-border dark:border-border-dark px-4 py-3 space-y-2 bg-canvas-panel dark:bg-canvas-dark-panel">
                  <input
                    type="text"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Reason for rejection (optional)"
                    className="w-full px-3 py-2 rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark placeholder-ink-secondary dark:placeholder-ink-secondary-dark focus:outline-none focus:border-accent-600 text-meta"
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={() =>
                        handleRejectSubmit(selectedChange.id)
                      }
                      variant="primary"
                      size="sm"
                      className="flex-1"
                    >
                      Submit Rejection
                    </Button>
                    <Button
                      onClick={() => {
                        setShowRejectForm(null);
                        setRejectReason("");
                      }}
                      variant="secondary"
                      size="sm"
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-center text-ink-secondary dark:text-ink-secondary-dark">
              <div>
                <p className="text-heading-sm font-semibold mb-2">
                  No change selected
                </p>
                <p className="text-meta">
                  Select a change from the list to review
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Unified diff viewer
interface DiffViewerProps {
  diff: string;
}

const DiffViewer: React.FC<DiffViewerProps> = ({ diff }) => {
  const lines = diff.split("\n");

  return (
    <div className="font-mono text-xs">
      {lines.map((line, idx) => {
        let bgClass = "";
        let textClass = "text-ink dark:text-ink-dark";

        if (line.startsWith("+++") || line.startsWith("---")) {
          bgClass = "bg-canvas-panel dark:bg-canvas-dark-panel";
          textClass = "text-ink-secondary dark:text-ink-secondary-dark";
        } else if (line.startsWith("+")) {
          bgClass = "bg-green-50 dark:bg-green-900/20";
          textClass = "text-green-700 dark:text-green-300";
        } else if (line.startsWith("-")) {
          bgClass = "bg-red-50 dark:bg-red-900/20";
          textClass = "text-red-700 dark:text-red-300";
        } else if (line.startsWith("@@")) {
          bgClass = "bg-blue-50 dark:bg-blue-900/20";
          textClass = "text-blue-700 dark:text-blue-300";
        }

        return (
          <div
            key={idx}
            className={cn("px-3 py-1 whitespace-pre-wrap break-all", bgClass, textClass)}
          >
            {line}
          </div>
        );
      })}
    </div>
  );
};
