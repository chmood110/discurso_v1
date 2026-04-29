import { cn } from "@/lib/cn";

export function Spinner({ size = "sm" }: { size?: "sm" | "md" | "lg" }) {
  const dim =
    size === "sm" ? "h-4 w-4" : size === "md" ? "h-6 w-6" : "h-8 w-8";
  return (
    <div
      className={cn(
        "animate-spin rounded-full border-2 border-slate-700/40 border-t-sky-400",
        dim
      )}
    />
  );
}
