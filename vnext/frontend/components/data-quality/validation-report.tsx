"use client";

import { AlertCircle, AlertTriangle, Info } from "lucide-react";
import type { ValidationReport } from "@/types";
import { cn } from "@/lib/cn";

interface Props {
  report: ValidationReport;
  className?: string;
}

const STYLES: Record<
  string,
  { wrap: string; icon: React.ComponentType<{ className?: string }> }
> = {
  blocking: {
    wrap: "border-red-400/30 bg-red-500/5 text-red-200",
    icon: AlertCircle,
  },
  warning: {
    wrap: "border-amber-400/30 bg-amber-500/5 text-amber-200",
    icon: AlertTriangle,
  },
  info: {
    wrap: "border-sky-400/20 bg-sky-500/5 text-sky-200",
    icon: Info,
  },
};

export function ValidationReportPanel({ report, className }: Props) {
  if (report.passed && report.warning_count === 0) return null;

  const headerColor = report.passed ? "text-amber-300" : "text-red-300";

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between border-b border-slate-900 pb-3">
        <h3 className="text-[10px] font-black uppercase tracking-eyebrow text-slate-500">
          {report.passed
            ? "Advertencias de calidad"
            : "Salida bloqueada por validación"}
        </h3>
        <span
          className={cn(
            "text-[10px] font-bold uppercase tracking-eyebrow_xs",
            headerColor
          )}
        >
          Score · {(report.score * 100).toFixed(0)}%
        </span>
      </div>

      <div className="space-y-2">
        {report.issues.map((issue, i) => {
          const style = STYLES[issue.severity] || STYLES.info;
          const Icon = style.icon;
          return (
            <div
              key={`${issue.code}-${i}`}
              className={cn(
                "flex items-start gap-3 border-l-2 px-4 py-3 text-sm font-light leading-relaxed",
                style.wrap
              )}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0 opacity-70" />
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-eyebrow_xs opacity-80">
                  <span>[{issue.code}]</span>
                  {issue.field && <span>· {issue.field}</span>}
                </div>
                <p>{issue.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      {!report.passed && (
        <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-red-300/80">
          {report.blocking_count} error
          {report.blocking_count !== 1 ? "es" : ""} crítico
          {report.blocking_count !== 1 ? "s" : ""} deben resolverse antes de
          continuar.
        </p>
      )}
    </div>
  );
}
