"use client";

import { cn } from "@/lib/cn";
import { Spinner } from "./spinner";

/**
 * Button — preserved API (variant / size / loading) so existing call sites
 * keep working. Visuals were redrawn for the navy theme:
 *   primary   → white pill that flips to sky on hover (the hero CTA)
 *   secondary → outline on slate, fills white on hover
 *   ghost     → transparent, only color shift on hover
 *   danger    → red surface (rare, but kept for completeness)
 */

interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

const VARIANTS: Record<NonNullable<Props["variant"]>, string> = {
  primary:
    "bg-white text-black hover:bg-sky-400 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-20 disabled:hover:bg-white disabled:hover:scale-100",
  secondary:
    "bg-white/5 text-white border border-white/10 hover:bg-white/10 hover:border-white/20 disabled:opacity-30",
  ghost:
    "bg-transparent text-slate-400 hover:text-white hover:bg-white/5 disabled:opacity-30",
  danger:
    "bg-red-500/90 text-white hover:bg-red-500 disabled:opacity-30",
};

const SIZES: Record<NonNullable<Props["size"]>, string> = {
  sm: "px-4 py-2 text-xs",
  md: "px-6 py-3 text-xs",
  lg: "px-10 py-4 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  loading,
  children,
  disabled,
  className,
  ...props
}: Props) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full font-bold uppercase tracking-eyebrow_xs transition-all",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
