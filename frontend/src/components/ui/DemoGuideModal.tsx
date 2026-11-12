"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  GraduationCap,
  X,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  FileText,
  UploadCloud,
  Sparkles,
  GitCompare,
  CreditCard,
  BookOpen,
  History,
  Lock,
  ExternalLink,
} from "lucide-react";

interface DemoGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DemoGuideModal: React.FC<DemoGuideModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const demoSteps = [
    {
      step: 1,
      title: "Sign In / Select Active Role",
      desc: "Use the top-right header role switcher or login page to select Finance Admin, Finance Officer, or HOD.",
      href: "/login",
      icon: Lock,
    },
    {
      step: 2,
      title: "Executive AP Overview",
      desc: "Review campus-wide budget utilization, pending approvals, and exception counts.",
      href: "/dashboard",
      icon: GraduationCap,
    },
    {
      step: 3,
      title: "Invoice Upload & OCR Extraction",
      desc: "Upload a PDF or image invoice with automatic magic-byte validation and duplicate hash checks.",
      href: "/invoices/upload",
      icon: UploadCloud,
    },
    {
      step: 4,
      title: "OCR Extraction & Field Verification",
      desc: "Inspect extracted parameters: Vendor name, GSTIN, Invoice #, Subtotal, CGST, SGST, IGST, and Grand Total.",
      href: "/invoices",
      icon: FileText,
    },
    {
      step: 5,
      title: "Invoice Review & Financial Math",
      desc: "Open any invoice detail page to verify live math reconciliation (Subtotal + Tax = Total).",
      href: "/invoices/1",
      icon: CheckCircle2,
    },
    {
      step: 6,
      title: "Multi-Agent AI Analysis Hub",
      desc: "Examine findings from all 5 agents: Understanding, Vendor Verification, 3-Way Match, Fraud Risk, and Recommendation.",
      href: "/invoices/1",
      icon: Sparkles,
    },
    {
      step: 7,
      title: "Three-Way Match Verification",
      desc: "Compare line items against Purchase Orders (PO) and Goods Receipt Notes (GRN) with strict variance tolerances.",
      href: "/matching",
      icon: GitCompare,
    },
    {
      step: 8,
      title: "Fraud & Exceptions Center",
      desc: "Inspect risk engine scoring, duplicate alerts, and unapproved vendor flags.",
      href: "/fraud",
      icon: ShieldCheck,
    },
    {
      step: 9,
      title: "Formal Human Officer Approval",
      desc: "Authorize or reject invoice. RBAC enforced: vendor accounts are blocked from approving financial transactions.",
      href: "/approvals",
      icon: CheckCircle2,
    },
    {
      step: 10,
      title: "ERP Posting Eligibility Check",
      desc: "Check live 7-gate validation (Approval, Non-duplicate, Reconciled Math, Active Vendor, Department, COA, Currency).",
      href: "/invoices/1",
      icon: ShieldCheck,
    },
    {
      step: 11,
      title: "Post to Mock University ERP",
      desc: "Click 'Post to Mock University ERP' to generate double-entry voucher and receive document ref UERP-2026-INV-XXXX.",
      href: "/invoices/1",
      icon: BookOpen,
    },
    {
      step: 12,
      title: "General Ledger & Balanced Vouchers",
      desc: "Inspect double-entry journal vouchers with balanced debits and credits and GST tax allocation.",
      href: "/ledger",
      icon: BookOpen,
    },
    {
      step: 13,
      title: "Trial Balance Zero-Variance Check",
      desc: "Check the Trial Balance tab to confirm perfect mathematical equilibrium (Net Variance = ₹0.00).",
      href: "/ledger",
      icon: CheckCircle2,
    },
    {
      step: 14,
      title: "Partial Payment & Settlement",
      desc: "Prepare partial disbursement, verify remaining balance tracking, and simulate bank settlement.",
      href: "/payments",
      icon: CreditCard,
    },
    {
      step: 15,
      title: "System Audit Trail",
      desc: "Review immutable audit logs recording all OCR runs, agent decisions, approvals, and ERP postings.",
      href: "/audit",
      icon: History,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-100 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-sky-600 text-white shadow-md">
              <GraduationCap className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-base font-bold tracking-tight">
                University Evaluator Demonstration Guide
              </h3>
              <p className="text-xs text-slate-300">
                15-Step End-to-End AP Automation & ERP Integration Workflow
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs">
          {/* Quick Demo Credentials Box */}
          <div className="p-4 rounded-xl border border-sky-100 bg-sky-50/70 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-sky-950 flex items-center space-x-1.5">
                <Lock className="h-4 w-4 text-sky-600" />
                <span>Demo User Accounts & Credentials</span>
              </span>
              <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-sky-200 text-sky-900">
                Default Password: BahiAI@2025!
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1 font-mono text-[11px]">
              <div className="p-2 rounded bg-white border border-sky-100">
                <span className="text-[10px] text-slate-400 block font-sans">Finance Admin</span>
                <span className="font-bold text-slate-800 truncate block">sarah.jenkins@university.edu</span>
              </div>
              <div className="p-2 rounded bg-white border border-sky-100">
                <span className="text-[10px] text-slate-400 block font-sans">Finance Officer</span>
                <span className="font-bold text-slate-800 truncate block">robert.vance@university.edu</span>
              </div>
              <div className="p-2 rounded bg-white border border-sky-100">
                <span className="text-[10px] text-slate-400 block font-sans">HOD Computer Science</span>
                <span className="font-bold text-slate-800 truncate block">alan.turing@university.edu</span>
              </div>
            </div>
          </div>

          {/* Workflow Steps List */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              End-to-End Evaluation Workflow Steps
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {demoSteps.map((s) => {
                const Icon = s.icon;
                return (
                  <div
                    key={s.step}
                    className="p-3.5 rounded-xl border border-slate-200/90 bg-white hover:border-sky-300 hover:shadow-sm transition flex items-start space-x-3 group"
                  >
                    <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-sky-100 text-sky-700 font-bold font-mono text-xs group-hover:bg-sky-600 group-hover:text-white transition">
                      {s.step}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <h5 className="font-bold text-slate-900 text-xs truncate">
                          {s.title}
                        </h5>
                        <Link
                          href={s.href}
                          onClick={onClose}
                          className="text-sky-600 hover:text-sky-800 inline-flex items-center space-x-0.5 text-[11px] font-semibold"
                        >
                          <span>Open</span>
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">
                        {s.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between text-xs">
          <span className="text-slate-500">
            Tip: You can quickly toggle between roles at any time using the header menu.
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-semibold hover:bg-slate-800 transition"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
};

