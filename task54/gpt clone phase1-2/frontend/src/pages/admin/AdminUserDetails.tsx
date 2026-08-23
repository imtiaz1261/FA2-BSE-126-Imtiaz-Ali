/**
 * Admin User Details Page
 *
 * View and manage individual user account
 */

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Mail,
  Calendar,
  Zap,
  Shield,
  Lock,
  CreditCard,
  AlertTriangle,
} from "lucide-react";
import { AdminLayout } from "@/components/admin/AdminLayout";
import { adminUsersApi, UserDetailResponse } from "@/services/adminApi";

export const AdminUserDetails: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [user, setUser] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    "account" | "subscription" | "usage" | "activity"
  >("account");

  useEffect(() => {
    if (!userId) return;

    const fetchUser = async () => {
      try {
        setLoading(true);
        const response = await adminUsersApi.getUserDetails(userId);
        setUser(response.data);
      } catch (err) {
        console.error("Failed to fetch user:", err);
        setError("Failed to load user details");
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [userId]);

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      </AdminLayout>
    );
  }

  if (!user) {
    return (
      <AdminLayout>
        <div className="text-center py-12">
          <p className="text-gray-600">User not found</p>
          <button
            onClick={() => navigate("/admin/users")}
            className="mt-4 text-blue-600 hover:text-blue-700"
          >
            Back to Users
          </button>
        </div>
      </AdminLayout>
    );
  }

  const tabs = [
    { id: "account", label: "Account" },
    { id: "subscription", label: "Subscription" },
    { id: "usage", label: "Usage" },
    { id: "activity", label: "Activity" },
  ];

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/admin/users")}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {user.name || "Unknown"}
            </h1>
            <p className="text-gray-600">{user.email}</p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        )}

        {/* Status badges */}
        <div className="flex gap-2">
          <span
            className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
              user.status === "active"
                ? "bg-green-100 text-green-700"
                : user.status === "suspended"
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-red-100 text-red-700"
            }`}
          >
            {user.status}
          </span>
          <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700">
            {user.plan}
          </span>
          {user.role === "admin" && (
            <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-700">
              Admin
            </span>
          )}
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 flex gap-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() =>
                setActiveTab(tab.id as "account" | "subscription" | "usage" | "activity")
              }
              className={`px-1 py-2 font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {activeTab === "account" && (
              <div className="bg-white rounded-lg shadow p-6 space-y-4">
                <h3 className="text-lg font-bold">Account Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      User ID
                    </label>
                    <p className="text-gray-900 font-mono">{user.id}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Email
                    </label>
                    <p className="text-gray-900">{user.email}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Name
                    </label>
                    <p className="text-gray-900">{user.name || "-"}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Role
                    </label>
                    <p className="text-gray-900">{user.role}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Joined
                    </label>
                    <p className="text-gray-900">
                      {new Date(user.joined_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Last Active
                    </label>
                    <p className="text-gray-900">
                      {user.last_active_at
                        ? new Date(user.last_active_at).toLocaleDateString()
                        : "Never"}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "subscription" && (
              <div className="bg-white rounded-lg shadow p-6 space-y-4">
                <h3 className="text-lg font-bold">Subscription</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Current Plan
                    </label>
                    <p className="text-gray-900 font-bold">{user.plan}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">
                      Status
                    </label>
                    <p className="text-gray-900">{user.subscription_status}</p>
                  </div>
                  {user.renewal_date && (
                    <div>
                      <label className="text-sm font-medium text-gray-600">
                        Renewal Date
                      </label>
                      <p className="text-gray-900">
                        {new Date(user.renewal_date).toLocaleDateString()}
                      </p>
                    </div>
                  )}
                  {user.stripe_customer_id && (
                    <div>
                      <label className="text-sm font-medium text-gray-600">
                        Stripe Customer
                      </label>
                      <p className="text-gray-900 font-mono text-sm">
                        {user.stripe_customer_id}
                      </p>
                    </div>
                  )}
                </div>
                {user.cancel_at_period_end && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded p-3 flex gap-2">
                    <AlertTriangle size={18} className="text-yellow-600" />
                    <p className="text-sm text-yellow-700">
                      This subscription is scheduled to cancel at the end of the current period
                    </p>
                  </div>
                )}
              </div>
            )}

            {activeTab === "usage" && (
              <div className="bg-white rounded-lg shadow p-6 space-y-4">
                <h3 className="text-lg font-bold">Usage</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 rounded p-4">
                    <label className="text-sm font-medium text-gray-600">
                      Messages Today
                    </label>
                    <p className="text-2xl font-bold text-blue-600">
                      {user.messages_today}
                    </p>
                  </div>
                  <div className="bg-green-50 rounded p-4">
                    <label className="text-sm font-medium text-gray-600">
                      Messages This Month
                    </label>
                    <p className="text-2xl font-bold text-green-600">
                      {user.messages_this_month}
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded p-4">
                    <label className="text-sm font-medium text-gray-600">
                      Tokens Used
                    </label>
                    <p className="text-2xl font-bold text-purple-600">
                      {(user.tokens_used / 1000000).toFixed(1)}M
                    </p>
                  </div>
                  <div className="bg-orange-50 rounded p-4">
                    <label className="text-sm font-medium text-gray-600">
                      Estimated Cost
                    </label>
                    <p className="text-2xl font-bold text-orange-600">
                      ${user.estimated_cost.toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-indigo-50 rounded p-4">
                    <label className="text-sm font-medium text-gray-600">
                      Agent Runs
                    </label>
                    <p className="text-2xl font-bold text-indigo-600">
                      {user.agent_runs}
                    </p>
                  </div>
                  <div className="bg-emerald-50 rounded p-4">
                    <label className="text-sm font-medium text-gray-600">
                      RAG Queries
                    </label>
                    <p className="text-2xl font-bold text-emerald-600">
                      {user.rag_queries}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "activity" && (
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-bold mb-4">Recent Activity</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 border-b border-gray-200">
                    <div>
                      <p className="font-medium text-gray-900">
                        {user.recent_conversations} Recent Conversations
                      </p>
                      <p className="text-sm text-gray-600">
                        Active chat threads
                      </p>
                    </div>
                    <span className="text-2xl font-bold text-gray-400">
                      {user.recent_conversations}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3">
                    <div>
                      <p className="font-medium text-gray-900">
                        {user.recent_messages} Recent Messages
                      </p>
                      <p className="text-sm text-gray-600">
                        Total messages sent
                      </p>
                    </div>
                    <span className="text-2xl font-bold text-gray-400">
                      {user.recent_messages}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar actions */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow p-6 space-y-3">
              <h3 className="font-bold text-gray-900">Admin Actions</h3>
              {user.status === "active" ? (
                <button className="w-full px-4 py-2 border border-yellow-300 bg-yellow-50 text-yellow-700 rounded-lg hover:bg-yellow-100 transition-colors font-medium flex items-center gap-2 justify-center">
                  <Lock size={18} />
                  Suspend User
                </button>
              ) : (
                <button className="w-full px-4 py-2 border border-green-300 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors font-medium">
                  Unsuspend User
                </button>
              )}

              {user.status !== "banned" && (
                <button className="w-full px-4 py-2 border border-red-300 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors font-medium flex items-center gap-2 justify-center">
                  <AlertTriangle size={18} />
                  Ban User
                </button>
              )}

              <button className="w-full px-4 py-2 border border-blue-300 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors font-medium flex items-center gap-2 justify-center">
                <CreditCard size={18} />
                Change Plan
              </button>

              <button className="w-full px-4 py-2 border border-green-300 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors font-medium">
                Issue Refund
              </button>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default AdminUserDetails;
