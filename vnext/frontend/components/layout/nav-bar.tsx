"use client";

import Link from "next/link";
import { cn } from "@/lib/cn";

/**
 * NavBar
 *
 * Shared header used by /analysis and /speech.
 *  · Left: the VOXPOLÍTICA wordmark with a sky stripe
 *  · Center (optional): tab pill — used by Speech for create/improve
 *  · Right (optional): a free-form action slot (back link, "Nuevo análisis", etc.)
 *
 * The component is fully presentational. Every page wires its own state in.
 */

export interface NavTab<T extends string> {
  value: T;
  label: string;
  icon?: React.ReactNode;
}

interface Props<T extends string> {
  /** When `false` the bar floats over the page; when `true` it sticks to top. */
  fixed?: boolean;
  tabs?: NavTab<T>[];
  activeTab?: T;
  onTabChange?: (tab: T) => void;
  rightSlot?: React.ReactNode;
  /** Adds a small "Inicio" link before the right slot. */
  showHome?: boolean;
}

export function NavBar<T extends string>({
  fixed = false,
  tabs,
  activeTab,
  onTabChange,
  rightSlot,
  showHome = false,
}: Props<T>) {
  return (
    <nav
      className={cn(
        "z-50 w-full border-b border-white/5 backdrop-blur-md",
        fixed
          ? "fixed left-0 top-0 px-8 py-6"
          : "px-10 py-12"
      )}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6">
        <Link href="/" className="flex items-center gap-3 group">
          <div className={cn("bg-sky-500 transition-all", fixed ? "h-6 w-1.5" : "h-[2px] w-8")} />
          <h2
            className={cn(
              "font-display font-extrabold tracking-tighter text-white",
              fixed ? "text-xl" : "text-2xl"
            )}
          >
            VOXPOLÍTICA
            {!fixed && (
              <span className="ml-1 font-light tracking-normal text-slate-500">
                / TLAXCALA
              </span>
            )}
          </h2>
        </Link>

        {tabs && tabs.length > 0 && (
          <div className="flex rounded-full border border-white/5 bg-slate-950/50 p-1">
            {tabs.map((t) => {
              const isActive = t.value === activeTab;
              return (
                <button
                  key={t.value}
                  onClick={() => onTabChange?.(t.value)}
                  className={cn(
                    "flex items-center gap-2 rounded-full px-6 py-2 text-xs font-bold uppercase tracking-widest transition-all",
                    isActive
                      ? "bg-sky-500 text-black shadow-lg"
                      : "text-slate-500 hover:text-white"
                  )}
                >
                  {t.icon}
                  {t.label}
                </button>
              );
            })}
          </div>
        )}

        <div className="flex items-center gap-6">
          {showHome && (
            <Link
              href="/"
              className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500 transition-colors hover:text-sky-400"
            >
              ← Inicio
            </Link>
          )}
          {rightSlot}
        </div>
      </div>
    </nav>
  );
}
