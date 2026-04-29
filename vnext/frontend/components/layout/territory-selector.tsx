"use client";

import { useMemo } from "react";
import { SearchableDropdown } from "@/components/ui/searchable-dropdown";
import { useMunicipalities, useNeighborhoods } from "@/hooks/use-municipalities";
import { useAppStore } from "@/lib/store";

/**
 * TerritorySelector
 *
 * Backend-aware shell around <SearchableDropdown />. It owns nothing —
 * everything still lives in the existing `useAppStore` (selection state,
 * Municipality / Neighborhood lists from the API).
 *
 * The two dropdowns rendered here both use the *typography-first* design,
 * with neighborhoods automatically loaded once a municipality is picked
 * (delegated to the existing `useNeighborhoods` hook — unchanged).
 *
 * Props are 1:1 compatible with the previous select-based version.
 */

interface Props {
  disabled?: boolean;
  showNeighborhood?: boolean;
  /** Optional: visual size of the municipality trigger (defaults to lg). */
  size?: "lg" | "md";
}

export function TerritorySelector({
  disabled = false,
  showNeighborhood = true,
  size = "lg",
}: Props) {
  const { selection, setMunicipality, setNeighborhood } = useAppStore();
  const { municipalities, loading: munsLoading } = useMunicipalities();
  const { neighborhoods, loading: nhLoading } = useNeighborhoods(
    selection.municipalityId
  );

  const munOptions = useMemo(
    () =>
      municipalities.map((m) => ({
        value: m.id,
        label: m.name,
        sublabel: m.region ?? undefined,
      })),
    [municipalities]
  );

  const nhOptions = useMemo(
    () =>
      neighborhoods.map((n) => ({
        value: n.id,
        label: n.name,
      })),
    [neighborhoods]
  );

  return (
    <div className="space-y-12">
      <SearchableDropdown
        options={munOptions}
        value={selection.municipalityId}
        onChange={(id, opt) => setMunicipality(id, opt.label)}
        placeholder="Selecciona el municipio…"
        searchPlaceholder="Filtra por nombre o región…"
        loading={munsLoading}
        disabled={disabled || munsLoading}
        size={size}
      />

      {showNeighborhood && selection.municipalityId && (
        <SearchableDropdown
          options={nhOptions}
          value={selection.neighborhoodId ?? ""}
          onChange={(id, opt) => setNeighborhood(id, opt.label)}
          placeholder={
            nhLoading
              ? "Cargando zonas…"
              : nhOptions.length === 0
                ? "Municipio completo"
                : "Zona o barrio (opcional)"
          }
          searchPlaceholder="Filtra zonas…"
          emptyLabel="Sin zonas registradas"
          loading={nhLoading}
          disabled={disabled || nhLoading || nhOptions.length === 0}
          size="md"
        />
      )}
    </div>
  );
}
