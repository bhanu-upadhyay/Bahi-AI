"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  Building,
  ShieldAlert,
  Sparkles,
  Eye,
} from "lucide-react";
import { api } from "@/services/api";
import { Department, InvoiceUploadResponse } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatCurrency } from "@/lib/utils";

export default function InvoiceUploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadProgressMsg, setUploadProgressMsg] = useState<string>("");
  const [uploadResult, setUploadResult] = useState<InvoiceUploadResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getDepartments().then(setDepartments).catch(() => {});
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file: File) => {
    setErrorMessage(null);
    setUploadResult(null);

    // Validate size (10 MB limit)
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage(`File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds 10 MB limit.`);
      return;
    }

    // Validate extension
    const validExtensions = [".pdf", ".png", ".jpg", ".jpeg"];
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!validExtensions.includes(ext)) {
      setErrorMessage(`Unsupported file format '${ext}'. Allowed formats: PDF, PNG, JPG, JPEG.`);
      return;
    }

    setSelectedFile(file);
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setErrorMessage(null);
    setUploadProgressMsg("Uploading document to secure server...");

    try {
      setTimeout(() => {
        setUploadProgressMsg("Running PyMuPDF & Tesseract OCR text extraction...");
      }, 500);

      setTimeout(() => {
        setUploadProgressMsg("Matching supplier against university registry & checking duplicates...");
      }, 1200);

      const deptId = selectedDept ? parseInt(selectedDept) : undefined;
      const result = await api.uploadInvoice(selectedFile, deptId);

      setUploadResult(result);
      setUploading(false);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to process invoice upload.");
      setUploading(false);
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setUploadResult(null);
    setErrorMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Link
            href="/invoices"
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900">
              Supplier Invoice Intake & OCR Processing
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated optical character recognition, digital PDF parsing, and duplicate screening
            </p>
          </div>
        </div>
      </div>

      {!uploadResult ? (
        <div className="bg-white rounded-2xl border border-slate-200/90 p-8 shadow-sm space-y-6">
          {/* Department Selection */}
          <div className="max-w-md space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 flex items-center space-x-1.5">
              <Building className="h-3.5 w-3.5 text-slate-400" />
              <span>Chargeable University Department (Optional)</span>
            </label>
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="w-full text-xs rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            >
              <option value="">Auto-Detect from Document or Assign Later</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.code} — {d.name}
                </option>
              ))}
            </select>
          </div>

          {/* Drag & Drop Dropzone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all ${
              dragActive
                ? "border-sky-500 bg-sky-50/50 scale-[1.01]"
                : "border-slate-200 hover:border-sky-400 bg-slate-50/50 hover:bg-white"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={handleFileChange}
              className="hidden"
            />

            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 shadow-sm">
                <UploadCloud className="h-7 w-7" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-bold text-slate-900">
                  Drag and drop supplier invoice here, or{" "}
                  <span className="text-sky-600 underline font-semibold">browse computer</span>
                </p>
                <p className="text-xs text-slate-500">
                  Accepts PDF documents (digital & scanned) and high-res images (PNG, JPG, JPEG) up to 10 MB
                </p>
              </div>
            </div>
          </div>

          {/* Selected File Card */}
          {selectedFile && (
            <div className="flex items-center justify-between p-4 rounded-xl border border-slate-200 bg-slate-50">
              <div className="flex items-center space-x-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white border border-slate-200 text-sky-600">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900">{selectedFile.name}</h4>
                  <p className="text-[11px] text-slate-500">
                    {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || "Document"}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={resetForm}
                className="text-xs text-slate-400 hover:text-slate-600"
              >
                Change
              </button>
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
            <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-xs text-rose-800 flex items-start space-x-2.5">
              <AlertTriangle className="h-4 w-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Upload Progress Indicator */}
          {uploading && (
            <div className="p-4 rounded-xl border border-sky-200 bg-sky-50 text-xs text-sky-800 space-y-2">
              <div className="flex items-center justify-between font-semibold">
                <span className="flex items-center space-x-2">
                  <RefreshCw className="h-3.5 w-3.5 animate-spin text-sky-600" />
                  <span>{uploadProgressMsg}</span>
                </span>
                <span className="text-[11px] font-mono">Processing...</span>
              </div>
              <div className="w-full bg-sky-200 rounded-full h-1.5 overflow-hidden">
                <div className="h-1.5 bg-sky-600 rounded-full animate-pulse w-3/4"></div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-100">
            <Link
              href="/invoices"
              className="px-4 py-2 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
            >
              Cancel
            </Link>
            <button
              disabled={!selectedFile || uploading}
              onClick={handleUploadSubmit}
              className={`px-5 py-2 rounded-lg text-xs font-bold text-white shadow-sm flex items-center space-x-1.5 transition ${
                !selectedFile || uploading
                  ? "bg-slate-400 cursor-not-allowed"
                  : "bg-sky-600 hover:bg-sky-700 shadow-sky-900/20"
              }`}
            >
              <span>{uploading ? "Extracting..." : "Process Document"}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      ) : (
        /* Extraction Complete Overview Card */
        <div className="bg-white rounded-2xl border border-slate-200/90 p-8 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Document Extracted Successfully
                </h3>
                <p className="text-xs text-slate-500">
                  OCR Engine: <span className="font-mono text-slate-700">{uploadResult.ocr_method}</span> • Server Filename: <span className="font-mono">{uploadResult.original_filename}</span>
                </p>
              </div>
            </div>
            <StatusBadge status={uploadResult.processing_status} type="processing" />
          </div>

          {/* Duplicate Alert Banner if duplicate */}
          {uploadResult.is_duplicate && (
            <div className="rounded-xl border border-rose-300 bg-rose-50 p-4 text-xs text-rose-900 flex items-start space-x-3">
              <ShieldAlert className="h-5 w-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="font-bold text-rose-900">Duplicate Submission Detected</h4>
                <p>{uploadResult.duplicate_warning}</p>
              </div>
            </div>
          )}

          {/* Extraction Summary Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2 text-xs">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                Extracted Supplier & Identifiers
              </span>
              <div className="flex justify-between">
                <span className="text-slate-500">Vendor:</span>
                <span className="font-bold text-slate-900">
                  {uploadResult.extracted_data?.vendor_name || "Unmatched (Needs Review)"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Invoice Number:</span>
                <span className="font-mono font-bold text-slate-900">
                  {uploadResult.invoice_number}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Purchase Order:</span>
                <span className="font-mono text-slate-700">
                  {uploadResult.extracted_data?.purchase_order_number || "None Found"}
                </span>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2 text-xs">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                Extracted Financials
              </span>
              <div className="flex justify-between">
                <span className="text-slate-500">Subtotal:</span>
                <span className="font-mono text-slate-800">
                  {formatCurrency(uploadResult.extracted_data?.subtotal)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Tax Amount:</span>
                <span className="font-mono text-slate-800">
                  {formatCurrency(uploadResult.extracted_data?.tax_amount)}
                </span>
              </div>
              <div className="flex justify-between border-t border-slate-200 pt-1 font-bold">
                <span className="text-slate-900">Total Amount:</span>
                <span className="font-mono text-emerald-700 text-sm">
                  {formatCurrency(uploadResult.extracted_data?.total_amount)}
                </span>
              </div>
            </div>
          </div>

          {/* Confidence Score Gauge */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700 flex items-center space-x-1.5">
                <Sparkles className="h-4 w-4 text-sky-600" />
                <span>OCR Field Extraction Confidence</span>
              </span>
              <span className="font-mono font-bold text-slate-900">
                {uploadResult.confidence_score}%
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-2 rounded-full ${
                  parseFloat(uploadResult.confidence_score as string || "0") >= 70
                    ? "bg-emerald-500"
                    : "bg-amber-500"
                }`}
                style={{ width: `${Math.min(parseFloat(uploadResult.confidence_score as string || "0"), 100)}%` }}
              />
            </div>
            {uploadResult.extracted_data?.missing_fields?.length > 0 && (
              <p className="text-[11px] text-amber-700">
                Fields requiring review: {uploadResult.extracted_data.missing_fields.join(", ")}
              </p>
            )}
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-100">
            <button
              onClick={resetForm}
              className="w-full sm:w-auto px-4 py-2 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
            >
              Upload Another Document
            </button>
            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <Link
                href={`/invoices/${uploadResult.invoice_id}`}
                className="w-full sm:w-auto inline-flex items-center justify-center space-x-1.5 px-5 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-bold text-xs shadow-md shadow-sky-900/20 transition"
              >
                <Eye className="h-4 w-4" />
                <span>Review & Validate Extracted Invoice</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
