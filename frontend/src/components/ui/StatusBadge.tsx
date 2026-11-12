import React from "react";
import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  type?: "processing" | "approval" | "payment" | "severity" | "general";
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  type = "general",
  className,
}) => {
  const s = status ? status.toUpperCase() : "UNKNOWN";

  let styles = "bg-slate-100 text-slate-700 border-slate-200";

  if (type === "processing" || type === "general") {
    switch (s) {
      case "MATCHED":
        styles = "bg-emerald-50 text-emerald-700 border-emerald-200";
        break;
      case "VALIDATED":
        styles = "bg-teal-50 text-teal-800 border-teal-200 font-semibold";
        break;
      case "EXTRACTED":
        styles = "bg-sky-50 text-sky-700 border-sky-200";
        break;
      case "PROCESSING":
        styles = "bg-blue-50 text-blue-700 border-blue-200";
        break;
      case "UPLOADED":
      case "RECEIVED":
        styles = "bg-slate-50 text-slate-700 border-slate-200";
        break;
      case "NEEDS_REVIEW":
        styles = "bg-amber-50 text-amber-800 border-amber-200 font-semibold";
        break;
      case "EXCEPTION":
        styles = "bg-amber-50 text-amber-800 border-amber-200";
        break;
      case "DUPLICATE":
        styles = "bg-rose-50 text-rose-800 border-rose-200 font-semibold";
        break;
      case "FAILED":
        styles = "bg-rose-100 text-rose-900 border-rose-300 font-semibold";
        break;
      case "DELIVERED":
      case "INSPECTED":
        styles = "bg-emerald-50 text-emerald-700 border-emerald-200";
        break;
      case "PARTIAL":
      case "PARTIALLY_DELIVERED":
        styles = "bg-indigo-50 text-indigo-700 border-indigo-200";
        break;
    }
  }

  if (type === "approval") {
    switch (s) {
      case "APPROVED":
        styles = "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold";
        break;
      case "IN_REVIEW":
        styles = "bg-blue-50 text-blue-700 border-blue-200";
        break;
      case "PENDING":
        styles = "bg-amber-50 text-amber-800 border-amber-200";
        break;
      case "REJECTED":
        styles = "bg-rose-50 text-rose-800 border-rose-200 font-semibold";
        break;
    }
  }

  if (type === "payment") {
    switch (s) {
      case "PAID":
      case "COMPLETED":
      case "SETTLED":
        styles = "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold";
        break;
      case "PARTIAL":
        styles = "bg-sky-50 text-sky-800 border-sky-200 font-semibold";
        break;
      case "SCHEDULED":
        styles = "bg-purple-50 text-purple-700 border-purple-200";
        break;
      case "UNPAID":
        styles = "bg-slate-100 text-slate-700 border-slate-300";
        break;
      case "CANCELLED":
      case "FAILED":
        styles = "bg-rose-50 text-rose-800 border-rose-200";
        break;
    }
  }

  if (type === "severity") {
    switch (s) {
      case "CRITICAL":
        styles = "bg-rose-600 text-white border-rose-700 font-semibold";
        break;
      case "HIGH":
        styles = "bg-rose-100 text-rose-800 border-rose-300 font-medium";
        break;
      case "MEDIUM":
        styles = "bg-amber-100 text-amber-800 border-amber-300";
        break;
      case "LOW":
        styles = "bg-blue-100 text-blue-800 border-blue-300";
        break;
    }
  }

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border tracking-wide",
        styles,
        className
      )}
    >
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current opacity-75"></span>
      {status.replace(/_/g, " ")}
    </span>
  );
};
