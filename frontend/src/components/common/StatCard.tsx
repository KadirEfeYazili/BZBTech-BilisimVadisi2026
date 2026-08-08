import type { LucideIcon } from "lucide-react";

import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: number;
  icon?: LucideIcon;
  /** Değerin altında gösterilen kısa açıklama. */
  hint?: string;
  /** Vurgu rengi; varsayılan nötr. */
  tone?: "neutral" | "active" | "upcoming" | "expired" | "unknown";
}

const TONE_CLASSES: Record<NonNullable<StatCardProps["tone"]>, string> = {
  neutral: "text-text-900",
  active: "text-brand-500",
  upcoming: "text-teal-500",
  expired: "text-text-500",
  unknown: "text-warn-600",
};

/** Gösterge panelindeki tek sayısal ölçüt kartı. */
export function StatCard({ label, value, icon: Icon, hint, tone = "neutral" }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-text-500">{label}</span>
        {Icon && <Icon className="h-4 w-4 text-text-500" aria-hidden="true" />}
      </div>

      <p className={cn("tabular mt-2 text-2xl font-semibold", TONE_CLASSES[tone])}>
        {formatNumber(value)}
      </p>

      {hint && <p className="mt-1 text-xs text-text-500">{hint}</p>}
    </div>
  );
}
