# Migración v1 → v2

Este documento es para alguien que conozca la v1 y quiera entender exactamente qué se preservó, qué cambió y dónde mirar si una integración rompe.

## Regla maestra

> **Toda la lógica de negocio se preservó al 100%.** Los cambios son exclusivamente la capa visual. Si el backend funcionaba antes, funciona ahora.

## Archivos sin cambios funcionales

Estos archivos se copiaron tal cual desde la v1 — diff = 0:

| Archivo | Por qué |
| --- | --- |
| `lib/api.ts` | Cliente HTTP del backend. Endpoints, payloads y headers idénticos. |
| `lib/store.ts` | Store de Zustand. Misma estructura, mismas keys, misma persistencia (`vox-store-v2` en `localStorage`). |
| `types/index.ts` | Tipos compartidos con el backend. Si el backend cambia un campo, este archivo cambia — no la UI. |
| `hooks/use-municipalities.ts` | Hooks de fetch de municipios y vecindades. |
| `next.config.js` | Rewrite del backend. |
| `tsconfig.json` | Configuración de TypeScript estricto. |
| `postcss.config.js` | Sin cambios. |

## Contratos de backend preservados

### `api.analysis.run(payload)`

Llamado desde `app/analysis/page.tsx`. Payload:

```ts
{
  municipality_id: string,        // del store
  objective?: string,              // del input "Objetivo crítico"
  force_refresh?: boolean          // false en first-fetch, true en regeneración manual
}
```

Comportamiento idéntico a v1:
- Primer fetch automático cuando `selection.municipalityId` cambia (con `force_refresh: false`).
- Botón "Regenerar" en el header del resultado dispara `force_refresh: true`.
- Errores se asignan a `errors.analysis` del store.
- Loading flag: `loading.analysis`.

### `api.speech.run(payload)`

Llamado desde `app/speech/page.tsx`. Payload:

```ts
{
  municipality_id: string,
  speech_goal: string,             // del input "El alma del mensaje"
  audience: string,                // del input "¿A quién le hablas?"
  tone: string,                    // valor canónico del select (no el label)
  channel: string,                 // valor canónico del select (no el label)
  duration_minutes: number,        // del slider, 1–120
  source_text?: string,            // SOLO cuando tab === "improve"
  priority_topics: string[],       // del input "agua, empleo, seguridad" parseado por coma
  force_refresh: true              // siempre true (cada generación es nueva)
}
```

**Validación preservada**:
- `municipalityId` requerido.
- `speech_goal` y `audience` requeridos (`.trim()`).
- En tab `improve`, `source_text` debe tener ≥ 40 palabras (`countWords(text) >= 40`).
- Solo entonces se habilita el botón "Generar / Aplicar mejoras".

Los valores de `tone` y `channel` enviados al backend son los que estaban en v1:

```
Tones:    "moderado" | "combativo y propositivo" | "urgente y solidario"
        | "institucional y cercano" | "esperanzador"

Canales:  "mitin" | "discurso_formal" | "reunion_vecinal"
        | "entrevista" | "video_redes" | "debate"
```

### Datos backend renderizados en el resultado del Speech

Todos los paneles que reportaba la v1 se siguen renderizando. Lista exhaustiva:

| Campo del backend | Se renderiza en |
| --- | --- |
| `speech_data.title` | Headline del paper (con fallback al municipio) |
| `speech_data.opening` | Bloque "Apertura" |
| `speech_data.body_sections[]` | **Cada uno** como `<PaperBlock>` propio (no se colapsa) |
| `speech_data.body_sections[].persuasion_technique` | Línea italic abajo del bloque |
| `speech_data.closing` | Bloque "Cierre directo" |
| `speech_data.local_references[]` | Footer del paper |
| `speech_data.duration_verification` | Panel "Verificación de duración" |
| `speech_data.generation_plan` | Panel "Plan de generación" + chips de batches |
| `speech_data.source_processing` | Panel "Procesamiento del texto fuente" + segment_previews |
| `speech_data.improvements_made[]` | Panel "Mejoras aplicadas" (solo en mejora) |
| `speech_data.adaptation_notes[]` | Panel "Notas de adaptación" |
| `validation.issues[]` | `<ValidationReportPanel>` |
| `validation.score`, `passed`, `blocking_count` | Header del ValidationReportPanel |
| `actual_word_count`, `target_word_count` | Stat "Palabras" en el paper |
| `target_duration_minutes` | Stat "Duración" en el paper |
| `speech_type` (`creation` vs `adaptation`/`improvement`) | Determina si se muestran improvements/source_processing |

### Datos backend renderizados en el resultado del Analysis

| Campo | Se renderiza en |
| --- | --- |
| `executive_summary` | Sección "Análisis de situación" (font-display 3xl) |
| `critical_needs[]` | Sección "Necesidades críticas" (con `severity` colorizada y `affected_population_pct`) |
| `opportunities[]` | Sección "Oportunidades estratégicas" |
| `kpi_board.kpis[]` | Sidebar "Métricas clave" (top 4 con baseline_value + target_value) |
| `strategy_section.executive_strategic` | Headline de la sección de estrategia |
| `strategy_section.messaging_axes[]` | Grid de `<AxisCard>` |
| `strategy_section.candidate_positioning` | Bloque "Posicionamiento" |
| `strategy_section.recommended_tone` | Bloque "Tono recomendado" |
| `strategy_section.communication_channels_priority[]` | Chips sky en el bloque de tono |
| `strategy_section.framing_suggestions[]` | Bloque "Framings" (italic con borde sky) |
| `strategy_section.risk_flags[]` | Bloque amber "⚠ Riesgos comunicacionales" |
| `data_quality.can_cite_as_municipal` | Decide entre `QualityBadge` "official_municipal" vs "calibrated_estimate" |
| `data_quality.overall_confidence` | `<ConfidenceBar>` |
| `validation.issues[]` | `<ValidationReportPanel>` (cuando hay) |

## Cambios estructurales menores

### Nueva dependencia

`lucide-react@0.460.0` añadida al `package.json`. Reemplaza:
- Los emojis (`✓`, `⚠`, `→`) que la v1 usaba para íconos.
- Los caracteres Unicode tipo `↓` para flechas.

Beneficios: tamaño consistente, `strokeWidth` controlable, accesibilidad mejorada.

### `lib/cn.ts` (nuevo)

Helper trivial que combina `clsx` + `tailwind-merge`. Permite escribir:

```tsx
className={cn("base-classes", isActive && "active-classes", props.className)}
```

sin que las clases peleen entre sí. Ya estaban los dos paquetes en deps de v1, solo se expuso el helper.

### Componentes legacy reskinneados

Estos componentes mantienen su API pública (props, exports) pero se redibujaron al estilo navy. Si un consumidor externo los importa por shape, no rompe:

- `components/ui/button.tsx` — `Button` (variant, size, loading, children)
- `components/ui/spinner.tsx` — `Spinner` (size)
- `components/ui/badge.tsx` — `Badge` (variant)
- `components/ui/card.tsx` — `Card` (className), `CardHeader` (title, subtitle)
- `components/ui/input.tsx` — `Input` (label, error, ...html)
- `components/ui/textarea.tsx` — `Textarea` (label, error, ...html)
- `components/ui/select.tsx` — `Select` (label, value, onChange, options, placeholder, disabled) — **ahora delega a `MinimalSelect`** internamente

### Componentes nuevos

Todo bajo `components/ui/`:

- `aurora-background.tsx`
- `master-loader.tsx`
- `searchable-dropdown.tsx`
- `minimal-select.tsx`
- `minimal-input.tsx`
- `minimal-textarea.tsx`
- `section-label.tsx`
- `paper-layout.tsx`

Y bajo `components/layout/`:

- `nav-bar.tsx` (nuevo)
- `territory-selector.tsx` (mismo nombre y exports que v1, pero ahora usa `SearchableDropdown` por dentro — la prop adicional `size` es opcional con default `lg`)

## Cosas que ya no existen (y dónde estaban)

- **`components/data-quality/quality-badge.tsx`** — el archivo sigue existiendo, pero el tipo `DataQualityLevel` antes vivía en `types/index.ts` y se importaba. Ahora se exporta directamente desde `quality-badge.tsx` para evitar la dependencia faltante (en v1 estaba importado pero no declarado en el types — bug latente que se arregló de paso).

## Si una integración rompe — debugging cheat sheet

| Síntoma | Probable causa | Dónde mirar |
| --- | --- | --- |
| Análisis llega vacío al cambiar municipio | El `useEffect` automático no disparó | `app/analysis/page.tsx` línea ~85 (`useEffect` con `selection.municipalityId`) |
| Botón "Generar discurso" no se habilita | Validación `isValid` | `app/speech/page.tsx` línea ~109 (`isValid = ...`) |
| El paper-layout sale negro | `<PaperLayout>` está dentro de un padre que aplica clases de texto navy | Forzar `text-slate-700` o usar la primitiva tal cual |
| Las eyebrows salen sin tracking | `tracking-eyebrow` y `tracking-eyebrow_xs` son tokens custom | `tailwind.config.js > theme.extend.letterSpacing` |
| Los anillos del loader no rotan | El `keyframe rotate` no se cargó | Está duplicado en `globals.css` y `tailwind.config.js`. Si el componente usa `animation: rotate ...` inline, lee de globals.css. Verificar que `globals.css` esté importado en `app/layout.tsx` |
| El SearchableDropdown no encuentra municipios | `useMunicipalities` aún cargando | El componente muestra "Cargando…" cuando `loading=true` |
| TypeScript se queja de `DataQualityLevel` no exportado | Fix v2 ya hecho | Importar desde `@/components/data-quality/quality-badge` (no desde `@/types`) |

## Rollback (si algo crítico rompe en producción)

1. La v1 vivía en el repo antes de aplicar este patch. Un `git revert` del merge de v2 deja el frontend exactamente como estaba.
2. El backend NO necesita cambios — los contratos son idénticos. No hay migraciones de DB.
3. El store de Zustand persiste en `localStorage` con la key `vox-store-v2`. Esa key existía en v1 también, así que el state es compatible bidireccionalmente.
