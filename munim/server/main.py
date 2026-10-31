"""Munim server: API, live updates and the four screens (merchant app, Soundbox, field rep, ops console)."""
import asyncio
import json
import socket
from datetime import timedelta

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import config, evals, onboarding, sarvam
from .agent import Agent, brain_name
from .bus import Bus
from .db import DB, iso, now
from .tools import get_today_summary, inr

WEB = config.ROOT / "web"
app = FastAPI(title="Munim")
bus = Bus()
db = DB(config.DB_PATH)
if not db.one("SELECT name FROM sqlite_master WHERE name='merchants'") or \
        "en" not in [c["name"] for c in db.q("PRAGMA table_info(messages)")] or \
        "gross" not in [c["name"] for c in db.q("PRAGMA table_info(settlements)")] or \
        "area" not in [c["name"] for c in db.q("PRAGMA table_info(merchants)")] or \
        not db.one("SELECT name FROM sqlite_master WHERE name='onboarding'"):
    db.reset()
agent = Agent(db, bus)
TASKS = set()


def spawn(coro):
    t = asyncio.create_task(coro)
    TASKS.add(t)
    t.add_done_callback(TASKS.discard)
    return t


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def meter_add(**kw):
    m = db.meta_get("meter", {"stt_seconds": 0, "tts_chars": 0})
    for k, v in kw.items():
        m[k] = m.get(k, 0) + v
    db.meta_set("meter", m)


# ------------------------------------------------------------------ pages (the React app, built into web/)
if (WEB / "assets").exists():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")


# ------------------------------------------------------------------ live updates
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await bus.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        bus.disconnect(websocket)


# ------------------------------------------------------------------ read APIs
@app.get("/api/info")
def info(request: Request):
    ip = lan_ip()
    return {"brain": brain_name(), "model": config.LLM_MODEL if brain_name() == "llm" else "offline rules",
            "sarvam": sarvam.enabled(), "merchant_id": config.DEMO_MERCHANT, "ip": ip,
            "urls": {"http": f"http://{ip}:8000", "https": f"https://{ip}:8443"},
            "approval_limit": inr(config.REFUND_APPROVAL_LIMIT), "undo_minutes": config.UNDO_WINDOW_MIN}


@app.get("/api/merchant/{mid}")
def merchant(mid: str):
    m = db.one("SELECT * FROM merchants WHERE id=?", (mid,))
    if not m:
        raise HTTPException(404, "No such merchant")
    ctx = {"merchant_id": mid, "case_id": None}
    msgs = db.q("SELECT m.*, c.channel FROM messages m JOIN cases c ON c.id=m.case_id WHERE m.merchant_id=? "
                "ORDER BY m.id DESC LIMIT 80", (mid,))
    for x in msgs:
        x["data"] = json.loads(x["data"]) if x["data"] else None
    kyc = db.one("SELECT * FROM kyc_links WHERE merchant_id=? ORDER BY created DESC LIMIT 1", (mid,))
    return {"merchant": m, "device": db.one("SELECT * FROM devices WHERE merchant_id=?", (mid,)),
            "today": get_today_summary(db, ctx),
            "settlements": db.q("SELECT * FROM settlements WHERE merchant_id=? ORDER BY for_date DESC LIMIT 3", (mid,)),
            "kyc_link": kyc, "messages": list(reversed(msgs)), "area_alert": _area_alert(m),
            "recent_payments": db.q("SELECT * FROM transactions WHERE merchant_id=? ORDER BY ts DESC LIMIT 6", (mid,))}


def _area_alert(m):
    """The latest fraud alert for this shop's area (last 3 hours), so a Soundbox switched on later still hears it."""
    a = db.one("SELECT * FROM fraud_alerts WHERE area=? AND created>=? ORDER BY created DESC LIMIT 1",
               (m["area"], iso(now() - timedelta(hours=3))))
    if not a:
        return None
    hi, en = Agent._alert_text({"reported_by": json.loads(a["shops"]), "claimed_amount": a["amount_text"], "area": a["area"]})
    return {"id": a["id"], "hi": hi, "en": en, "created": a["created"]}


@app.get("/api/cases")
def cases():
    rows = db.q("SELECT c.*, m.shop FROM cases c JOIN merchants m ON m.id=c.merchant_id WHERE c.channel!='alert' "
                "ORDER BY c.updated DESC LIMIT 40")
    for r in rows:
        r.pop("llm_messages", None)
    return rows


@app.get("/api/case/{cid}")
def case(cid: str):
    c = db.one("SELECT c.*, m.shop, m.owner, m.city FROM cases c JOIN merchants m ON m.id=c.merchant_id WHERE c.id=?", (cid,))
    if not c:
        raise HTTPException(404, "No such case")
    c.pop("llm_messages", None)
    steps = db.q("SELECT * FROM steps WHERE case_id=? ORDER BY id", (cid,))
    for s in steps:
        s["args"] = json.loads(s["args"] or "{}")
        s["result"] = json.loads(s["result"]) if s["result"] else None
        s["undoable"] = bool(s["undo"]) and s["status"] == "ok"
        s.pop("undo", None)
    aps = db.q("SELECT * FROM approvals WHERE case_id=? ORDER BY id DESC", (cid,))
    for a in aps:
        a["evidence"] = json.loads(a["evidence"] or "[]")
        a["args"] = json.loads(a["args"] or "{}")
    msgs = db.q("SELECT * FROM messages WHERE case_id=? ORDER BY id", (cid,))
    return {"case": c, "steps": steps, "approvals": aps, "messages": msgs}


@app.get("/api/ledger")
def ledger():
    rows = db.q("SELECT s.*, c.merchant_id, c.channel FROM steps s JOIN cases c ON c.id=s.case_id "
                "WHERE s.kind IN ('act','human','event') ORDER BY s.id DESC LIMIT 80")
    for s in rows:
        s["undoable"] = bool(s["undo"]) and s["status"] == "ok"
        s.pop("undo", None)
        s["result"] = json.loads(s["result"]) if s["result"] else None
        s["args"] = json.loads(s["args"] or "{}")
    return rows


@app.get("/api/leads")
def leads(rep: str = ""):
    sql = "SELECT l.*, m.shop, m.owner, m.city, m.phone FROM leads l JOIN merchants m ON m.id=l.merchant_id WHERE l.status!='cancelled'"
    args = ()
    if rep:
        sql += " AND l.rep=?"
        args = (rep,)
    return db.q(sql + " ORDER BY l.created DESC", args)


@app.get("/api/stats")
def stats():
    cs = db.q("SELECT * FROM cases WHERE channel NOT IN ('alert', 'onboarding')")  # sign-ups count under sales
    done = [c for c in cs if c["status"] == "resolved"]
    from datetime import datetime
    secs = [(datetime.fromisoformat(c["resolved"]) - datetime.fromisoformat(c["created"])).total_seconds()
            for c in done if c["resolved"]]
    blocked = db.one("SELECT COUNT(*) n FROM steps WHERE status='blocked'")["n"]
    human_minutes = db.one("SELECT COUNT(*) n FROM steps WHERE kind='human'")["n"]
    meter = db.meta_get("meter", {"stt_seconds": 0, "tts_chars": 0})
    voice_cost = meter["stt_seconds"] / 60 * config.PRICE_STT_PER_MIN + meter["tts_chars"] / 1000 * config.PRICE_TTS_PER_1K_CHARS
    llm_cost = sum(c["cost_inr"] or 0 for c in cs)
    touched = {r["case_id"] for r in db.q("SELECT DISTINCT case_id FROM steps WHERE kind='human' OR tool='handover_to_human'")}
    solo = [c for c in done if c["id"] not in touched]
    total_cost = llm_cost + voice_cost
    economics = {
        "human_cost_per_case": config.HUMAN_COST_PER_CASE,
        "munim_cost_per_case": round(total_cost / len(cs), 2) if cs else 0,
        "solved_without_person": len(solo),
        "saved_inr": round(len(solo) * config.HUMAN_COST_PER_CASE - total_cost, 2),
        "fast_path_share": round(100 * len([c for c in cs if c["brain"] in ("fast", "rules")]) / len(cs)) if cs else 0,
        "calls_prevented": len([c for c in done if c["channel"] == "proactive"]),
    }
    leads_rows = db.q("SELECT * FROM leads WHERE status!='cancelled'")
    sales = {**onboarding.stats(db), "leads": len(leads_rows), "visits": len([l for l in leads_rows if l["visit"]])}
    return {"sales": sales, "economics": economics, "cases": len(cs), "resolved": len(done), "auto_resolved": len([c for c in done if c["channel"] != "x"]),
            "waiting_human": len([c for c in cs if c["status"] == "waiting_human"]),
            "avg_resolve_seconds": round(sum(secs) / len(secs), 1) if secs else None,
            "blocked": blocked, "human_touches": human_minutes,
            "cost_inr": round(llm_cost + voice_cost, 2),
            "cost_per_case_inr": round((llm_cost + voice_cost) / len(cs), 2) if cs else 0,
            "eval": db.meta_get("eval")}


# ------------------------------------------------------------------ actions
@app.post("/api/message")
async def message(request: Request):
    b = await request.json()
    text = (b.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "Type a message first")
    spawn(agent.on_message(b.get("merchant_id", config.DEMO_MERCHANT), text, b.get("channel", "app"),
                           by_operator=bool(b.get("operator"))))
    return {"ok": True}


@app.post("/api/voice")
async def voice(file: UploadFile = File(...), merchant_id: str = Form(config.DEMO_MERCHANT), channel: str = Form("app")):
    audio = await file.read()
    if len(audio) < 2000:
        raise HTTPException(400, "That recording was too short. Hold the button and speak for a few seconds.")
    try:
        text, secs = await sarvam.stt(audio, file.filename or "voice.wav")
    except sarvam.SarvamError as e:
        raise HTTPException(400, str(e))
    meter_add(stt_seconds=secs)
    if not text:
        raise HTTPException(400, "Couldn't hear any words. Try again a little closer to the mic.")
    spawn(agent.on_message(merchant_id, text, channel, voice=True))
    return {"ok": True, "transcript": text}


# ------------------------------------------------------------------ voice onboarding for new shopkeepers
@app.post("/api/onboard/start")
def onboard_start():
    sid, q = onboarding.start(db)
    return {"sid": sid, "next": q}


@app.post("/api/onboard/answer")
async def onboard_answer(request: Request):
    b = await request.json()
    try:
        return onboarding.step(db, b.get("sid", ""), b.get("text", ""))
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.post("/api/onboard/finish")
async def onboard_finish(request: Request):
    b = await request.json()
    return await onboarding.finish(agent, db, b.get("sid", ""))


@app.post("/api/stt")
async def stt_only(file: UploadFile = File(...)):
    """Speech to text only (used by sign-up answers)."""
    audio = await file.read()
    try:
        text, secs = await sarvam.stt(audio, file.filename or "voice.wav")
    except sarvam.SarvamError as e:
        raise HTTPException(400, str(e))
    meter_add(stt_seconds=secs)
    return {"transcript": text}


@app.post("/api/tts")
async def tts(request: Request):
    b = await request.json()
    try:
        wav, chars = await sarvam.tts(b.get("text", ""), "en-IN" if b.get("lang") == "en" else "hi-IN")
    except sarvam.SarvamError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    if chars:
        meter_add(tts_chars=chars)
    return Response(wav, media_type="audio/wav")


@app.post("/api/kyc/complete")
async def kyc_complete(request: Request):
    b = await request.json()
    spawn(agent.on_kyc_completed(b.get("merchant_id", config.DEMO_MERCHANT)))
    return {"ok": True}


@app.post("/api/approve")
async def approve(request: Request):
    b = await request.json()
    try:
        ap = db.one("SELECT * FROM approvals WHERE id=?", (int(b["approval_id"]),))
        if not ap or ap["status"] != "pending":
            raise ValueError("This approval is no longer pending")
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    spawn(agent.decide(int(b["approval_id"]), bool(b.get("approved")), b.get("by") or "Teammate"))
    return {"ok": True}


@app.post("/api/undo")
async def undo(request: Request):
    b = await request.json()
    try:
        await agent.undo(int(b["step_id"]), b.get("by") or "Teammate")
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/event")
async def event(request: Request):
    b = await request.json()
    kind = b.get("kind")
    mid = b.get("merchant_id", config.DEMO_MERCHANT)
    t = now()
    if kind == "customer_pays":
        amount = int(b.get("amount") or 500)
        payer = b.get("payer") or "Walk-in customer"
        n = db.one("SELECT COUNT(*) n FROM transactions")["n"]
        dev = db.one("SELECT * FROM devices WHERE merchant_id=?", (mid,))
        online = dev and dev["status"] == "online"
        db.x("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
             (f"TXN58{n:04d}", mid, amount, payer, "customer@ybl", iso(t), "success", f"ORD-9{n:04d}", 1 if online else 0))
        await bus.emit("payment", merchant_id=mid, amount=amount, announced=bool(online))
        if online:
            await bus.emit("announce", merchant_id=mid, text=f"Received {inr(amount)}", speak=f"{amount} रुपये प्राप्त हुए।",
                           en=f"Received {amount} rupees.")
        await bus.emit("state", merchant_id=mid)
        return {"ok": True, "announced": bool(online)}
    if kind == "device_offline":
        db.x("UPDATE devices SET status='offline', plan_expires=?, last_seen=? WHERE merchant_id=?",
             (iso(t - timedelta(minutes=2)), iso(t - timedelta(minutes=2)), mid))
        await bus.emit("device", merchant_id=mid)
        await bus.emit("state", merchant_id=mid)

        async def later():
            await asyncio.sleep(2.5)
            await agent.on_event(mid, "device_offline", "Soundbox SB-7731 stopped reporting 2 minutes ago")
        spawn(later())
        return {"ok": True}
    if kind == "double_debit":
        amount = int(b.get("amount") or 4800)
        n = db.one("SELECT COUNT(*) n FROM transactions")["n"]
        db.x("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
             (f"TXN59{n:04d}", mid, amount, "Abhinandan K.", "abhinandan@okicici", iso(t - timedelta(seconds=40)), "success", f"ORD-8{n:04d}", 1))
        db.x("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
             (f"TXN59{n + 1:04d}", mid, amount, "Abhinandan K.", "abhinandan@okicici", iso(t - timedelta(seconds=9)), "success", None, 1))
        await bus.emit("state", merchant_id=mid)
        return {"ok": True}
    if kind == "fake_claims":
        # Two shops in the same area are each told "I sent ₹2,000" by a customer showing a screenshot. Nothing arrived.
        async def go():
            await agent.on_message("M1001", "Rohit ne ₹2,000 ka screenshot dikhaya, aaya kya?", "app")
            await asyncio.sleep(2)
            await agent.on_message("M1002", "Rohit naam ka customer bol raha ₹2,000 bheja, screenshot dikhaya. Rohit ne bheja, aaya kya?", "app")
        spawn(go())
        return {"ok": True}
    if kind == "shop_closed":
        spawn(agent.on_message(mid, "Dukaan band, aaj ka hisaab sunao", "soundbox"))
        return {"ok": True}
    raise HTTPException(400, "Unknown event")


@app.post("/api/reset")
async def reset():
    db.reset()
    agent.locks.clear()
    await bus.emit("reset")
    return {"ok": True}


@app.post("/api/eval/run")
async def eval_run():
    if db.meta_get("eval_running"):
        raise HTTPException(400, "The test set is already running")
    db.meta_set("eval_running", True)

    async def go():
        try:
            await evals.run_all(bus, db)
        finally:
            db.meta_set("eval_running", False)
    spawn(go())
    return {"ok": True, "total": len(evals.EVALSET)}


# ------------------------------------------------------------------ settings: paste the Sarvam key from the app
def _save_env(key, value):
    env = config.ROOT / ".env"
    lines = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    lines = [l for l in lines if not l.strip().startswith(key + "=")]
    lines.append(f"{key}={value}")
    env.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _check_llm():
    import httpx
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": "application/json"}
    if "sarvam.ai" in config.LLM_BASE_URL:
        headers["api-subscription-key"] = config.LLM_API_KEY
    body = {"model": config.LLM_MODEL, "messages": [{"role": "user", "content": "Reply with the single word OK."}], "max_tokens": 400}
    try:
        async with httpx.AsyncClient(timeout=45) as c:
            r = await c.post(config.LLM_BASE_URL.rstrip("/") + "/chat/completions", headers=headers, json=body)
        return (True, "Working") if r.status_code < 400 else (False, f"Error {r.status_code}: {r.text[:140]}")
    except Exception as e:
        return False, f"Could not reach the model: {e.__class__.__name__}"


@app.get("/api/settings")
def settings_get():
    k = config.SARVAM_API_KEY
    return {"has_key": bool(k), "hint": (k[:4] + "…" + k[-4:]) if len(k) > 10 else "", "brain": brain_name(),
            "brain_mode": config.BRAIN, "model": config.LLM_MODEL}


@app.post("/api/settings")
async def settings_post(request: Request):
    b = await request.json()
    if b.get("brain") in ("saver", "llm"):
        config.BRAIN = b["brain"]
        _save_env("BRAIN", b["brain"])
        if not b.get("sarvam_key"):
            return {"brain_mode": config.BRAIN}
    key = (b.get("sarvam_key") or "").strip()
    if key:
        _save_env("SARVAM_API_KEY", key)
        config.SARVAM_API_KEY = key
        if "sarvam.ai" in config.LLM_BASE_URL:
            config.LLM_API_KEY = key
    if not config.SARVAM_API_KEY:
        raise HTTPException(400, "Paste your Sarvam API key first")
    try:
        sarvam._cache_path("नमस्ते, मैं मुनीम हूँ।", "hi-IN").unlink(missing_ok=True)
        await sarvam.tts("नमस्ते, मैं मुनीम हूँ।", "hi-IN")
        voice = (True, "Working")
    except sarvam.SarvamError as e:
        voice = (False, str(e)[:160])
    brain = await _check_llm()
    return {"voice": {"ok": voice[0], "detail": voice[1]}, "brain": {"ok": brain[0], "detail": brain[1]}}


@app.get("/{path:path}")
def spa(path: str):
    f = WEB / path
    if path and f.is_file() and WEB in f.resolve().parents:
        return FileResponse(f)
    index = WEB / "index.html"
    if not index.exists():
        raise HTTPException(404, "The app isn't built yet. Run: cd frontend && npm install && npm run build")
    return FileResponse(index)
