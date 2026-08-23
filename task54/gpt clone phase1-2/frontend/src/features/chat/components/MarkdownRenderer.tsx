import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { CodeBlock } from "./CodeBlock";

/** Full markdown rendering for assistant messages: headings, GFM tables,
 * lists, blockquotes, LaTeX math ($inline$ and $$block$$), and fenced code
 * blocks routed through the syntax-highlighted, copyable `CodeBlock`.
 */
export function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="chat-markdown text-body text-ink dark:text-ink-dark">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const isBlock = Boolean(match) || String(children).includes("\n");
            if (!isBlock) {
              return (
                <code
                  className="rounded bg-canvas-panel dark:bg-canvas-dark-alt px-1.5 py-0.5 font-mono text-[13px]"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <CodeBlock
                language={match?.[1]}
                code={String(children).replace(/\n$/, "")}
              />
            );
          },
          // Strip the <pre> wrapper react-markdown adds around <code> blocks
          // — CodeBlock already renders its own container.
          pre({ children }) {
            return <>{children}</>;
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto rounded-control border border-border dark:border-border-dark">
                <table className="w-full border-collapse text-body">{children}</table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="border-b border-border dark:border-border-dark bg-canvas-panel dark:bg-canvas-dark-alt px-3 py-2 text-left font-semibold">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="border-b border-border dark:border-border-dark px-3 py-2">
                {children}
              </td>
            );
          },
          a({ children, href }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-accent-600 dark:text-accent-400 hover:underline"
              >
                {children}
              </a>
            );
          },
          ul({ children }) {
            return <ul className="my-2 list-disc pl-5">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="my-2 list-decimal pl-5">{children}</ol>;
          },
          h1({ children }) {
            return <h1 className="mb-2 mt-4 text-display font-semibold first:mt-0">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="mb-2 mt-4 text-heading font-semibold first:mt-0">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="mb-1.5 mt-3 text-body font-semibold first:mt-0">{children}</h3>;
          },
          p({ children }) {
            return <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-2 border-l-2 border-accent-600 dark:border-accent-400 pl-3 text-ink/70 dark:text-ink-dark/70">
                {children}
              </blockquote>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
