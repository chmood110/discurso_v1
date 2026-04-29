"use client";

/**
 * Legacy <Input /> — kept so any older code still compiles.
 * For new pages prefer <MinimalInput />.
 */

import { cn } from "@/lib/cn";

interface Props extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className, ...props }: Props) {
  return (
    <div className={className}>
      {label && (
        <label className="mb-2 block text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500">
          {label}
        </label>
      )}
      <input
        {...props}
        className={cn(
          "w-full border-b bg-transparent py-3 text-base text-white transition-colors",
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
