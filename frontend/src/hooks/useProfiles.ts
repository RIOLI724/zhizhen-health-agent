"use client";

import { useCallback, useEffect, useState } from "react";

import type { HealthProfile, ProfileSex } from "@/lib/types";

const STORAGE_KEY = "zhizhen-profiles-v1";

const DEFAULT_PROFILE: HealthProfile = {
  id: "self",
  relation: "self",
  label: "本人",
  age: "",
  sex: "",
  pregnant: false,
};

function loadProfiles(): HealthProfile[] {
  if (typeof window === "undefined") return [DEFAULT_PROFILE];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [DEFAULT_PROFILE];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length === 0) return [DEFAULT_PROFILE];
    return parsed
      .filter(
        (item): item is HealthProfile =>
          !!item &&
          typeof item === "object" &&
          typeof (item as HealthProfile).id === "string" &&
          typeof (item as HealthProfile).label === "string"
      )
      .map((item) => ({
        id: item.id,
        relation: item.relation === "family" ? "family" : "self",
        label: item.label,
        age: item.age ?? "",
        sex: item.sex ?? "",
        pregnant: Boolean(item.pregnant),
      }));
  } catch {
    return [DEFAULT_PROFILE];
  }
}

export function useProfiles() {
  const [profiles, setProfiles] = useState<HealthProfile[]>([DEFAULT_PROFILE]);
  const [activeId, setActiveId] = useState<string>("self");
  const [hydrated, setHydrated] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect -- 首次挂载从 localStorage 恢复档案 */
  useEffect(() => {
    const list = loadProfiles();
    setProfiles(list);
    setActiveId(window.localStorage.getItem(`${STORAGE_KEY}-active`) ?? list[0].id);
    setHydrated(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(profiles));
    window.localStorage.setItem(`${STORAGE_KEY}-active`, activeId);
  }, [profiles, activeId, hydrated]);

  const activeProfile =
    profiles.find((profile) => profile.id === activeId) ?? profiles[0];

  const updateProfile = useCallback((id: string, patch: Partial<HealthProfile>) => {
    setProfiles((previous) =>
      previous.map((profile) =>
        profile.id === id ? { ...profile, ...patch } : profile
      )
    );
  }, []);

  const addFamilyProfile = useCallback((label: string) => {
    const id = `family-${Date.now()}`;
    setProfiles((previous) => [
      ...previous,
      {
        id,
        relation: "family",
        label: label.trim() || "家人",
        age: "",
        sex: "",
        pregnant: false,
      },
    ]);
    setActiveId(id);
  }, []);

  const removeProfile = useCallback((id: string) => {
    setProfiles((previous) => {
      const next = previous.filter((profile) => profile.id !== id);
      const safe = next.length > 0 ? next : [DEFAULT_PROFILE];
      setActiveId((current) =>
        current === id ? safe[0].id : current
      );
      return safe;
    });
  }, []);

  return {
    profiles,
    activeProfile,
    activeId,
    setActiveId,
    updateProfile,
    addFamilyProfile,
    removeProfile,
  };
}

export type ProfilesStore = ReturnType<typeof useProfiles>;
export type { ProfileSex };
