"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { GitCompare, CheckCircle2, AlertTriangle, ArrowUpRight, RefreshCw, FileText } from "lucide-react";
import { api } from "@/services/api";
import { Invoice } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function MatchingPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    api
      .getInvoices()
      .then((data) => {
        setInvoices(data);
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
            <GitCompare className="h-5 w-5 text-sky-600" />
            <span>Three-Way Match Verification Engine</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Cross-verifying Vendor Invoices against Approved Purchase Orders and Goods Receipt Notes (GRN)
          </p>
        </div>
        <button
          onClick={loadData}
          className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Rules Information Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/60 text-xs text-emerald-900 space-y-1">
          <div className="font-bold flex items-center space-x-1.5 text-emerald-800">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>Matched Within Tolerance</span>
          </div>
          <p className="text-emerald-700">
            Invoiced quantity ≤ accepted GRN quantity, and unit price matches authorized PO within 0.00% variance.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/60 text-xs text-amber-900 space-y-1">
          <div className="font-bold flex items-center space-x-1.5 text-amber-800">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <span>Exception Hold</span>
          </div>
          <p className="text-amber-700">
            Quantity mismatch, price variance, or missing delivery note detected. Requires procurement review.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/60 text-xs text-rose-900 space-y-1">
          <div className="font-bold flex items-center space-x-1.5 text-rose-800">
            <AlertTriangle className="h-4 w-4 text-rose-600" />
            <span>Duplicate Rejection</span>
          </div>
          <p className="text-rose-700">
            Vendor submitted invoice already settled or identical normalized number. Blocked by database constraint.
          </p>
        </div>
      </div>

      {/* Verification Ledger */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900">Three-Way Matching Verification Matrix</h3>
          <p className="text-xs text-slate-500">Live comparison records across university transactions</p>
        </div>

        {loading ? (
          <TableSkeleton rows={8} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4">Invoice #</th>
                  <th className="py-3 px-4">Vendor</th>
                  <th className="py-3 px-4">Dept</th>
                  <th className="py-3 px-4">Linked PO</th>
                  <th className="py-3 px-4">Invoice Total</th>
                  <th className="py-3 px-4">Match Status</th>
                  <th className="py-3 px-4">Approval State</th>
                  <th className="py-3 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                      {inv.invoice_number}
                    </td>
                    <td className="py-3 px-4 text-slate-800 font-medium">{inv.vendor?.legal_name}</td>
                    <td className="py-3 px-4">
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-700">
                        {inv.department?.code}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700">
                      {inv.purchase_order_id ? `PO #${inv.purchase_order_id}` : "No PO"}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900">
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
                        <span>Audit</span>
                        <ArrowUpRight className="h-3 w-3 ml-0.5" />
                      </Link>
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

