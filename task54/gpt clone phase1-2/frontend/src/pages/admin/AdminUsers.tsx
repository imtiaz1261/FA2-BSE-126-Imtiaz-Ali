/**
 * Admin Users Management Page
 *
 * Search, filter, and manage users
 */

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Filter, ChevronRight, MoreVertical } from "lucide-react";
import { AdminLayout } from "@/components/admin/AdminLayout";
import { adminUsersApi, UserListResponse } from "@/services/adminApi";

export const AdminUsers: React.FC = () => {
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [plan, setPlan] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await adminUsersApi.listUsers({
          search: search || undefined,
          plan: plan || undefined,
          status: status || undefined,
          page,
          page_size: pageSize,
        });
        setUsers(response.data);
      } catch (err) {
        console.error("Failed to fetch users:", err);
        setError("Failed to load users");
      } finally {
        setLoading(false);
      }
    };

    const debounceTimer = setTimeout(fetchUsers, 500);
    return () => clearTimeout(debounceTimer);
  }, [search, plan, status, page, pageSize]);

  const handleViewUser = (userId: string) => {
    navigate(`/admin/users/${userId}`);
  };

  if (loading && !users) {
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
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
          <p className="text-gray-600 mt-1">Search and manage user accounts</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search
                size={18}
                className="absolute left-3 top-3 text-gray-400"
              />
              <input
                type="text"
                placeholder="Search by email or name..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600"
              />
            </div>

            {/* Plan filter */}
            <select
              value={plan}
              onChange={(e) => {
                setPlan(e.target.value);
                setPage(1);
              }}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600"
            >
              <option value="">All Plans</option>
              <option value="free">Free</option>
              <option value="plus">Plus</option>
              <option value="pro">Pro</option>
            </select>

            {/* Status filter */}
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-600"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
              <option value="banned">Banned</option>
            </select>

            {/* Filter button */}
            <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2">
              <Filter size={18} />
              More Filters
            </button>
          </div>
        </div>

        {/* Users table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {users && users.items.length > 0 ? (
            <>
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                      User
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                      Plan
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                      Usage Today
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                      Joined
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                      Last Active
                    </th>
                    <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {users.items.map((user) => (
                    <tr
                      key={user.id}
                      className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-gray-900">
                            {user.name || "Unknown"}
                          </p>
                          <p className="text-sm text-gray-600">{user.email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700">
                          {user.plan}
                        </span>
                      </td>
                      <td className="px-6 py-4">
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
                      </td>
                      <td className="px-6 py-4 text-gray-900">
                        {user.messages_used_today} messages
                      </td>
                      <td className="px-6 py-4 text-gray-600">
                        {new Date(user.joined_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-gray-600">
                        {user.last_active_at
                          ? new Date(user.last_active_at).toLocaleDateString()
                          : "Never"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleViewUser(user.id)}
                            className="p-2 hover:bg-gray-100 rounded transition-colors"
                          >
                            <ChevronRight size={18} />
                          </button>
                          <button className="p-2 hover:bg-gray-100 rounded transition-colors">
                            <MoreVertical size={18} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  Showing {users.items.length} of {users.total} users
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50 transition-colors"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2">
                    Page {page} of{" "}
                    {Math.ceil((users.total || 0) / pageSize)}
                  </span>
                  <button
                    onClick={() =>
                      setPage(
                        Math.min(
                          Math.ceil((users.total || 0) / pageSize),
                          page + 1
                        )
                      )
                    }
                    disabled={
                      page === Math.ceil((users.total || 0) / pageSize)
                    }
                    className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 hover:bg-gray-50 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-gray-500">
              No users found
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
};

export default AdminUsers;
