import { cn } from "@/lib/cn";

/**
 * SectionLabel — the small uppercase eyebrow (10px, 0.3em tracking) used
 * to mark every section of every form. The optional `number` prop reproduces
 * the "01 Demarcación", "02 Área Específica" pattern from the design.
 *
 * Tone:
 *   accent   → bright sky (active/required step)
 *   muted    → slate-600 (secondary or completed step)
 *
 * Optional `icon` slot accepts a lucide icon element.
 */

interface Props {
  children: React.ReactNode;
  number?: string;
  icon?: React.ReactNode;
  tone?: "accent" | "muted";
  className?: string;
}

export function SectionLabel({
  children,
  number,
  icon,
  tone = "accent",
  className,
}: Props) {
  const color = tone === "accent" ? "text-sky-500" : "text-slate-600";

  return (
    <div
      className={cn(
        "flex items-center gap-3 text-[10px] font-black uppercase tracking-eyebrow",
        color,
        className
      )}
    >
      {icon}
      {number && <span>{number}</span>}
      <span>{children}</span>
    </div>
  );
}
