import { cn } from "@/lib/cn";

/**
 * Card — kept for backwards compatibility with internal call sites that
 * still want a self-contained surface. New pages prefer the editorial
 * approach (no card chrome, just spacing + dividers) — but Card is here
 * when a contained block is genuinely needed.
 */

export function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "border border-slate-900 bg-slate-950/40 p-6",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-5 space-y-1">
      <h2 className="text-[10px] font-black uppercase tracking-eyebrow text-slate-400">
        {title}
      </h2>
      {subtitle && (
        <p className="text-sm font-light text-slate-500">{subtitle}</p>
      )}
    </div>
  );
}
