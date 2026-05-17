# Phonely Air — Voice Booking Agent

> A fully voice-driven airline booking assistant built on Phonely. Callers can search flights,
> book a seat, and receive a confirmation — entirely over a phone call, with no app or website.

**Phone Number:** +1 878 777 5033

**GitHub:** https://github.com/Omarhus01/phonely-airline-agent

**Demo Video:** *(link added after recording)*

---

## What This Project Is

This is a voice AI agent built for Phonely as part of a software engineering internship
assessment. The task was to build a working voice assistant for an airline that handles the
full booking flow — flight search, passenger details, booking confirmation, and post-call
notification — using a live AWS API, Phonely's call flow builder, and a custom Python
notification service deployed on Render.

The agent is not a chatbot. It is a real phone number you can call. It uses a structured
21-node conversation flow, live API calls during the call, and a knowledge base for policy
questions.

---

## System Architecture

```
Caller
  │
  ▼
Phonely Voice Agent  (phonely.ai — flow + LLM + telephony)
  │
  ├── system_prompt.txt    → Guidelines node (IATA table, date rules, guardrails)
  ├── airline_policies.txt → Knowledge Base node (RAG for policy Q&A)
  │
  └── 21-node Call Flow
        │
        ├── [Talk]      Greeting Message
        ├── [Talk+KB]   Answer business questions      ←── airline_policies.txt
        ├── [Talk]      Collect trip details
        ├── [Code]      Convert city and date          (city names → IATA, natural date → ISO)
        ├── [Code]      Validate inputs                (explicit bool; Phonely exists = true for "")
        ├── [Filter]    Check valid inputs             → Search flights | Collect missing trip detail
        ├── [Talk]      Collect missing trip detail    (loops back to Convert city and date)
        ├── [API GET]   Search flights API             ←── AWS Lambda /airline-assessment
        ├── [Code]      Compute has flights            (explicit bool; Phonely array operator broken)
        ├── [Filter]    Check flights found            → Present flights | No flights found
        ├── [Talk]      No flights found               (retry → Collect trip details | end)
        ├── [Talk]      Present flights and select     (reads @flights array, captures flight number)
        ├── [Talk]      Collect passenger details      (first, last, email or phone)
        ├── [Code]      Resolve flightId               (flight number → 32-char hex, deterministic)
        ├── [API POST]  Book flight API                ←── AWS Lambda /airline-assessment
        ├── [Filter]    Check booking succeeded        → Send notification | Booking error
        ├── [API POST]  Send notification              ←── notify.py on Render
        ├── [Talk]      Read confirmation              (spells out confirmation number)
        ├── [Talk]      End Call
        ├── [Talk]      Booking error
        └── [Transfer]  Transfer to support            (reachable from 4 nodes via transfer_requested)

Post-call (Phonely-managed, fires after every call ends — outside the main 21-node flow):
  └── [Post-call]  Email & SMS Notification   Phonely sends a pre-configured summary to the
                                              operator email (omaribra@uni.minerva.edu).
                                              This is NOT the same as the Send notification
                                              API node above — that one sends the passenger
                                              confirmation during the call via notify.py.
```

> **Note:** The Phonely call flow exists only in the Phonely dashboard. There is no JSON
> export of the flow in this repo. To inspect or modify the flow, log into the Phonely account
> and open the "Airline Booking AI Agent" project.

**External services**

| Service | Role |
|---|---|
| Phonely | Voice agent platform (flow + LLM + telephony) |
| AWS Lambda | Flight search (GET) and booking (POST) — provided by assessment |
| Render | Hosts `notify.py` at `https://phonely-airline-agent.onrender.com` |
| Resend | Email delivery (HTTP API, sandbox sender `onboarding@resend.dev`) |

---

## Files in This Repo

| File | Description |
|---|---|
| `notify.py` | FastAPI server. Exposes `/notify` (POST) for email via Resend and stubbed SMS. Exposes `/` (GET) health check. Deployed on Render. |
| `airline_policies.txt` | Knowledge base content uploaded to Phonely. Used by the *Answer business questions* node for RAG. Covers cancellation, baggage, seat selection, special assistance, and support transfer. |
| `system_prompt.txt` | Agent guidelines: IATA lookup table (~25 cities), date validation rules, conversation order, guardrails, and out-of-scope rebuttals. |
| `airports.json` | Reference-only. Not consumed at runtime. The actual IATA mapping is the `IATA_TABLE` dict embedded directly inside the Phonely *Convert city and date* Code node. This file was consulted when writing that dict and exists for human reference only. |
| `tests/test_airline_api.py` | Integration tests hitting the live AWS Lambda endpoint — no mocks. Covers happy path, no-flights route, past/future date rejection, booking format. |
| `tests/test_notify.py` | Unit tests for the notify endpoint. Resend HTTP calls are mocked. Covers email routing, SMS stub routing, priority (email over phone), and missing contact fallback. |
| `requirements.txt` | Python dependencies for `notify.py` and the test suite. |
| `.env.example` | Documents required environment variables. Copy to `.env` for local development. |

---

## Phonely Flow — Node-by-Node Detail

### Code nodes (run inside Phonely sandbox)

**Convert city and date** — reads `arg1` (departure city), `arg2` (destination city), `arg3`
(travel date). Returns `departure_iata`, `destination_iata`, `travel_date` (ISO). Includes an
`IATA_TABLE` dict mapping ~25 city names and aliases to codes. Date parsing avoids
`datetime.strptime` (blocked in Phonely sandbox) by manually slicing with `int()`. Validates
that the date is today or within one year; returns `""` for anything out of range.

**Validate inputs** — returns `{"is_valid": bool}` checking that all three output fields from
Convert city and date are non-empty strings. Necessary because Phonely's built-in `exists`
filter operator evaluates `""` (empty string) as truthy.

**Compute has flights** — reads `arg1` (the `flights` array from the AWS API response, which
Phonely sometimes passes as a JSON string). Parses if needed, returns `{"has_flights": bool}`.
Necessary because Phonely's *is an array containing `flightId`* operator returned `false` for
arrays of objects with a `flightId` key (it checks for the literal string, not the key name).

**Resolve flightId** — reads `arg1` (selected flight number like `"AA697"`) and `arg2` (the
flights array). Walks the array to find the matching object and returns `selected_flight_id`
(32-char hex), `matched_airline`, and `matched_price`. Handles the array arriving as either a
list or JSON string. This node exists because the LLM consistently failed to store the 32-char
hex flightId reliably even when it correctly identified the flight in conversation — capturing
only the short flight number via LLM and resolving deterministically eliminated that failure mode.

### Filter nodes

All Filter V2 nodes branch on a Code-node-computed `bool` field using *is equal to True
(Boolean)* — not on raw API response fields or variable existence. This was required after
discovering that Phonely's `exists` and array operators produce incorrect results for empty
strings and arrays of objects respectively.

### Transfer to support

A single *Cold Transfer* node is wired as the destination for `transfer_requested` exit
conditions on four nodes: *Answer business questions*, *Collect trip details*, *Present flights
and select*, and *Collect passenger details*.

---

## Requirements Coverage

| # | Requirement | Status | Implementation |
|---|---|---|---|
| 1 | Resolve city/airport names to IATA | ✅ | Convert city and date Code node |
| 2 | Check flight availability + present options | ✅ | Search flights API + Present flights and select |
| 3 | Collect passenger details (name + contact) | ✅ | Collect passenger details Talk node |
| 4 | Confirm booking + confirmation number | ✅ | Book flight API + Read confirmation |
| 5 | Send confirmation — Email | ✅ | `notify.py` via Resend HTTP API |
| 5 | Send confirmation — SMS for US phones | ⚠️ | Stubbed in `notify.py` (see Limitations) |
| 6 | Unknown city/airport | ✅ | Validate inputs + Collect missing trip detail loop |
| 6 | Invalid date (past or beyond 1 year) | ✅ | `to_date()` in Convert city and date returns `""` |
| 6 | No flights available (e.g. AAL → YVR) | ✅ | Compute has flights + No flights found node |
| 6 | Transfer to support | ✅ | `transfer_requested` exit on 4 nodes → Transfer node |
| 6 | Knowledge base for policies | ✅ | `airline_policies.txt` uploaded, RAG in Answer business questions |

---

## Setup

**Clone and install**

```bash
git clone https://github.com/Omarhus01/phonely-airline-agent.git
cd phonely-airline-agent
pip install -r requirements.txt
```

**Environment variables**

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `RESEND_API_KEY` | API key from resend.com. Required for email delivery in `notify.py`. |

---

## Running Locally

```bash
uvicorn notify:app --reload
```

The server starts at `http://localhost:8000`. The `/notify` endpoint is available at
`http://localhost:8000/notify` and the health check at `http://localhost:8000/`.

**Test the endpoint manually:**

```bash
curl -X POST http://localhost:8000/notify \
  -H "Content-Type: application/json" \
  -d '{
    "contact_email": "you@example.com",
    "confirmation_number": "CONF123456",
    "flight_number": "DL204",
    "departure_city": "JFK",
    "arrival_city": "LAX",
    "travel_date": "2026-06-10",
    "first_name": "Omar"
  }'
```

## Production (Render)

The service is deployed at `https://phonely-airline-agent.onrender.com`. Render reads
`RESEND_API_KEY` from its environment variable dashboard. The start command is:

```
uvicorn notify:app --host 0.0.0.0 --port $PORT
```

Render is configured to auto-deploy on every push to the `main` branch.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

**`tests/test_notify.py`** — unit tests, no network calls. Mocks `notify.http.post` (the
Resend HTTP call) so no real emails are sent. Requires no env vars set (defaults to a dummy
key). Covers: health check, email routing, SMS stub routing, email-over-phone priority,
Resend payload shape.

**`tests/test_airline_api.py`** — integration tests that hit the live AWS Lambda endpoint.
Requires internet access. No env vars needed. Covers: happy-path flight search, required
response fields, no-flights route (AAL→YVR), past date rejection, beyond-one-year rejection,
multiple valid routes, booking confirmation format. **Run sparingly — each run consumes real
API capacity and the booking tests create real bookings against the assessment endpoint.**

Run only unit tests (no network):

```bash
python -m pytest tests/test_notify.py -v
```

---

## Architectural Decisions and Workarounds

### Why Code nodes compute booleans for filters

Phonely's built-in filter operators have two correctness bugs discovered during development:

1. The `exists` operator returns `true` for empty strings (`""`). This caused the flow to
   proceed to flight search with empty IATA codes when a city was unrecognized.
2. The `is an array containing <key>` operator returns `false` for an array of objects that
   contain that key — it checks for the literal string, not the key name.

Both were fixed by adding explicit Code nodes (*Validate inputs*, *Compute has flights*) that
return `{"is_valid": bool}` and `{"has_flights": bool}`, and using Boolean equality filters
(`is equal to True (Boolean)`) instead of existence checks.

### Why the LLM never stores the flightId

The booking API requires a 32-character hex `flightId`. Asking the LLM to capture and store
this value from the API response produced hallucinated or truncated values even when the
conversation correctly identified the right flight. The fix: the LLM captures only the
human-readable flight number (e.g. `"AA697"`) via the *Present flights and select* node, and
the *Resolve flightId* Code node deterministically walks the flights array to find the matching
`flightId`. This eliminated the failure mode entirely.

### Why Phonely sandbox blocks `datetime.strptime`

Phonely's Python sandbox blocks the `_strptime` module import. Date parsing in the *Convert
city and date* node was rewritten to use manual integer slicing on the `YYYY-MM-DD` string
(`int(s[0:4])`, `int(s[5:7])`, `int(s[8:10])`) and a `MONTHS` dict for word-form dates
like `"June 15 2026"`.

### Why flights arrays arrive as JSON strings sometimes

Phonely occasionally serializes array variables to JSON strings before passing them to Code
nodes. Both *Compute has flights* and *Resolve flightId* handle this with:

```python
if isinstance(flights_raw, str):
    flights = json.loads(flights_raw)
```

### Why the LLM hallucinated fake flights

Early in development, *Present flights and select* included only a text description of what to
say. The LLM invented flight numbers and airlines not in the API response. Fixed by injecting
the raw `@flights` array variable directly into the node prompt and adding explicit anti-
hallucination instructions: *"Only present flights from the @flights variable. Do not invent
or modify any flight details."*

---

## Call Flow Walkthrough

```
Agent:  "Thank you for calling Phonely Air. How can I help you today?"
Caller: "I want to book a flight from New York to Los Angeles"
Agent:  "What date would you like to travel?"
Caller: "June 10th 2026"
Agent:  "I found 5 flights from JFK to LAX on June 10th, 2026.
         Option 1: Delta flight DL204, departs 6 AM, arrives 9 AM, $189.
         Option 2: United flight UA881, departs 10 AM, arrives 1 PM, $215.
         ...
         Which option would you prefer?"
Caller: "Option 1"
Agent:  "Great. What is your first name?"
Caller: "Omar"
Agent:  "And your last name?"
Caller: "Ibrahim"
Agent:  "Would you like your confirmation sent to an email address or phone number?"
Caller: "omaribra@uni.minerva.edu"
Agent:  "Booking your flight now... Your booking is confirmed.
         Your confirmation number is C-O-N-F-4-2-2-8-6-7.
         A confirmation email is on its way. Safe travels, Omar!"
```

---

## Example Calls

### Policy Q&A — Refund Policy

The *Answer business questions* node handles policy questions via the knowledge base. The caller
asked about the refund policy mid-call and the agent answered directly from `airline_policies.txt`
before continuing to booking.

![Policy Q&A — refund policy answered from knowledge base](examples/policy%20example.png)

---

### No Flights Available — AAL to YVR

The assessment test case. The caller spells out "A-A-L-B-O-R-G" and the *Convert city and date*
Code node correctly resolves it to `AAL`. The AWS API returns a 404 with `"flights": []`. The
*Compute has flights* Code node catches the empty array and the *No flights found* node tells the
caller gracefully and offers a retry.

![Caller spells out Aalborg — policy Q&A handled first, then AAL→YVR booking attempt starts](examples/Invalid%20trip1%20.png)

![IATA resolved correctly from spelled-out name — agent confirms Aalborg, date collected, search runs](examples/Invalid%20trip2%20.png)

![Search flights API returns GET 404 with empty flights array — Compute has flights and Check flights found nodes handle it, agent offers retry](examples/invalid%20trip3.png)

---

### Unknown City — Atlantis

When a caller provides an unrecognized city, the *Convert city and date* Code node returns `""`
for the IATA code, *Validate inputs* returns `is_valid: false`, and the *Collect missing trip
detail* node asks for a nearby major city. The agent holds its ground through two attempts before
the caller gives up and switches to New York.

![Unknown city — agent correctly rejects "Atlantis" twice and asks for a nearby major city](examples/wrong%20places%20.png)

---

## Limitations

**SMS not active** — Twilio's A2P 10DLC registration (required for US local numbers) takes
days to weeks. The `notify.py` script detects phone numbers and logs a structured stub message,
but no SMS is sent. Email confirmation works fully.

**Resend sandbox restriction** — The Resend account is in sandbox mode. The `onboarding@resend.dev`
sender is only allowed to deliver to verified recipient addresses. In production, a verified
sending domain would be required.

**Cities are limited** — Only the ~25 cities in the IATA table (system prompt + Code nodes)
are supported. Unknown cities return empty IATA strings, which the *Validate inputs* node
catches, and the caller is asked to try a nearby major city.

**No booking modification** — The AWS API supports search and booking only. There is no
endpoint to cancel, change, or look up existing bookings by confirmation number. Those requests
are routed to the transfer-to-support node.

**Trial account restrictions** — The Phonely account is on a free trial. Call duration and
concurrent call limits apply.

**Known IATA table drift risk** — The city-to-IATA mapping lives in three places that must
be kept in sync manually:

1. `system_prompt.txt` — the Guidelines shown to the LLM (affects what cities it tells callers it supports)
2. `airports.json` — the reference document in this repo
3. The `IATA_TABLE` dict inside the Phonely *Convert city and date* Code node — **this is the only one that actually runs at call time**

Adding a city to `system_prompt.txt` without adding it to the Code node's `IATA_TABLE` means
the LLM will confidently tell a caller that city is supported, but the Code node will return
`""`, which *Validate inputs* catches as invalid — the caller hears "I'm sorry, I don't have
that airport in our system."

**Current known discrepancy:** `system_prompt.txt` maps `"San Francisco / Bay Area → SFO"`,
but the Code node's `IATA_TABLE` does not include `"bay area"` as a key — only
`"san francisco"`. A caller who says "Bay Area" will hit the unrecognized-city path despite
the system prompt implying it is supported.

---

## Test Cases

| # | Scenario | Input | Expected Behavior |
|---|---|---|---|
| 1 | Happy path — email confirmation | JFK → LAX, valid date, email | Full booking, confirmation number, email sent |
| 2 | City name resolution | "New York" → "Los Angeles" | Converted to JFK → LAX without error |
| 3 | Alternate city names | "NYC" → "LA" | Same as above |
| 4 | No flights available | AAL → YVR | Agent says no flights found, offers different date |
| 5 | Invalid date — past | Yesterday's date | Agent asks for a valid date |
| 6 | Invalid date — too far | More than 1 year from now | Agent asks for a date within one year |
| 7 | Unknown city | "Springfield" | Agent asks caller to try a nearby major city |
| 8 | Policy question — refund | "What's your cancellation policy?" | Knowledge base answers from `airline_policies.txt` |
| 9 | Policy question — baggage | "How much does a checked bag cost?" | Correct fee from knowledge base |
| 10 | Transfer request mid-call | "I want to speak to a human" | Agent triggers transfer immediately |
| 11 | Phone contact | Caller gives phone number instead of email | SMS stub logged, `sms_stub` returned |
