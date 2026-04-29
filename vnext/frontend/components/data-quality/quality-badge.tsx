"use client";

import { cn } from "@/lib/cn";

/**
 * Data quality indicators — adapted from v1 to the navy palette.
 * Public API (props, level enum, ConfidenceBar) preserved 1:1 so existing
 * call sites compile without changes.
 */

export type DataQualityLevel =
  | "official_municipal"
  | "official_state"
  | "calibrated_estimate"
  | "unavailable";

interface Props {
  level: DataQualityLevel;
  compact?: boolean;
  className?: string;
}

const CONFIG: Record<
  DataQualityLevel,
  { label: string; icon: string; classes: string }
> = {
  official_municipal: {
    label: "Dato oficial municipal",
    icon: "✓",
    classes: "border-sky-500/40 bg-sky-500/10 text-sky-300",
  },
  official_state: {
    label: "Dato estatal",
    icon: "~",
    classes: "border-blue-400/30 bg-blue-500/10 text-blue-300",
  },
  calibrated_estimate: {
    label: "Estimación regional",
    icon: "≈",
    classes: "border-amber-400/30 bg-amber-500/10 text-amber-300",
  },
  unavailable: {
    label: "Sin dato",
    icon: "—",
    classes: "border-slate-700 bg-slate-900 text-slate-500",
  },
};

export function QualityBadge({ level, compact = false, className }: Props) {
  const cfg = CONFIG[level] ?? CONFIG.unavailable;

  if (compact) {
    return (
      <span
        title={cfg.label}
        className={cn(
          "inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-semibold",
          cfg.classes,
          className
        )}
      >
        {cfg.icon}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-3 py-1 text-[10px] font-bold uppercase tracking-eyebrow_xs",
        cfg.classes,
        className
      )}
    >
      <span>{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}

export function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 80 ? "bg-sky-400" : pct >= 50 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="flex items-center gap-3">
      <div className="h-1 w-32 overflow-hidden rounded-full bg-slate-800">
        <div
          className={cn("h-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500">
        {pct}% confianza
      </span>
    </div>
  );
}
