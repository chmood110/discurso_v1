"use client";

/* ============================================================================
 * /analysis — Análisis Territorial
 *
 * Lógica de negocio PRESERVADA al 100% del proyecto original:
 *   · useAppStore (zustand) gobierna selection / analysisRun / loading / errors
 *   · api.analysis.run preserva el contrato del backend (force_refresh,
 *     objective, municipality_id) — primer fetch automático al elegir municipio,
 *     regeneración manual con force_refresh=true
 *   · api.exports.analysisBlob + downloadBlob para PDF
 *   · Render completo de critical_needs, opportunities, kpi_board.kpis,
 *     strategy_section (executive_strategic, messaging_axes, candidate_positioning,
 *     recommended_tone + communication_channels_priority, framing_suggestions,
 *     risk_flags), validation report, methodology disclaimer, confidence bar.
 *
 * Lo que cambia es exclusivamente la capa visual.
 * ========================================================================== */

import { useEffect, useState } from "react";
import { ArrowRight, FileDown, MapPin, Target } from "lucide-react";

import { AuroraBackground } from "@/components/ui/aurora-background";
import { MasterLoader } from "@/components/ui/master-loader";
import { MinimalInput } from "@/components/ui/minimal-input";
import { SectionLabel } from "@/components/ui/section-label";
import { TerritorySelector } from "@/components/layout/territory-selector";
import { NavBar } from "@/components/layout/nav-bar";
import {
  ConfidenceBar,
  QualityBadge,
} from "@/components/data-quality/quality-badge";
import { MethodologyDisclaimer } from "@/components/data-quality/methodology-disclaimer";
import { ValidationReportPanel } from "@/components/data-quality/validation-report";

import { useAppStore } from "@/lib/store";
import * as api from "@/lib/api";
import { cn } from "@/lib/cn";
import type {
  AnalysisDetail,
  CriticalNeed,
  MessagingAxis,
  StrategySection,
} from "@/types";

// ---------- helpers (same as the original) -----------------------------------

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asRecordArray(value: unknown): UnknownRecord[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function getNeedDescription(need: CriticalNeed): string {
  const raw = (need as UnknownRecord).description;
  return typeof raw === "string" ? raw : "";
}

function getNeedAffectedPopulationPct(need: CriticalNeed): number | null {
  const raw = (need as UnknownRecord).affected_population_pct;
  return asNumber(raw);
}

// =============================================================================

export default function AnalysisPage() {
  const {
    selection,
    analysisRun,
    setAnalysisRun,
    loading,
    setLoading,
    errors,
    setError,
    clearError,
  } = useAppStore();

  const [objective, setObjective] = useState("");
  const [zona, setZona] = useState("");

  // First fetch when a municipality is set — same logic as v1.
  useEffect(() => {
    if (!selection.municipalityId) return;
    let mounted = true;

    api.analysis
      .run({
        municipality_id: selection.municipalityId,
        force_refresh: false,
      })
      .then((run) => {
        if (mounted) setAnalysisRun(run);
      })
      .catch(() => {
        // silently — first-fetch errors don't show; user retries via button
      });

    return () => {
      mounted = false;
    };
  }, [selection.municipalityId, setAnalysisRun]);

  async function handleRun(forceRefresh = false) {
    if (!selection.municipalityId) return;

    clearError("analysis");
    setLoading("analysis", true);

    try {
      const run = await api.analysis.run({
        municipality_id: selection.municipalityId,
        objective: objective || undefined,
        force_refresh: forceRefresh,
      });
      setAnalysisRun(run);
    } catch (e: unknown) {
      setError(
        "analysis",
        e instanceof Error ? e.message : "Error generando análisis"
      );
    } finally {
      setLoading("analysis", false);
    }
  }

  async function handleExport() {
    if (!analysisRun) return;
    setLoading("export", true);

    try {
      const blob = await api.exports.analysisBlob(analysisRun.id);
      api.downloadBlob(blob, `analisis-${selection.municipalityName}.pdf`);
    } catch (e: unknown) {
      setError(
        "export",
        e instanceof Error ? e.message : "Error exportando PDF"
      );
    } finally {
      setLoading("export", false);
    }
  }

  const hasResult = !!analysisRun && !loading.analysis;
  const isLoading = loading.analysis;

  return (
    <AuroraBackground variant="soft">
      <NavBar
        rightSlot={
          hasResult ? (
            <button
              onClick={() => {
                setAnalysisRun(null);
                clearError("analysis");
              }}
              className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500 transition-colors hover:text-sky-400"
            >
              Nuevo análisis
            </button>
          ) : (
            <span className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
              ← Inicio
            </span>
          )
        }
      />

      <main className="mx-auto max-w-6xl px-10 pb-32">
        {/* ----- LOADING STATE ----- */}
        {isLoading && (
          <div className="flex min-h-[60vh] items-center justify-center">
            <MasterLoader
              size="lg"
              headline="Sincronizando inteligencia"
              subline="Procesando vectores territoriales"
            />
          </div>
        )}

        {/* ----- FORM STATE ----- */}
        {!isLoading && !hasResult && (
          <FormView
            objective={objective}
            setObjective={setObjective}
            zona={zona}
            setZona={setZona}
            disabled={isLoading}
            onSubmit={() => handleRun(false)}
            error={errors.analysis}
          />
        )}

        {/* ----- RESULTS STATE ----- */}
        {hasResult && analysisRun && (
          <ResultView
            run={analysisRun}
            zona={zona}
            municipalityName={selection.municipalityName}
            objective={objective || analysisRun.objective || ""}
            onRegenerate={() => handleRun(true)}
            regenerateLoading={loading.analysis}
            onExport={handleExport}
            exportLoading={loading.export}
          />
        )}
      </main>
    </AuroraBackground>
  );
}

// =============================================================================
// FORM
// =============================================================================

interface FormViewProps {
  objective: string;
  setObjective: (v: string) => void;
  zona: string;
  setZona: (v: string) => void;
  disabled: boolean;
  onSubmit: () => void;
  error?: string;
}

function FormView({
  objective,
  setObjective,
  zona,
  setZona,
  disabled,
  onSubmit,
  error,
}: FormViewProps) {
  const { selection } = useAppStore();
  const canSubmit = !!selection.municipalityId && !disabled;

  return (
    <div className="animate-fade-in-slow">
      <header className="mb-20">
        <h1 className="font-display text-7xl font-extrabold leading-[0.9] tracking-tighter text-white md:text-8xl">
          Inteligencia <br />
          <span className="text-slate-700">Territorial.</span>
        </h1>
        <p className="mt-8 max-w-2xl text-xl font-light leading-relaxed text-slate-400">
          Sistema de diagnóstico demográfico y prospectiva estratégica para la
          toma de decisiones de alto nivel.
        </p>
      </header>

      <div className="max-w-4xl space-y-24">
        {/* 01 — Demarcación (municipio + opcional vecindad) */}
        <section className="space-y-6">
          <SectionLabel number="01" tone="accent" icon={<MapPin className="h-3.5 w-3.5" />}>
            Demarcación
          </SectionLabel>
          <TerritorySelector disabled={disabled} size="lg" />
        </section>

        {/* 02 + 03 — Zona + objetivo en grid */}
        <section className="grid gap-20 md:grid-cols-2">
          <div className="space-y-6">
            <SectionLabel number="02" tone="muted">
              Área específica
            </SectionLabel>
            <MinimalInput
              value={zona}
              onChange={(e) => setZona(e.target.value)}
              placeholder="Barrio o zona (opcional)"
              disabled={!selection.municipalityId || disabled}
              inputSize="lg"
            />
          </div>
          <div className="space-y-6">
            <SectionLabel
              number="03"
              tone="muted"
              icon={<Target className="h-3.5 w-3.5" />}
            >
              Objetivo crítico
            </SectionLabel>
            <MinimalInput
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="Ej. Seguridad ciudadana"
              disabled={disabled}
              inputSize="lg"
            />
          </div>
        </section>

        {error && (
          <div className="border-l-2 border-red-400/40 bg-red-500/5 px-6 py-4">
            <p className="text-sm font-light text-red-200">{error}</p>
          </div>
        )}

        <div className="flex justify-end pt-12">
          <button
            type="button"
            onClick={onSubmit}
            disabled={!canSubmit}
            className="group flex items-center gap-10 text-white transition-all disabled:opacity-20"
          >
            <div className="text-right">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-eyebrow_xs text-sky-500">
                Confirmar
              </p>
              <p className="font-display text-2xl font-bold">
                GENERAR DIAGNÓSTICO
              </p>
            </div>
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/20 transition-all duration-500 group-hover:bg-white group-hover:text-black">
              <ArrowRight className="h-6 w-6" />
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// RESULTS
// =============================================================================

interface ResultViewProps {
  run: AnalysisDetail;
  zona: string;
  municipalityName: string;
  objective: string;
  onRegenerate: () => void;
  regenerateLoading: boolean;
  onExport: () => void;
  exportLoading: boolean;
}

function ResultView({
  run,
  zona,
  municipalityName,
  objective,
  onRegenerate,
  regenerateLoading,
  onExport,
  exportLoading,
}: ResultViewProps) {
  const qualityLevel = run.data_quality.can_cite_as_municipal
    ? "official_municipal"
    : "calibrated_estimate";

  return (
    <div className="animate-fade-in-slow space-y-32">
      {/* ===== Header ===== */}
      <section className="space-y-10 border-b border-slate-900 pb-16">
        <div className="flex items-center gap-3">
          <div className="h-2 w-2 animate-pulse rounded-full bg-sky-500" />
          <span className="text-[10px] font-black uppercase tracking-eyebrow text-sky-500">
            Informe Territorial Consolidado
          </span>
          <span className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
            · {new Date(run.created_at).toLocaleDateString("es-MX")}
          </span>
        </div>

        <div className="flex flex-col items-end justify-between gap-12 md:flex-row">
          <div className="space-y-4">
            <h1 className="font-display text-7xl font-extrabold leading-none tracking-tighter text-white md:text-8xl">
              {municipalityName || run.municipality_id}
            </h1>
            {zona && (
              <p className="text-3xl font-light italic text-slate-600">
                Demarcación: {zona}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <QualityBadge level={qualityLevel} />
              <ConfidenceBar confidence={run.data_quality.overall_confidence} />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6">
            <button
              onClick={onRegenerate}
              disabled={regenerateLoading}
              className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500 transition-colors hover:text-white disabled:opacity-30"
            >
              {regenerateLoading ? "Regenerando…" : "↻ Regenerar"}
            </button>
            <button
              onClick={onExport}
              disabled={exportLoading}
              className="flex items-center gap-3 border-b-2 border-white pb-2 text-[10px] font-black uppercase tracking-eyebrow_xs transition-all hover:border-sky-400 hover:text-sky-400 disabled:opacity-40"
            >
              {exportLoading ? "Exportando…" : "Exportar PDF"}{" "}
              <FileDown className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {!run.data_quality.can_cite_as_municipal && (
          <MethodologyDisclaimer
            disclaimer="Este análisis usa estimaciones regionales calibradas. Las cifras son orientativas, no estadísticas municipales exactas."
            quality_label="Datos estimados"
          />
        )}
      </section>

      {/* ===== Editorial grid ===== */}
      <div className="grid gap-20 md:grid-cols-12">
        {/* --- Left column (8 cols): narrative ----------------------------- */}
        <div className="space-y-20 md:col-span-8">
          {/* Executive summary */}
          {run.executive_summary && (
            <article className="space-y-8">
              <SectionLabel tone="muted">
                <span className="mr-3 inline-block h-px w-10 bg-slate-800 align-middle" />
                Análisis de situación
              </SectionLabel>
              <p className="font-display text-3xl font-light leading-tight text-white md:text-4xl">
                {run.executive_summary}
              </p>
              {objective && (
                <p className="border-l border-slate-800 pl-8 text-lg font-light leading-relaxed text-slate-400">
                  Objetivo crítico declarado:{" "}
                  <span className="font-medium text-slate-200">
                    {objective}
                  </span>
                  .
                </p>
              )}
            </article>
          )}

          {/* Critical needs */}
          {run.critical_needs?.length > 0 && (
            <article className="space-y-12">
              <SectionLabel tone="muted">
                <span className="mr-3 inline-block h-px w-10 bg-slate-800 align-middle" />
                Necesidades críticas
              </SectionLabel>
              <div className="space-y-10">
                {run.critical_needs.map((need, i) => (
                  <NeedRow key={i} need={need} index={i} />
                ))}
              </div>
            </article>
          )}

          {/* Opportunities */}
          {run.opportunities?.length > 0 && (
            <article className="space-y-12">
              <SectionLabel tone="muted">
                <span className="mr-3 inline-block h-px w-10 bg-slate-800 align-middle" />
                Oportunidades estratégicas
              </SectionLabel>
              <ul className="space-y-4">
                {run.opportunities.map((opportunity, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-4 text-base font-light leading-relaxed text-slate-300"
                  >
                    <ArrowRight className="mt-1.5 h-4 w-4 shrink-0 text-sky-500" />
                    <span>{opportunity}</span>
                  </li>
                ))}
              </ul>
            </article>
          )}

          {/* Strategy section (full editorial) */}
          {run.strategy_section && (
            <StrategySectionPanel strategy={run.strategy_section} />
          )}

          {/* Validation issues — surfaced when present */}
          {run.validation?.issues?.length > 0 && (
            <article className="space-y-8">
              <SectionLabel tone="muted">
                <span className="mr-3 inline-block h-px w-10 bg-slate-800 align-middle" />
                Validación del informe
              </SectionLabel>
              <ValidationReportPanel report={run.validation} />
            </article>
          )}
        </div>

        {/* --- Right column (4 cols): hard data ----------------------------- */}
        <aside className="space-y-20 md:col-span-4">
          <KPIBoard kpiBoard={run.kpi_board} />
          <RunMetadata run={run} />
        </aside>
      </div>
    </div>
  );
}

// =============================================================================
// SUBCOMPONENTS
// =============================================================================

function NeedRow({ need, index }: { need: CriticalNeed; index: number }) {
  const description = getNeedDescription(need);
  const affected = getNeedAffectedPopulationPct(need);

  const severityColor =
    need.severity === "alta"
      ? "text-red-300"
      : need.severity === "media"
        ? "text-amber-300"
        : "text-slate-400";

  return (
    <div className="space-y-3 border-l border-slate-800 pl-6">
      <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-eyebrow_xs">
        <span className="text-slate-700">{String(index + 1).padStart(2, "0")}</span>
        {need.severity && (
          <span className={severityColor}>· severidad {need.severity}</span>
        )}
      </div>
      <h4 className="text-xl font-bold text-white">{need.title}</h4>
      {description && (
        <p className="text-sm font-light leading-relaxed text-slate-400">
          {description}
        </p>
      )}
      {affected !== null && (
        <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-600">
          Afecta al {affected.toFixed(0)}% de la población
        </p>
      )}
    </div>
  );
}

function KPIBoard({ kpiBoard }: { kpiBoard: Record<string, unknown> }) {
  const kpis = asRecordArray(kpiBoard?.kpis);
  if (!kpis.length) return null;

  return (
    <section className="space-y-12">
      <SectionLabel tone="muted">Métricas clave</SectionLabel>
      <div className="space-y-12">
        {kpis.slice(0, 4).map((kpi, i) => {
          const base = asNumber(kpi.baseline_value);
          const target = asNumber(kpi.target_value);
          const unit = asString(kpi.baseline_unit);
          const name = asString(kpi.name, "Indicador");

          if (base === null) return null;

          return (
            <div key={i} className="group cursor-default space-y-2">
              <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700 transition-colors group-hover:text-sky-500">
                {name}
              </p>
              <p className="font-display text-5xl font-extrabold tracking-tighter text-white">
                {base.toLocaleString()}
                {unit && (
                  <span className="ml-2 text-2xl font-light text-slate-500">
                    {unit}
                  </span>
                )}
              </p>
              {target !== null && (
                <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-sky-400">
                  Meta · {target.toLocaleString()} {unit}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RunMetadata({ run }: { run: AnalysisDetail }) {
  return (
    <section className="space-y-6 border-t border-slate-900 pt-10">
      <SectionLabel tone="muted">Metadatos del run</SectionLabel>
      <dl className="space-y-4 text-xs">
        <MetaRow label="ID" value={run.id.slice(0, 8) + "…"} mono />
        <MetaRow label="Status" value={run.status} />
        <MetaRow
          label="Generado"
          value={new Date(run.created_at).toLocaleString("es-MX")}
        />
        <MetaRow
          label="Cobertura"
          value={`${(run.data_quality.overall_confidence * 100).toFixed(0)}% conf.`}
        />
      </dl>
    </section>
  );
}

function MetaRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between border-b border-slate-900/60 pb-3">
      <dt className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
        {label}
      </dt>
      <dd className={cn("text-slate-300", mono && "font-mono")}>{value}</dd>
    </div>
  );
}

// ---------- Strategy section ------------------------------------------------

function StrategySectionPanel({ strategy }: { strategy: StrategySection }) {
  const hasContent =
    Boolean(strategy.executive_strategic) ||
    Boolean(strategy.messaging_axes?.length) ||
    Boolean(strategy.candidate_positioning) ||
    Boolean(strategy.recommended_tone) ||
    Boolean(strategy.framing_suggestions?.length) ||
    Boolean(strategy.risk_flags?.length);

  if (!hasContent) return null;

  return (
    <article className="space-y-12">
      <SectionLabel tone="accent">
        <span className="mr-3 inline-block h-px w-10 bg-sky-700/40 align-middle" />
        Estrategia de comunicación
        {strategy.ai_generated && (
          <span className="ml-2 text-slate-700">· IA</span>
        )}
      </SectionLabel>

      {strategy.executive_strategic && (
        <p className="font-display text-2xl font-light leading-tight text-white md:text-3xl">
          {strategy.executive_strategic}
        </p>
      )}

      {strategy.messaging_axes?.length > 0 && (
        <div className="space-y-10">
          <h4 className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500">
            Ejes de mensaje
          </h4>
          <div className="grid gap-10 sm:grid-cols-2">
            {strategy.messaging_axes.map((ax, i) => (
              <AxisCard key={i} ax={ax} />
            ))}
          </div>
        </div>
      )}

      {(strategy.candidate_positioning || strategy.recommended_tone) && (
        <div className="grid gap-12 md:grid-cols-2">
          {strategy.candidate_positioning && (
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500">
                Posicionamiento
              </h4>
              <p className="text-base font-light leading-relaxed text-slate-300">
                {strategy.candidate_positioning}
              </p>
            </div>
          )}
          {strategy.recommended_tone && (
            <div className="space-y-3">
              <h4 className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500">
                Tono recomendado
              </h4>
              <p className="text-base font-light leading-relaxed text-slate-300">
                {strategy.recommended_tone}
              </p>
              {strategy.communication_channels_priority?.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {strategy.communication_channels_priority.map((ch, i) => (
                    <span
                      key={i}
                      className="rounded-full border border-sky-400/30 bg-sky-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-eyebrow_xs text-sky-300"
                    >
                      {ch}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {strategy.framing_suggestions?.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500">
            Framings
          </h4>
          <div className="space-y-3">
            {strategy.framing_suggestions.map((framing, i) => (
              <p
                key={i}
                className="border-l-2 border-sky-400/40 pl-4 text-base font-light italic text-slate-300"
              >
                {framing}
              </p>
            ))}
          </div>
        </div>
      )}

      {strategy.risk_flags?.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-amber-300">
            ⚠ Riesgos comunicacionales
          </h4>
          <ul className="space-y-2">
            {strategy.risk_flags.map((risk, i) => (
              <li
                key={i}
                className="text-sm font-light leading-relaxed text-amber-100/80"
              >
                · {risk}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

function AxisCard({ ax }: { ax: MessagingAxis }) {
  return (
    <div className="space-y-3 border-l-2 border-sky-500/60 pl-5">
      <p className="text-sm font-bold uppercase tracking-eyebrow_xs text-white">
        {ax.axis}
      </p>
      <p className="text-base font-light leading-relaxed text-slate-300">
        {ax.message}
      </p>
      <div className="space-y-1 pt-1 text-xs">
        {ax.rationale && (
          <p className="text-slate-500">
            <span className="font-bold text-slate-400">Argumento · </span>
            {ax.rationale}
          </p>
        )}
        {ax.data_anchor && (
          <p className="text-sky-400">
            <span className="font-bold">Dato ancla · </span>
            {ax.data_anchor}
          </p>
        )}
        {ax.emotional_hook && (
          <p className="text-violet-300">
            <span className="font-bold">Emoción · </span>
            {ax.emotional_hook}
          </p>
        )}
      </div>
    </div>
  );
}
