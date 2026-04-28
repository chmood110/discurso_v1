"use client";
interface Option { value: string; label: string; }
interface Props {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  options: Option[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}
export function Select({ label, value, onChange, options, placeholder, disabled, className = "" }: Props) {
  return (
    <div className={className}>
      {label && <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
