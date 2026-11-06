"""应用入口：装配配置、RAG 管线、规则与工具。"""

import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.api.routes_meta import router as meta_router
from app.api.routes_triage import router as triage_router
from app.config import get_settings
from app.llm import get_llm
from app.llm.vision import get_vision_extractor
from app.metrics import MetricsStore
from app.rag.embeddings import get_embedder
from app.rag.pipeline import RAGPipeline
from app.rules.engine import load_rules
from app.tools.health_tools import build_health_tools


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.vector_dir.mkdir(parents=True, exist_ok=True)

    pipeline = RAGPipeline(settings, get_embedder(settings))
    if settings.knowledge_path.exists():
        entries = json.loads(
            settings.knowledge_path.read_text(encoding="utf-8")
        )
        pipeline.load_entries(entries)

    rules = (
        load_rules(settings.triage_rules_path)
        if settings.triage_rules_path.exists()
        else {"symptoms": {}}
    )

    app.state.settings = settings
    app.state.pipeline = pipeline
    app.state.triage_rules = rules
    app.state.health_tools = build_health_tools(pipeline, rules)
    app.state.llm = get_llm(settings)
    app.state.vision = get_vision_extractor(settings)
    app.state.metrics = MetricsStore()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(triage_router)
    app.include_router(meta_router)
    return app


app = create_app()
