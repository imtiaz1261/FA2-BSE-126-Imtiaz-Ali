/**
 * Admin Moderation Page
 *
 * Review and manage flagged conversations
 */

import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, XCircle, Eye } from "lucide-react";
import { AdminLayout } from "@/components/admin/AdminLayout";
import { adminModerationApi, ModerationFlag } from "@/services/adminApi";

export const AdminModeration: React.FC = () => {
  const [flags, setFlags] = useState<ModerationFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFlag, setSelectedFlag] = useState<ModerationFlag | null>(null);

  // Filters
  const [status, setStatus] = useState<string>("");
  const [severity, setSeverity] = useState<string>("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);

  // Actions
  const [approveNote, setApproveNote] = useState("");
  const [banReason, setBanReason] = useState("");

  useEffect(() => {
    const fetchQueue = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await adminModerationApi.getQueue({
          status: status || undefined,
          severity: severity || undefined,
          page,
          page_size: pageSize,
        });
        setFlags(response.data.items);
        setTotal(response.data.total);
      } catch (err) {
        console.error("Failed to fetch moderation queue:", err);
        setError("Failed to load moderation queue");
      } finally {
        setLoading(false);
      }
    };

    fetchQueue();
  }, [status, severity, page, pageSize]);

  const handleApprove = async () => {
    if (!selectedFlag) return;
    try {
      await adminModerationApi.approve(selectedFlag.id, { note: approveNote });
      setFlags(flags.filter((f) => f.id !== selectedFlag.id));
      setSelectedFlag(null);
      setApproveNote("");
    } catch (err) {
      console.error("Failed to approve flag:", err);
      setError("Failed to approve flag");
    }
  };

  const handleBan = async () => {
    if (!selectedFlag) return;
    try {
      await adminModerationApi.ban(selectedFlag.id, { reason: banReason });
      setFlags(flags.filter((f) => f.id !== selectedFlag.id));
      setSelectedFlag(null);
      setBanReason("");
    } catch (err) {
      console.error("Failed to ban user:", err);
      setError("Failed to ban user");
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-100 text-red-700";
      case "high":
        return "bg-orange-100 text-orange-700";
      case "medium":
        return "bg-yellow-100 text-yellow-700";
      case "low":
        return "bg-blue-100 text-blue-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  if (loading && flags.length === 0) {
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
          <h1 className="text-3xl font-bold text-gray-900">Moderation Queue</h1>
          <p className="text-gray-600 mt-1">
            Review and manage flagged conversations
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Queue list */}
          <div className="lg:col-span-2 bg-white rounded-lg shadow overflow-hidden">
            {/* Filters */}
            <div className="p-4 border-b border-gray-200 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <select
                  value={status}
                  onChange={(e) => {
                    setStatus(e.target.value);
                    setPage(1);
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="">All Status</option>
                  <option value="pending">Pending</option>
                  <option value="approved">Approved</option>
                  <option value="banned">Banned</option>
                </select>

                <select
                  value={severity}
                  onChange={(e) => {
                    setSeverity(e.target.value);
                    setPage(1);
                  }}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="">All Severity</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>

            {/* Flags list */}
            <div className="divide-y divide-gray-200">
              {flags.length > 0 ? (
                flags.map((flag) => (
                  <div
                    key={flag.id}
                    onClick={() => setSelectedFlag(flag)}
                    className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors border-l-4 ${
                      selectedFlag?.id === flag.id ? "bg-blue-50 border-blue-600" : "border-gray-200"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${getSeverityColor(flag.severity)}`}>
                            {flag.severity}
                          </span>
                          <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
                            {flag.category}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">
                          {flag.reason || "No reason provided"}
                        </p>
                        <p className="text-xs text-gray-500">
                          Flagged {new Date(flag.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <Eye size={18} className="text-gray-400" />
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-gray-500">
                  No flags in queue
                </div>
              )}
            </div>

            {/* Pagination */}
            {total > pageSize && (
              <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between text-sm">
                <p className="text-gray-600">
                  Showing {flags.length} of {total} flags
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 hover:bg-gray-50"
                  >
                    Previous
                  </button>
                  <span className="px-2 py-1 text-gray-600">
                    Page {page}
                  </span>
                  <button
                    onClick={() =>
                      setPage(Math.min(Math.ceil(total / pageSize), page + 1))
                    }
                    disabled={page === Math.ceil(total / pageSize)}
                    className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 hover:bg-gray-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Details panel */}
          <div className="bg-white rounded-lg shadow p-6 h-fit">
            {selectedFlag ? (
              <div className="space-y-4">
                <h3 className="font-bold text-gray-900">Flag Details</h3>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-600">
                    Category
                  </label>
                  <p className="text-gray-900">{selectedFlag.category}</p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-600">
                    Severity
                  </label>
                  <p className="text-gray-900 capitalize">
                    {selectedFlag.severity}
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-600">
                    Reason
                  </label>
                  <p className="text-gray-900 text-sm">
                    {selectedFlag.reason || "No reason provided"}
                  </p>
                </div>

                <div className="pt-4 space-y-3">
                  {selectedFlag.status === "pending" ? (
                    <>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-600">
                          Approval Note
                        </label>
                        <textarea
                          value={approveNote}
                          onChange={(e) => setApproveNote(e.target.value)}
                          placeholder="Add a note..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                          rows={3}
                        />
                      </div>

                      <button
                        onClick={handleApprove}
                        className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium flex items-center gap-2 justify-center"
                      >
                        <CheckCircle size={18} />
                        Approve
                      </button>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-600">
                          Ban Reason (if needed)
                        </label>
                        <textarea
                          value={banReason}
                          onChange={(e) => setBanReason(e.target.value)}
                          placeholder="Reason for ban..."
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                          rows={3}
                        />
                      </div>

                      <button
                        onClick={handleBan}
                        className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium flex items-center gap-2 justify-center"
                      >
                        <XCircle size={18} />
                        Ban User
                      </button>
                    </>
                  ) : (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-sm font-medium text-gray-900">
                        Status: {selectedFlag.status}
                      </p>
                      {selectedFlag.reviewed_at && (
                        <p className="text-xs text-gray-600 mt-1">
                          Reviewed{" "}
                          {new Date(selectedFlag.reviewed_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                <AlertTriangle size={32} className="mx-auto mb-2 opacity-50" />
                <p>Select a flag to review</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default AdminModeration;
