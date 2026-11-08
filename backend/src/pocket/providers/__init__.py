from pocket.core.config import Settings
from pocket.providers.base import ChatProvider, Message
from pocket.providers.fake import FakeProvider
from pocket.providers.openai_compat import OpenAICompatProvider

__all__ = ['ChatProvider', 'Message', 'create_provider']


def create_provider(settings: Settings) -> ChatProvider:
    """The one place that turns POCKET_PROVIDER into an object. A missing key → boot fails."""
    if settings.provider == 'fake':
        return FakeProvider()
    if settings.provider == 'llamacpp':
        return OpenAICompatProvider('llamacpp', settings.llamacpp_url)
    key = settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else ''
    if not key or not settings.openrouter_model:
        raise RuntimeError('openrouter needs POCKET_OPENROUTER_API_KEY and POCKET_OPENROUTER_MODEL')
    return OpenAICompatProvider(
        'openrouter', 'https://openrouter.ai/api', settings.openrouter_model, api_key=key
    )
