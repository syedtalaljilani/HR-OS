"""Failure-injection tests: the AI layer must degrade, not crash."""
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import ai.ollama.client as ai_ollama_client  # noqa: E402
from app.services import ai_client, extraction_service  # noqa: E402
from app.evaluation import llm_judges  # noqa: E402


TALAL_PDF = REPO_ROOT / "TalalAIEngineerCV.pdf"


class TestSanitizeSafety:
    def test_structured_content_is_left_untouched(self):
        msg = {"role": "user", "content": [{"type": "text", "text": "hi"}]}
        out = ai_client._sanitize_messages([msg])[0]
        assert out is msg or out["content"] == msg["content"]

    def test_missing_content_untouched(self):
        out = ai_client._sanitize_messages([{"role": "user"}])
        assert "content" not in out[0]


class TestExtractionDegrades:
    def test_llm_down_uses_deterministic_fallback(self):
        def boom(*a, **k):
            raise ai_client.AIUnavailable("ollama down")

        with mock.patch.object(ai_client, "chat_json", side_effect=boom):
            result = extraction_service.extract_profile_from_cv(
                TALAL_PDF.read_bytes(), "cv.pdf"
            )
        assert result["text"]
        assert isinstance(result["profile"], dict)
        assert result["profile"].get("name")
        assert isinstance(result["profile"].get("skills"), list)

    def test_llm_returns_list_uses_fallback(self):
        def liar(*a, **k):
            return [1, 2, 3]  # non-dict result

        with mock.patch.object(ai_client, "chat_json", side_effect=liar):
            result = extraction_service.extract_profile_from_cv(
                TALAL_PDF.read_bytes(), "cv.pdf"
            )
        assert isinstance(result["profile"], dict)
        assert result["profile"].get("name")


class TestScreeningDegrades:
    def test_graph_survives_total_llm_failure(self):
        from app.db.models.application import Application
        from app.db.session import SessionLocal
        from app.services.langgraph_screening_service import screen_application

        def boom(*a, **k):
            raise ai_ollama_client.AIUnavailable("ollama down")

        with SessionLocal() as db:
            app_row = (
                db.query(Application)
                .filter(Application.id == "8f778a4c-af3e-4072-a69f-1500d520147c")
                .first()
            )
            if app_row is None:
                pytest.skip("Talal test application not present in DB")
            with mock.patch.object(
                ai_ollama_client, "chat_json", side_effect=boom
            ):
                result = screen_application(db, app_row)
        assert result is not None
        assert result.score is not None

    def test_graph_copes_with_garbage_json_shapes(self):
        from app.db.models.application import Application
        from app.db.session import SessionLocal
        from app.services.langgraph_screening_service import screen_application

        def gremlin(*a, **k):
            return {"requirements": 42, "status": "NOT-REAL"}

        with SessionLocal() as db:
            app_row = (
                db.query(Application)
                .filter(Application.id == "8f778a4c-af3e-4072-a69f-1500d520147c")
                .first()
            )
            if app_row is None:
                pytest.skip("Talal test application not present in DB")
            with mock.patch.object(
                ai_ollama_client, "chat_json", side_effect=gremlin
            ):
                result = screen_application(db, app_row)
        assert result is not None
        assert result.score is not None


class TestJudgesDegrade:
    def test_judge_survives_ollama_failure(self):
        import urllib.error

        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            out = llm_judges.judge_extraction("some cv text that is long enough", {"name": "X"})
        assert "extraction_faithfulness" in out
        assert out["extraction_faithfulness"]["value"] is None
        assert out["extraction_faithfulness"]["skipped"] if "skipped" in out["extraction_faithfulness"] else True

    def test_judge_handles_non_json_llm_response(self):
        fake_body = {"message": {"content": "sorry no json here"}}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                import json
                return json.dumps(fake_body).encode()

        with mock.patch("urllib.request.urlopen", return_value=FakeResp()):
            out = llm_judges.judge_screening([{"requirement": "r", "status": "MATCH"}], {"score": 100})
        assert out["screening_soundness"]["value"] is None