"use client";
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { AnalysisDetail, Municipality, Neighborhood, SpeechDetail } from "@/types";

interface TerritorySelection {
  municipalityId: string;
  municipalityName: string;
  neighborhoodId?: string;
  neighborhoodName?: string;
}

interface LoadingState {
  analysis: boolean;
  speech: boolean;
  export: boolean;
}

interface AppStore {
  selection: TerritorySelection;
  municipalities: Municipality[];
  neighborhoods: Neighborhood[];
  setMunicipality: (id: string, name: string) => void;
  setNeighborhood: (id: string, name: string) => void;
  setMunicipalities: (list: Municipality[]) => void;
  setNeighborhoods: (list: Neighborhood[]) => void;

  analysisRun: AnalysisDetail | null;
  speechRun: SpeechDetail | null;
  setAnalysisRun: (run: AnalysisDetail | null) => void;
  setSpeechRun: (run: SpeechDetail | null) => void;

  loading: LoadingState;
  setLoading: (key: keyof LoadingState, value: boolean) => void;

  errors: Record<string, string>;
  setError: (key: string, message: string) => void;
  clearError: (key: string) => void;

  clearDerivedState: () => void;
}

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      selection: { municipalityId: "", municipalityName: "" },
      municipalities: [],
      neighborhoods: [],

      setMunicipality: (id, name) => {
        if (get().selection.municipalityId !== id) get().clearDerivedState();
        set({ selection: { municipalityId: id, municipalityName: name } });
      },
      setNeighborhood: (id, name) =>
        set((s) => ({ selection: { ...s.selection, neighborhoodId: id, neighborhoodName: name } })),
      setMunicipalities: (list) => set({ municipalities: list }),
      setNeighborhoods: (list) => set({ neighborhoods: list }),

      analysisRun: null,
      speechRun: null,
      setAnalysisRun: (run) => set({ analysisRun: run }),
      setSpeechRun: (run) => set({ speechRun: run }),

      loading: { analysis: false, speech: false, export: false },
      setLoading: (key, value) =>
        set((s) => ({ loading: { ...s.loading, [key]: value } })),

      errors: {},
      setError: (key, message) => set((s) => ({ errors: { ...s.errors, [key]: message } })),
      clearError: (key) =>
        set((s) => { const { [key]: _, ...rest } = s.errors; return { errors: rest }; }),

      clearDerivedState: () =>
        set({ analysisRun: null, speechRun: null, neighborhoods: [] }),
    }),
    {
      name: "vox-store-v2",
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ selection: s.selection }),
    }
  )
);