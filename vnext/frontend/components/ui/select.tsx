"use client";

import { MinimalSelect } from "./minimal-select";

/**
 * Legacy <Select /> shim — preserves the original {value, onChange, options,
 * label, placeholder, disabled} contract used by older pages, but renders
 * the new minimal selector underneath.
 */

interface Option {
  value: string;
  label: string;
}

interface Props {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  options: Option[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function Select({
  label,
  value,
  onChange,
  options,
  placeholder,
  disabled,
  className,
}: Props) {
  return (
    <div className={className}>
      {label && (
        <label className="mb-2 block text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500">
          {label}
        </label>
      )}
      <MinimalSelect
        value={value}
        onChange={onChange}
        options={options}
        placeholder={placeholder}
        disabled={disabled}
      />
    </div>
  );
}
