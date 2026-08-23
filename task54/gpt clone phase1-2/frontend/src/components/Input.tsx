import React, { useId } from "react";
import { cn } from "@/lib/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  errorText?: string;
  leftIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, helperText, errorText, leftIcon, id, ...props }, ref) => {
    const inputId = id ?? useId();
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-meta font-medium text-ink dark:text-ink-dark">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {leftIcon && (
            <span className="pointer-events-none absolute left-3 flex h-4 w-4 items-center justify-center text-ink/50 dark:text-ink-dark/50">
              {leftIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!errorText || undefined}
            className={cn(
              "h-10 w-full rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark text-ink dark:text-ink-dark text-body px-3 placeholder:text-ink/40 dark:placeholder:text-ink-dark/40 transition-colors focus-visible:border-accent",
              leftIcon && "pl-9",
              errorText && "border-danger focus-visible:outline-danger",
              "disabled:cursor-not-allowed disabled:opacity-60",
              className
            )}
            {...props}
          />
        </div>
        {errorText ? (
          <p className="text-meta text-danger">{errorText}</p>
        ) : (
          helperText && <p className="text-meta text-ink/60 dark:text-ink-dark/60">{helperText}</p>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";