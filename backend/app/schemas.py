"""API 数据契约。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    # 允许空内容：历史里可能存在失败请求留下的占位消息，仅作上下文
    content: str = Field(default="", max_length=4000)


class SessionProfile(BaseModel):
    """会话级就诊人档案：仅当前会话有效，不落库。"""

    relation: Literal["self", "family"] = "self"
    age: int | None = Field(default=None, ge=0, le=120)
    sex: Literal["male", "female", "other"] | None = None
    pregnant: bool | None = None


ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}


class ReportImage(BaseModel):
    """上传的报告图片：base64 内存传递，不落盘。"""

    data: str = Field(min_length=64, max_length=8_000_000)
    mime: str = "image/jpeg"

    @field_validator("mime")
    @classmethod
    def _normalize_mime(cls, value: str) -> str:
        # 部分手机浏览器会把 JPEG 报成非标准的 image/jpg
        normalized = value.strip().lower()
        if normalized == "image/jpg":
            normalized = "image/jpeg"
        if normalized not in ALLOWED_IMAGE_MIMES:
            raise ValueError("仅支持 JPG / PNG / WebP 格式的图片")
        return normalized

    @field_validator("data")
    @classmethod
    def _strip_data_url(cls, value: str) -> str:
        # 兼容前端误传 data URL
        if value.startswith("data:"):
            _, _, value = value.partition(",")
        return value.strip()


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    deep_search: bool = False
    profile: SessionProfile = Field(default_factory=SessionProfile)
    report_image: ReportImage | None = None
