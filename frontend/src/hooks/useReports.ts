"use client";

import { useCallback, useEffect, useState } from "react";

import type { SavedReport } from "@/lib/types";

const STORAGE_KEY = "zhizhen-reports-v1";
const MAX_REPORTS = 50;

function loadReports(): SavedReport[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item): item is SavedReport =>
        !!item &&
        typeof item === "object" &&
        typeof (item as SavedReport).id === "string" &&
        Array.isArray((item as SavedReport).rows)
    );
  } catch {
    return [];
  }
}

export function useReports() {
  const [reports, setReports] = useState<SavedReport[]>([]);
  const [hydrated, setHydrated] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect -- 首次挂载从 localStorage 恢复报告库 */
  useEffect(() => {
    setReports(loadReports());
    setHydrated(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(reports));
  }, [reports, hydrated]);

  const addReport = useCallback(
    (report: Omit<SavedReport, "id" | "date">) => {
      const entry: SavedReport = {
        ...report,
        id: `report-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
        date: Date.now(),
      };
      setReports((previous) => [entry, ...previous].slice(0, MAX_REPORTS));
      return entry.id;
    },
    []
  );

  const removeReport = useCallback((id: string) => {
    setReports((previous) => previous.filter((report) => report.id !== id));
  }, []);

  return { reports, addReport, removeReport };
}

export type ReportsStore = ReturnType<typeof useReports>;
