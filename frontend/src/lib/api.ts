import type {
  ChatEvent,
  ChatHistoryItem,
  ReportImagePayload,
  SessionProfile,
} from "./types";

interface StreamChatOptions {
  message: string;
  history: ChatHistoryItem[];
  deepSearch?: boolean;
  profile?: SessionProfile;
  reportImage?: ReportImagePayload | null;
  onEvent: (event: ChatEvent) => void;
  signal?: AbortSignal;
}

export async function streamChat({
  message,
  history,
  deepSearch = false,
  profile,
  reportImage,
  onEvent,
  signal,
}: StreamChatOptions): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history,
        deep_search: deepSearch,
        profile: {
          relation: profile?.relation ?? "self",
          age: profile?.age ? Number(profile.age) : null,
          sex: profile?.sex || null,
          pregnant: profile?.sex === "female" ? profile.pregnant : null,
        },
        report_image: reportImage
          ? { data: reportImage.data, mime: reportImage.mime }
          : null,
      }),
      signal,
    });
  } catch {
    // 网络层失败：后端未启动或正在重启
    throw new Error(
      "无法连接服务：请先在 VS Code 运行「后端 FastAPI (uvicorn)」，等终端出现“启动完成”后再重试"
    );
  }

  if (!response.ok || !response.body) {
    if (response.status >= 500) {
      // 代理/后端 5xx：多数是后端未启动或正在重启
      throw new Error(
        "服务暂时不可用：请确认后端已启动（VS Code 运行「后端 FastAPI (uvicorn)」），等 3 秒再重试"
      );
    }
    // 后端校验失败（422 等）时把具体原因带给用户，便于自助排查
    let detail = "";
    try {
      const data = await response.json();
      detail =
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail ?? data).slice(0, 150);
    } catch {
      // 响应体不是 JSON 时忽略
    }
    throw new Error(
      `请求失败（${response.status}）${detail ? "：" + detail : ""}`
    );
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    let separator = buffer.indexOf("\n\n");
    while (separator !== -1) {
      const frame = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 2);
      dispatchFrame(frame, onEvent);
      separator = buffer.indexOf("\n\n");
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) dispatchFrame(buffer, onEvent);
}

function dispatchFrame(frame: string, onEvent: (event: ChatEvent) => void): void {
  const payload = frame
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trim())
    .join("");

  if (!payload) return;

  try {
    onEvent(JSON.parse(payload) as ChatEvent);
  } catch {
    // 忽略无法解析的帧，不打断整条流
  }
}
