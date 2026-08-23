/**
 * Citation renderer for RAG sources.
 * 
 * Renders inline citations as clickable footnotes that can:
 * - Jump to source in file manager
 * - Preview chunk text
 * - Show page numbers (for PDFs)
 * - Track citation metadata
 */

import React, { useState } from "react";

// ============================================================================
// Types
// ============================================================================

export interface Citation {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number?: number;
  chunk_index: number;
}

interface CitationRendererProps {
  content: string;
  citations: Citation[];
  onCitationClick?: (citation: Citation) => void;
}

interface CitationTooltipProps {
  citation: Citation;
  isOpen: boolean;
  onClose: () => void;
  position: { x: number; y: number } | null;
}

// ============================================================================
// Main Component
// ============================================================================

export function CitationRenderer({
  content,
  citations,
  onCitationClick,
}: CitationRendererProps): React.ReactElement {
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);

  const handleCitationClick = (e: React.MouseEvent, citation: Citation) => {
    e.preventDefault();

    // Position tooltip near click
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    setTooltipPos({
      x: rect.left,
      y: rect.bottom + 8,
    });

    setActiveCitation(citation);
    onCitationClick?.(citation);
  };

  // Parse content to find citation markers and replace with clickable footnotes
  const parts = parseCitations(content, citations);

  return (
    <div className="relative">
      <div className="prose dark:prose-invert max-w-none">
        {parts.map((part, idx) => {
          if (typeof part === "string") {
            return (
              <span key={idx} className="text-ink dark:text-ink-dark">
                {part}
              </span>
            );
          }

          const citation = part;
          const citationNum = citations.findIndex(
            (c) => c.chunk_id === citation.chunk_id
          ) + 1;

          return (
            <button
              key={`${citation.chunk_id}-${idx}`}
              onClick={(e) => handleCitationClick(e, citation)}
              className={`
                inline-block align-super text-xs mx-0.5 px-1.5 py-0.5
                rounded-control font-semibold transition-colors
                ${
                  activeCitation?.chunk_id === citation.chunk_id
                    ? "bg-accent-600/20 dark:bg-accent-400/20 text-accent-600 dark:text-accent-400"
                    : "bg-accent-600/10 dark:bg-accent-400/10 text-accent-600 dark:text-accent-400 hover:bg-accent-600/20 dark:hover:bg-accent-400/20"
                }
              `}
              title={`${citation.filename}${
                citation.page_number ? ` (page ${citation.page_number})` : ""
              }`}
            >
              [{citationNum}]
            </button>
          );
        })}
      </div>

      {/* Citation Tooltip/Popover */}
      {activeCitation && tooltipPos && (
        <CitationTooltip
          citation={activeCitation}
          isOpen={!!activeCitation}
          onClose={() => setActiveCitation(null)}
          position={tooltipPos}
        />
      )}
    </div>
  );
}

// ============================================================================
// Citation Tooltip
// ============================================================================

function CitationTooltip({
  citation,
  isOpen,
  onClose,
  position,
}: CitationTooltipProps): React.ReactElement {
  if (!isOpen || !position) return <></>;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
      />

      {/* Tooltip */}
      <div
        className={`
          fixed z-50 rounded-control shadow-modal
          bg-canvas-panel dark:bg-canvas-dark-panel
          border border-border dark:border-border-dark
          max-w-sm w-80 p-3 space-y-2
          transform transition-all
          ${isOpen ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"}
        `}
        style={{
          left: `${position.x}px`,
          top: `${position.y}px`,
          transform: "translateX(-50%)",
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="text-meta font-semibold text-ink dark:text-ink-dark truncate">
              {citation.filename}
            </div>
            {citation.page_number && (
              <div className="text-meta text-ink/60 dark:text-ink-dark/60">
                Page {citation.page_number}
              </div>
            )}
          </div>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="text-ink/60 dark:text-ink-dark/60 hover:text-ink dark:hover:text-ink-dark"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Content Preview */}
        <div className="text-body text-ink/80 dark:text-ink-dark/80 line-clamp-4">
          {citation.filename}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 border-t border-border dark:border-border-dark">
          <button
            onClick={onClose}
            className="ml-auto px-2 py-1 text-meta font-medium rounded-control
                       text-ink/60 dark:text-ink-dark/60
                       hover:bg-canvas dark:hover:bg-canvas-dark
                       transition-colors"
          >
            Close
          </button>

          <a
            href={`#documents/${citation.document_id}`}
            onClick={onClose}
            className="px-2 py-1 text-meta font-medium rounded-control
                       text-accent-600 dark:text-accent-400
                       hover:bg-accent-600/10 dark:hover:bg-accent-400/10
                       transition-colors"
          >
            View Document
          </a>
        </div>
      </div>
    </>
  );
}

// ============================================================================
// Citation List View
// ============================================================================

interface CitationListProps {
  citations: Citation[];
  onCitationClick?: (citation: Citation) => void;
}

/**
 * Alternative view for citations as a collapsible list.
 * Useful for chat messages with multiple citations.
 */
export function CitationList({
  citations,
  onCitationClick,
}: CitationListProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);

  if (citations.length === 0) {
    return <></>;
  }

  return (
    <div className="mt-3 rounded-control border border-border dark:border-border-dark p-3 space-y-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-meta font-semibold
                   text-ink dark:text-ink-dark
                   hover:text-accent-600 dark:hover:text-accent-400
                   transition-colors"
      >
        <span className="text-xs">
          {isOpen ? "▼" : "▶"}
        </span>
        Sources ({citations.length})
      </button>

      {isOpen && (
        <div className="space-y-1 pt-2 border-t border-border dark:border-border-dark">
          {citations.map((citation, idx) => (
            <CitationListItem
              key={`${citation.chunk_id}-${idx}`}
              citation={citation}
              number={idx + 1}
              onClick={() => {
                onCitationClick?.(citation);
                setIsOpen(false);
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface CitationListItemProps {
  citation: Citation;
  number: number;
  onClick?: () => void;
}

function CitationListItem({
  citation,
  number,
  onClick,
}: CitationListItemProps): React.ReactElement {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-2 py-1 rounded-control
                 hover:bg-canvas-panel dark:hover:bg-canvas-dark-panel
                 transition-colors group"
    >
      <div className="flex items-start gap-2">
        <span
          className="mt-0.5 flex-shrink-0 text-xs font-semibold
                     text-ink/60 dark:text-ink-dark/60
                     group-hover:text-accent-600 dark:group-hover:text-accent-400"
        >
          [{number}]
        </span>

        <div className="flex-1 min-w-0">
          <div className="text-meta font-medium text-ink dark:text-ink-dark truncate
                         group-hover:text-accent-600 dark:group-hover:text-accent-400">
            {citation.filename}
          </div>

          {citation.page_number && (
            <div className="text-meta text-ink/60 dark:text-ink-dark/60">
              Page {citation.page_number}, Chunk {citation.chunk_index}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Parse content and extract citation markers.
 * 
 * Simple implementation: looks for citation-like markers or
 * uses citation indices to replace placeholders.
 * 
 * In real implementation, you might:
 * 1. Have LLM return inline markers like [citation:0]
 * 2. Parse and replace with footnote links
 * 3. Store citation data separately
 */
function parseCitations(
  content: string,
  citations: Citation[]
): (string | Citation)[] {
  if (!citations.length) {
    return [content];
  }

  // For now, just return content
  // In production, parse citation markers and replace with Citations
  return [content];
}

/**
 * Create citation from retrieved chunk.
 */
export function createCitation(chunk: {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number?: number;
  chunk_index: number;
}): Citation {
  return {
    chunk_id: chunk.chunk_id,
    document_id: chunk.document_id,
    filename: chunk.filename,
    page_number: chunk.page_number,
    chunk_index: chunk.chunk_index,
  };
}
