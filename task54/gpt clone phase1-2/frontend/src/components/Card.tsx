import React from "react";
import { cn } from "@/lib/cn";

export function Card({ className, children, ...props }: Readonly<React.HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={cn(
        "rounded-control border border-border dark:border-border-dark bg-canvas dark:bg-canvas-dark-panel text-ink dark:text-ink-dark p-4",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}