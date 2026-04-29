"use client";

import { AlertTriangle } from "lucide-react";

interface Props {
  disclaimer: string;
  quality_label?: string;
  className?: string;
}

/**
 * MethodologyDisclaimer — surfaced when the analysis can't be cited as
 * official municipal data. Re-skinned for the navy palette but keeps the
 * exact same prop API.
 */
export function MethodologyDisclaimer({
  disclaimer,
  quality_label,
  className = "",
}: Props) {
  if (!disclaimer) return null;

  return (
    <div
      className={`flex items-start gap-4 border-l-2 border-amber-400/40 bg-amber-500/5 px-6 py-5 ${className}`}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400/70" />
      <div className="space-y-1">
        {quality_label && (
          <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-amber-300/80">
            {quality_label}
          </p>
        )}
        <p className="text-sm font-light leading-relaxed text-amber-100/70">
          {disclaimer}
        </p>
      </div>
    </div>
  );
}
