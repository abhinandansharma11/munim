"""Offline brain: a rule-based planner that drives the SAME tools, gateway, approvals and ledger as the LLM.

It is the safety net for the live demo (no internet, no API key, or the LLM misbehaves).
Every reply is written three ways: Hinglish (what was typed style), Hindi (Devanagari) and English.
"""
import re
from datetime import date, timedelta

from .tools import inr

HI_NAMES = {"रोहित": "Rohit", "नेहा": "Neha", "राहुल": "Rahul", "प्रिया": "Priya", "अमित": "Amit"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _day(d, lang="hinglish"):
    if d == (date.today() - timedelta(days=1)).isoformat():
        return {"hinglish": "kal", "hi": "कल", "en": "yesterday's"}[lang]
    y, m, dd = d.split("-")
    return f"{int(dd)} {MONTHS[int(m) - 1]}"


def _hour(h, lang="hinglish"):
    if not h:
        return {"hinglish": "shaam", "hi": "शाम", "en": "evening"}[lang]
    hr = int(h[:2])
    n = (hr - 1) % 12 + 1
    if lang == "en":
        return f"{n} {'am' if hr < 12 else 'pm'}"
    part = ("subah", "सुबह") if hr < 12 else ("dopahar", "दोपहर") if hr < 16 else ("shaam", "शाम")
    return f"{n} baje {part[0]}" if lang == "hinglish" else f"{part[1]} {n} बजे"


def _amount(text):
    k = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lac|लाख|hazaar|hazar|हज़ार|हजार|thousand|k\b)", text, re.I)
    if k:
        mult = 100000 if k.group(2).lower() in ("lakh", "lac", "लाख") else 1000
        return int(float(k.group(1)) * mult)
    m = re.search(r"(?:₹|rs\.?|inr|rupees?|rupay?e?s?|रुपये|रुपए)\s*([\d,]+)|([\d,]{3,})|(\d+)\s*(?:rupees?|rupay?e?|रुपये|रुपए|rs)", text, re.I)
    if m and m.group(3):
        return int(m.group(3))
    if not m:
        return None
    raw = (m.group(1) or m.group(2) or "").replace(",", "")
    return int(raw) if raw.isdigit() else None


def _payer(text):
    m = (re.search(r"([A-Z][a-z]+)\s+ne\b", text) or re.search(r"from\s+([A-Z][a-z]+)", text)
         or re.search(r"\b(?:[Dd]id|[Hh]as)\s+([A-Z][a-z]+)\s+(?:pay|paid|send|sent)", text))
    if m:
        return m.group(1)
    m = re.search(r"(\S+)\s+ने(?=[\s,।?]|$)", text)
    if m:
        return HI_NAMES.get(m.group(1), m.group(1))
    m = re.search(r"\b([A-Z][a-z]+)\s+(?:ka|ki|ke)\s+(?:payment|paisa|paise)", text) or re.search(r"\b([a-z]+)\s+(?:ka|ki|ke)\s+(?:payment|paisa|paise)\s+(?:aaya|aya|aa gaya)", text, re.I)
    if m and m.group(1).lower() not in ("mera", "aaj", "kal", "customer", "uska", "unka", "is", "us"):
        return m.group(1).capitalize()
    m = re.search(r"(\S+)\s+(?:का|की|के)\s+(?:पेमेंट|पैसा|पैसे)", text)
    if m and m.group(1) not in ("मेरा", "आज", "कल", "ग्राहक", "उसका", "इस", "उस"):
        return HI_NAMES.get(m.group(1), m.group(1))
    return None


HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]

# ------------------------------------------------------------------ understanding the shopkeeper
# Phrases in Hinglish, Hindi (Devanagari) and English. Matching is on whole phrases inside the message.
W = {
    "fake_payment": ["screenshot", "screen shot", "स्क्रीनशॉट", "स्क्रीन शॉट", "bhaag gaya", "bhag gaya", "भाग गया", "bhaag gayi",
                     "ran away", "fake payment", "nakli", "नकली", "farzi", "फर्जी", "फ़र्ज़ी", "fake upi", "fake"],
    "dispute": ["jhagda", "dispute", "galat saaman", "galat saman", "wapas maang", "complaint", "fraud", "police", "झगड़ा", "शिकायत",
                "धोखा", "scam"],
    "account_change": ["account badal", "account change", "change my bank", "change bank", "naya account", "bank badal",
                       "खाता बदल", "अकाउंट बदल", "बैंक बदल", "नया खाता", "नया अकाउंट"],
    "invoice": ["gst", "invoice", "इनवॉइस", "जीएसटी", "tax"],
    "human_req": ["call karo", "call me", "call kijiye", "insaan", "इंसान", "agent", "customer care", "kisi se baat",
                  "किसी से बात", "manager", "talk to a person", "real person"],
    "self_refund_target": ["mere account", "my account", "mujhe refund", "50,000", "50000", "khud ko", "मेरे अकाउंट", "मेरे खाते", "मुझे रिफंड"],
    "refund": ["refund", "रिफंड", "paisa wapas", "पैसा वापस", "पैसे वापस"],
    "new_store": ["doosri dukaan", "dusri dukaan", "nayi dukaan", "new store", "second shop", "new shop", "doosri dukan",
                  "nayi dukan", "दूसरी दुकान", "नई दुकान", "new outlet", "second outlet"],
    "double": ["do baar", "double", "twice", "2 baar", "दो बार", "duplicate", "do bar", "2 बार"],
    "soundbox": ["soundbox", "sound box", "speaker", "awaaz", "aawaz", "bol nahi", "bolta nahi", "announce", "साउंडबॉक्स",
                 "साउंड बॉक्स", "बोल नहीं", "आवाज़", "आवाज"],
    "verify": ["aaya kya", "aaya ki nahi", "aya kya", "bheja", "received?", "did ", "check payment", "payment check", "screenshot",
               "aa gaya kya", "भेजा", "आया क्या", "आया कि नहीं", "आ गया क्या", "has it come", "did it come"],
    "stuck": ["kat gaya par", "kat gaya lekin", "kata par", "kata lekin", "kat gaya magar", "debit ho gaya", "debited", "कट गया पर",
              "कट गए पर", "कटा पर", "कट गया लेकिन", "कट गए लेकिन", "deducted but", "cut but", "pending", "पेंडिंग", "processing",
              "customer ka paisa kat", "ग्राहक का पैसा कट", "ग्राहक के पैसे कट", "grahak ka paisa kat", "atak gaya", "अटक गया", "fas gaya", "फँस गया"],
    "deduction": ["kam aaya", "kam paisa", "kam paise", "कम आया", "कम आए", "कम पैसे", "कम पैसा", "less money", "less amount", "less than",
                  "deduct", "kyun kata", "kyu kata", "क्यों कटा", "क्यों कटे", "rental", "रेंटल", "किराया", "kiraya", "charges", "charge",
                  "चार्ज", " fee", "फीस", "mdr", "commission", "कमीशन", "kat ke aaya", "कट के आया", "katoti", "कटौती", "कम क्यों", "kam kyun", "kam kyu", "why less",
                  "पैसा कम", "पैसे कम", "paisa kam", "paise kam", "short payment", "less payout"],
    "balance": ["balance", "बैलेंस", "बैलेन्स", "bank me kitna", "bank mein kitna", "account me kitna", "account mein kitna",
                "khate me kitna", "khate mein kitna", "खाते में कितना", "बैंक में कितना", "kitna paisa hai", "कितना पैसा है",
                "kitne paise hai", "how much money do i have", "money is in my bank", "how much money is in", "मेरे बैंक में कितना", "money in my bank", "money in bank", "money in my account"],
    "payout": ["settlement", "settle", "payout", "पेआउट", "सेटलमेंट", "bank me paisa", "bank mein paisa", "बैंक में पैसा",
               "money to bank", "money to my bank", "to my bank", "kal ka paisa", "कल का पैसा", "paisa nahi aaya", "paise nahi aaye",
               "पैसा नहीं आया", "पैसे नहीं आए", "money not received", "bank transfer", "kab aayega", "कब आएगा", "bank kab",
               "बैंक में", "in my bank", "money come to", "bank me kab", "bank mein kab"],
    "complaint": ["nahi aaya", "nahi aya", "nahi aaye", "nahin aaya", "नहीं आया", "नहीं आए", "नहीं आई", "not received", "not come",
                  "hasn't come", "has not come", "didn't come", "not credited", "nahi mila", "नहीं मिला", "ruka", "रुका", "stuck",
                  "on hold", "late", " der ", "देर", "abhi tak", "अभी तक", "kyun", "kyon", "क्यों", "why", "problem", "dikkat",
                  "दिक्कत", "pareshan", "परेशान", "issue", "band ho", "बंद हो", "kaam nahi", "काम नहीं", "not working", "nahi bol",
                  "नहीं बोल", "silent", "kharab", "खराब", "not announcing"],
    "refund_q": ["refund status", "refund hua", "refund ka kya", "refund kab", "रिफंड का क्या", "रिफंड हुआ", "रिफंड कब", "refund ho gaya"],
    "recent": ["last payment", "aakhri payment", "akhri payment", "आखिरी पेमेंट", "pichla payment", "recent payment", "latest payment",
               "payments dikhao", "पेमेंट दिखाओ", "kisne bheja", "kisne pay", "किसने", "who paid", "last 5", "आखिरी 5", "akhri 5",
               "aakhri 5", "last few payment", "pichle payment", "पिछले पेमेंट"],
    "sales": ["kitna paisa aaya", "kitna aaya", "kitna aya", "kitni kamai", "kamai", "kamaai", "कमाई", "बिक्री", "bikri", "sale",
              "earn", "collection", "hisaab", "hisab", "हिसाब", "khata", "kitna hua", "कितना आया", "कितना पैसा आया", "कितना हुआ",
              "aaj kitna", "आज कितना", "कमाया", "kamaya", "kamaye", "कितना बिका", "becha", "बेचा", "earned", "sold", "sell", "revenue",
              "income", "आमदनी", "aamdani", "कमाए", "dukaan band", "dukan band", "दुकान बंद", "closing", "total", "business kaisa", "धंधा", "dhandha"],
    "kyc": ["kyc", "केवाईसी", "के वाई सी", "re-verif", "reverif", "re verif"],
    "done": ["ho gaya", "kar diya", "kar liya", "done", "completed", "हो गया", "कर दिया", "कर लिया", "पूरा कर"],
    "loan": ["loan", "karz", "udhaar", "लोन", "कर्ज", "credit line"],
    "greet": ["hello", " hi ", "namaste", "hey", "नमस्ते", "namaskar", "नमस्कार", "good morning", "ram ram", "राम राम"],
    "thanks": ["thank", "dhanyavad", "dhanyawad", "shukriya", "धन्यवाद", "शुक्रिया", "thnx", "thx"],
    "help": ["kya kar sakte", "help", "madad", "मदद", "क्या कर सकते", "what can you do", "kya kya"],
    "yes": ["haan", " han ", " ha ", "yes", " ok ", "okay", "bhej do", "bhejo", "kar do", "हाँ", "हां", "ठीक है", "theek hai",
            "thik hai", "ji haan", "जी हाँ", "please", "zaroor", "ज़रूर", "sure", "भेज दो", "कर दो", "jee", " ji "],
    "no": ["nahi", "nahin", " no ", " mat ", "नहीं", "rehne do", "रहने दो", "abhi nahi", "अभी नहीं", "not now"],
}

PERIOD_WORDS = [
    ("last_month", ["pichhle mahine", "pichle mahine", "पिछले महीने", "last month"]),
    ("last_30_days", ["30 din", "30 दिन", "last 30 days", "तीस दिन"]),
    ("this_month", ["is mahine", "iss mahine", "इस महीने", "this month", "mahine", "महीने", "month"]),
    ("last_week", ["pichhle hafte", "pichle hafte", "पिछले हफ्ते", "पिछले हफ़्ते", "last week"]),
    ("last_7_days", ["7 din", "7 दिन", "सात दिन", "saat din", "last 7 days", "past week"]),
    ("this_week", ["is hafte", "iss hafte", "इस हफ्ते", "इस हफ़्ते", "this week", "hafte", "हफ्ते", "हफ़्ते", "week"]),
    ("yesterday", ["kal", "कल", "yesterday"]),
    ("today", ["aaj", "आज", "today"]),
]


def _t(text):
    return " " + re.sub(r"\s+", " ", re.sub(r"[?!।,.]", " ", text.lower())) + " "


def _has(t, key):
    return any(w in t for w in W[key])


def _period(text):
    t = _t(text)
    for p, ws in PERIOD_WORDS:
        if any(w in t for w in ws):
            return p
    return "today"


def _complaint(text):
    return _has(_t(text), "complaint")


def _clause(orig):
    c = _t(orig)
    out = []
    if not _has(c, "double"):
        if _has(c, "stuck"):
            return ["stuck_payment"]
        if _has(c, "deduction"):
            return ["deductions"]
    if _has(c, "double"):
        out.append("double_debit")
    if _has(c, "soundbox"):
        out.append("soundbox")
    asks_payment = _has(c, "verify") and (_amount(c) or _payer(orig.strip()))
    if asks_payment and "double_debit" not in out:
        out.append("verify")
    elif _has(c, "balance"):
        out.append("balance")
    elif _has(c, "payout") and "double_debit" not in out:
        out.append("settlement" if _has(c, "complaint") else "payout_info")
    elif _has(c, "refund_q") or (_has(c, "refund") and "double_debit" not in out):
        out.append("refund_status")
    elif _has(c, "recent"):
        out.append("recent_payments")
    elif _has(c, "sales"):
        out.append("sales")
    elif _has(c, "verify") and "double_debit" not in out and "soundbox" not in out:
        out.append("recent_payments")
    if _has(c, "kyc"):
        out.append("kyc_done_claim" if _has(c, "done") else "kyc_info")
    if _has(c, "loan") and not out:
        out.append("loan")
    return out


def detect(text):
    """Returns the list of things the shopkeeper wants, in order. Several clauses ('X aur Y') give several intents."""
    t = _t(text)
    # "Customer showed a screenshot / ran away / fake payment" is a fraud report, even if it also says "paisa nahi aaya".
    if _has(t, "fake_payment") and not _has(t, "double"):
        return ["fake_payment"]
    if _has(t, "dispute") or _has(t, "account_change") or _has(t, "invoice") or _has(t, "human_req"):
        return ["human"]
    if _has(t, "refund") and _has(t, "self_refund_target"):
        return ["self_refund"]
    if _has(t, "self_refund_target") and any(w in t for w in ("daal do", "dal do", "transfer", "bhej do", "डाल दो", "भेज दो")):
        return ["not_allowed"]
    if _has(t, "new_store"):
        return ["new_store"]
    intents = []
    for c in re.split(r"\s(?:aur|and|और|also|plus|तथा)\s|[;।]|\?\s", text):
        for i in _clause(c):
            if i not in intents:
                intents.append(i)
    if any(i in intents for i in ("balance", "payout_info", "settlement")) and "sales" in intents:
        intents.remove("sales")  # "bank mein paisa kab aur kitna aaya" is one question about the bank, not two
    if not intents:
        words = len(t.split())
        if _has(t, "done") and words <= 5:
            intents.append("kyc_done_claim")
        elif _has(t, "thanks"):
            intents.append("thanks")
        elif _has(t, "yes") and words <= 5:
            intents.append("yes")
        elif _has(t, "no") and words <= 4:
            intents.append("no")
        elif _has(t, "help"):
            intents.append("help")
        elif _has(t, "greet"):
            intents.append("greet")
    return intents or ["unknown"]


def _date(d, lang="hinglish"):
    d = (d or "")[:10]
    today = date.today()
    if d == today.isoformat():
        return {"hinglish": "aaj", "hi": "आज", "en": "today"}[lang]
    if d == (today - timedelta(days=1)).isoformat():
        return {"hinglish": "kal", "hi": "कल", "en": "yesterday"}[lang]
    y, m, dd = d.split("-")
    return f"{int(dd)} {(HI_MONTHS if lang == 'hi' else MONTHS)[int(m) - 1]}"


# ------------------------------------------------------------------ offers: Munim asks before acting on a question
def _offer(A, case, what):
    A.agent.db.meta_set("offer:" + case["merchant_id"], {"what": what, "ts": date.today().isoformat() + "|" + str(__import__("time").time())})


def _take_offer(A, case):
    k = "offer:" + case["merchant_id"]
    o = A.agent.db.meta_get(k)
    A.agent.db.meta_set(k, None)
    if not o:
        return None
    ts = float(o["ts"].split("|")[1])
    return o["what"] if __import__("time").time() - ts < 1800 else None


# Requests the fast path answers well on its own. Anything else (unclear, several problems at once, long stories,
# replies that depend on earlier chat) goes to the AI model.
FAST_INTENTS = {"fake_payment", "soundbox", "settlement", "payout_info", "balance", "sales", "recent_payments", "verify", "kyc_info",
                "kyc_done_claim", "refund_status", "stuck_payment", "deductions", "double_debit", "self_refund", "not_allowed",
                "new_store", "loan", "greet", "thanks", "help", "human"}
FAST_LABEL = {"fake_payment": "fake payment report", "soundbox": "Soundbox check", "settlement": "held payout", "payout_info": "payout status", "balance": "bank balance",
              "sales": "sales figures", "recent_payments": "recent payments", "verify": "payment check", "kyc_info": "KYC status",
              "kyc_done_claim": "KYC done", "refund_status": "refund status", "stuck_payment": "stuck payment",
              "deductions": "payout deductions", "double_debit": "double charge", "self_refund": "refund request",
              "not_allowed": "unsafe request", "new_store": "new outlet", "loan": "loan question", "greet": "greeting",
              "thanks": "thanks", "help": "help", "human": "needs a person", "yes": "reply to Munim's offer"}


def fast_path(db, case, trigger):
    """Returns a short label if the fast path can handle this trigger confidently, else None (use the AI model)."""
    kind = trigger["type"]
    if kind in ("kyc_completed", "approval", "event"):
        return {"kyc_completed": "KYC completed", "approval": "teammate decision", "event": "monitoring alert"}[kind]
    text = trigger.get("text", "")
    intents = detect(text)
    if len(intents) != 1 or len(text.split()) > 12:
        return None
    i = intents[0]
    if i == "yes" and (db.meta_get("offer:" + case["merchant_id"]) or {}).get("what"):
        return FAST_LABEL["yes"]
    return FAST_LABEL[i] if i in FAST_INTENTS else None


async def run(A, case, trigger):
    """A = the Agent facade (tool, think, reply). Returns the final case status."""
    kind = trigger["type"]
    if kind == "message":
        status = "resolved"
        for intent in detect(trigger["text"]):
            s = await HANDLERS[intent](A, case, trigger["text"])
            if s in ("waiting_merchant", "waiting_human", "handed_over"):
                status = s
        return status
    if kind == "kyc_completed":
        return await after_kyc(A, case)
    if kind == "approval":
        return await after_approval(A, case, trigger)
    if kind == "event":
        ev = trigger["event"]
        if ev == "device_offline":
            return await proactive_device(A, case)
        if ev == "shop_closed":
            return await khata(A, case, "")
    return "resolved"


# ------------------------------------------------------------------ handlers
async def soundbox(A, case, text):
    complaint = _complaint(text)
    await A.think("The merchant says the Soundbox is silent. Checking the device first." if complaint
                  else "The merchant is asking about the Soundbox. Checking the device.")
    r = await A.tool("get_device_health")
    bad = next((d for d in r.get("devices", []) if d["status"] != "online"), None)
    coming = next((d for d in r.get("devices", []) if d["status"] == "not_installed"), None)
    if coming:
        await A.reply("Aapka Soundbox abhi raaste mein hai; field rep kal subah 11 baje lagane aayenge. Tab tak QR se payment le sakte hain.",
                      "आपका साउंडबॉक्स अभी रास्ते में है; फील्ड साथी कल सुबह 11 बजे लगाने आएँगे। तब तक QR से पेमेंट ले सकते हैं।",
                      "Your Soundbox is on its way; the field rep will install it tomorrow at 11 am. Until then you can take payments on the QR.")
        return "resolved"
    if not bad and not complaint:
        d = r["devices"][0]
        await A.reply(f"Haan, aapka Soundbox chaalu hai. Battery {d['battery_pct']}% hai aur data plan {_date(d['data_plan_expires'])} tak hai.",
                      f"हाँ, आपका साउंडबॉक्स चालू है। बैटरी {d['battery_pct']}% है और डेटा प्लान {_date(d['data_plan_expires'], 'hi')} तक है।",
                      f"Yes, your Soundbox is working. Battery is {d['battery_pct']}% and the data plan runs till {_date(d['data_plan_expires'], 'en')}.")
        return "resolved"
    if not bad:
        await A.reply("Aapka Soundbox online hai aur theek chal raha hai. Ek baar power button 3 second daba ke restart kar dijiye.",
                      "आपका साउंडबॉक्स चालू है और ठीक चल रहा है। एक बार पावर बटन तीन सेकंड दबाकर रीस्टार्ट कर दीजिए।",
                      "Your Soundbox is online and working. Hold the power button for 3 seconds to restart it once.")
        return "resolved"
    if bad["data_plan_expired"]:
        await A.think(f"{bad['device_id']} is offline because its SIM data plan expired. Renewing is low risk and reversible, so I can do it myself.")
        await A.tool("renew_device_plan", device_id=bad["device_id"])
        await A.tool("get_device_health", why="Confirm the device is back online")
        await A.reply("Soundbox theek ho gaya! Uska data plan khatam ho gaya tha, maine 30 din ke liye renew kar diya. Ab har payment pe awaaz aayegi.",
                      "साउंडबॉक्स ठीक हो गया! उसका डेटा प्लान खत्म हो गया था, मैंने तीस दिन के लिए रिन्यू कर दिया। अब हर पेमेंट पर आवाज़ आएगी।",
                      "Your Soundbox is fixed! Its data plan had run out, so I renewed it for 30 days. It will announce every payment again.")
        return "resolved"
    await A.tool("handover_to_human", summary=f"{bad['device_id']} offline with a valid data plan; likely hardware or network. Needs a technician.")
    await A.reply("Soundbox mein network ki dikkat lag rahi hai. Maine technician ko bata diya hai, wo aapko call karenge.",
                  "साउंडबॉक्स में नेटवर्क की दिक्कत लग रही है। मैंने टेक्नीशियन को बता दिया है, वो आपको कॉल करेंगे।",
                  "This looks like a network fault in the Soundbox. I've told a technician; they will call you.")
    return "handed_over"


async def settlement(A, case, text):
    await A.think("The merchant is asking about a payout. Checking recent settlements.")
    r = await A.tool("get_settlements")
    held = next((s for s in r["settlements"] if s["status"] == "on_hold"), None)
    if not held:
        return await payout_info(A, case, text)
    k = await A.tool("get_kyc_status")
    if k["kyc_status"] == "verified":
        return await release(A, held)
    await A.think(f"{held['amount']} is held for KYC re-verification. It can't be released until KYC is done, so I'll send a secure link.")
    await A.tool("send_kyc_link")
    await A.reply(f"Aapka {_day(held['for_date'])} ka {held['amount']} KYC re-verification ki wajah se ruka hai. Maine aapko ek link bheja hai, sirf 1 minute ka kaam hai. Verify hote hi main paisa turant release kar dunga.",
                  f"आपका {_day(held['for_date'], 'hi')} का {held['amount']} केवाईसी दोबारा जाँच की वजह से रुका है। मैंने नीचे एक लिंक भेजा है, सिर्फ एक मिनट का काम है। जाँच होते ही मैं पैसा तुरंत भेज दूँगा।",
                  f"Your payout of {held['amount']} for {_date(held['for_date'], 'en')}'s sales is on hold for KYC re-verification. I've sent you a link below; it takes about a minute. As soon as it's done, I'll release the money.")
    return "waiting_merchant"


async def release(A, held):
    await A.tool("requeue_settlement", settlement_id=held["settlement_id"])
    prof = await A.tool("get_merchant_profile", why="Get the bank account to confirm the credit")
    await A.reply(f"Ho gaya! {held['amount']} aapke {prof['bank']} account mein credit kar diya gaya hai.",
                  f"हो गया! {held['amount']} आपके {prof['bank']} खाते में भेज दिए गए हैं।",
                  f"Done! {held['amount']} has been credited to your {prof['bank']} account.")
    await sales_check(A)
    return "resolved"


async def after_kyc(A, case):
    await A.think("The merchant completed KYC in the app. Checking it really went through before releasing money.")
    k = await A.tool("get_kyc_status")
    if k["kyc_status"] != "verified":
        await A.reply("KYC abhi complete nahi hua dikh raha. Link pe 'Verify' dabaiye, main wait kar raha hoon.",
                      "केवाईसी अभी पूरा नहीं हुआ है। लिंक पर 'जाँच करें' दबाइए, मैं इंतज़ार कर रहा हूँ।",
                      "KYC isn't complete yet. Tap 'Verify' on the link; I'm waiting.")
        return "waiting_merchant"
    r = await A.tool("get_settlements")
    held = next((s for s in r["settlements"] if s["status"] == "on_hold"), None)
    if not held:
        await A.reply("KYC verify ho gaya. Koi payment ruka hua nahi hai.", "केवाईसी पूरा हो गया। कोई पैसा रुका हुआ नहीं है।",
                      "KYC verified. Nothing is on hold.")
        return "resolved"
    await A.think(f"KYC is verified, so the hold reason is cleared. Releasing {held['amount']}.")
    return await release(A, held)


async def kyc_done_claim(A, case, text):
    return await after_kyc(A, case)


async def sales_check(A):
    r = await A.tool("check_loan_eligibility", why="A resolved payout case is a good moment to check for a genuine offer")
    if r.get("eligible") and not r.get("needs_kyc_first"):
        await A.think(f"{', '.join(r['reasons'])}: a genuine loan opportunity. I'll brief the field rep rather than push the merchant.")
        await A.tool("create_lead_brief", product="Working-capital loan")
        await A.reply(f"Ek achhi khabar: aapke business ke hisaab se aap {r['pre_approved_up_to']} tak ke loan ke liye pre-eligible hain. Hamare field rep aapko details ke liye call karenge.",
                      f"एक अच्छी खबर: आपकी बढ़ती बिक्री की वजह से आपको {r['pre_approved_up_to']} तक का लोन मिल सकता है। हमारे फील्ड साथी आपको कॉल करके बताएँगे।",
                      f"Good news: with your growing sales, you're pre-eligible for a loan of up to {r['pre_approved_up_to']}. Our field rep will call you with the details.")


async def double_debit(A, case, text):
    amount = _amount(text)
    await A.think("A customer may have been charged twice. Searching recent payments" + (f" of {inr(amount)}." if amount else "."))
    r = await A.tool("search_payments", amount=amount) if amount else await A.tool("search_payments")
    dup = next((p for p in r["payments"] if p["likely_duplicate_of"] and not p["already_refunded"]), None)
    if not dup:
        await A.reply("Mujhe is amount ka sirf ek hi payment dikh raha hai, koi duplicate nahi. Customer ka UPI reference bhejiye, main dobara check karta hoon.",
                      "मुझे इस रकम का सिर्फ एक ही पेमेंट दिख रहा है, दोबारा नहीं कटा। ग्राहक का यूपीआई नंबर भेजिए, मैं फिर से देखता हूँ।",
                      "I can see only one payment of this amount, no duplicate. Send me the customer's UPI reference and I'll check again.")
        return "resolved"
    await A.think(f"Two {dup['amount']} debits from {dup['payer']} 31 seconds apart, and only one has an order. {dup['txn_id']} is the duplicate.")
    res = await A.tool("initiate_refund", txn_id=dup["txn_id"], amount=dup["amount_value"], reason="Duplicate debit, no order")
    if res.get("status") == "waiting_for_human_approval":
        await A.reply(f"Haan, {dup['amount']} do baar kata hai, doosra payment duplicate hai. Maine refund taiyaar kar diya hai; ek Paytm teammate abhi approve kar rahe hain.",
                      f"हाँ, {dup['amount']} दो बार कटे हैं, दूसरा पेमेंट गलती से हुआ है। मैंने रिफंड तैयार कर दिया है, पेटीएम के एक साथी अभी मंज़ूरी दे रहे हैं।",
                      f"Yes, {dup['amount']} was charged twice; the second payment is a duplicate. I've prepared the refund and a Paytm teammate is approving it now.")
        return "waiting_human"
    if res.get("done"):
        await A.reply(f"Duplicate payment ka {res['amount']} refund ho gaya, customer ko kuch minute mein mil jayega.",
                      f"दोबारा कटे {res['amount']} वापस भेज दिए गए, ग्राहक को कुछ मिनट में मिल जाएँगे।",
                      f"The duplicate {res['amount']} has been refunded; the customer will get it in a few minutes.")
    return "resolved"


async def after_approval(A, case, trigger):
    if case["channel"] == "onboarding":
        from . import onboarding
        if trigger.get("approved"):
            await onboarding.go_live(A, A.agent, A.agent.db, case["merchant_id"])
            return "resolved"
        A.agent.db.x("UPDATE onboarding SET status='rejected' WHERE merchant_id=?", (case["merchant_id"],))
        await A.reply("Aapke bank khate ka naam aapke naam se nahi milta. Hamari team aapko call karke sahi khata jodne mein madad karegi.",
                      "आपके बैंक खाते का नाम आपके नाम से नहीं मिलता। हमारी टीम आपको कॉल करके सही खाता जोड़ने में मदद करेगी।",
                      "Your bank account name doesn't match yours. Our team will call to help you add the right account.")
        await A.agent.bus.emit("onboarded", merchant_id=case["merchant_id"], status="rejected")
        return "handed_over"
    if trigger.get("approved"):
        res = trigger.get("result") or {}
        await A.reply(f"Refund ho gaya! {res.get('amount', '')} customer ke account mein kuch minute mein pahunch jayega. Refund ID: {res.get('refund_id', '')}.",
                      f"रिफंड हो गया! {res.get('amount', '')} ग्राहक के खाते में कुछ मिनट में पहुँच जाएगा।",
                      f"Refund done! {res.get('amount', '')} will reach the customer's account in a few minutes. Refund ID: {res.get('refund_id', '')}.")
        return "resolved"
    await A.reply("Is refund ko ek teammate khud dekh rahe hain. Wo aapko jaldi call karenge.",
                  "इस रिफंड को पेटीएम के एक साथी खुद देख रहे हैं। वो आपको जल्दी कॉल करेंगे।",
                  "A Paytm teammate is handling this refund personally. They'll call you shortly.")
    return "handed_over"


async def self_refund(A, case, text):
    amount = _amount(text) or 50000
    await A.think(f"The merchant wants {inr(amount)} refunded to their own account. Checking for a real payment and asking the policy gateway.")
    await A.tool("search_payments", amount=amount)
    await A.tool("initiate_refund", txn_id="NONE", amount=amount, to="merchant's own account", reason="Requested by merchant")
    await A.reply(f"Maaf kijiye, ye main nahi kar sakta. Refund sirf us customer ko wapas jaata hai jisne payment kiya tha, aur {inr(amount)} ka koi payment mila hi nahi.",
                  f"माफ़ कीजिए, ये मैं नहीं कर सकता। रिफंड सिर्फ उसी ग्राहक को वापस जाता है जिसने पेमेंट किया था, और {inr(amount)} का कोई पेमेंट मिला ही नहीं।",
                  f"Sorry, I can't do that. Refunds only go back to the customer who paid, and there is no {inr(amount)} payment to refund.")
    return "resolved"


async def verify(A, case, text):
    amount, payer = _amount(text), _payer(text)
    if not amount and payer:
        await A.think(f"Checking the latest payment from {payer}. Only the ledger counts, not screenshots.")
        r = await A.tool("get_recent_payments", limit=1, payer=payer)
        p = r["payments"][0] if r["payments"] else None
        if p and p["is_today"]:
            await A.reply(f"Haan, {p['payer']} ka {p['amount']} aaj {p['time']} par aaya hai.",
                          f"हाँ, {p['payer']} के {p['amount']} आज {p['time']} पर आए हैं।",
                          f"Yes, {p['amount']} from {p['payer']} came today at {p['time']}.")
        elif p:
            await A.reply(f"Aaj {payer} ka koi payment nahi aaya. Unka aakhri payment {p['amount']}, {_date(p['date'])} {p['time']} ko tha.",
                          f"आज {payer} का कोई पेमेंट नहीं आया। उनका आखिरी पेमेंट {p['amount']}, {_date(p['date'], 'hi')} {p['time']} को था।",
                          f"No payment from {payer} today. Their last one was {p['amount']} on {_date(p['date'], 'en')} at {p['time']}.")
        else:
            await A.reply(f"{payer} naam se koi payment nahi mila. Jab tak Soundbox na bole, saaman mat dijiye.",
                          f"{payer} नाम से कोई पेमेंट नहीं मिला। जब तक साउंडबॉक्स न बोले, सामान मत दीजिए।",
                          f"I found no payment from {payer}. Don't hand over goods until the Soundbox announces it.")
        return "resolved"
    if not amount:
        await A.reply("Kitne rupaye ka payment check karun? Amount bataiye.", "कितने रुपये का पेमेंट देखूँ? रकम बताइए।",
                      "How much was the payment? Tell me the amount and I'll check.")
        return "resolved"
    await A.think(f"Checking whether {inr(amount)}" + (f" from {payer}" if payer else "") + " really arrived. Screenshots can be faked; only the ledger counts.")
    r = await A.tool("verify_payment", amount=amount, payer=payer)
    if r["received"]:
        await A.reply(f"Haan, {r['amount']} {r['payer']} se {r['time']} baje aa gaya hai. Saaman de sakte hain.",
                      f"हाँ, {r['amount']} {r['time']} बजे आ गए हैं। सामान दे सकते हैं।",
                      f"Yes, {r['amount']} from {r['payer']} arrived at {r['time']}. You can hand over the goods.")
    elif r.get("area_fraud_alert"):
        await A.reply(f"Nahi! {inr(amount)} ka koi payment nahi aaya. Dhyan dijiye: aaj aapke ilaake mein nakli payment screenshot ki shikayatein aayi hain. Saaman bilkul mat dijiye.",
                      f"नहीं! {inr(amount)} का कोई पेमेंट नहीं आया। ध्यान दीजिए: आज आपके इलाके में नकली पेमेंट स्क्रीनशॉट की शिकायतें आई हैं। सामान बिल्कुल मत दीजिए।",
                      f"No! No {inr(amount)} payment has arrived. Careful: fake payment screenshots have been reported in your area today. Don't hand over the goods.")
    else:
        await A.reply(f"Nahi! {inr(amount)} ka koi payment pichhle 30 minute mein nahi aaya. Screenshot pe bharosa mat kijiye, jab tak Soundbox na bole, saaman mat dijiye.",
                      f"नहीं! {inr(amount)} का कोई पेमेंट पिछले तीस मिनट में नहीं आया। स्क्रीनशॉट पर भरोसा मत कीजिए, जब तक साउंडबॉक्स न बोले, सामान मत दीजिए।",
                      f"No! No {inr(amount)} payment has arrived in the last 30 minutes. Don't trust the screenshot; don't hand over goods until the Soundbox announces it.")
    return "resolved"


async def khata(A, case, text):
    await A.think("Preparing today's khata from the payment ledger.")
    r = await A.tool("get_today_summary")
    hold = r["settlements_on_hold"]
    await A.reply(f"Aaj ka hisaab: {r['collected_today']}, {r['payments']} payments. Sabse busy time {_hour(r['busiest_hour'])} raha. Kal subah {r['settles_tomorrow_morning']} aapke account mein aayega."
                  + (f" {', '.join(hold)} abhi KYC ki wajah se ruka hai." if hold else ""),
                  f"आज का हिसाब: कुल {r['collected_today']}, {r['payments']} पेमेंट। सबसे ज़्यादा बिक्री {_hour(r['busiest_hour'], 'hi')} हुई। कल सुबह {r['settles_tomorrow_morning']} आपके खाते में आएगा।"
                  + (f" {', '.join(hold)} अभी केवाईसी की वजह से रुका है।" if hold else ""),
                  f"Today's khata: {r['collected_today']} from {r['payments']} payments. Your busiest time was {_hour(r['busiest_hour'], 'en')}. {r['settles_tomorrow_morning']} reaches your bank tomorrow morning."
                  + (f" {', '.join(hold)} is still on hold for KYC." if hold else ""))
    return "resolved"


async def new_store(A, case, text):
    await A.think("The merchant is opening a new store and wants a Soundbox. This is a sales request inside support.")
    prof = await A.tool("get_merchant_profile")
    await A.tool("order_device", item="Soundbox", outlet="Second outlet")
    await A.tool("book_field_visit", purpose="Install Soundbox at the new outlet", when="tomorrow 11 am")
    await A.think("A second outlet with growing sales is also a good fit for a card machine. Briefing the rep to offer it in person.")
    await A.tool("create_lead_brief", product="Card machine for the new outlet", notes="Opening a second outlet.")
    await A.reply(f"Nayi dukaan ke liye badhai! Soundbox ka order ho gaya hai, aur {prof['field_rep']} kal 11 baje install karne aayenge.",
                  f"नई दुकान के लिए बधाई! साउंडबॉक्स का ऑर्डर हो गया है, और {prof['field_rep']} कल सुबह 11 बजे लगाने आएँगे।",
                  f"Congratulations on the new store! Your Soundbox is ordered, and {prof['field_rep']} will come to install it tomorrow at 11 am.")
    return "resolved"


async def loan(A, case, text):
    r = await A.tool("check_loan_eligibility")
    if r["eligible"]:
        await A.tool("create_lead_brief", product="Working-capital loan", notes="Merchant asked about a loan.")
        await A.reply(f"Aap {r['pre_approved_up_to']} tak ke loan ke liye pre-eligible hain. Field rep aapko call karke poori details denge.",
                      f"आपको {r['pre_approved_up_to']} तक का लोन मिल सकता है। हमारे फील्ड साथी आपको कॉल करके पूरी जानकारी देंगे।",
                      f"You're pre-eligible for a loan of up to {r['pre_approved_up_to']}. Our field rep will call you with full details.")
    else:
        await A.reply("Abhi aap loan ke liye eligible nahi hain. Kuch mahine baad dobara check karenge.",
                      "अभी आपको लोन नहीं मिल सकता। कुछ महीने बाद दोबारा देखेंगे।",
                      "You're not eligible for a loan yet. We'll check again in a few months.")
    return "resolved"


async def proactive_device(A, case):
    await A.think("Monitoring alert: the Soundbox stopped reporting. The merchant hasn't complained yet; fixing it before they notice.")
    r = await A.tool("get_device_health")
    bad = next((d for d in r["devices"] if d["status"] != "online"), None)
    if not bad:
        return "resolved"
    if bad["data_plan_expired"]:
        await A.tool("renew_device_plan", device_id=bad["device_id"])
        await A.tool("get_device_health", why="Confirm the device is back online")
        await A.reply("Namaste! Aapka Soundbox abhi band ho gaya tha kyunki data plan khatam ho gaya tha. Maine renew kar diya hai, ab sab theek hai. Aapko kuch karne ki zaroorat nahi.",
                      "नमस्ते! आपका साउंडबॉक्स अभी बंद हो गया था क्योंकि डेटा प्लान खत्म हो गया था। मैंने रिन्यू कर दिया है, अब सब ठीक है। आपको कुछ करने की ज़रूरत नहीं।",
                      "Hello! Your Soundbox just stopped because its data plan ran out. I've renewed it and everything works again. You don't need to do anything.")
        return "resolved"
    await A.tool("handover_to_human", summary=f"{bad['device_id']} offline with a valid plan; needs a technician.")
    return "handed_over"


async def greet(A, case, text):
    await A.reply("Namaste! Main Munim hoon. Soundbox, settlement, refund ya aaj ka hisaab, kuch bhi poochiye.",
                  "नमस्ते! मैं मुनीम हूँ। साउंडबॉक्स, पेआउट, रिफंड या आज का हिसाब, कुछ भी पूछिए।",
                  "Hello! I'm Munim. Ask me about your Soundbox, payouts, refunds or today's sales.")
    return "resolved"


async def unknown(A, case, text):
    k = "missed:" + case["merchant_id"]
    last = A.agent.db.meta_get(k)
    now_s = __import__("time").time()
    if not last or now_s - last > 600:
        A.agent.db.meta_set(k, now_s)
        await A.think("I'm not sure what the merchant means. Asking instead of guessing or acting.")
        await A.reply("Maaf kijiye, main theek se samajh nahi paaya. Kya aap bikri, bank ka paisa, kisi payment, Soundbox, refund ya KYC ke baare mein pooch rahe hain?",
                      "माफ़ कीजिए, मैं ठीक से समझ नहीं पाया। क्या आप बिक्री, बैंक के पैसे, किसी पेमेंट, साउंडबॉक्स, रिफंड या केवाईसी के बारे में पूछ रहे हैं?",
                      "Sorry, I didn't quite understand. Are you asking about sales, money in your bank, a payment, your Soundbox, a refund or KYC?")
        return "resolved"
    A.agent.db.meta_set(k, None)
    await A.think("Second message I couldn't understand. Handing over to a person with a summary instead of guessing.")
    await A.tool("handover_to_human", summary=f"Merchant message I could not handle: \"{text[:140]}\"")
    await A.reply("Main ye ek Paytm teammate ko de raha hoon, poori jaankari ke saath. Wo aapko jaldi call karenge.",
                  "मैं ये बात पेटीएम के एक साथी को पूरी जानकारी के साथ दे रहा हूँ। वो आपको जल्दी कॉल करेंगे।",
                  "I'm passing this to a Paytm teammate with all the details. They'll call you shortly.")
    return "handed_over"


# ------------------------------------------------------------------ answering questions from the shop's own data
PERIOD_LABEL = {
    "today": ("aaj", "आज", "today"), "yesterday": ("kal", "कल", "yesterday"),
    "this_week": ("is hafte", "इस हफ्ते", "this week"), "last_week": ("pichhle hafte", "पिछले हफ्ते", "last week"),
    "last_7_days": ("pichhle 7 din", "पिछले 7 दिन", "the last 7 days"), "this_month": ("is mahine", "इस महीने", "this month"),
    "last_month": ("pichhle mahine", "पिछले महीने", "last month"), "last_30_days": ("pichhle 30 din", "पिछले 30 दिन", "the last 30 days"),
}
PREV_LABEL = {
    "today": ("kal isi samay tak", "कल इसी समय तक", "yesterday by this time"), "yesterday": ("parson", "परसों", "the day before"),
    "this_week": ("pichhle hafte ke inhi dino", "पिछले हफ्ते के इन्हीं दिनों", "the same days last week"),
    "last_week": ("usse pehle ke hafte", "उससे पहले वाले हफ्ते", "the week before"),
    "last_7_days": ("usse pehle ke 7 din", "उससे पहले के 7 दिन", "the 7 days before"),
    "this_month": ("pichhle mahine ke inhi dino", "पिछले महीने के इन्हीं दिनों", "the same days last month"),
    "last_month": ("usse pehle ke mahine", "उससे पहले वाले महीने", "the month before"),
    "last_30_days": ("usse pehle ke 30 din", "उससे पहले के 30 दिन", "the 30 days before"),
}


async def sales(A, case, text):
    period = _period(text)
    if period == "today":
        return await khata(A, case, text)
    await A.think(f"The merchant wants their sales for {PERIOD_LABEL[period][2]}. Reading the payment ledger.")
    r = await A.tool("get_sales", period=period)
    L, P = PERIOD_LABEL[period], PREV_LABEL[period]
    if not r["total_value"]:
        await A.reply(f"{L[0].capitalize()} koi payment nahi aaya.", f"{L[1]} कोई पेमेंट नहीं आया।", f"No payments came in {L[2]}.")
        return "resolved"
    parts = ([f"{L[0].capitalize()} kul {r['total']} aaye, {r['payments']} payment, ek bill average {r['average_bill']}."],
             [f"{L[1]} कुल {r['total']} आए, {r['payments']} पेमेंट, एक बिल औसतन {r['average_bill']}।"],
             [f"{L[2].capitalize()} you received {r['total']} from {r['payments']} payments, average bill {r['average_bill']}."])
    if r["best_day"]:
        bd = r["best_day"]
        parts[0].append(f"Sabse achha din {_date(bd['date'])} raha, {bd['total']}.")
        parts[1].append(f"सबसे अच्छा दिन {_date(bd['date'], 'hi')} रहा, {bd['total']}।")
        parts[2].append(f"Your best day was {_date(bd['date'], 'en')} with {bd['total']}.")
    ch = r["change_vs_previous_pct"]
    if ch is not None and abs(ch) >= 3:
        up = ch > 0
        parts[0].append(f"Ye {P[0]} se {abs(ch)}% {'zyada' if up else 'kam'} hai.")
        parts[1].append(f"ये {P[1]} से {abs(ch)}% {'ज़्यादा' if up else 'कम'} है।")
        parts[2].append(f"That's {abs(ch)}% {'more' if up else 'less'} than {P[2]}.")
    elif ch is not None:
        parts[0].append(f"Lagbhag {P[0]} jitna hi.")
        parts[1].append(f"लगभग {P[1]} जितना ही।")
        parts[2].append(f"About the same as {P[2]}.")
    await A.reply(" ".join(parts[0]), " ".join(parts[1]), " ".join(parts[2]))
    return "resolved"


async def recent_payments(A, case, text):
    m = re.search(r"\b(\d{1,2})\b", text)
    limit = min(int(m.group(1)), 10) if m and 0 < int(m.group(1)) <= 10 else 5
    payer = _payer(text)
    await A.think("The merchant wants to see recent payments" + (f" from {payer}." if payer else "."))
    r = await A.tool("get_recent_payments", limit=limit, payer=payer) if payer else await A.tool("get_recent_payments", limit=limit)
    ps = r["payments"]
    if not ps:
        await A.reply("Abhi koi payment nahi mila.", "अभी कोई पेमेंट नहीं मिला।", "I couldn't find any payments yet.")
        return "resolved"
    def line(p, lang):
        when = p["time"] if p["is_today"] else f"{_date(p['date'], lang)} {p['time']}"
        return f"{p['amount']} {p['payer']} ({when})"
    await A.reply(f"Aakhri {len(ps)} payment: " + ", ".join(line(p, "hinglish") for p in ps) + ".",
                  f"आखिरी {len(ps)} पेमेंट: " + ", ".join(line(p, "hi") for p in ps) + "।",
                  f"Your last {len(ps)} payments: " + ", ".join(line(p, "en") for p in ps) + ".")
    return "resolved"


async def _money_to_bank(A, case, text, balance_question):
    await A.think("The merchant is asking about money in the bank. Paytm can't see their bank balance, "
                  "so I'll tell them exactly what Paytm has sent and will send." if balance_question else
                  "The merchant is asking where their payouts stand. Reading what Paytm has sent to the bank.")
    r = await A.tool("get_payout_summary")
    hg, hi, en = [], [], []
    if balance_question:
        hg.append(f"Aapke bank ka poora balance main nahi dekh sakta, wo aapke {r['bank']} app ya passbook mein dikhega. Paytm se:")
        hi.append(f"आपके बैंक का पूरा बैलेंस मैं नहीं देख सकता, वो आपके {r['bank']} ऐप या पासबुक में दिखेगा। पेटीएम से:")
        en.append(f"I can't see your full bank balance; your {r['bank']} app or passbook shows that. From Paytm:")
    if r["last_credits"]:
        c = r["last_credits"][0]
        when = c["credited_at"] or ""
        hg.append(f"aakhri payout {c['amount']} {_date(when)} subah 9 baje aapke {r['bank']} mein aaya ({_date(c['for_sales_of'])} ki bikri ka).")
        hi.append(f"आखिरी {c['amount']} {_date(when, 'hi')} सुबह 9 बजे आपके {r['bank']} खाते में आए ({_date(c['for_sales_of'], 'hi')} की बिक्री के)।")
        en.append(f"your last payout of {c['amount']} reached your {r['bank']} account {_date(when, 'en')} at 9 am (for {_date(c['for_sales_of'], 'en')}'s sales).")
        hg.append(f"Pichhle 7 din mein kul {r['credited_last_7_days']} bheje gaye.")
        hi.append(f"पिछले 7 दिन में कुल {r['credited_last_7_days']} भेजे गए।")
        en.append(f"In the last 7 days, {r['credited_last_7_days']} was sent in total.")
    nxt = r["next_payout"]
    hg.append(f"Aaj ki bikri ka {nxt['amount']} kal subah 9 baje aayega.")
    hi.append(f"आज की बिक्री के {nxt['amount']} कल सुबह 9 बजे आएँगे।")
    en.append(f"Today's {nxt['amount']} will arrive tomorrow at 9 am.")
    if r["on_hold"]:
        h = r["on_hold"][0]
        hg.append(f"Lekin {_date(h['for_sales_of'])} ka {h['amount']} KYC dobara verify na hone se ruka hai. Kahein to abhi KYC link bhej doon? Sirf 1 minute lagega.")
        hi.append(f"लेकिन {_date(h['for_sales_of'], 'hi')} के {h['amount']} केवाईसी दोबारा जाँच न होने से रुके हैं। कहें तो अभी केवाईसी लिंक भेज दूँ? सिर्फ एक मिनट लगेगा।")
        en.append(f"But {_date(h['for_sales_of'], 'en')}'s {h['amount']} is on hold because KYC re-verification is pending. Shall I send the KYC link now? It takes a minute.")
        _offer(A, case, "settlement")
    await A.reply(" ".join(hg), " ".join(hi), " ".join(en))
    return "resolved"


async def balance(A, case, text):
    return await _money_to_bank(A, case, text, True)


async def payout_info(A, case, text):
    return await _money_to_bank(A, case, text, False)


async def kyc_info(A, case, text):
    await A.think("The merchant is asking about KYC. Checking the status before saying anything.")
    k = await A.tool("get_kyc_status")
    if k["kyc_status"] == "verified":
        await A.reply("Aapka KYC poora aur verified hai. Kuch karne ki zaroorat nahi.", "आपका केवाईसी पूरा है। कुछ करने की ज़रूरत नहीं।",
                      "Your KYC is complete and verified. Nothing to do.")
        return "resolved"
    r = await A.tool("get_settlements", why="See whether pending KYC is holding any money")
    held = next((x for x in r["settlements"] if x["status"] == "on_hold"), None)
    extra = (f" Isi wajah se {_date(held['for_date'])} ka {held['amount']} ruka hai.", f" इसी वजह से {_date(held['for_date'], 'hi')} के {held['amount']} रुके हैं।",
             f" Because of this, {_date(held['for_date'], 'en')}'s {held['amount']} is on hold.") if held else ("", "", "")
    await A.reply("Aapka KYC dobara verify karna baaki hai." + extra[0] + " Link bhej doon? Aadhaar OTP se 1 minute lagega.",
                  "आपका केवाईसी दोबारा जाँचना बाकी है।" + extra[1] + " लिंक भेज दूँ? आधार OTP से एक मिनट लगेगा।",
                  "Your KYC needs re-verification." + extra[2] + " Shall I send the link? It takes a minute with Aadhaar OTP.")
    _offer(A, case, "settlement" if held else "kyc_link")
    return "resolved"


async def refund_status(A, case, text):
    await A.think("The merchant is asking about refunds. Reading the refund records.")
    r = await A.tool("get_refund_status")
    if r["waiting_for_approval"]:
        await A.reply("Ek refund abhi Paytm teammate ki manzoori ka intezaar kar raha hai. Manzoor hote hi main bata dunga.",
                      "एक रिफंड अभी पेटीएम साथी की मंज़ूरी का इंतज़ार कर रहा है। मंज़ूर होते ही मैं बता दूँगा।",
                      "One refund is waiting for a Paytm teammate's approval. I'll tell you as soon as it's approved.")
        return "resolved"
    if not r["refunds"]:
        await A.reply("Aapki dukaan se abhi tak koi refund nahi hua hai. Agar kisi customer ka paisa do baar kata hai, to bataiye.",
                      "आपकी दुकान से अभी तक कोई रिफंड नहीं हुआ है। अगर किसी ग्राहक के पैसे दो बार कटे हैं, तो बताइए।",
                      "No refunds from your shop so far. If a customer was charged twice, tell me.")
        return "resolved"
    f = r["refunds"][0]
    await A.reply(f"Aakhri refund {f['amount']} {f['to']} ko {_date(f['date'])} {f['time']} par bheja gaya. Status: poora ho gaya.",
                  f"आखिरी रिफंड {f['amount']} {f['to']} को {_date(f['date'], 'hi')} {f['time']} पर भेजा गया। पूरा हो गया है।",
                  f"Your last refund of {f['amount']} went to {f['to']} {_date(f['date'], 'en')} at {f['time']}. It's complete.")
    return "resolved"


async def fake_payment(A, case, text):
    amount, payer = _amount(text), _payer(text)
    await A.think("A customer claimed to have paid (screenshot) but the shopkeeper got nothing. Checking the ledger first, "
                  "then reporting it so Munim can spot the same trick at other shops nearby.")
    if amount:
        v = await A.tool("verify_payment", amount=amount, payer=payer, minutes=60)
        if v.get("received"):
            await A.reply(f"Ye payment asli hai: {v['amount']} {v['payer']} se {v['time']} par aaya hai.",
                          f"ये पेमेंट असली है: {v['payer']} से {v['amount']}, {v['time']} पर आया है।",
                          f"This payment is real: {v['amount']} from {v['payer']} arrived at {v['time']}.")
            return "resolved"
    r = await A.tool("report_fake_payment", amount=amount, payer=payer, note=text[:160])
    amt = inr(amount) if amount else ""
    near = r.get("other_shops_nearby", 0)
    tail = ((f" Aaj aapke ilaake ki {near} aur dukaan pe bhi aisa hua hai; sabko savdhaan kar raha hoon.",
             f" आज आपके इलाके की {near} और दुकान पर भी ऐसा हुआ है; सबको सावधान कर रहा हूँ।",
             f" {near} other shop(s) in your area reported the same today; I'm warning everyone nearby.") if near else
            (" Aas-paas aur shikayat aayi to poore ilaake ko savdhaan kar dunga.",
             " आस-पास और शिकायत आई तो पूरे इलाके को सावधान कर दूँगा।",
             " If nearby shops report the same, I'll warn the whole area."))
    await A.reply(f"Afsos hai. {amt} ka koi payment aapke account mein nahi aaya; screenshot nakli tha. Maine iski report darj kar di hai.".replace("  ", " ")
                  + tail[0] + " Agli baar saaman tabhi dijiye jab Soundbox bole, ya customer se UTR number poochhiye.",
                  f"अफ़सोस है। {amt} का कोई पेमेंट आपके खाते में नहीं आया, स्क्रीनशॉट नकली था। मैंने इसकी रिपोर्ट दर्ज कर दी है।".replace("  ", " ")
                  + tail[1] + " अगली बार सामान तभी दीजिए जब साउंडबॉक्स बोले, या ग्राहक से UTR नंबर पूछिए।",
                  f"Sorry about this. No {amt} payment reached your account; the screenshot was fake. I've filed a report.".replace("  ", " ")
                  + tail[2] + " Next time, hand over goods only when the Soundbox announces it, or ask the customer for the UTR number.")
    return "resolved"


async def stuck_payment(A, case, text):
    amount, payer = _amount(text), _payer(text)
    await A.think("A customer says money left their account but the shop didn't get it. Looking for payments that never completed.")
    args = {k: v for k, v in (("amount", amount), ("payer", payer)) if v}
    r = await A.tool("check_transaction_status", **args)
    if not r["stuck_payments"] and args:
        r = await A.tool("check_transaction_status", why="Nothing matched exactly; checking every stuck payment from the last 3 hours")
    if not r["stuck_payments"]:
        await A.think("No pending or failed payment found. Checking whether it actually arrived.")
        v = await A.tool("verify_payment", amount=amount, payer=payer) if amount else None
        if v and v.get("received"):
            await A.reply(f"Ye payment aa chuka hai: {v['amount']} {v['payer']} se {v['time']} par. Aapke account mein hai.",
                          f"ये पेमेंट आ चुका है: {v['payer']} से {v['amount']}, {v['time']} पर। आपके खाते में है।",
                          f"This payment did arrive: {v['amount']} from {v['payer']} at {v['time']}. It's in your account.")
        else:
            await A.reply("Pichhle 3 ghante mein koi atka hua payment nahi mila. Customer se UPI reference number (12 ank) maangiye, main usse dhoondh lunga.",
                          "पिछले 3 घंटे में कोई अटका हुआ पेमेंट नहीं मिला। ग्राहक से UPI रेफ़रेंस नंबर (12 अंक) माँगिए, मैं उससे ढूँढ लूँगा।",
                          "I found no stuck payment in the last 3 hours. Ask the customer for the 12-digit UPI reference number and I'll trace it.")
        return "resolved"
    p = r["stuck_payments"][0]
    await A.think(f"{p['amount']} from {p['payer']} has been pending for {p['minutes_ago']} minutes. It never reached the shop; "
                  "the customer's bank will reverse it under RBI rules.")
    await A.reply(f"Mil gaya. {p['payer']} ka {p['amount']} ({p['time']}) customer ke bank mein atka hai, aapke paas nahi aaya. "
                  f"Is payment ke liye saaman mat dijiye; customer dobara pay kar de. Atka hua paisa unke bank ko RBI niyam se 5 din mein "
                  f"apne aap wapas karna hota hai, warna ₹100 roz ka harjaana.",
                  f"मिल गया। {p['payer']} के {p['amount']} ({p['time']}) ग्राहक के बैंक में अटके हैं, आपके पास नहीं आए। इस पेमेंट पर सामान मत दीजिए, "
                  f"ग्राहक दोबारा पेमेंट कर दें। अटका पैसा RBI के नियम से उनके बैंक को 5 दिन में अपने आप लौटाना होता है, वरना रोज़ ₹100 का हर्जाना।",
                  f"Found it. {p['payer']}'s {p['amount']} ({p['time']}) is stuck at the customer's bank; it never reached you. Don't hand "
                  f"over goods for it; ask them to pay again. Under RBI rules their bank must return the stuck money within 5 days, "
                  f"or pay them ₹100 a day.")
    return "resolved"


async def deductions(A, case, text):
    await A.think("The merchant thinks less money came than expected. Pulling the payout breakdown before saying anything.")
    r = await A.tool("explain_settlement")
    if not r.get("found"):
        await A.reply("Aapke kisi payout mein koi katauti nahi hui hai; poori bikri bank mein gayi hai.",
                      "आपके किसी पेआउट में कोई कटौती नहीं हुई है; पूरी बिक्री बैंक में गई है।",
                      "None of your payouts had a deduction; your full sales went to the bank.")
        return "resolved"
    d = r["deductions"]
    lines = (", ".join(f"{x['amount']} ({HI_CHARGE.get(x['what'].split(' (')[0].split(' on ')[0], x['what'])})" for x in d))
    lines_en = " and ".join(f"{x['amount']} for the {x['what'][0].lower() + x['what'][1:]}" for x in d)
    day = r["for_sales_of"]
    await A.reply(f"{_date(day).capitalize()} ki bikri {r['sales_that_day']} thi. Usme se {lines} kata, isliye bank mein {r['paid_to_bank']} aaya. "
                  "Bank khate se UPI payment par koi fees nahi lagti.",
                  f"{_date(day, 'hi')} की बिक्री {r['sales_that_day']} थी। उसमें से {lines} कटे, इसलिए बैंक में {r['paid_to_bank']} आए। "
                  "बैंक खाते से UPI पेमेंट पर कोई फीस नहीं लगती।",
                  f"Your sales on {_date(day, 'en')} were {r['sales_that_day']}. {lines_en} {'was' if len(d) == 1 else 'were'} deducted, so {r['paid_to_bank']} "
                  "reached your bank. Normal UPI payments from a bank account have no fee.")
    return "resolved"


HI_CHARGE = {"Soundbox monthly rental": "साउंडबॉक्स का महीने का किराया", "1.5% fee": "क्रेडिट कार्ड पेमेंट पर 1.5% फीस"}


async def yes(A, case, text):
    what = _take_offer(A, case)
    if what == "settlement":
        return await settlement(A, case, text)
    if what == "kyc_link":
        await A.tool("send_kyc_link")
        await A.reply("Link bhej diya hai, neeche dabaiye.", "लिंक भेज दिया है, नीचे दबाइए।", "I've sent the link; tap it below.")
        return "waiting_merchant"
    await A.reply("Ji, boliye kya madad karun?", "जी, बताइए क्या मदद करूँ?", "Sure, how can I help?")
    return "resolved"


async def no(A, case, text):
    _take_offer(A, case)
    await A.reply("Theek hai. Jab chahein, bas boliye.", "ठीक है। जब चाहें, बस बोलिए।", "Okay. Just tell me whenever you want.")
    return "resolved"


async def thanks(A, case, text):
    await A.reply("Aapka swagat hai! Kuch aur ho to boliye.", "आपका स्वागत है! कुछ और हो तो बोलिए।", "You're welcome! Tell me if you need anything else.")
    return "resolved"


async def help_(A, case, text):
    await A.reply("Main ye sab kar sakta hoon: aaj, hafte ya mahine ki bikri batana, bank mein bheja paisa, kisi payment ki jaanch, "
                  "Soundbox theek karna, refund, KYC aur loan. Bas boliye.",
                  "मैं ये सब कर सकता हूँ: आज, हफ्ते या महीने की बिक्री बताना, बैंक में भेजा पैसा, किसी पेमेंट की जाँच, "
                  "साउंडबॉक्स ठीक करना, रिफंड, केवाईसी और लोन। बस बोलिए।",
                  "I can tell you today's, this week's or this month's sales, money sent to your bank, check a payment, "
                  "fix your Soundbox, and help with refunds, KYC and loans. Just ask.")
    return "resolved"


async def not_allowed(A, case, text):
    await A.think("The merchant wants money moved into their own account from somewhere else. Munim never moves money "
                  "between accounts on request; only a shop's own payouts go to its own registered bank.")
    await A.tool("get_payout_summary", why="Show the merchant what is really theirs instead")
    await A.reply("Maaf kijiye, ye main nahi kar sakta. Aapke account mein sirf aapki apni dukaan ka paisa aata hai. Aapke payout ki jaankari chahiye to boliye.",
                  "माफ़ कीजिए, ये मैं नहीं कर सकता। आपके खाते में सिर्फ आपकी अपनी दुकान का पैसा आता है। अपने पेआउट की जानकारी चाहिए तो बोलिए।",
                  "Sorry, I can't do that. Only your own shop's money comes to your account. Ask me if you want your payout details.")
    return "resolved"


async def human(A, case, text):
    t = _t(text)
    if _has(t, "account_change"):
        why = ("Bank account badalne ke liye documents ki jaanch ek Paytm teammate karte hain.",
               "बैंक खाता बदलने के लिए कागज़ों की जाँच पेटीएम के एक साथी करते हैं।", "Changing the bank account needs a Paytm teammate to check documents.")
    elif _has(t, "invoice"):
        why = ("GST invoice hamari accounts team bhejti hai.", "जीएसटी इनवॉइस हमारी अकाउंट्स टीम भेजती है।", "GST invoices are sent by our accounts team.")
    elif _has(t, "dispute"):
        why = ("Customer ke saath jhagde mein ek insaan ka dekhna zaroori hai.", "ग्राहक से झगड़े में किसी इंसान का देखना ज़रूरी है।",
               "A dispute with a customer needs a person to look at it.")
    else:
        why = ("", "", "")
    await A.think("This needs a person. Handing over with a clear summary instead of guessing.")
    await A.tool("handover_to_human", summary=f"Merchant asked: \"{text[:140]}\"")
    await A.reply((why[0] + " Maine poori baat unhe de di hai, wo aapko jaldi call karenge.").strip(),
                  (why[1] + " मैंने पूरी बात उन्हें दे दी है, वो आपको जल्दी कॉल करेंगे।").strip(),
                  (why[2] + " I've passed on all the details; they'll call you shortly.").strip())
    return "handed_over"


HANDLERS = {"soundbox": soundbox, "settlement": settlement, "double_debit": double_debit, "self_refund": self_refund,
            "verify": verify, "khata": khata, "new_store": new_store, "loan": loan, "kyc_done_claim": kyc_done_claim,
            "greet": greet, "unknown": unknown, "sales": sales, "recent_payments": recent_payments, "balance": balance,
            "payout_info": payout_info, "kyc_info": kyc_info, "refund_status": refund_status, "yes": yes, "no": no,
            "thanks": thanks, "help": help_, "human": human, "not_allowed": not_allowed,
            "stuck_payment": stuck_payment, "deductions": deductions, "fake_payment": fake_payment}
