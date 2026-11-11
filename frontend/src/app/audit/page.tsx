"use client";

import React, { useEffect, useState } from "react";
import { History, ShieldCheck, RefreshCw } from "lucide-react";
import { api } from "@/services/api";
import { AuditLog } from "@/types";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDateTime } from "@/lib/utils";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    api
      .getAuditLogs()
      .then((data) => {
        setLogs(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <History className="h-5 w-5 text-sky-600" />
            <span>Immutable System Audit Trail</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Append-only compliance log recording all financial events, approvals, matches, and anomalies
          </p>
        </div>
        <button
          onClick={loadData}
          className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Ledger Compliance Events</h3>
          <span className="text-xs font-mono font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
            Append-Only Active
          </span>
        </div>

        {loading ? (
          <TableSkeleton rows={8} />
        ) : logs.length === 0 ? (
          <EmptyState
            title="No audit logs found"
            description="Audit events will record here automatically as invoices and approvals occur."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Action Event</th>
                  <th className="py-3 px-4">Entity</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">IP Origin</th>
                  <th className="py-3 px-4">Event Payload</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                      {formatDateTime(log.created_at)}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {log.action}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-700 font-medium">
                        {log.entity_type} #{log.entity_id}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-700">
                      {log.user ? (
                        <span>
                          {log.user.full_name} ({log.user.role})
                        </span>
                      ) : (
                        <span className="text-slate-400 font-mono text-[11px]">System Automation</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                      {log.ip_address || "127.0.0.1"}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-600 max-w-xs truncate">
                      {log.new_values ? JSON.stringify(log.new_values) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

