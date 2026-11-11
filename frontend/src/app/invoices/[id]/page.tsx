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
  Download,
  Save,
  Check,
  Sparkles,
  FileSearch,
  ExternalLink,
} from "lucide-react";
import { api } from "@/services/api";
import { Invoice, Vendor, Department, PurchaseOrder } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/utils";

export default function InvoiceDetailPage() {
  const params = useParams();
  const invoiceId = parseInt(params.id as string);

  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationSuccess, setValidationSuccess] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [showRawText, setShowRawText] = useState(false);

  // Editable Form State
  const [formData, setFormData] = useState({
    vendor_id: "",
    department_id: "",
    purchase_order_id: "",
    invoice_number: "",
    invoice_date: "",
    due_date: "",
    subtotal: "",
    tax_amount: "",
    total_amount: "",
    currency: "USD",
    description: "",
    tax_identifier: "",
  });

  const loadData = () => {
    if (invoiceId) {
      Promise.all([
        api.getInvoiceById(invoiceId),
        api.getVendors(),
        api.getDepartments(),
        api.getPurchaseOrders(),
      ])
        .then(([inv, vList, dList, poList]) => {
          setInvoice(inv);
          setVendors(vList);
          setDepartments(dList);
          setPurchaseOrders(poList);

          setFormData({
            vendor_id: inv.vendor_id ? inv.vendor_id.toString() : "",
            department_id: inv.department_id ? inv.department_id.toString() : "",
            purchase_order_id: inv.purchase_order_id ? inv.purchase_order_id.toString() : "",
            invoice_number: inv.invoice_number || "",
            invoice_date: inv.invoice_date || "",
            due_date: inv.due_date || "",
            subtotal: inv.subtotal ? inv.subtotal.toString() : "0.00",
            tax_amount: inv.tax_amount ? inv.tax_amount.toString() : "0.00",
            total_amount: inv.total_amount ? inv.total_amount.toString() : "0.00",
            currency: inv.currency || "USD",
            description: inv.description || "",
            tax_identifier: inv.tax_identifier || "",
          });

          setLoading(false);
        })
        .catch((err) => {
          setValidationError(err.message || "Failed to load invoice details");
          setLoading(false);
        });
    }
  };

  useEffect(() => {
    loadData();
  }, [invoiceId]);

  const handleSaveCorrections = async () => {
    setSaving(true);
    setValidationSuccess(null);
    setValidationError(null);

    try {
      const updated = await api.reviewInvoice(invoiceId, {
        vendor_id: formData.vendor_id ? parseInt(formData.vendor_id) : undefined,
        department_id: formData.department_id ? parseInt(formData.department_id) : undefined,
        purchase_order_id: formData.purchase_order_id ? parseInt(formData.purchase_order_id) : undefined,
        invoice_number: formData.invoice_number || undefined,
        invoice_date: formData.invoice_date || undefined,
        due_date: formData.due_date || undefined,
        subtotal: formData.subtotal || undefined,
        tax_amount: formData.tax_amount || undefined,
        total_amount: formData.total_amount || undefined,
        currency: formData.currency,
        description: formData.description,
        tax_identifier: formData.tax_identifier,
      });

      setInvoice(updated);
      setValidationSuccess("Corrections saved successfully to audit log.");
      setSaving(false);
    } catch (err: any) {
      setValidationError(err.message || "Failed to save corrections.");
      setSaving(false);
    }
  };

  const handleValidateInvoice = async () => {
    setValidating(true);
    setValidationSuccess(null);
    setValidationError(null);

    // Save current form state first
    await handleSaveCorrections();

    try {
      const result = await api.validateInvoice(invoiceId);
      setInvoice(result.invoice);
      setValidationSuccess("Invoice successfully validated! Ready for approval and three-way matching.");
      setValidating(false);
      loadData();
    } catch (err: any) {
      setValidationError(err.message || "Invoice validation failed.");
      setValidating(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-96 rounded-xl lg:col-span-2" />
          <Skeleton className="h-96 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!invoice) {
    return (
      <EmptyState
        title="Invoice not found"
        description="The requested invoice could not be retrieved from the database."
        actionText="Back to Invoices"
        onAction={() => window.history.back()}
      />
    );
  }

  const isReviewable = ["NEEDS_REVIEW", "UPLOADED", "EXTRACTED", "DUPLICATE", "VALIDATED"].includes(
    invoice.processing_status
  );

  return (
    <div className="space-y-8">
      {/* Top Header */}
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
              File: <span className="font-semibold text-slate-700">{invoice.original_filename || "N/A"}</span> • Uploaded {formatDateTime(invoice.created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          {invoice.document_path && (
            <a
              href={api.getDocumentUrl(invoice.id)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm transition"
            >
              <Download className="h-3.5 w-3.5 text-slate-500" />
              <span>Download Document</span>
            </a>
          )}
          {invoice.purchase_order && (
            <Link
              href="/matching"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-sm transition"
            >
              <GitCompare className="h-3.5 w-3.5 text-sky-600" />
              <span>3-Way Match Record</span>
            </Link>
          )}
        </div>
      </div>

      {/* Duplicate / Fraud Alert Banner */}
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

      {/* Validation Feedback Messages */}
      {validationSuccess && (
        <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50 text-xs text-emerald-800 flex items-center space-x-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
          <span>{validationSuccess}</span>
        </div>
      )}
      {validationError && (
        <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-xs text-rose-800 flex items-center space-x-2">
          <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Human Review & Field Correction Panel */}
      {isReviewable && (
        <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <FileSearch className="h-4 w-4 text-sky-600" />
                <span>Human Review & Field Validation</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Review OCR extracted parameters, resolve missing values, and validate invoice for university accounting
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <button
                disabled={saving}
                onClick={handleSaveCorrections}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
              >
                <Save className="h-3.5 w-3.5 text-slate-500" />
                <span>{saving ? "Saving..." : "Save Changes"}</span>
              </button>
              <button
                disabled={validating}
                onClick={handleValidateInvoice}
                className="inline-flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition"
              >
                <Check className="h-3.5 w-3.5" />
                <span>{validating ? "Validating..." : "Validate Invoice"}</span>
              </button>
            </div>
          </div>

          {/* Form Fields Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            {/* Vendor */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Vendor / Supplier *</label>
              <select
                value={formData.vendor_id}
                onChange={(e) => setFormData({ ...formData, vendor_id: e.target.value })}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              >
                <option value="">-- Select Registered Supplier --</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.vendor_code} — {v.legal_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Department */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Department *</label>
              <select
                value={formData.department_id}
                onChange={(e) => setFormData({ ...formData, department_id: e.target.value })}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              >
                <option value="">-- Select Department --</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code} — {d.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Invoice Number */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Invoice Number *</label>
              <input
                type="text"
                value={formData.invoice_number}
                onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
                placeholder="e.g. INV-2025-001"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Purchase Order */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Linked Purchase Order</label>
              <select
                value={formData.purchase_order_id}
                onChange={(e) => setFormData({ ...formData, purchase_order_id: e.target.value })}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              >
                <option value="">-- No PO Linked / Direct Spend --</option>
                {purchaseOrders.map((po) => (
                  <option key={po.id} value={po.id}>
                    {po.po_number} ({formatCurrency(po.total_amount)})
                  </option>
                ))}
              </select>
            </div>

            {/* Invoice Date */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Invoice Date *</label>
              <input
                type="date"
                value={formData.invoice_date}
                onChange={(e) => setFormData({ ...formData, invoice_date: e.target.value })}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Due Date */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Due Date *</label>
              <input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Subtotal */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Subtotal Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.subtotal}
                onChange={(e) => setFormData({ ...formData, subtotal: e.target.value })}
                placeholder="0.00"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Tax Amount */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Tax Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.tax_amount}
                onChange={(e) => setFormData({ ...formData, tax_amount: e.target.value })}
                placeholder="0.00"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Total Amount */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-700">Total Invoiced Amount *</label>
              <input
                type="number"
                step="0.01"
                value={formData.total_amount}
                onChange={(e) => setFormData({ ...formData, total_amount: e.target.value })}
                placeholder="0.00"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>
          </div>
        </div>
      )}

      {/* OCR Telemetry & Raw Text Accordion */}
      <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-50 text-sky-700">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-slate-900">OCR Extraction Telemetry</h4>
              <p className="text-[11px] text-slate-500">
                Method: <span className="font-mono text-slate-700">{invoice.ocr_method || "N/A"}</span> • Confidence:{" "}
                <span className="font-mono font-semibold text-slate-800">
                  {invoice.confidence_score ? `${invoice.confidence_score}%` : "Manual Entry"}
                </span>{" "}
                • Hash: <span className="font-mono text-[10px] text-slate-400">{invoice.file_hash?.slice(0, 16)}...</span>
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowRawText(!showRawText)}
            className="text-xs font-semibold text-sky-600 hover:text-sky-800"
          >
            {showRawText ? "Hide Raw Text" : "View Extracted Raw Text"}
          </button>
        </div>

        {showRawText && (
          <div className="mt-3 p-4 rounded-xl bg-slate-950 text-slate-200 font-mono text-[11px] max-h-60 overflow-y-auto whitespace-pre-wrap border border-slate-800">
            {invoice.raw_text || "No raw text recorded for this invoice."}
          </div>
        )}
      </div>

      {/* Line Items Table */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-900">Invoice Line Items</h3>
          <p className="text-xs text-slate-500">Extracted and validated itemized service and goods lines</p>
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
                    Document processed as single summarized expense. Itemized lines can be attached upon matching.
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
              <p className="text-xs text-slate-400 py-4 text-center">
                Invoice pending validation. Approvals trigger upon validation.
              </p>
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
