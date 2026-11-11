import React from "react";
import { BarChart3, Download, FileSpreadsheet } from "lucide-react";

export default function ReportsPage() {
  return (
    <div className="max-w-3xl mx-auto py-12 text-center space-y-6">
      <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-100">
        <BarChart3 className="h-8 w-8" />
      </div>
      <div className="space-y-2">
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 uppercase tracking-wider">
          Phase 2 Analytics
        </span>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">
          Executive Reports & Spend Intelligence
        </h2>
        <p className="text-sm text-slate-500 max-w-lg mx-auto">
          Comprehensive AP cycle time metrics, vendor price elasticity trends, early-payment discount capture rate, and department audit compliance summaries.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-2">
          <FileSpreadsheet className="h-5 w-5 text-indigo-600" />
          <h4 className="text-xs font-bold text-slate-900">Quarterly Spend Audit Export</h4>
          <p className="text-[11px] text-slate-500">
            Export full transactional detail with tax reconciliation across all campus cost centers.
          </p>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-2">
          <Download className="h-5 w-5 text-indigo-600" />
          <h4 className="text-xs font-bold text-slate-900">Vendor Performance Scorecard</h4>
          <p className="text-[11px] text-slate-500">
            Fulfillment velocity, price variance frequency, and invoice error rates per vendor.
          </p>
        </div>
      </div>
    </div>
  );
}

