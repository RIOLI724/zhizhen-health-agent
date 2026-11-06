"use client";

import { useCallback, useEffect, useState } from "react";

export type VitalType = "bp" | "glucose" | "weight";

export interface VitalEntry {
  id: string;
  type: VitalType;
  value: number;
  second?: number;
  date: string;
}

const STORAGE_KEY = "zhizhen-vitals-v1";

function loadEntries(): VitalEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item): item is VitalEntry =>
        !!item &&
        typeof item === "object" &&
        typeof (item as VitalEntry).id === "string" &&
        typeof (item as VitalEntry).value === "number"
    );
  } catch {
    return [];
  }
}

export function useVitals() {
  const [entries, setEntries] = useState<VitalEntry[]>([]);
  const [hydrated, setHydrated] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect -- 首次挂载从 localStorage 恢复记录 */
  useEffect(() => {
    setEntries(loadEntries());
    setHydrated(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  }, [entries, hydrated]);

  const addEntry = useCallback(
    (type: VitalType, value: number, second: number | undefined, date: string) => {
      const entry: VitalEntry = {
        id: `vital-${Date.now()}-${Math.random().toString(16).slice(2, 6)}`,
        type,
        value,
        second,
        date,
      };
      setEntries((previous) => [entry, ...previous]);
    },
    []
  );

  const removeEntry = useCallback((id: string) => {
    setEntries((previous) => previous.filter((entry) => entry.id !== id));
  }, []);

  return { entries, addEntry, removeEntry };
}

export type VitalsStore = ReturnType<typeof useVitals>;
