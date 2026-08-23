/**
 * Usage Meter Component
 * 
 * Shows daily message usage for free-tier users
 * Changes color as approaching the limit
 */

import React, { useEffect } from "react";
import { cn } from "@/lib/cn";
import { useSettingsStore } from "@/store/settingsStore";

interface UsageMeterProps {
  compact?: boolean;
  showLabel?: boolean;
}

export function UsageMeter({ compact = false, showLabel = true }: UsageMeterProps) {
  const { usage, isLoadingUsage, fetchUsage } = useSettingsStore();

  useEffect(() => {
    fetchUsage();
    // Refresh usage every 5 minutes
    const interval = setInterval(fetchUsage, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchUsage]);

  if (isLoadingUsage || !usage) {
    return null;
  }

  const percentage = (usage.used / usage.limit) * 100;
  const isWarning = percentage >= 70;
  const isCritical = percentage >= 90;

  const getColor = () => {
    if (isCritical) return "bg-danger";
    if (isWarning) return "bg-yellow-500";
    return "bg-green-600";
  };

  const getTextColor = () => {
    if (isCritical) return "text-danger";
    if (isWarning) return "text-yellow-600";
    return "text-green-600";
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 rounded-full bg-canvas dark:bg-canvas-dark overflow-hidden">
          <div
            className={cn("h-full transition-all", getColor())}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
        <span className={cn("text-meta font-medium whitespace-nowrap", getTextColor())}>
          {usage.used}/{usage.limit}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {showLabel && (
        <div className="flex items-center justify-between">
          <label className="text-body font-medium text-ink dark:text-ink-dark">
            Today's message usage
          </label>
          <span className={cn("text-meta font-medium", getTextColor())}>
            {usage.used} of {usage.limit} used
          </span>
        </div>
      )}

      {/* Progress bar */}
      <div className="w-full h-3 rounded-full bg-canvas dark:bg-canvas-dark overflow-hidden border border-border/50 dark:border-border-dark/50">
        <div
          className={cn("h-full transition-all duration-300", getColor())}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>

      {/* Info text */}
      <p className={cn("text-meta", getTextColor())}>
        {usage.remaining > 0
          ? `${usage.remaining} message${usage.remaining === 1 ? "" : "s"} remaining today`
          : "Message limit reached for today"}
      </p>

      {/* Warning message */}
      {isCritical && (
        <div className="p-2 rounded-control bg-danger/10 dark:bg-red-500/10 border border-danger/50 dark:border-red-500/50">
          <p className="text-meta font-medium text-danger dark:text-red-400">
            ⚠️ You've reached your daily message limit. Try again tomorrow.
          </p>
        </div>
      )}

      {isWarning && !isCritical && (
        <div className="p-2 rounded-control bg-yellow-600/10 dark:bg-yellow-600/10 border border-yellow-600/50 dark:border-yellow-600/50">
          <p className="text-meta font-medium text-yellow-700 dark:text-yellow-600">
            ℹ️ You're approaching your daily message limit.
          </p>
        </div>
      )}
    </div>
  );
}
