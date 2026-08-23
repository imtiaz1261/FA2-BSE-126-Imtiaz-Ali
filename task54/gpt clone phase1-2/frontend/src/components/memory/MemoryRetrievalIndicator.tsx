import React from "react";
import { cn } from "@/lib/cn";

export interface MemoryRetrievalIndicatorProps {
  isActive?: boolean;
  messageCount?: number;
  className?: string;
}

export const MemoryRetrievalIndicator: React.FC<MemoryRetrievalIndicatorProps> = ({
  isActive = false,
  messageCount = 0,
  className,
}) => {
  if (!isActive && messageCount === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-2.5 py-1.5 rounded-control text-xs font-medium",
        "bg-accent-600/10 text-accent-600 dark:text-accent-400",
        "animate-pulse",
        className
      )}
    >
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-600 dark:bg-accent-400" />
      {isActive ? (
        <span>Retrieving memories...</span>
      ) : (
        <span>{messageCount} memory item{messageCount !== 1 ? "s" : ""} injected</span>
      )}
    </div>
  );
};
