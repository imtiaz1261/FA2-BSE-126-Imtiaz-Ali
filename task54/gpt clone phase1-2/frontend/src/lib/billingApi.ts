/**
 * Frontend API client for billing endpoints.
 * Type-safe interface to backend billing service.
 */

// Types
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
  user_id: string;
  plan: string;
  status: string;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
  canceled_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CheckoutSessionRequest {
  plan: "plus" | "pro";
  success_url?: string;
  cancel_url?: string;
}

export interface CheckoutSessionResponse {
  session_id: string;
  checkout_url: string;
}

export interface PortalSessionResponse {
  portal_url: string;
}

export interface WebhookEventResponse {
  id: string;
  type: string;
  processed: boolean;
  message: string;
}

// API Client
class BillingApi {
  private baseUrl = "/api/billing";

  /**
   * Get all available subscription plans.
   */
  async getPlans(): Promise<Plan[]> {
    const response = await fetch(`${this.baseUrl}/plans`);
    if (!response.ok) {
      throw new Error(`Failed to fetch plans: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get current user's usage data.
   */
  async getUsage(): Promise<UsageData> {
    const response = await fetch(`${this.baseUrl}/usage`);
    if (!response.ok) {
      throw new Error(`Failed to fetch usage: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get current user's subscription details.
   */
  async getSubscription(): Promise<SubscriptionData> {
    const response = await fetch(`${this.baseUrl}/subscription`);
    if (!response.ok) {
      throw new Error(`Failed to fetch subscription: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Create a Stripe Checkout session.
   * Redirects to Stripe Checkout when successful.
   */
  async createCheckoutSession(
    request: CheckoutSessionRequest
  ): Promise<CheckoutSessionResponse> {
    const response = await fetch(`${this.baseUrl}/checkout-session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to create checkout session");
    }

    return response.json();
  }

  /**
   * Create a Stripe Customer Portal session.
   * Redirects to Stripe Customer Portal when successful.
   */
  async createPortalSession(): Promise<PortalSessionResponse> {
    const response = await fetch(`${this.baseUrl}/portal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to create portal session");
    }

    return response.json();
  }

  /**
   * Upgrade to a specific plan.
   * Opens Stripe Checkout.
   */
  async upgradePlan(
    planId: "plus" | "pro",
    successUrl?: string,
    cancelUrl?: string
  ): Promise<void> {
    const sessionResponse = await this.createCheckoutSession({
      plan: planId,
      success_url: successUrl,
      cancel_url: cancelUrl,
    });

    // Redirect to Stripe Checkout
    window.location.href = sessionResponse.checkout_url;
  }

  /**
   * Open Stripe Customer Portal for plan management.
   */
  async manageBilling(): Promise<void> {
    const sessionResponse = await this.createPortalSession();

    // Redirect to Stripe Customer Portal
    window.location.href = sessionResponse.portal_url;
  }

  /**
   * Check if user is on trial.
   */
  async isOnTrial(): Promise<boolean> {
    try {
      const subscription = await this.getSubscription();
      return subscription.status === "trialing";
    } catch {
      return false;
    }
  }

  /**
   * Check if user has reached daily quota.
   */
  async hasReachedQuota(): Promise<boolean> {
    try {
      const usage = await this.getUsage();
      return usage.used_today >= usage.daily_limit;
    } catch {
      return false;
    }
  }

  /**
   * Get plan by ID.
   */
  async getPlan(planId: string): Promise<Plan | null> {
    try {
      const plans = await this.getPlans();
      return plans.find((p) => p.id === planId) || null;
    } catch {
      return null;
    }
  }

  /**
   * Check if user can send more messages today.
   */
  async canSendMessage(): Promise<{ can_send: boolean; reason?: string }> {
    try {
      const usage = await this.getUsage();
      const canSend = usage.used_today < usage.daily_limit;

      if (!canSend) {
        return {
          can_send: false,
          reason: `Daily limit (${usage.daily_limit} messages) reached. Resets at ${usage.reset_at}`,
        };
      }

      return { can_send: true };
    } catch (error) {
      console.error("Failed to check message quota:", error);
      // On error, allow message to go through
      return { can_send: true };
    }
  }
}

// Export singleton instance
export const billingApi = new BillingApi();
