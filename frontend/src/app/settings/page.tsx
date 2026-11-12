"use client";

import React, { useEffect, useState } from "react";
import {
  Settings,
  Sliders,
  Shield,
  Key,
  Database,
  Server,
  CheckCircle2,
  AlertTriangle,
  Lock,
  RefreshCw,
  Cpu,
  FileCheck,
} from "lucide-react";
import { api } from "@/services/api";
import { ERPConnectionStatus } from "@/types";

export default function SettingsPage() {
  const [erpStatus, setErpStatus] = useState<ERPConnectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [savedNotice, setSavedNotice] = useState(false);

  const loadData = () => {
    setLoading(true);
    api
      .getERPStatus()
      .then((st) => {
        setErpStatus(st);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveDemoConfig = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <Settings className="h-5 w-5 text-sky-600" />
            <span>AP Engine Configuration & System Governance</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure matching tolerance thresholds, ERP adapter simulation, and security protocols
          </p>
        </div>
        <button
          onClick={loadData}
          className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition self-start"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {savedNotice && (
        <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50 text-xs text-emerald-800 flex items-center space-x-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
          <span>Configuration parameters updated and synchronized with active AP engine session.</span>
        </div>
      )}

      {/* Grid of Configuration Panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Panel 1: Three-Way Match Tolerances */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm space-y-4">
          <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-100">
            <Sliders className="h-4 w-4 text-sky-600" />
            <h3 className="text-sm font-bold text-slate-900">Three-Way Match Tolerances</h3>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="font-semibold text-slate-700 block">
                Unit Price Variance Allowance
              </label>
              <div className="mt-1 flex items-center space-x-2">
                <input
                  type="text"
                  readOnly
                  value="0.00% (Strict Parity)"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-slate-50 text-slate-800 font-mono text-xs font-semibold"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Invoiced unit price must exactly match authorized PO line item rate.
              </p>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block">
                Quantity Tolerance Allowance
              </label>
              <div className="mt-1 flex items-center space-x-2">
                <input
                  type="text"
                  readOnly
                  value="0 units (Invoiced <= Received)"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-slate-50 text-slate-800 font-mono text-xs font-semibold"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Invoiced quantity cannot exceed accepted GRN quantity.
              </p>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block">
                OCR Confidence Routing Cutoff
              </label>
              <div className="mt-1 flex items-center space-x-2">
                <input
                  type="text"
                  readOnly
                  value="70.0% Minimum Confidence"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-slate-50 text-slate-800 font-mono text-xs font-semibold"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Invoices scoring below 70% confidence require mandatory human review.
              </p>
            </div>
          </div>
        </div>

        {/* Panel 2: ERP Integration & Adapter Parameters */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm space-y-4">
          <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-100">
            <Server className="h-4 w-4 text-sky-600" />
            <h3 className="text-sm font-bold text-slate-900">ERP Adapter & Simulation Mode</h3>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="font-semibold text-slate-700 block">Active ERP Target</label>
              <div className="mt-1 p-2.5 rounded-lg border border-sky-100 bg-sky-50 flex items-center justify-between">
                <div>
                  <span className="font-bold text-sky-950 font-mono text-xs">
                    {erpStatus?.adapter_name || "MOCK_UNIVERSITY_ERP"}
                  </span>
                  <p className="text-[11px] text-sky-700">Mock University Financial System</p>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-200 text-sky-900">
                  SIMULATION
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-slate-700 block">Simulated Latency</label>
                <input
                  type="text"
                  readOnly
                  value={`${erpStatus?.latency_ms || 150} ms`}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 bg-slate-50 text-slate-800 font-mono text-xs"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block">Posting Policy</label>
                <input
                  type="text"
                  readOnly
                  value="Strict Human Approval"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 bg-slate-50 text-slate-800 text-xs font-semibold"
                />
              </div>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block">
                Double-Entry Invariance
              </label>
              <div className="mt-1 p-2 rounded-lg bg-slate-50 border border-slate-200 text-[11px] font-mono text-slate-700">
                Sum(Debits) == Sum(Credits) with automatic penny balancing to Account 5099
              </div>
            </div>
          </div>
        </div>

        {/* Panel 3: Security & RBAC Configuration */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm space-y-4">
          <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-100">
            <Lock className="h-4 w-4 text-sky-600" />
            <h3 className="text-sm font-bold text-slate-900">Security & Access Control</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
              <div>
                <span className="font-semibold text-slate-800 block">Password Hasher</span>
                <span className="text-[11px] text-slate-500">Argon2id multi-pass cryptographic algorithm</span>
              </div>
              <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                ENFORCED
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
              <div>
                <span className="font-semibold text-slate-800 block">Session Encryption</span>
                <span className="text-[11px] text-slate-500">Signed JWT (HS256) with 60-minute expiration</span>
              </div>
              <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                ACTIVE
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
              <div>
                <span className="font-semibold text-slate-800 block">RBAC Permission Boundary</span>
                <span className="text-[11px] text-slate-500">Vendor accounts restricted from approvals & disbursements</span>
              </div>
              <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                STRICT
              </span>
            </div>
          </div>
        </div>

        {/* Panel 4: Document Intake & Filesystem Guardrails */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm space-y-4">
          <div className="flex items-center space-x-2.5 pb-3 border-b border-slate-100">
            <FileCheck className="h-4 w-4 text-sky-600" />
            <h3 className="text-sm font-bold text-slate-900">Document Upload Guardrails</h3>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
              <div>
                <span className="font-semibold text-slate-800 block">Magic Byte Verification</span>
                <span className="text-[11px] text-slate-500">PDF (%PDF), PNG, JPEG magic signatures inspected</span>
              </div>
              <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-sky-100 text-sky-800">
                ENABLED
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
              <div>
                <span className="font-semibold text-slate-800 block">Maximum Upload Size</span>
                <span className="text-[11px] text-slate-500">10 MB server-side limit rejecting oversized files</span>
              </div>
              <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-slate-200 text-slate-800">
                10 MB
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100">
              <div>
                <span className="font-semibold text-slate-800 block">Path Traversal Defense</span>
                <span className="text-[11px] text-slate-500">Strict uploads-root sandboxing and null-byte stripping</span>
              </div>
              <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                SECURED
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
