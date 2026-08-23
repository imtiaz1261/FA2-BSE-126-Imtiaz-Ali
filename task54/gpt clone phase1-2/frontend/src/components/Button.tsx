import React from "react";
import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-meta gap-1.5",
  md: "h-10 px-4 text-body gap-2",
  lg: "h-12 px-5 text-body gap-2",
};

const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-accent-600 text-white hover:bg-accent-700 active:bg-accent-700 disabled:bg-accent-600/50",
  secondary: "bg-transparent text-ink dark:text-ink-dark border border-border dark:border-border-dark hover:border-accent-600 dark:hover:border-accent-400",
  ghost: "bg-transparent text-ink dark:text-ink-dark hover:bg-canvas-panel dark:hover:bg-canvas-dark-panel",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading = false, disabled, leftIcon, rightIcon, children, ...props }, ref) => (
    <button
      ref={ref}
      type="button"
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center rounded-control font-medium transition-colors duration-150 select-none disabled:cursor-not-allowed disabled:opacity-60",
        sizeStyles[size],
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {loading ? (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      ) : (
        leftIcon
      )}
      {children}
      {!loading && rightIcon}
    </button>
  )
);
Button.displayName = "Button";