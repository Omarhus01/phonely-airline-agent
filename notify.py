import os

import requests as http
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

app = FastAPI()


class NotificationRequest(BaseModel):
    contact_phone: str = ""
    contact_email: str = ""
    confirmation_number: str
    flight_number: str = ""
    departure_city: str
    arrival_city: str
    travel_date: str
    first_name: str = "Traveler"


def send_email(to: str, req: NotificationRequest):
    body = (
        f"Hello {req.first_name},\n\n"
        f"Your Phonely Air booking is confirmed!\n\n"
        f"Confirmation Number: {req.confirmation_number}\n"
        f"Flight:              {req.flight_number}\n"
        f"From:                {req.departure_city}\n"
        f"To:                  {req.arrival_city}\n"
        f"Date:                {req.travel_date}\n\n"
        f"Thank you for flying with Phonely Air!"
    )
    response = http.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Phonely Air <onboarding@resend.dev>",
            "to": [to],
            "subject": f"Phonely Air Confirmation — {req.confirmation_number}",
            "text": body,
        },
    )
    response.raise_for_status()


@app.post("/notify")
def notify(req: NotificationRequest):
    if req.contact_email:
        try:
            send_email(req.contact_email, req)
            return {"sent": "email", "to": req.contact_email}
        except Exception as e:
            return {"sent": "email_failed", "to": req.contact_email, "error": str(e)}
    if req.contact_phone:
        return {"sent": "sms_pending", "to": req.contact_phone}
    return {"sent": "none", "reason": "no contact info provided"}


@app.get("/")
def health():
    return {"status": "ok"}
