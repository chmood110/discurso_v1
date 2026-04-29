"use client";

import { forwardRef } from "react";
import { cn } from "@/lib/cn";

interface Props extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

/**
 * MinimalTextarea — twin of MinimalInput for multi-line content
 * (source speech, long objectives, etc.). The 30%-tinted slate-950 background
 * helps the textarea read as a *zone* without breaking the borderless feel.
 */
export const MinimalTextarea = forwardRef<HTMLTextAreaElement, Props>(
  function MinimalTextarea({ className, ...props }, ref) {
    return (
      <textarea
        ref={ref}
        {...props}
        className={cn(
          "no-scrollbar w-full resize-none border-b border-slate-800 bg-slate-950/30 py-6 text-xl font-light text-white transition-colors",
          "placeholder:text-slate-800 focus:border-sky-500 focus:outline-none",
          "disabled:opacity-40",
          className
        )}
      />
    );
  }
);
