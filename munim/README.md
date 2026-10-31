# Munim: Paytm's AI teammate for shopkeepers

Team send_me_location · Paytm Hackathon, Track 3

## The real problems Munim solves
| What shopkeepers face | What Munim does |
|---|---|
| Payout held or "amount not settled in promised time" (common consumer complaints) | Finds the reason (e.g. KYC re-verification), sends the link, releases the money, confirms the bank credit |
| "Less money came" because of Soundbox rental or card fees deducted from payouts | Explains the payout line by line: sales, each deduction, what reached the bank |
| Customer debited but shop not paid (stuck UPI payment) | Finds the pending payment, says don't hand over goods, explains RBI's rule: the customer's bank must auto-reverse within T+5 days or pay ₹100/day |
| Fake UPI payment screenshots used to cheat shopkeepers | Checks the Paytm ledger, not the screenshot |
| Soundbox silent (SIM data plan expired) | Spots it from monitoring, renews the plan before the shopkeeper even calls |
| Customer charged twice | Finds the duplicate, prepares the refund to the original payer, a person approves above ₹2,000 |
| Sales questions, "bank balance", last payments, KYC status | Answers from the shop's own data, in Hindi or English |

Why now: Paytm says its merchant sales work already runs on AI agents, its AI Soundbox talks in 11 languages, and its
costs fell 18% from "AI-led efficiency". Munim is that same direction applied to merchant support.

## How Munim understands
- **With the Sarvam key:** Sarvam's `sarvam-105b` model reads the message, a live snapshot of the shop's account and the
  recent chat, decides what the shopkeeper means (question or problem), calls tools to check facts, acts, and writes
  the reply in Hindi and English. Nothing is pre-written.
- **Without a key / no internet:** an offline backup brain covers the demo scenarios with the same tools and safety checks.

## Built to be cheap for Paytm
| Lever | What it does | Effect |
|---|---|---|
| Saver mode (default) | Routine, clear requests take the fast path with no AI call; the AI model handles unclear, mixed or long messages | Most cases cost ₹0 in AI |
| Prevention | Monitoring fixes problems (e.g. expired Soundbox plan) before the shopkeeper calls | The cheapest call is the one that never happens |
| Cheaper voice | Bulbul v4 Flash (₹1 per 1,000 chars, a third of v3); common lines cached on disk | Voice reply ≈ ₹0.20 |
| Speak only when useful | The app speaks replies when the shopkeeper spoke or for alerts; typed questions get text | Fewer voice calls |
| Prompt caching | Fixed instructions and tools come first so repeated AI calls are billed at the cached rate | Lower AI cost per call |
| Person only for risk | Humans see only refunds above ₹2,000, disputes and documents | Agent time goes where it matters |

The desk shows live: cost per case (Munim vs ₹100 for a person), money saved today, % of cases with no AI call,
and problems fixed before the shopkeeper called.

## Run it (laptop)
1. Install Python 3.10 or newer.
2. Double-click `start-windows.bat` (Windows) or run `./start-mac-linux.sh` (Mac/Linux).
3. Open http://localhost:8000 on the laptop. Everything works offline with dummy data.

## Try it on your phone
1. Put the phone on the same Wi-Fi or hotspot as the laptop.
2. Scan a QR code on the laptop's start page (Shopkeeper app, Soundbox, Field rep).
3. If the phone shows a warning, tap Advanced → Proceed. Allow the microphone.

## Add the Sarvam AI key (voice + smart brain)
Laptop → Paytm desk → **Demo** → Sarvam AI key → paste → **Save & test**.
Both lines should turn green. Without a key, Munim still works: it uses its offline brain and the phone's own voice.

## Voice sign-up for new shopkeepers (`/join`)
A new shopkeeper joins Paytm by talking to Munim: shop name, owner, business, location, mobile (OTP), Aadhaar KYC
(OTP), bank and last 4 digits. Munim suggests the right device for the business, then checks before going live:
₹1 bank test (does the account holder's name match?), mobile, KYC and duplicate accounts. If everything is clean it
activates the shop itself (the QR works immediately), orders the device and books the field rep's installation visit.
If a check fails, a Paytm teammate approves or rejects on the desk. Demo: an account number ending **0000** belongs to
"someone else", which sends the sign-up to a person. The desk shows new shops signed up and minutes to go live.
Munim only collects and pre-fills; Paytm's usual KYC verification still applies.

## Fraud alert network (3 shops, one area)
Sharma Kirana, Gupta Medicals and Khan Electronics are all in Vijay Nagar, Indore. Every time Munim checks "did this
payment come?" and the answer is no, that is a signal. When 2 different shops in the same area get such a claim within
60 minutes, Munim creates a fraud report and warns every shop in the area on its Soundbox and app, with no person
needed. The third shop hears the warning on its own. Open the shops from the "Fraud alert demo" QR codes on the start
page (`/merchant?m=M1002`, `/soundbox?m=M1003`, ...), or press Demo → "Fake ₹2,000 claims at 2 shops" on the desk.

## Screens
| Page | Who | Address |
|---|---|---|
| Start + QR codes | Presenter | `/` |
| Shopkeeper app | Merchant phone | `/merchant` |
| Soundbox | Second phone on the counter | `/soundbox` |
| Field rep | Third phone | `/rep` |
| New shopkeeper sign-up | Any phone | `/join` |
| Paytm desk | Laptop / projector | `/console` |

## Tech
- **Frontend:** React 18 + TypeScript + Vite, Tailwind CSS, Framer Motion, lucide icons. Hindi/English switch on every screen.
- **Backend:** Python FastAPI + SQLite, live updates over WebSockets.
- **AI:** Sarvam `sarvam-105b` with tool calling (falls back to an offline rule brain), Sarvam Saaras speech-to-text, Bulbul text-to-speech.
- **Safety:** every action passes a policy check; refunds above ₹2,000 need a human OK; one-tap Undo; full activity log.

## Changing the frontend
The built app is already in `web/`. Only if you edit `frontend/src`:
```
cd frontend && npm install && npm run build
```
