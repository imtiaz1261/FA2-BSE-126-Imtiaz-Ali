/**
 * Stat Card Component
 *
 * Displays a single KPI with icon, title, value, and optional trend
 */

import React from "lucide-react";
import { TrendingUp, TrendingDown } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<{ size: number }>;
  color?: "blue" | "green" | "purple" | "orange" | "indigo" | "emerald" | "red";
  change?: number;
  changeLabel?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon: Icon,
  color = "blue",
  change,
  changeLabel = "vs previous period",
}) => {
  const colorClasses = {
    blue: {
      bg: "bg-blue-50",
      border: "border-blue-200",
      icon: "text-blue-600",
      badge: "bg-blue-100 text-blue-700",
    },
    green: {
      bg: "bg-green-50",
      border: "border-green-200",
      icon: "text-green-600",
      badge: "bg-green-100 text-green-700",
    },
    purple: {
      bg: "bg-purple-50",
      border: "border-purple-200",
      icon: "text-purple-600",
      badge: "bg-purple-100 text-purple-700",
    },
    orange: {
      bg: "bg-orange-50",
      border: "border-orange-200",
      icon: "text-orange-600",
      badge: "bg-orange-100 text-orange-700",
    },
    indigo: {
      bg: "bg-indigo-50",
      border: "border-indigo-200",
      icon: "text-indigo-600",
      badge: "bg-indigo-100 text-indigo-700",
    },
    emerald: {
      bg: "bg-emerald-50",
      border: "border-emerald-200",
      icon: "text-emerald-600",
      badge: "bg-emerald-100 text-emerald-700",
    },
    red: {
      bg: "bg-red-50",
      border: "border-red-200",
      icon: "text-red-600",
      badge: "bg-red-100 text-red-700",
    },
  };

  const styles = colorClasses[color];

  return (
    <div className={`${styles.bg} border ${styles.border} rounded-lg p-6`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {change !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              {change >= 0 ? (
                <TrendingUp size={16} className="text-green-600" />
              ) : (
                <TrendingDown size={16} className="text-red-600" />
              )}
              <span
                className={`text-sm font-medium ${
                  change >= 0 ? "text-green-700" : "text-red-700"
                }`}
              >
                {change >= 0 ? "+" : ""}
                {change.toFixed(1)}%
              </span>
              <span className="text-xs text-gray-600">{changeLabel}</span>
            </div>
          )}
        </div>
        <div className={`${styles.icon} p-3 bg-white rounded-lg`}>
          <Icon size={24} />
        </div>
      </div>
    </div>
  );
};

export default StatCard;
