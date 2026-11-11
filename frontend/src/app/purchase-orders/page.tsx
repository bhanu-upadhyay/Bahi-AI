"use client";

import React, { useEffect, useState } from "react";
import { ShoppingCart, RefreshCw, FileText } from "lucide-react";
import { api } from "@/services/api";
import { PurchaseOrder } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function PurchaseOrdersPage() {
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    api
      .getPurchaseOrders()
      .then((data) => {
        setPos(data);
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
            <ShoppingCart className="h-5 w-5 text-sky-600" />
            <span>Authorized Purchase Orders (PO)</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            University procurement purchase orders, delivery commitments, and line item specifications
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
        {loading ? (
          <TableSkeleton rows={7} />
        ) : pos.length === 0 ? (
          <EmptyState
            title="No purchase orders found"
            description="No purchase order records in database."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4">PO Number</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Supplier</th>
                  <th className="py-3 px-4">Issue Date</th>
                  <th className="py-3 px-4">Expected Delivery</th>
                  <th className="py-3 px-4">Total Amount</th>
                  <th className="py-3 px-4">PO Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pos.map((po) => (
                  <tr key={po.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {po.po_number}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-700">
                        {po.department?.code || `Dept ${po.department_id}`}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800">
                      {po.vendor?.legal_name || `Vendor ${po.vendor_id}`}
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(po.issue_date)}</td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(po.expected_delivery_date)}</td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {formatCurrency(po.total_amount)}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={po.status} type="processing" />
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

