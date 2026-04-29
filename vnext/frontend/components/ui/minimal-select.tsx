"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * MinimalSelect
 *
 * The smaller cousin of SearchableDropdown — for low-cardinality enums
 * (tone, channel) rendered inside a 3-column parameter grid.
 * Same border-bottom-only language, no search input, no fancy hover states.
 */

export interface MinimalSelectOption {
  value: string;
  label: string;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  options: MinimalSelectOption[];
  placeholder?: string;
  disabled?: boolean;
}

export function MinimalSelect({
  value,
  onChange,
  options,
  placeholder = "Selecciona…",
  disabled,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const current = options.find((o) => o.value === value);

  return (
    <div
      ref={wrapperRef}
      className={cn("relative", disabled && "pointer-events-none opacity-40")}
    >
      <div
        onClick={() => setIsOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center justify-between border-b border-slate-800 py-3 text-lg font-light text-white transition-all hover:border-slate-500"
      >
        <span className="truncate">{current?.label ?? placeholder}</span>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-slate-700 transition-transform",
            isOpen && "rotate-180"
          )}
        />
      </div>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-2 w-full animate-fade-in border border-slate-900 bg-slate-950 py-2 shadow-2xl">
          {options.map((opt) => {
            const isSelected = opt.value === value;
            return (
              <div
                key={opt.value}
                onClick={() => {
                  onChange(opt.value);
                  setIsOpen(false);
                }}
                className={cn(
                  "cursor-pointer px-4 py-3 text-sm transition-colors",
                  isSelected
                    ? "bg-white/5 text-sky-400"
                    : "text-slate-400 hover:bg-white/5 hover:text-white"
                )}
              >
                {opt.label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
