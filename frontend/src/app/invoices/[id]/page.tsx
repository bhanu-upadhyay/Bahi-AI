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
  Calculator,
} from "lucide-react";
import { api } from "@/services/api";
import { Invoice, Vendor, Department, PurchaseOrder } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { MultiAgentHub } from "@/components/invoices/MultiAgentHub";
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
    currency: "INR",
    description: "",
    tax_identifier: "",
    cgst_amount: "",
    sgst_amount: "",
    igst_amount: "",
    customer_name: "",
    customer_gstin: "",
  });

  // Track initial extracted values to distinguish Extracted vs User-Corrected
  const [initialExtracted, setInitialExtracted] = useState<Record<string, any>>({});

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

          const gst = inv.extraction_metadata?.gst_breakdown || {};
          const initVals = {
            vendor_id: inv.vendor_id ? inv.vendor_id.toString() : "",
            department_id: inv.department_id ? inv.department_id.toString() : "",
            purchase_order_id: inv.purchase_order_id ? inv.purchase_order_id.toString() : "",
            invoice_number: inv.invoice_number || "",
            invoice_date: inv.invoice_date || "",
            due_date: inv.due_date || "",
            subtotal: inv.subtotal ? inv.subtotal.toString() : (gst.taxable_subtotal || "0.00"),
            tax_amount: inv.tax_amount ? inv.tax_amount.toString() : (gst.total_tax || "0.00"),
            total_amount: inv.total_amount ? inv.total_amount.toString() : (gst.grand_total || "0.00"),
            currency: inv.currency || "INR",
            description: inv.description || "",
            tax_identifier: inv.tax_identifier || gst.supplier_gstin || "",
            cgst_amount: gst.cgst_amount || "",
            sgst_amount: gst.sgst_amount || "",
            igst_amount: gst.igst_amount || "",
            customer_name: gst.customer_name || "",
            customer_gstin: gst.customer_gstin || "",
          };

          setFormData(initVals);
          setInitialExtracted(initVals);
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
        cgst_amount: formData.cgst_amount || undefined,
        sgst_amount: formData.sgst_amount || undefined,
        igst_amount: formData.igst_amount || undefined,
        customer_name: formData.customer_name || undefined,
        customer_gstin: formData.customer_gstin || undefined,
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
      const detail = err.detail || err.message;
      if (typeof detail === "object" && detail?.errors) {
        setValidationError(`Validation Failed: ${detail.errors.join("; ")}`);
      } else {
        setValidationError(err.message || "Invoice validation failed.");
      }
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

  const gstBreakdown = invoice.extraction_metadata?.gst_breakdown || {};
  const fieldConfs = invoice.extraction_metadata?.field_confidences || {};
  const reconciliationStatus = gstBreakdown.reconciliation_status || invoice.extraction_metadata?.reconciliation_status;
  const reconciliationMessage = gstBreakdown.reconciliation_message || invoice.extraction_metadata?.reconciliation_message;

  // Live reconciliation calculation for current inputs
  const subNum = parseFloat(formData.subtotal || "0");
  const cgstNum = parseFloat(formData.cgst_amount || "0");
  const sgstNum = parseFloat(formData.sgst_amount || "0");
  const igstNum = parseFloat(formData.igst_amount || "0");
  const taxNum = (cgstNum || sgstNum) ? (cgstNum + sgstNum) : (igstNum ? igstNum : parseFloat(formData.tax_amount || "0"));
  const totNum = parseFloat(formData.total_amount || "0");
  const liveExpectedTot = subNum + taxNum;
  const liveDiff = Math.abs(liveExpectedTot - totNum);
  const isLiveReconciled = liveDiff <= 0.05 || (liveDiff <= 1.00 && gstBreakdown.roundoff_amount);

  // Helper to determine whether a field was modified by user
  const isFieldModified = (fieldName: string) => {
    return initialExtracted[fieldName] !== undefined && formData[fieldName as keyof typeof formData] !== initialExtracted[fieldName];
  };

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

      {/* Financial Reconciliation Status Banner */}
      <div className={`p-4 rounded-xl border flex items-center justify-between text-xs ${
        isLiveReconciled
          ? "border-emerald-200 bg-emerald-50 text-emerald-900"
          : "border-amber-200 bg-amber-50 text-amber-900"
      }`}>
        <div className="flex items-center space-x-2.5">
          <Calculator className={`h-4 w-4 ${isLiveReconciled ? "text-emerald-600" : "text-amber-600"}`} />
          <div>
            <span className="font-bold">
              {isLiveReconciled ? "Financial Math Reconciled" : "Financial Reconciliation Warning"}
            </span>
            <p className="text-[11px] opacity-80">
              Taxable Subtotal ({formatCurrency(subNum)}) + Total Tax ({formatCurrency(taxNum)}) = {formatCurrency(liveExpectedTot)} • Invoiced Grand Total: {formatCurrency(totNum)}
              {!isLiveReconciled && ` (Difference: ${formatCurrency(liveDiff)})`}
            </p>
          </div>
        </div>
        <span className={`px-2.5 py-1 rounded-full font-mono text-[11px] font-bold ${
          isLiveReconciled ? "bg-emerald-200 text-emerald-900" : "bg-amber-200 text-amber-900"
        }`}>
          {isLiveReconciled ? "RECONCILED" : "DISCREPANCY"}
        </span>
      </div>

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

      {/* Multi-Agent AI Automation Hub */}
      <MultiAgentHub invoice={invoice} onInvoiceUpdated={loadData} />

      {/* Human Review & Field Correction Panel */}
      {isReviewable && (
        <div className="bg-white rounded-2xl border border-slate-200/90 p-6 shadow-sm space-y-6">
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-xs">
            {/* Vendor / Supplier */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Vendor / Supplier *</label>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  isFieldModified("vendor_id") ? "bg-amber-100 text-amber-800" : "bg-sky-100 text-sky-800"
                }`}>
                  {isFieldModified("vendor_id") ? "User-Corrected" : "Extracted (OCR)"}
                </span>
              </div>
              {gstBreakdown.supplier_name && (
                <p className="text-[11px] text-slate-500 font-medium">
                  OCR Header: <span className="text-slate-800 font-bold">{gstBreakdown.supplier_name}</span>
                </p>
              )}
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
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Department *</label>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  isFieldModified("department_id") ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"
                }`}>
                  {isFieldModified("department_id") ? "User-Assigned" : "Department"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Allocated budget unit</p>
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
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Invoice Number *</label>
                <span className="text-[10px] text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded font-mono">
                  {(fieldConfs.invoice_number ? fieldConfs.invoice_number * 100 : 95).toFixed(0)}% Conf
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Extracted from invoice header</p>
              <input
                type="text"
                value={formData.invoice_number}
                onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
                placeholder="e.g. 9766 or INV-2025-001"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Supplier GSTIN / Tax ID */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Supplier GSTIN / Tax ID</label>
                <span className="text-[10px] text-sky-700 bg-sky-100 px-1.5 py-0.5 rounded font-mono">
                  {(fieldConfs.tax_identifier ? fieldConfs.tax_identifier * 100 : 95).toFixed(0)}% Conf
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Tax Identification</p>
              <input
                type="text"
                value={formData.tax_identifier}
                onChange={(e) => setFormData({ ...formData, tax_identifier: e.target.value })}
                placeholder="e.g. 08HWZOU5586H5Z7"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Customer / Billed To */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Customer / Billed To</label>
                <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                  {formData.customer_name ? "Extracted" : "Optional"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Invoice recipient entity</p>
              <input
                type="text"
                value={formData.customer_name}
                onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                placeholder="e.g. Agrawal Infotech"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Customer GSTIN */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Customer GSTIN</label>
                <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                  {formData.customer_gstin ? "Extracted" : "Optional"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Customer tax registration</p>
              <input
                type="text"
                value={formData.customer_gstin}
                onChange={(e) => setFormData({ ...formData, customer_gstin: e.target.value })}
                placeholder="e.g. 08FEYMY0855T9ZT"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Linked Purchase Order */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Linked Purchase Order</label>
                <span className="text-[10px] text-slate-400">Optional</span>
              </div>
              <p className="text-[11px] text-slate-400">Match against university PO</p>
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
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Invoice Date *</label>
                <span className="text-[10px] text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded font-mono">
                  {(fieldConfs.invoice_date ? fieldConfs.invoice_date * 100 : 95).toFixed(0)}% Conf
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Issue date of document</p>
              <input
                type="date"
                value={formData.invoice_date}
                onChange={(e) => setFormData({ ...formData, invoice_date: e.target.value })}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>

            {/* Due Date */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-slate-700">Due Date *</label>
                <span className="text-[10px] text-slate-400">Payment Terms</span>
              </div>
              <p className="text-[11px] text-slate-400">Payment deadline</p>
              <input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
              />
            </div>
          </div>

          {/* Financial Breakdown Section */}
          <div className="pt-4 border-t border-slate-100 space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Financial Values & Tax Breakdown
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
              {/* Taxable Subtotal */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="font-semibold text-slate-700">Taxable Subtotal</label>
                  <span className="text-[10px] text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded font-mono">
                    {(fieldConfs.subtotal ? fieldConfs.subtotal * 100 : 95).toFixed(0)}% Conf
                  </span>
                </div>
                <input
                  type="number"
                  step="0.01"
                  value={formData.subtotal}
                  onChange={(e) => setFormData({ ...formData, subtotal: e.target.value })}
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>

              {/* CGST Amount */}
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">CGST Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.cgst_amount}
                  onChange={(e) => setFormData({ ...formData, cgst_amount: e.target.value })}
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>

              {/* SGST Amount */}
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">SGST Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.sgst_amount}
                  onChange={(e) => setFormData({ ...formData, sgst_amount: e.target.value })}
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>

              {/* IGST Amount */}
              <div className="space-y-1">
                <label className="font-semibold text-slate-700">IGST Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.igst_amount}
                  onChange={(e) => setFormData({ ...formData, igst_amount: e.target.value })}
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>

              {/* Total Tax Amount */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label className="font-semibold text-slate-700">Total Tax</label>
                  <span className="text-[10px] text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded font-mono">
                    {(fieldConfs.tax_amount ? fieldConfs.tax_amount * 100 : 95).toFixed(0)}% Conf
                  </span>
                </div>
                <input
                  type="number"
                  step="0.01"
                  value={formData.tax_amount}
                  onChange={(e) => setFormData({ ...formData, tax_amount: e.target.value })}
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>

              {/* Grand Total */}
              <div className="space-y-1 md:col-span-2">
                <div className="flex items-center justify-between">
                  <label className="font-semibold text-slate-900">Grand Total Invoiced *</label>
                  <span className="text-[10px] text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded font-mono">
                    {(fieldConfs.total_amount ? fieldConfs.total_amount * 100 : 95).toFixed(0)}% Conf
                  </span>
                </div>
                <input
                  type="number"
                  step="0.01"
                  value={formData.total_amount}
                  onChange={(e) => setFormData({ ...formData, total_amount: e.target.value })}
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 font-mono font-bold text-slate-900 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>
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
              <tr className="bg-slate-50 border-b border-slate-100 text-slate-500 font-semibold">
                <th className="py-2.5 px-4 w-16">#</th>
                <th className="py-2.5 px-4">Description</th>
                <th className="py-2.5 px-4 text-right">Qty</th>
                <th className="py-2.5 px-4 text-right">Unit Price</th>
                <th className="py-2.5 px-4 text-right">Tax Rate</th>
                <th className="py-2.5 px-4 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invoice.lines && invoice.lines.length > 0 ? (
                invoice.lines.map((line) => (
                  <tr key={line.id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-4 font-mono text-slate-400">{line.line_number}</td>
                    <td className="py-2.5 px-4 font-medium text-slate-800">{line.description}</td>
                    <td className="py-2.5 px-4 text-right font-mono">{line.quantity}</td>
                    <td className="py-2.5 px-4 text-right font-mono">{formatCurrency(line.unit_price)}</td>
                    <td className="py-2.5 px-4 text-right font-mono">{line.tax_rate}%</td>
                    <td className="py-2.5 px-4 text-right font-mono font-bold text-slate-900">
                      {formatCurrency(line.line_total)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-6 text-center text-slate-400 text-xs">
                    No itemized lines recorded. Subtotal and tax extracted from document totals summary.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
