from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Read once at boot from POCKET_* variables (and .env). A wrong value stops the process before
    the first request instead of failing the first chat.
    """

    model_config = SettingsConfigDict(env_prefix='POCKET_', env_file='.env', extra='ignore')

    environment: Literal['development', 'test', 'production'] = 'development'
    # The web app's origin — the only one CORS allows (credentials are never sent cross-origin).
    web_origin: str = 'http://localhost:4100'

    # fake: canned streamed replies (tests, UI work). llamacpp: the local GGUF model (C5).
    # openrouter: a hosted model behind the same interface (C6).
    provider: Literal['fake', 'llamacpp', 'openrouter'] = 'fake'
    llamacpp_url: str = 'http://127.0.0.1:8080'
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = ''

    # Said to the model before every conversation. The language rule is the product's promise.
    system_prompt: str = (
        "You are PocketGPT, a helpful assistant running on the user's own computer. "
        "Always answer in the language of the user's last message (English, Russian or Uzbek). "
        'Be concise. If you do not know, say so.'
    )
    # The model's context window, in tokens. Older messages are dropped to fit it (C6).
    context_tokens: int = Field(default=4096, ge=512, le=131072)
    # SQLite file for conversations; ':memory:' in tests.
    db_path: str = 'data/pocket.db'

    # Generation limits shared by every provider.
    max_new_tokens: int = Field(default=512, ge=16, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
