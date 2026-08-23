/**
 * Admin Dashboard Overview Page
 *
 * High-level KPI cards and charts
 */

import React, { useEffect, useState } from "react";
import { format, subDays } from "date-fns";
import {
  Users,
  MessageSquare,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  Download,
} from "lucide-react";
import { AdminLayout } from "@/components/admin/AdminLayout";
import { DateRangePicker } from "@/components/admin/DateRangePicker";
import { StatCard } from "@/components/admin/StatCard";
import { adminAnalyticsApi } from "@/services/adminApi";

export const AdminOverview: React.FC = () => {
  const [dateRange, setDateRange] = useState({
    start_date: format(subDays(new Date(), 30), "yyyy-MM-dd"),
    end_date: format(new Date(), "yyyy-MM-dd"),
  });

  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await adminAnalyticsApi.getOverview(dateRange);
        setMetrics(response.data.data);
      } catch (err) {
        console.error("Failed to fetch overview metrics:", err);
        setError("Failed to load metrics");
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [dateRange]);

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-1">
              Platform overview and key metrics
            </p>
          </div>
          <div className="flex gap-4">
            <DateRangePicker value={dateRange} onChange={setDateRange} />
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2">
              <Download size={18} />
              Export
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        )}

        {/* KPI Cards */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Daily Active Users"
              value={metrics.dau?.toLocaleString() || 0}
              icon={Users}
              color="blue"
              change={metrics.dau_change}
            />
            <StatCard
              title="Messages Today"
              value={metrics.messages_today?.toLocaleString() || 0}
              icon={MessageSquare}
              color="green"
              change={metrics.messages_change}
            />
            <StatCard
              title="Tokens Used"
              value={`${(metrics.tokens_today / 1000000).toFixed(1)}M`}
              icon={TrendingUp}
              color="purple"
              change={metrics.tokens_change}
            />
            <StatCard
              title="AI Cost Today"
              value={`$${metrics.estimated_cost_today?.toFixed(2) || "0.00"}`}
              icon={DollarSign}
              color="orange"
              change={metrics.cost_change}
            />
          </div>
        )}

        {/* Secondary KPIs */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StatCard
              title="Monthly Active Users"
              value={metrics.mau?.toLocaleString() || 0}
              icon={Users}
              color="indigo"
            />
            <StatCard
              title="Paid Subscriptions"
              value={metrics.paid_subscriptions?.toLocaleString() || 0}
              icon={TrendingUp}
              color="emerald"
            />
            <StatCard
              title="Monthly Churn Rate"
              value={`${metrics.monthly_churn_rate?.toFixed(1) || "0.0"}%`}
              icon={AlertTriangle}
              color="red"
            />
          </div>
        )}

        {/* Charts placeholder */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold text-gray-900 mb-4">
              Daily Active Users
            </h3>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded">
              <p className="text-gray-500">Chart placeholder</p>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="font-bold text-gray-900 mb-4">Plan Distribution</h3>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded">
              <p className="text-gray-500">Chart placeholder</p>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default AdminOverview;
