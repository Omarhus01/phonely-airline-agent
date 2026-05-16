import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

app = FastAPI()


class NotificationRequest(BaseModel):
    contact_phone: str = ""
    contact_email: str = ""
    confirmation_number: str
    flight_number: str
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
    msg = MIMEText(body)
    msg["Subject"] = f"Phonely Air Confirmation — {req.confirmation_number}"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)


@app.post("/notify")
def notify(req: NotificationRequest):
    if req.contact_email:
        send_email(req.contact_email, req)
        return {"sent": "email", "to": req.contact_email}
    if req.contact_phone:
        # SMS via Twilio — not configured in this deployment
        # Route is detected; extend with Twilio SDK when A2P registration is complete
        return {"sent": "sms_pending", "to": req.contact_phone}
    return {"sent": "none", "reason": "no contact info provided"}


@app.get("/")
def health():
    return {"status": "ok"}
