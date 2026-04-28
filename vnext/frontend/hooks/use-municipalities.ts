"use client";

import { useEffect, useState } from "react";
import * as api from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Neighborhood } from "@/types";

export function useMunicipalities() {
  const { municipalities, setMunicipalities } = useAppStore();
  const [loading, setLoading] = useState<boolean>(municipalities.length === 0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (municipalities.length > 0) {
      setLoading(false);
      return;
    }

    let mounted = true;

    api.territory
      .municipalities()
      .then((list) => {
        if (!mounted) return;
        setMunicipalities(list);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : "Error cargando municipios");
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [municipalities.length, setMunicipalities]);

  return { municipalities, loading, error };
}

export function useNeighborhoods(municipalityId: string) {
  const { setNeighborhoods, neighborhoods } = useAppStore();
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!municipalityId) {
      setNeighborhoods([]);
      setLoading(false);
      return;
    }

    let mounted = true;
    setLoading(true);

    api.territory
      .neighborhoods(municipalityId)
      .then((list: Neighborhood[]) => {
        if (!mounted) return;
        setNeighborhoods(list);
        setLoading(false);
      })
      .catch(() => {
        if (!mounted) return;
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [municipalityId, setNeighborhoods]);

  return { neighborhoods, loading };
}