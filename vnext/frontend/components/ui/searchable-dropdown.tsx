"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * SearchableDropdown
 *
 * The "no boxes, only typography" selector used as the headline of every form.
 * Closed: a single oversized Outfit phrase sitting on a hairline border that
 *         underlines the value (or the placeholder, dimmed to slate-900).
 * Open:   a floating panel anchored to the trigger with a search field and
 *         a virtual list of options. ESC and outside-click both close it.
 *
 * The component is generic over the option's `value`. Pass `options` as
 * `{ value, label, sublabel? }` so it can wrap typed objects (Municipality,
 * Neighborhood, …) without hard-coding any business shape.
 */

export interface DropdownOption {
  value: string;
  label: string;
  sublabel?: string;
}

interface Props {
  options: DropdownOption[];
  value: string;
  onChange: (value: string, option: DropdownOption) => void;
  placeholder: string;
  searchPlaceholder?: string;
  emptyLabel?: string;
  loading?: boolean;
  disabled?: boolean;
  /** Visual size of the trigger label. */
  size?: "lg" | "md";
}

export function SearchableDropdown({
  options,
  value,
  onChange,
  placeholder,
  searchPlaceholder = "Filtro de búsqueda…",
  emptyLabel = "Sin coincidencias",
  loading = false,
  disabled = false,
  size = "lg",
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === "Escape") setIsOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  const selected = options.find((o) => o.value === value);
  const displayLabel = selected?.label ?? "";

  const filtered = options.filter((opt) => {
    const q = query.toLowerCase().trim();
    if (!q) return true;
    return (
      opt.label.toLowerCase().includes(q) ||
      (opt.sublabel ? opt.sublabel.toLowerCase().includes(q) : false)
    );
  });

  const triggerSize =
    size === "lg"
      ? "text-4xl md:text-6xl"
      : "text-3xl md:text-5xl";

  return (
    <div
      ref={wrapperRef}
      className={cn("relative w-full", disabled && "pointer-events-none opacity-40")}
    >
      <div
        role="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((v) => !v)}
        className="group flex w-full cursor-pointer items-center justify-between border-b border-slate-800 py-4 transition-all hover:border-sky-500/50"
      >
        <span
          className={cn(
            "font-display font-extrabold tracking-tighter transition-colors",
            triggerSize,
            displayLabel ? "text-white" : "text-slate-900"
          )}
        >
          {displayLabel || (loading ? "Cargando…" : placeholder)}
        </span>
        <ChevronDown
          className={cn(
            "h-8 w-8 text-slate-800 transition-all duration-500",
            isOpen && "rotate-180 text-sky-500"
          )}
        />
      </div>

      {isOpen && (
        <div className="absolute left-0 top-full z-[100] mt-2 w-full animate-fade-in border border-slate-900 bg-ink shadow-2xl">
          <div className="flex items-center gap-4 border-b border-slate-900 p-6">
            <Search className="h-5 w-5 text-slate-700" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full border-none bg-transparent text-xl font-light text-white placeholder:text-slate-800 focus:outline-none"
            />
          </div>

          <div
            className="thin-scrollbar max-h-96 overflow-y-auto py-4"
            role="listbox"
          >
            {filtered.length === 0 ? (
              <div className="px-10 py-10 text-sm font-bold uppercase tracking-eyebrow text-slate-800">
                {emptyLabel}
              </div>
            ) : (
              filtered.map((opt) => {
                const isSelected = opt.value === value;
                return (
                  <div
                    key={opt.value}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      onChange(opt.value, opt);
                      setIsOpen(false);
                      setQuery("");
                    }}
                    className={cn(
                      "flex cursor-pointer items-center justify-between px-10 py-4 transition-colors",
                      isSelected
                        ? "font-bold text-sky-400"
                        : "text-slate-500 hover:bg-white/5 hover:text-white"
                    )}
                  >
                    <div className="flex flex-col">
                      <span className="font-display text-2xl uppercase tracking-tight">
                        {opt.label}
                      </span>
                      {opt.sublabel && (
                        <span className="mt-0.5 text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
                          {opt.sublabel}
                        </span>
                      )}
                    </div>
                    {isSelected && (
                      <span className="h-2 w-2 rounded-full bg-sky-400" />
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
