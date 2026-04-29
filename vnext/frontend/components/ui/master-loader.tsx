"use client";

import { Sparkles } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * MasterLoader
 *
 * Single source of truth for the "thinking" state across the platform.
 * Three concentric rings rotate at different speeds and directions around a
 * pulsing core. The `size` prop swaps between the dense Analysis variant
 * (240px, 3 rings) and the lighter Speech variant (200px, 2 rings).
 *
 * `headline` is rendered as Outfit-display uppercase. `subline` sits below
 * with the wide [0.3em] tracking we use for eyebrow labels everywhere.
 */

interface Props {
  size?: "lg" | "md";
  headline: string;
  subline?: string;
  showSpark?: boolean;
  className?: string;
}

export function MasterLoader({
  size = "lg",
  headline,
  subline,
  showSpark = false,
  className,
}: Props) {
  const isLg = size === "lg";

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        className
      )}
    >
      <div
        className="relative flex items-center justify-center"
        style={{
          width: isLg ? 240 : 200,
          height: isLg ? 240 : 200,
        }}
      >
        {/* outermost ring — only present in the large variant */}
        {isLg && (
          <Ring size={210} duration="25s" borderRadius="45%" opacity={0.5} />
        )}

        {/* mid ring — reverse rotation, with a satellite dot */}
        <Ring
          size={isLg ? 150 : 140}
          duration={isLg ? "15s" : "12s"}
          reverse
          borderRadius={isLg ? "40%" : "35%"}
        >
          <span
            className="absolute h-1.5 w-1.5 rounded-full"
            style={{
              bottom: -3,
              right: "20%",
              background: "#94a3b8",
            }}
          />
        </Ring>

        {/* inner ring — primary sky satellite */}
        <Ring size={isLg ? 100 : 90} duration={isLg ? "10s" : "8s"}>
          <span
            className="absolute h-1.5 w-1.5 rounded-full"
            style={{
              top: -3,
              left: "50%",
              background: "#38bdf8",
              boxShadow: "0 0 10px #38bdf8",
            }}
          />
        </Ring>

        {/* pulsing core */}
        <div
          className="relative z-10 flex items-center justify-center rounded-[14px]"
          style={{
            width: isLg ? 50 : 44,
            height: isLg ? 50 : 44,
            background: "#f8fafc",
            boxShadow: "0 0 40px rgba(248, 250, 252, 0.25)",
            animation: "pulseCore 2s ease-in-out infinite alternate",
          }}
        >
          {showSpark ? (
            <Sparkles className="h-5 w-5 fill-current text-slate-900" />
          ) : (
            <span
              className="block rounded-[3px]"
              style={{ width: 10, height: 10, background: "#0f172a" }}
            />
          )}
        </div>
      </div>

      <div className="mt-12 space-y-2">
        <h2 className="font-display text-xl font-bold uppercase tracking-eyebrow_xs text-white">
          {headline}
        </h2>
        {subline && (
          <p className="text-[10px] font-bold uppercase tracking-eyebrow text-slate-600">
            {subline}
          </p>
        )}
      </div>
    </div>
  );
}

interface RingProps {
  size: number;
  duration: string;
  reverse?: boolean;
  borderRadius?: string;
  opacity?: number;
  children?: React.ReactNode;
}

function Ring({
  size,
  duration,
  reverse,
  borderRadius = "35%",
  opacity = 1,
  children,
}: RingProps) {
  return (
    <div
      className="absolute"
      style={{
        width: size,
        height: size,
        border: "1px solid rgba(226, 232, 240, 0.05)",
        borderRadius,
        opacity,
        animation: `rotate ${duration} linear infinite${reverse ? " reverse" : ""}`,
      }}
    >
      {children}
    </div>
  );
}
