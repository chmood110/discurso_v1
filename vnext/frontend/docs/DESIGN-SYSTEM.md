# Sistema de Diseño · VoxPolítica v2

Editorial minimalista de alto nivel. Toda la pantalla es Navy (`#020617`) con acentos Sky (`sky-400` / `sky-500`) y una escala completa de Slate (`200` → `900`). La tipografía hace el trabajo pesado: hay muy poca chrome (cero cards con sombras suaves, casi cero bordes redondeados, separadores hairline en vez de fondos diferenciados).

## 1. Tokens

### 1.1 Color

| Token | Valor | Uso |
| --- | --- | --- |
| `bg-ink` | `#020617` | Canvas base de toda la app |
| `bg-ink-soft` | `#0f172a` | Variante para superficies elevadas |
| `text-white` | `#ffffff` | Headlines, valores grandes |
| `text-slate-200` | — | Texto de cuerpo principal |
| `text-slate-400` / `text-slate-500` | — | Texto secundario / descripciones |
| `text-slate-600` / `text-slate-700` | — | Eyebrow labels muteados |
| `text-slate-800` / `text-slate-900` | — | Placeholders y hairlines |
| `text-sky-400` / `text-sky-500` | — | Acento primario (siempre — nunca emerald) |
| `text-amber-300` / `text-red-300` | — | Estados de advertencia / error |

`tailwind.config.js` también expone `brand.500` (`#0ea5e9` = sky-500) por si algún uso semántico necesita un alias estable.

### 1.2 Tipografía

Dos familias, dos jobs:

| Token Tailwind | Familia | Para qué |
| --- | --- | --- |
| `font-display` | Outfit | Headlines, números grandes, eyebrows del paper layout |
| `font-body` | Plus Jakarta Sans | Cuerpo, párrafos, todo el texto que se lee |

Las fuentes se cargan vía `@import` en `globals.css`. Si necesitas más pesos: están disponibles 200/300/400/500/600/700/800 en Outfit y 300/400/500/600/700 en Plus Jakarta Sans.

**Reglas**:
- Nunca mezclar Outfit dentro de un párrafo de body.
- Las eyebrow labels (`SectionLabel`) siempre van en Plus Jakarta Sans (`uppercase`, `tracking-eyebrow`, peso `black` o `bold`, tamaño `[10px]`).
- Los números (KPIs, métricas, "01"/"02") van en Outfit `font-extrabold` con `tracking-tighter`.

### 1.3 Spacing y ritmo

El sistema es deliberadamente generoso. Si dudas, usa más aire:

- **Entre secciones de un mismo bloque**: `space-y-6` (24px)
- **Entre subsecciones**: `space-y-12` o `space-y-16` (48–64px)
- **Entre secciones macro de una página**: `space-y-20` o `space-y-32` (80–128px)
- **Padding lateral de página**: `px-10` desktop, `px-6` mobile
- **Max-width de la página**: `max-w-6xl` (Analysis), `max-w-4xl` (Speech), `max-w-5xl` (Landing)

### 1.4 Tracking (letter-spacing)

Dos custom tokens en `tailwind.config.js`:

| Token | Valor | Uso |
| --- | --- | --- |
| `tracking-eyebrow` | `0.3em` | Labels uppercase prominentes (sección, eje) |
| `tracking-eyebrow_xs` | `0.2em` | Labels uppercase secundarios (metadatos, badges) |

### 1.5 Animaciones

Todas declaradas en `tailwind.config.js > theme.extend.keyframes/animation`:

| Clase | Para qué |
| --- | --- |
| `animate-aurora-pan` | Fondo animado del landing (combina con `bg-aurora-navy bg-300`) |
| `animate-pulse-core` | Núcleo del MasterLoader (también vía CSS inline) |
| `animate-spin-slow` / `animate-spin-mid` / `animate-spin-fast` | Anillos del MasterLoader |
| `animate-fade-in` / `animate-fade-in-slow` | Transición entre estados (form → loading → results) |
| `animate-slide-in-bottom` | Aparición del form inicial |

## 2. Primitivas

### 2.1 `<AuroraBackground variant="aurora" | "soft">`

Wrapper full-screen del canvas. Dos variantes:
- **`aurora`**: Gradiente animado, panea cada 30s. Solo en el landing.
- **`soft`**: Radial estático, mucho más quieto. Para Analysis y Speech (donde el contenido es lo que importa).

```tsx
<AuroraBackground variant="soft">
  <NavBar ... />
  <main>...</main>
</AuroraBackground>
```

### 2.2 `<MasterLoader size="lg" | "md" headline subline showSpark? />`

El "thinking state" canónico. Anillos orbitales + núcleo pulsante + headline.
- `lg` (240px, 3 anillos) → Analysis
- `md` (200px, 2 anillos) → Speech
- `showSpark` reemplaza el cuadro central por un ícono ✨ Sparkles

### 2.3 `<SearchableDropdown options value onChange placeholder ... />`

El selector tipográfico. Genérico sobre `{ value, label, sublabel? }` para envolver `Municipality`, `Neighborhood`, o cualquier shape futura sin tocar el componente. Cierra con click outside y ESC.

```tsx
<SearchableDropdown
  options={municipalities.map(m => ({ value: m.id, label: m.name, sublabel: m.region }))}
  value={selection.municipalityId}
  onChange={(id, opt) => setMunicipality(id, opt.label)}
  placeholder="Selecciona el municipio…"
  size="lg"  // "lg" para headlines, "md" para inputs secundarios
/>
```

### 2.4 `<MinimalSelect options value onChange />`

Hermano menor del SearchableDropdown — sin search, para enums chicos (tono, canal). Mismo lenguaje visual: solo border-bottom, foco en sky.

### 2.5 `<MinimalInput inputSize="lg" | "md" />` y `<MinimalTextarea />`

Inputs sin caja: solo `border-b border-slate-800`, fondo transparente, foco mueve la línea a sky. Combinarlos siempre con un `<SectionLabel />` arriba.

### 2.6 `<SectionLabel number? icon? tone="accent" | "muted">`

La eyebrow de toda forma. Ejemplos:

```tsx
<SectionLabel number="01" tone="accent" icon={<MapPin className="h-3.5 w-3.5" />}>
  Demarcación
</SectionLabel>
```

`accent` = sky (paso activo / requerido), `muted` = slate-600 (paso secundario).

### 2.7 `<PaperLayout>`

Wrapper blanco con franja sky superior. Solo se usa en el resultado del Speech — es la "hoja de papel" donde vive el guion. Dentro de él, los colores se invierten (slate-700 en blanco), así que tener cuidado al copiar componentes navy hacia adentro.

### 2.8 `<NavBar fixed? tabs? activeTab? onTabChange? rightSlot? showHome?>`

Header compartido. Variantes:
- **Floating** (default): se usa en Analysis. `px-10 py-12`.
- **Fixed**: se pega al top con backdrop blur, usado en Speech junto al sistema de tabs.

### 2.9 `<TerritorySelector size="lg" | "md" disabled? showNeighborhood?>`

Wrapper backend-aware del `SearchableDropdown`. No tiene estado propio: lee/escribe en `useAppStore`. La prop `size` controla el tamaño del dropdown del municipio (lg en Analysis, md en Speech).

## 3. Patrones recurrentes

### 3.1 Una sección de formulario

```tsx
<section className="space-y-6">
  <SectionLabel number="01" tone="accent" icon={<MapPin className="h-3.5 w-3.5" />}>
    Demarcación
  </SectionLabel>
  <TerritorySelector size="lg" />
</section>
```

### 3.2 Una sección de resultado tipo "artículo"

```tsx
<article className="space-y-8">
  <SectionLabel tone="muted">
    <span className="mr-3 inline-block h-px w-10 bg-slate-800 align-middle" />
    Análisis de situación
  </SectionLabel>
  <p className="font-display text-3xl font-light leading-tight text-white md:text-4xl">
    {executive_summary}
  </p>
</article>
```

El hairline horizontal de 40px antes del label es la firma editorial del sistema. Reservar para secciones macro dentro de la columna principal de resultados.

### 3.3 Métrica grande estilo "número editorial"

```tsx
<div className="space-y-2">
  <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-slate-700">
    Densidad electoral
  </p>
  <p className="font-display text-5xl font-extrabold tracking-tighter text-white">
    18,500
  </p>
  <p className="text-[10px] font-bold uppercase tracking-eyebrow_xs text-sky-400">
    votantes activos
  </p>
</div>
```

### 3.4 Un panel de información secundaria sobre fondo navy

```tsx
<section className="space-y-6 border-t border-slate-900 pt-10">
  <SectionLabel tone="muted">Verificación de duración</SectionLabel>
  <div className="grid gap-6 md:grid-cols-4">
    <Stat label="Objetivo" value="10 min" />
    {/* … */}
  </div>
</section>
```

Ese `border-t border-slate-900 pt-10` es el separador estándar entre paneles del Speech.

## 4. Reglas no-negociables

1. **Cero cards con sombra.** El sistema separa con espacio y hairlines, no con elevación.
2. **Cero emerald.** Si ves verde, alguien copió de la v1. El acento es sky.
3. **Cero placeholders blancos.** Los placeholders viven en `text-slate-800` (casi imperceptibles, intencional). El usuario debe leer el label, no el placeholder.
4. **Headlines en Outfit, body en Jakarta.** Mezclar las dos en un solo nivel de jerarquía rompe la voz.
5. **Eyebrow labels SIEMPRE uppercase + tracking.** Sin excepciones. Si necesitas un label en case normal, no es un eyebrow — es un párrafo y va en `font-body text-sm`.
6. **`SearchableDropdown` para cardinalidad alta, `MinimalSelect` para enums chicos.** Si tienes 60 municipios, dropdown con search. Si tienes 5 tonos, select.
7. **El `<PaperLayout>` es solo para el resultado del Speech.** No usarlo como contenedor genérico.

## 5. Cómo agregar una nueva pantalla

1. Crear `app/<ruta>/page.tsx` con `"use client"`.
2. Envolver todo en `<AuroraBackground variant="soft">`.
3. Añadir un `<NavBar />` (decidir si flotante o fijo).
4. Tres estados típicos: `form` / `loading` / `result`. Usar `useState<"form"|"loading"|"result">` o derivar del store.
5. Para el `loading`, `<MasterLoader />` con headline en español y subline opcional.
6. Para el `form`, secciones numeradas (`01`, `02`, …) usando `<SectionLabel number>` y `<MinimalInput>` / `<SearchableDropdown>` / `<MinimalSelect>`.
7. Para el `result`, layout editorial: 8 columnas para narrativa + 4 columnas para data dura, separados por `gap-20`.
8. Cualquier llamado a backend va en `lib/api.ts`. El estado de loading/error se maneja en `useAppStore` (añadir keys nuevas si hace falta).
