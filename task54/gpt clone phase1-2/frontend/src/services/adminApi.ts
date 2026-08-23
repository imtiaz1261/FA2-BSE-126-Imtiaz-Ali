/**
 * Admin API service
 *
 * Type-safe client for all admin endpoints:
 * - Analytics
 * - User management
 * - Billing
 * - Moderation
 */

import { apiClient } from "./apiClient";

export interface DateRange {
  start_date?: string;
  end_date?: string;
}

// Analytics types
export interface AnalyticsDataPoint {
  date: string;
  [key: string]: string | number;
}

export interface AnalyticsResponse {
  data: AnalyticsDataPoint[];
  total?: number;
  total_cost?: number;
}

export interface OverviewMetrics {
  dau: number;
  mau: number;
  messages_today: number;
  tokens_today: number;
  estimated_cost_today: number;
  paid_subscriptions: number;
  monthly_churn_rate: number;
  new_users_today: number;
}

export interface ModelPerformance {
  model: string;
  requests: number;
  success_rate: number;
  error_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost: number;
}

// User types
export interface UserListItem {
  id: string;
  email: string;
  name: string | null;
  plan: string;
  status: string;
  messages_used_today: number;
  joined_at: string;
  last_active_at: string | null;
  role: string;
}

export interface UserListResponse {
  items: UserListItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface UserDetailResponse {
  id: string;
  email: string;
  name: string | null;
  role: string;
  status: string;
  is_verified: boolean;
  joined_at: string;
  last_active_at: string | null;
  plan: string;
  subscription_status: string;
  renewal_date: string | null;
  stripe_customer_id: string | null;
  cancel_at_period_end: boolean;
  messages_today: number;
  messages_this_month: number;
  tokens_used: number;
  estimated_cost: number;
  agent_runs: number;
  rag_queries: number;
  recent_conversations: number;
  recent_messages: number;
}

export interface SuspendUserRequest {
  reason: string;
}

export interface BanUserRequest {
  reason: string;
}

export interface ChangePlanRequest {
  plan: "free" | "plus" | "pro";
}

export interface RefundRequest {
  payment_intent_id: string;
  amount?: number;
  reason: string;
}

// Moderation types
export interface ModerationFlag {
  id: string;
  conversation_id: string;
  user_id: string;
  category: string;
  severity: "low" | "medium" | "high" | "critical";
  reason: string | null;
  status: "pending" | "approved" | "banned" | "dismissed";
  created_at: string;
  reviewed_at: string | null;
}

export interface ModerationQueueResponse {
  items: ModerationFlag[];
  page: number;
  page_size: number;
  total: number;
}

export interface ModerationDetailsResponse {
  flag: ModerationFlag;
  user_email: string;
  user_name: string | null;
  conversation_title: string | null;
  message_count: number;
  recent_messages: Array<{
    id: string;
    role: string;
    content: string;
    created_at: string;
  }>;
}

export interface ApproveModerationRequest {
  note: string;
}

export interface BanModeratedUserRequest {
  reason: string;
}

// Analytics API
export const adminAnalyticsApi = {
  getOverview: (dateRange?: DateRange) =>
    apiClient.get<{ data: OverviewMetrics; period: DateRange }>(
      "/api/v1/admin/analytics/overview",
      { params: dateRange }
    ),

  getActiveUsers: (dateRange?: DateRange) =>
    apiClient.get<AnalyticsResponse>(
      "/api/v1/admin/analytics/active-users",
      { params: dateRange }
    ),

  getMessages: (dateRange?: DateRange) =>
    apiClient.get<AnalyticsResponse>("/api/v1/admin/analytics/messages", {
      params: dateRange,
    }),

  getTokens: (dateRange?: DateRange) =>
    apiClient.get<AnalyticsResponse>("/api/v1/admin/analytics/tokens", {
      params: dateRange,
    }),

  getCost: (dateRange?: DateRange) =>
    apiClient.get<AnalyticsResponse & { period: DateRange }>(
      "/api/v1/admin/analytics/cost",
      { params: dateRange }
    ),

  getPlanDistribution: () =>
    apiClient.get<AnalyticsResponse>("/api/v1/admin/analytics/plans"),

  getChurn: (dateRange?: DateRange) =>
    apiClient.get<AnalyticsResponse>("/api/v1/admin/analytics/churn", {
      params: dateRange,
    }),

  getRetention: (dateRange?: DateRange) =>
    apiClient.get<{ cohorts: AnalyticsDataPoint[]; period: DateRange }>(
      "/api/v1/admin/analytics/retention",
      { params: dateRange }
    ),

  getModelPerformance: (dateRange?: DateRange) =>
    apiClient.get<{ models: ModelPerformance[] }>(
      "/api/v1/admin/analytics/models",
      { params: dateRange }
    ),
};

// User management API
export const adminUsersApi = {
  listUsers: (params: {
    search?: string;
    plan?: string;
    status?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
    sort?: string;
    order?: string;
  }) =>
    apiClient.get<UserListResponse>("/api/v1/admin/users", { params }),

  getUserDetails: (userId: string) =>
    apiClient.get<UserDetailResponse>(`/api/v1/admin/users/${userId}`),

  suspendUser: (userId: string, data: SuspendUserRequest) =>
    apiClient.post(`/api/v1/admin/users/${userId}/suspend`, data),

  unsuspendUser: (userId: string) =>
    apiClient.post(`/api/v1/admin/users/${userId}/unsuspend`, {}),

  banUser: (userId: string, data: BanUserRequest) =>
    apiClient.post(`/api/v1/admin/users/${userId}/ban`, data),

  changePlan: (userId: string, data: ChangePlanRequest) =>
    apiClient.post(`/api/v1/admin/users/${userId}/plan`, data),
};

// Billing API
export const adminBillingApi = {
  changePlan: (userId: string, data: ChangePlanRequest) =>
    apiClient.post(`/api/v1/admin/billing/users/${userId}/plan`, data),

  issueRefund: (userId: string, data: RefundRequest) =>
    apiClient.post(`/api/v1/admin/billing/users/${userId}/refund`, data),
};

// Moderation API
export const adminModerationApi = {
  getQueue: (params: {
    status?: string;
    severity?: string;
    category?: string;
    page?: number;
    page_size?: number;
  }) =>
    apiClient.get<ModerationQueueResponse>("/api/v1/admin/moderation", {
      params,
    }),

  getDetails: (flagId: string) =>
    apiClient.get<ModerationDetailsResponse>(
      `/api/v1/admin/moderation/${flagId}`
    ),

  approve: (flagId: string, data: ApproveModerationRequest) =>
    apiClient.post(`/api/v1/admin/moderation/${flagId}/approve`, data),

  ban: (flagId: string, data: BanModeratedUserRequest) =>
    apiClient.post(`/api/v1/admin/moderation/${flagId}/ban`, data),
};

export default {
  analytics: adminAnalyticsApi,
  users: adminUsersApi,
  billing: adminBillingApi,
  moderation: adminModerationApi,
};
