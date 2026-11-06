/**
 * 同源 API 代理：把 /api/* 转发到 FastAPI。
 *
 * 用路由处理器而不是 next.config rewrites，是为了让 SSE 真正流式透传
 * （rewrites 代理会缓冲事件流，前端会变成"最后一次性到达"）。
 */

const BACKEND = process.env.API_BACKEND ?? "http://127.0.0.1:8000";

async function proxy(
  request: Request,
  context: { params: Promise<{ path: string[] }> }
): Promise<Response> {
  const { path } = await context.params;
  const url = new URL(request.url);
  const target = `${BACKEND}/api/${path.join("/")}${url.search}`;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const accept = request.headers.get("accept");
  if (accept) headers.set("accept", accept);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  const upstreamType = upstream.headers.get("content-type");
  if (upstreamType) responseHeaders.set("content-type", upstreamType);
  responseHeaders.set("cache-control", "no-cache, no-transform");
  if (upstreamType?.includes("text/event-stream")) {
    responseHeaders.set("x-accel-buffering", "no");
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
