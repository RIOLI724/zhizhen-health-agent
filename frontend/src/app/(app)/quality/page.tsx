"use client";

import { useEffect, useState } from "react";

interface QualityData {
  app: string;
  mode: string;
  vision: string | null;
  knowledge_entries: number;
  red_flag_rules: number;
  eval: {
    generated_at: string;
    embedder?: string;
    metrics: {
      retrieval: Record<string, number>;
      triage: Record<string, number>;
      safety: Record<string, number>;
    };
    comparison?: Record<string, Record<string, number>>;
  } | null;
  metrics: {
    total: number;
    avg_duration_ms: number;
    p95_duration_ms: number;
    avg_ttft_ms: number;
    ok_rate: number;
    recent: Array<{
      intent: string;
      tools: number;
      duration_ms: number;
      mode: string;
      ok: boolean;
      at: string;
      ttft_ms?: number | null;
    }>;
  };
}

const STACK = [
  ["前端", "Next.js 16 · React 19 · TypeScript · Tailwind CSS 4"],
  ["后端", "FastAPI · LangGraph 状态图 · SSE"],
  ["检索", "Chroma 向量库 · BM25 · RRF 混合检索"],
  ["模型", "GLM-4-Flash 对话 · GLM-4.6V-Flash 视觉识别"],
  ["评测", "hit@k / MRR · 红旗召回 · 越界拒答"],
];

const EVAL_LABELS: Record<string, string> = {
  retrieval: "检索",
  triage: "分诊",
  safety: "安全",
};

export default function QualityPage() {
  const [data, setData] = useState<QualityData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/quality")
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then(setData)
      .catch(() => setError("质量数据加载失败：请确认后端已启动"));
  }, []);

  if (error) {
    return (
      <div className="page">
        <header className="page__header">
          <h1>质量面板</h1>
        </header>
        <p className="page__error">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page">
        <header className="page__header">
          <h1>质量面板</h1>
        </header>
        <p className="page__muted">加载中…</p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page__header">
        <h1>质量面板</h1>
        <p>
          {data.app} · 模型 {data.mode}
          {data.vision ? ` · 视觉 ${data.vision}` : ""}
        </p>
      </header>

      <p className="quality-internal">
        内部页 · 面向开发与面试评审，不对普通用户展示；正常产品导航中不包含此页
      </p>

      <div className="stat-grid">
        <div className="stat-card">
          <strong>{data.knowledge_entries}</strong>
          <span>指南知识条目</span>
        </div>
        <div className="stat-card">
          <strong>{data.red_flag_rules}</strong>
          <span>红旗分诊规则</span>
        </div>
        <div className="stat-card">
          <strong>
            {data.eval
              ? `${(data.eval.metrics.retrieval["hit@1"] * 100).toFixed(1)}%`
              : "—"}
          </strong>
          <span>检索 hit@1</span>
        </div>
        <div className="stat-card">
          <strong>
            {data.eval
              ? `${(data.eval.metrics.safety["safety_pass_rate"] * 100).toFixed(0)}%`
              : "—"}
          </strong>
          <span>安全通过率</span>
        </div>
      </div>

      {data.eval ? (
        <section className="quality-section">
          <div className="quality-section__head">
            <strong>离线评测</strong>
            <small>
              生成于 {data.eval.generated_at}
              {data.eval.embedder ? ` · 向量 ${data.eval.embedder}` : ""}
            </small>
          </div>
          {Object.entries(data.eval.metrics).map(([group, metrics]) => (
            <div className="quality-row" key={group}>
              <span>{EVAL_LABELS[group] ?? group}</span>
              <div>
                {Object.entries(metrics).map(([key, value]) => (
                  <em key={key}>
                    {key} {typeof value === "number" ? value : String(value)}
                  </em>
                ))}
              </div>
            </div>
          ))}
          {data.eval.comparison?.mock && data.eval.comparison?.bge ? (
            <div className="quality-row">
              <span>向量对比</span>
              <div>
                <em>mock hit@1 {data.eval.comparison.mock["hit@1"]}</em>
                <em>bge hit@1 {data.eval.comparison.bge["hit@1"]}</em>
                <em>mock mrr {data.eval.comparison.mock.mrr}</em>
                <em>bge mrr {data.eval.comparison.bge.mrr}</em>
              </div>
            </div>
          ) : null}
        </section>
      ) : (
        <section className="quality-section">
          <p className="page__muted">
            评测报告尚未生成：运行 <code>python -m eval.run_eval --check</code>
          </p>
        </section>
      )}

      <section className="quality-section">
        <div className="quality-section__head">
          <strong>实时请求</strong>
          <small>最近 {data.metrics.total} 次 · 不含用户内容</small>
        </div>
        <div className="quality-stats">
          <span>平均 {data.metrics.avg_duration_ms} ms</span>
          <span>P95 {data.metrics.p95_duration_ms} ms</span>
          <span>首字 {data.metrics.avg_ttft_ms} ms</span>
          <span>成功率 {(data.metrics.ok_rate * 100).toFixed(1)}%</span>
        </div>
        {data.metrics.recent.length > 0 ? (
          <div className="quality-table">
            {data.metrics.recent.map((item, index) => (
              <div className="quality-table__row" key={`${item.at}-${index}`}>
                <span>{item.at}</span>
                <span>{item.intent}</span>
                <span>{item.tools} 次工具</span>
                <span>{item.duration_ms} ms</span>
                <span className={item.ok ? "is-ok" : "is-bad"}>
                  {item.ok ? "成功" : "失败"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="page__muted">还没有请求记录，去对话里问几个问题</p>
        )}
      </section>

      <section className="quality-section">
        <div className="quality-section__head">
          <strong>技术栈</strong>
        </div>
        {STACK.map(([label, value]) => (
          <div className="quality-row" key={label}>
            <span>{label}</span>
            <div>
              <em>{value}</em>
            </div>
          </div>
        ))}
      </section>

      <section className="quality-section">
        <div className="quality-section__head">
          <strong>设计取舍</strong>
        </div>
        <ul className="quality-notes">
          <li>红旗分诊走确定性规则，模型无权降级——医疗场景的安全底线</li>
          <li>回答只展示正文，检索与引用在后端保障可追溯</li>
          <li>无 Key 或模型限流时自动回退规则模板，对话不中断</li>
          <li>报告图片只在内存处理，不落盘、不回传</li>
        </ul>
      </section>
    </div>
  );
}
