from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.trials import router as trials_router
from app.config import settings
from app.database.session import engine
from app.vector_db.client import get_qdrant
from app.vector_db.setup import ensure_collection


def setup_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer()
            if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    logger = structlog.get_logger()

    try:
        async with get_qdrant() as qdrant_client:
            await ensure_collection(qdrant_client)
            logger.info("qdrant_collection_ensured")
    except Exception as exc:
        logger.warning("qdrant_setup_failed_continue_startup", error=str(exc))

    logger.info("app_started", app_name=settings.app_name)
    yield
    await engine.dispose()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(trials_router)
    app.include_router(documents_router)
    app.include_router(chat_router)

    return app


app = create_app()
