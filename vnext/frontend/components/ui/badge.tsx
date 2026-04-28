type Variant = "success" | "warning" | "error" | "info" | "neutral";
const CLASSES: Record<Variant, string> = {
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  error:   "bg-red-50 text-red-700 border-red-200",
  info:    "bg-blue-50 text-blue-700 border-blue-200",
  neutral: "bg-slate-100 text-slate-600 border-slate-200",
};
export function Badge({ children, variant = "neutral" }: { children: React.ReactNode; variant?: Variant }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${CLASSES[variant]}`}>
      {children}
    </span>
  );
}
