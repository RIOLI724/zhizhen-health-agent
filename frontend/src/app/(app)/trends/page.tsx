"use client";

import { useEffect, useMemo, useState } from "react";

import { useVitals, type VitalType } from "@/hooks/useVitals";

interface MetricConfig {
  value: VitalType;
  label: string;
  unit: string;
  normal?: [number, number];
  secondLabel?: string;
}

const METRICS: MetricConfig[] = [
  { value: "bp", label: "血压", unit: "mmHg", normal: [90, 140], secondLabel: "舒张压" },
  { value: "glucose", label: "血糖", unit: "mmol/L", normal: [3.9, 7.8] },
  { value: "weight", label: "体重", unit: "kg" },
];

const CHART_WIDTH = 640;
const CHART_HEIGHT = 220;
const PAD = { top: 16, right: 16, bottom: 30, left: 46 };

export default function TrendsPage() {
  const { entries, addEntry, removeEntry } = useVitals();
  const [metric, setMetric] = useState<VitalType>("bp");
  const [value, setValue] = useState("");
  const [second, setSecond] = useState("");
  const [date, setDate] = useState("");
  const [error, setError] = useState("");

  /* eslint-disable react-hooks/set-state-in-effect -- 日期需在客户端挂载后初始化，避免预渲染取当前时间 */
  useEffect(() => {
    setDate(new Date().toISOString().slice(0, 10));
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const config = METRICS.find((item) => item.value === metric) ?? METRICS[0];
  const series = useMemo(
    () =>
      entries
        .filter((entry) => entry.type === metric)
        .sort((a, b) => a.date.localeCompare(b.date)),
    [entries, metric]
  );

  const submit = () => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("请输入有效的数值");
      return;
    }
    let parsedSecond: number | undefined;
    if (config.secondLabel) {
      parsedSecond = Number(second);
      if (!Number.isFinite(parsedSecond) || parsedSecond <= 0) {
        setError(`请输入有效的${config.secondLabel}`);
        return;
      }
    }
    setError("");
    addEntry(metric, parsed, parsedSecond, date || new Date().toISOString().slice(0, 10));
    setValue("");
    setSecond("");
  };

  return (
    <div className="page">
      <header className="page__header">
        <h1>健康趋势</h1>
      </header>

      <section className="vital-form">
        <div className="vital-form__row">
          <label>
            <span>指标</span>
            <select
              value={metric}
              onChange={(event) => {
                setMetric(event.target.value as VitalType);
                setError("");
              }}
            >
              {METRICS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>{config.secondLabel ? "收缩压" : "数值"}</span>
            <input
              type="number"
              inputMode="decimal"
              placeholder={config.unit}
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          </label>
          {config.secondLabel ? (
            <label>
              <span>{config.secondLabel}</span>
              <input
                type="number"
                inputMode="decimal"
                placeholder={config.unit}
                value={second}
                onChange={(event) => setSecond(event.target.value)}
              />
            </label>
          ) : null}
          <label>
            <span>日期</span>
            <input
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </label>
          <button type="button" className="vital-form__add" onClick={submit}>
            记录
          </button>
        </div>
        {error ? <p className="page__error">{error}</p> : null}
      </section>

      <section className="vital-chart-card">
        <div className="vital-chart-card__head">
          <strong>{config.label}趋势</strong>
          <span>
            {config.normal
              ? `参考区间 ${config.normal[0]}–${config.normal[1]} ${config.unit}`
              : `单位 ${config.unit}`}
          </span>
        </div>
        {series.length === 0 ? (
          <p className="vital-chart-card__empty">还没有记录，先在上方添加一条</p>
        ) : (
          <TrendChart
            values={series.map((entry) => entry.value)}
            dates={series.map((entry) => entry.date)}
            normal={config.normal}
            unit={config.unit}
          />
        )}
      </section>

      <section className="vital-list">
        {series.length === 0 ? null : (
          <div className="vital-list__head">
            <span>记录</span>
            <small>{series.length} 条</small>
          </div>
        )}
        {[...series].reverse().map((entry) => (
          <div className="vital-item" key={entry.id}>
            <span className="vital-item__date">{entry.date}</span>
            <strong>
              {entry.second ? `${entry.value}/${entry.second}` : entry.value}
              <small>{config.unit}</small>
            </strong>
            <button type="button" onClick={() => removeEntry(entry.id)}>
              删除
            </button>
          </div>
        ))}
      </section>
    </div>
  );
}

function TrendChart({
  values,
  dates,
  normal,
  unit,
}: {
  values: number[];
  dates: string[];
  normal?: [number, number];
  unit: string;
}) {
  const candidates = [...values, ...(normal ? [normal[0], normal[1]] : [])];
  const min = Math.min(...candidates);
  const max = Math.max(...candidates);
  const span = max - min || 1;
  const yMin = min - span * 0.15;
  const yMax = max + span * 0.15;

  const innerWidth = CHART_WIDTH - PAD.left - PAD.right;
  const innerHeight = CHART_HEIGHT - PAD.top - PAD.bottom;
  const x = (index: number) =>
    PAD.left +
    (values.length === 1 ? innerWidth / 2 : (index / (values.length - 1)) * innerWidth);
  const y = (value: number) =>
    PAD.top + ((yMax - value) / (yMax - yMin)) * innerHeight;

  const points = values
    .map((value, index) => `${x(index)},${y(value)}`)
    .join(" ");

  return (
    <svg
      className="vital-chart"
      viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      role="img"
      aria-label="趋势图"
    >
      {normal ? (
        <rect
          x={PAD.left}
          y={y(normal[1])}
          width={innerWidth}
          height={Math.max(y(normal[0]) - y(normal[1]), 1)}
          fill="rgba(167, 227, 208, 0.28)"
        />
      ) : null}
      <line
        x1={PAD.left}
        y1={PAD.top + innerHeight}
        x2={CHART_WIDTH - PAD.right}
        y2={PAD.top + innerHeight}
        stroke="rgba(22, 33, 31, 0.15)"
      />
      {[0, 0.5, 1].map((ratio) => {
        const value = yMax - ratio * (yMax - yMin);
        return (
          <g key={ratio}>
            <line
              x1={PAD.left}
              y1={y(value)}
              x2={CHART_WIDTH - PAD.right}
              y2={y(value)}
              stroke="rgba(22, 33, 31, 0.06)"
            />
            <text x={PAD.left - 8} y={y(value) + 3} textAnchor="end" fontSize="9" fill="#7d8a85">
              {Math.round(value)}
            </text>
          </g>
        );
      })}
      <polyline
        points={points}
        fill="none"
        stroke="#0f5f52"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {values.map((value, index) => (
        <circle
          key={`${dates[index]}-${index}`}
          cx={x(index)}
          cy={y(value)}
          r="3.5"
          fill="#ffffff"
          stroke="#0f5f52"
          strokeWidth="2"
        />
      ))}
      {dates.length > 0 ? (
        <>
          <text x={PAD.left} y={CHART_HEIGHT - 8} fontSize="9" fill="#7d8a85">
            {dates[0].slice(5)}
          </text>
          <text
            x={CHART_WIDTH - PAD.right}
            y={CHART_HEIGHT - 8}
            textAnchor="end"
            fontSize="9"
            fill="#7d8a85"
          >
            {dates[dates.length - 1].slice(5)}
          </text>
          <text
            x={CHART_WIDTH - PAD.right}
            y={PAD.top + 10}
            textAnchor="end"
            fontSize="9"
            fill="#b8734a"
          >
            {unit}
          </text>
        </>
      ) : null}
    </svg>
  );
}
