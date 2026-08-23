/**
 * Data Controls Settings Tab
 * Export data, clear conversations, delete account
 */

import React, { useState } from "react";
import { cn } from "@/lib/cn";
import { settingsApi } from "@/lib/settingsApi";
import { useSettingsStore } from "@/store/settingsStore";

interface DataControlsTabProps {
  onClose?: () => void;
}

type ConfirmationStep = null | "clear-confirm" | "delete-confirm";

export function DataControlsTab({ onClose }: DataControlsTabProps) {
  const { initiateDataExport } = useSettingsStore();

  const [exportLoading, setExportLoading] = useState(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);

  const [confirmationStep, setConfirmationStep] = useState<ConfirmationStep>(null);
  const [clearConfirmText, setClearConfirmText] = useState("");
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deletePassword, setDeletePassword] = useState("");

  const [isProcessing, setIsProcessing] = useState(false);

  // Export data
  const handleExportData = async () => {
    setExportLoading(true);
    setExportMessage(null);

    try {
      const jobId = await initiateDataExport();
      setExportMessage(
        "✓ Export initiated! You'll receive an email with a download link shortly."
      );
    } catch (err) {
      setExportMessage(
        `✗ Export failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setExportLoading(false);
    }
  };

  // Clear all conversations
  const handleClearConversations = async () => {
    if (clearConfirmText !== "I understand") {
      return;
    }

    setIsProcessing(true);
    try {
      await settingsApi.clearAllConversations(clearConfirmText);
      setConfirmationStep(null);
      setClearConfirmText("");
      setExportMessage("✓ All conversations cleared.");
    } catch (err) {
      setExportMessage(
        `✗ Failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setIsProcessing(false);
    }
  };

  // Delete account
  const handleDeleteAccount = async () => {
    if (
      deleteConfirmText !== "I understand" &&
      deleteConfirmText !== ""
    ) {
      return;
    }

    setIsProcessing(true);
    try {
      await settingsApi.deleteAccount(deleteConfirmText || "I understand", deletePassword || undefined);
      // Redirect to login or home
      window.location.href = "/";
    } catch (err) {
      setExportMessage(
        `✗ Failed: ${err instanceof Error ? err.message : "Unknown error"}`
      );
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6 pb-6">
      {/* Message */}
      {exportMessage && (
        <div
          className={cn(
            "p-3 rounded-control border text-meta",
            exportMessage.startsWith("✓")
              ? "border-green-600/50 bg-green-600/10 text-green-700 dark:text-green-400"
              : "border-red-600/50 bg-red-600/10 text-red-700 dark:text-red-400"
          )}
        >
          {exportMessage}
        </div>
      )}

      {/* Export Data */}
      <div className="space-y-3">
        <h3 className="font-medium text-body text-ink dark:text-ink-dark">Export your data</h3>
        <p className="text-meta text-ink/60 dark:text-ink-dark/60">
          Download a JSON file of all your conversations, messages, and settings. A download link will be emailed to you.
        </p>
        <button
          onClick={handleExportData}
          disabled={exportLoading}
          className={cn(
            "px-4 py-2 rounded-control text-meta font-medium transition-colors",
            "border border-border dark:border-border-dark",
            "hover:bg-canvas-panel dark:hover:bg-canvas-dark-alt",
            "disabled:opacity-50"
          )}
        >
          {exportLoading ? "Exporting..." : "Export Data"}
        </button>
      </div>

      <div className="border-t border-border dark:border-border-dark" />

      {/* Clear All Conversations */}
      <div className="space-y-3">
        <h3 className="font-medium text-body text-ink dark:text-ink-dark">Clear all conversations</h3>
        <p className="text-meta text-ink/60 dark:text-ink-dark/60">
          Permanently delete all conversations and messages. This action cannot be undone.
        </p>

        {confirmationStep !== "clear-confirm" ? (
          <button
            onClick={() => setConfirmationStep("clear-confirm")}
            className={cn(
              "px-4 py-2 rounded-control text-meta font-medium transition-colors",
              "border border-danger/50 text-danger hover:bg-danger/10",
              "dark:border-red-500/50 dark:text-red-400 dark:hover:bg-red-500/10"
            )}
          >
            Clear All Conversations
          </button>
        ) : (
          <div className="space-y-2 p-3 rounded-control bg-danger/10 dark:bg-red-500/10 border border-danger/50 dark:border-red-500/50">
            <p className="text-meta text-danger dark:text-red-400">
              Type "I understand" to confirm:
            </p>
            <input
              type="text"
              value={clearConfirmText}
              onChange={(e) => setClearConfirmText(e.target.value)}
              placeholder='Type "I understand"'
              disabled={isProcessing}
              className={cn(
                "w-full px-3 py-2 rounded-control border text-body font-mono text-sm",
                "bg-canvas dark:bg-canvas-dark",
                "border-border dark:border-border-dark",
                "text-ink dark:text-ink-dark",
                "focus:outline-none focus:ring-2 focus:ring-danger",
                "disabled:opacity-50"
              )}
            />
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setConfirmationStep(null);
                  setClearConfirmText("");
                }}
                disabled={isProcessing}
                className={cn(
                  "flex-1 px-3 py-2 rounded-control text-meta font-medium transition-colors",
                  "border border-border dark:border-border-dark",
                  "hover:bg-canvas-panel dark:hover:bg-canvas-dark-alt",
                  "disabled:opacity-50"
                )}
              >
                Cancel
              </button>
              <button
                onClick={handleClearConversations}
                disabled={clearConfirmText !== "I understand" || isProcessing}
                className={cn(
                  "flex-1 px-3 py-2 rounded-control text-meta font-medium transition-colors",
                  "bg-danger text-white hover:bg-danger-dark",
                  "dark:bg-red-600 dark:hover:bg-red-700",
                  "disabled:opacity-50"
                )}
              >
                {isProcessing ? "Clearing..." : "Permanently Clear"}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-border dark:border-border-dark" />

      {/* Delete Account */}
      <div className="space-y-3">
        <h3 className="font-medium text-body text-ink dark:text-ink-dark">Delete account</h3>
        <p className="text-meta text-ink/60 dark:text-ink-dark/60">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>

        {confirmationStep !== "delete-confirm" ? (
          <button
            onClick={() => setConfirmationStep("delete-confirm")}
            className={cn(
              "px-4 py-2 rounded-control text-meta font-medium transition-colors",
              "border border-danger/50 text-danger hover:bg-danger/10",
              "dark:border-red-500/50 dark:text-red-400 dark:hover:bg-red-500/10"
            )}
          >
            Delete Account
          </button>
        ) : (
          <div className="space-y-2 p-3 rounded-control bg-danger/10 dark:bg-red-500/10 border border-danger/50 dark:border-red-500/50">
            <p className="text-meta text-danger dark:text-red-400 font-medium">
              This will permanently delete your account and all your data.
            </p>
            <p className="text-meta text-danger/80 dark:text-red-400/80">
              Type your email address to confirm:
            </p>
            <input
              type="email"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder="your@email.com"
              disabled={isProcessing}
              className={cn(
                "w-full px-3 py-2 rounded-control border text-body font-mono text-sm",
                "bg-canvas dark:bg-canvas-dark",
                "border-border dark:border-border-dark",
                "text-ink dark:text-ink-dark",
                "focus:outline-none focus:ring-2 focus:ring-danger",
                "disabled:opacity-50"
              )}
            />
            <p className="text-meta text-danger/80 dark:text-red-400/80 mt-2">
              Enter your password for additional verification:
            </p>
            <input
              type="password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              placeholder="Password"
              disabled={isProcessing}
              className={cn(
                "w-full px-3 py-2 rounded-control border text-body font-mono text-sm",
                "bg-canvas dark:bg-canvas-dark",
                "border-border dark:border-border-dark",
                "text-ink dark:text-ink-dark",
                "focus:outline-none focus:ring-2 focus:ring-danger",
                "disabled:opacity-50"
              )}
            />
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setConfirmationStep(null);
                  setDeleteConfirmText("");
                  setDeletePassword("");
                }}
                disabled={isProcessing}
                className={cn(
                  "flex-1 px-3 py-2 rounded-control text-meta font-medium transition-colors",
                  "border border-border dark:border-border-dark",
                  "hover:bg-canvas-panel dark:hover:bg-canvas-dark-alt",
                  "disabled:opacity-50"
                )}
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={!deleteConfirmText || !deletePassword || isProcessing}
                className={cn(
                  "flex-1 px-3 py-2 rounded-control text-meta font-medium transition-colors",
                  "bg-danger text-white hover:bg-danger-dark",
                  "dark:bg-red-600 dark:hover:bg-red-700",
                  "disabled:opacity-50"
                )}
              >
                {isProcessing ? "Deleting..." : "Delete Account"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
