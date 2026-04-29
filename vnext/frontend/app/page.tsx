"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { AuroraBackground } from "@/components/ui/aurora-background";
import { cn } from "@/lib/cn";

/**
 * Landing page (/)
 *
 * The editorial entry point. Two modules are listed as huge typographic
 * rows with hover-driven opacity / scale shifts and a sky underline that
 * sweeps in from the left. The interaction is identical to the design
 * reference; everything else (background, fonts, accent) comes from the
 * shared design tokens.
 *
 * Lógica preservada: each module simply links to its existing route
 * (/analysis, /speech) — no shape change there.
 */

interface Modulo {
  id: string;
  numero: string;
  titulo: string;
  descripcion: string;
  href: string;
}

const MODULOS: Modulo[] = [
  {
    id: "analisis",
    numero: "01",
    titulo: "Análisis Territorial",
    descripcion:
      "Explora el panorama social y demográfico de los 60 municipios. Convierte datos complejos en estrategias políticas precisas y accionables.",
    href: "/analysis",
  },
  {
    id: "discurso",
    numero: "02",
    titulo: "Discurso Político",
    descripcion:
      "Crea narrativas desde cero o perfecciona tus textos actuales. Genera mensajes persuasivos y estructurados en segundos mediante inteligencia artificial.",
    href: "/speech",
  },
];

export default function HomePage() {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <AuroraBackground variant="aurora">
      <main className="flex min-h-screen flex-col items-center justify-center p-6 md:p-12">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-20">
          {/* ------- Hero ------- */}
          <header className="space-y-6">
            <p className="text-xs font-bold uppercase tracking-eyebrow text-sky-400 opacity-80">
              Voxpolítica · Tlaxcala
            </p>
            <h1 className="font-display text-5xl font-bold leading-none tracking-tight text-slate-50 md:text-7xl">
              Inteligencia <br className="hidden md:block" />
              <span className="font-light text-slate-400">Territorial</span>
            </h1>
          </header>

          {/* ------- Modules ------- */}
          <div
            className="relative flex w-full flex-col"
            onMouseLeave={() => setHoveredId(null)}
          >
            {MODULOS.map((modulo) => {
              const isHovered = hoveredId === modulo.id;
              const isOtherHovered =
                hoveredId !== null && hoveredId !== modulo.id;

              return (
                <Link
                  key={modulo.id}
                  href={modulo.href}
                  onMouseEnter={() => setHoveredId(modulo.id)}
                  className={cn(
                    "group relative flex cursor-pointer flex-col items-start py-12 transition-all duration-700 ease-out md:flex-row md:items-center",
                    isOtherHovered
                      ? "scale-[0.98] opacity-30"
                      : "scale-100 opacity-100"
                  )}
                >
                  {/* base hairline */}
                  <div className="absolute bottom-0 left-0 h-[1px] w-full bg-slate-800/40" />

                  {/* animated sky underline */}
                  <div
                    className={cn(
                      "absolute bottom-0 left-0 h-[1px] bg-gradient-to-r from-sky-400 via-sky-600 to-transparent transition-all duration-1000 ease-in-out",
                      isHovered ? "w-full opacity-100" : "w-0 opacity-0"
                    )}
                  />

                  {/* large typographic number */}
                  <div className="mb-6 w-24 shrink-0 md:mb-0">
                    <span
                      className={cn(
                        "font-display text-5xl font-light tracking-tighter transition-colors duration-700 md:text-7xl",
                        isHovered
                          ? "text-sky-400/80"
                          : "text-slate-700/50"
                      )}
                    >
                      {modulo.numero}
                    </span>
                  </div>

                  {/* central content */}
                  <div className="flex-grow pr-8 md:pl-8">
                    <h2
                      className={cn(
                        "mb-4 font-display text-3xl font-semibold transition-all duration-500 md:text-4xl",
                        isHovered
                          ? "translate-x-2 text-white"
                          : "text-slate-200"
                      )}
                    >
                      {modulo.titulo}
                    </h2>
                    <p
                      className={cn(
                        "max-w-2xl font-body text-lg font-light leading-relaxed transition-all delay-75 duration-500",
                        isHovered
                          ? "translate-x-2 text-slate-300"
                          : "text-slate-500"
                      )}
                    >
                      {modulo.descripcion}
                    </p>
                  </div>

                  {/* arrow */}
                  <div className="mt-8 shrink-0 overflow-hidden md:mt-0">
                    <div
                      className={cn(
                        "transition-transform duration-700 ease-out",
                        isHovered
                          ? "translate-x-0 text-sky-400 opacity-100"
                          : "-translate-x-8 text-slate-600 opacity-0"
                      )}
                    >
                      <ArrowRight className="h-10 w-10" strokeWidth={1} />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>

          {/* ------- Footer ------- */}
          <footer className="flex items-center justify-between border-t border-slate-900 pt-8">
            <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
              VoxPolítica 2.0 · Estado de Tlaxcala, México
            </p>
            <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
              60 municipios · INEGI · CONEVAL
            </p>
          </footer>
        </div>
      </main>
    </AuroraBackground>
  );
}
