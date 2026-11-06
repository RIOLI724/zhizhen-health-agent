"""应用配置：环境变量 / .env 覆盖，默认零外部依赖。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "智诊 Agent"

    # ---- LLM ----
    llm_provider: str = "mock"
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    llm_api_key: str = ""
    llm_model: str = "glm-4-flash"
    llm_temperature: float = 0.4

    # ---- 视觉（报告图片识别，GLM-4.6V-Flash 免费档）----
    vision_model: str = "glm-4.6v-flash"

    # ---- Embedding ----
    embedding_provider: str = "local_bge"
    embedding_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    embedding_api_key: str = ""
    embedding_model: str = "embedding-3"
    local_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    mock_embedding_dim: int = 256

    # ---- RAG ----
    top_k: int = 4
    retrieval_min_score: float = 0.05
    hybrid_search: bool = True
    rrf_k: int = 60

    # ---- 数据 ----
    data_dir: Path = BASE_DIR / "data"
    knowledge_path: Path = BASE_DIR / "data" / "knowledge" / "entries.json"
    triage_rules_path: Path = BASE_DIR / "data" / "rules" / "triage_rules.json"

    # ---- CORS ----
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @property
    def vector_dir(self) -> Path:
        return self.data_dir / "vector"

@lru_cache
def get_settings() -> Settings:
    return Settings()
