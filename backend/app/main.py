from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import stream
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="AI Teleprompter")

    # This cannot be wildcarded in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(stream.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
