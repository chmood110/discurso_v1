"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { TerritorySelector } from "@/components/layout/territory-selector";
import { QualityBadge, ConfidenceBar } from "@/components/data-quality/quality-badge";
import { MethodologyDisclaimer } from "@/components/data-quality/methodology-disclaimer";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAppStore } from "@/lib/store";
import * as api from "@/lib/api";
import type {
  AnalysisDetail,
  CriticalNeed,
  StrategySection,
  MessagingAxis,
} from "@/types";

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

  useEffect(() => {
    if (!selection.municipalityId) return;

    let mounted = true;

    api.analysis
      .run({ municipality_id: selection.municipalityId, force_refresh: false })
      .then((run) => {
        if (mounted) setAnalysisRun(run);
      })
      .catch(() => {});

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
      setError("analysis", e instanceof Error ? e.message : "Error generando análisis");
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
      setError("export", e instanceof Error ? e.message : "Error exportando PDF");
    } finally {
      setLoading("export", false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <div className="flex items-start justify-between">
        <div>
          <p className="mb-1 text-xs font-bold uppercase tracking-widest text-emerald-600">
            VoxPolítica
          </p>
          <h1 className="text-2xl font-bold text-slate-900">Análisis Territorial</h1>
          <p className="mt-1 text-sm text-slate-500">
            Diagnóstico INEGI/CONEVAL + estrategia de comunicación integrada
          </p>
        </div>
        <Link href="/" className="text-sm text-slate-400 hover:text-slate-600">
          ← Inicio
        </Link>
      </div>

      <Card>
        <CardHeader title="Territorio" />
        <TerritorySelector disabled={loading.analysis} />
        <div className="mt-4 space-y-3">
          <input
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="Objetivo del análisis (opcional)"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <div className="flex gap-2">
            <Button
              onClick={() => handleRun(false)}
              loading={loading.analysis}
              disabled={!selection.municipalityId}
              className="flex-1"
            >
              {analysisRun ? "Usar análisis vigente" : "Generar análisis"}
            </Button>
            {analysisRun && (
              <Button
                variant="secondary"
                onClick={() => handleRun(true)}
                loading={loading.analysis}
              >
                Regenerar
              </Button>
            )}
          </div>
        </div>
      </Card>

      {errors.analysis && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errors.analysis}
        </div>
      )}

      {analysisRun && (
        <AnalysisResult
          run={analysisRun}
          onExport={handleExport}
          exportLoading={loading.export}
        />
      )}
    </main>
  );
}

function AnalysisResult({
  run,
  onExport,
  exportLoading,
}: {
  run: AnalysisDetail;
  onExport: () => void;
  exportLoading: boolean;
}) {
  const qualityLevel = run.data_quality.can_cite_as_municipal
    ? "official_municipal"
    : "calibrated_estimate";

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-100 bg-gradient-to-r from-emerald-50 to-slate-50 p-5">
        <div className="mb-3 flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900">{run.municipality_id}</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {new Date(run.created_at).toLocaleString("es-MX")}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <QualityBadge level={qualityLevel} />
            <Button
              variant="secondary"
              size="sm"
              onClick={onExport}
              loading={exportLoading}
            >
              ↓ PDF
            </Button>
          </div>
        </div>
        <ConfidenceBar confidence={run.data_quality.overall_confidence} />
      </div>

      {!run.data_quality.can_cite_as_municipal && (
        <MethodologyDisclaimer
          disclaimer="Este análisis usa estimaciones regionales calibradas. Las cifras son orientativas, no estadísticas municipales exactas."
          quality_label="Datos estimados"
        />
      )}

      {run.executive_summary && (
        <Card className="border-l-4 border-l-emerald-500">
          <CardHeader title="Síntesis" />
          <p className="text-sm leading-relaxed text-slate-700">{run.executive_summary}</p>
        </Card>
      )}

      {run.critical_needs?.length > 0 && (
        <Card>
          <CardHeader title="Necesidades Críticas" />
          <div className="space-y-3">
            {run.critical_needs.map((need, i) => (
              <NeedCard key={i} need={need} />
            ))}
          </div>
        </Card>
      )}

      {run.opportunities?.length > 0 && (
        <Card>
          <CardHeader title="Oportunidades Estratégicas" />
          <ul className="space-y-2">
            {run.opportunities.map((opportunity, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="mt-0.5 shrink-0 text-emerald-500">→</span>
                <span>{opportunity}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <KPIBoard kpiBoard={run.kpi_board} />

      {run.strategy_section && <StrategySectionPanel strategy={run.strategy_section} />}
    </div>
  );
}

function NeedCard({ need }: { need: CriticalNeed }) {
  const variant =
    need.severity === "alta" ? "error" : need.severity === "media" ? "warning" : "neutral";

  const bg =
    need.severity === "alta"
      ? "border-red-100 bg-red-50"
      : need.severity === "media"
        ? "border-amber-100 bg-amber-50"
        : "border-slate-100 bg-slate-50";

  const description = getNeedDescription(need);
  const affectedPopulationPct = getNeedAffectedPopulationPct(need);

  return (
    <div className={`rounded-lg border p-3 ${bg}`}>
      <div className="mb-1 flex items-start gap-2">
        <Badge variant={variant}>{need.severity}</Badge>
        <p className="text-sm font-semibold leading-snug text-slate-800">{need.title}</p>
      </div>

      {description && (
        <p className="ml-1 text-xs leading-relaxed text-slate-600">{description}</p>
      )}

      {affectedPopulationPct !== null && (
        <p className="ml-1 mt-1 text-xs text-slate-500">
          Afecta al {affectedPopulationPct.toFixed(0)}% de la población
        </p>
      )}
    </div>
  );
}

function KPIBoard({ kpiBoard }: { kpiBoard: Record<string, unknown> }) {
  const kpis = asRecordArray(kpiBoard?.kpis);
  if (!kpis.length) return null;

  return (
    <Card>
      <CardHeader title="KPIs SMART — Metas Verificables" />
      <div className="space-y-2">
        {kpis.slice(0, 4).map((kpi, i) => {
          const base = asNumber(kpi.baseline_value);
          const target = asNumber(kpi.target_value);
          const unit = asString(kpi.baseline_unit);
          const name = asString(kpi.name, "Indicador");

          if (base === null) return null;

          return (
            <div key={i} className="rounded-lg bg-slate-50 px-3 py-2.5">
              <p className="mb-0.5 text-sm font-medium text-slate-800">{name}</p>
              <p className="text-sm font-mono text-emerald-700">
                {base.toLocaleString()} {unit}
                {target !== null && <span className="mx-2 text-slate-400">→</span>}
                {target !== null && (
                  <span className="font-bold">
                    {target.toLocaleString()} {unit}
                  </span>
                )}
              </p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function StrategySectionPanel({ strategy }: { strategy: StrategySection }) {
  const hasContent =
    Boolean(strategy.executive_strategic) ||
    Boolean(strategy.messaging_axes?.length) ||
    Boolean(strategy.candidate_positioning);

  if (!hasContent) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 py-2">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent to-emerald-200" />
        <span className="rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-xs font-bold uppercase tracking-widest text-emerald-600">
          Estrategia de Comunicación{strategy.ai_generated ? " · IA" : ""}
        </span>
        <div className="h-px flex-1 bg-gradient-to-l from-transparent to-emerald-200" />
      </div>

      {strategy.executive_strategic && (
        <Card className="border-emerald-200 bg-gradient-to-r from-emerald-50 to-slate-50">
          <p className="text-sm font-medium leading-relaxed text-slate-800">
            {strategy.executive_strategic}
          </p>
        </Card>
      )}

      {strategy.messaging_axes?.length > 0 && (
        <Card>
          <CardHeader title="Ejes de Mensaje" />
          <div className="space-y-4">
            {strategy.messaging_axes.map((axis, i) => (
              <AxisCard key={i} ax={axis} />
            ))}
          </div>
        </Card>
      )}

      {(strategy.candidate_positioning || strategy.recommended_tone) && (
        <div className="grid gap-4 md:grid-cols-2">
          {strategy.candidate_positioning && (
            <Card>
              <CardHeader title="Posicionamiento" />
              <p className="text-sm leading-relaxed text-slate-700">
                {strategy.candidate_positioning}
              </p>
            </Card>
          )}

          {strategy.recommended_tone && (
            <Card>
              <CardHeader title="Tono y Canales" />
              <p className="mb-2 text-sm text-slate-700">{strategy.recommended_tone}</p>
              {strategy.communication_channels_priority?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {strategy.communication_channels_priority.map((channel, i) => (
                    <span
                      key={i}
                      className="rounded-full border border-emerald-100 bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700"
                    >
                      {channel}
                    </span>
                  ))}
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      {strategy.framing_suggestions?.length > 0 && (
        <Card>
          <CardHeader title="Framings" />
          <div className="space-y-2">
            {strategy.framing_suggestions.map((framing, i) => (
              <p
                key={i}
                className="border-l-2 border-emerald-400 pl-3 text-sm italic text-slate-700"
              >
                {framing}
              </p>
            ))}
          </div>
        </Card>
      )}

      {strategy.risk_flags?.length > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader title="⚠ Riesgos Comunicacionales" />
          <ul className="space-y-1.5">
            {strategy.risk_flags.map((risk, i) => (
              <li key={i} className="text-sm leading-relaxed text-amber-800">
                {risk}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function AxisCard({ ax }: { ax: MessagingAxis }) {
  return (
    <div className="border-l-2 border-emerald-500 py-1 pl-4">
      <p className="mb-0.5 text-sm font-bold text-slate-900">{ax.axis}</p>
      <p className="text-sm text-slate-700">{ax.message}</p>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5">
        {ax.rationale && (
          <p className="text-xs text-slate-500">
            <span className="font-medium">Argumento:</span> {ax.rationale}
          </p>
        )}
        {ax.data_anchor && (
          <p className="text-xs text-emerald-600">
            <span className="font-medium">Dato ancla:</span> {ax.data_anchor}
          </p>
        )}
        {ax.emotional_hook && (
          <p className="text-xs text-violet-600">
            <span className="font-medium">Emoción:</span> {ax.emotional_hook}
          </p>
        )}
      </div>
    </div>
  );
}