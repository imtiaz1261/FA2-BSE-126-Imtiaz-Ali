/**
 * API client for document upload and RAG operations.
 * 
 * Handles:
 * - File uploads with progress tracking
 * - Job status polling
 * - Document listing and deletion
 * - Chunk retrieval for RAG
 */

import { apiRequest } from "./apiClient";

// ============================================================================
// Types
// ============================================================================

export interface UploadJobResponse {
  job_id: string;
  document_id: string | null;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  error_message: string | null;
}

export interface UploadStatusResponse {
  job_id: string;
  document_id: string | null;
  status: "pending" | "processing" | "ready" | "failed";
  progress: number;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentMetadata {
  id: string;
  filename: string;
  file_type: "pdf" | "docx" | "txt" | "csv";
  file_size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  chunk_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentMetadata[];
  total_count: number;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  chunk_index: number;
  text: string;
  relevance_score: number;
}

export interface RetrievalResult {
  query: string;
  chunks: RetrievedChunk[];
  total_chunks_searched: number;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

// ============================================================================
// Upload with Progress
// ============================================================================

/**
 * Upload a file with progress tracking.
 * 
 * @param file - File to upload
 * @param conversationId - Optional conversation scope
 * @param onProgress - Callback for upload progress
 * @returns Upload job response
 */
export async function uploadDocument(
  file: File,
  conversationId?: string,
  onProgress?: (progress: UploadProgress) => void
): Promise<UploadJobResponse> {
  const formData = new FormData();
  formData.append("file", file);

  if (conversationId) {
    formData.append("conversation_id", conversationId);
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && onProgress) {
        const progress = (event.loaded / event.total) * 100;
        onProgress({
          loaded: event.loaded,
          total: event.total,
          percentage: progress,
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
        reject(new Error(`Upload failed: ${xhr.statusText}`));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Upload failed"));
    });

    xhr.addEventListener("abort", () => {
      reject(new Error("Upload cancelled"));
    });

    // Get auth token and add to headers
    const token = localStorage.getItem("access_token");
    xhr.open("POST", `${import.meta.env.VITE_API_URL}/documents/upload`);
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }

    xhr.send(formData);
  });
}

// ============================================================================
// Status Polling
// ============================================================================

/**
 * Poll the status of an upload job.
 * 
 * @param jobId - Job ID from upload response
 * @returns Current job status
 */
export async function getUploadStatus(jobId: string): Promise<UploadStatusResponse> {
  return apiRequest(`/documents/status/${jobId}`, {
    method: "GET",
  });
}

/**
 * Poll upload status with retry logic.
 * 
 * @param jobId - Job ID
 * @param maxAttempts - Max polling attempts
 * @param delayMs - Delay between polls
 * @param onStatusChange - Callback when status changes
 * @returns Final status when complete
 */
export async function pollUploadStatus(
  jobId: string,
  maxAttempts: number = 300, // 5 minutes at 1s intervals
  delayMs: number = 1000,
  onStatusChange?: (status: UploadStatusResponse) => void
): Promise<UploadStatusResponse> {
  let lastStatus: UploadStatusResponse | null = null;
  let attempts = 0;

  while (attempts < maxAttempts) {
    try {
      const status = await getUploadStatus(jobId);

      // Notify of status change
      if (
        !lastStatus ||
        lastStatus.status !== status.status ||
        lastStatus.progress !== status.progress
      ) {
        onStatusChange?.(status);
      }

      lastStatus = status;

      // Stop polling when done or failed
      if (status.status === "ready" || status.status === "failed") {
        return status;
      }

      // Wait before next poll
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      attempts++;
    } catch (error) {
      console.error("Error polling upload status:", error);
      // Continue polling on error
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      attempts++;
    }
  }

  throw new Error("Upload polling timeout");
}

// ============================================================================
// Document Management
// ============================================================================

/**
 * List documents for a conversation.
 * 
 * @param conversationId - Optional conversation to filter by
 * @param statusFilter - Optional status filter
 * @returns List of documents
 */
export async function listDocuments(
  conversationId?: string,
  statusFilter?: string
): Promise<DocumentListResponse> {
  const params = new URLSearchParams();

  if (conversationId) {
    params.append("conversation_id", conversationId);
  }

  if (statusFilter) {
    params.append("status_filter", statusFilter);
  }

  const query = params.toString();
  const url = query ? `/documents?${query}` : "/documents";

  return apiRequest(url, {
    method: "GET",
  });
}

/**
 * Delete a document.
 * 
 * @param documentId - Document to delete
 * @returns Success response
 */
export async function deleteDocument(
  documentId: string
): Promise<{ message: string; document_id: string }> {
  return apiRequest(`/documents/${documentId}`, {
    method: "DELETE",
  });
}

// ============================================================================
// Retrieval
// ============================================================================

/**
 * Retrieve relevant chunks for a query (RAG).
 * 
 * @param query - Search query
 * @param conversationId - Optional conversation scope
 * @param topK - Number of results (1-20)
 * @returns Retrieval results with chunks
 */
export async function retrieveChunks(
  query: string,
  conversationId?: string,
  topK: number = 5
): Promise<RetrievalResult> {
  const params = new URLSearchParams();
  params.append("query", query);
  params.append("top_k", topK.toString());

  if (conversationId) {
    params.append("conversation_id", conversationId);
  }

  return apiRequest(`/documents/retrieve?${params}`, {
    method: "POST",
  });
}

// ============================================================================
// Validation
// ============================================================================

const SUPPORTED_TYPES = ["pdf", "docx", "txt", "csv"];
const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB

export function validateFile(file: File): { valid: boolean; error?: string } {
  const extension = file.name.split(".").pop()?.toLowerCase();

  if (!extension || !SUPPORTED_TYPES.includes(extension)) {
    return {
      valid: false,
      error: `Unsupported file type: ${extension}. Supported: ${SUPPORTED_TYPES.join(", ")}`,
    };
  }

  if (file.size > MAX_FILE_SIZE) {
    return {
      valid: false,
      error: `File size exceeds 20MB limit (${(file.size / 1024 / 1024).toFixed(1)}MB)`,
    };
  }

  return { valid: true };
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}
