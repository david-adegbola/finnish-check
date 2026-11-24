import pytest

import app as app_module


@pytest.fixture
def client(monkeypatch):
    # Tests never call the real API: force mock mode even if a .env with a key exists
    monkeypatch.setenv("LLM_MODE", "mock")
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()
