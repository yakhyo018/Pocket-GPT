import pytest
from fastapi.testclient import TestClient

from pocket.core.config import Settings
from pocket.main import create_app
from pocket.providers.fake import FakeProvider


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, environment='test', provider='fake', db_path=':memory:')


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, FakeProvider(delay=0)))
