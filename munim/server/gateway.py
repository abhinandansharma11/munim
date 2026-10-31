"""Policy gateway: runs before EVERY tool call. Plain, readable rules, so judges and compliance can check them."""
from . import config
from .tools import TOOLS, inr

MAX_TOOL_CALLS_PER_CASE = 16


def check(db, tool, args, ctx):
    """Returns (decision, reason). decision is one of: allow, needs_human, block."""
    args = args or {}
    mid = ctx["merchant_id"]

    if tool not in TOOLS:
        return "block", f"'{tool}' is not an approved tool"

    used = db.one("SELECT COUNT(*) AS n FROM steps WHERE case_id=? AND kind='act'", (ctx["case_id"],))["n"]
    if used >= MAX_TOOL_CALLS_PER_CASE:
        return "block", "Too many actions in one case; handing to a human is safer"

    if tool == "renew_device_plan":
        d = db.one("SELECT * FROM devices WHERE id=?", (args.get("device_id"),))
        if not d or d["merchant_id"] != mid:
            return "block", "That device does not belong to this merchant"

    if tool == "requeue_settlement":
        s = db.one("SELECT * FROM settlements WHERE id=?", (args.get("settlement_id"),))
        if not s or s["merchant_id"] != mid:
            return "block", "That settlement does not belong to this merchant"
        if s["status"] != "on_hold":
            return "block", "That settlement is not on hold"
        if s["hold_reason"] == "kyc_reverification":
            m = db.one("SELECT kyc_status FROM merchants WHERE id=?", (mid,))
            if m["kyc_status"] != "verified":
                return "block", "KYC is not verified yet, so the payout must stay on hold"

    if tool == "initiate_refund":
        t = db.one("SELECT * FROM transactions WHERE id=?", (args.get("txn_id"),))
        to = (args.get("to") or "").strip().lower()
        try:
            amount = int(args.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0
        if not t or t["merchant_id"] != mid:
            return "block", "No such payment for this merchant; refunds must point to a real payment"
        if to and to not in (t["payer_vpa"].lower(), t["payer"].lower()):
            return "block", "Refunds only go back to the customer who paid, never to another account"
        if amount <= 0 or amount > t["amount"]:
            return "block", f"Refund amount must be between ₹1 and the payment amount ({inr(t['amount'])})"
        if db.one("SELECT 1 AS y FROM refunds WHERE txn_id=?", (t["id"],)):
            return "block", "This payment was already refunded"
        if amount > config.REFUND_APPROVAL_LIMIT:
            return "needs_human", f"Refunds above {inr(config.REFUND_APPROVAL_LIMIT)} need a teammate's approval"

    if tool == "activate_merchant":
        import json as _j
        r = db.one("SELECT data FROM onboarding WHERE merchant_id=?", (mid,))
        d = _j.loads(r["data"]) if r else {}
        if not d.get("checks_ok"):
            return "needs_human", "A sign-up check did not pass, so a teammate must approve activation"

    return "allow", "Within policy"
