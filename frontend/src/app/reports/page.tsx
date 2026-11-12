"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart3,
  Download,
  FileSpreadsheet,
  PieChart,
  TrendingUp,
  Receipt,
  Building,
  CheckCircle2,
  Calendar,
  Layers,
  RefreshCw,
} from "lucide-react";
import { api } from "@/services/api";
import { DashboardSummary, TrialBalanceResponse } from "@/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";

export default function ReportsPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trialBalance, setTrialBalance] = useState<TrialBalanceResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      api.getDashboardSummary().catch(() => null),
      api.getTrialBalance().catch(() => null),
    ])
      .then(([sum, tb]) => {
        setSummary(sum);
        setTrialBalance(tb);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleExportDepartmentSpend = () => {
    if (!summary || !summary.department_budgets) return;
    const headers = ["Department Code", "Department Name", "Allocated (INR)", "Committed (INR)", "Spent (INR)", "Available (INR)", "Utilization %"];
    const rows = summary.department_budgets.map((d) => [
      d.department_code,
      `"${d.department_name}"`,
      d.allocated_amount,
      d.committed_amount,
      d.spent_amount,
      d.available_amount,
      `${d.utilization_percentage.toFixed(1)}%`,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `bahi_ai_department_spend_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportTrialBalance = () => {
    if (!trialBalance || !trialBalance.accounts) return;
    const headers = ["Account Code", "Account Name", "Type", "Debit (INR)", "Credit (INR)"];
    const rows = trialBalance.accounts.map((a) => [
      a.account_code,
      `"${a.account_name}"`,
      a.account_type,
      a.net_debit || a.debit_total,
      a.net_credit || a.credit_total,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `bahi_ai_trial_balance_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <TableSkeleton rows={4} />
      </div>
    );
  }

  // Extract Tax Credits from Trial Balance
  const cgstAccount = trialBalance?.accounts?.find((a) => a.account_code === "1401");
  const sgstAccount = trialBalance?.accounts?.find((a) => a.account_code === "1402");
  const igstAccount = trialBalance?.accounts?.find((a) => a.account_code === "1403");
  const apAccount = trialBalance?.accounts?.find((a) => a.account_code === "2101");

  const totalTaxCredit =
    (Number(cgstAccount?.net_debit || cgstAccount?.debit_total) || 0) +
    (Number(sgstAccount?.net_debit || sgstAccount?.debit_total) || 0) +
    (Number(igstAccount?.net_debit || igstAccount?.debit_total) || 0);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <BarChart3 className="h-5 w-5 text-sky-600" />
            <span>Executive Reports & Spend Intelligence</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Campus-wide Accounts Payable analytics, GST Input Tax Credit (ITC) reconciliation, and budget performance
          </p>
        </div>
        <div className="flex items-center space-x-2.5">
          <button
            onClick={loadData}
            title="Refresh analytics data"
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={handleExportDepartmentSpend}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm transition"
          >
            <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
            <span>Export Spend CSV</span>
          </button>
          <button
            onClick={handleExportTrialBalance}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-sm transition"
          >
            <Download className="h-4 w-4" />
            <span>Export GL Balance</span>
          </button>
        </div>
      </div>

      {/* Top Level Financial Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <span className="text-xs font-medium text-slate-500">Total Budget Allocated</span>
          <div className="mt-2">
            <span className="text-lg font-bold font-mono text-slate-900">
              {formatCurrency(summary?.total_budget_allocated || 0)}
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">Central university appropriation</p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <span className="text-xs font-medium text-slate-500">Total Spent & Settled</span>
          <div className="mt-2">
            <span className="text-lg font-bold font-mono text-emerald-700">
              {formatCurrency(summary?.total_budget_spent || 0)}
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">Executed AP disbursements</p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <span className="text-xs font-medium text-slate-500">AP Trade Creditors (Liability)</span>
          <div className="mt-2">
            <span className="text-lg font-bold font-mono text-purple-700">
              {formatCurrency(apAccount?.net_credit || apAccount?.credit_total || summary?.total_payable_amount || 0)}
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">GL 2101 Outstanding Invoiced</p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <span className="text-xs font-medium text-slate-500">Total GST ITC Claimable</span>
          <div className="mt-2">
            <span className="text-lg font-bold font-mono text-sky-700">
              {formatCurrency(totalTaxCredit)}
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">CGST + SGST + IGST Input Tax</p>
          </div>
        </div>
      </div>

      {/* Department Spend & Budget Utilization */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <Building className="h-4 w-4 text-sky-600" />
              <span>Departmental Budget Utilization Report</span>
            </h3>
            <p className="text-xs text-slate-500">Live encumbrance and spend tracking by academic and administrative unit</p>
          </div>
          <span className="px-2.5 py-1 rounded-full font-mono text-[11px] font-bold bg-slate-100 text-slate-700">
            FY 2024–2025
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                <th className="py-3 px-4">Code</th>
                <th className="py-3 px-4">Department Unit</th>
                <th className="py-3 px-4 text-right">Allocated</th>
                <th className="py-3 px-4 text-right">Spent</th>
                <th className="py-3 px-4 text-right">Available</th>
                <th className="py-3 px-4 w-48">Utilization</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {summary?.department_budgets?.map((dept) => {
                const pct = dept.utilization_percentage || 0;
                return (
                  <tr key={dept.department_id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-bold text-slate-900">{dept.department_code}</td>
                    <td className="py-3 px-4 font-sans font-medium text-slate-800">
                      {dept.department_name}
                    </td>
                    <td className="py-3 px-4 text-right">{formatCurrency(dept.allocated_amount)}</td>
                    <td className="py-3 px-4 text-right text-emerald-700 font-bold">
                      {formatCurrency(dept.spent_amount)}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-600">
                      {formatCurrency(dept.available_amount)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              pct > 90 ? "bg-rose-500" : pct > 70 ? "bg-amber-500" : "bg-sky-500"
                            }`}
                            style={{ width: `${Math.min(pct, 100)}%` }}
                          />
                        </div>
                        <span className="text-[11px] font-bold text-slate-700 w-10 text-right">
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Statutory GST Input Tax Credit (ITC) Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-sky-100 bg-sky-50/50 space-y-2">
          <div className="flex items-center justify-between text-xs font-bold text-sky-950">
            <span>CGST Input Tax Credit</span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-sky-200 text-sky-900">
              Account 1401
            </span>
          </div>
          <span className="text-xl font-bold font-mono text-slate-900 block">
            {formatCurrency(cgstAccount?.net_debit || cgstAccount?.debit_total || 0)}
          </span>
          <p className="text-[11px] text-slate-500">
            Central GST statutory offset ledger balance claimable from central government
          </p>
        </div>

        <div className="p-4 rounded-xl border border-indigo-100 bg-indigo-50/50 space-y-2">
          <div className="flex items-center justify-between text-xs font-bold text-indigo-950">
            <span>SGST Input Tax Credit</span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-indigo-200 text-indigo-900">
              Account 1402
            </span>
          </div>
          <span className="text-xl font-bold font-mono text-slate-900 block">
            {formatCurrency(sgstAccount?.net_debit || sgstAccount?.debit_total || 0)}
          </span>
          <p className="text-[11px] text-slate-500">
            State GST statutory offset ledger balance claimable from state jurisdiction
          </p>
        </div>

        <div className="p-4 rounded-xl border border-purple-100 bg-purple-50/50 space-y-2">
          <div className="flex items-center justify-between text-xs font-bold text-purple-950">
            <span>IGST Input Tax Credit</span>
            <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-purple-200 text-purple-900">
              Account 1403
            </span>
          </div>
          <span className="text-xl font-bold font-mono text-slate-900 block">
            {formatCurrency(igstAccount?.net_debit || igstAccount?.debit_total || 0)}
          </span>
          <p className="text-[11px] text-slate-500">
            Integrated GST for inter-state university equipment and licensing acquisitions
          </p>
        </div>
      </div>
    </div>
  );
}
