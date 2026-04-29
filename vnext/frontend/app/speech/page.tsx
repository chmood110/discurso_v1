"use client";

/* ============================================================================
 * /speech — Discurso Político
 *
 * LÓGICA DE NEGOCIO PRESERVADA:
 *   · useAppStore (selection, speechRun, loading, errors)
 *   · api.speech.run con el payload completo (municipality_id, speech_goal,
 *     audience, tone, channel, duration_minutes, source_text si tab=improve,
 *     priority_topics como string[], force_refresh)
 *   · api.exports.speechBlob + downloadBlob
 *   · Validación: mínimo 40 palabras en source_text para improve, audience+goal
 *     siempre requeridos.
 *   · Renderiza TODOS los paneles del backend:
 *       - duration_verification (target/estimated/range/status)
 *       - generation_plan (target_words, minimum, body_sections, batches)
 *       - source_processing (paragraph_count, segments, alpha_ratio, segment_previews)
 *       - validation.issues
 *       - improvements_made / adaptation_notes
 *       - body_sections[] (cada uno con title + persuasion_technique opcional)
 *
 *   Cambia: la skin (paper layout para discurso, navy para forma/loader/paneles).
 * ========================================================================== */

import { useMemo, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  FileDown,
  Home,
  MapPin,
  PenTool,
  PlusCircle,
  Sparkles,
  Type,
  Users,
} from "lucide-react";

import { AuroraBackground } from "@/components/ui/aurora-background";
import { MasterLoader } from "@/components/ui/master-loader";
import { MinimalInput } from "@/components/ui/minimal-input";
import { MinimalSelect } from "@/components/ui/minimal-select";
import { MinimalTextarea } from "@/components/ui/minimal-textarea";
import { PaperLayout } from "@/components/ui/paper-layout";
import { SectionLabel } from "@/components/ui/section-label";
import { TerritorySelector } from "@/components/layout/territory-selector";
import { NavBar, type NavTab } from "@/components/layout/nav-bar";
import { ValidationReportPanel } from "@/components/data-quality/validation-report";

import { useAppStore } from "@/lib/store";
import * as api from "@/lib/api";
import { cn } from "@/lib/cn";
import type {
  DurationVerification,
  GenerationPlan,
  SourceProcessingMeta,
  SpeechData,
  SpeechDetail,
} from "@/types";

// ---------- option tables (canonical values match backend) ------------------

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

const TABS: NavTab<Tab>[] = [
  { value: "create", label: "Crear", icon: <PlusCircle className="h-3.5 w-3.5" /> },
  { value: "improve", label: "Mejorar", icon: <PenTool className="h-3.5 w-3.5" /> },
];

// ---------- helpers (preserved from v1) -------------------------------------

function countWords(text: string): number {
  return (text.trim().match(/\S+/g) || []).length;
}

function formatFloat(value?: number | null, digits = 1): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function buildDurationStatus(verification?: DurationVerification) {
  if (!verification) {
    return { label: "Sin verificar", className: "text-slate-500" };
  }
  if (verification.within_tolerance) {
    return { label: "Dentro de tolerancia", className: "text-sky-300" };
  }
  if (verification.estimated_minutes < verification.target_minutes) {
    return { label: "Más corto de lo solicitado", className: "text-amber-300" };
  }
  return { label: "Más largo de lo solicitado", className: "text-amber-300" };
}

// =============================================================================

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

  const set = <K extends keyof typeof form>(key: K, value: typeof form[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const targetWords = form.duration * 130;
  const sourceWords = useMemo(() => countWords(sourceText), [sourceText]);
  const sourceEstimatedMinutes = useMemo(
    () => sourceWords / 130,
    [sourceWords]
  );

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
          ? form.priorityTopics
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean)
          : [],
        force_refresh: true,
      });
      setSpeechRun(run);
    } catch (e: unknown) {
      setError(
        "speech",
        e instanceof Error ? e.message : "Error generando discurso"
      );
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
      setError(
        "export",
        e instanceof Error ? e.message : "Error exportando PDF"
      );
    } finally {
      setLoading("export", false);
    }
  }

  const isLoading = loading.speech;
  const hasResult = !!speechRun && !isLoading;

  return (
    <AuroraBackground variant="soft">
      <NavBar
        fixed
        tabs={TABS}
        activeTab={tab}
        onTabChange={(t: Tab) => handleTabChange(t)}
      />

      <main className="mx-auto max-w-4xl px-6 pb-32 pt-32">
        {/* ---------- LOADING ---------- */}
        {isLoading && (
          <div className="flex min-h-[50vh] flex-col items-center justify-center">
            <MasterLoader
              size="md"
              showSpark
              headline="Sintetizando mensaje"
              subline={`Cruzando contexto de ${
                selection.municipalityName || "Tlaxcala"
              } con tono ${form.tone}`}
            />
          </div>
        )}

        {/* ---------- FORM ---------- */}
        {!isLoading && !hasResult && (
          <FormView
            tab={tab}
            form={form}
            set={set}
            sourceText={sourceText}
            setSourceText={setSourceText}
            sourceWords={sourceWords}
            sourceEstimatedMinutes={sourceEstimatedMinutes}
            targetWords={targetWords}
            isValid={isValid}
            error={errors.speech}
            onSubmit={handleRun}
          />
        )}

        {/* ---------- RESULT ---------- */}
        {hasResult && speechRun && (
          <ResultView
            run={speechRun}
            tab={tab}
            municipalityName={selection.municipalityName}
            form={form}
            onBack={() => {
              setSpeechRun(null);
              clearError("speech");
            }}
            onReset={() => {
              setSpeechRun(null);
              setForm({
                goal: "",
                audience: "",
                tone: "moderado",
                channel: "mitin",
                duration: 10,
                priorityTopics: "",
              });
              setSourceText("");
              clearError("speech");
            }}
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
  tab: Tab;
  form: {
    goal: string;
    audience: string;
    tone: string;
    channel: string;
    duration: number;
    priorityTopics: string;
  };
  set: <K extends keyof FormViewProps["form"]>(
    key: K,
    value: FormViewProps["form"][K]
  ) => void;
  sourceText: string;
  setSourceText: (v: string) => void;
  sourceWords: number;
  sourceEstimatedMinutes: number;
  targetWords: number;
  isValid: boolean;
  error?: string;
  onSubmit: () => void;
}

function FormView({
  tab,
  form,
  set,
  sourceText,
  setSourceText,
  sourceWords,
  sourceEstimatedMinutes,
  targetWords,
  isValid,
  error,
  onSubmit,
}: FormViewProps) {
  const [isDragging, setIsDragging] = useState(false);

  return (
    <div className="animate-slide-in-bottom space-y-20">
      <header>
        <h1 className="mb-4 font-display text-5xl font-extrabold tracking-tighter text-white md:text-6xl">
          {tab === "create" ? "Nuevo discurso" : "Evolución de texto"}
        </h1>
        <p className="text-lg font-light leading-relaxed text-slate-400">
          {tab === "create"
            ? "Configura la narrativa maestra para tu intervención territorial."
            : "Transforma tu borrador en un mensaje político de alto impacto."}
        </p>
      </header>

      <div className="space-y-16">
        {/* 01 — Demarcación */}
        <section className="space-y-6">
          <SectionLabel
            number="01"
            tone="accent"
            icon={<MapPin className="h-3.5 w-3.5" />}
          >
            Define el escenario
          </SectionLabel>
          <TerritorySelector size="md" />
        </section>

        {/* 02 — Source text (only when improving) */}
        {tab === "improve" && (
          <section className="animate-slide-in-bottom space-y-6">
            <SectionLabel
              number="02"
              tone="accent"
              icon={<Type className="h-3.5 w-3.5" />}
            >
              Tu borrador actual
            </SectionLabel>
            <MinimalTextarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="Pega aquí el texto que deseas que la IA perfeccione…"
              className="min-h-[180px]"
              maxLength={200000}
            />
            <div className="flex flex-wrap items-center gap-4 text-[10px] font-bold uppercase tracking-eyebrow_xs">
              <span className="text-slate-600">
                {sourceText.length.toLocaleString()} caracteres
              </span>
              <span className="text-slate-600">
                {sourceWords.toLocaleString()} palabras
              </span>
              <span className="text-slate-600">
                ~{sourceEstimatedMinutes.toFixed(1)} min
              </span>
              <span
                className={cn(
                  sourceWords >= 40 ? "text-sky-400" : "text-amber-400"
                )}
              >
                {sourceWords >= 40
                  ? "· texto válido para procesar"
                  : "· mínimo 40 palabras"}
              </span>
            </div>
          </section>
        )}

        {/* 03/04 — Intent (goal + audience) */}
        <section className="grid gap-16 md:grid-cols-2">
          <div className="space-y-6">
            <SectionLabel
              tone="muted"
              icon={<Sparkles className="h-3.5 w-3.5" />}
            >
              El alma del mensaje
            </SectionLabel>
            <MinimalInput
              value={form.goal}
              onChange={(e) => set("goal", e.target.value)}
              placeholder={
                tab === "create"
                  ? "¿Cuál es el objetivo central?"
                  : "¿Qué quieres mejorar?"
              }
            />
          </div>
          <div className="space-y-6">
            <SectionLabel
              tone="muted"
              icon={<Users className="h-3.5 w-3.5" />}
            >
              ¿A quién le hablas?
            </SectionLabel>
            <MinimalInput
              value={form.audience}
              onChange={(e) => set("audience", e.target.value)}
              placeholder="Define tu audiencia objetivo"
            />
          </div>
        </section>

        {/* 05 — Parameters */}
        <section className="grid gap-12 pt-4 md:grid-cols-3">
          <div className="space-y-4">
            <span className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-600">
              Tono sugerido
            </span>
            <MinimalSelect
              value={form.tone}
              onChange={(v) => set("tone", v)}
              options={TONE_OPTIONS}
            />
          </div>
          <div className="space-y-4">
            <span className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-600">
              Canal de entrega
            </span>
            <MinimalSelect
              value={form.channel}
              onChange={(v) => set("channel", v)}
              options={CHANNEL_OPTIONS}
            />
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-sky-400">
                Duración
              </span>
              <span className="font-display text-lg font-bold text-white">
                {form.duration} min
              </span>
            </div>
            <div className="px-1 pt-4">
              <input
                type="range"
                min={1}
                max={120}
                value={form.duration}
                onMouseDown={() => setIsDragging(true)}
                onMouseUp={() => setIsDragging(false)}
                onChange={(e) => set("duration", Number(e.target.value))}
                className={cn("w-full", isDragging && "slider-thumb-active")}
              />
              <div className="mt-2 flex justify-between text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
                <span>1 min</span>
                <span>60</span>
                <span>120</span>
              </div>
            </div>
            <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
              ~{targetWords.toLocaleString()} palabras objetivo
            </p>
          </div>
        </section>

        {/* 06 — Priority topics */}
        <section className="space-y-6">
          <SectionLabel tone="muted">Temas prioritarios (opcional)</SectionLabel>
          <MinimalInput
            value={form.priorityTopics}
            onChange={(e) => set("priorityTopics", e.target.value)}
            placeholder="agua, empleo, seguridad"
          />
          <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
            Separa con comas. Se enviarán como priority_topics al motor.
          </p>
        </section>

        {/* Error */}
        {error && (
          <div className="border-l-2 border-red-400/40 bg-red-500/5 px-6 py-4">
            <p className="text-sm font-light text-red-200">{error}</p>
          </div>
        )}

        {/* Submit */}
        <div className="flex items-center justify-between border-t border-white/5 pt-12">
          <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
            * Información validada por el motor IA territorial
          </p>
          <button
            onClick={onSubmit}
            disabled={!isValid}
            className="flex items-center gap-4 rounded-full bg-white px-10 py-4 font-bold text-black transition-all hover:scale-105 hover:bg-sky-400 active:scale-95 disabled:scale-100 disabled:opacity-20 disabled:hover:bg-white"
          >
            <span>{tab === "create" ? "Generar discurso" : "Aplicar mejoras"}</span>
            <ArrowRight className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// RESULT
// =============================================================================

interface ResultViewProps {
  run: SpeechDetail;
  tab: Tab;
  municipalityName: string;
  form: FormViewProps["form"];
  onBack: () => void;
  onReset: () => void;
  onExport: () => void;
  exportLoading: boolean;
}

function ResultView({
  run,
  tab,
  municipalityName,
  form,
  onBack,
  onReset,
  onExport,
  exportLoading,
}: ResultViewProps) {
  const d = run.speech_data as SpeechData;
  const verification = d.duration_verification;
  const sourceProcessing = d.source_processing as
    | SourceProcessingMeta
    | undefined;
  const generationPlan = d.generation_plan as GenerationPlan | undefined;
  const isImprovement = run.speech_type !== "creation";
  const durationStatus = buildDurationStatus(verification);

  const tone =
    TONE_OPTIONS.find((t) => t.value === form.tone)?.label ?? form.tone;
  const channel =
    CHANNEL_OPTIONS.find((c) => c.value === form.channel)?.label ?? form.channel;

  return (
    <div className="animate-fade-in-slow space-y-12">
      {/* Top toolbar */}
      <div className="mb-2 flex items-center justify-between">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-500 transition-colors hover:text-white"
        >
          <Home className="h-4 w-4" /> Volver al formulario
        </button>
        <div className="flex gap-3">
          <button
            onClick={onExport}
            disabled={exportLoading}
            className="flex items-center gap-2 rounded-full bg-white/5 px-6 py-3 text-[10px] font-bold uppercase tracking-eyebrow_xs text-white transition-all hover:bg-white/10 disabled:opacity-30"
          >
            <FileDown className="h-4 w-4" />
            {exportLoading ? "Exportando…" : "Exportar PDF"}
          </button>
        </div>
      </div>

      {/* THE PAPER */}
      <PaperLayout>
        <header className="mb-16 border-b border-slate-100 pb-10">
          <div className="mb-8 flex items-start justify-between gap-6">
            <div className="space-y-1">
              <p className="text-[10px] font-black uppercase tracking-eyebrow_xs text-sky-600">
                Guion de oratoria · master
              </p>
              <h1 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
                {d.title ||
                  (tab === "create"
                    ? `Propuesta para ${municipalityName}`
                    : `Versión evolucionada · ${municipalityName}`)}
              </h1>
              {isImprovement && (
                <span className="mt-2 inline-block rounded-full border border-sky-300 bg-sky-50 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-eyebrow_xs text-sky-700">
                  Versión mejorada
                </span>
              )}
            </div>
            <div className="text-right text-slate-700">
              <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-400">
                Fecha
              </p>
              <p className="text-sm font-bold">
                {new Date(run.created_at).toLocaleDateString("es-MX")}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            <PaperMeta label="Duración" value={`${run.target_duration_minutes} min`} />
            <PaperMeta label="Tono" value={tone} />
            <PaperMeta label="Canal" value={channel} />
            <PaperMeta
              label="Palabras"
              value={`${run.actual_word_count.toLocaleString()} / ${run.target_word_count.toLocaleString()}`}
            />
          </div>
        </header>

        <div className="mx-auto max-w-2xl space-y-12">
          {/* Opening */}
          {d.opening && (
            <PaperBlock label="Apertura" tone="accent">
              <p className="font-display text-2xl font-medium italic leading-tight text-slate-800">
                {d.opening}
              </p>
            </PaperBlock>
          )}

          {/* Body sections (preserved as array — backend may emit many) */}
          {d.body_sections?.map((sec, i) => (
            <PaperBlock
              key={i}
              label={sec.title || `Cuerpo ${i + 1}`}
              tone="muted"
            >
              <p className="whitespace-pre-wrap text-base font-light leading-relaxed text-slate-700">
                {sec.content}
              </p>
              {sec.persuasion_technique && (
                <p className="mt-3 text-xs italic text-slate-400">
                  Técnica · {sec.persuasion_technique}
                </p>
              )}
            </PaperBlock>
          ))}

          {/* Closing */}
          {d.closing && (
            <PaperBlock label="Cierre directo" tone="accent" topBorder>
              <p className="font-display text-2xl font-extrabold leading-tight text-slate-900">
                {d.closing}
              </p>
            </PaperBlock>
          )}

          {/* Local references — small footer style */}
          {d.local_references && d.local_references.length > 0 && (
            <p className="pt-6 text-center text-xs italic text-slate-400">
              Referencias locales · {d.local_references.join(" · ")}
            </p>
          )}
        </div>

        <footer className="mt-20 flex items-center justify-between border-t border-slate-100 pt-10 text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-300">
          <span>VoxPolítica Intelligence v4.2</span>
          <span>Documento confidencial</span>
          <span>Copia orador 01</span>
        </footer>
      </PaperLayout>

      {/* ===== Backend insight panels (still on navy) ===== */}

      {verification && (
        <NavyPanel label="Verificación de duración" tone="muted">
          <div className="grid gap-6 md:grid-cols-4">
            <Stat label="Objetivo" value={`${verification.target_minutes} min`} />
            <Stat
              label="Estimado"
              value={`${verification.estimated_minutes.toFixed(1)} min`}
              tone={durationStatus.className}
            />
            <Stat
              label="Rango aceptable"
              value={`${verification.lower_bound_minutes.toFixed(1)}–${verification.upper_bound_minutes.toFixed(1)} min`}
            />
            <Stat
              label="Estado"
              value={durationStatus.label}
              tone={durationStatus.className}
            />
          </div>
        </NavyPanel>
      )}

      {generationPlan && (
        <NavyPanel label="Plan de generación" tone="muted">
          <div className="grid gap-6 md:grid-cols-4">
            <Stat
              label="Palabras objetivo"
              value={generationPlan.target_words.toLocaleString()}
            />
            <Stat
              label="Mínimo aceptable"
              value={generationPlan.minimum_words.toLocaleString()}
            />
            <Stat
              label="Secciones del cuerpo"
              value={String(generationPlan.body_sections)}
            />
            <Stat
              label="Palabras por sección"
              value={generationPlan.body_section_words.toLocaleString()}
            />
          </div>

          {generationPlan.batches?.length > 0 && (
            <div className="mt-8 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
                Lotes de segmentación
              </p>
              <div className="flex flex-wrap gap-2">
                {generationPlan.batches.map((batch, idx) => (
                  <span
                    key={`${idx}-${batch.join("-")}`}
                    className="rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1 text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-400"
                  >
                    Lote {idx + 1} · {batch.join(", ")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </NavyPanel>
      )}

      {isImprovement && sourceProcessing && (
        <NavyPanel label="Procesamiento del texto fuente" tone="muted">
          <div className="grid gap-6 md:grid-cols-4">
            <Stat
              label="Palabras"
              value={sourceProcessing.word_count.toLocaleString()}
            />
            <Stat
              label="Párrafos"
              value={String(sourceProcessing.paragraph_count)}
            />
            <Stat
              label="Tramos"
              value={String(sourceProcessing.segments_count)}
            />
            <Stat
              label="Tiempo estimado"
              value={`${formatFloat(sourceProcessing.estimated_minutes)} min`}
            />
          </div>

          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <Stat
              label="Ratio alfabético"
              value={formatFloat(sourceProcessing.alpha_ratio, 3)}
            />
            <Stat
              label="Palabras útiles"
              value={sourceProcessing.prompt_ready_word_count.toLocaleString()}
            />
          </div>

          {sourceProcessing.segment_previews?.length > 0 && (
            <div className="mt-8 space-y-3">
              <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
                Vista previa de tramos
              </p>
              <div className="space-y-2">
                {sourceProcessing.segment_previews.map((preview, idx) => (
                  <div
                    key={`${idx}-${preview.slice(0, 20)}`}
                    className="border-l-2 border-slate-800 bg-slate-950/40 px-4 py-3 text-sm font-light text-slate-400"
                  >
                    <span className="mr-2 text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-600">
                      Tramo {idx + 1}
                    </span>
                    {preview}
                  </div>
                ))}
              </div>
            </div>
          )}
        </NavyPanel>
      )}

      {isImprovement && d.improvements_made && d.improvements_made.length > 0 && (
        <NavyPanel label="Mejoras aplicadas" tone="accent">
          <ul className="space-y-2">
            {d.improvements_made.map((imp, i) => (
              <li
                key={i}
                className="flex items-start gap-3 text-sm font-light leading-relaxed text-slate-300"
              >
                <span className="text-sky-400">✓</span>
                <span>{imp}</span>
              </li>
            ))}
          </ul>
        </NavyPanel>
      )}

      {d.adaptation_notes && d.adaptation_notes.length > 0 && (
        <NavyPanel label="Notas de adaptación" tone="muted">
          <ul className="space-y-2">
            {d.adaptation_notes.map((note, i) => (
              <li
                key={i}
                className="flex items-start gap-3 text-sm font-light leading-relaxed text-slate-300"
              >
                <span className="text-slate-600">·</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </NavyPanel>
      )}

      {run.validation?.issues?.length > 0 && (
        <NavyPanel label="Validación del resultado" tone="muted">
          <ValidationReportPanel report={run.validation} />
        </NavyPanel>
      )}

      {/* Reset CTA */}
      <div className="flex justify-center pt-8">
        <button
          onClick={onReset}
          className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-eyebrow text-slate-600 transition-colors hover:text-sky-400"
        >
          Reiniciar proceso creativo <ArrowUpRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

function PaperMeta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="mb-1 text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-400">
        {label}
      </p>
      <p className="text-sm font-semibold text-slate-700">{value}</p>
    </div>
  );
}

function PaperBlock({
  children,
  label,
  tone,
  topBorder,
}: {
  children: React.ReactNode;
  label: string;
  tone: "accent" | "muted";
  topBorder?: boolean;
}) {
  const labelColor = tone === "accent" ? "text-sky-600" : "text-slate-400";
  return (
    <div
      className={cn(
        "space-y-4",
        topBorder && "border-t border-slate-100 pt-12"
      )}
    >
      <p
        className={cn(
          "text-[10px] font-black uppercase tracking-eyebrow_xs",
          labelColor
        )}
      >
        {label}
      </p>
      {children}
    </div>
  );
}

function NavyPanel({
  children,
  label,
  tone,
}: {
  children: React.ReactNode;
  label: string;
  tone: "accent" | "muted";
}) {
  return (
    <section className="space-y-6 border-t border-slate-900 pt-10">
      <SectionLabel tone={tone}>{label}</SectionLabel>
      {children}
    </section>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
        {label}
      </p>
      <p
        className={cn(
          "font-display text-xl font-bold tracking-tight",
          tone || "text-white"
        )}
      >
        {value}
      </p>
    </div>
  );
}
