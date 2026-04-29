"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/cn";

/**
 * MinimalInput — bottom-border input with no fill, no rounded corners,
 * placeholder dimmed to slate-800. The "size" prop controls the typography
 * weight: `lg` for headline-style fields, `md` for the standard form fields.
 *
 * Pair with <SectionLabel /> above to reproduce the exact form pattern
 * from the design references.
 */

interface Props extends React.InputHTMLAttributes<HTMLInputElement> {
  inputSize?: "lg" | "md";
}

export const MinimalInput = forwardRef<HTMLInputElement, Props>(
  function MinimalInput({ inputSize = "md", className, ...props }, ref) {
    const typo =
      inputSize === "lg"
        ? "text-2xl font-light"
        : "text-xl font-light";

    return (
      <input
        ref={ref}
        {...props}
        className={cn(
          "w-full border-b border-slate-800 bg-transparent py-4 text-white transition-colors",
          "placeholder:text-slate-800 focus:border-sky-500 focus:outline-none",
          "disabled:opacity-40",
          typo,
          className
        )}
      />
    );
  }
);
