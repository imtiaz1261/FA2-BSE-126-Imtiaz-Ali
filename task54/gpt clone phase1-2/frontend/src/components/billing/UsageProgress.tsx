import React from "react";
import { cn } from "@/lib/cn";

export interface UsageProgressProps {
  used: number;
  limit: number;
  unit?: string;
  showPercentage?: boolean;
}

export const UsageProgress: React.FC<UsageProgressProps> = ({
  used,
  limit,
  unit = "messages",
  showPercentage = true,
}) => {
  const percentage = limit > 0 ? (used / limit) * 100 : 0;
  const isWarning = percentage >= 80;
  const isExceeded = percentage >= 100;

  const getStatusColor = () => {
    if (isExceeded) return "bg-red-600 dark:bg-red-500";
    if (isWarning) return "bg-yellow-600 dark:bg-yellow-500";
    return "bg-accent-600 dark:bg-accent-400";
  };

  const getStatusText = () => {
    if (isExceeded) return "Exceeded";
    if (isWarning) return "Warning";
    return "OK";
  };

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-body font-medium text-ink dark:text-ink-dark">
          Daily {unit}
        </span>
        <span className="text-meta text-ink-secondary dark:text-ink-secondary-dark">
          {used} / {limit}
        </span>
      </div>

      {/* Progress bar */}
      <div className="relative h-2 bg-canvas-panel dark:bg-canvas-dark-panel rounded-full overflow-hidden">
        <div
          className={cn("h-full transition-all", getStatusColor())}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-ink-secondary dark:text-ink-secondary-dark">
          {showPercentage && (
            <>
              {Math.round(percentage)}% used
              {isExceeded && " - Upgrade to continue"}
            </>
          )}
        </span>
        <span
          className={cn(
            "text-xs font-medium px-2 py-0.5 rounded-control",
            isExceeded
              ? "bg-red-600/10 text-red-600 dark:text-red-400"
              : isWarning
                ? "bg-yellow-600/10 text-yellow-600 dark:text-yellow-400"
                : "bg-accent-600/10 text-accent-600 dark:text-accent-400"
          )}
        >
          {getStatusText()}
        </span>
      </div>

      {/* Remaining */}
      <div className="text-xs text-ink-secondary dark:text-ink-secondary-dark">
        {Math.max(0, limit - used)} {unit} remaining today
      </div>
    </div>
  );
};
