"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Building2,
  Calendar,
  CreditCard,
  FileText,
  GitCompare,
  ShieldAlert,
  CheckCircle2,
  Clock,
  AlertTriangle,
  UserCheck,
  Package,
} from "lucide-react";
import { api } from "@/services/api";
import { Invoice } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/utils";

export default function InvoiceDetailPage() {
  const params = useParams();
  const invoiceId = parseInt(params.id as string);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (invoiceId) {
      api
        .getInvoiceById(invoiceId)
        .then((res) => {
          setInvoice(res);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message || "Failed to load invoice details");
          setLoading(false);
        });
    }
  }, [invoiceId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-64 rounded-xl lg:col-span-2" />
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <EmptyState
        title="Invoice not found"
        description={error || "The requested invoice could not be retrieved from the database."}
        actionText="Back to Invoices"
        onAction={() => window.history.back()}
      />
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Breadcrumb & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <Link
            href="/invoices"
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold tracking-tight text-slate-900 font-mono">
                {invoice.invoice_number}
              </h2>
              <StatusBadge status={invoice.processing_status} type="processing" />
              <StatusBadge status={invoice.approval_status} type="approval" />
              <StatusBadge status={invoice.payment_status} type="payment" />
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Normalized key: <span className="font-mono text-slate-700">{invoice.normalized_invoice_number}</span> • Registered {formatDate(invoice.created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {invoice.purchase_order && (
            <Link
              href="/matching"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm transition"
            >
              <GitCompare className="h-4 w-4 text-sky-600" />
              <span>3-Way Match Record</span>
            </Link>
          )}
        </div>
      </div>

      {/* Fraud / Anomaly Banner (if active alerts exist) */}
      {invoice.fraud_alerts && invoice.fraud_alerts.length > 0 && (
        <div className="rounded-xl border border-rose-300 bg-rose-50/80 p-5 text-rose-900 shadow-sm">
          <div className="flex items-start space-x-3">
            <ShieldAlert className="h-5 w-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-2 flex-1">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-bold tracking-tight text-rose-900">
                  Risk Engine Exception Flagged
                </h4>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-rose-200 text-rose-900">
                  Risk Score: {invoice.fraud_alerts[0].risk_score} / 100
                </span>
              </div>
              {invoice.fraud_alerts.map((alert) => (
                <div key={alert.id} className="text-xs text-rose-800 space-y-1">
                  <div className="flex items-center space-x-2">
                    <StatusBadge status={alert.severity} type="severity" />
                    <span className="font-semibold">{alert.alert_type}</span>
                  </div>
                  <p className="bg-white/60 p-2.5 rounded-lg border border-rose-200/60 font-sans">
                    {alert.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Overview Metadata Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Vendor Card */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm space-y-3">
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-slate-500 pb-2 border-b border-slate-100">
            <Building2 className="h-4 w-4 text-sky-600" />
            <span>Vendor Details</span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900">
              {invoice.vendor?.legal_name || "Vendor"}
            </h4>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Code: {invoice.vendor?.vendor_code}
            </p>
          </div>
          <div className="text-xs text-slate-600 space-y-1 pt-1">
            <p>Contact: {invoice.vendor?.contact_person}</p>
            <p>Email: {invoice.vendor?.email}</p>
            <p className="font-mono text-[11px]">Tax ID: {invoice.vendor?.tax_identifier}</p>
            <p className="text-slate-400 font-mono text-[11px]">
              Bank: {invoice.vendor?.bank_name} (•••• {invoice.vendor?.bank_account_last_four})
            </p>
          </div>
        </div>

        {/* PO & Department Card */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm space-y-3">
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-slate-500 pb-2 border-b border-slate-100">
            <Package className="h-4 w-4 text-sky-600" />
            <span>Purchase Order & Department</span>
          </div>
          <div>
            <h4 className="text-sm font-bold text-slate-900">
              {invoice.department?.name || "Department"}
            </h4>
            <span className="text-xs font-mono font-medium text-slate-500">
              Dept Code: {invoice.department?.code}
            </span>
          </div>
          <div className="text-xs text-slate-600 space-y-1.5 pt-1">
            <div className="flex justify-between">
              <span>Linked PO:</span>
              <span className="font-mono font-bold text-slate-900">
                {invoice.purchase_order?.po_number || "No PO Linked"}
              </span>
            </div>
            {invoice.purchase_order && (
              <div className="flex justify-between">
                <span>PO Total:</span>
                <span className="font-mono text-slate-800">
                  {formatCurrency(invoice.purchase_order.total_amount)}
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Invoice Date:</span>
              <span>{formatDate(invoice.invoice_date)}</span>
            </div>
            <div className="flex justify-between">
              <span>Due Date:</span>
              <span className="font-semibold text-slate-800">{formatDate(invoice.due_date)}</span>
            </div>
          </div>
        </div>

        {/* Financial Summary Card */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm space-y-3 flex flex-col justify-between">
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-slate-500 pb-2 border-b border-slate-100">
            <CreditCard className="h-4 w-4 text-emerald-600" />
            <span>Financial Breakdown</span>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between text-slate-600">
              <span>Subtotal:</span>
              <span className="font-mono">{formatCurrency(invoice.subtotal)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Tax (GST/VAT):</span>
              <span className="font-mono">{formatCurrency(invoice.tax_amount)}</span>
            </div>
            <div className="pt-2 border-t border-slate-100 flex justify-between items-baseline">
              <span className="text-sm font-bold text-slate-900">Total Payable:</span>
              <span className="text-xl font-bold font-mono text-slate-900">
                {formatCurrency(invoice.total_amount)}
              </span>
            </div>
          </div>
          <div className="pt-2 text-[11px] text-slate-400">
            Payment Status: <span className="font-medium text-slate-700">{invoice.payment_status}</span>
          </div>
        </div>
      </div>

      {/* Invoice Line Items Table */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900">Invoice Line Items</h3>
          <p className="text-xs text-slate-500">Itemized line billing extracted from invoice document</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                <th className="py-3 px-4 w-16">Line</th>
                <th className="py-3 px-4">Item Description</th>
                <th className="py-3 px-4 text-right">Quantity</th>
                <th className="py-3 px-4 text-right">Unit Price</th>
                <th className="py-3 px-4 text-right">Tax Rate</th>
                <th className="py-3 px-4 text-right">Line Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invoice.lines && invoice.lines.length > 0 ? (
                invoice.lines.map((line) => (
                  <tr key={line.id} className="hover:bg-slate-50/60">
                    <td className="py-3 px-4 font-mono text-slate-500">{line.line_number}</td>
                    <td className="py-3 px-4 font-medium text-slate-800">{line.description}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-700">{line.quantity}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-700">{formatCurrency(line.unit_price)}</td>
                    <td className="py-3 px-4 text-right font-mono text-slate-500">{line.tax_rate}%</td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                      {formatCurrency(line.line_total)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-400">
                    No itemized lines available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Approval & Audit Timeline */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Approvals History */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100 flex items-center space-x-2">
            <UserCheck className="h-4 w-4 text-sky-600" />
            <span>Approval Workflow & Decisions</span>
          </h3>

          <div className="mt-4 space-y-3">
            {invoice.approvals && invoice.approvals.length > 0 ? (
              invoice.approvals.map((app) => (
                <div key={app.id} className="p-3 rounded-lg border border-slate-100 bg-slate-50 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900">
                      Level {app.approval_level} • {app.approver?.full_name || "Approver"}
                    </span>
                    <StatusBadge status={app.status} type="approval" />
                  </div>
                  {app.comments && (
                    <p className="text-slate-600 bg-white p-2 rounded border border-slate-200/60 text-[11px]">
                      &quot;{app.comments}&quot;
                    </p>
                  )}
                  <div className="text-[10px] text-slate-400 flex justify-between">
                    <span>Role: {app.approver?.role?.replace("_", " ")}</span>
                    <span>{app.decided_at ? formatDateTime(app.decided_at) : "Pending Review"}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 py-4 text-center">No approval records created yet.</p>
            )}
          </div>
        </div>

        {/* Payments Information */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 pb-3 border-b border-slate-100 flex items-center space-x-2">
            <CreditCard className="h-4 w-4 text-sky-600" />
            <span>Disbursement & Settlement</span>
          </h3>

          <div className="mt-4 space-y-3">
            {invoice.payments && invoice.payments.length > 0 ? (
              invoice.payments.map((p) => (
                <div key={p.id} className="p-3 rounded-lg border border-slate-100 bg-slate-50 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-900">{p.payment_reference}</span>
                    <StatusBadge status={p.status} type="payment" />
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600">
                    <div>Method: <span className="font-medium text-slate-900">{p.payment_method}</span></div>
                    <div>Amount: <span className="font-mono font-bold text-slate-900">{formatCurrency(p.amount)}</span></div>
                    <div>Scheduled: {formatDate(p.scheduled_date)}</div>
                    <div>Settled: {p.payment_date ? formatDate(p.payment_date) : "Pending"}</div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 py-4 text-center">No payment scheduled for this invoice.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

