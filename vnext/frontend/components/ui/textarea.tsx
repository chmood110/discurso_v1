"use client";

import { cn } from "@/lib/cn";

interface Props extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

/**
 * Legacy <Textarea />. Prefer <MinimalTextarea /> in new pages.
 */
export function Textarea({ label, error, className, ...props }: Props) {
  return (
    <div className={className}>
      {label && (
        <label className="mb-2 block text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500">
          {label}
        </label>
      )}
      <textarea
        {...props}
        className={cn(
          "no-scrollbar w-full resize-none border-b bg-slate-950/30 px-3 py-3 text-sm text-white transition-colors",
          "placeholder:text-slate-800 focus:outline-none",
          error
            ? "border-red-400/60 focus:border-red-400"
            : "border-slate-800 focus:border-sky-500"
        )}
      />
      {error && (
        <p className="mt-2 text-[10px] font-bold uppercase tracking-eyebrow_xs text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}
