"use client";

interface Props {
  disclaimer: string;
  quality_label?: string;
  className?: string;
}

export function MethodologyDisclaimer({ disclaimer, quality_label, className = "" }: Props) {
  if (!disclaimer) return null;
  return (
    <div className={`rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 ${className}`}>
      <div className="flex items-start gap-3">
        <span className="text-amber-600 mt-0.5 flex-shrink-0">⚠</span>
        <div>
          {quality_label && (
            <p className="text-xs font-semibold text-amber-700 mb-1">{quality_label}</p>
          )}
          <p className="text-xs text-amber-700 leading-relaxed">{disclaimer}</p>
        </div>
      </div>
    </div>
  );
}
