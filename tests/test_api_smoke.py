from src.api.main import app


def test_fastapi_app_exists():
    assert app.title == "HireFlow API"
