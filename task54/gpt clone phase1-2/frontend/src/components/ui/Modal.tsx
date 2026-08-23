import React, { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";

/**
 * A minimal, accessible Modal. Module 1's design system doesn't ship one yet
 * (it's slated for that system's own Module 2), so this implements just
 * enough for the onboarding flow using the same tokens: `rounded-control`
 * radius, hairline border, and the single `shadow-modal` elevation reserved
 * for modals per the design spec.
 */
export interface ModalProps {
  open: boolean;
  onClose?: () => void;
  /** When false, the modal can't be dismissed via backdrop/Esc — used for onboarding. */
  dismissible?: boolean;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Modal({
  open,
  onClose,
  dismissible = true,
  title,
  children,
  className,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && dismissible) onClose?.();
      if (e.key === "Tab") {
        // Basic focus trap
        const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (!focusable || focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      previouslyFocused?.focus();
    };
  }, [open, dismissible, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in"
      aria-hidden={false}
    >
      <div
        className="absolute inset-0 bg-black/40"
        onClick={dismissible ? onClose : undefined}
        aria-hidden="true"
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={cn(
          "relative w-full max-w-md rounded-control border border-border dark:border-border-dark",
          "bg-canvas dark:bg-canvas-dark-panel text-ink dark:text-ink-dark",
          "p-6 shadow-modal animate-scale-in focus:outline-none",
          className
        )}
      >
        {title && <h2 className="mb-4 text-heading font-semibold">{title}</h2>}
        {children}
      </div>
    </div>
  );
}
