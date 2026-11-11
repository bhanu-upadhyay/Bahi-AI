import React from "react";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  actionText?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  actionText,
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white p-12 text-center",
        className
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500 mb-4">
        {icon || <Inbox className="h-6 w-6" />}
      </div>
      <h3 className="text-base font-semibold text-slate-800">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-4 inline-flex items-center rounded-lg bg-sky-700 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-sky-800 transition"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};

