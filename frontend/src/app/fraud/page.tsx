"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldAlert, AlertTriangle, CheckCircle, RefreshCw, ArrowUpRight } from "lucide-react";
import { api } from "@/services/api";
import { FraudAlert } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTime } from "@/lib/utils";

export default function FraudAlertsPage() {
  const [alerts, setAlerts] = useState<FraudAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("OPEN");

  const loadData = () => {
    setLoading(true);
    api
      .getFraudAlerts(statusFilter || undefined)
      .then((data) => {
        setAlerts(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleResolve = async (alertId: number) => {
    try {
      await api.resolveFraudAlert(alertId, "RESOLVED");
      loadData();
    } catch (e) {
      alert("Error resolving alert");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <ShieldAlert className="h-5 w-5 text-rose-600" />
            <span>Fraud Screening & Exception Center</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Automated anomaly detection, duplicate invoice protection, and variance flags
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-700 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="OPEN">Open Exceptions</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="RESOLVED">Resolved</option>
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
        ) : alerts.length === 0 ? (
          <EmptyState
            title="No fraud alerts or exceptions"
            description="All active vendor invoices have cleared anomaly and tolerance validation."
          />
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm space-y-3 hover:border-slate-300 transition"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex items-center space-x-3">
                  <StatusBadge status={alert.severity} type="severity" />
                  <span className="font-mono text-xs font-bold text-slate-900">
                    {alert.alert_type}
                  </span>
                  <span className="text-xs text-slate-500 font-mono">
                    Invoice #{alert.invoice_id}
                  </span>
                </div>
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                    Risk Score: {alert.risk_score} / 100
                  </span>
                  <StatusBadge status={alert.status} />
                </div>
              </div>

              <p className="text-xs text-slate-700 leading-relaxed font-sans">
                {alert.description}
              </p>

              <div className="flex items-center justify-between pt-2 text-[11px] text-slate-400">
                <span>Detected: {formatDateTime(alert.created_at)}</span>
                <div className="flex items-center space-x-3">
                  <Link
                    href={`/invoices/${alert.invoice_id}`}
                    className="text-sky-600 hover:text-sky-800 font-semibold flex items-center space-x-1"
                  >
                    <span>Inspect Invoice</span>
                    <ArrowUpRight className="h-3 w-3" />
                  </Link>
                  {alert.status === "OPEN" && (
                    <button
                      onClick={() => handleResolve(alert.id)}
                      className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-900 text-white font-medium text-xs shadow-sm transition"
                    >
                      Resolve Exception
                    </button>
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

