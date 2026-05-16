"""
Unit tests for the notify endpoint.
SMTP is mocked so no real emails are sent.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("GMAIL_USER", "test@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "testpassword")

from notify import app

client = TestClient(app)

SAMPLE = {
    "confirmation_number": "CONF123456",
    "flight_number": "DL204",
    "departure_city": "New York",
    "arrival_city": "Los Angeles",
    "travel_date": "2026-06-10",
    "first_name": "Omar",
}


class TestNotifyEndpoint:
    def test_health_check(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @patch("notify.smtplib.SMTP_SSL")
    def test_email_route_triggered(self, mock_smtp):
        mock_smtp.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post("/notify", json={**SAMPLE, "contact_email": "passenger@example.com"})
        assert r.status_code == 200
        assert r.json()["sent"] == "email"
        assert r.json()["to"] == "passenger@example.com"

    def test_phone_route_detected(self):
        r = client.post("/notify", json={**SAMPLE, "contact_phone": "2125551234"})
        assert r.status_code == 200
        assert r.json()["sent"] == "sms_pending"
        assert r.json()["to"] == "2125551234"

    def test_no_contact_returns_none(self):
        r = client.post("/notify", json=SAMPLE)
        assert r.status_code == 200
        assert r.json()["sent"] == "none"

    @patch("notify.smtplib.SMTP_SSL")
    def test_email_takes_priority_over_phone(self, mock_smtp):
        mock_smtp.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        r = client.post("/notify", json={
            **SAMPLE,
            "contact_email": "passenger@example.com",
            "contact_phone": "2125551234",
        })
        assert r.json()["sent"] == "email"
