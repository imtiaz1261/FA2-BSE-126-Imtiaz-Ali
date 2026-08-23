/**
 * Drag-and-drop document upload component.
 * 
 * Features:
 * - Drag-and-drop zone with visual feedback
 * - Per-file progress bars
 * - Live indexing status polling
 * - Error handling and retry
 * - Design token compliance (Module 1)
 */

import React, { useRef, useState } from "react";
import {
  deleteDocument,
  formatFileSize,
  listDocuments,
  pollUploadStatus,
  uploadDocument,
  validateFile,
  type DocumentMetadata,
  type UploadStatusResponse,
} from "@/lib/documentsApi";

// ============================================================================
// Types
// ============================================================================

interface UploadingFile {
  file: File;
  jobId: string;
  documentId: string | null;
  progress: number;
  status: "uploading" | "processing" | "ready" | "failed";
  error: string | null;
  chunks: number;
}

interface DocumentUploadProps {
  conversationId?: string;
  onUploadComplete?: (doc: DocumentMetadata) => void;
  onError?: (error: string) => void;
}

// ============================================================================
// Component
// ============================================================================

export function DocumentUpload({
  conversationId,
  onUploadComplete,
  onError,
}: DocumentUploadProps): React.ReactElement {
  const [uploading, setUploading] = useState<UploadingFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ============================================================================
  // Upload Handlers
  // ============================================================================

  const handleFileUpload = async (files: File[]) => {
    for (const file of files) {
      // Validate file
      const validation = validateFile(file);
      if (!validation.valid) {
        onError?.(validation.error || "Invalid file");
        continue;
      }

      // Initialize uploading state
      const fileState: UploadingFile = {
        file,
        jobId: "",
        documentId: null,
        progress: 0,
        status: "uploading",
        error: null,
        chunks: 0,
      };

      setUploading((prev) => [...prev, fileState]);

      try {
        // Upload file with progress tracking
        const response = await uploadDocument(
          file,
          conversationId,
          (progress) => {
            setUploading((prev) =>
              prev.map((f) =>
                f.file === file
                  ? { ...f, progress: Math.round(progress.percentage) }
                  : f
              )
            );
          }
        );

        // Update state with job info
        setUploading((prev) =>
          prev.map((f) =>
            f.file === file
              ? {
                  ...f,
                  jobId: response.job_id,
                  documentId: response.document_id,
                  status: "processing",
                  progress: 100,
                }
              : f
          )
        );

        // Poll for indexing status
        await pollUploadStatus(response.job_id, 300, 500, (status) => {
          setUploading((prev) =>
            prev.map((f) =>
              f.file === file
                ? {
                    ...f,
                    status: status.status as any,
                    progress: status.progress,
                    chunks: status.chunk_count,
                    error: status.error_message,
                  }
                : f
            )
          );

          // Notify when complete
          if (status.status === "ready") {
            onUploadComplete?.({
              id: response.document_id || "",
              filename: file.name,
              file_type: (file.name.split(".").pop()?.toLowerCase() || "txt") as any,
              file_size_bytes: file.size,
              status: "ready",
              chunk_count: status.chunk_count,
              error_message: null,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            });
          }
        });
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : "Upload failed";

        setUploading((prev) =>
          prev.map((f) =>
            f.file === file
              ? {
                  ...f,
                  status: "failed",
                  error: errorMsg,
                }
              : f
          )
        );

        onError?.(errorMsg);
      }
    }
  };

  // ============================================================================
  // Drag-and-Drop Handlers
  // ============================================================================

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    handleFileUpload(files);
    // Reset input so same file can be uploaded again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleRetry = (file: UploadingFile) => {
    setUploading((prev) =>
      prev.filter(
        (f) => !(f.file === file.file && f.status === "failed")
      )
    );
    handleFileUpload([file.file]);
  };

  const handleRemove = (file: UploadingFile) => {
    setUploading((prev) => prev.filter((f) => f.file !== file.file));
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative rounded-control border-2 border-dashed p-8 text-center
          transition-all duration-200
          ${
            isDragging
              ? "border-accent-600 dark:border-accent-400 bg-accent-600/5 dark:bg-accent-400/5"
              : "border-border dark:border-border-dark hover:border-accent-600/50 dark:hover:border-accent-400/50"
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.csv"
          onChange={handleInputChange}
          className="hidden"
          aria-label="Upload documents"
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          className="cursor-pointer"
        >
          <div className="space-y-2">
            <UploadIcon />
            <div className="text-body font-medium text-ink dark:text-ink-dark">
              Drop files here or click to browse
            </div>
            <div className="text-meta text-ink/60 dark:text-ink-dark/60">
              PDF, DOCX, TXT, CSV up to 20MB
            </div>
          </div>
        </button>
      </div>

      {/* Uploading Files List */}
      {uploading.length > 0 && (
        <div className="space-y-3">
          {uploading.map((file) => (
            <UploadingFileItem
              key={file.file.name}
              file={file}
              onRetry={handleRetry}
              onRemove={handleRemove}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {uploading.length === 0 && (
        <div className="text-center py-4 text-meta text-ink/40 dark:text-ink-dark/40">
          No files uploaded yet
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Uploading File Item
// ============================================================================

interface UploadingFileItemProps {
  file: UploadingFile;
  onRetry: (file: UploadingFile) => void;
  onRemove: (file: UploadingFile) => void;
}

function UploadingFileItem({
  file,
  onRetry,
  onRemove,
}: UploadingFileItemProps): React.ReactElement {
  const statusConfig = {
    uploading: {
      label: "Uploading",
      color: "bg-accent-600/10 dark:bg-accent-400/10",
      textColor: "text-accent-600 dark:text-accent-400",
    },
    processing: {
      label: "Indexing",
      color: "bg-accent-600/10 dark:bg-accent-400/10",
      textColor: "text-accent-600 dark:text-accent-400",
    },
    ready: {
      label: "Ready",
      color: "bg-success/10 dark:bg-success/10",
      textColor: "text-success",
    },
    failed: {
      label: "Failed",
      color: "bg-danger/10 dark:bg-danger/10",
      textColor: "text-danger",
    },
  };

  const config = statusConfig[file.status];
  const isComplete = file.status === "ready" || file.status === "failed";

  return (
    <div className="rounded-control border border-border dark:border-border-dark p-3 space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="text-body font-medium text-ink dark:text-ink-dark truncate">
            {file.file.name}
          </div>
          <div className="text-meta text-ink/60 dark:text-ink-dark/60">
            {formatFileSize(file.file.size)}
          </div>
        </div>

        <div className={`px-2 py-1 rounded text-meta font-medium ${config.color} ${config.textColor}`}>
          {config.label}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-canvas-panel dark:bg-canvas-dark-panel rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            file.status === "failed"
              ? "bg-danger"
              : "bg-accent-600 dark:bg-accent-400"
          }`}
          style={{ width: `${file.progress}%` }}
        />
      </div>

      {/* Status Details */}
      <div className="flex items-center justify-between gap-3">
        <div className="text-meta text-ink/60 dark:text-ink-dark/60">
          {file.status === "ready" && `${file.chunks} chunks indexed`}
          {file.status === "processing" && `Processing (${file.progress}%)`}
          {file.status === "uploading" && `Uploading (${file.progress}%)`}
          {file.status === "failed" && file.error}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {file.status === "failed" && (
            <button
              onClick={() => onRetry(file)}
              className="px-2 py-1 text-meta font-medium rounded-control
                         text-accent-600 dark:text-accent-400
                         hover:bg-accent-600/10 dark:hover:bg-accent-400/10
                         transition-colors"
            >
              Retry
            </button>
          )}

          {!isComplete && (
            <button
              onClick={() => onRemove(file)}
              className="px-2 py-1 text-meta font-medium rounded-control
                         text-ink/60 dark:text-ink-dark/60
                         hover:bg-canvas-panel dark:hover:bg-canvas-dark-panel
                         transition-colors"
            >
              Cancel
            </button>
          )}

          {isComplete && (
            <button
              onClick={() => onRemove(file)}
              className="px-2 py-1 text-meta font-medium rounded-control
                         text-ink/60 dark:text-ink-dark/60
                         hover:bg-canvas-panel dark:hover:bg-canvas-dark-panel
                         transition-colors"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Icons
// ============================================================================

function UploadIcon(): React.ReactElement {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="mx-auto text-ink/60 dark:text-ink-dark/60"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}
