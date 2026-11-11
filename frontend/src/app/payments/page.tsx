"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { CreditCard, CheckCircle, Clock, ArrowUpRight, RefreshCw, Send } from "lucide-react";
import { api } from "@/services/api";
import { Payment } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    api
      .getPayments()
      .then((data) => {
        setPayments(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSimulate = async (id: number) => {
    try {
      await api.simulatePayment(id);
      loadData();
    } catch (e: any) {
      alert(`Simulation failed: ${e.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <CreditCard className="h-5 w-5 text-sky-600" />
            <span>Disbursements & Payment Execution Simulation</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Mock payment orchestration engine for ACH, Wire Transfers, and internal university ledger disbursements
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
        <div className="p-4 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900">Payment Batch Registry</h3>
          <p className="text-xs text-slate-500">Live payment orders linked to approved invoices</p>
        </div>

        {loading ? (
          <TableSkeleton rows={5} />
        ) : payments.length === 0 ? (
          <EmptyState
            title="No payment batches found"
            description="No disbursements currently scheduled or settled."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3.5 px-4">Payment Ref #</th>
                  <th className="py-3.5 px-4">Invoice #</th>
                  <th className="py-3.5 px-4">Method</th>
                  <th className="py-3.5 px-4">Scheduled Date</th>
                  <th className="py-3.5 px-4">Settled Date</th>
                  <th className="py-3.5 px-4">Amount</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {payments.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {p.payment_reference}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700">
                      <Link href={`/invoices/${p.invoice_id}`} className="hover:text-sky-600">
                        Invoice #{p.invoice_id}
                      </Link>
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800">
                      <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px]">
                        {p.payment_method}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(p.scheduled_date)}</td>
                    <td className="py-3 px-4 text-slate-500">
                      {p.payment_date ? formatDate(p.payment_date) : "—"}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {formatCurrency(p.amount)}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={p.status} type="payment" />
                    </td>
                    <td className="py-3 px-4 text-right">
                      {p.status === "SCHEDULED" ? (
                        <button
                          onClick={() => handleSimulate(p.id)}
                          className="inline-flex items-center space-x-1 px-3 py-1 rounded bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs shadow-sm transition"
                        >
                          <Send className="h-3 w-3" />
                          <span>Simulate Settlement</span>
                        </button>
                      ) : (
                        <span className="text-emerald-700 font-semibold text-xs inline-flex items-center space-x-1">
                          <CheckCircle className="h-3.5 w-3.5" />
                          <span>Settled</span>
                        </span>
                      )}
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

