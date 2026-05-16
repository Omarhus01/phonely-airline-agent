# Phonely Air — Voice Booking Agent

> A fully voice-driven airline booking assistant built on Phonely. Callers can search flights,
> book a seat, and receive a confirmation — entirely over a phone call, with no app or website.

**Phone Number:** +1 814 637 8506

**GitHub:** https://github.com/Omarhus01/phonely-airline-agent

**Demo Video:** *(link added after recording)*

---

## What This Project Is

This is a voice AI agent built for Phonely as part of a software engineering internship
assessment. The task was to build a working voice assistant for an airline company that handles
the full booking flow — flight search, passenger details, booking confirmation, and post-call
notification — using a live AWS API, Phonely's call flow builder, and a custom Python
notification service.

The agent is not a chatbot. It is a real phone number you can call. It uses a structured
conversation flow, live API calls during the call, and a knowledge base for policy questions.
The goal was to make it feel like calling an airline's automated phone system, but smarter.

---

## System Architecture

```
Caller
  │
  ▼
Phonely Voice Agent
  │
  ├── Guidelines (system prompt: IATA table, date rules, error handling, conversation order)
  ├── Knowledge Base (airline_policies.txt — RAG for policy questions)
  │
  └── Call Flow (10 nodes)
        │
        ├── Greeting Message
        ├── Answer business questions  ←── Knowledge Base (RAG)
        ├── Collect trip details        (departure city, destination city, travel date)
        ├── Search flights API  ────────── GET /airline-assessment?src=&dst=&date=
        ├── Present flights and select  (reads API response aloud, caller picks)
        ├── Collect passenger details   (first name, last name, email or phone)
        ├── Book flight API  ───────────── POST /airline-assessment (flightId, passenger, date)
        ├── Read confirmation           (spells out confirmation number)
        ├── Send notification API  ──────── POST notify.py (confirmation email to passenger)
        ├── Read confirmation           (spells out confirmation number)
        └── End Call
              │
              └── Post-call: Phonely Email Notification
                    └── Conversation summary → omaribra@uni.minerva.edu (operator log)
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Voice platform | Phonely |
| Flight API | AWS Lambda (pre-built, provided by assessment) |
| Notification service | FastAPI + Gmail SMTP (Python, deployed on Render) |
| Knowledge base | Phonely RAG (airline_policies.txt) |
| Airport resolution | Phonely Guidelines (IATA lookup table, no code) |

---

## Features

- **IATA resolution** — caller says "Los Angeles to New York", agent converts to LAX → JFK
- **Live flight search** — real GET request during the call, results read aloud
- **Flight selection** — caller picks by option number, agent stores the flight ID
- **Passenger collection** — first name, last name, email or phone collected in sequence
- **Live booking** — real POST request during the call, confirmation number returned
- **Confirmation read-back** — number spelled out character by character for voice clarity
- **Policy Q&A** — knowledge base answers questions about refunds, baggage, changes
- **Transfer to support** — caller can request a human agent at any point in the flow
- **Email confirmation** — formatted booking confirmation sent to passenger after call
- **Error handling** — unknown cities, invalid dates, no flights found, all handled gracefully

---

## Call Flow Walkthrough

```
Agent:  "Thank you for calling Phonely Air. What city are you departing from?"
Caller: "New York"
Agent:  "Got it, New York. And where are you flying to?"
Caller: "Los Angeles"
Agent:  "What date would you like to travel?"
Caller: "June 10th 2026"
Agent:  "I found 3 flights from JFK to LAX on June 10th.
         Option 1: Delta flight DL204, departs 6 AM, arrives 9 AM, $189.
         Option 2: United flight UA881, departs 10 AM, arrives 1 PM, $215.
         Option 3: American flight AA302, departs 3 PM, arrives 6 PM, $175.
         Which option would you prefer?"
Caller: "Option 3"
Agent:  "Great choice. What is your first name?"
Caller: "Omar"
Agent:  "And your last name?"
Caller: "Ibrahim"
Agent:  "Would you like your confirmation sent to an email address or phone number?"
Caller: "omaribra@uni.minerva.edu"
Agent:  "Booking your flight now... Your booking is confirmed.
         Your confirmation number is C-O-N-F-4-2-2-8-6-7.
         A confirmation has been sent to your email. Safe travels, Omar!"
```

---

## Test Cases

These are the scenarios verified during development. The AWS API is live and
can be called independently to validate behavior outside of a phone call.

| # | Scenario | Input | Expected Behavior |
|---|---|---|---|
| 1 | Happy path — email confirmation | JFK → LAX, valid date, email | Full booking, confirmation number, email sent |
| 2 | City name resolution | "New York" → "Los Angeles" | Converted to JFK → LAX without error |
| 3 | Alternate city names | "NYC" → "LA" | Same as above |
| 4 | No flights available | AAL → YVR | Agent says no flights found, offers different date |
| 5 | Invalid date — past | Yesterday's date | Agent asks for a valid date |
| 6 | Invalid date — too far | More than 1 year from now | Agent asks for a date within one year |
| 7 | Unknown city | "Springfield" | Agent asks caller to try a nearby major city |
| 8 | Policy question — refund | "What's your cancellation policy?" | Knowledge base answers from airline_policies.txt |
| 9 | Policy question — baggage | "How much does a checked bag cost?" | Correct fee from knowledge base |
| 10 | Transfer request mid-call | "I want to speak to a human" | Agent triggers transfer immediately |
| 11 | Phone contact | Caller gives phone number instead of email | Routing detected, SMS path acknowledged |

---

## Python Tests

The `tests/` directory contains integration tests that verify the AWS API directly,
independent of the voice platform.

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

Tests cover: flight search (happy path, no-flights case), booking (valid POST, response
contains confirmationNumber), and the notify endpoint (email routing, phone routing,
missing contact fallback).

---

## Limitations

**SMS not active** — Twilio's A2P 10DLC registration (required for US local numbers) takes
days to weeks to be approved. The notify.py script detects phone numbers and has the routing
logic in place, but the SMS send is not executed in the current deployment. Email confirmation
works fully.

**Cities are limited** — Only the 25 cities in the IATA table (airports.json) are supported.
Cities outside that list return an "airport not found" response from the agent. Extending
support requires adding entries to the table in Phonely's Guidelines.

**Trial account restrictions** — The Phonely account is on a free trial. Call duration and
concurrent call limits apply. The agent may not be reachable if the trial expires.

**No booking modification** — The API supports search and booking only. There is no endpoint
to cancel, change, or look up existing bookings by confirmation number. The agent directs
those requests to customer support.

**Voice-only interface** — There is no web UI or app. All interaction happens over a phone
call. This is intentional — the goal was to build a voice-first experience, not a chatbot.

---

## What I Learned

This project introduced me to building AI systems that operate over a live phone call, which
is different from building a chatbot or a web app in ways I did not expect. The constraints
are stricter — no markdown, no UI, no retry button, responses have to be short or the caller
loses track — and errors are harder to catch because you only see them after a real call.

The most interesting challenge was that Phonely variables are only substituted during real
calls. In testing, you have to hardcode values manually. This forced me to think carefully
about what the agent actually does at runtime versus what the test configuration shows, which
is a useful habit for any production system.

The project also applied concepts from the CodePath AI110 course directly: the agentic loop
(plan the route → call the search API → present options → act on the selection → verify the
booking), RAG via the knowledge base, tool use via the API Request nodes, and guardrails via
the Guidelines (never make up flights, never accept invalid dates, never confirm without a
real confirmation number from the API).
