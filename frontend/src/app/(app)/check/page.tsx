"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { Icon } from "@/components/ui/Icon";

interface QuestionOption {
  value: string;
  label: string;
}

interface Question {
  id: string;
  title: string;
  type: "single" | "multi";
  options: QuestionOption[];
}

interface Symptom {
  id: string;
  name: string;
  questions: Question[];
}

interface TriageResult {
  symptom: string;
  level: string;
  department: string;
  timeframe: string;
  reasons: string[];
  evidence: string[];
}

const LEVEL_LABEL: Record<string, string> = {
  L1: "立即急救",
  L2: "尽快就医",
  L3: "近期门诊",
  L4: "可观察",
};

export default function CheckPage() {
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [selected, setSelected] = useState<Symptom | null>(null);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [result, setResult] = useState<TriageResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/triage/symptoms")
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then(setSymptoms)
      .catch(() => setError("问卷加载失败：请确认后端已启动"));
  }, []);

  const allAnswered = useMemo(
    () =>
      Boolean(
        selected &&
          selected.questions.every(
            (question) => (answers[question.id]?.length ?? 0) > 0
          )
      ),
    [selected, answers]
  );

  const chooseSymptom = (symptom: Symptom) => {
    setSelected(symptom);
    setAnswers({});
    setResult(null);
    setError("");
  };

  const toggleOption = (question: Question, value: string) => {
    setAnswers((previous) => {
      const current = previous[question.id] ?? [];
      if (question.type === "single") {
        return { ...previous, [question.id]: [value] };
      }
      if (value === "none") {
        return { ...previous, [question.id]: ["none"] };
      }
      const withoutNone = current.filter((item) => item !== "none");
      const next = withoutNone.includes(value)
        ? withoutNone.filter((item) => item !== value)
        : [...withoutNone, value];
      return { ...previous, [question.id]: next };
    });
  };

  const submit = async () => {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      const payload: Record<string, string | string[]> = {};
      selected.questions.forEach((question) => {
        const value = answers[question.id] ?? [];
        payload[question.id] =
          question.type === "single" ? value[0] : value;
      });
      const response = await fetch("/api/triage/assess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symptom: selected.id, answers: payload }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(
          typeof data?.detail === "string" ? data.detail : "评估失败"
        );
      }
      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "评估失败，请稍后再试");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setSelected(null);
    setAnswers({});
    setResult(null);
    setError("");
  };

  return (
    <div className="page">
      <header className="page__header">
        <h1>症状自查</h1>
      </header>

      {error ? <p className="page__error">{error}</p> : null}

      {!selected ? (
        <div className="symptom-grid">
          {symptoms.map((symptom) => (
            <button
              key={symptom.id}
              type="button"
              className="symptom-card"
              onClick={() => chooseSymptom(symptom)}
            >
              <span className="symptom-card__icon">
                <Icon name="check" />
              </span>
              <strong>{symptom.name}</strong>
              <small>{symptom.questions.length} 个问题</small>
            </button>
          ))}
        </div>
      ) : result ? (
        <section className={`triage-result triage-result--${result.level.toLowerCase()}`}>
          <div className="triage-result__head">
            <span className="triage-result__level">
              {result.level} · {LEVEL_LABEL[result.level] ?? "就医建议"}
            </span>
            <strong>{result.symptom}</strong>
          </div>
          <div className="triage-result__meta">
            <div>
              <small>建议科室</small>
              <strong>{result.department}</strong>
            </div>
            <div>
              <small>就医时限</small>
              <strong>{result.timeframe}</strong>
            </div>
          </div>
          <div className="triage-result__reasons">
            <small>判断依据</small>
            <ul>
              {result.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
            {result.evidence.length > 0 ? (
              <p className="triage-result__evidence">
                参考：{result.evidence.join("；")}
              </p>
            ) : null}
          </div>
          <div className="triage-result__actions">
            <button type="button" onClick={reset}>
              再查一个
            </button>
            <Link href="/">去对话问 AI</Link>
          </div>
        </section>
      ) : (
        <div className="wizard">
          <div className="wizard__head">
            <button type="button" className="page__back" onClick={reset}>
              ← 换一个症状
            </button>
            <strong>{selected.name}</strong>
          </div>

          {selected.questions.map((question) => (
            <section className="wizard__question" key={question.id}>
              <p>{question.title}</p>
              <div className="wizard__options">
                {question.options.map((option) => {
                  const active = (answers[question.id] ?? []).includes(
                    option.value
                  );
                  return (
                    <button
                      key={option.value}
                      type="button"
                      className={`wizard__option ${active ? "is-active" : ""}`}
                      onClick={() => toggleOption(question, option.value)}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </section>
          ))}

          <button
            type="button"
            className="page__cta page__cta--wide"
            disabled={!allAnswered || loading}
            onClick={submit}
          >
            {loading ? "评估中…" : "查看分诊结果"}
          </button>
        </div>
      )}
    </div>
  );
}
