import React from "react";
import { BookOpen, Sparkles, Database } from "lucide-react";

export default function LedgerPage() {
  return (
    <div className="max-w-3xl mx-auto py-12 text-center space-y-6">
      <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-sky-50 text-sky-700 shadow-sm border border-sky-100">
        <BookOpen className="h-8 w-8" />
      </div>
      <div className="space-y-2">
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-sky-100 text-sky-800 uppercase tracking-wider">
          Phase 2 Integration
        </span>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">
          Enterprise ERP Ledger Integration
        </h2>
        <p className="text-sm text-slate-500 max-w-lg mx-auto">
          Bi-directional synchronization with University Banner / SAP / Oracle ERP financial general ledgers. Automated journal entry vouchers and GL code mapping will activate in Phase 2.
        </p>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 text-left shadow-sm space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Planned Phase 2 Features
        </h3>
        <ul className="text-xs text-slate-700 space-y-2.5">
          <li className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-600"></span>
            <span>Automated chart-of-accounts expense code distribution by department</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-600"></span>
            <span>Real-time commitment and encumbrance posting upon PO release</span>
          </li>
          <li className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-600"></span>
            <span>Pre-settlement batch generation for bank portal ACH transmission</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

