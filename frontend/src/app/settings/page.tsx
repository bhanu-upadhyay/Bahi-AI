import React from "react";
import { Settings, Sliders, Shield, Key } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="max-w-3xl mx-auto py-12 text-center space-y-6">
      <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-700 shadow-sm border border-slate-200">
        <Settings className="h-8 w-8" />
      </div>
      <div className="space-y-2">
        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-200 text-slate-800 uppercase tracking-wider">
          Configuration
        </span>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">
          AP Engine Tolerance & Workflow Configuration
        </h2>
        <p className="text-sm text-slate-500 max-w-lg mx-auto">
          Configure three-way match tolerance thresholds, multi-tier approval delegation rules, OCR confidence score cutoffs, and automated email intake channels.
        </p>
      </div>

      <div className="bg-white p-6 rounded-2xl border border-slate-200/90 text-left shadow-sm space-y-4">
        <div className="flex items-start space-x-3 pb-3 border-b border-slate-100">
          <Sliders className="h-5 w-5 text-sky-600 mt-0.5" />
          <div>
            <h4 className="text-xs font-bold text-slate-900">Match Tolerances</h4>
            <p className="text-[11px] text-slate-500">Unit price variance allowance: 0.00% • Line quantity allowance: 0 units</p>
          </div>
        </div>

        <div className="flex items-start space-x-3 pb-3 border-b border-slate-100">
          <Shield className="h-5 w-5 text-sky-600 mt-0.5" />
          <div>
            <h4 className="text-xs font-bold text-slate-900">Fraud Screening Rules</h4>
            <p className="text-[11px] text-slate-500">Exact duplicate check: Strict normalized alphanumeric hash match enabled</p>
          </div>
        </div>

        <div className="flex items-start space-x-3">
          <Key className="h-5 w-5 text-sky-600 mt-0.5" />
          <div>
            <h4 className="text-xs font-bold text-slate-900">Authentication & RBAC</h4>
            <p className="text-[11px] text-slate-500">University SAML / Okta SSO integration preparing for Phase 2</p>
          </div>
        </div>
      </div>
    </div>
  );
}

