import { cn } from "@/lib/cn";

type Variant = "success" | "warning" | "error" | "info" | "neutral";

const CLASSES: Record<Variant, string> = {
  success: "border-sky-400/40 bg-sky-500/10 text-sky-300",
  warning: "border-amber-400/30 bg-amber-500/10 text-amber-300",
  error: "border-red-400/30 bg-red-500/10 text-red-300",
  info: "border-blue-400/30 bg-blue-500/10 text-blue-300",
  neutral: "border-slate-700 bg-slate-900 text-slate-400",
};

export function Badge({
  children,
  variant = "neutral",
  className,
}: {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-eyebrow_xs",
        CLASSES[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
