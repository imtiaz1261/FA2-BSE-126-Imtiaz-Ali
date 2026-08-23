/**
 * Admin Layout Component
 *
 * Main layout for admin dashboard with sidebar navigation
 */

import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  BarChart3,
  Users,
  AlertCircle,
  Settings,
  LogOut,
  Menu,
  X,
} from "lucide-react";

interface AdminLayoutProps {
  children: React.ReactNode;
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({ children }) => {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navItems = [
    { path: "/admin", label: "Overview", icon: BarChart3 },
    { path: "/admin/analytics", label: "Analytics", icon: BarChart3 },
    { path: "/admin/users", label: "Users", icon: Users },
    { path: "/admin/moderation", label: "Moderation", icon: AlertCircle },
    { path: "/admin/billing", label: "Billing", icon: Settings },
  ];

  const isActive = (path: string) => {
    if (path === "/admin") {
      return location.pathname === "/admin";
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? "w-64" : "w-20"
        } bg-gray-900 text-white transition-all duration-300 flex flex-col`}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-800 flex items-center justify-between">
          {sidebarOpen && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="font-bold">A</span>
              </div>
              <span className="font-bold text-lg">Admin</span>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover:bg-gray-800 rounded transition-colors"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
                  isActive(item.path)
                    ? "bg-blue-600 text-white"
                    : "text-gray-300 hover:bg-gray-800"
                }`}
                title={!sidebarOpen ? item.label : ""}
              >
                <Icon size={20} />
                {sidebarOpen && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-800">
          <button className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-gray-300 hover:bg-gray-800 transition-colors">
            <LogOut size={20} />
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="bg-white border-b border-gray-200 px-8 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-auto">
          <div className="p-8">{children}</div>
        </div>
      </div>
    </div>
  );
};

export default AdminLayout;
