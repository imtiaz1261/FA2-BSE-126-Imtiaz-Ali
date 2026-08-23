/**
 * File manager component for viewing and managing indexed documents.
 * 
 * Features:
 * - List all documents in a conversation
 * - Show file metadata (size, chunks, status)
 * - Delete documents
 * - Re-index failed documents
 * - Design token compliance (Module 1)
 */

import React, { useEffect, useState } from "react";
import {
  deleteDocument,
  formatFileSize,
  listDocuments,
  type DocumentMetadata,
} from "@/lib/documentsApi";

// ============================================================================
// Types
// ============================================================================

interface FileManagerProps {
  conversationId?: string;
  onDocumentDeleted?: (documentId: string) => void;
  onError?: (error: string) => void;
}

interface FileManagerState {
  documents: DocumentMetadata[];
  loading: boolean;
  error: string | null;
}

// ============================================================================
// Component
// ============================================================================

export function FileManager({
  conversationId,
  onDocumentDeleted,
  onError,
}: FileManagerProps): React.ReactElement {
  const [state, setState] = useState<FileManagerState>({
    documents: [],
    loading: false,
    error: null,
  });

  const [deleting, setDeleting] = useState<Set<string>>(new Set());

  // ============================================================================
  // Load Documents
  // ============================================================================

  const loadDocuments = async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await listDocuments(conversationId);
      setState((prev) => ({
        ...prev,
        documents: response.documents,
        loading: false,
      }));
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Failed to load documents";
      setState((prev) => ({
        ...prev,
        loading: false,
        error: errorMsg,
      }));
      onError?.(errorMsg);
    }
  };

  // Load documents on mount and when conversation changes
  useEffect(() => {
    if (conversationId) {
      loadDocuments();
    }
  }, [conversationId]);

  // ============================================================================
  // Delete Document
  // ============================================================================

  const handleDelete = async (documentId: string) => {
    if (!confirm("Delete this document and all its indexed chunks?")) {
      return;
    }

    setDeleting((prev) => new Set(prev).add(documentId));

    try {
      await deleteDocument(documentId);

      setState((prev) => ({
        ...prev,
        documents: prev.documents.filter((d) => d.id !== documentId),
      }));

      onDocumentDeleted?.(documentId);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Failed to delete document";
      onError?.(errorMsg);
    } finally {
      setDeleting((prev) => {
        const next = new Set(prev);
        next.delete(documentId);
        return next;
      });
    }
  };

  // ============================================================================
  // Render
  // ============================================================================

  if (!conversationId) {
    return (
      <div className="text-center py-4 text-meta text-ink/40 dark:text-ink-dark/40">
        No conversation selected
      </div>
    );
  }

  if (state.loading) {
    return (
      <div className="text-center py-4">
        <LoadingSpinner />
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="rounded-control bg-danger/10 dark:bg-danger/10 p-3 text-danger">
        <div className="text-meta font-medium">Error</div>
        <div className="text-body">{state.error}</div>
      </div>
    );
  }

  if (state.documents.length === 0) {
    return (
      <div className="text-center py-8">
        <EmptyIcon />
        <div className="text-body font-medium text-ink dark:text-ink-dark mt-2">
          No documents indexed
        </div>
        <div className="text-meta text-ink/60 dark:text-ink-dark/60">
          Upload documents to get started with RAG
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {state.documents.map((doc) => (
        <FileManagerItem
          key={doc.id}
          document={doc}
          isDeleting={deleting.has(doc.id)}
          onDelete={handleDelete}
        />
      ))}
    </div>
  );
}

// ============================================================================
// File Manager Item
// ============================================================================

interface FileManagerItemProps {
  document: DocumentMetadata;
  isDeleting: boolean;
  onDelete: (documentId: string) => void;
}

function FileManagerItem({
  document,
  isDeleting,
  onDelete,
}: FileManagerItemProps): React.ReactElement {
  const statusConfig = {
    pending: {
      label: "Pending",
      color: "bg-ink/5 dark:bg-ink-dark/5 text-ink/60 dark:text-ink-dark/60",
    },
    processing: {
      label: "Indexing",
      color: "bg-accent-600/10 dark:bg-accent-400/10 text-accent-600 dark:text-accent-400",
    },
    ready: {
      label: "Ready",
      color: "bg-success/10 text-success",
    },
    failed: {
      label: "Failed",
      color: "bg-danger/10 text-danger",
    },
  };

  const config = statusConfig[document.status];
  const isReady = document.status === "ready";

  return (
    <div
      className="rounded-control border border-border dark:border-border-dark
                 p-3 hover:bg-canvas-panel dark:hover:bg-canvas-dark-panel
                 transition-colors space-y-2"
    >
      {/* Header Row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Filename */}
          <div className="flex items-center gap-2 mb-1">
            <FileIcon fileType={document.file_type} />
            <div className="text-body font-medium text-ink dark:text-ink-dark truncate">
              {document.filename}
            </div>
          </div>

          {/* Metadata Row */}
          <div className="flex items-center gap-3 text-meta text-ink/60 dark:text-ink-dark/60">
            <span>{formatFileSize(document.file_size_bytes)}</span>
            <span>•</span>
            <span>
              {document.chunk_count} chunk{document.chunk_count !== 1 ? "s" : ""}
            </span>
            {document.error_message && (
              <>
                <span>•</span>
                <span className="text-danger">{document.error_message}</span>
              </>
            )}
          </div>
        </div>

        {/* Status Badge */}
        <div
          className={`
            px-2 py-1 rounded text-meta font-medium whitespace-nowrap
            ${config.color}
          `}
        >
          {config.label}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2 pt-2 border-t border-border dark:border-border-dark">
        <button
          onClick={() => onDelete(document.id)}
          disabled={isDeleting}
          className={`
            px-2 py-1 text-meta font-medium rounded-control
            transition-colors
            ${
              isDeleting
                ? "opacity-50 cursor-not-allowed"
                : "text-danger hover:bg-danger/10 dark:hover:bg-danger/10"
            }
          `}
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </button>

        {isReady && (
          <a
            href={`#documents/${document.id}`}
            className="ml-auto px-2 py-1 text-meta font-medium rounded-control
                       text-accent-600 dark:text-accent-400
                       hover:bg-accent-600/10 dark:hover:bg-accent-400/10
                       transition-colors"
          >
            View
          </a>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Icons
// ============================================================================

interface FileIconProps {
  fileType: string;
}

function FileIcon({ fileType }: FileIconProps): React.ReactElement {
  const iconMap: Record<string, string> = {
    pdf: "🔴",
    docx: "🔵",
    txt: "⚪",
    csv: "🟢",
  };

  const icon = iconMap[fileType] || "📄";

  return <span className="text-lg">{icon}</span>;
}

function LoadingSpinner(): React.ReactElement {
  return (
    <div className="inline-block">
      <div
        className="inline-block h-4 w-4 animate-spin rounded-full
                   border-2 border-ink/20 dark:border-ink-dark/20
                   border-t-accent-600 dark:border-t-accent-400"
      />
    </div>
  );
}

function EmptyIcon(): React.ReactElement {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="mx-auto text-ink/20 dark:text-ink-dark/20"
    >
      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
      <polyline points="13 2 13 9 20 9" />
      <line x1="12" y1="12" x2="12" y2="18" />
      <line x1="9" y1="15" x2="15" y2="15" />
    </svg>
  );
}
