"use client";

import { useState } from "react";
import Link from "next/link";

import { ReportCard } from "@/components/chat/ReportCard";
import { useReportsStore } from "@/components/providers/AppProviders";
import { Icon } from "@/components/ui/Icon";
import type { SavedReport } from "@/lib/types";

export default function ReportsPage() {
  const { reports, removeReport } = useReportsStore();
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="page">
      <header className="page__header">
        <h1>报告库</h1>
        {reports.length > 0 ? <p>{reports.length} 份报告</p> : null}
      </header>

      {reports.length === 0 ? (
        <div className="page__empty">
          <span className="page__empty-icon">
            <Icon name="doc" />
          </span>
          <strong>还没有报告记录</strong>
          <p>上传报告图片，或解读一份样例报告，都会自动存进报告库。</p>
          <Link href="/" className="page__cta">
            去对话
          </Link>
        </div>
      ) : (
        <div className="report-list">
          {reports.map((report) => (
            <ReportItem
              key={report.id}
              report={report}
              open={openId === report.id}
              onToggle={() =>
                setOpenId(openId === report.id ? null : report.id)
              }
              onDelete={() => {
                if (window.confirm("删除这份报告记录？")) {
                  removeReport(report.id);
                }
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ReportItem({
  report,
  open,
  onToggle,
  onDelete,
}: {
  report: SavedReport;
  open: boolean;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const abnormal = report.rows.filter((row) => row.flag !== "normal").length;

  return (
    <section className="report-item">
      <button
        className="report-item__head"
        type="button"
        onClick={onToggle}
        aria-expanded={open}
      >
        <span
          className={`report-item__badge report-item__badge--${report.source}`}
        >
          {report.source === "upload" ? "上传识别" : "样例"}
        </span>
        <strong>{report.title}</strong>
        {abnormal > 0 ? (
          <span className="report-item__flag">{abnormal} 项异常</span>
        ) : (
          <span className="report-item__ok">未见异常</span>
        )}
        <small>{formatDate(report.date)}</small>
      </button>

      {open ? (
        <div className="report-item__body">
          <ReportCard
            report={{ title: report.title, rows: report.rows, note: report.note }}
          />
          {report.interpretation ? (
            <div className="report-item__interpretation">
              <strong>解读</strong>
              <p>{report.interpretation}</p>
            </div>
          ) : null}
          <div className="report-item__actions">
            <button type="button" onClick={onDelete}>
              删除记录
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function formatDate(timestamp: number): string {
  const date = new Date(timestamp);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
