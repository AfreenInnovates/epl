import { useCallback, useState } from "react";

import type { SavedResearchRun } from "../types";

const STORAGE_KEY = "eplai.saved-research-runs.v1";
const MAX_SAVED_RUNS = 12;

function readRuns(): SavedResearchRun[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeRuns(runs: SavedResearchRun[]) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(runs));
  } catch {
    // Storage can be unavailable in private browsing or when the quota is full.
  }
}

export function useSavedRuns() {
  const [runs, setRuns] = useState<SavedResearchRun[]>(readRuns);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);

  const save = useCallback((run: SavedResearchRun) => {
    setLastSavedId(run.id);
    setRuns((current) => {
      const next = [run, ...current.filter((item) => item.id !== run.id)].slice(
        0,
        MAX_SAVED_RUNS,
      );
      writeRuns(next);
      return next;
    });
  }, []);

  const remove = useCallback((id: string) => {
    setRuns((current) => {
      const next = current.filter((run) => run.id !== id);
      writeRuns(next);
      return next;
    });
  }, []);

  return { runs, save, remove, lastSavedId };
}
