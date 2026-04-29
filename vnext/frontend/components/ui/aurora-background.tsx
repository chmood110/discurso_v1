/**
 * AuroraBackground
 *
 * The animated deep-navy aurora used as the canvas of the landing page.
 * Wraps its children inside a flex container so it can be dropped in as a
 * full-screen layout primitive without any extra wrapper.
 *
 * The "soft" variant skips the panning animation and uses a static radial
 * gradient — quieter, cheaper, and the right choice for content-heavy
 * pages (Analysis, Speech) where we don't want background motion competing
 * with the foreground.
 */

import { cn } from "@/lib/cn";

interface Props {
  children: React.ReactNode;
  variant?: "aurora" | "soft";
  className?: string;
}

export function AuroraBackground({
  children,
  variant = "aurora",
  className,
}: Props) {
  const bg =
    variant === "aurora"
      ? "bg-aurora-navy bg-300 animate-aurora-pan"
      : "bg-soft-radial";

  return (
    <div
      className={cn(
        "relative min-h-screen w-full text-slate-200",
        bg,
        className
      )}
    >
      {children}
    </div>
  );
}
