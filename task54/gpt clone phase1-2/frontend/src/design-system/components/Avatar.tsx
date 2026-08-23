import React from "react";
import { cn } from "@/lib/cn";

export type AvatarTone = "neutral" | "accent";
export type AvatarSize = "sm" | "md";

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  tone?: AvatarTone;
  size?: AvatarSize;
}

const sizeStyles: Record<AvatarSize, string> = {
  sm: "h-8 w-8 text-meta",
  md: "h-10 w-10 text-body",
};

const toneStyles: Record<AvatarTone, string> = {
  neutral: "bg-canvas-panel dark:bg-canvas-dark-panel text-ink dark:text-ink-dark",
  accent: "bg-accent-600/10 text-accent-600 dark:text-accent-400",
};

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0]}${parts[parts.length - 1]![0]}`.toUpperCase();
}

export const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(
  ({ className, name, tone = "neutral", size = "sm", ...props }, ref) => (
    <div
      ref={ref}
      aria-label={name}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold",
        sizeStyles[size],
        toneStyles[tone],
        className
      )}
      {...props}
    >
      {getInitials(name)}
    </div>
  )
);
Avatar.displayName = "Avatar";