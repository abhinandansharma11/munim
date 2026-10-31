"""Test-set runner: plays 20 merchant tickets through Munim on a fresh copy of the data and scores the results."""
import json
import tempfile
import time
from pathlib import Path

from . import config
from .agent import Agent
from .bus import NullBus
from .db import DB, iso, now

EVALSET = json.loads((Path(__file__).parent / "evalset.json").read_text(encoding="utf-8"))


def _judge(db, case_id, item):
    case = db.one("SELECT * FROM cases WHERE id=?", (case_id,))
    steps = db.q("SELECT * FROM steps WHERE case_id=? ORDER BY id", (case_id,))
    used = {s["tool"] for s in steps if s["kind"] == "act" and s["status"] in ("ok", "pending")}
    succeeded = {s["tool"] for s in steps if s["kind"] == "act" and s["status"] == "ok"}
    blocked = [s for s in steps if s["status"] == "blocked"]
    replies = " ".join(m["text"].lower() for m in db.q("SELECT text FROM messages WHERE case_id=? AND role='munim'", (case_id,)))
    problems = []
    if case["status"] not in item["expect_status"]:
        problems.append(f"ended as {case['status']}")
    for t in item.get("must_use", []):
        if t not in used:
            problems.append(f"did not use {t}")
    for t in item.get("must_not_succeed", []):
        if t in succeeded:
            problems.append(f"ran {t}")
    if item.get("reply_has_any") and not any(w in replies for w in item["reply_has_any"]):
        problems.append("reply did not give the right answer")
    secs = 0
    if steps:
        from datetime import datetime
        secs = (datetime.fromisoformat(steps[-1]["ts"]) - datetime.fromisoformat(case["created"])).total_seconds()
    return {"id": item["id"], "group": item["group"], "text": item["text"], "status": case["status"],
            "pass": not problems, "problems": problems, "tools": sorted(used), "blocked": len(blocked),
            "brain": case["brain"], "cost_inr": round(case["cost_inr"] or 0, 4), "seconds": secs,
            "steps": len([s for s in steps if s["kind"] == "act"])}


async def run_all(bus, main_db):
    results = []
    started = time.time()
    with tempfile.TemporaryDirectory() as d:
        for i, item in enumerate(EVALSET):
            db = DB(Path(d) / f"eval_{i}.db")
            db.reset()
            agent = Agent(db, NullBus(), delay=0)
            t0 = time.time()
            cid = await agent.on_message(item.get("merchant_id", config.DEMO_MERCHANT), item["text"], item.get("channel", "app"))
            r = _judge(db, cid, item)
            r["seconds"] = round(time.time() - t0, 2)
            results.append(r)
            db.conn.close()
            await bus.emit("eval_progress", done=i + 1, total=len(EVALSET), last=r)
    groups = {}
    for g in ("solve", "human", "unsafe"):
        rs = [r for r in results if r["group"] == g]
        groups[g] = {"passed": sum(r["pass"] for r in rs), "total": len(rs)}
    summary = {
        "ran_at": iso(now()), "seconds": round(time.time() - started, 1), "groups": groups,
        "passed": sum(r["pass"] for r in results), "total": len(results),
        "avg_seconds": round(sum(r["seconds"] for r in results) / len(results), 2),
        "avg_cost_inr": round(sum(r["cost_inr"] for r in results) / len(results), 4),
        "brains": sorted({r["brain"] for r in results}), "results": results,
    }
    main_db.meta_set("eval", summary)
    await bus.emit("eval_done")
    return summary
