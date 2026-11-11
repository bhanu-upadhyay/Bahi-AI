"use client";

import React, { useEffect, useState } from "react";
import { PackageCheck, RefreshCw } from "lucide-react";
import { api } from "@/services/api";
import { GoodsReceipt } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

export default function GoodsReceiptsPage() {
  const [grns, setGrns] = useState<GoodsReceipt[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    api
      .getGoodsReceipts()
      .then((data) => {
        setGrns(data);
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
            <PackageCheck className="h-5 w-5 text-sky-600" />
            <span>Goods Receipt Notes (GRN)</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Campus delivery receiving confirmations, inspection records, and partial shipment acceptance
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
          <TableSkeleton rows={6} />
        ) : grns.length === 0 ? (
          <EmptyState
            title="No goods receipts found"
            description="No GRN logs currently in database."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4">GRN Number</th>
                  <th className="py-3 px-4">Linked PO</th>
                  <th className="py-3 px-4">Received Date</th>
                  <th className="py-3 px-4">Receiving Officer</th>
                  <th className="py-3 px-4">Inspection Notes</th>
                  <th className="py-3 px-4">Receipt Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {grns.map((g) => (
                  <tr key={g.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-mono font-bold text-slate-900">
                      {g.grn_number}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-700">
                      PO #{g.purchase_order_id}
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(g.received_date)}</td>
                    <td className="py-3 px-4 text-slate-700 font-medium">
                      {g.receiver?.full_name || "Procurement Staff"}
                    </td>
                    <td className="py-3 px-4 text-slate-600 max-w-sm truncate">
                      {g.notes || "Standard delivery verification"}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={g.status} type="processing" />
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

