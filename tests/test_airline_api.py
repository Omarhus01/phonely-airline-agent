"""
Integration tests for the AWS airline API.
These hit the real endpoint — no mocks.
"""

import requests
import pytest
from datetime import date, timedelta

BASE_URL = "https://zz1mpoguje.execute-api.us-east-1.amazonaws.com/default/airline-assessment"
VALID_DATE = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")


class TestFlightSearch:
    def test_happy_path_returns_flights(self):
        r = requests.get(BASE_URL, params={"src": "JFK", "dst": "LAX", "date": VALID_DATE})
        assert r.status_code == 200
        flights = r.json()["flights"]
        assert isinstance(flights, list)
        assert len(flights) > 0

    def test_each_flight_has_required_fields(self):
        r = requests.get(BASE_URL, params={"src": "JFK", "dst": "LAX", "date": VALID_DATE})
        for flight in r.json()["flights"]:
            assert "flightId" in flight
            assert "airline" in flight
            assert "flightNumber" in flight
            assert "departureTime" in flight
            assert "arrivalTime" in flight
            assert "durationMinutes" in flight
            assert "stops" in flight
            assert "price" in flight

    def test_no_flights_aal_to_yvr(self):
        r = requests.get(BASE_URL, params={"src": "AAL", "dst": "YVR", "date": VALID_DATE})
        # API returns 404 with an empty flights array for unsupported routes
        assert r.status_code == 404
        assert r.json()["flights"] == []

    def test_past_date_rejected(self):
        past = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        r = requests.get(BASE_URL, params={"src": "JFK", "dst": "LAX", "date": past})
        assert r.status_code == 400
        assert "error" in r.json()

    def test_date_beyond_one_year_rejected(self):
        far = (date.today() + timedelta(days=400)).strftime("%Y-%m-%d")
        r = requests.get(BASE_URL, params={"src": "JFK", "dst": "LAX", "date": far})
        assert r.status_code == 400
        assert "error" in r.json()

    def test_different_valid_routes(self):
        routes = [("SFO", "ORD"), ("MIA", "SEA"), ("DEN", "BOS")]
        for src, dst in routes:
            r = requests.get(BASE_URL, params={"src": src, "dst": dst, "date": VALID_DATE})
            assert r.status_code == 200
            assert len(r.json()["flights"]) > 0


class TestFlightBooking:
    def _get_first_flight_id(self):
        r = requests.get(BASE_URL, params={"src": "JFK", "dst": "LAX", "date": VALID_DATE})
        return r.json()["flights"][0]["flightId"]

    def test_booking_returns_confirmation_number(self):
        flight_id = self._get_first_flight_id()
        r = requests.post(BASE_URL, json={
            "flightId": flight_id,
            "passenger": {"firstName": "Test", "lastName": "User"},
            "date": VALID_DATE,
        })
        assert r.status_code == 200
        data = r.json()
        assert "confirmationNumber" in data
        assert data["confirmationNumber"].startswith("CONF")

    def test_confirmation_number_format(self):
        flight_id = self._get_first_flight_id()
        r = requests.post(BASE_URL, json={
            "flightId": flight_id,
            "passenger": {"firstName": "Omar", "lastName": "Ibrahim"},
            "date": VALID_DATE,
        })
        conf = r.json()["confirmationNumber"]
        assert len(conf) > 4
        assert conf[:4] == "CONF"

    def test_invalid_flight_id_still_returns_confirmation(self):
        # The API does not validate flightId — any value returns a confirmation.
        # This means flight ID integrity is the caller's responsibility.
        r = requests.post(BASE_URL, json={
            "flightId": "invalid-flight-id-000000000000000",
            "passenger": {"firstName": "Test", "lastName": "User"},
            "date": VALID_DATE,
        })
        assert r.status_code == 200
        assert "confirmationNumber" in r.json()
