/**
 * Admin Billing Management Page
 *
 * Manage user plans and issue refunds
 */

import React, { useState } from "react";
import { Search, CreditCard, AlertCircle } from "lucide-react";
import { AdminLayout } from "@/components/admin/AdminLayout";
import { adminBillingApi } from "@/services/adminApi";

interface BillingAction {
  type: "plan_change" | "refund" | null;
  userId: string | null;
}

export const AdminBilling: React.FC = () => {
  const [search, setSearch] = useState("");
  const [action, setAction] = useState<BillingAction>({
    type: null,
    userId: null,
  });

  // Form states
  const [newPlan, setNewPlan] = useState<"free" | "plus" | "pro">("free");
  const [refundAmount, setRefundAmount] = useState("");
  const [paymentIntentId, setPaymentIntentId] = useState("");
  const [refundReason, setRefundReason] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleChangePlan = async () => {
    if (!action.userId) return;

    try {
      setLoading(true);
      setError(null);
      await adminBillingApi.changePlan(action.userId, { plan: newPlan });
      setSuccess(`Plan changed to ${newPlan}`);
      resetForm();
    } catch (err) {
      console.error("Failed to change plan:", err);
      setError("Failed to change plan");
    } finally {
      setLoading(false);
    }
  };

  const handleRefund = async () => {
    if (!action.userId) return;

    try {
      setLoading(true);
      setError(null);
      await adminBillingApi.issueRefund(action.userId, {
        payment_intent_id: paymentIntentId,
        amount: refundAmount ? parseFloat(refundAmount) : undefined,
        reason: refundReason,
      });
      setSuccess("Refund processed successfully");
      resetForm();
    } catch (err) {
      console.error("Failed to issue refund:", err);
      setError("Failed to issue refund");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setAction({ type: null, userId: null });
    setNewPlan("free");
    setRefundAmount("");
    setPaymentIntentId("");
    setRefundReason("");
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Billing Management</h1>
          <p className="text-gray-600 mt-1">
            Manage user plans and process refunds
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 flex items-start gap-3">
            <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Error</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-700">
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - User search */}
          <div className="lg:col-span-2 space-y-6">
            {/* Search user */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold text-gray-900 mb-4">Select User</h3>
              <div className="relative">
                <Search
                  size={18}
                  className="absolute left-3 top-3 text-gray-400"
                />
                <input
                  type="text"
                  placeholder="Search by email or user ID..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600"
                />
              </div>
            </div>

            {/* Action cards */}
            {action.userId && (
              <>
                {action.type === "plan_change" && (
                  <div className="bg-white rounded-lg shadow p-6 space-y-4">
                    <h3 className="font-bold text-gray-900">Change User Plan</h3>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        New Plan
                      </label>
                      <div className="grid grid-cols-3 gap-3">
                        {(["free", "plus", "pro"] as const).map((plan) => (
                          <button
                            key={plan}
                            onClick={() => setNewPlan(plan)}
                            className={`p-3 rounded-lg border-2 font-medium capitalize transition-colors ${
                              newPlan === plan
                                ? "border-blue-600 bg-blue-50 text-blue-700"
                                : "border-gray-300 bg-white text-gray-700 hover:border-gray-400"
                            }`}
                          >
                            {plan}
                          </button>
                        ))}
                      </div>
                    </div>

                    <p className="text-sm text-gray-600">
                      For paid plans, this will synchronize with Stripe.
                      Downgrading to free will cancel the Stripe subscription at period end.
                    </p>

                    <div className="flex gap-2">
                      <button
                        onClick={handleChangePlan}
                        disabled={loading}
                        className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium"
                      >
                        {loading ? "Processing..." : "Change Plan"}
                      </button>
                      <button
                        onClick={resetForm}
                        className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {action.type === "refund" && (
                  <div className="bg-white rounded-lg shadow p-6 space-y-4">
                    <h3 className="font-bold text-gray-900">Issue Refund</h3>

                    <div className="bg-yellow-50 border border-yellow-200 rounded p-3 flex gap-2">
                      <AlertCircle size={18} className="text-yellow-600 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-yellow-700">
                        This will process a refund through Stripe. Ensure you have the correct payment intent ID.
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Payment Intent ID
                      </label>
                      <input
                        type="text"
                        placeholder="pi_..."
                        value={paymentIntentId}
                        onChange={(e) => setPaymentIntentId(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Refund Amount (optional)
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-2 text-gray-500">$</span>
                        <input
                          type="number"
                          placeholder="Leave empty for full refund"
                          value={refundAmount}
                          onChange={(e) => setRefundAmount(e.target.value)}
                          step="0.01"
                          min="0"
                          className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600"
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Leave empty to refund the full amount
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Reason
                      </label>
                      <textarea
                        placeholder="Customer request, technical issue, etc."
                        value={refundReason}
                        onChange={(e) => setRefundReason(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600"
                        rows={3}
                      />
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={handleRefund}
                        disabled={loading || !paymentIntentId}
                        className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors font-medium"
                      >
                        {loading ? "Processing..." : "Issue Refund"}
                      </button>
                      <button
                        onClick={resetForm}
                        className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Right sidebar - Quick actions */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="font-bold text-gray-900 mb-4">Actions</h3>
              <div className="space-y-3">
                <button
                  onClick={() =>
                    setAction({
                      type: action.type === "plan_change" ? null : "plan_change",
                      userId: action.userId || "temp",
                    })
                  }
                  className={`w-full px-4 py-3 rounded-lg border-2 font-medium transition-colors flex items-center gap-2 justify-center ${
                    action.type === "plan_change"
                      ? "border-blue-600 bg-blue-50 text-blue-700"
                      : "border-gray-300 bg-white text-gray-700 hover:border-gray-400"
                  }`}
                >
                  <CreditCard size={18} />
                  Change Plan
                </button>

                <button
                  onClick={() =>
                    setAction({
                      type: action.type === "refund" ? null : "refund",
                      userId: action.userId || "temp",
                    })
                  }
                  className={`w-full px-4 py-3 rounded-lg border-2 font-medium transition-colors flex items-center gap-2 justify-center ${
                    action.type === "refund"
                      ? "border-green-600 bg-green-50 text-green-700"
                      : "border-gray-300 bg-white text-gray-700 hover:border-gray-400"
                  }`}
                >
                  <CreditCard size={18} />
                  Issue Refund
                </button>
              </div>
            </div>

            {/* Info box */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 mb-2">Important</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Plan changes sync with Stripe</li>
                <li>• Refunds are processed immediately</li>
                <li>• All actions are audit logged</li>
                <li>• Requires explicit user selection</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default AdminBilling;
