"use client";

import React, { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import {
  Bell,
  Search,
  User as UserIcon,
  ChevronDown,
  ShieldCheck,
  Building,
  GraduationCap,
} from "lucide-react";
import { api } from "@/services/api";
import { User } from "@/types";
import { DemoGuideModal } from "@/components/ui/DemoGuideModal";

export const Header: React.FC = () => {
  const pathname = usePathname();
  const [activeAlerts, setActiveAlerts] = useState<number>(0);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showDemoGuide, setShowDemoGuide] = useState(false);

  useEffect(() => {
    // Fetch active fraud alerts count
    api
      .getFraudAlerts("OPEN")
      .then((alerts) => setActiveAlerts(alerts.length))
      .catch(() => {});

    // Fetch users for demonstration role switcher
    api
      .getUsers()
      .then((u) => {
        setUsers(u);
        if (u.length > 0) {
          // Default to Finance Admin
          const admin = u.find((x) => x.role === "FINANCE_ADMIN") || u[0];
          setSelectedUser(admin);
        }
      })
      .catch(() => {});
  }, []);

  const getPageTitle = () => {
    if (pathname === "/" || pathname === "/dashboard") return "Executive AP Overview";
    if (pathname.startsWith("/invoices/")) return "Invoice Processing Details";
    if (pathname.startsWith("/invoices")) return "Vendor Invoices";
    if (pathname.startsWith("/matching")) return "Three-Way Match Verification";
    if (pathname.startsWith("/fraud")) return "Fraud & Exceptions Center";
    if (pathname.startsWith("/budgets")) return "Department Budget Allocation";
    if (pathname.startsWith("/approvals")) return "Multi-Level Approvals Queue";
    if (pathname.startsWith("/payments")) return "Payment Scheduling & Disbursements";
    if (pathname.startsWith("/vendor")) return "Approved Vendor Registry";
    if (pathname.startsWith("/purchase-orders")) return "Purchase Orders";
    if (pathname.startsWith("/goods-receipts")) return "Goods Receipt Notes";
    if (pathname.startsWith("/audit")) return "System Audit Trail";
    if (pathname.startsWith("/ledger")) return "ERP General Ledger";
    if (pathname.startsWith("/reports")) return "Finance Reports & Analytics";
    if (pathname.startsWith("/settings")) return "System Configuration";
    return "Accounts Payable";
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-30 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      {/* Breadcrumbs & Title */}
      <div className="flex items-center space-x-3">
        <div>
          <div className="flex items-center space-x-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            <span>University Finance</span>
            <span>/</span>
            <span className="text-sky-700">FY 2024–2025</span>
          </div>
          <h1 className="text-lg font-bold text-slate-900 tracking-tight leading-tight">
            {getPageTitle()}
          </h1>
        </div>
      </div>

      {/* Right Actions */}
      <div className="flex items-center space-x-4">
        {/* Environment Badge */}
        <div className="hidden md:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-600 text-xs font-medium">
          <Building className="h-3.5 w-3.5 text-slate-500" />
          <span>Central Campus Accounts</span>
        </div>

        {/* Demo Guide Button */}
        <button
          onClick={() => setShowDemoGuide(true)}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-sky-50 border border-sky-200 text-sky-800 text-xs font-semibold hover:bg-sky-100 transition shadow-sm"
          title="Open University Evaluator Demonstration Guide"
        >
          <GraduationCap className="h-4 w-4 text-sky-600" />
          <span>Demo Guide</span>
        </button>

        {/* Notifications / Exception Bell */}
        <a
          href="/fraud"
          className="relative p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
          title="Exceptions & Fraud Alerts"
        >
          <Bell className="h-5 w-5" />
          {activeAlerts > 0 && (
            <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-600 text-[10px] font-bold text-white ring-2 ring-white">
              {activeAlerts}
            </span>
          )}
        </a>

        {/* Role Switcher & User Profile Menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserDropdown(!showUserDropdown)}
            className="flex items-center space-x-3 pl-2 pr-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-800 text-white font-semibold text-xs">
              {selectedUser ? selectedUser.full_name.charAt(0) : "U"}
            </div>
            <div className="text-left hidden sm:block">
              <div className="text-xs font-semibold text-slate-900 leading-tight">
                {selectedUser?.full_name || "Finance Admin"}
              </div>
              <div className="text-[10px] font-medium text-slate-500 flex items-center space-x-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>{selectedUser?.role?.replace("_", " ") || "FINANCE ADMIN"}</span>
              </div>
            </div>
            <ChevronDown className="h-4 w-4 text-slate-400" />
          </button>

          {/* User / Role Dropdown */}
          {showUserDropdown && (
            <div className="absolute right-0 mt-2 w-64 rounded-xl bg-white p-2 shadow-xl border border-slate-200 z-50">
              <div className="px-3 py-2 border-b border-slate-100 mb-1">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Switch Active Role (Demo)
                </p>
              </div>
              <div className="space-y-1">
                {users.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => {
                      setSelectedUser(u);
                      setShowUserDropdown(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 text-left rounded-lg text-xs transition ${
                      selectedUser?.id === u.id
                        ? "bg-sky-50 text-sky-800 font-semibold"
                        : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <div>
                      <div className="font-medium text-slate-900">{u.full_name}</div>
                      <div className="text-[10px] text-slate-500">{u.role.replace(/_/g, " ")}</div>
                    </div>
                    {selectedUser?.id === u.id && (
                      <ShieldCheck className="h-4 w-4 text-sky-600" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <DemoGuideModal isOpen={showDemoGuide} onClose={() => setShowDemoGuide(false)} />
    </header>
  );
};

