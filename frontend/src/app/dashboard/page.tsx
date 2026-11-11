"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Clock,
  AlertTriangle,
  CreditCard,
  TrendingUp,
  PieChart,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  Calendar,
  Building2,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/services/api";
import { DashboardSummary } from "@/types";
import { KPICard } from "@/components/ui/KPICard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/utils";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDashboardSummary()
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load dashboard summary");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-96 rounded-xl lg:col-span-2" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <EmptyState
        title="Unable to connect to Bahi-AI Backend"
        description={error || "Ensure the FastAPI server is running on port 8000 and PostgreSQL is healthy."}
        actionText="Retry Connection"
        onAction={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Banner Context */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-slate-700/60">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-sky-400 uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-sky-400"></span>
            <span>University Finance & AP Operations</span>
          </div>
          <h2 className="text-xl font-bold tracking-tight">
            Campus Accounts Payable Executive Control
          </h2>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl">
            Live telemetry connected to PostgreSQL database. 3-way invoice matching, fraud screening, and departmental budget controls active for FY 2024–2025.
          </p>
        </div>
        <div className="flex items-center space-x-3 flex-shrink-0">
          <Link
            href="/invoices"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-sm transition"
          >
            <span>Process Invoices</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/fraud"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-600 transition"
          >
            <ShieldAlert className="h-4 w-4 text-amber-400" />
            <span>Exceptions ({data.exceptions_detected})</span>
          </Link>
        </div>
      </div>

      {/* Primary KPI Grid (All Backend Backed) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Invoices"
          value={data.total_invoices}
          subtitle="Processed in FY 2024-25"
          icon={<FileText className="h-5 w-5 text-sky-600" />}
          trend={{ value: `${data.workflow_status_counts["MATCHED"] || 0} Matched`, isPositive: true }}
        />
        <KPICard
          title="Pending Approvals"
          value={data.pending_approvals}
          subtitle="HOD & Finance Sign-Off"
          variant="alert"
          icon={<Clock className="h-5 w-5 text-amber-600" />}
          trend={{ value: `${data.invoices_under_review} in review` }}
        />
        <KPICard
          title="Exceptions & Fraud"
          value={data.exceptions_detected}
          subtitle="Anomalies flagged"
          variant={data.exceptions_detected > 0 ? "alert" : "default"}
          icon={<AlertTriangle className="h-5 w-5 text-rose-600" />}
          trend={{ value: "Strict Screening" }}
        />
        <KPICard
          title="Total Payable"
          value={formatCurrency(data.total_payable_amount)}
          subtitle={`${formatCurrency(data.scheduled_payments_amount)} scheduled`}
          variant="success"
          icon={<CreditCard className="h-5 w-5 text-emerald-600" />}
          trend={{ value: "Disbursements" }}
        />
      </div>

      {/* Main Section: Department Budget Utilization & Workflow Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Department Budgets */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200/90 p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center space-x-2">
                <PieChart className="h-4 w-4 text-sky-600" />
                <span>Department Budget Utilization (FY 2024–2025)</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Overall University Budget Allocation: {formatCurrency(data.total_budget_allocated)} • Spent & Committed: {data.overall_budget_utilization}%
              </p>
            </div>
            <Link
              href="/budgets"
              className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center space-x-1"
            >
              <span>View All</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="mt-5 space-y-4">
            {data.department_budgets.map((dept) => {
              const util = dept.utilization_percentage;
              let barColor = "bg-sky-600";
              if (util > 80) barColor = "bg-rose-500";
              else if (util > 60) barColor = "bg-amber-500";

              return (
                <div key={dept.department_id} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-800">
                      {dept.department_name} ({dept.department_code})
                    </span>
                    <span className="font-medium text-slate-500">
                      {formatCurrency(dept.spent_amount)} spent / {formatCurrency(dept.allocated_amount)} ({util}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-2.5 rounded-full ${barColor} transition-all duration-500`}
                      style={{ width: `${Math.min(util, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-400">
                    <span>Committed: {formatCurrency(dept.committed_amount)}</span>
                    <span className="text-emerald-600 font-medium">
                      Available: {formatCurrency(dept.available_amount)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Workflow Status Breakdown */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center space-x-2 pb-4 border-b border-slate-100">
              <TrendingUp className="h-4 w-4 text-sky-600" />
              <span>AP Pipeline Status</span>
            </h3>

            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-50/70 border border-emerald-100">
                <div className="flex items-center space-x-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                  <span className="text-xs font-semibold text-emerald-900">Matched (3-Way Validated)</span>
                </div>
                <span className="text-sm font-bold text-emerald-800 font-mono">
                  {data.workflow_status_counts["MATCHED"] || 0}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-blue-50/70 border border-blue-100">
                <div className="flex items-center space-x-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
                  <span className="text-xs font-semibold text-blue-900">Processing & Extraction</span>
                </div>
                <span className="text-sm font-bold text-blue-800 font-mono">
                  {(data.workflow_status_counts["PROCESSING"] || 0) + (data.workflow_status_counts["RECEIVED"] || 0)}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-amber-50/70 border border-amber-100">
                <div className="flex items-center space-x-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                  <span className="text-xs font-semibold text-amber-900">Exceptions (Variance/Hold)</span>
                </div>
                <span className="text-sm font-bold text-amber-800 font-mono">
                  {data.workflow_status_counts["EXCEPTION"] || 0}
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-rose-50/70 border border-rose-100">
                <div className="flex items-center space-x-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                  <span className="text-xs font-semibold text-rose-900">Duplicates Rejected</span>
                </div>
                <span className="text-sm font-bold text-rose-800 font-mono">
                  {data.workflow_status_counts["DUPLICATE"] || 0}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <Link
              href="/matching"
              className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition"
            >
              <span>Inspect Three-Way Matching</span>
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom Grid: Recent Invoices & Recent Audit Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Invoices Table */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Recent Invoice Intake</h3>
              <p className="text-xs text-slate-500">Live invoices synced with PostgreSQL</p>
            </div>
            <Link
              href="/invoices"
              className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center space-x-1"
            >
              <span>All Invoices</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4">Invoice #</th>
                  <th className="py-3 px-4">Vendor</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Amount</th>
                  <th className="py-3 px-4">Match Status</th>
                  <th className="py-3 px-4">Approval</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-normal">
                {data.recent_invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/60 transition">
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                      {inv.invoice_number}
                    </td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {inv.vendor?.legal_name || "Vendor"}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 font-mono text-[11px]">
                        {inv.department?.code || "DEPT"}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900 font-mono">
                      {formatCurrency(inv.total_amount)}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={inv.processing_status} type="processing" />
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={inv.approval_status} type="approval" />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/invoices/${inv.id}`}
                        className="inline-flex items-center text-sky-600 hover:text-sky-800 font-semibold text-xs"
                      >
                        <span>Details</span>
                        <ArrowUpRight className="h-3 w-3 ml-0.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Audit Feed */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm">
          <div className="pb-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Audit Trail</h3>
              <p className="text-xs text-slate-500">Immutable ledger actions</p>
            </div>
            <Link
              href="/audit"
              className="text-xs font-semibold text-sky-600 hover:text-sky-700 flex items-center space-x-1"
            >
              <span>View Log</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="mt-4 space-y-3">
            {data.recent_audit_activity.slice(0, 5).map((log) => (
              <div key={log.id} className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800 font-mono text-[11px]">
                    {log.action}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {formatDateTime(log.created_at)}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 flex items-center justify-between">
                  <span>Entity: {log.entity_type} #{log.entity_id}</span>
                  <span className="text-slate-400 font-mono text-[10px]">
                    {log.user?.full_name || "System Agent"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

