"use client";

import React, { useEffect, useState } from "react";
import { Building2, Search, RefreshCw, Mail, Phone, MapPin, Shield } from "lucide-react";
import { api } from "@/services/api";
import { Vendor } from "@/types";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";

export default function VendorsPage() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const loadData = () => {
    setLoading(true);
    api
      .getVendors(search || undefined)
      .then((data) => {
        setVendors(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 flex items-center space-x-2">
            <Building2 className="h-5 w-5 text-sky-600" />
            <span>Approved University Vendor Registry</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Verified suppliers, verified banking profiles (masked for PCI compliance), and tax identifiers
          </p>
        </div>
        <button
          onClick={loadData}
          className="p-2 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by vendor name, code, or tax identifier..."
          className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 bg-white"
        />
      </form>

      {/* Vendor Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-3">
            <TableSkeleton rows={4} />
          </div>
        ) : vendors.length === 0 ? (
          <div className="col-span-3">
            <EmptyState
              title="No vendors found"
              description="No suppliers matched your search query."
              actionText="Clear Search"
              onAction={() => {
                setSearch("");
                loadData();
              }}
            />
          </div>
        ) : (
          vendors.map((v) => (
            <div
              key={v.id}
              className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm space-y-3 hover:border-slate-300 transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <span className="font-mono text-xs font-bold text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-100">
                    {v.vendor_code}
                  </span>
                  <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    Active Supplier
                  </span>
                </div>
                <h3 className="text-sm font-bold text-slate-900 mt-2">{v.legal_name}</h3>
                <p className="text-xs text-slate-500 mt-0.5">Contact: {v.contact_person}</p>
              </div>

              <div className="text-xs text-slate-600 space-y-1.5 pt-2 border-t border-slate-100">
                <div className="flex items-center space-x-2 text-slate-500">
                  <Mail className="h-3.5 w-3.5 text-slate-400" />
                  <span className="truncate">{v.email}</span>
                </div>
                <div className="flex items-center space-x-2 text-slate-500">
                  <Phone className="h-3.5 w-3.5 text-slate-400" />
                  <span>{v.phone}</span>
                </div>
                <div className="flex items-center space-x-2 text-slate-500">
                  <MapPin className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                  <span className="truncate">{v.address}</span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 bg-slate-50 -mx-5 -mb-5 p-3 rounded-b-xl text-[11px] space-y-1">
                <div className="flex justify-between font-mono text-slate-600">
                  <span>Tax ID:</span>
                  <span className="font-semibold text-slate-800">{v.tax_identifier}</span>
                </div>
                <div className="flex justify-between font-mono text-slate-500 text-[10px]">
                  <span>Banking:</span>
                  <span>{v.bank_name} (•••• {v.bank_account_last_four})</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

