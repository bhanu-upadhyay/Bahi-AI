"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  X,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  ExternalLink,
  Layers,
  ArrowRight,
} from "lucide-react";
import { api } from "@/services/api";
import { JournalEntry } from "@/types";
import { formatCurrency, formatDate } from "@/lib/utils";

interface JournalEntryModalProps {
  entryId: number | null;
  onClose: () => void;
  onEntryUpdated?: () => void;
}

export const JournalEntryModal: React.FC<JournalEntryModalProps> = ({
  entryId,
  onClose,
  onEntryUpdated,
}) => {
  const [entry, setEntry] = useState<JournalEntry | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [reversing, setReversing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showReversePrompt, setShowReversePrompt] = useState<boolean>(false);
  const [reversalReason, setReversalReason] = useState<string>("");

  useEffect(() => {
    if (entryId) {
      setLoading(true);
      setError(null);
      api
        .getJournalEntryById(entryId)
        .then((data) => {
          setEntry(data);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message || "Failed to load journal entry.");
          setLoading(false);
        });
    }
  }, [entryId]);

  if (!entryId) return null;

  const handleReverse = async () => {
    if (!entry) return;
    try {
      setReversing(true);
      setError(null);
      await api.reverseJournalEntry(entry.id, reversalReason || "Manual reversal requested by Finance Officer");
      setReversing(false);
      setShowReversePrompt(false);
      if (onEntryUpdated) onEntryUpdated();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to reverse journal entry.");
      setReversing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-sky-100 text-sky-700">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold font-mono text-slate-900">
                  {entry?.entry_number || `Entry #${entryId}`}
                </h3>
                {entry && (
                  <span
                    className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full border ${
                      entry.status === "POSTED"
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : "bg-rose-50 text-rose-800 border-rose-200"
                    }`}
                  >
                    {entry.status}
                  </span>
                )}
                {entry?.is_balanced && (
                  <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded-full bg-teal-50 text-teal-800 border border-teal-200 flex items-center space-x-1">
                    <CheckCircle2 className="h-3 w-3 text-teal-600" />
                    <span>BALANCED</span>
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Posting Date: {entry ? formatDate(entry.posting_date) : "..."} • Period: {entry?.accounting_period || "..."}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-500 hover:text-slate-700 transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs flex-1">
          {error && (
            <div className="p-3.5 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="py-12 text-center text-slate-400">Loading journal voucher details...</div>
          ) : !entry ? (
            <div className="py-12 text-center text-slate-400">Journal entry not found.</div>
          ) : (
            <>
              {/* Summary Metadata Card */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-xl bg-slate-50 border border-slate-200">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">Description</span>
                  <p className="font-medium text-slate-800 mt-0.5">{entry.description}</p>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">Linked Invoice</span>
                  <p className="mt-0.5">
                    {entry.invoice_id ? (
                      <Link
                        href={`/invoices/${entry.invoice_id}`}
                        className="text-sky-600 font-bold hover:underline inline-flex items-center space-x-1"
                      >
                        <span>Invoice #{entry.invoice_id}</span>
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    ) : (
                      <span className="text-slate-400">Direct GL Entry</span>
                    )}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">ERP Document Ref</span>
                  <p className="font-mono font-bold text-slate-800 mt-0.5">
                    {entry.erp_document_reference || "MOCK-ERP-LOCAL"}
                  </p>
                </div>
              </div>

              {/* Line Items Table */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-100 text-slate-600 font-semibold border-b border-slate-200">
                      <th className="py-2.5 px-3 w-12">#</th>
                      <th className="py-2.5 px-3">Account</th>
                      <th className="py-2.5 px-3">Description</th>
                      <th className="py-2.5 px-3 text-right">Debit</th>
                      <th className="py-2.5 px-3 text-right">Credit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {entry.lines && entry.lines.length > 0 ? (
                      entry.lines.map((line) => (
                        <tr key={line.id} className="hover:bg-slate-50/60 font-mono">
                          <td className="py-2.5 px-3 text-slate-400">{line.line_number}</td>
                          <td className="py-2.5 px-3 font-sans">
                            <span className="font-mono font-bold text-slate-900">{line.account_code}</span>
                            <span className="text-slate-500 ml-1.5 font-medium">{line.account_name}</span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-700 font-sans max-w-xs truncate">
                            {line.description}
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                            {Number(line.debit_amount) > 0 ? formatCurrency(Number(line.debit_amount)) : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                            {Number(line.credit_amount) > 0 ? formatCurrency(Number(line.credit_amount)) : "—"}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-slate-400 font-sans">
                          No lines found for this entry.
                        </td>
                      </tr>
                    )}
                  </tbody>
                  <tfoot>
                    <tr className="bg-slate-50 font-bold border-t border-slate-200 text-slate-900 font-mono">
                      <td colSpan={3} className="py-3 px-3 text-right font-sans font-bold">
                        Voucher Total:
                      </td>
                      <td className="py-3 px-3 text-right text-emerald-700">
                        {formatCurrency(Number(entry.total_debit))}
                      </td>
                      <td className="py-3 px-3 text-right text-emerald-700">
                        {formatCurrency(Number(entry.total_credit))}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>

              {/* Reversal Prompt */}
              {showReversePrompt && (
                <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/70 space-y-3 animate-in fade-in">
                  <div className="flex items-center space-x-2 text-rose-900 font-bold">
                    <AlertTriangle className="h-4 w-4 text-rose-600" />
                    <span>Confirm Journal Voucher Reversal</span>
                  </div>
                  <p className="text-slate-600 text-[11px]">
                    This will create an inverted reversal journal entry swapping all debits and credits, marking this entry as REVERSED. This cannot be undone.
                  </p>
                  <input
                    type="text"
                    value={reversalReason}
                    onChange={(e) => setReversalReason(e.target.value)}
                    placeholder="Enter reason for reversal (required for audit trail)..."
                    className="w-full rounded-lg border border-rose-300 px-3 py-2 text-xs text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-rose-500/20"
                  />
                  <div className="flex items-center space-x-2 justify-end">
                    <button
                      onClick={() => setShowReversePrompt(false)}
                      className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleReverse}
                      disabled={reversing}
                      className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-bold shadow-sm transition"
                    >
                      {reversing ? "Reversing..." : "Confirm & Post Reversal"}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/60">
          <div>
            {entry && entry.status === "POSTED" && !showReversePrompt && (
              <button
                onClick={() => setShowReversePrompt(true)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold transition"
              >
                <RotateCcw className="h-3.5 w-3.5 text-rose-600" />
                <span>Reverse Voucher</span>
              </button>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};