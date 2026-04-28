"use client";
interface Props extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}
export function Textarea({ label, error, className = "", ...props }: Props) {
  return (
    <div className={className}>
      {label && <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>}
      <textarea
        className={`w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none ${error ? "border-red-400" : "border-slate-300"}`}
        {...props}
      />
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
  );
}
