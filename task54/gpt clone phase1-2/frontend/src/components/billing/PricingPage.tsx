import React, { useEffect, useState } from "react";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { PricingCard } from "./PricingCard";
import { UsageProgress } from "./UsageProgress";
import { BillingSection } from "./BillingSection";

export interface Plan {
  id: string;
  name: string;
  price_cents: number;
  currency: string;
  interval: string;
  daily_messages: number;
  description: string;
  features: string[];
  stripe_price_id?: string;
}

export interface UsageData {
  plan: string;
  daily_limit: number;
  used_today: number;
  remaining_today: number;
  percentage_used: number;
  reset_at: string;
}

export interface SubscriptionData {
  id: string;
  plan: string;
  status: string;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
  canceled_at?: string;
}

export const PricingPage: React.FC = () => {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [plansRes, usageRes, subRes] = await Promise.all([
        fetch("/api/billing/plans"),
        fetch("/api/billing/usage"),
        fetch("/api/billing/subscription"),
      ]);

      if (plansRes.ok) {
        setPlans(await plansRes.json());
      }
      if (usageRes.ok) {
        setUsage(await usageRes.json());
      }
      if (subRes.ok) {
        setSubscription(await subRes.json());
      }
    } catch (error) {
      console.error("Failed to fetch billing data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (planId: string) => {
    setUpgrading(planId);
    try {
      const response = await fetch("/api/billing/checkout-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: planId,
          success_url: window.location.origin + "/billing?success=true",
          cancel_url: window.location.origin + "/billing?cancelled=true",
        }),
      });

      if (response.ok) {
        const { checkout_url } = await response.json();
        window.location.href = checkout_url;
      }
    } catch (error) {
      console.error("Failed to create checkout session:", error);
    } finally {
      setUpgrading(null);
    }
  };

  const handleManageBilling = async () => {
    try {
      const response = await fetch("/api/billing/portal", { method: "POST" });
      if (response.ok) {
        const { portal_url } = await response.json();
        window.location.href = portal_url;
      }
    } catch (error) {
      console.error("Failed to open billing portal:", error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin w-8 h-8 border-4 border-accent-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-12 space-y-12">
      {/* Header */}
      <div className="text-center space-y-4">
        <h1 className="text-heading-xl font-bold text-ink dark:text-ink-dark">
          Simple, Transparent Pricing
        </h1>
        <p className="text-body text-ink-secondary dark:text-ink-secondary-dark max-w-2xl mx-auto">
          Choose the plan that fits your needs. Upgrade or downgrade anytime.
        </p>
      </div>

      {/* Current subscription section */}
      {subscription && (
        <div className="space-y-4">
          <h2 className="text-heading-sm font-semibold text-ink dark:text-ink-dark">
            Your Current Plan
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <BillingSection
              plan={subscription.plan}
              status={subscription.status}
              currentPeriodEnd={subscription.current_period_end}
              cancelAtPeriodEnd={subscription.cancel_at_period_end}
              onManageBilling={handleManageBilling}
            />
            {usage && (
              <Card className="p-6">
                <UsageProgress
                  used={usage.used_today}
                  limit={usage.daily_limit}
                  unit="messages"
                />
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Pricing cards */}
      <div className="space-y-4">
        <h2 className="text-heading-sm font-semibold text-ink dark:text-ink-dark">
          All Plans
        </h2>
        <div className="grid gap-6 md:grid-cols-3 lg:gap-8">
          {plans.map((plan) => (
            <PricingCard
              key={plan.id}
              planId={plan.id}
              name={plan.name}
              price={plan.price_cents}
              currency={plan.currency}
              interval={plan.interval}
              description={plan.description}
              features={plan.features}
              isPopular={plan.id === "plus"}
              isCurrentPlan={subscription?.plan === plan.id}
              onUpgrade={handleUpgrade}
              loading={upgrading === plan.id}
            />
          ))}
        </div>
      </div>

      {/* FAQ section */}
      <Card className="p-8 bg-canvas-panel dark:bg-canvas-dark-panel">
        <h2 className="text-heading-sm font-semibold text-ink dark:text-ink-dark mb-6">
          Frequently Asked Questions
        </h2>
        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-ink dark:text-ink-dark">
              Can I change my plan?
            </h3>
            <p className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
              Yes, you can upgrade or downgrade your plan anytime. Changes take
              effect immediately.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-ink dark:text-ink-dark">
              Do you offer refunds?
            </h3>
            <p className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
              We don't offer refunds, but you can cancel your subscription at
              any time with no penalty.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-ink dark:text-ink-dark">
              What happens when I reach my limit?
            </h3>
            <p className="text-meta text-ink-secondary dark:text-ink-secondary-dark mt-1">
              When you reach your daily message limit, you'll need to upgrade to
              a higher plan or wait until the next day.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
