/**
 * Image composer input for vision requests.
 * 
 * Features:
 * - Drag-drop image upload
 * - File picker
 * - Paste from clipboard
 * - Image preview thumbnails with remove buttons
 * - Upload progress and error states
 * - Mode toggle (Q&A vs extraction)
 */

import React, { useRef, useState, useEffect } from "react";
import {
  deleteImage,
  formatFileSize,
  imageToBase64,
  uploadImages,
  validateImageFile,
  type ImageUploadResponse,
} from "@/lib/visionApi";

// ============================================================================
// Types
// ============================================================================

interface SelectedImage {
  file: File;
  base64?: string;
  uploadResponse?: ImageUploadResponse;
  status: "pending" | "uploading" | "uploaded" | "error";
  progress: number;
  error?: string;
}

interface ImageComposerProps {
  conversationId?: string;
  onImagesReady?: (images: ImageUploadResponse[]) => void;
  onModeChange?: (mode: "qa" | "extract") => void;
  mode?: "qa" | "extract";
}

// ============================================================================
// Component
// ============================================================================

export function ImageComposer({
  conversationId,
  onImagesReady,
  onModeChange,
  mode = "qa",
}: ImageComposerProps): React.ReactElement {
  const [selectedImages, setSelectedImages] = useState<SelectedImage[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [currentMode, setCurrentMode] = useState<"qa" | "extract">(mode);

  // ============================================================================
  // File Selection & Upload
  // ============================================================================

  const handleFileSelect = async (files: File[]) => {
    const newImages: SelectedImage[] = [];

    for (const file of files) {
      // Validate
      const validation = validateImageFile(file);
      if (!validation.valid) {
        newImages.push({
          file,
          status: "error",
          progress: 0,
          error: validation.error,
        });
        continue;
      }

      // Convert to preview
      const base64 = await imageToBase64(file);
      newImages.push({
        file,
        base64,
        status: "pending",
        progress: 0,
      });
    }

    // Add to state
    setSelectedImages((prev) => [...prev, ...newImages]);

    // Auto-upload new images
    uploadSelectedImages(newImages.filter((img) => img.status === "pending"));
  };

  const uploadSelectedImages = async (imagesToUpload: SelectedImage[]) => {
    if (imagesToUpload.length === 0 || isUploading) return;

    setIsUploading(true);

    try {
      const files = imagesToUpload.map((img) => img.file);

      const uploadedImages = await uploadImages(
        files,
        conversationId,
        (fileIndex, progress) => {
          setSelectedImages((prev) =>
            prev.map((img, idx) =>
              idx >= fileIndex && idx < fileIndex + 1
                ? { ...img, progress: Math.round(progress.percentage), status: "uploading" }
                : img
            )
          );
        }
      );

      // Update with upload responses
      setSelectedImages((prev) =>
        prev.map((img, idx) => {
          const uploaded = uploadedImages.find(
            (u) => u.filename === img.file.name
          );
          return uploaded
            ? {
                ...img,
                uploadResponse: uploaded,
                status: "uploaded",
                progress: 100,
              }
            : img;
        })
      );

      // Notify parent
      onImagesReady?.(uploadedImages);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Upload failed";

      setSelectedImages((prev) =>
        prev.map((img) =>
          img.status === "uploading"
            ? { ...img, status: "error", error: errorMsg }
            : img
        )
      );
    } finally {
      setIsUploading(false);
    }
  };

  // ============================================================================
  // Drag-and-Drop
  // ============================================================================

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    handleFileSelect(files);
  };

  // ============================================================================
  // Paste Handler
  // ============================================================================

  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      const files: File[] = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === "file") {
          const file = items[i].getAsFile();
          if (file) files.push(file);
        }
      }

      if (files.length > 0) {
        handleFileSelect(files);
      }
    };

    document.addEventListener("paste", handlePaste);
    return () => document.removeEventListener("paste", handlePaste);
  }, []);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-3">
      {/* Mode Toggle */}
      <div className="flex items-center gap-2 p-2 rounded-control bg-canvas-panel dark:bg-canvas-dark-panel">
        <label className="text-meta font-medium text-ink/60 dark:text-ink-dark/60">
          Mode:
        </label>

        <button
          onClick={() => {
            setCurrentMode("qa");
            onModeChange?.("qa");
          }}
          className={`px-2 py-1 rounded text-meta font-medium transition-colors ${
            currentMode === "qa"
              ? "bg-accent-600/20 text-accent-600 dark:bg-accent-400/20 dark:text-accent-400"
              : "text-ink/60 dark:text-ink-dark/60 hover:text-ink dark:hover:text-ink-dark"
          }`}
        >
          Q&A
        </button>

        <button
          onClick={() => {
            setCurrentMode("extract");
            onModeChange?.("extract");
          }}
          className={`px-2 py-1 rounded text-meta font-medium transition-colors ${
            currentMode === "extract"
              ? "bg-accent-600/20 text-accent-600 dark:bg-accent-400/20 dark:text-accent-400"
              : "text-ink/60 dark:text-ink-dark/60 hover:text-ink dark:hover:text-ink-dark"
          }`}
        >
          Extract
        </button>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative rounded-control border-2 border-dashed p-4 text-center
          transition-all duration-200
          ${
            isDragging
              ? "border-accent-600 dark:border-accent-400 bg-accent-600/5 dark:bg-accent-400/5"
              : "border-border dark:border-border-dark"
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          onChange={(e) => handleFileSelect(Array.from(e.target.files || []))}
          className="hidden"
        />

        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full cursor-pointer space-y-1"
        >
          <ImageIcon />
          <div className="text-body font-medium text-ink dark:text-ink-dark">
            Drop images or click to browse
          </div>
          <div className="text-meta text-ink/60 dark:text-ink-dark/60">
            JPEG, PNG, WebP, GIF up to 10MB • Or paste (Cmd/Ctrl+V)
          </div>
        </button>
      </div>

      {/* Image Previews */}
      {selectedImages.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
          {selectedImages.map((img, idx) => (
            <ImagePreviewThumbnail
              key={`${img.file.name}-${idx}`}
              image={img}
              onRemove={() => {
                setSelectedImages((prev) => prev.filter((_, i) => i !== idx));
                if (img.uploadResponse) {
                  deleteImage(img.uploadResponse.image_id).catch(console.error);
                }
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Image Thumbnail
// ============================================================================

interface ImagePreviewThumbnailProps {
  image: SelectedImage;
  onRemove: () => void;
}

function ImagePreviewThumbnail({
  image,
  onRemove,
}: ImagePreviewThumbnailProps): React.ReactElement {
  return (
    <div className="relative rounded-control overflow-hidden border border-border dark:border-border-dark">
      {/* Image Preview */}
      {image.base64 && (
        <img
          src={image.base64}
          alt={image.file.name}
          className="w-full h-24 object-cover"
        />
      )}

      {/* Overlay */}
      <div
        className={`
          absolute inset-0 flex items-center justify-center
          transition-all duration-200
          ${
            image.status === "error"
              ? "bg-danger/20"
              : image.status === "uploading"
                ? "bg-accent-600/10 dark:bg-accent-400/10"
                : "bg-black/0 hover:bg-black/10"
          }
        `}
      >
        {/* Status Indicator */}
        {image.status === "uploading" && (
          <div className="text-center space-y-1">
            <div className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-accent-600 dark:border-accent-400 border-t-transparent" />
            <div className="text-xs font-medium text-accent-600 dark:text-accent-400">
              {image.progress}%
            </div>
          </div>
        )}

        {image.status === "error" && (
          <div className="text-center space-y-1">
            <ErrorIcon />
            <div className="text-xs font-medium text-danger">Error</div>
          </div>
        )}

        {image.status === "uploaded" && (
          <div className="text-center">
            <CheckIcon />
          </div>
        )}
      </div>

      {/* Remove Button */}
      <button
        onClick={onRemove}
        className={`
          absolute top-1 right-1 rounded-full p-1 transition-all
          ${
            image.status === "uploaded"
              ? "bg-black/50 hover:bg-black/70 text-white"
              : "bg-white/50 hover:bg-white/70"
          }
        `}
        aria-label="Remove image"
      >
        ✕
      </button>

      {/* Error Tooltip */}
      {image.error && (
        <div className="absolute inset-x-0 bottom-0 bg-danger/90 text-white text-xs p-1 truncate">
          {image.error}
        </div>
      )}

      {/* Info Overlay */}
      <div className="absolute bottom-0 inset-x-0 bg-black/40 text-white text-xs px-1 py-0.5 truncate">
        {image.file.name}
      </div>
    </div>
  );
}

// ============================================================================
// Icons
// ============================================================================

function ImageIcon(): React.ReactElement {
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
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <polyline points="21 15 16 10 5 21" />
    </svg>
  );
}

function ErrorIcon(): React.ReactElement {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="text-danger"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function CheckIcon(): React.ReactElement {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      className="text-success"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}
