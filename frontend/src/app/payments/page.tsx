"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  CreditCard,
  CheckCircle,
  Clock,
  ArrowUpRight,
  RefreshCw,
  Send,
  Plus,
  X,
  AlertCircle,
  AlertTriangle,
  Building2,
  FileText,
  DollarSign,
  Calendar,
  CheckCircle2,
  ShieldCheck,
  Search,
  Filter,
} from "lucide-react";
import { api } from "@/services/api";
import { Payment, Invoice, InvoicePaymentBalance } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [simulatingId, setSimulatingId] = useState<number | null>(null);

  // Modal State for New Disbursement
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string>("");
  const [balanceInfo, setBalanceInfo] = useState<InvoicePaymentBalance | null>(null);
  const [loadingBalance, setLoadingBalance] = useState(false);
  const [paymentAmount, setPaymentAmount] = useState<string>("");
  const [paymentMethod, setPaymentMethod] = useState("ACH");
  const [scheduledDate, setScheduledDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [comments, setComments] = useState("");
  const [submittingPayment, setSubmittingPayment] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = () => {
    setLoading(true);
    Promise.all([api.getPayments(), api.getInvoices()])
      .then(([payList, invList]) => {
        setPayments(payList);
        setInvoices(invList);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load payment data:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  // When invoice selection changes in modal, fetch live balance
  useEffect(() => {
    if (!selectedInvoiceId) {
      setBalanceInfo(null);
      setPaymentAmount("");
      return;
    }

    const invId = parseInt(selectedInvoiceId, 10);
    if (isNaN(invId)) return;

    setLoadingBalance(true);
    setModalError(null);

    api
      .getInvoicePaymentBalance(invId)
      .then((bal) => {
        setBalanceInfo(bal);
        // Default to outstanding balance
        setPaymentAmount(bal.outstanding_balance.toString());
        setLoadingBalance(false);
      })
      .catch((err) => {
        setModalError(err.message || "Failed to fetch invoice balance");
        setLoadingBalance(false);
      });
  }, [selectedInvoiceId]);

  const handleSimulate = async (id: number) => {
    setSimulatingId(id);
    try {
      const updated = await api.simulatePayment(id);
      setToastMessage({
        type: "success",
        text: `Disbursement ${updated.payment_reference} settled successfully!`,
      });
      loadData();
    } catch (e: any) {
      setToastMessage({
        type: "error",
        text: `Settlement failed: ${e.message}`,
      });
    } finally {
      setSimulatingId(null);
    }
  };

  const handlePreparePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvoiceId || !paymentAmount) {
      setModalError("Please select an invoice and specify an amount.");
      return;
    }

    const amountNum = parseFloat(paymentAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setModalError("Payment amount must be greater than zero.");
      return;
    }

    if (balanceInfo && amountNum > Number(balanceInfo.outstanding_balance)) {
      setModalError(
        `Amount (₹${amountNum.toFixed(2)}) exceeds remaining outstanding balance (₹${Number(
          balanceInfo.outstanding_balance
        ).toFixed(2)}).`
      );
      return;
    }

    setSubmittingPayment(true);
    setModalError(null);

    try {
      const res = await api.preparePayment({
        invoice_id: parseInt(selectedInvoiceId, 10),
        amount: amountNum,
        payment_method: paymentMethod,
        scheduled_date: scheduledDate,
        comments: comments || undefined,
      });

      setToastMessage({
        type: "success",
        text: `Payment ${res.payment_reference} scheduled successfully. Remaining: ₹${Number(
          res.remaining_balance_after
        ).toFixed(2)}`,
      });

      setIsModalOpen(false);
      setSelectedInvoiceId("");
      setBalanceInfo(null);
      setPaymentAmount("");
      setComments("");
      loadData();
    } catch (err: any) {
      setModalError(err.message || "Failed to prepare payment.");
    } finally {
      setSubmittingPayment(false);
    }
  };

  // KPI Calculations
  const stats = useMemo(() => {
    let totalSettled = 0;
    let totalScheduled = 0;
    let settledCount = 0;

    payments.forEach((p) => {
      const amt = Number(p.amount) || 0;
      if (p.status === "SETTLED") {
        totalSettled += amt;
        settledCount += 1;
      } else if (p.status === "SCHEDULED") {
        totalScheduled += amt;
      }
    });

    const settlementRate = payments.length > 0 ? (settledCount / payments.length) * 100 : 0;

    return {
      totalSettled,
      totalScheduled,
      totalCount: payments.length,
      settlementRate,
    };
  }, [payments]);

  // Filtered Payments
  const filteredPayments = useMemo(() => {
    return payments.filter((p) => {
      const matchesSearch =
        p.payment_reference.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.invoice_id.toString().includes(searchQuery) ||
        p.payment_method.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus = statusFilter === "ALL" || p.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [payments, searchQuery, statusFilter]);

  // Candidate invoices for payment preparation (Approved and not fully paid)
  const candidateInvoices = useMemo(() => {
    return invoices.filter((inv) => inv.approval_status === "APPROVED" && inv.payment_status !== "PAID");
  }, [invoices]);

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`p-4 rounded-xl border flex items-center justify-between text-xs ${
            toastMessage.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-rose-50 border-rose-200 text-rose-900"
          }`}
        >
          <div className="flex items-center space-x-2">
            {toastMessage.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0" />
            )}
            <span className="font-medium">{toastMessage.text}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-slate-400 hover:text-slate-600 font-bold"
          >
            ×
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <CreditCard className="h-5 w-5 text-sky-600" />
            <span>Disbursements & Payment Execution Simulation</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Orchestrate partial and full disbursements, monitor outstanding AP liabilities, and simulate settlements
          </p>
        </div>
        <div className="flex items-center space-x-2.5">
          <button
            onClick={loadData}
            title="Refresh payment records"
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={() => {
              setIsModalOpen(true);
              setModalError(null);
            }}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-sm transition"
          >
            <Plus className="h-4 w-4" />
            <span>Prepare Disbursement</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Settled</span>
            <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
              <CheckCircle className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2">
            <span className="text-lg font-bold font-mono text-slate-900">
              {formatCurrency(stats.totalSettled)}
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">Total executed disbursements</p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Pending Scheduled</span>
            <div className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2">
            <span className="text-lg font-bold font-mono text-slate-900">
              {formatCurrency(stats.totalScheduled)}
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">Queued disbursement orders</p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Disbursement Records</span>
            <div className="p-1.5 rounded-lg bg-sky-50 text-sky-600">
              <FileText className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2">
            <span className="text-lg font-bold font-mono text-slate-900">
              {stats.totalCount}
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">Total registered disbursements</p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200/90 bg-white shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Settlement Rate</span>
            <div className="p-1.5 rounded-lg bg-purple-50 text-purple-600">
              <ArrowUpRight className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-2">
            <span className="text-lg font-bold font-mono text-slate-900">
              {stats.settlementRate.toFixed(1)}%
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">Completed batch completion</p>
          </div>
        </div>
      </div>

      {/* Main Payment Registry */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden">
        {/* Table Toolbar */}
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Payment Batch Registry</h3>
            <p className="text-xs text-slate-500">Live payment orders linked to approved invoices</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Search */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search ref or invoice..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/20 w-44 sm:w-56"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="py-1.5 px-2.5 text-xs rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            >
              <option value="ALL">All Statuses</option>
              <option value="SCHEDULED">Scheduled</option>
              <option value="SETTLED">Settled</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>

        {loading ? (
          <TableSkeleton rows={5} />
        ) : filteredPayments.length === 0 ? (
          <EmptyState
            title="No payment batches found"
            description="No disbursements match your filter criteria. Use 'Prepare Disbursement' to schedule a payment."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3.5 px-4">Payment Ref #</th>
                  <th className="py-3.5 px-4">Invoice #</th>
                  <th className="py-3.5 px-4">Method</th>
                  <th className="py-3.5 px-4">Scheduled Date</th>
                  <th className="py-3.5 px-4">Settled Date</th>
                  <th className="py-3.5 px-4">Amount</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredPayments.map((p) => {
                  const isSimulating = simulatingId === p.id;
                  return (
                    <tr key={p.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">
                        {p.payment_reference}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-700">
                        <Link
                          href={`/invoices/${p.invoice_id}`}
                          className="hover:text-sky-600 inline-flex items-center space-x-1"
                        >
                          <span>Invoice #{p.invoice_id}</span>
                          <ArrowUpRight className="h-3 w-3 text-slate-400" />
                        </Link>
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-800">
                        <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-700">
                          {p.payment_method}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500">{formatDate(p.scheduled_date)}</td>
                      <td className="py-3 px-4 text-slate-500">
                        {p.payment_date ? formatDate(p.payment_date) : "—"}
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">
                        {formatCurrency(p.amount)}
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={p.status} type="payment" />
                      </td>
                      <td className="py-3 px-4 text-right">
                        {p.status === "SCHEDULED" ? (
                          <button
                            onClick={() => handleSimulate(p.id)}
                            disabled={isSimulating}
                            className="inline-flex items-center space-x-1 px-3 py-1 rounded bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white font-medium text-xs shadow-sm transition"
                          >
                            <Send className={`h-3 w-3 ${isSimulating ? "animate-pulse" : ""}`} />
                            <span>{isSimulating ? "Settling..." : "Simulate Settlement"}</span>
                          </button>
                        ) : (
                          <span className="text-emerald-700 font-semibold text-xs inline-flex items-center space-x-1">
                            <CheckCircle className="h-3.5 w-3.5" />
                            <span>Settled</span>
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Prepare Disbursement Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                  <CreditCard className="h-4 w-4 text-sky-600" />
                  <span>Prepare New Disbursement Order</span>
                </h3>
                <p className="text-xs text-slate-500">
                  Schedule full or partial payment with automated balance reconciliation
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handlePreparePayment} className="p-5 space-y-4 text-xs">
              {modalError && (
                <div className="p-3 rounded-lg border border-rose-200 bg-rose-50 text-rose-800 flex items-start space-x-2">
                  <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <span>{modalError}</span>
                </div>
              )}

              {/* Step 1: Select Invoice */}
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-700">Select Approved Invoice *</label>
                <select
                  value={selectedInvoiceId}
                  onChange={(e) => setSelectedInvoiceId(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                  required
                >
                  <option value="">-- Choose an approved invoice --</option>
                  {candidateInvoices.map((inv) => (
                    <option key={inv.id} value={inv.id}>
                      Invoice #{inv.invoice_number} (ID: {inv.id}) — {formatCurrency(inv.total_amount)} — {inv.payment_status}
                    </option>
                  ))}
                </select>
                {candidateInvoices.length === 0 && (
                  <p className="text-[11px] text-amber-600">
                    No approved unpaid/partial invoices currently found in the system.
                  </p>
                )}
              </div>

              {/* Live Invoice Balance Card */}
              {loadingBalance ? (
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-100 animate-pulse text-slate-400">
                  Calculating outstanding ledger balance...
                </div>
              ) : balanceInfo ? (
                <div className="p-3.5 rounded-xl border border-sky-100 bg-sky-50/60 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sky-950">Invoice Balance Breakdown</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-200 text-sky-900">
                      {balanceInfo.payment_status}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center pt-1 font-mono">
                    <div className="p-2 rounded-lg bg-white border border-sky-100">
                      <span className="text-[10px] text-slate-400 block font-sans">Total Invoiced</span>
                      <span className="font-bold text-slate-900">
                        {formatCurrency(balanceInfo.total_invoiced_amount)}
                      </span>
                    </div>
                    <div className="p-2 rounded-lg bg-white border border-sky-100">
                      <span className="text-[10px] text-slate-400 block font-sans">Already Settled</span>
                      <span className="font-bold text-emerald-700">
                        {formatCurrency(balanceInfo.total_paid_amount)}
                      </span>
                    </div>
                    <div className="p-2 rounded-lg bg-white border border-sky-100">
                      <span className="text-[10px] text-slate-400 block font-sans">Outstanding</span>
                      <span className="font-bold text-sky-700">
                        {formatCurrency(balanceInfo.outstanding_balance)}
                      </span>
                    </div>
                  </div>
                </div>
              ) : null}

              {/* Step 2: Payment Parameters */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label className="font-semibold text-slate-700">Disbursement Amount (₹) *</label>
                    {balanceInfo && (
                      <button
                        type="button"
                        onClick={() => setPaymentAmount(balanceInfo.outstanding_balance.toString())}
                        className="text-[10px] text-sky-600 hover:underline font-bold"
                      >
                        Pay Max
                      </button>
                    )}
                  </div>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                    placeholder="0.00"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 font-mono font-bold focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-semibold text-slate-700">Payment Method *</label>
                  <select
                    value={paymentMethod}
                    onChange={(e) => setPaymentMethod(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                  >
                    <option value="ACH">ACH Direct Deposit</option>
                    <option value="WIRE">Wire Transfer</option>
                    <option value="CHECK">University Check</option>
                    <option value="LEDGER_TRANSFER">Internal Ledger Transfer</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-700">Scheduled Settlement Date *</label>
                <input
                  type="date"
                  value={scheduledDate}
                  onChange={(e) => setScheduledDate(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-700">Payment Memo / Notes</label>
                <input
                  type="text"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Optional university disbursement memo..."
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>

              {/* Modal Actions */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingPayment || !selectedInvoiceId || !paymentAmount}
                  className="px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white font-bold shadow-sm transition inline-flex items-center space-x-1.5"
                >
                  <Send className="h-3.5 w-3.5" />
                  <span>{submittingPayment ? "Scheduling..." : "Schedule Disbursement"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
