"use client";

import React, { useEffect, useState } from "react";
import { PieChart, DollarSign, Wallet, Lock, CheckCircle2, RefreshCw } from "lucide-react";
import { api } from "@/services/api";
import { Budget } from "@/types";
import { KPICard } from "@/components/ui/KPICard";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export default function BudgetsPage() {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    api
      .getBudgets("2024-2025")
      .then((data) => {
        setBudgets(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalAllocated = budgets.reduce((acc, b) => acc + parseFloat(b.allocated_amount as string), 0);
  const totalSpent = budgets.reduce((acc, b) => acc + parseFloat(b.spent_amount as string), 0);
  const totalCommitted = budgets.reduce((acc, b) => acc + parseFloat(b.committed_amount as string), 0);
  const totalAvailable = budgets.reduce((acc, b) => acc + parseFloat(b.available_amount as string), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <PieChart className="h-5 w-5 text-sky-600" />
            <span>University Department Budget Envelopes</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Fiscal Year 2024–2025 spending commitments, actual expenditures, and remaining headroom
          </p>
        </div>
        <button
          onClick={loadData}
          className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Aggregate KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Allocation"
          value={formatCurrency(totalAllocated)}
          subtitle="FY 2024-25 Authorized Budget"
          icon={<DollarSign className="h-5 w-5 text-sky-600" />}
        />
        <KPICard
          title="Actual Spent"
          value={formatCurrency(totalSpent)}
          subtitle="Disbursed invoice settlements"
          icon={<Wallet className="h-5 w-5 text-slate-600" />}
        />
        <KPICard
          title="Committed Orders"
          value={formatCurrency(totalCommitted)}
          subtitle="Encumbered on approved POs"
          icon={<Lock className="h-5 w-5 text-amber-600" />}
        />
        <KPICard
          title="Net Available Headroom"
          value={formatCurrency(totalAvailable)}
          subtitle="Uncommitted expenditure allowance"
          variant="success"
          icon={<CheckCircle2 className="h-5 w-5 text-emerald-600" />}
        />
      </div>

      {/* Department Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {loading ? (
          <div className="col-span-2">
            <TableSkeleton rows={4} />
          </div>
        ) : (
          budgets.map((b) => {
            const allocated = parseFloat(b.allocated_amount as string);
            const spent = parseFloat(b.spent_amount as string);
            const committed = parseFloat(b.committed_amount as string);
            const available = parseFloat(b.available_amount as string);
            const util = allocated > 0 ? ((spent + committed) / allocated) * 100 : 0;

            let barColor = "bg-sky-600";
            if (util > 80) barColor = "bg-rose-500";
            else if (util > 60) barColor = "bg-amber-500";

            return (
              <div
                key={b.id}
                className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm space-y-4 hover:border-slate-300 transition"
              >
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      {b.department?.name || "Department"}
                    </h4>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      {b.department?.code} • FY {b.fiscal_year}
                    </span>
                  </div>
                  <span className="text-xs font-bold font-mono px-2 py-1 rounded bg-slate-100 text-slate-800">
                    {util.toFixed(1)}% Used
                  </span>
                </div>

                <div className="space-y-1.5">
                  <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                    <div
                      className={`h-3 rounded-full ${barColor} transition-all duration-500`}
                      style={{ width: `${Math.min(util, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-2 text-xs border-t border-slate-100">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Allocated</span>
                    <span className="font-mono font-semibold text-slate-900">{formatCurrency(allocated)}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Spent & Committed</span>
                    <span className="font-mono font-semibold text-slate-700">{formatCurrency(spent + committed)}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Available</span>
                    <span className="font-mono font-bold text-emerald-700">{formatCurrency(available)}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

