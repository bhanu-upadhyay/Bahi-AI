"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Send,
  Building,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  ExternalLink,
  BookOpen,
  ShieldCheck,
  Cpu,
  Layers,
  ArrowRight,
} from "lucide-react";
import { api } from "@/services/api";
import {
  Invoice,
  PostingEligibilityResponse,
  ERPPosting,
} from "@/types";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/utils";

interface ERPPostingPanelProps {
  invoice: Invoice;
  onInvoiceUpdated?: () => void;
}

export const ERPPostingPanel: React.FC<ERPPostingPanelProps> = ({
  invoice,
  onInvoiceUpdated,
}) => {
  const [eligibility, setEligibility] = useState<PostingEligibilityResponse | null>(null);
  const [posting, setPosting] = useState<ERPPosting | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [simulateFailure, setSimulateFailure] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [eligRes, postRes] = await Promise.all([
        api.getPostingEligibility(invoice.id).catch(() => null),
        api.getInvoiceERPPosting(invoice.id).catch(() => null),
      ]);
      setEligibility(eligRes);
      setPosting(postRes);
    } catch (err: any) {
      console.error("Error loading ERP posting data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (invoice?.id) {
      loadData();
    }
  }, [invoice?.id, invoice?.approval_status, invoice?.processing_status]);

  const handlePostToERP = async () => {
    setSubmitting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await api.postInvoiceToERP(invoice.id, {
        simulate_failure: simulateFailure,
        comments: "Posted via Bahi-AI Accounts Payable Dashboard",
      });
      setPosting(res);
      setSuccessMsg(`Successfully posted to Mock University ERP! Document Ref: ${res.erp_document_reference}`);
      if (onInvoiceUpdated) onInvoiceUpdated();
    } catch (err: any) {
      setError(err.message || "ERP posting failed.");
    } finally {
      setSubmitting(false);
      loadData();
    }
  };

  const isAlreadyPosted = posting?.status === "SYNCED" || invoice.processing_status === "POSTED";

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Top Banner */}
      <div className="p-5 border-b border-slate-100 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/20 border border-indigo-400/30 text-indigo-300">
            <Building className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-bold text-white">ERP General Ledger Integration</h3>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-500/30 text-emerald-200 border border-emerald-400/30">
                MOCK UNIVERSITY ERP
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5">
              Automated double-entry journal vouchers, GL code distribution, and ledger synchronization
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {isAlreadyPosted ? (
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono bg-emerald-500 text-white shadow-sm">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>POSTED & SYNCED</span>
            </span>
          ) : eligibility?.eligible ? (
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono bg-indigo-500 text-white shadow-sm">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>READY FOR POSTING</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono bg-amber-500 text-white shadow-sm">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>POSTING BLOCKED</span>
            </span>
          )}
        </div>
      </div>

      <div className="p-6 space-y-6 text-xs">
        {/* Messages */}
        {successMsg && (
          <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-800 flex items-center space-x-2.5">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
            <span className="font-semibold">{successMsg}</span>
          </div>
        )}
        {error && (
          <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 flex items-center space-x-2.5">
            <XCircle className="h-4 w-4 text-rose-600 flex-shrink-0" />
            <span className="font-medium">{error}</span>
          </div>
        )}

        {/* State A: Already Posted to ERP */}
        {isAlreadyPosted && posting && (
          <div className="p-5 rounded-xl border border-emerald-200 bg-emerald-50/60 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-emerald-200/60">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <div>
                  <h4 className="text-sm font-bold text-emerald-900">
                    Voucher Posted to University General Ledger
                  </h4>
                  <p className="text-[11px] text-emerald-700">
                    Posted at {formatDateTime(posting.posted_at || posting.created_at)}
                  </p>
                </div>
              </div>
              <Link
                href="/ledger"
                className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-white border border-emerald-300 text-emerald-800 font-bold hover:bg-emerald-100 transition shadow-sm"
              >
                <BookOpen className="h-3.5 w-3.5 text-emerald-600" />
                <span>Open in General Ledger</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-0.5">
                <span className="text-[10px] text-slate-400 font-semibold uppercase">ERP Document Ref</span>
                <p className="font-mono font-bold text-slate-900 text-sm">{posting.erp_document_reference}</p>
              </div>
              <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-0.5">
                <span className="text-[10px] text-slate-400 font-semibold uppercase">Adapter</span>
                <p className="font-semibold text-slate-800">{posting.erp_adapter}</p>
              </div>
              <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-0.5">
                <span className="text-[10px] text-slate-400 font-semibold uppercase">Idempotency Key</span>
                <p className="font-mono text-slate-600 text-[10px] truncate">{posting.idempotency_key}</p>
              </div>
            </div>
          </div>
        )}

        {/* State B: Eligibility Checks Grid */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Posting Eligibility Verification (7 Dimension Check)
            </h4>
            <span className="text-[11px] text-slate-500">
              Only approved invoices with validated accounting parameters may be posted
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {eligibility?.checks.map((check, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-xl border flex items-start space-x-2.5 ${
                  check.passed
                    ? "bg-emerald-50/50 border-emerald-200 text-emerald-950"
                    : check.severity === "WARNING"
                    ? "bg-amber-50/50 border-amber-200 text-amber-950"
                    : "bg-rose-50/50 border-rose-200 text-rose-950"
                }`}
              >
                {check.passed ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                ) : check.severity === "WARNING" ? (
                  <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="h-4 w-4 text-rose-600 flex-shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="font-bold text-[11px]">{check.check_name.replace(/_/g, " ")}</div>
                  <p className="text-[10px] opacity-80 mt-0.5 leading-snug">{check.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* State C: Posting Action Controls (If not already posted) */}
        {!isAlreadyPosted && (
          <div className="pt-4 border-t border-slate-100 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="space-y-1">
                <h4 className="text-xs font-bold text-slate-900">Execute ERP General Ledger Posting</h4>
                <p className="text-[11px] text-slate-500">
                  Submits balanced journal voucher (Debits to expense/tax, Credit to Accounts Payable) to Mock University ERP
                </p>
                <div className="flex items-center space-x-2 pt-1">
                  <label className="inline-flex items-center space-x-1.5 text-[11px] text-slate-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={simulateFailure}
                      onChange={(e) => setSimulateFailure(e.target.checked)}
                      className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/20"
                    />
                    <span>Simulate network/gateway failure (Test Error Resilience)</span>
                  </label>
                </div>
              </div>

              <div className="flex items-center space-x-3 flex-shrink-0">
                <button
                  onClick={handlePostToERP}
                  disabled={submitting || !eligibility?.eligible}
                  className={`inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl font-bold shadow-md transition ${
                    !eligibility?.eligible
                      ? "bg-slate-200 text-slate-400 cursor-not-allowed"
                      : submitting
                      ? "bg-indigo-400 text-white cursor-wait"
                      : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-500/20"
                  }`}
                >
                  <Send className={`h-4 w-4 ${submitting ? "animate-spin" : ""}`} />
                  <span>{submitting ? "Posting Voucher..." : "Post to Mock University ERP"}</span>
                </button>
              </div>
            </div>

            {/* Ineligible Explanation */}
            {!eligibility?.eligible && (
              <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/70 text-amber-900 space-y-1.5">
                <div className="flex items-center space-x-2 font-bold text-xs">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <span>Why is ERP posting blocked?</span>
                </div>
                <ul className="text-[11px] text-amber-800 space-y-1 pl-6 list-disc">
                  {eligibility?.blocking_reasons.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};