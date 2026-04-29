# VoxPolítica · Tlaxcala — Frontend (v2)

Plataforma de inteligencia territorial para los 60 municipios de Tlaxcala. La v2 mantiene el contrato completo del backend de la v1 y reemplaza la capa visual por un sistema de diseño editorial Navy / Sky.

## Quickstart

```bash
npm install
npm run dev
```

Por defecto el frontend espera el backend en `http://localhost:8000` (configurable vía `BACKEND_URL` para los rewrites de Next o `NEXT_PUBLIC_API_URL` para la base que usa `lib/api.ts`).

## Stack

- **Next.js 14** (App Router, RSC donde aplica, todas las pantallas son `"use client"` por la naturaleza interactiva).
- **TypeScript estricto** (`tsconfig.json` sin cambios respecto a v1).
- **Tailwind 3** con tokens custom (ver `docs/DESIGN-SYSTEM.md`).
- **Zustand** persistido en `localStorage` para la selección de territorio.
- **lucide-react** para todos los íconos.
- `clsx` + `tailwind-merge` envueltos en `lib/cn.ts`.

## Estructura

```
app/
  page.tsx            ← Landing editorial (módulos 01/02)
  analysis/page.tsx   ← Análisis Territorial
  speech/page.tsx     ← Discurso Político
  layout.tsx          ← Body navy, fuentes, metadatos
  globals.css         ← @import de fuentes, slider, paper, keyframes

components/
  ui/                 ← Primitivas del sistema de diseño
  layout/             ← NavBar + TerritorySelector
  data-quality/       ← QualityBadge, ConfidenceBar, disclaimers, validation

hooks/
  use-municipalities.ts  ← Sin cambios: trae municipios y vecindades del API

lib/
  api.ts              ← Sin cambios: cliente HTTP del backend
  store.ts            ← Sin cambios: Zustand store
  cn.ts               ← Helper clsx + tailwind-merge

types/
  index.ts            ← Sin cambios: tipos compartidos con backend

docs/
  DESIGN-SYSTEM.md    ← Tokens, primitivas, cuándo usar qué
  MIGRATION.md        ← v1 → v2: qué se preservó y qué cambió
```

## Comandos

| Comando | Qué hace |
| --- | --- |
| `npm run dev` | Servidor de desarrollo en `:3000` |
| `npm run build` | Build de producción (verificado: compila sin errores) |
| `npm run start` | Sirve el build |
| `npm run type-check` | `tsc --noEmit` (verificado: 0 errores) |
| `npm run lint` | ESLint con `next/core-web-vitals` |

## Variables de entorno

| Variable | Default | Para qué |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000/api/v1` | Base usada por `lib/api.ts` |
| `BACKEND_URL` | `http://localhost:8000` | Destino del rewrite `/api/v1/:path*` definido en `next.config.js` |

## Troubleshooting

**`Cannot find module 'lucide-react'`**: la dependencia se añadió en v2; correr `npm install` después de extraer el tarball.

**Las fuentes Outfit / Plus Jakarta Sans no cargan**: `app/globals.css` las pide a Google Fonts vía `@import`. Si el ambiente bloquea Google Fonts, se puede mover a `next/font/google` declarando dos fuentes en `app/layout.tsx` y exponiéndolas como variables CSS (`--font-display`, `--font-body`) — Tailwind ya está configurado para leerlas (`tailwind.config.js` → `theme.extend.fontFamily`).

**El loader orbital se ve "tieso"**: las animaciones (`pulseCore`, `rotate`) están definidas dos veces a propósito — una en `tailwind.config.js` (utility classes) y otra en `globals.css` (inline style en `MasterLoader`). Es redundancia consciente: si una build de Tailwind purgea las clases por error, los estilos inline del componente siguen funcionando.

**Errores de hidratación en `SearchableDropdown`**: el componente usa `useEffect` para click-outside y ESC. Asegurar que su contenedor padre sea `"use client"`. Las tres páginas ya lo son.

## QA manual recomendado

Lista mínima de smoke-test antes de cada release:

- [ ] Landing: hover sobre cada módulo activa el subrayado sky y dimea el otro.
- [ ] Analysis: seleccionar municipio → primer fetch automático (force_refresh: false) → resultados se renderizan.
- [ ] Analysis: botón "↻ Regenerar" llama con force_refresh: true.
- [ ] Analysis: validation issues, methodology disclaimer y confidence bar visibles cuando los datos los reportan.
- [ ] Analysis: PDF export descarga `analisis-<municipio>.pdf`.
- [ ] Speech: tab "Crear" sin source_text habilita "Generar" cuando hay municipio + goal + audience.
- [ ] Speech: tab "Mejorar" requiere ≥ 40 palabras en el textarea.
- [ ] Speech: el slider de duración recalcula `targetWords` en vivo.
- [ ] Speech: paneles de duration_verification, generation_plan, source_processing, improvements_made, validation aparecen cuando el backend los retorna.
- [ ] Speech: cada `body_section` se renderiza como bloque propio con su `persuasion_technique` (si existe).
- [ ] Speech: PDF export descarga `discurso-<municipio>.pdf`.
- [ ] Móvil ≤ 768px: la grilla de 12 columnas en Analysis colapsa, los headlines escalan, el dropdown de municipios sigue siendo tappable.

## Próximos pasos sugeridos

- Migrar las fuentes a `next/font/google` para evitar el FOUT del `@import`.
- Añadir Storybook con un caso por primitiva del sistema (ya están autodocumentadas en JSDoc).
- Considerar un componente `<DataPanel>` que envuelva la sección Validation/Generation Plan/Source Processing del Speech — comparten patrón pero hoy se repiten.
