"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { TerritorySelector } from "@/components/layout/territory-selector";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useAppStore } from "@/lib/store";
import * as api from "@/lib/api";
import type {
  DurationVerification,
  GenerationPlan,
  SourceProcessingMeta,
  SpeechData,
  SpeechDetail,
} from "@/types";

const CHANNEL_OPTIONS = [
  { value: "mitin", label: "Mitin" },
  { value: "discurso_formal", label: "Discurso Formal" },
  { value: "reunion_vecinal", label: "Reunión Vecinal" },
  { value: "entrevista", label: "Entrevista" },
  { value: "video_redes", label: "Video Redes Sociales" },
  { value: "debate", label: "Debate" },
];

const TONE_OPTIONS = [
  { value: "moderado", label: "Moderado" },
  { value: "combativo y propositivo", label: "Combativo y propositivo" },
  { value: "urgente y solidario", label: "Urgente y solidario" },
  { value: "institucional y cercano", label: "Institucional y cercano" },
  { value: "esperanzador", label: "Esperanzador" },
];

type Tab = "create" | "improve";

function countWords(text: string): number {
  return (text.trim().match(/\S+/g) || []).length;
}

function formatFloat(value?: number | null, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function buildDurationStatus(verification?: DurationVerification) {
  if (!verification) {
    return {
      label: "Sin verificar",
      className: "text-slate-500",
    };
  }

  if (verification.within_tolerance) {
    return {
      label: "Dentro de tolerancia",
      className: "text-emerald-700",
    };
  }

  if (verification.estimated_minutes < verification.target_minutes) {
    return {
      label: "Más corto de lo solicitado",
      className: "text-amber-700",
    };
  }

  return {
    label: "Más largo de lo solicitado",
    className: "text-amber-700",
  };
}

export default function SpeechPage() {
  const {
    selection,
    speechRun,
    setSpeechRun,
    loading,
    setLoading,
    errors,
    setError,
    clearError,
  } = useAppStore();

  const [tab, setTab] = useState<Tab>("create");
  const [form, setForm] = useState({
    goal: "",
    audience: "",
    tone: "moderado",
    channel: "mitin",
    duration: 10,
    priorityTopics: "",
  });
  const [sourceText, setSourceText] = useState("");

  const set = (key: string, value: string | number) =>
    setForm((f) => ({ ...f, [key]: value }));

  const targetWords = form.duration * 130;
  const sourceWords = useMemo(() => countWords(sourceText), [sourceText]);
  const sourceEstimatedMinutes = useMemo(() => sourceWords / 130, [sourceWords]);

  const isValid =
    !!selection.municipalityId &&
    !!form.goal.trim() &&
    !!form.audience.trim() &&
    (tab === "create" || sourceWords >= 40);

  function handleTabChange(t: Tab) {
    setTab(t);
    setSpeechRun(null);
    clearError("speech");
  }

  async function handleRun() {
    if (!isValid) return;
    clearError("speech");
    setLoading("speech", true);
    try {
      const run = await api.speech.run({
        municipality_id: selection.municipalityId,
        speech_goal: form.goal,
        audience: form.audience,
        tone: form.tone,
        channel: form.channel,
        duration_minutes: form.duration,
        source_text: tab === "improve" ? sourceText : undefined,
        priority_topics: form.priorityTopics
          ? form.priorityTopics.split(",").map((t) => t.trim()).filter(Boolean)
          : [],
        force_refresh: true,
      });
      setSpeechRun(run);
    } catch (e: unknown) {
      setError("speech", e instanceof Error ? e.message : "Error generando discurso");
    } finally {
      setLoading("speech", false);
    }
  }

  async function handleExport() {
    if (!speechRun) return;
    setLoading("export", true);
    try {
      const blob = await api.exports.speechBlob(speechRun.id);
      api.downloadBlob(blob, `discurso-${selection.municipalityName}.pdf`);
    } catch (e: unknown) {
      setError("export", e instanceof Error ? e.message : "Error exportando PDF");
    } finally {
      setLoading("export", false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-bold uppercase tracking-widest text-emerald-600">
            VoxPolítica
          </p>
          <h1 className="text-2xl font-bold text-slate-900">Discurso Político</h1>
          <p className="mt-1 text-sm text-slate-500">
            Generación y mejora con control de duración, segmentación y validación del texto base
          </p>
        </div>
        <Link href="/" className="text-sm text-slate-400 hover:text-slate-600">
          ← Inicio
        </Link>
      </div>

      <div className="inline-flex gap-1 rounded-xl border border-slate-200 bg-slate-100 p-1">
        {(["create", "improve"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => handleTabChange(t)}
            className={`rounded-lg px-5 py-2 text-sm font-semibold transition-all ${
              tab === t
                ? "border border-slate-200 bg-white text-emerald-700 shadow-sm"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t === "create" ? "Crear discurso" : "Mejorar discurso"}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader title={tab === "create" ? "Nuevo discurso" : "Discurso a mejorar"} />
        <div className="space-y-4">
          <TerritorySelector disabled={loading.speech} />

          {tab === "improve" && (
            <div className="space-y-2">
              <label className="block text-xs font-medium text-slate-600">
                Discurso original *
              </label>
              <textarea
                value={sourceText}
                onChange={(e) => setSourceText(e.target.value)}
                placeholder="Pega aquí el discurso a mejorar…"
                rows={11}
                maxLength={200000}
                disabled={loading.speech}
                className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                <span>{sourceText.length.toLocaleString()} caracteres</span>
                <span>{sourceWords.toLocaleString()} palabras</span>
                <span>~{sourceEstimatedMinutes.toFixed(1)} min</span>
                {sourceWords >= 40 ? (
                  <span className="font-medium text-emerald-600">texto válido para procesar</span>
                ) : (
                  <span className="font-medium text-amber-600">mínimo 40 palabras</span>
                )}
              </div>
            </div>
          )}

          <Input
            label={tab === "create" ? "Objetivo del discurso *" : "Objetivo de la mejora *"}
            value={form.goal}
            onChange={(e) => set("goal", e.target.value)}
            placeholder={
              tab === "create"
                ? "Ej: Movilizar apoyo en zona industrial"
                : "Ej: Fortalecer el anclaje territorial y las propuestas concretas"
            }
            disabled={loading.speech}
          />

          <Input
            label="Audiencia *"
            value={form.audience}
            onChange={(e) => set("audience", e.target.value)}
            placeholder="Ej: Trabajadoras y trabajadores textiles"
            disabled={loading.speech}
          />

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Select
              label="Tono"
              value={form.tone}
              onChange={(v) => set("tone", v)}
              options={TONE_OPTIONS}
              disabled={loading.speech}
            />
            <Select
              label="Canal"
              value={form.channel}
              onChange={(v) => set("channel", v)}
              options={CHANNEL_OPTIONS}
              disabled={loading.speech}
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              Duración: <strong className="text-slate-900">{form.duration} min</strong>{" "}
              <span className="text-slate-400">(~{targetWords.toLocaleString()} palabras objetivo)</span>
            </label>
            <input
              type="range"
              min={1}
              max={120}
              value={form.duration}
              onChange={(e) => set("duration", Number(e.target.value))}
              className="w-full accent-emerald-600"
              disabled={loading.speech}
            />
            <div className="mt-0.5 flex justify-between text-xs text-slate-400">
              <span>1 min</span>
              <span>60 min</span>
              <span>120 min</span>
            </div>
          </div>

          <Input
            label="Temas prioritarios (separados por comas)"
            value={form.priorityTopics}
            onChange={(e) => set("priorityTopics", e.target.value)}
            placeholder="agua, empleo, seguridad"
            disabled={loading.speech}
          />

          <Button
            onClick={handleRun}
            loading={loading.speech}
            disabled={!isValid}
            className="w-full"
          >
            {tab === "create" ? "Generar discurso" : "Mejorar discurso"}
          </Button>
        </div>
      </Card>

      {errors.speech && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errors.speech}
        </div>
      )}

      {speechRun && (
        <SpeechResult
          run={speechRun}
          onExport={handleExport}
          exportLoading={loading.export}
        />
      )}
    </main>
  );
}

function SpeechResult({
  run,
  onExport,
  exportLoading,
}: {
  run: SpeechDetail;
  onExport: () => void;
  exportLoading: boolean;
}) {
  const d = run.speech_data as SpeechData;
  const verification = d.duration_verification;
  const sourceProcessing = d.source_processing as SourceProcessingMeta | undefined;
  const generationPlan = d.generation_plan as GenerationPlan | undefined;
  const isImprovement = run.speech_type !== "creation";
  const durationStatus = buildDurationStatus(verification);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
        <div className="mb-2 flex items-start justify-between gap-4">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <h2 className="font-bold text-slate-900">{d.title || "Discurso"}</h2>
              {isImprovement && (
                <span className="rounded-full border border-emerald-200 bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                  Versión mejorada
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500">
              {run.municipality_id} · {new Date(run.created_at).toLocaleString("es-MX")}
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={onExport} loading={exportLoading}>
            ↓ PDF
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="font-medium text-slate-700">
            {run.actual_word_count.toLocaleString()} palabras
          </span>
          <span className="text-slate-600">
            objetivo: {run.target_word_count.toLocaleString()}
          </span>
          {verification && (
            <span className={durationStatus.className}>
              ~{verification.estimated_minutes.toFixed(1)} min
            </span>
          )}
          <span className={durationStatus.className}>{durationStatus.label}</span>
          {run.retry_count > 0 && <Badge variant="warning">{run.retry_count} reintento(s)</Badge>}
          {!run.validation.passed && (
            <Badge variant="error">{run.validation.blocking_count} bloqueo(s)</Badge>
          )}
        </div>
      </div>

      {verification && (
        <Card>
          <CardHeader title="Verificación de duración" />
          <div className="grid grid-cols-1 gap-3 text-sm text-slate-700 md:grid-cols-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Objetivo</p>
              <p className="font-semibold">{verification.target_minutes} min</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Estimado</p>
              <p className="font-semibold">{verification.estimated_minutes.toFixed(1)} min</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Rango aceptable</p>
              <p className="font-semibold">
                {verification.lower_bound_minutes.toFixed(1)} – {verification.upper_bound_minutes.toFixed(1)} min
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Estado</p>
              <p className={`font-semibold ${durationStatus.className}`}>
                {durationStatus.label}
              </p>
            </div>
          </div>
        </Card>
      )}

      {generationPlan && (
        <Card>
          <CardHeader title="Plan de generación" />
          <div className="grid grid-cols-1 gap-3 text-sm text-slate-700 md:grid-cols-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Palabras objetivo</p>
              <p className="font-semibold">{generationPlan.target_words.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Mínimo aceptable</p>
              <p className="font-semibold">{generationPlan.minimum_words.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Secciones del cuerpo</p>
              <p className="font-semibold">{generationPlan.body_sections}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Palabras por sección</p>
              <p className="font-semibold">{generationPlan.body_section_words.toLocaleString()}</p>
            </div>
          </div>
          {generationPlan.batches?.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-xs uppercase tracking-wide text-slate-400">Lotes de segmentación</p>
              <div className="flex flex-wrap gap-2">
                {generationPlan.batches.map((batch, idx) => (
                  <span
                    key={`${idx}-${batch.join("-")}`}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600"
                  >
                    Lote {idx + 1}: {batch.join(", ")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {isImprovement && sourceProcessing && (
        <Card>
          <CardHeader title="Procesamiento del texto fuente" />
          <div className="grid grid-cols-1 gap-3 text-sm text-slate-700 md:grid-cols-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Palabras</p>
              <p className="font-semibold">{sourceProcessing.word_count.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Párrafos</p>
              <p className="font-semibold">{sourceProcessing.paragraph_count}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Tramos</p>
              <p className="font-semibold">{sourceProcessing.segments_count}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Tiempo estimado</p>
              <p className="font-semibold">{formatFloat(sourceProcessing.estimated_minutes)} min</p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 text-sm text-slate-700 md:grid-cols-2">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Ratio alfabético</p>
              <p className="font-semibold">{formatFloat(sourceProcessing.alpha_ratio, 3)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Palabras útiles para prompt</p>
              <p className="font-semibold">
                {sourceProcessing.prompt_ready_word_count.toLocaleString()}
              </p>
            </div>
          </div>

          {sourceProcessing.segment_previews?.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs uppercase tracking-wide text-slate-400">Vista previa de tramos</p>
              <div className="space-y-2">
                {sourceProcessing.segment_previews.map((preview, idx) => (
                  <div
                    key={`${idx}-${preview.slice(0, 20)}`}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600"
                  >
                    <span className="mr-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Tramo {idx + 1}
                    </span>
                    {preview}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {isImprovement && d.improvements_made && d.improvements_made.length > 0 && (
        <Card className="border-emerald-200 bg-emerald-50">
          <CardHeader title="Mejoras aplicadas" />
          <ul className="space-y-1">
            {d.improvements_made.map((imp, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-emerald-800">
                <span className="shrink-0 font-bold">✓</span>
                <span>{imp}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {d.adaptation_notes && d.adaptation_notes.length > 0 && (
        <Card>
          <CardHeader title="Notas de adaptación" />
          <ul className="space-y-1">
            {d.adaptation_notes.map((note, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="shrink-0 font-bold text-slate-400">•</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {run.validation.issues && run.validation.issues.length > 0 && (
        <Card>
          <CardHeader title="Validación del resultado" />
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge variant={run.validation.passed ? "success" : "warning"}>
                score {run.validation.score}
              </Badge>
              <Badge variant="neutral">
                checks {run.validation.checks_run}
              </Badge>
              <Badge variant="warning">
                warnings {run.validation.warning_count}
              </Badge>
              <Badge variant={run.validation.blocking_count > 0 ? "error" : "success"}>
                bloqueos {run.validation.blocking_count}
              </Badge>
            </div>
            <div className="space-y-2">
              {run.validation.issues.map((issue, idx) => (
                <div
                  key={`${issue.code}-${idx}`}
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    issue.severity === "blocking"
                      ? "border-red-200 bg-red-50 text-red-700"
                      : "border-amber-200 bg-amber-50 text-amber-700"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{issue.code}</span>
                    {issue.field && (
                      <span className="text-xs uppercase tracking-wide opacity-70">
                        {issue.field}
                      </span>
                    )}
                  </div>
                  <p className="mt-1">{issue.description}</p>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {d.opening && (
        <Card>
          <p className="mb-3 text-xs font-bold uppercase tracking-widest text-emerald-600">
            Apertura
          </p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
            {d.opening}
          </p>
        </Card>
      )}

      {d.body_sections?.map((sec, i) => (
        <Card key={i}>
          <p className="mb-2 text-xs font-bold uppercase tracking-widest text-slate-500">
            {sec.title}
          </p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
            {sec.content}
          </p>
          {sec.persuasion_technique && (
            <p className="mt-2 text-xs italic text-slate-400">
              Técnica: {sec.persuasion_technique}
            </p>
          )}
        </Card>
      ))}

      {d.closing && (
        <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50 to-slate-50">
          <p className="mb-3 text-xs font-bold uppercase tracking-widest text-emerald-600">
            Cierre
          </p>
          <p className="whitespace-pre-wrap text-sm font-medium leading-relaxed text-slate-800">
            {d.closing}
          </p>
        </Card>
      )}

      {d.local_references && d.local_references.length > 0 && (
        <p className="text-center text-xs text-slate-400">
          Referencias locales: {d.local_references.join(" · ")}
        </p>
      )}
    </div>
  );
}