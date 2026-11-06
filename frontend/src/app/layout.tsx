import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "智诊 · AI 健康助手",
  description: "会查指南、会读报告的健康 Agent（演示版）",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        {/* eslint-disable-next-line @next/next/no-page-custom-font -- 字体由 Google Fonts CDN 提供，保持冻结视觉，不改为 next/font */}
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=Noto+Serif+SC:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="agent-body">{children}</body>
    </html>
  );
}
