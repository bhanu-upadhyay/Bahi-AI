import React from "react";
import { cn } from "@/lib/utils";

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  variant?: "default" | "alert" | "success" | "accent";
  className?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  variant = "default",
  className,
}) => {
  return (
    <div
      className={cn(
        "bg-white rounded-xl border border-slate-200/90 p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] transition-all hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)] hover:border-slate-300",
        variant === "alert" && "border-amber-300/80 bg-gradient-to-br from-white to-amber-50/30",
        variant === "success" && "border-emerald-300/80 bg-gradient-to-br from-white to-emerald-50/30",
        variant === "accent" && "border-sky-300/80 bg-gradient-to-br from-white to-sky-50/30",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </p>
        {icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
            {icon}
          </div>
        )}
      </div>
      <div className="mt-3 flex items-baseline justify-between">
        <h3 className="text-2xl font-bold tracking-tight text-slate-900 font-sans">
          {value}
        </h3>
        {trend && (
          <span
            className={cn(
              "text-xs font-semibold",
              trend.isPositive ? "text-emerald-700" : "text-slate-600"
            )}
          >
            {trend.value}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="mt-1 text-xs text-slate-500 font-medium">{subtitle}</p>
      )}
    </div>
  );
};

