"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  Building2,
  ShoppingCart,
  PackageCheck,
  GitCompare,
  ShieldAlert,
  PieChart,
  CheckSquare,
  CreditCard,
  BookOpen,
  BarChart3,
  History,
  Settings,
  GraduationCap,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  isPhase2?: boolean;
}

const navSections: { title?: string; items: NavItem[] }[] = [
  {
    items: [
      { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
      { name: "Invoices", href: "/invoices", icon: FileText },
      { name: "Vendors", href: "/vendor", icon: Building2 },
    ],
  },
  {
    title: "Procurement & Receiving",
    items: [
      { name: "Purchase Orders", href: "/purchase-orders", icon: ShoppingCart },
      { name: "Goods Receipts", href: "/goods-receipts", icon: PackageCheck },
      { name: "Three-Way Matching", href: "/matching", icon: GitCompare },
      { name: "Fraud & Exceptions", href: "/fraud", icon: ShieldAlert },
    ],
  },
  {
    title: "Financial Control",
    items: [
      { name: "Department Budgets", href: "/budgets", icon: PieChart },
      { name: "Approvals", href: "/approvals", icon: CheckSquare },
      { name: "Payments", href: "/payments", icon: CreditCard },
    ],
  },
  {
    title: "Governance & Intelligence",
    items: [
      { name: "ERP Ledger", href: "/ledger", icon: BookOpen, isPhase2: true },
      { name: "Reports", href: "/reports", icon: BarChart3, isPhase2: true },
      { name: "Audit Logs", href: "/audit", icon: History },
      { name: "Settings", href: "/settings", icon: Settings, isPhase2: true },
    ],
  },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const isCurrent = (href: string) => {
    if (href === "/dashboard" && (pathname === "/" || pathname === "/dashboard")) {
      return true;
    }
    return pathname.startsWith(href) && href !== "/dashboard";
  };

  return (
    <aside className="w-64 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col justify-between min-h-screen">
      {/* Brand Header */}
      <div>
        <div className="h-16 flex items-center px-6 border-b border-slate-800/80 bg-slate-950/40">
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-600 text-white font-bold shadow-md shadow-sky-900/40">
              <GraduationCap className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="text-base font-bold tracking-tight text-white">
                  Bahi<span className="text-sky-400 font-extrabold">-AI</span>
                </span>
                <span className="rounded bg-sky-950/80 px-1.5 py-0.5 text-[10px] font-semibold text-sky-300 border border-sky-800/60">
                  AP
                </span>
              </div>
              <p className="text-[11px] font-medium text-slate-400">
                University Accounts Payable
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Sections */}
        <nav className="px-3 py-4 space-y-6 overflow-y-auto max-h-[calc(100vh-140px)]">
          {navSections.map((section, idx) => (
            <div key={idx} className="space-y-1">
              {section.title && (
                <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  {section.title}
                </div>
              )}
              {section.items.map((item) => {
                const active = isCurrent(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      "flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group",
                      active
                        ? "bg-sky-600 text-white shadow-sm shadow-sky-900/50"
                        : "text-slate-300 hover:text-white hover:bg-slate-800/80"
                    )}
                  >
                    <div className="flex items-center space-x-2.5">
                      <Icon
                        className={cn(
                          "h-4 w-4 flex-shrink-0 transition-colors",
                          active ? "text-white" : "text-slate-400 group-hover:text-slate-200"
                        )}
                      />
                      <span>{item.name}</span>
                    </div>
                    {item.isPhase2 && (
                      <span className="text-[9px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        Phase 2
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* System Status Footer */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/50">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[11px] font-medium text-slate-300">FastAPI Online</span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">v0.1.0</span>
        </div>
      </div>
    </aside>
  );
};

