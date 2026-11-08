from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pocket import __version__
from pocket.api import chat, conversations, health
from pocket.core.config import Settings, get_settings
from pocket.providers import ChatProvider, create_provider
from pocket.store import Store


def create_app(settings: Settings | None = None, provider: ChatProvider | None = None) -> FastAPI:
    """App factory: tests build their own app (settings, provider); importing connects nothing."""
    settings = settings or get_settings()
    app = FastAPI(
        title='PocketGPT',
        version=__version__,
        docs_url=None if settings.environment == 'production' else '/docs',
        openapi_url=None if settings.environment == 'production' else '/openapi.json',
    )
    app.state.settings = settings
    app.state.provider = provider or create_provider(settings)
    app.state.store = Store(settings.db_path)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=['GET', 'POST', 'DELETE'],
        allow_headers=['Content-Type'],
    )
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    return app


def run() -> None:
    import uvicorn

    uvicorn.run('pocket.main:create_app', factory=True, host='127.0.0.1', port=8200)
