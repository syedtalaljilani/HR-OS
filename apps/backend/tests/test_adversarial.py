"""Regression tests for adversarial-input crashes found in live testing."""
import pytest
from fastapi import HTTPException

from app.services import extraction_service
from app.api.routes import public as public_routes


class TestCorruptCVInputs:
    def test_garbage_pdf_bytes_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            extraction_service.extract_text_from_cv_bytes(b"%PDF-" + b"\x00" * 300, "x.pdf")
        assert exc.value.status_code == 400

    def test_garbage_docx_bytes_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            extraction_service.extract_text_from_cv_bytes(
                b"PK\x03\x04 not a docx" * 10, "x.docx"
            )
        assert exc.value.status_code == 400

    def test_unsupported_suffix_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            extraction_service.extract_text_from_cv_bytes(b"x" * 100, "x.exe")
        assert exc.value.status_code == 400

    def test_valid_txt_still_extracts(self):
        assert extraction_service.extract_text_from_cv_bytes(b"hello cv", "x.txt") == "hello cv"


class TestApplicationDataValidation:
    def test_overlong_name_is_422(self):
        with pytest.raises(HTTPException) as exc:
            public_routes._build_application_data(
                full_name="N" * 501,
                email="ok@ok.ok",
                phone=None,
                address=None,
                expected_salary=None,
                consent="true",
                skills=None,
                education=None,
                experience=None,
                profile_data=None,
            )
        assert exc.value.status_code == 422

    def test_invalid_email_is_422(self):
        with pytest.raises(HTTPException) as exc:
            public_routes._build_application_data(
                full_name="John",
                email="not-an-email",
                phone=None,
                address=None,
                expected_salary=None,
                consent="true",
                skills=None,
                education=None,
                experience=None,
                profile_data=None,
            )
        assert exc.value.status_code == 422

    def test_valid_submission_passes(self):
        data = public_routes._build_application_data(
            full_name="John Doe",
            email="john@doe.io",
            phone="+92 305 6892753",
            address="Multan",
            expected_salary="PKR 30k",
            consent="on",
            skills="Python, FastAPI",
            education=None,
            experience=None,
            profile_data=None,
        )
        assert data.full_name == "John Doe"
        assert data.consent is True
        assert str(data.expected_salary) == "30"