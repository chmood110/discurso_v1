"use client";
import { Spinner } from "./spinner";

interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

const VARIANTS = {
  primary:   "bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50",
  secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50",
  ghost:     "text-slate-600 hover:bg-slate-100 disabled:opacity-50",
  danger:    "bg-red-600 text-white hover:bg-red-700 disabled:opacity-50",
};
const SIZES = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm", lg: "px-5 py-2.5 text-base" };

export function Button({ variant = "primary", size = "md", loading, children, disabled, className = "", ...props }: Props) {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center gap-2 rounded-lg font-medium transition-colors ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
