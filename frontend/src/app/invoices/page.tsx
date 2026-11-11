"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Search,
  Filter,
  FileText,
  ArrowUpRight,
  UploadCloud,
  RefreshCw,
  Building,
} from "lucide-react";
import { api } from "@/services/api";
import { Invoice, Department } from "@/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [selectedDept, setSelectedDept] = useState<string>("");

  const loadData = () => {
    setLoading(true);
    Promise.all([
      api.getInvoices({
        search: search || undefined,
        status: selectedStatus || undefined,
        department_id: selectedDept ? parseInt(selectedDept) : undefined,
      }),
      api.getDepartments(),
    ])
      .then(([invRes, deptRes]) => {
        setInvoices(invRes);
        setDepartments(deptRes);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [selectedStatus, selectedDept]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  return (
    <div className="space-y-6">
      {/* Top Header with Upload Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900">
            University Vendor Invoices
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time accounts payable ledger, OCR intake, and invoice match status
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={loadData}
            className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
            title="Refresh Invoices"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <Link
            href="/invoices/upload"
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold shadow-md shadow-sky-900/20 transition"
          >
            <UploadCloud className="h-4 w-4" />
            <span>Upload Invoice</span>
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-96">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search invoice number or vendor..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition"
          />
        </form>

        <div className="flex items-center space-x-3 w-full md:w-auto">
          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
          >
            <option value="">All Match & Intake Statuses</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
            <option value="EXTRACTED">Extracted</option>
            <option value="VALIDATED">Validated</option>
            <option value="MATCHED">Matched</option>
            <option value="EXCEPTION">Exceptions</option>
            <option value="DUPLICATE">Duplicate</option>
          </select>

          {/* Department Filter */}
          <select
            value={selectedDept}
            onChange={(e) => setSelectedDept(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.code} - {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Invoices Data Table */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm overflow-hidden">
        {loading ? (
          <TableSkeleton rows={7} />
        ) : invoices.length === 0 ? (
          <EmptyState
            title="No invoices found"
            description="No invoices match the selected filter criteria."
            actionText="Upload First Invoice"
            onAction={() => window.location.href = "/invoices/upload"}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/90 text-slate-500 font-semibold border-b border-slate-200">
                  <th className="py-3.5 px-4">Invoice #</th>
                  <th className="py-3.5 px-4">Vendor</th>
                  <th className="py-3.5 px-4">Department</th>
                  <th className="py-3.5 px-4">Issue Date</th>
                  <th className="py-3.5 px-4">Due Date</th>
                  <th className="py-3.5 px-4">Total Amount</th>
                  <th className="py-3.5 px-4">Intake & Match</th>
                  <th className="py-3.5 px-4">Approval</th>
                  <th className="py-3.5 px-4">Payment</th>
                  <th className="py-3.5 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-normal">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                      <Link href={`/invoices/${inv.id}`} className="hover:text-sky-600">
                        {inv.invoice_number}
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-slate-800 font-medium max-w-xs truncate">
                      {inv.vendor?.legal_name || (
                        <span className="text-amber-600 italic">Unassigned Vendor</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {inv.department ? (
                        <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] text-slate-700 font-medium">
                          {inv.department.code}
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[11px]">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(inv.invoice_date)}</td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(inv.due_date)}</td>
                    <td className="py-3 px-4 font-semibold text-slate-900 font-mono">
                      {formatCurrency(inv.total_amount)}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={inv.processing_status} type="processing" />
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={inv.approval_status} type="approval" />
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={inv.payment_status} type="payment" />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/invoices/${inv.id}`}
                        className="inline-flex items-center text-sky-600 hover:text-sky-800 font-semibold text-xs px-2.5 py-1 rounded-md hover:bg-sky-50 transition"
                      >
                        <span>{inv.processing_status === "NEEDS_REVIEW" ? "Review" : "Details"}</span>
                        <ArrowUpRight className="h-3 w-3 ml-0.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
