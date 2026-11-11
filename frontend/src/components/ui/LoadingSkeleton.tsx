import React from "react";
import { cn } from "@/lib/utils";

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-slate-200/80", className)}
    />
  );
};

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => {
  return (
    <div className="space-y-3 p-4">
      <Skeleton className="h-8 w-full rounded-lg" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  );
};

