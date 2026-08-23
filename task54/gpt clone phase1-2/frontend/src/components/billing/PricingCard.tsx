import React from "react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";

export interface PlanFeature {
  id: string;
  label: string;
  included: boolean;
}

export interface PricingCardProps {
  planId: string;
  name: string;
  price: number;
  currency: string;
  interval: string;
  description: string;
  features: string[];
  isPopular?: boolean;
  isCurrentPlan?: boolean;
  onUpgrade?: (planId: string) => void;
  loading?: boolean;
}

export const PricingCard: React.FC<PricingCardProps> = ({
  planId,
  name,
  price,
  currency,
  interval,
  description,
  features,
  isPopular = false,
  isCurrentPlan = false,
  onUpgrade,
  loading = false,
}) => {
  const displayPrice = price / 100; // Convert cents to dollars
  const formattedPrice = displayPrice.toFixed(2);

  return (
    <Card
      className={cn(
        "relative p-6 flex flex-col transition-all",
        isPopular && "ring-2 ring-accent-600 dark:ring-accent-400 lg:scale-105",
        !isPopular && "hover:border-accent-600/50 dark:hover:border-accent-400/50"
      )}
    >
      {/* Popular badge */}
      {isPopular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-accent-600 text-white px-3 py-1 rounded-full text-xs font-semibold">
            Most Popular
          </span>
        </div>
      )}

      {/* Plan name and description */}
      <div className="mb-6">
        <h3 className="text-heading-sm font-bold text-ink dark:text-ink-dark">
          {name}
        </h3>
        <p className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
          {description}
        </p>
      </div>

      {/* Price */}
      <div className="mb-6">
        {price === 0 ? (
          <p className="text-heading font-bold text-ink dark:text-ink-dark">
            Free
          </p>
        ) : (
          <div className="flex items-baseline gap-1">
            <span className="text-heading font-bold text-ink dark:text-ink-dark">
              {currency}
              {formattedPrice}
            </span>
            <span className="text-body text-ink-secondary dark:text-ink-secondary-dark">
              /{interval}
            </span>
          </div>
        )}
      </div>

      {/* CTA Button */}
      <Button
        onClick={() => onUpgrade?.(planId)}
        loading={loading}
        disabled={isCurrentPlan || loading}
        variant={isPopular ? "primary" : "secondary"}
        className="w-full mb-6"
      >
        {isCurrentPlan ? "✓ Current Plan" : "Upgrade"}
      </Button>

      {/* Features list */}
      <div className="space-y-3 flex-1">
        {features.map((feature) => (
          <div key={feature} className="flex items-start gap-2">
            <span className="text-accent-600 dark:text-accent-400 mt-0.5">✓</span>
            <span className="text-meta text-ink dark:text-ink-dark">{feature}</span>
          </div>
        ))}
      </div>
    </Card>
  );
};
