"""
Unit tests for the notify endpoint.
HTTP calls to Resend are mocked so no real emails are sent.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("RESEND_API_KEY", "re_test_key")

from notify import app

client = TestClient(app)

SAMPLE = {
    "confirmation_number": "CONF123456",
    "flight_number": "DL204",
    "departure_city": "JFK",
    "arrival_city": "LAX",
    "travel_date": "2026-06-10",
    "first_name": "Omar",
}


class TestNotifyEndpoint:
    def test_health_check(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @patch("notify.http.post")
    def test_email_route_triggered(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        r = client.post("/notify", json={**SAMPLE, "contact_email": "passenger@example.com"})
        assert r.status_code == 200
        assert r.json()["sent"] == "email"
        assert r.json()["to"] == "passenger@example.com"

    def test_phone_route_detected(self):
        r = client.post("/notify", json={**SAMPLE, "contact_phone": "2125551234"})
        assert r.status_code == 200
        assert r.json()["sent"] == "sms_stub"
        assert r.json()["to"] == "2125551234"

    def test_no_contact_returns_none(self):
        r = client.post("/notify", json=SAMPLE)
        assert r.status_code == 200
        assert r.json()["sent"] == "none"

    @patch("notify.http.post")
    def test_email_takes_priority_over_phone(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        r = client.post("/notify", json={
            **SAMPLE,
            "contact_email": "passenger@example.com",
            "contact_phone": "2125551234",
        })
        assert r.json()["sent"] == "email"

    @patch("notify.http.post")
    def test_resend_api_called_with_correct_fields(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        client.post("/notify", json={**SAMPLE, "contact_email": "passenger@example.com"})

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs["json"]
        assert payload["to"] == ["passenger@example.com"]
        assert SAMPLE["confirmation_number"] in payload["subject"]
