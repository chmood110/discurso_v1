"use client";
import type { DataQualityLevel } from "@/types";

interface Props {
  level: DataQualityLevel;
  compact?: boolean;
  className?: string;
}

const CONFIG: Record<DataQualityLevel, { label: string; icon: string; classes: string }> = {
  official_municipal: {
    label: "Dato oficial municipal",
    icon: "✓",
    classes: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  official_state: {
    label: "Dato estatal",
    icon: "~",
    classes: "bg-blue-50 text-blue-700 border-blue-200",
  },
  calibrated_estimate: {
    label: "Estimación regional",
    icon: "≈",
    classes: "bg-amber-50 text-amber-700 border-amber-200",
  },
  unavailable: {
    label: "Sin dato",
    icon: "—",
    classes: "bg-slate-100 text-slate-500 border-slate-200",
  },
};

export function QualityBadge({ level, compact = false, className = "" }: Props) {
  const cfg = CONFIG[level] ?? CONFIG.unavailable;
  if (compact) {
    return (
      <span
        className={`inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-semibold ${cfg.classes} ${className}`}
        title={cfg.label}
      >
        {cfg.icon}
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${cfg.classes} ${className}`}>
      <span>{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}

export function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500">{pct}% confianza</span>
    </div>
  );
}
