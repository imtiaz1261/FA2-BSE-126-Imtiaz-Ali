/**
 * API client for Image Understanding (Vision) operations.
 * 
 * Handles:
 * - Image uploads with validation
 * - Vision Q&A requests
 * - Structured data extraction
 * - Progress tracking
 */

import { apiRequest } from "./apiClient";

// ============================================================================
// Types
// ============================================================================

export interface ImageUploadResponse {
  image_id: string;
  filename: string;
  file_type: "jpeg" | "png" | "webp" | "gif";
  file_size_bytes: number;
  signed_url: string;
  signed_url_expires_at: string;
  metadata: {
    format: string;
    width: number;
    height: number;
    size_bytes: number;
  };
}

export interface ImageErrorDetail {
  image_index: number;
  filename: string;
  error_code: string;
  error_message: string;
}

export interface ImageValidationError {
  errors: ImageErrorDetail[];
}

export interface VisionQARequest {
  image_ids: string[];
  question: string;
  conversation_id?: string;
}

export interface VisionQAResponse {
  request_id: string;
  answer: string;
  images_processed: string[];
  confidence?: number;
  created_at: string;
}

export interface ExtractionSchema {
  type: "receipt" | "form" | "table" | "custom";
  fields?: Record<string, "string" | "number" | "date" | "list">;
}

export interface VisionExtractionRequest {
  image_ids: string[];
  extraction_type: string;
  custom_schema?: Record<string, string>;
  conversation_id?: string;
}

export interface ExtractionResult {
  request_id: string;
  extraction_type: string;
  data: Record<string, any>;
  confidence_scores?: Record<string, number>;
  images_processed: string[];
  created_at: string;
}

export interface VisionRequestStatus {
  request_id: string;
  status: "pending" | "completed" | "failed";
  request_type: "qa" | "extract";
  response?: string;
  extraction_result?: Record<string, any>;
  error_message?: string;
  images_used: string[];
  created_at: string;
  updated_at: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

// ============================================================================
// Image Upload
// ============================================================================

const SUPPORTED_TYPES = ["jpeg", "jpg", "png", "webp", "gif"];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB per spec

export function validateImageFile(file: File): { valid: boolean; error?: string } {
  const extension = file.name.split(".").pop()?.toLowerCase();

  if (!extension || !SUPPORTED_TYPES.includes(extension)) {
    return {
      valid: false,
      error: `Unsupported format: ${extension}. Supported: ${SUPPORTED_TYPES.join(", ")}`,
    };
  }

  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `File size ${(file.size / 1024 / 1024).toFixed(1)}MB exceeds 10MB limit`,
    };
  }

  return { valid: true };
}

/**
 * Upload one or more images.
 * 
 * @param files - Files to upload
 * @param conversationId - Optional conversation scope
 * @param onProgress - Progress callback per file
 * @returns Uploaded image metadata
 */
export async function uploadImages(
  files: File[],
  conversationId?: string,
  onProgress?: (fileIndex: number, progress: UploadProgress) => void
): Promise<ImageUploadResponse[]> {
  const formData = new FormData();

  // Add files
  files.forEach((file) => {
    formData.append("files", file);
  });

  // Add conversation ID if provided
  if (conversationId) {
    formData.append("conversation_id", conversationId);
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Track progress
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        const percentage = (event.loaded / event.total) * 100;
        // Assume even distribution across files
        const fileIndex = Math.floor((event.loaded / event.total) * files.length);
        onProgress(fileIndex, {
          loaded: event.loaded,
          total: event.total,
          percentage,
        });
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch (e) {
          reject(new Error("Failed to parse upload response"));
        }
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          reject(new Error(error.detail || xhr.statusText));
        } catch {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Upload failed"));
    });

    // Get auth token
    const token = localStorage.getItem("access_token");
    xhr.open("POST", `${import.meta.env.VITE_API_URL}/chat/vision/upload`);
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }

    xhr.send(formData);
  });
}

// ============================================================================
// Vision Q&A
// ============================================================================

/**
 * Ask a question about one or more images.
 * 
 * @param imageIds - IDs of uploaded images
 * @param question - Question about the image(s)
 * @param conversationId - Optional conversation ID
 * @returns Vision answer
 */
export async function visionQA(
  imageIds: string[],
  question: string,
  conversationId?: string
): Promise<VisionQAResponse> {
  return apiRequest("/chat/vision/qa", {
    method: "POST",
    body: JSON.stringify({
      image_ids: imageIds,
      question,
      conversation_id: conversationId,
    }),
  });
}

// ============================================================================
// Structured Extraction
// ============================================================================

/**
 * Extract structured data from image(s).
 * 
 * @param imageIds - IDs of uploaded images
 * @param extractionType - Type: 'receipt', 'form', 'table', 'custom'
 * @param customSchema - For 'custom' type: {fieldName: fieldType}
 * @param conversationId - Optional conversation ID
 * @returns Extracted data
 */
export async function visionExtract(
  imageIds: string[],
  extractionType: string,
  customSchema?: Record<string, string>,
  conversationId?: string
): Promise<ExtractionResult> {
  return apiRequest("/chat/vision/extract", {
    method: "POST",
    body: JSON.stringify({
      image_ids: imageIds,
      extraction_type: extractionType,
      custom_schema: customSchema,
      conversation_id: conversationId,
    }),
  });
}

// ============================================================================
// Request Status & Management
// ============================================================================

/**
 * Get status of a vision request.
 * 
 * @param requestId - Vision request ID
 * @returns Request status and results
 */
export async function getVisionStatus(requestId: string): Promise<VisionRequestStatus> {
  return apiRequest(`/chat/vision/${requestId}`, {
    method: "GET",
  });
}

/**
 * Delete an uploaded image.
 * 
 * @param imageId - Image ID to delete
 * @returns Success response
 */
export async function deleteImage(imageId: string): Promise<{ message: string; image_id: string }> {
  return apiRequest(`/chat/vision/images/${imageId}`, {
    method: "DELETE",
  });
}

// ============================================================================
// Utilities
// ============================================================================

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

/**
 * Convert image to base64 for preview.
 */
export async function imageToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Get image dimensions.
 */
export async function getImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.width, height: img.height });
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}
