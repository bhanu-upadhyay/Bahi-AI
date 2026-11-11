"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { CheckSquare, CheckCircle, XCircle, Clock, ArrowUpRight, RefreshCw } from "lucide-react";
import { api } from "@/services/api";
import { Approval } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTime } from "@/lib/utils";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("PENDING");

  const loadData = () => {
    setLoading(true);
    api
      .getApprovals(statusFilter || undefined)
      .then((data) => {
        setApprovals(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleAction = async (approvalId: number, status: "APPROVED" | "REJECTED") => {
    const comments = prompt(`Enter optional review comments for ${status.toLowerCase()}:`, "") || undefined;
    try {
      await api.actOnApproval(approvalId, { status, comments });
      loadData();
    } catch (e: any) {
      alert(`Error updating approval: ${e.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <CheckSquare className="h-5 w-5 text-sky-600" />
            <span>Multi-Level Approvals Queue</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Stage-gate authorization for university expenditures (HOD, Finance Officer, Finance Admin)
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-700 focus:outline-none"
          >
            <option value="">All Approvals</option>
            <option value="PENDING">Pending Review</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>
          <button
            onClick={loadData}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {loading ? (
          <TableSkeleton rows={4} />
        ) : approvals.length === 0 ? (
          <EmptyState
            title="No approvals found"
            description="There are currently no tasks matching your selected approval status filter."
          />
        ) : (
          approvals.map((app) => (
            <div
              key={app.id}
              className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm space-y-3 hover:border-slate-300 transition"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-sky-50 text-sky-800 border border-sky-100">
                    Stage {app.approval_level}
                  </span>
                  <span className="text-xs font-semibold text-slate-900">
                    Invoice #{app.invoice_id}
                  </span>
                  <span className="text-xs text-slate-500">
                    Assigned Approver: <strong className="text-slate-700">{app.approver?.full_name}</strong> ({app.approver?.role?.replace("_", " ")})
                  </span>
                </div>
                <StatusBadge status={app.status} type="approval" />
              </div>

              {app.comments && (
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs text-slate-700">
                  <span className="font-semibold text-slate-500 block text-[10px] uppercase">Notes:</span>
                  &quot;{app.comments}&quot;
                </div>
              )}

              <div className="flex items-center justify-between pt-2 text-[11px] text-slate-400">
                <span>
                  {app.decided_at
                    ? `Decided on: ${formatDateTime(app.decided_at)}`
                    : `Created: ${formatDateTime(app.created_at)}`}
                </span>
                <div className="flex items-center space-x-3">
                  <Link
                    href={`/invoices/${app.invoice_id}`}
                    className="text-sky-600 hover:text-sky-800 font-semibold flex items-center space-x-1"
                  >
                    <span>View Invoice</span>
                    <ArrowUpRight className="h-3 w-3" />
                  </Link>

                  {app.status === "PENDING" && (
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleAction(app.id, "APPROVED")}
                        className="inline-flex items-center space-x-1 px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs shadow-sm transition"
                      >
                        <CheckCircle className="h-3.5 w-3.5" />
                        <span>Approve</span>
                      </button>
                      <button
                        onClick={() => handleAction(app.id, "REJECTED")}
                        className="inline-flex items-center space-x-1 px-3 py-1 rounded bg-rose-600 hover:bg-rose-700 text-white font-medium text-xs shadow-sm transition"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        <span>Reject</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

