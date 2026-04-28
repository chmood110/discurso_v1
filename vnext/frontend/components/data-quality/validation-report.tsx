"use client";
import type { ValidationReport } from "@/types";

interface Props {
  report: ValidationReport;
  className?: string;
}

const SEVERITY_STYLES = {
  blocking: "bg-red-50 border-red-200 text-red-700",
  warning:  "bg-amber-50 border-amber-200 text-amber-700",
  info:     "bg-blue-50 border-blue-200 text-blue-600",
};

export function ValidationReportPanel({ report, className = "" }: Props) {
  if (report.passed && report.warning_count === 0) return null;

  return (
    <div className={`rounded-xl border ${report.passed ? "border-amber-200 bg-amber-50" : "border-red-200 bg-red-50"} p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800">
            {report.passed ? "⚠ Advertencias de calidad" : "✗ Salida bloqueada por validación"}
          </span>
        </div>
        <span className={`text-xs font-semibold ${report.passed ? "text-amber-600" : "text-red-600"}`}>
          Score: {(report.score * 100).toFixed(0)}%
        </span>
      </div>

      <div className="space-y-2">
        {report.issues.map((issue, i) => (
          <div key={i} className={`rounded border p-2.5 text-xs ${SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.info}`}>
            <div className="flex items-start gap-2">
              <span className="font-mono font-bold shrink-0">
                {issue.severity === "blocking" ? "✗" : issue.severity === "warning" ? "⚠" : "ℹ"}
              </span>
              <div>
                <span className="font-semibold">[{issue.code}]</span>{" "}
                {issue.description}
                {issue.field && <span className="ml-1 opacity-70">• campo: {issue.field}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>

      {!report.passed && (
        <p className="mt-3 text-xs text-red-600 font-medium">
          {report.blocking_count} error{report.blocking_count !== 1 ? "es" : ""} crítico{report.blocking_count !== 1 ? "s" : ""} deben resolverse antes de continuar.
        </p>
      )}
    </div>
  );
}
