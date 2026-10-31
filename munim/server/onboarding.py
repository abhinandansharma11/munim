"""Voice onboarding: a new shopkeeper joins Paytm by talking to Munim.

Munim asks one simple question at a time (Hindi or English, voice or tap), fills the application itself, then runs the
same agent loop as support: it checks identity, bank and duplicates, decides whether it may activate the shop on its own
(or asks a Paytm teammate), activates the QR, orders the device and books the field rep's installation visit.
"""
import json
import re
import uuid

from .db import iso, now

CATEGORIES = [
    ("Kirana store", "किराना", ["kirana", "grocery", "general store", "किराना", "राशन", "ration"]),
    ("Tea & snacks", "चाय-नाश्ता", ["chai", "tea", "चाय", "nashta", "नाश्ता", "food", "dhaba", "ढाबा", "restaurant", "snack", "samosa"]),
    ("Pharmacy", "मेडिकल", ["medical", "pharmacy", "dawa", "दवा", "मेडिकल", "chemist"]),
    ("Electronics", "मोबाइल-इलेक्ट्रॉनिक्स", ["mobile", "electronic", "मोबाइल", "इलेक्ट्रॉनिक", "phone"]),
    ("Clothes", "कपड़े", ["kapde", "kapda", "कपड़े", "cloth", "garment", "saree", "साड़ी"]),
    ("Other", "अन्य", []),
]
BANKS = [("SBI", ["sbi", "state bank", "स्टेट बैंक", "एसबीआई"]), ("HDFC", ["hdfc", "एचडीएफसी"]), ("ICICI", ["icici", "आईसीआईसीआई"]),
         ("PNB", ["pnb", "punjab", "पंजाब"]), ("Bank of Baroda", ["baroda", "bob", "बड़ौदा"]), ("Other bank", [])]
DEVICES = {
    "soundbox": ("Soundbox + QR", "साउंडबॉक्स + QR"),
    "card": ("Soundbox + card machine", "साउंडबॉक्स + कार्ड मशीन"),
    "qr": ("Only QR (no device)", "सिर्फ QR (बिना मशीन)"),
}
CITIES = {"indore": "Indore", "इंदौर": "Indore", "bhopal": "Bhopal", "भोपाल": "Bhopal", "pune": "Pune", "पुणे": "Pune",
          "delhi": "Delhi", "दिल्ली": "Delhi", "lucknow": "Lucknow", "लखनऊ": "Lucknow", "jaipur": "Jaipur", "जयपुर": "Jaipur"}

STEPS = ["shop", "owner", "category", "area", "mobile", "kyc", "bank", "acct", "device", "confirm"]


def _clean(text, fillers):
    t = re.sub(r"[।.!?,]+$", "", text.strip())
    for f in fillers:
        t = re.sub(re.escape(f), " ", t, flags=re.I)
    t = re.sub(r"\s+(hai|है|ji|जी|h)\s*$", "", t.strip(), flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" ,.-")
    return " ".join(w.capitalize() if w.isascii() else w for w in t.split())


def _pick(text, table):
    t = text.lower()
    for item in table:
        if any(k in t for k in item[-1]):
            return item
    return table[-1]


def recommend(category):
    return "card" if category in ("Electronics", "Clothes") else "soundbox"


def question(key, d, ack=("", "")):
    """The next thing Munim asks, in Hindi and English, with tap options where they help."""
    a_hi, a_en = ack
    q = {"key": key, "kind": "text", "step": STEPS.index(key) + 1, "total": len(STEPS)}
    if key == "shop":
        q.update(hi="नमस्ते! मैं मुनीम हूँ। दो मिनट में आपकी दुकान पेटीएम पर जोड़ देता हूँ। आपकी दुकान का नाम क्या है?",
                 en="Namaste! I'm Munim. I'll add your shop to Paytm in two minutes. What's your shop's name?")
    elif key == "owner":
        q.update(hi="और आपका नाम?", en="And your name?")
    elif key == "category":
        q.update(kind="choice", hi="आप क्या बेचते हैं?", en="What do you sell?",
                 options=[{"value": c[0], "en": c[0], "hi": c[1]} for c in CATEGORIES])
    elif key == "area":
        q.update(hi="दुकान कहाँ है? इलाका और शहर बताइए।", en="Where is the shop? Tell me the area and city.",
                 options=[{"value": "Vijay Nagar, Indore", "en": "Vijay Nagar, Indore", "hi": "विजय नगर, इंदौर"}])
    elif key == "mobile":
        q.update(kind="tel", hi="आपका मोबाइल नंबर? इस पर एक OTP आएगा।", en="Your mobile number? You'll get an OTP on it.")
    elif key == "kyc":
        q.update(kind="otp", hi="अब आधार से केवाईसी। आधार से जुड़े मोबाइल पर OTP आएगा, मैं अपने आप भर दूँगा।",
                 en="Now KYC with Aadhaar. An OTP comes to your Aadhaar-linked mobile; I'll fill it in for you.")
    elif key == "bank":
        q.update(kind="choice", hi="पैसा किस बैंक खाते में चाहिए?", en="Which bank account should the money go to?",
                 options=[{"value": b[0], "en": b[0], "hi": b[0]} for b in BANKS])
    elif key == "acct":
        q.update(kind="digits4", hi="खाता नंबर के आखिरी 4 अंक बताइए।", en="Tell me the last 4 digits of the account number.")
    elif key == "device":
        rec = recommend(d.get("category"))
        why_hi = "ज़्यादातर ग्राहक UPI से छोटे पेमेंट करते हैं" if rec == "soundbox" else "बड़े बिल पर ग्राहक कार्ड से भी देना चाहेंगे"
        why_en = "most customers pay small amounts by UPI" if rec == "soundbox" else "for bigger bills, customers will also want to pay by card"
        order = [rec] + [k for k in DEVICES if k != rec]
        q.update(kind="choice", hi=f"आपकी दुकान के लिए मेरी सलाह: {DEVICES[rec][1]}, क्योंकि {why_hi}। ठीक है?",
                 en=f"My suggestion for your shop: {DEVICES[rec][0]}, because {why_en}. Okay?",
                 options=[{"value": k, "en": DEVICES[k][0] + (" (suggested)" if k == rec else ""),
                           "hi": DEVICES[k][1] + (" (सलाह)" if k == rec else "")} for k in order])
    elif key == "confirm":
        q.update(kind="confirm", hi="बस हो गया! एक बार देख लीजिए, सब सही है तो शुरू करें दबाइए।",
                 en="All done! Check once; if everything is right, tap Start.", summary=summary(d))
    q["hi"], q["en"] = (a_hi + " " + q["hi"]).strip(), (a_en + " " + q["en"]).strip()
    return q


def summary(d):
    return [
        {"en": "Shop", "hi": "दुकान", "v": d.get("shop", "")},
        {"en": "Owner", "hi": "मालिक", "v": d.get("owner", "")},
        {"en": "Business", "hi": "धंधा", "v": d.get("category", "")},
        {"en": "Location", "hi": "जगह", "v": f"{d.get('area', '')}, {d.get('city', '')}"},
        {"en": "Mobile", "hi": "मोबाइल", "v": d.get("mobile", "")[:2] + "••••" + d.get("mobile", "")[-4:], "ok": True},
        {"en": "KYC", "hi": "केवाईसी", "v": "Aadhaar OTP", "ok": True},
        {"en": "Bank", "hi": "बैंक", "v": f"{d.get('bank', '')} ••{d.get('acct', '')}"},
        {"en": "Device", "hi": "मशीन", "v": DEVICES.get(d.get("device", "soundbox"))[0]},
    ]


def answer(d, key, text):
    """Fill one field from the shopkeeper's words. Returns (ack_hi, ack_en) or raises ValueError(hi, en)."""
    t = (text or "").strip()
    if key == "shop":
        v = _clean(t, ["meri dukaan ka naam", "meri dukan ka naam", "dukaan ka naam", "dukan ka naam", "shop ka naam",
                       "my shop is called", "my shop's name is", "my shop name is", "shop name is", "my shop is",
                       "मेरी दुकान का नाम", "दुकान का नाम"])
        if len(v) < 2:
            raise ValueError("दुकान का नाम फिर से बताइए।", "Please say the shop's name again.")
        d["shop"] = v
        return f"बढ़िया, {v}!", f"Great, {v}!"
    if key == "owner":
        v = _clean(t, ["mera naam", "my name is", "i am", "i'm", "मेरा नाम", "मैं"])
        if len(v) < 2:
            raise ValueError("अपना नाम फिर से बताइए।", "Please say your name again.")
        d["owner"] = v
        return f"नमस्ते {v.split()[0]} जी।", f"Hello {v.split()[0]}."
    if key == "category":
        c = _pick(t, CATEGORIES)
        d["category"] = c[0]
        return "", ""
    if key == "area":
        city = next((v for k, v in CITIES.items() if k in t.lower()), "Indore")
        area = "Vijay Nagar" if ("vijay nagar" in t.lower() or "विजय नगर" in t) else _clean(re.sub(
            "|".join(map(re.escape, CITIES)), "", t, flags=re.I), ["dukaan", "dukan", "दुकान", "mein", "में", "hai", "है", "at", "in"])
        d["area"], d["city"] = area or "Vijay Nagar", city
        return "", ""
    if key == "mobile":
        digits = re.sub(r"\D", "", t)
        if len(digits) < 10:
            raise ValueError("10 अंक का मोबाइल नंबर बताइए।", "Please give a 10-digit mobile number.")
        d["mobile"] = digits[-10:]
        d["mobile_verified"] = True
        return "OTP से नंबर पक्का हो गया।", "Number verified with OTP."
    if key == "kyc":
        d["kyc"] = "verified"
        return "केवाईसी पूरा हुआ।", "KYC done."
    if key == "bank":
        d["bank"] = _pick(t, BANKS)[0]
        return "", ""
    if key == "acct":
        digits = re.sub(r"\D", "", t)
        if len(digits) < 4:
            raise ValueError("खाते के आखिरी 4 अंक बताइए।", "Please give the last 4 digits of the account.")
        d["acct"] = digits[-4:]
        return "", ""
    if key == "device":
        tl = t.lower()
        if tl in DEVICES:
            d["device"] = tl
        elif any(w in tl for w in ("card", "कार्ड")):
            d["device"] = "card"
        elif any(w in tl for w in ("sirf qr", "only qr", "सिर्फ")):
            d["device"] = "qr"
        else:  # "haan / ok / theek hai" = take the suggestion
            d["device"] = recommend(d.get("category"))
        return "", ""
    return "", ""


# ------------------------------------------------------------------ sessions
def start(db):
    sid = uuid.uuid4().hex[:12]
    db.x("INSERT INTO onboarding(id, data, step, status, created) VALUES (?,?,?,?,?)", (sid, "{}", "shop", "asking", iso(now())))
    return sid, question("shop", {})


def step(db, sid, text):
    s = db.one("SELECT * FROM onboarding WHERE id=?", (sid,))
    if not s:
        raise KeyError("No such sign-up")
    d, key = json.loads(s["data"]), s["step"]
    try:
        ack = answer(d, key, text)
    except ValueError as e:
        return {"error": {"hi": e.args[0], "en": e.args[1]}, "next": question(key, d)}
    nxt = STEPS[STEPS.index(key) + 1] if key != "confirm" else "confirm"
    db.x("UPDATE onboarding SET data=?, step=? WHERE id=?", (json.dumps(d), nxt, sid))
    return {"next": question(nxt, d, ack)}


# ------------------------------------------------------------------ the agent part: check, decide, act
async def finish(agent, db, sid):
    """Runs on 'Start': creates the shop, checks it, activates it (or asks a teammate), orders the device, books the rep."""
    from .agent import Facade
    s = db.one("SELECT * FROM onboarding WHERE id=?", (sid,))
    d = json.loads(s["data"])
    if s["merchant_id"]:
        return {"merchant_id": s["merchant_id"], "status": s["status"]}
    n = db.one("SELECT COUNT(*) n FROM merchants")["n"]
    mid = f"M{1001 + n}"
    db.x("INSERT INTO merchants VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
         (mid, d["shop"], d["owner"], d.get("city", "Indore"), d["mobile"][:5] + " " + d["mobile"][5:7] + "xxx", d["category"],
          "verified", f"{d['bank']} ••{d['acct']}", 0, json.dumps([0, 0, 0]), 0, 1, "Anil Verma", d.get("area", "Vijay Nagar")))
    db.x("UPDATE onboarding SET merchant_id=?, status='checking' WHERE id=?", (mid, sid))
    case = agent._new_case(mid, "onboarding", f"New shop sign-up: {d['shop']}")
    db.x("UPDATE onboarding SET case_id=? WHERE id=?", (case["id"], sid))
    agent._set_case(case["id"], brain="rules")
    A = Facade(agent, case)
    mins = max(1, round((now() - __import__("datetime").datetime.fromisoformat(s["created"])).total_seconds() / 60))
    await agent._step(case["id"], "event", f"New shopkeeper signed up by talking to Munim in the app: {d['shop']} "
                      f"({d['category']}, {d.get('area')}). Took {mins} min, no forms.", actor="Merchant")
    await A.think("Before this shop goes live I must check identity, the bank account and duplicates. "
                  "If everything is clean I can activate it myself; if anything looks off, a Paytm teammate decides.")
    await A.tool("verify_bank_account")
    checks = await A.tool("run_onboarding_checks")
    res = await A.tool("activate_merchant")
    if res.get("status") == "waiting_for_human_approval":
        db.x("UPDATE onboarding SET status='waiting_human' WHERE id=?", (sid,))
        flags = "; ".join(checks.get("flags", []))
        await A.reply(f"Aapki details mil gayi. Ek cheez dobara dekhni hai ({flags}), isliye Paytm ke ek saathi abhi check kar rahe hain. Kuch minute lagenge.",
                      "आपकी जानकारी मिल गई। एक चीज़ दोबारा देखनी है, इसलिए पेटीएम के एक साथी अभी जाँच रहे हैं। कुछ मिनट लगेंगे।",
                      "Got your details. One thing needs a second look, so a Paytm teammate is checking it now. It takes a few minutes.")
        agent._set_case(case["id"], status="waiting_human")
        await agent.bus.emit("case", case_id=case["id"], merchant_id=mid, status="waiting_human")
        return {"merchant_id": mid, "status": "waiting_human"}
    out = await go_live(A, agent, db, mid, d)
    agent._set_case(case["id"], status="resolved", resolved=iso(now()))
    await agent.bus.emit("phase", case_id=case["id"], phase="done", merchant_id=mid)
    await agent.bus.emit("case", case_id=case["id"], merchant_id=mid, status="resolved")
    return out


async def go_live(A, agent, db, mid, d=None):
    """After activation: order the device, book the installation, welcome the shopkeeper."""
    if d is None:
        d = json.loads(db.one("SELECT data FROM onboarding WHERE merchant_id=?", (mid,))["data"])
    m = db.one("SELECT * FROM merchants WHERE id=?", (mid,))
    dev = d.get("device", "soundbox")
    upi = db.one("SELECT data FROM onboarding WHERE merchant_id=?", (mid,))
    upi_id = json.loads(upi["data"]).get("upi_id", "")
    visit = None
    if dev != "qr":
        await A.tool("order_device", item=DEVICES[dev][0], outlet=m["shop"])
        v = await A.tool("book_field_visit", purpose=f"Install {DEVICES[dev][0]} at a new shop", when="tomorrow 11 am")
        visit = v.get("visit")
    first = m["owner"].split()[0]
    if visit:
        await A.reply(f"Badhai ho {first} ji! {m['shop']} ab Paytm par hai. Aapka QR abhi se chalu hai ({upi_id}). "
                      f"{DEVICES[dev][0]} kal subah 11 baje {m['rep']} lagane aayenge.",
                      f"बधाई हो {first} जी! {m['shop']} अब पेटीएम पर है। आपका QR अभी से चालू है। "
                      f"{DEVICES[dev][1]} कल सुबह 11 बजे {m['rep']} लगाने आएँगे।",
                      f"Congratulations {first}! {m['shop']} is now on Paytm. Your QR works from right now ({upi_id}). "
                      f"{m['rep']} will install your {DEVICES[dev][0]} tomorrow at 11 am.")
    else:
        await A.reply(f"Badhai ho {first} ji! {m['shop']} ab Paytm par hai. Aapka QR abhi se chalu hai ({upi_id}).",
                      f"बधाई हो {first} जी! {m['shop']} अब पेटीएम पर है। आपका QR अभी से चालू है।",
                      f"Congratulations {first}! {m['shop']} is now on Paytm. Your QR works from right now ({upi_id}).")
    db.x("UPDATE onboarding SET status='active', done=? WHERE merchant_id=?", (iso(now()), mid))
    await agent.bus.emit("onboarded", merchant_id=mid, status="active", upi_id=upi_id, visit=visit)
    return {"merchant_id": mid, "status": "active", "upi_id": upi_id, "visit": visit, "device": DEVICES[dev]}


def stats(db):
    rows = db.q("SELECT * FROM onboarding WHERE status='active' AND done IS NOT NULL")
    from datetime import datetime
    mins = [(datetime.fromisoformat(r["done"]) - datetime.fromisoformat(r["created"])).total_seconds() / 60 for r in rows]
    return {"signed_up": len(rows), "avg_minutes": round(sum(mins) / len(mins), 1) if mins else None}
