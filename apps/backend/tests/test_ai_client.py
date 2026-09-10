import json
import urllib.error
import urllib.request

import pytest

from app.services import ai_client
from app.services.ai_client import AIUnavailable


class _FakeResponse:
    def __init__(self, body: dict):
        self._raw = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._raw


class TestChatJson:
    def test_returns_parsed_json(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            assert req.full_url.startswith("http://localhost:11434/api/chat")
            captured = json.loads(req.data)
            assert captured["format"] == "json"
            assert captured["options"]["temperature"] == 0.1
            return _FakeResponse({"message": {"content": '{"ok": true}'}})

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        assert ai_client.chat_json([{"role": "user", "content": "hi"}]) == {"ok": True}

    def test_temperature_override(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            captured = json.loads(req.data)
            assert captured["options"]["temperature"] == 0.0
            return _FakeResponse({"message": {"content": '{"ok": true}'}})

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        ai_client.chat_json([{"role": "user", "content": "hi"}], temperature=0.0)

    def test_network_error_raises_unavailable(self, monkeypatch):
        def boom(req, timeout=None):
            raise urllib.error.URLError("down")

        monkeypatch.setattr(urllib.request, "urlopen", boom)
        with pytest.raises(AIUnavailable):
            ai_client.chat_json([{"role": "user", "content": "hi"}])

    def test_bad_json_raises_unavailable(self, monkeypatch):
        monkeypatch.setattr(
            urllib.request, "urlopen",
            lambda req, timeout=None: _FakeResponse(
                {"message": {"content": "not json"}}
            ),
        )
        with pytest.raises(AIUnavailable):
            ai_client.chat_json([{"role": "user", "content": "hi"}])

    def test_empty_images_raises_unavailable(self):
        with pytest.raises(AIUnavailable):
            ai_client.ocr_images([])


class TestOcrImages:
    def test_sends_all_images_single_request(self, monkeypatch):
        captured = {}

        def fake_urlopen(req, timeout=None):
            payload = json.loads(req.data)
            captured["images"] = payload["messages"][0]["images"]
            captured["model"] = payload["model"]
            captured["temperature"] = payload["options"]["temperature"]
            return _FakeResponse(
                {"message": {"content": "Extracted CV text."}}
            )

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        text = ai_client.ocr_images(["aGVsbG8=", "d29ybGQ="], model="deepseek-ocr")
        assert text == "Extracted CV text."
        assert captured["images"] == ["aGVsbG8=", "d29ybGQ="]
        assert captured["model"] == "deepseek-ocr"
        assert captured["temperature"] == 0.0

    def test_network_error_raises_unavailable(self, monkeypatch):
        def boom(req, timeout=None):
            raise TimeoutError("slow")

        monkeypatch.setattr(urllib.request, "urlopen", boom)
        with pytest.raises(AIUnavailable):
            ai_client.ocr_images(["aGVsbG8="])