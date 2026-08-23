import React, { useState } from "react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

export interface BillingSectionProps {
  plan: string;
  status: string;
  currentPeriodEnd?: string;
  cancelAtPeriodEnd?: boolean;
  onManageBilling?: () => void;
  onCancel?: () => void;
  loading?: boolean;
}

export const BillingSection: React.FC<BillingSectionProps> = ({
  plan,
  status,
  currentPeriodEnd,
  cancelAtPeriodEnd = false,
  onManageBilling,
  onCancel,
  loading = false,
}) => {
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const getPlanBadgeColor = () => {
    switch (plan) {
      case "pro":
        return "bg-purple-600/10 text-purple-600 dark:text-purple-400";
      case "plus":
        return "bg-blue-600/10 text-blue-600 dark:text-blue-400";
      case "free":
      default:
        return "bg-gray-600/10 text-gray-600 dark:text-gray-400";
    }
  };

  const getStatusBadgeColor = () => {
    switch (status) {
      case "active":
      case "trialing":
        return "bg-green-600/10 text-green-600 dark:text-green-400";
      case "past_due":
        return "bg-yellow-600/10 text-yellow-600 dark:text-yellow-400";
      case "canceled":
        return "bg-red-600/10 text-red-600 dark:text-red-400";
      default:
        return "bg-gray-600/10 text-gray-600 dark:text-gray-400";
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <Card className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-heading-sm font-bold text-ink dark:text-ink-dark">
          Subscription
        </h3>
        <div className="flex gap-2">
          <span
            className={cn(
              "px-2.5 py-1 rounded-control text-xs font-medium",
              getPlanBadgeColor()
            )}
          >
            {plan.charAt(0).toUpperCase() + plan.slice(1)}
          </span>
          <span
            className={cn(
              "px-2.5 py-1 rounded-control text-xs font-medium",
              getStatusBadgeColor()
            )}
          >
            {status.replace("_", " ").charAt(0).toUpperCase() +
              status.slice(1).replace("_", " ")}
          </span>
        </div>
      </div>

      {/* Billing info */}
      {plan !== "free" && (
        <div className="space-y-2 pt-2 border-t border-border dark:border-border-dark">
          <div className="flex justify-between text-meta">
            <span className="text-ink-secondary dark:text-ink-secondary-dark">
              Next billing date:
            </span>
            <span className="text-ink dark:text-ink-dark font-medium">
              {formatDate(currentPeriodEnd)}
            </span>
          </div>

          {cancelAtPeriodEnd && (
            <div className="p-3 bg-yellow-600/10 dark:bg-yellow-600/20 rounded-control">
              <p className="text-xs text-yellow-600 dark:text-yellow-400">
                ⚠️ Your subscription will be canceled on{" "}
                {formatDate(currentPeriodEnd)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-2 border-t border-border dark:border-border-dark">
        {plan !== "free" && (
          <>
            <Button
              onClick={onManageBilling}
              loading={loading}
              disabled={loading}
              size="sm"
              variant="secondary"
              className="flex-1"
            >
              Manage Billing
            </Button>

            {!cancelAtPeriodEnd && (
              <Button
                onClick={() => setShowCancelConfirm(true)}
                disabled={loading}
                size="sm"
                variant="secondary"
                className="flex-1 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              >
                Cancel
              </Button>
            )}
          </>
        )}
      </div>

      {/* Cancel confirmation */}
      {showCancelConfirm && (
        <div className="p-4 bg-canvas-panel dark:bg-canvas-dark-panel rounded-control space-y-3">
          <p className="text-body text-ink dark:text-ink-dark">
            Are you sure you want to cancel? You'll lose access to premium
            features.
          </p>
          <div className="flex gap-2">
            <Button
              onClick={() => {
                setShowCancelConfirm(false);
                onCancel?.();
              }}
              loading={loading}
              disabled={loading}
              size="sm"
              variant="primary"
              className="flex-1"
            >
              Cancel Subscription
            </Button>
            <Button
              onClick={() => setShowCancelConfirm(false)}
              disabled={loading}
              size="sm"
              variant="secondary"
              className="flex-1"
            >
              Keep Plan
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
};
