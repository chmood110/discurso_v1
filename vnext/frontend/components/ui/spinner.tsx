export function Spinner({ size = "sm" }: { size?: "sm" | "md" | "lg" }) {
  const s = size === "sm" ? "h-4 w-4" : size === "md" ? "h-6 w-6" : "h-8 w-8";
  return (
    <div className={`${s} animate-spin rounded-full border-2 border-slate-200 border-t-emerald-600`} />
  );
}
