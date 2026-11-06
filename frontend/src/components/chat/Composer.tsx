"use client";

import { useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";

import { Icon } from "@/components/ui/Icon";
import type { ReportImagePayload } from "@/lib/types";

interface ComposerProps {
  onSend: (
    text: string,
    deepSearch: boolean,
    reportImage: ReportImagePayload | null
  ) => void;
  isStreaming: boolean;
}

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

export function Composer({ onSend, isStreaming }: ComposerProps) {
  const [text, setText] = useState("");
  const [deepSearch, setDeepSearch] = useState(false);
  const [image, setImage] = useState<ReportImagePayload | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    // 部分手机浏览器会把 JPEG 报成非标准的 image/jpg，这里归一化
    let mime = file.type.toLowerCase();
    if (mime === "image/jpg") mime = "image/jpeg";
    if (!["image/jpeg", "image/png", "image/webp"].includes(mime)) {
      window.alert("请使用 JPG / PNG / WebP 格式的图片（iPhone 请先截图或转存为 JPG）");
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      window.alert("图片太大，请控制在 5MB 以内");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result ?? "");
      const base64 = result.includes(",")
        ? result.slice(result.indexOf(",") + 1)
        : result;
      setImage({ data: base64, mime, name: file.name });
    };
    reader.readAsDataURL(file);
  };

  const send = () => {
    const value = text.trim();
    if ((!value && !image) || isStreaming) return;
    onSend(value, deepSearch, image);
    setText("");
    setImage(null);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      send();
    }
  };

  return (
    <div className="composer-wrap">
      <div className="composer">
        <div className="composer__top">
          <label className="deep-toggle">
            <input
              type="checkbox"
              checked={deepSearch}
              onChange={(event) => setDeepSearch(event.target.checked)}
            />
            <span>深度搜索</span>
          </label>
        </div>

        {image ? (
          <div className="composer__image">
            <Icon name="doc" />
            <span>{image.name}</span>
            <button
              type="button"
              onClick={() => setImage(null)}
              aria-label="移除图片"
            >
              ×
            </button>
          </div>
        ) : null}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hidden
          onChange={selectFile}
        />

        <div className="composer__row">
          <button
            className="composer__attach"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            aria-label="上传报告图片"
            disabled={isStreaming}
          >
            <Icon name="paperclip" />
          </button>

          <textarea
            id="input"
            rows={1}
            placeholder={image ? "补充说明（可留空），发送后开始识别…" : "描述症状或健康问题…"}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={handleKeyDown}
          />

          <button
            className="composer__send"
            type="button"
            onClick={send}
            aria-label="发送"
            disabled={isStreaming || (!text.trim() && !image)}
          >
            <Icon name="send" />
          </button>
        </div>
      </div>
    </div>
  );
}
