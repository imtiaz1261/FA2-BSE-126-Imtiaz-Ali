import React, { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight, oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTheme } from "@/theme/ThemeProvider";

interface CodeBlockProps {
  language: string | undefined;
  code: string;
}

/** Renders a fenced code block from markdown with a language label,
 * syntax highlighting (auto-detected from the fence's language tag,
 * e.g. ```python), and a "Copy code" button.
 */
export function CodeBlock({ language, code }: CodeBlockProps) {
  const { theme } = useTheme();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API can fail without permission/HTTPS — fail silently,
      // the button simply won't show the "Copied" confirmation.
    }
  };

  return (
    <div className="my-3 overflow-hidden rounded-control border border-border dark:border-border-dark">
      <div className="flex items-center justify-between bg-canvas-panel dark:bg-canvas-dark-alt px-3 py-1.5">
        <span className="text-meta font-medium text-ink/60 dark:text-ink-dark/60">
          {language || "text"}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-meta font-medium text-ink/60 dark:text-ink-dark/60 hover:text-accent-600 dark:hover:text-accent-400 transition-colors"
        >
          {copied ? (
            <>
              <CheckIcon /> Copied
            </>
          ) : (
            <>
              <CopyIcon /> Copy code
            </>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={theme === "dark" ? oneDark : oneLight}
        customStyle={{
          margin: 0,
          padding: "12px",
          fontSize: "13px",
          lineHeight: 1.5,
          background: "transparent",
        }}
        wrapLongLines
      >
        {code.replace(/\n$/, "")}
      </SyntaxHighlighter>
    </div>
  );
}

function CopyIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M3 10.5V3a1 1 0 0 1 1-1h7.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3.5 8.5 6.5 11.5 12.5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
