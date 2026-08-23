import React, { useState } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

export interface MemoryItemProps {
  id: string;
  fact: string;
  category: string;
  relevance_score: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  source_conversation_id?: string;
}

interface MemoryItemCardProps {
  item: MemoryItemProps;
  categoryLabel?: string;
  onEdit?: (id: string, newFact: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
  onToggleActive?: (id: string, isActive: boolean) => Promise<void>;
}

const CATEGORY_ICONS: Record<string, string> = {
  personal_info: "👤",
  preferences: "⚙️",
  goals_and_values: "🎯",
  skills_and_expertise: "💡",
  constraints: "⏱️",
  recurring_tasks: "🔄",
  project_context: "📁",
  other: "📝",
};

export const MemoryItemCard: React.FC<MemoryItemCardProps> = ({
  item,
  categoryLabel,
  onEdit,
  onDelete,
  onToggleActive,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedFact, setEditedFact] = useState(item.fact);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  const handleSaveEdit = async () => {
    if (!editedFact.trim()) return;
    if (editedFact === item.fact) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    try {
      if (onEdit) {
        await onEdit(item.id, editedFact);
      }
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to save edit:", error);
      setEditedFact(item.fact);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (
      !window.confirm(
        "Are you sure you want to delete this memory? This action cannot be undone."
      )
    ) {
      return;
    }

    setIsDeleting(true);
    try {
      if (onDelete) {
        await onDelete(item.id);
      }
    } catch (error) {
      console.error("Failed to delete:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleToggleActive = async () => {
    try {
      if (onToggleActive) {
        await onToggleActive(item.id, !item.is_active);
      }
    } catch (error) {
      console.error("Failed to toggle active state:", error);
    }
  };

  const icon = CATEGORY_ICONS[item.category] || "📝";

  return (
    <Card
      className={cn(
        "p-4 space-y-3 transition-all",
        !item.is_active && "opacity-60"
      )}
    >
      {isEditing ? (
        // Edit mode
        <div className="space-y-3">
          <textarea
            value={editedFact}
            onChange={(e) => setEditedFact(e.target.value)}
            className={cn(
              "w-full px-3 py-2 rounded-control border",
              "bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark",
              "border-border dark:border-border-dark",
              "focus:outline-none focus:ring-2 focus:ring-accent-600",
              "font-sans text-body resize-none"
            )}
            rows={3}
            autoFocus
          />

          <div className="flex gap-2">
            <Button
              onClick={handleSaveEdit}
              loading={isSaving}
              disabled={!editedFact.trim() || editedFact === item.fact}
              size="sm"
              variant="primary"
            >
              Save
            </Button>
            <Button
              onClick={() => {
                setIsEditing(false);
                setEditedFact(item.fact);
              }}
              size="sm"
              variant="secondary"
              disabled={isSaving}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        // View mode
        <>
          {/* Memory fact content */}
          <div>
            <p className="text-body text-ink dark:text-ink-dark leading-relaxed">
              {item.fact}
            </p>
          </div>

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border dark:border-border-dark">
            {/* Category badge */}
            <span className="px-2.5 py-1 rounded-control text-xs font-medium bg-accent-600/10 text-accent-600 dark:text-accent-400 flex items-center gap-1">
              <span>{icon}</span>
              {categoryLabel || item.category}
            </span>

            {/* Relevance score */}
            <span className="px-2.5 py-1 rounded-control text-xs font-medium bg-canvas-panel dark:bg-canvas-dark-panel text-ink-secondary dark:text-ink-secondary-dark">
              Score: {(item.relevance_score * 100).toFixed(0)}%
            </span>

            {/* Created date */}
            <span className="px-2.5 py-1 rounded-control text-xs text-ink-secondary dark:text-ink-secondary-dark">
              {formatDate(item.created_at)}
            </span>

            {/* Status badge */}
            {!item.is_active && (
              <span className="px-2.5 py-1 rounded-control text-xs font-medium bg-yellow-600/10 text-yellow-600 dark:text-yellow-400">
                Inactive
              </span>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-between pt-1">
            {/* Active toggle */}
            <button
              onClick={handleToggleActive}
              className={cn(
                "px-2.5 py-1 rounded-control text-xs font-medium transition-colors",
                item.is_active
                  ? "bg-green-600/10 text-green-600 dark:text-green-400 hover:bg-green-600/20"
                  : "bg-gray-600/10 text-gray-600 dark:text-gray-400 hover:bg-gray-600/20"
              )}
            >
              {item.is_active ? "✓ Active" : "○ Inactive"}
            </button>

            {/* Edit and Delete buttons */}
            <div className="flex gap-1">
              <button
                onClick={() => {
                  setIsEditing(true);
                  setEditedFact(item.fact);
                }}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-control text-xs font-medium text-accent-600 hover:bg-accent-600/10 dark:text-accent-400 dark:hover:bg-accent-600/20 transition-colors"
              >
                ✏️ Edit
              </button>
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-control text-xs font-medium text-red-600 hover:bg-red-600/10 dark:text-red-400 dark:hover:bg-red-600/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                🗑️ Delete
              </button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
};
