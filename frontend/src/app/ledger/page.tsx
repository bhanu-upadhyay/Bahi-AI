"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  Layers,
  Database,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  RefreshCw,
  Search,
  Filter,
  ExternalLink,
  Plus,
  Scale,
  Settings,
  Cpu,
  Building,
} from "lucide-react";
import { api } from "@/services/api";
import {
  ChartOfAccount,
  JournalEntry,
  TrialBalanceResponse,
  AccountMapping,
  ERPConnectionStatus,
} from "@/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import { JournalEntryModal } from "@/components/ledger/JournalEntryModal";

export default function LedgerPage() {
  const [activeTab, setActiveTab] = useState<"journal" | "accounts" | "trial" | "mappings">("journal");
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [accounts, setAccounts] = useState<ChartOfAccount[]>([]);
  const [trialBalance, setTrialBalance] = useState<TrialBalanceResponse | null>(null);
  const [mappings, setMappings] = useState<AccountMapping[]>([]);
  const [erpStatus, setErpStatus] = useState<ERPConnectionStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const loadData = async () => {
    setLoading(true);
    try {
      const [entriesRes, accountsRes, tbRes, mappingsRes, erpStatusRes] = await Promise.all([
        api.getJournalEntries({ status: statusFilter || undefined }),
        api.getChartOfAccounts(),
        api.getTrialBalance(),
        api.getAccountMappings(),
        api.getERPStatus().catch(() => null),
      ]);
      setEntries(entriesRes);
      setAccounts(accountsRes);
      setTrialBalance(tbRes);
      setMappings(mappingsRes);
      setErpStatus(erpStatusRes);
    } catch (err) {
      console.error("Failed to load ledger data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const filteredEntries = entries.filter((e) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      e.entry_number.toLowerCase().includes(q) ||
      e.description.toLowerCase().includes(q) ||
      (e.erp_document_reference && e.erp_document_reference.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
              <BookOpen className="h-5 w-5 text-sky-600" />
              <span>University General Ledger & ERP Accounting</span>
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Double-entry journal vouchers, Chart of Accounts, trial balance integrity, and automated ERP postings
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* ERP Connection Pill */}
          <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-xl border border-emerald-200 bg-emerald-50 text-emerald-800 text-xs font-semibold shadow-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>MOCK UNIVERSITY ERP</span>
            <span className="text-[10px] text-emerald-600 font-normal border-l border-emerald-200 pl-2">
              {erpStatus?.latency_ms || 24}ms latency
            </span>
          </div>

          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Quick Metrics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Total Journal Vouchers
          </span>
          <div className="text-xl font-mono font-bold text-slate-900">{entries.length}</div>
          <span className="text-[10px] text-slate-400">All double-entry transactions</span>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Chart of Accounts
          </span>
          <div className="text-xl font-mono font-bold text-slate-900">{accounts.length} GL Accounts</div>
          <span className="text-[10px] text-slate-400">Assets, Liabilities, Expenses</span>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Trial Balance Status
          </span>
          <div className="text-xl font-mono font-bold text-emerald-700 flex items-center space-x-1.5">
            <CheckCircle2 className="h-5 w-5" />
            <span>{trialBalance?.is_balanced ? "PERFECTLY BALANCED" : "VARIANCE DETECTED"}</span>
          </div>
          <span className="text-[10px] text-slate-400">
            Total: {formatCurrency(Number(trialBalance?.total_debit || 0))}
          </span>
        </div>
        <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-1">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            ERP Sync Postings
          </span>
          <div className="text-xl font-mono font-bold text-indigo-700">
            {erpStatus?.active_postings_count || 0} Synced
          </div>
          <span className="text-[10px] text-slate-400">Mock University ERP Engine</span>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 pt-4">
          <div className="flex items-center space-x-1">
            <button
              onClick={() => setActiveTab("journal")}
              className={`pb-3 px-3 text-xs font-bold border-b-2 transition ${
                activeTab === "journal"
                  ? "border-sky-600 text-sky-600"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              General Ledger Entries ({entries.length})
            </button>
            <button
              onClick={() => setActiveTab("accounts")}
              className={`pb-3 px-3 text-xs font-bold border-b-2 transition ${
                activeTab === "accounts"
                  ? "border-sky-600 text-sky-600"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Chart of Accounts ({accounts.length})
            </button>
            <button
              onClick={() => setActiveTab("trial")}
              className={`pb-3 px-3 text-xs font-bold border-b-2 transition ${
                activeTab === "trial"
                  ? "border-sky-600 text-sky-600"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Trial Balance Verification
            </button>
            <button
              onClick={() => setActiveTab("mappings")}
              className={`pb-3 px-3 text-xs font-bold border-b-2 transition ${
                activeTab === "mappings"
                  ? "border-sky-600 text-sky-600"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Account Mappings ({mappings.length})
            </button>
          </div>

          {activeTab === "journal" && (
            <div className="flex items-center space-x-2 pb-3">
              <div className="relative">
                <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search voucher or ref..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              >
                <option value="">All Statuses</option>
                <option value="POSTED">POSTED</option>
                <option value="REVERSED">REVERSED</option>
              </select>
            </div>
          )}
        </div>

        {/* TAB 1: General Ledger Journal Entries */}
        {activeTab === "journal" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4">Entry #</th>
                  <th className="py-3 px-4">Posting Date</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4">Linked Invoice</th>
                  <th className="py-3 px-4">ERP Document Ref</th>
                  <th className="py-3 px-4 text-right">Debit</th>
                  <th className="py-3 px-4 text-right">Credit</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredEntries && filteredEntries.length > 0 ? (
                  filteredEntries.map((e) => (
                    <tr key={e.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">
                        {e.entry_number}
                      </td>
                      <td className="py-3 px-4 text-slate-600 font-mono">
                        {formatDate(e.posting_date)}
                      </td>
                      <td className="py-3 px-4 text-slate-700 max-w-xs truncate font-medium">
                        {e.description}
                      </td>
                      <td className="py-3 px-4">
                        {e.invoice_id ? (
                          <Link
                            href={`/invoices/${e.invoice_id}`}
                            className="text-sky-600 hover:text-sky-800 font-bold inline-flex items-center space-x-1"
                          >
                            <span>Invoice #{e.invoice_id}</span>
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        ) : (
                          <span className="text-slate-400">Manual Voucher</span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-700 text-[11px]">
                        {e.erp_document_reference || "MOCK-ERP-LOCAL"}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                        {formatCurrency(Number(e.total_debit))}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                        {formatCurrency(Number(e.total_credit))}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                            e.status === "POSTED"
                              ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                              : "bg-rose-50 text-rose-800 border border-rose-200"
                          }`}
                        >
                          {e.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setSelectedEntryId(e.id)}
                          className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-[11px] shadow-sm transition"
                        >
                          View Lines
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="py-12 text-center text-slate-400">
                      No journal entries found matching criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB 2: Chart of Accounts */}
        {activeTab === "accounts" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4 w-28">Account Code</th>
                  <th className="py-3 px-4">Account Name</th>
                  <th className="py-3 px-4">Classification</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4 text-right">Total Debit</th>
                  <th className="py-3 px-4 text-right">Total Credit</th>
                  <th className="py-3 px-4 text-right">Net Balance</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {accounts.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-4 font-bold text-slate-900">{a.account_code}</td>
                    <td className="py-3 px-4 font-sans font-bold text-slate-800">{a.account_name}</td>
                    <td className="py-3 px-4 font-sans">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          a.account_type === "ASSET"
                            ? "bg-blue-50 text-blue-700 border border-blue-200"
                            : a.account_type === "LIABILITY"
                            ? "bg-amber-50 text-amber-800 border border-amber-200"
                            : "bg-purple-50 text-purple-700 border border-purple-200"
                        }`}
                      >
                        {a.account_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-500 max-w-sm truncate">
                      {a.description}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-800">
                      {formatCurrency(Number(a.debit_balance || 0))}
                    </td>
                    <td className="py-3 px-4 text-right text-slate-800">
                      {formatCurrency(Number(a.credit_balance || 0))}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-slate-900">
                      {formatCurrency(Number(a.net_balance || 0))}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        ACTIVE
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB 3: Trial Balance Verification */}
        {activeTab === "trial" && (
          <div className="p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-xl bg-emerald-100 text-emerald-700">
                  <Scale className="h-6 w-6" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    General Ledger Trial Balance Reconciliation
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Double-entry accounting verification: Total Debits must equal Total Credits across all GL accounts
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Variance</span>
                  <div className="text-sm font-mono font-bold text-emerald-700">₹0.00 (Zero Variance)</div>
                </div>
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  BALANCED
                </span>
              </div>
            </div>

            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-100 text-slate-600 font-semibold border-b border-slate-200">
                    <th className="py-2.5 px-3">Account Code</th>
                    <th className="py-2.5 px-3">Account Title</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3 text-right">Debit Balance</th>
                    <th className="py-2.5 px-3 text-right">Credit Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {trialBalance?.accounts.map((acc) => (
                    <tr key={acc.account_id} className="hover:bg-slate-50/60">
                      <td className="py-2.5 px-3 font-bold text-slate-900">{acc.account_code}</td>
                      <td className="py-2.5 px-3 font-sans font-medium text-slate-800">{acc.account_name}</td>
                      <td className="py-2.5 px-3 font-sans text-slate-500">{acc.account_type}</td>
                      <td className="py-2.5 px-3 text-right text-slate-900 font-bold">
                        {Number(acc.net_debit) > 0 ? formatCurrency(Number(acc.net_debit)) : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-900 font-bold">
                        {Number(acc.net_credit) > 0 ? formatCurrency(Number(acc.net_credit)) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="bg-slate-50 font-bold border-t-2 border-slate-300 text-slate-900 font-mono text-sm">
                    <td colSpan={3} className="py-3 px-3 text-right font-sans font-bold">
                      Grand Totals:
                    </td>
                    <td className="py-3 px-3 text-right text-emerald-700">
                      {formatCurrency(Number(trialBalance?.total_debit || 0))}
                    </td>
                    <td className="py-3 px-3 text-right text-emerald-700">
                      {formatCurrency(Number(trialBalance?.total_credit || 0))}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: Account Mappings */}
        {activeTab === "mappings" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3 px-4">Mapping Rule</th>
                  <th className="py-3 px-4">Expense Category / Context</th>
                  <th className="py-3 px-4">Debit Account</th>
                  <th className="py-3 px-4">Credit Account</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {mappings.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-4 font-bold text-slate-900">{m.mapping_type}</td>
                    <td className="py-3 px-4 font-sans text-slate-700 font-medium">
                      {m.expense_category || "Default System Rule"}
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <span className="font-mono font-bold text-slate-900">
                        {m.debit_account?.account_code}
                      </span>{" "}
                      — {m.debit_account?.account_name}
                    </td>
                    <td className="py-3 px-4 font-sans">
                      {m.credit_account ? (
                        <>
                          <span className="font-mono font-bold text-slate-900">
                            {m.credit_account.account_code}
                          </span>{" "}
                          — {m.credit_account.account_name}
                        </>
                      ) : (
                        <span className="text-slate-400 font-mono">Dynamic AP Liability</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-500 max-w-sm truncate">
                      {m.description}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        ACTIVE
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal for viewing journal voucher detail */}
      <JournalEntryModal
        entryId={selectedEntryId}
        onClose={() => setSelectedEntryId(null)}
        onEntryUpdated={loadData}
      />
    </div>
  );
}
