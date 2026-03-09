from fastapi.testclient import TestClient
from src.main import app
import json

client = TestClient(app)

def test_start_typing_test():
    response = client.post("/start_typing_test", json={"text": "The quick brown fox jumps over the lazy dog."})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "wpm" in data
    assert isinstance(data["wpm"], float)