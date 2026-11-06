import type { NextConfig } from "next";

// 局域网调试来源从环境变量读取，避免把本机网络信息写进仓库
const devOrigins = (process.env.DEV_ORIGINS ?? "127.0.0.1")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  allowedDevOrigins: devOrigins,
  devIndicators: false,
  cacheComponents: true,
  partialPrefetching: true,
};

export default nextConfig;
