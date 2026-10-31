"""Munim's tools: the actions it can take on (mock) Paytm systems.

Each tool has a risk tier:
  read      - only reads data
  auto      - changes data, low risk and reversible (Munim may do it alone; one-tap Undo)
  merchant  - needs the merchant to do or confirm something
  human     - needs a Paytm teammate to approve (decided by the policy gateway)
"""
import json
import re
from datetime import datetime, timedelta

from . import config
from .db import iso, now


def inr(n):
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if n < 0 else "") + "₹" + s


HI_PRODUCT = {"Install Soundbox + QR at a new shop": "नई दुकान में साउंडबॉक्स + QR लगाना",
              "Install Soundbox + card machine at a new shop": "नई दुकान में साउंडबॉक्स + कार्ड मशीन लगाना","Working-capital loan": "बिज़नेस लोन", "Card machine for the new outlet": "नई दुकान के लिए कार्ड मशीन",
              "Install Soundbox at the new outlet": "नई दुकान में साउंडबॉक्स लगाना"}


def _merchant(db, mid):
    return db.one("SELECT * FROM merchants WHERE id=?", (mid,))


# ---------------------------------------------------------------- read tools
def get_merchant_profile(db, ctx):
    m = _merchant(db, ctx["merchant_id"])
    vol = json.loads(m["monthly_volume"])
    growth = round((vol[-1] - vol[0]) / vol[0] * 100) if vol[0] else 0
    return {
        "merchant_id": m["id"], "shop": m["shop"], "owner": m["owner"], "city": m["city"],
        "category": m["category"], "kyc_status": m["kyc_status"], "bank": m["bank"],
        "months_on_paytm": m["months_active"], "outlets": m["outlets"],
        "monthly_collections_last_3": [inr(v) for v in vol], "growth_3_months_pct": growth,
        "field_rep": m["rep"],
    }


def get_device_health(db, ctx):
    out = []
    for d in db.q("SELECT * FROM devices WHERE merchant_id=?", (ctx["merchant_id"],)):
        expired = datetime.fromisoformat(d["plan_expires"]) < now()
        diagnosis = "working normally"
        if d["status"] == "not_installed":
            diagnosis = "not installed yet: the field rep is booked to install it"
        elif d["status"] != "online":
            diagnosis = "offline because its SIM data plan expired" if expired else "offline: no network signal"
        out.append({"device_id": d["id"], "type": d["kind"], "status": d["status"],
                    "data_plan_expired": expired, "data_plan_expires": d["plan_expires"][:10],
                    "battery_pct": d["battery"], "last_seen": d["last_seen"], "diagnosis": diagnosis})
    return {"devices": out}


def get_settlements(db, ctx):
    rows = db.q("SELECT * FROM settlements WHERE merchant_id=? ORDER BY for_date DESC LIMIT 5", (ctx["merchant_id"],))
    reasons = {"kyc_reverification": "on hold until the merchant re-verifies KYC"}
    return {"settlements": [{
        "settlement_id": r["id"], "for_date": r["for_date"], "amount": inr(r["amount"]),
        "amount_value": r["amount"], "status": r["status"],
        "hold_reason": reasons.get(r["hold_reason"], r["hold_reason"]), "credited_at": r["credited_at"],
        "sales_that_day": inr(r["gross"] or r["amount"]),
        "deductions": [{"what": c["what"], "amount": inr(c["amount"])} for c in json.loads(r["charges"] or "[]")],
    } for r in rows]}


def get_kyc_status(db, ctx):
    m = _merchant(db, ctx["merchant_id"])
    link = db.one("SELECT * FROM kyc_links WHERE merchant_id=? ORDER BY created DESC LIMIT 1", (m["id"],))
    return {"kyc_status": m["kyc_status"], "latest_link": link and {"link_id": link["id"], "status": link["status"]}}


def search_payments(db, ctx, amount=None, payer=None, minutes=120):
    since = iso(now() - timedelta(minutes=int(minutes or 120)))
    sql, args = "SELECT * FROM transactions WHERE merchant_id=? AND ts>=? AND status='success'", [ctx["merchant_id"], since]
    if amount:
        sql += " AND amount=?"
        args.append(int(amount))
    if payer:
        sql += " AND lower(payer) LIKE ?"
        args.append("%" + str(payer).lower().split()[0] + "%")
    rows = db.q(sql + " ORDER BY ts", tuple(args))
    refunded = {r["txn_id"] for r in db.q("SELECT txn_id FROM refunds WHERE merchant_id=?", (ctx["merchant_id"],))}
    out = []
    for i, r in enumerate(rows):
        dup_of = None
        for prev in rows[:i]:
            gap = (datetime.fromisoformat(r["ts"]) - datetime.fromisoformat(prev["ts"])).total_seconds()
            if prev["payer_vpa"] == r["payer_vpa"] and prev["amount"] == r["amount"] and gap <= 120 and not r["order_id"]:
                dup_of = prev["id"]
        hh, mm = int(r["ts"][11:13]), r["ts"][14:16]
        out.append({"txn_id": r["id"], "amount": inr(r["amount"]), "amount_value": r["amount"], "payer": r["payer"],
                    "payer_vpa": r["payer_vpa"], "time": f"{(hh - 1) % 12 + 1}:{mm} {'am' if hh < 12 else 'pm'}", "order_id": r["order_id"],
                    "likely_duplicate_of": dup_of, "already_refunded": r["id"] in refunded})
    return {"payments": out[-12:], "count": len(out)}


def active_area_alert(db, mid):
    m = _merchant(db, mid)
    return db.one("SELECT * FROM fraud_alerts WHERE area=? AND created>=? ORDER BY created DESC LIMIT 1",
                  (m["area"], iso(now() - timedelta(hours=3))))


def verify_payment(db, ctx, amount, payer=None, minutes=30):
    res = search_payments(db, ctx, amount=amount, payer=payer, minutes=minutes)
    found = res["payments"]
    if found:
        p = found[-1]
        return {"received": True, "amount": p["amount"], "payer": p["payer"], "time": p["time"], "txn_id": p["txn_id"]}
    out = {"received": False, "checked": f"No {inr(int(amount))} payment"
           + (f" from {payer}" if payer else "") + f" in the last {minutes} minutes"}
    alert = active_area_alert(db, ctx["merchant_id"])
    if alert:
        out["area_fraud_alert"] = (f"Fraud alert active in {alert['area']}: {len(json.loads(alert['shops']))} shops reported fake "
                                   f"{alert['amount_text']} payment claims in the last few hours.")
    return out


def get_today_summary(db, ctx):
    start = iso(now().replace(hour=0, minute=0, second=0))
    rows = db.q("SELECT * FROM transactions WHERE merchant_id=? AND ts>=? AND status='success'", (ctx["merchant_id"], start))
    total = sum(r["amount"] for r in rows)
    refunds = db.q("SELECT * FROM refunds WHERE merchant_id=? AND created>=?", (ctx["merchant_id"], start))
    refunded = sum(r["amount"] for r in refunds)
    by_hour = {}
    for r in rows:
        by_hour[r["ts"][11:13]] = by_hour.get(r["ts"][11:13], 0) + r["amount"]
    busiest = max(by_hour, key=by_hour.get) if by_hour else None
    held = db.q("SELECT * FROM settlements WHERE merchant_id=? AND status='on_hold'", (ctx["merchant_id"],))
    return {"collected_today": inr(total), "collected_value": total, "payments": len(rows),
            "refunded_today": inr(refunded), "busiest_hour": f"{busiest}:00" if busiest else None,
            "settles_tomorrow_morning": inr(total - refunded),
            "settlements_on_hold": [inr(h["amount"]) for h in held]}


def check_loan_eligibility(db, ctx):
    m = _merchant(db, ctx["merchant_id"])
    vol = json.loads(m["monthly_volume"])
    growth = round((vol[-1] - vol[0]) / vol[0] * 100) if vol[0] else 0
    eligible = m["loan_limit"] > 0 and m["months_active"] >= 12 and growth > 10
    reasons = [f"{m['months_active']} months on Paytm", f"collections up {growth}% in 3 months"]
    return {"eligible": eligible, "product": "Working-capital loan", "pre_approved_up_to": inr(m["loan_limit"]),
            "reasons": reasons if eligible else ["volume growth or history below threshold"],
            "needs_kyc_first": m["kyc_status"] != "verified"}


PERIODS = ("today", "yesterday", "this_week", "last_week", "last_7_days", "this_month", "last_month", "last_30_days")


def _period_range(period):
    t = now()
    d0 = t.replace(hour=0, minute=0, second=0)
    p = period if period in PERIODS else "today"
    if p == "today":
        return p, d0, t
    if p == "yesterday":
        return p, d0 - timedelta(days=1), d0
    if p == "this_week":
        return p, d0 - timedelta(days=d0.weekday()), t
    if p == "last_week":
        start = d0 - timedelta(days=d0.weekday() + 7)
        return p, start, start + timedelta(days=7)
    if p == "last_7_days":
        return p, d0 - timedelta(days=7), d0
    if p == "this_month":
        return p, d0.replace(day=1), t
    if p == "last_month":
        end = d0.replace(day=1)
        return p, (end - timedelta(days=1)).replace(day=1), end
    return p, d0 - timedelta(days=30), d0


def _clock(ts):
    hh, mm = int(ts[11:13]), ts[14:16]
    return f"{(hh - 1) % 12 + 1}:{mm} {'am' if hh < 12 else 'pm'}"


def _sum(db, mid, a, b):
    rows = db.q("SELECT * FROM transactions WHERE merchant_id=? AND ts>=? AND ts<? AND status='success'", (mid, iso(a), iso(b)))
    return rows, sum(r["amount"] for r in rows)


def get_sales(db, ctx, period="today"):
    mid = ctx["merchant_id"]
    p, a, b = _period_range(period)
    rows, total = _sum(db, mid, a, b)
    span = b - a
    _, prev_total = _sum(db, mid, a - span, a)
    first = db.one("SELECT MIN(ts) AS f FROM transactions WHERE merchant_id=?", (mid,))["f"]
    if not first or first > iso(a - span):
        prev_total = 0  # not enough history to compare fairly
    by_day, by_hour, by_payer = {}, {}, {}
    for r in rows:
        by_day[r["ts"][:10]] = by_day.get(r["ts"][:10], 0) + r["amount"]
        by_hour[r["ts"][11:13]] = by_hour.get(r["ts"][11:13], 0) + 1
        by_payer[r["payer"]] = by_payer.get(r["payer"], 0) + r["amount"]
    big = max(rows, key=lambda r: r["amount"]) if rows else None
    best = max(by_day.items(), key=lambda x: x[1]) if len(by_day) > 1 else None
    busiest = max(by_hour, key=by_hour.get) if by_hour else None
    return {
        "period": p, "from": a.date().isoformat(), "to": (b - timedelta(seconds=1)).date().isoformat(),
        "total": inr(total), "total_value": total, "payments": f"{len(rows):,}",
        "average_bill": inr(total / len(rows)) if rows else inr(0),
        "biggest_payment": big and {"amount": inr(big["amount"]), "payer": big["payer"], "date": big["ts"][:10], "time": _clock(big["ts"])},
        "best_day": best and {"date": best[0], "total": inr(best[1])},
        "busiest_hour": f"{busiest}:00" if busiest else None,
        "previous_period_total": inr(prev_total),
        "change_vs_previous_pct": round((total - prev_total) / prev_total * 100) if prev_total else None,
        "top_customers": [{"payer": k, "total": inr(v)} for k, v in sorted(by_payer.items(), key=lambda x: -x[1])[:3]],
        "note": "Partial period: counted up to now." if b >= now() - timedelta(seconds=5) else "",
    }


def get_recent_payments(db, ctx, limit=5, payer=None):
    sql, args = "SELECT * FROM transactions WHERE merchant_id=? AND status='success'", [ctx["merchant_id"]]
    if payer:
        sql += " AND lower(payer) LIKE ?"
        args.append("%" + str(payer).lower().split()[0] + "%")
    rows = db.q(sql + " ORDER BY ts DESC LIMIT ?", (*args, max(1, min(int(limit or 5), 20))))
    today = now().date().isoformat()
    return {"payments": [{"txn_id": r["id"], "amount": inr(r["amount"]), "payer": r["payer"], "date": r["ts"][:10],
                          "is_today": r["ts"][:10] == today, "time": _clock(r["ts"])} for r in rows]}


def get_payout_summary(db, ctx):
    """What Paytm has sent (and will send) to the merchant's bank. Paytm cannot see the bank account balance itself."""
    mid = ctx["merchant_id"]
    m = _merchant(db, mid)
    rows = db.q("SELECT * FROM settlements WHERE merchant_id=? ORDER BY for_date DESC LIMIT 10", (mid,))
    credited = [r for r in rows if r["status"] == "settled"]
    held = [r for r in rows if r["status"] == "on_hold"]
    week_ago = (now() - timedelta(days=7)).date().isoformat()
    today_sum = get_today_summary(db, ctx)
    reasons = {"kyc_reverification": "KYC re-verification pending"}
    return {
        "bank": m["bank"],
        "bank_balance_visible_to_paytm": False,
        "last_credits": [{"for_sales_of": r["for_date"], "amount": inr(r["amount"]), "credited_at": r["credited_at"]} for r in credited[:3]],
        "credited_last_7_days": inr(sum(r["amount"] for r in credited if r["for_date"] >= week_ago)),
        "on_hold": [{"settlement_id": r["id"], "for_sales_of": r["for_date"], "amount": inr(r["amount"]),
                     "reason": reasons.get(r["hold_reason"], r["hold_reason"])} for r in held],
        "next_payout": {"amount": today_sum["settles_tomorrow_morning"], "for_sales_of": now().date().isoformat(),
                        "expected": "tomorrow 9 am"},
    }


def get_refund_status(db, ctx):
    rows = db.q("SELECT r.*, t.payer FROM refunds r LEFT JOIN transactions t ON t.id=r.txn_id WHERE r.merchant_id=? "
                "ORDER BY r.created DESC LIMIT 5", (ctx["merchant_id"],))
    pend = db.q("SELECT a.* FROM approvals a JOIN cases c ON c.id=a.case_id WHERE c.merchant_id=? AND a.tool='initiate_refund' "
                "AND a.status='pending'", (ctx["merchant_id"],))
    return {"refunds": [{"refund_id": r["id"], "amount": inr(r["amount"]), "to": r["payer"], "status": r["status"],
                         "time": _clock(r["created"]), "date": r["created"][:10]} for r in rows],
            "waiting_for_approval": [p["title"] for p in pend]}


# RBI harmonised turnaround time (TAT) for failed UPI payments to merchants: auto-reversal by T+5 days,
# then ₹100 per day compensation to the customer (RBI circular DPSS.CO.PD No.629/02.01.014/2019-20).
RBI_TAT = {"merchant_upi_reversal_days": 5, "compensation_per_day": 100}


def check_transaction_status(db, ctx, amount=None, payer=None, minutes=180):
    """Payments that did NOT complete (pending or failed). Use when a customer says money was cut but the shop didn't get it."""
    since = iso(now() - timedelta(minutes=int(minutes or 180)))
    sql, args = "SELECT * FROM transactions WHERE merchant_id=? AND ts>=? AND status!='success'", [ctx["merchant_id"], since]
    if amount:
        sql += " AND amount=?"
        args.append(int(amount))
    if payer:
        sql += " AND lower(payer) LIKE ?"
        args.append("%" + str(payer).lower().split()[0] + "%")
    rows = db.q(sql + " ORDER BY ts DESC", tuple(args))
    out = []
    for r in rows:
        age = int((now() - datetime.fromisoformat(r["ts"])).total_seconds() // 60)
        out.append({"txn_id": r["id"], "amount": inr(r["amount"]), "payer": r["payer"], "time": _clock(r["ts"]),
                    "minutes_ago": age, "status": r["status"],
                    "money_with_shop": False,
                    "what_happens": (f"The customer's bank has not confirmed it. If it does not complete, the customer's bank must "
                                     f"return the money to the customer automatically within T+{RBI_TAT['merchant_upi_reversal_days']} days "
                                     f"(RBI rule), else pay them ₹{RBI_TAT['compensation_per_day']} per day of delay."),
                    "advice": "Do not hand over goods for this payment. Ask the customer to pay again; the stuck amount goes back to them."})
    return {"stuck_payments": out, "count": len(out),
            "note": "Only payments with status success reach the shop. Pending or failed ones never settle to the merchant."}


def explain_settlement(db, ctx, for_date=None):
    """Why a payout was smaller than the day's sales: every deduction, line by line."""
    mid = ctx["merchant_id"]
    if for_date:
        r = db.one("SELECT * FROM settlements WHERE merchant_id=? AND for_date=?", (mid, str(for_date)[:10]))
    else:  # the latest payout that had any deduction
        r = db.one("SELECT * FROM settlements WHERE merchant_id=? AND charges!='[]' ORDER BY for_date DESC LIMIT 1", (mid,))
    if not r:
        return {"found": False}
    charges = json.loads(r["charges"] or "[]")
    refunds = db.q("SELECT * FROM refunds WHERE merchant_id=? AND substr(created,1,10)=?", (mid, r["for_date"]))
    return {"found": True, "settlement_id": r["id"], "for_sales_of": r["for_date"], "sales_that_day": inr(r["gross"] or r["amount"]),
            "deductions": [{"what": c["what"], "amount": inr(c["amount"])} for c in charges]
            + [{"what": f"Refund {x['id']}", "amount": inr(x["amount"])} for x in refunds],
            "paid_to_bank": inr(r["amount"]), "status": r["status"], "credited_at": r["credited_at"],
            "note": "UPI payments from bank accounts have no fee. Credit-card payments carry a fee, and the Soundbox rental is taken monthly."}


def report_fake_payment(db, ctx, amount=None, payer=None, note=""):
    """The shopkeeper was shown a payment screenshot but no money arrived. Recorded as a fraud signal for the area."""
    m = _merchant(db, ctx["merchant_id"])
    since = iso(now() - timedelta(minutes=60))
    others = db.one("SELECT COUNT(DISTINCT merchant_id) n FROM fraud_signals WHERE area=? AND ts>=? AND merchant_id!=?",
                    (m["area"], since, m["id"]))["n"]
    return {"reported": True, "area": m["area"], "amount": inr(int(amount)) if amount else None, "payer": payer,
            "other_shops_nearby": others}, None


def _onb(db, mid):
    r = db.one("SELECT * FROM onboarding WHERE merchant_id=?", (mid,))
    return r, (json.loads(r["data"]) if r else {})


def _save_onb(db, mid, d):
    db.x("UPDATE onboarding SET data=? WHERE merchant_id=?", (json.dumps(d), mid))


def verify_bank_account(db, ctx):
    """Penny drop: send ₹1 to the account and read back the account holder's name."""
    m = _merchant(db, ctx["merchant_id"])
    r, d = _onb(db, m["id"])
    holder = "Suresh Kumar" if d.get("acct") == "0000" else m["owner"]  # demo: account ending 0000 belongs to someone else
    match = holder.lower().split()[0] == m["owner"].lower().split()[0]
    d.update(bank_holder=holder, bank_name_match=match)
    _save_onb(db, m["id"], d)
    return {"sent": "₹1", "account": m["bank"], "holder_name": holder, "matches_owner": match}


def run_onboarding_checks(db, ctx):
    m = _merchant(db, ctx["merchant_id"])
    r, d = _onb(db, m["id"])
    dup = db.one("SELECT id, shop FROM merchants WHERE phone=? AND id!=?", (m["phone"], m["id"]))
    checks = [("Mobile verified by OTP", bool(d.get("mobile_verified"))), ("Aadhaar KYC done", d.get("kyc") == "verified"),
              ("Bank account holder matches owner", bool(d.get("bank_name_match"))),
              ("No other Paytm shop on this mobile", not dup)]
    flags = [c for c, ok in checks if not ok]
    if not d.get("bank_name_match"):
        flags[flags.index("Bank account holder matches owner")] = f"Bank account belongs to {d.get('bank_holder')}, not {m['owner']}"
    d.update(checks_ok=not flags, flags=flags)
    _save_onb(db, m["id"], d)
    return {"all_clear": not flags, "checks": [{"check": c, "ok": ok} for c, ok in checks], "flags": flags}


def activate_merchant(db, ctx):
    """Make the shop live: Paytm QR works immediately; the device is marked as coming."""
    m = _merchant(db, ctx["merchant_id"])
    r, d = _onb(db, m["id"])
    slug = re.sub(r"[^a-z0-9]", "", m["shop"].lower())[:14] or "shop"
    upi = f"{slug}{m['id'][-2:]}@paytm"
    d["upi_id"] = upi
    _save_onb(db, m["id"], d)
    if d.get("device", "soundbox") != "qr" and not db.one("SELECT 1 y FROM devices WHERE merchant_id=?", (m["id"],)):
        n = db.one("SELECT COUNT(*) n FROM devices")["n"]
        db.x("INSERT INTO devices VALUES (?,?,?,?,?,?,?)", (f"SB-{8800 + n}", m["id"], "Soundbox", "not_installed",
                                                           iso(now() + timedelta(days=30)), 100, iso(now())))
    return {"active": True, "upi_id": upi, "qr": "live", "shop": m["shop"]}


def create_fraud_report(db, ctx, area):
    """Network tool: turn 2+ 'payment claimed but never arrived' signals from different shops in one area into a report."""
    since = iso(now() - timedelta(minutes=60))
    sig = db.q("SELECT s.*, m.shop FROM fraud_signals s JOIN merchants m ON m.id=s.merchant_id WHERE s.area=? AND s.ts>=? ORDER BY s.ts",
               (area, since))
    shops = list(dict.fromkeys(s["shop"] for s in sig))
    amts = sorted({s["amount"] for s in sig})
    amount_text = inr(amts[0]) if len(amts) == 1 else f"{inr(amts[0])}–{inr(amts[-1])}"
    aid = db.next_id("FRAUD")
    db.x("INSERT INTO fraud_alerts VALUES (?,?,?,?,?,?)", (aid, area, amount_text, json.dumps(shops), iso(now()), ctx.get("case_id")))
    mins = max(1, int((now() - datetime.fromisoformat(sig[0]["ts"])).total_seconds() // 60)) if sig else 0
    return {"alert_id": aid, "area": area, "shops_reporting": shops, "claimed_amount": amount_text,
            "within_minutes": mins, "pattern": "Customers claimed to have paid (showing a screenshot) but no payment reached Paytm"}, None


def alert_area_shops(db, ctx, alert_id):
    """Network tool: warn every Paytm shop in the area through its Soundbox and app."""
    a = db.one("SELECT * FROM fraud_alerts WHERE id=?", (alert_id,))
    shops = db.q("SELECT id, shop FROM merchants WHERE area=?", (a["area"],))
    return {"alert_id": alert_id, "area": a["area"], "shops_warned": [s["shop"] for s in shops],
            "shop_ids": [s["id"] for s in shops], "claimed_amount": a["amount_text"],
            "reported_by": json.loads(a["shops"])}, None


# ---------------------------------------------------------------- action tools
def renew_device_plan(db, ctx, device_id):
    d = db.one("SELECT * FROM devices WHERE id=?", (device_id,))
    t = now()
    db.x("UPDATE devices SET plan_expires=?, status='online', last_seen=? WHERE id=?",
         (iso(t + timedelta(days=30)), iso(t), device_id))
    undo = {"device_id": device_id, "plan_expires": d["plan_expires"], "status": d["status"], "last_seen": d["last_seen"]}
    return {"done": True, "device_id": device_id, "status": "online",
            "data_plan_valid_till": (t + timedelta(days=30)).date().isoformat()}, undo


def send_kyc_link(db, ctx):
    lid = db.next_id("KYC")
    db.x("INSERT INTO kyc_links VALUES (?,?,?,?,?)", (lid, ctx["merchant_id"], "sent", iso(now()), None))
    return {"sent": True, "link_id": lid, "status": "waiting_for_merchant",
            "note": "The merchant must complete re-verification in the app. Tell them and wait."}, None


def requeue_settlement(db, ctx, settlement_id):
    s = db.one("SELECT * FROM settlements WHERE id=?", (settlement_id,))
    m = _merchant(db, ctx["merchant_id"])
    db.x("UPDATE settlements SET status='settled', hold_reason=NULL, credited_at=? WHERE id=?", (iso(now()), settlement_id))
    return {"done": True, "settlement_id": settlement_id, "amount": inr(s["amount"]), "credited_to": m["bank"],
            "status": "credited"}, {"settlement_id": settlement_id, "status": s["status"], "hold_reason": s["hold_reason"]}


def initiate_refund(db, ctx, txn_id, amount, reason=""):
    t = db.one("SELECT * FROM transactions WHERE id=?", (txn_id,))
    rid = db.next_id("RFD")
    db.x("INSERT INTO refunds VALUES (?,?,?,?,?,?,?,?)",
         (rid, txn_id, ctx["merchant_id"], int(amount), t["payer_vpa"], "processed", iso(now()), ctx.get("approved_by")))
    return {"done": True, "refund_id": rid, "amount": inr(int(amount)), "to": f"{t['payer']} ({t['payer_vpa']})",
            "expected": "in the customer's account within a few minutes (UPI)"}, None


def create_lead_brief(db, ctx, product, notes=""):
    m = _merchant(db, ctx["merchant_id"])
    vol = json.loads(m["monthly_volume"])
    growth = round((vol[-1] - vol[0]) / vol[0] * 100) if vol[0] else 0
    brief = (f"{m['shop']}, {m['city']} ({m['category'].lower()}, {m['months_active']} months on Paytm). "
             f"Monthly collections {inr(vol[0])} → {inr(vol[-1])} (+{growth}% in 3 months). "
             f"Offer: {product}" + (f" (pre-approved up to {inr(m['loan_limit'])})" if 'loan' in product.lower() and m['loan_limit'] else "")
             + ". " + (notes.strip() + " " if notes else "")
             + "Context: a support issue was just solved by Munim, so keep the first call short and friendly.")
    brief_hi = (f"{m['shop']}, {m['city']} ({m['months_active']} महीने से पेटीएम पर)। "
                f"हर महीने की बिक्री {inr(vol[0])} से बढ़कर {inr(vol[-1])} (3 महीने में +{growth}%)। "
                f"ऑफ़र: {HI_PRODUCT.get(product, product)}"
                + (f" ({inr(m['loan_limit'])} तक पहले से मंज़ूर)" if 'loan' in product.lower() and m['loan_limit'] else "")
                + "। मुनीम ने अभी इनकी एक दिक्कत हल की है, इसलिए पहली कॉल छोटी और दोस्ताना रखें।")
    lid = db.next_id("LEAD")
    db.x("INSERT INTO leads VALUES (?,?,?,?,?,?,?,?,?,?)",
         (lid, m["id"], product, brief, brief_hi, m["rep"], None, "new", iso(now()), ctx.get("case_id")))
    return {"done": True, "lead_id": lid, "sent_to": m["rep"], "brief": brief}, {"lead_id": lid}


def book_field_visit(db, ctx, purpose, when="tomorrow 11 am"):
    m = _merchant(db, ctx["merchant_id"])
    lead = db.one("SELECT * FROM leads WHERE merchant_id=? AND status IN ('new','visit_booked') ORDER BY created DESC LIMIT 1", (m["id"],))
    if lead:
        db.x("UPDATE leads SET visit=?, status='visit_booked' WHERE id=?", (f"{when}: {purpose}", lead["id"]))
        lid = lead["id"]
    else:
        lid = db.next_id("LEAD")
        db.x("INSERT INTO leads VALUES (?,?,?,?,?,?,?,?,?,?)",
             (lid, m["id"], purpose, f"{m['shop']}, {m['city']}: {purpose}", f"{m['shop']}, {m['city']}: {HI_PRODUCT.get(purpose, purpose)}",
              m["rep"], f"{when}: {purpose}",
              "visit_booked", iso(now()), ctx.get("case_id")))
    return {"done": True, "lead_id": lid, "rep": m["rep"], "visit": when, "purpose": purpose}, {"lead_id": lid, "had_lead": bool(lead)}


def order_device(db, ctx, item, outlet="new outlet"):
    oid = db.next_id("ORD")
    db.x("INSERT INTO orders VALUES (?,?,?,?,?,?)", (oid, ctx["merchant_id"], item, outlet, "placed", iso(now())))
    return {"done": True, "order_id": oid, "item": item, "outlet": outlet}, {"order_id": oid}


def handover_to_human(db, ctx, summary):
    return {"handed_over": True, "summary": summary, "queue": "Merchant care, priority"}, None


# ---------------------------------------------------------------- undo
def undo_action(db, tool, data):
    if tool == "renew_device_plan":
        db.x("UPDATE devices SET plan_expires=?, status=?, last_seen=? WHERE id=?",
             (data["plan_expires"], data["status"], data["last_seen"], data["device_id"]))
    elif tool == "requeue_settlement":
        db.x("UPDATE settlements SET status=?, hold_reason=?, credited_at=NULL WHERE id=?",
             (data["status"], data["hold_reason"], data["settlement_id"]))
    elif tool == "create_lead_brief":
        db.x("UPDATE leads SET status='cancelled' WHERE id=?", (data["lead_id"],))
    elif tool == "book_field_visit":
        if data.get("had_lead"):
            db.x("UPDATE leads SET visit=NULL, status='new' WHERE id=?", (data["lead_id"],))
        else:
            db.x("UPDATE leads SET status='cancelled' WHERE id=?", (data["lead_id"],))
    elif tool == "order_device":
        db.x("UPDATE orders SET status='cancelled' WHERE id=?", (data["order_id"],))
    else:
        raise ValueError("This action cannot be undone")


# ---------------------------------------------------------------- registry
def _p(props=None, required=None):
    props = dict(props or {})
    props["why"] = {"type": "string", "description": "One short sentence: why you are calling this tool now."}
    return {"type": "object", "properties": props, "required": list(required or [])}


TOOLS = {
    "get_merchant_profile": dict(fn=get_merchant_profile, tier="read", label="Read merchant profile",
        desc="Shop details, KYC status, bank, months on Paytm, collections for the last 3 months.", params=_p()),
    "get_device_health": dict(fn=get_device_health, tier="read", label="Check Soundbox health",
        desc="Status of the merchant's Soundbox devices, data plan expiry and a diagnosis.", params=_p()),
    "get_settlements": dict(fn=get_settlements, tier="read", label="Check settlements",
        desc="Last 5 settlements (payouts to the bank) with status and any hold reason.", params=_p()),
    "get_kyc_status": dict(fn=get_kyc_status, tier="read", label="Check KYC status",
        desc="Merchant KYC status and the latest re-verification link.", params=_p()),
    "search_payments": dict(fn=search_payments, tier="read", label="Search payments",
        desc="Search the merchant's recent payments. Flags likely duplicate debits (same payer, same amount, within 2 minutes, no order).",
        params=_p({"amount": {"type": "integer", "description": "Amount in rupees"},
                   "payer": {"type": "string", "description": "Customer name"},
                   "minutes": {"type": "integer", "description": "How far back to look, default 120"}})),
    "verify_payment": dict(fn=verify_payment, tier="read", label="Verify a payment",
        desc="Check whether a specific payment really reached the merchant (protects against fake payment screenshots).",
        params=_p({"amount": {"type": "integer"}, "payer": {"type": "string"},
                   "minutes": {"type": "integer", "description": "default 30"}}, ["amount"])),
    "get_today_summary": dict(fn=get_today_summary, tier="read", label="Today's khata",
        desc="Today's collections, number of payments, refunds, busiest hour, tomorrow's settlement.", params=_p()),
    "get_sales": dict(fn=get_sales, tier="read", label="Check sales",
        desc="Sales for a period: total, number of payments, average bill, biggest payment, best day, busiest hour, "
             "change vs the previous period, top customers. Use for any 'how much did I earn/sell' question.",
        params=_p({"period": {"type": "string", "enum": list(PERIODS)}}, ["period"])),
    "get_recent_payments": dict(fn=get_recent_payments, tier="read", label="List recent payments",
        desc="The latest payments received (who paid, how much, when). Optionally filter by customer name.",
        params=_p({"limit": {"type": "integer", "description": "1-20, default 5"}, "payer": {"type": "string"}})),
    "get_payout_summary": dict(fn=get_payout_summary, tier="read", label="Check money sent to bank",
        desc="What Paytm has credited to the merchant's bank, anything on hold and why, and tomorrow's payout. "
             "Paytm cannot see the merchant's bank balance; use this when they ask about balance or money in the bank.",
        params=_p()),
    "get_refund_status": dict(fn=get_refund_status, tier="read", label="Check refunds",
        desc="Recent refunds and any refund waiting for a teammate's approval.", params=_p()),
    "check_transaction_status": dict(fn=check_transaction_status, tier="read", label="Check stuck payments",
        desc="Find payments that did NOT complete (pending/failed), with RBI auto-reversal timelines. Use when a customer says "
             "money was cut from their account but the shop did not get it.",
        params=_p({"amount": {"type": "integer"}, "payer": {"type": "string"}, "minutes": {"type": "integer", "description": "default 180"}})),
    "explain_settlement": dict(fn=explain_settlement, tier="read", label="Explain a payout",
        desc="Line-by-line breakdown of a payout: that day's sales, each deduction (Soundbox rental, card fees, refunds) and what reached the bank. "
             "Use when the merchant asks why less money came or what was deducted.",
        params=_p({"for_date": {"type": "string", "description": "YYYY-MM-DD; leave empty for the latest payout with a deduction"}})),
    "report_fake_payment": dict(fn=report_fake_payment, tier="auto", label="Report fake payment",
        desc="Use when a customer showed a payment screenshot (or claimed to pay) but verify_payment shows no money arrived. "
             "Records it for the area; if other shops nearby report the same, Munim warns every shop in the area.",
        params=_p({"amount": {"type": "integer"}, "payer": {"type": "string"}, "note": {"type": "string"}})),
    "verify_bank_account": dict(fn=verify_bank_account, tier="read", label="Verify bank account (₹1 test)", internal=True,
        desc="Onboarding: send ₹1 to the bank account and read back the holder's name.", params=_p()),
    "run_onboarding_checks": dict(fn=run_onboarding_checks, tier="read", label="Run sign-up checks", internal=True,
        desc="Onboarding: mobile OTP, Aadhaar KYC, bank name match, duplicate account.", params=_p()),
    "activate_merchant": dict(fn=activate_merchant, tier="auto", label="Activate the shop on Paytm", internal=True,
        desc="Onboarding: make the shop live (QR works now). Needs a teammate if any check failed.", params=_p()),
    "create_fraud_report": dict(fn=create_fraud_report, tier="auto", label="Create fraud report", internal=True,
        desc="Network: combine fake-payment signals from several shops in one area into a fraud report.",
        params=_p({"area": {"type": "string"}}, ["area"])),
    "alert_area_shops": dict(fn=alert_area_shops, tier="auto", label="Warn all shops in the area", internal=True,
        desc="Network: warn every Paytm shop in an area through its Soundbox and app.",
        params=_p({"alert_id": {"type": "string"}}, ["alert_id"])),
    "check_loan_eligibility": dict(fn=check_loan_eligibility, tier="read", label="Check loan eligibility",
        desc="Whether the merchant is pre-eligible for a working-capital loan, and why.", params=_p()),
    "renew_device_plan": dict(fn=renew_device_plan, tier="auto", label="Renew Soundbox data plan",
        desc="Renew the Soundbox SIM data plan for 30 days and bring it back online.",
        params=_p({"device_id": {"type": "string"}}, ["device_id"])),
    "send_kyc_link": dict(fn=send_kyc_link, tier="merchant", label="Send KYC re-verify link",
        desc="Send a secure KYC re-verification link to the merchant. The merchant must complete it; then wait.", params=_p()),
    "requeue_settlement": dict(fn=requeue_settlement, tier="auto", label="Release held settlement",
        desc="Release a settlement that was on hold and credit it to the merchant's bank. Only allowed once the hold reason is cleared.",
        params=_p({"settlement_id": {"type": "string"}}, ["settlement_id"])),
    "initiate_refund": dict(fn=initiate_refund, tier="human", label="Refund a payment",
        desc=f"Refund a payment back to the original payer. Refunds above ₹{config.REFUND_APPROVAL_LIMIT} wait for a human to approve.",
        params=_p({"txn_id": {"type": "string"}, "amount": {"type": "integer"},
                   "reason": {"type": "string"}, "to": {"type": "string", "description": "Leave empty: refunds always go to the original payer."}},
                  ["txn_id", "amount"])),
    "create_lead_brief": dict(fn=create_lead_brief, tier="auto", label="Send lead to field rep",
        desc="Create a one-page sales brief for the merchant's field rep (for a genuine opportunity only).",
        params=_p({"product": {"type": "string"}, "notes": {"type": "string"}}, ["product"])),
    "book_field_visit": dict(fn=book_field_visit, tier="auto", label="Book field-rep visit",
        desc="Book a visit by the merchant's field rep.",
        params=_p({"purpose": {"type": "string"}, "when": {"type": "string"}}, ["purpose"])),
    "order_device": dict(fn=order_device, tier="auto", label="Order a device",
        desc="Place an order for a Soundbox or card machine when the merchant asks for one.",
        params=_p({"item": {"type": "string"}, "outlet": {"type": "string"}}, ["item"])),
    "handover_to_human": dict(fn=handover_to_human, tier="human", label="Hand over to a human",
        desc="Hand the case to a Paytm teammate with a short summary, when you cannot solve it safely.",
        params=_p({"summary": {"type": "string"}}, ["summary"])),
}

UNDOABLE = {"renew_device_plan", "requeue_settlement", "create_lead_brief", "book_field_visit", "order_device"}


def llm_tool_specs():
    specs = []
    for name, t in TOOLS.items():
        if t.get("internal"):
            continue  # network tools are run by Munim's monitoring, never by the chat model
        specs.append({"type": "function", "function": {"name": name, "description": t["desc"], "parameters": t["params"]}})
    specs.append({"type": "function", "function": {
        "name": "reply_to_merchant",
        "description": "Send your message to the merchant. Use for every reply. Give the SAME short message three ways: "
                       "'text' in the merchant's own style (Hinglish in Latin script if they wrote that way), "
                       "'hindi' in simple Devanagari Hindi, 'english' in simple English. The app shows the merchant's chosen language.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "hindi": {"type": "string"}, "english": {"type": "string"},
                       "done": {"type": "boolean", "description": "true if the case is fully solved"}},
                       "required": ["text", "hindi", "english"]}}})
    return specs


def run_tool(db, name, args, ctx):
    t = TOOLS[name]
    clean = {k: v for k, v in (args or {}).items() if k not in ("why", "to") and v not in (None, "")}
    out = t["fn"](db, ctx, **clean)
    if isinstance(out, tuple):
        return out
    return out, None
