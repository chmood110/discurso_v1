"use client";
import { Select } from "@/components/ui/select";
import { useMunicipalities, useNeighborhoods } from "@/hooks/use-municipalities";
import { useAppStore } from "@/lib/store";

interface Props {
  disabled?: boolean;
  showNeighborhood?: boolean;
}

export function TerritorySelector({ disabled = false, showNeighborhood = true }: Props) {
  const { selection, setMunicipality, setNeighborhood } = useAppStore();
  const { municipalities, loading: munsLoading } = useMunicipalities();
  const { neighborhoods, loading: nhLoading } = useNeighborhoods(selection.municipalityId);

  const munOptions = municipalities.map((m) => ({
    value: m.id,
    label: `${m.name} (${m.region})`,
  }));

  const nhOptions = neighborhoods.map((n) => ({
    value: n.id,
    label: `${n.name} (${n.type})`,
  }));

  return (
    <div className="space-y-3">
      <Select
        label="Municipio"
        value={selection.municipalityId}
        onChange={(id) => {
          const mun = municipalities.find((m) => m.id === id);
          setMunicipality(id, mun?.name ?? id);
        }}
        options={munOptions}
        placeholder={munsLoading ? "Cargando municipios…" : "Selecciona un municipio"}
        disabled={disabled || munsLoading}
      />

      {showNeighborhood && selection.municipalityId && (
        <Select
          label="Zona / Barrio (opcional)"
          value={selection.neighborhoodId ?? ""}
          onChange={(id) => {
            const nh = neighborhoods.find((n) => n.id === id);
            setNeighborhood(id, nh?.name ?? id);
          }}
          options={nhOptions}
          placeholder={nhLoading ? "Cargando zonas…" : "Municipio completo"}
          disabled={disabled || nhLoading}
        />
      )}
    </div>
  );
}
