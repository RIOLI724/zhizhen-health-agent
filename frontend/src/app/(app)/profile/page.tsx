"use client";

import { useState } from "react";

import { useProfilesStore } from "@/components/providers/AppProviders";
import type { ProfileSex } from "@/lib/types";

export default function ProfilePage() {
  const {
    profiles,
    activeId,
    setActiveId,
    updateProfile,
    addFamilyProfile,
    removeProfile,
  } = useProfilesStore();
  const [newLabel, setNewLabel] = useState("");

  const handleAdd = () => {
    if (!newLabel.trim()) return;
    addFamilyProfile(newLabel);
    setNewLabel("");
  };

  return (
    <div className="page">
      <header className="page__header">
        <h1>健康档案</h1>
      </header>

      <div className="profile-list">
        {profiles.map((profile) => (
          <section
            key={profile.id}
            className={`profile-page-card ${
              profile.id === activeId ? "is-active" : ""
            }`}
          >
            <div className="profile-page-card__head">
              <button
                type="button"
                className="profile-page-card__activate"
                onClick={() => setActiveId(profile.id)}
                disabled={profile.id === activeId}
              >
                {profile.id === activeId ? "当前使用" : "设为当前"}
              </button>
              <strong>{profile.label}</strong>
              <span className="profile-page-card__tag">
                {profile.relation === "self" ? "本人" : "家人"}
              </span>
              {profile.relation === "family" ? (
                <button
                  type="button"
                  className="profile-page-card__remove"
                  onClick={() => {
                    if (window.confirm(`删除「${profile.label}」的档案？`)) {
                      removeProfile(profile.id);
                    }
                  }}
                  aria-label={`删除 ${profile.label}`}
                >
                  ×
                </button>
              ) : null}
            </div>

            <div className="profile-page-card__fields">
              <label>
                <span>年龄</span>
                <input
                  type="number"
                  min={0}
                  max={120}
                  inputMode="numeric"
                  placeholder="选填"
                  value={profile.age}
                  onChange={(event) =>
                    updateProfile(profile.id, { age: event.target.value })
                  }
                />
              </label>
              <label>
                <span>性别</span>
                <select
                  value={profile.sex}
                  onChange={(event) => {
                    const sex = event.target.value as ProfileSex;
                    updateProfile(
                      profile.id,
                      sex === "female" ? { sex } : { sex, pregnant: false }
                    );
                  }}
                >
                  <option value="">未填</option>
                  <option value="male">男</option>
                  <option value="female">女</option>
                  <option value="other">其他</option>
                </select>
              </label>
              {profile.sex === "female" ? (
                <label className="profile-page-card__check">
                  <input
                    type="checkbox"
                    checked={profile.pregnant}
                    onChange={(event) =>
                      updateProfile(profile.id, {
                        pregnant: event.target.checked,
                      })
                    }
                  />
                  <span>孕产期</span>
                </label>
              ) : null}
            </div>
          </section>
        ))}
      </div>

      <div className="profile-add">
        <input
          type="text"
          placeholder="家人称呼，如：母亲"
          value={newLabel}
          maxLength={12}
          onChange={(event) => setNewLabel(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") handleAdd();
          }}
        />
        <button type="button" onClick={handleAdd} disabled={!newLabel.trim()}>
          添加家人档案
        </button>
      </div>
    </div>
  );
}
