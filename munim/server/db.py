"""SQLite store: the mock Paytm merchant data plus Munim's own cases, ledger and approvals."""
import json
import random
import sqlite3
import threading
from datetime import datetime, timedelta

SCHEMA = """
CREATE TABLE merchants (
  id TEXT PRIMARY KEY, shop TEXT, owner TEXT, city TEXT, phone TEXT, category TEXT,
  kyc_status TEXT, bank TEXT, months_active INTEGER, monthly_volume TEXT,
  loan_limit INTEGER, outlets INTEGER, rep TEXT, area TEXT
);
CREATE TABLE onboarding (
  id TEXT PRIMARY KEY, data TEXT, step TEXT, status TEXT, created TEXT, done TEXT, merchant_id TEXT, case_id TEXT
);
CREATE TABLE fraud_signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, merchant_id TEXT, area TEXT, amount INTEGER, payer TEXT, ts TEXT, case_id TEXT
);
CREATE TABLE fraud_alerts (
  id TEXT PRIMARY KEY, area TEXT, amount_text TEXT, shops TEXT, created TEXT, case_id TEXT
);
CREATE TABLE devices (
  id TEXT PRIMARY KEY, merchant_id TEXT, kind TEXT, status TEXT, plan_expires TEXT,
  battery INTEGER, last_seen TEXT
);
CREATE TABLE transactions (
  id TEXT PRIMARY KEY, merchant_id TEXT, amount INTEGER, payer TEXT, payer_vpa TEXT,
  ts TEXT, status TEXT, order_id TEXT, announced INTEGER DEFAULT 1
);
CREATE TABLE settlements (
  id TEXT PRIMARY KEY, merchant_id TEXT, amount INTEGER, for_date TEXT, status TEXT,
  hold_reason TEXT, credited_at TEXT, gross INTEGER, charges TEXT
);
CREATE TABLE refunds (
  id TEXT PRIMARY KEY, txn_id TEXT, merchant_id TEXT, amount INTEGER, to_vpa TEXT,
  status TEXT, created TEXT, approved_by TEXT
);
CREATE TABLE kyc_links (
  id TEXT PRIMARY KEY, merchant_id TEXT, status TEXT, created TEXT, completed TEXT
);
CREATE TABLE orders (
  id TEXT PRIMARY KEY, merchant_id TEXT, item TEXT, outlet TEXT, status TEXT, created TEXT
);
CREATE TABLE leads (
  id TEXT PRIMARY KEY, merchant_id TEXT, product TEXT, brief TEXT, brief_hi TEXT, rep TEXT,
  visit TEXT, status TEXT, created TEXT, case_id TEXT
);
CREATE TABLE cases (
  id TEXT PRIMARY KEY, merchant_id TEXT, channel TEXT, title TEXT, status TEXT,
  created TEXT, updated TEXT, resolved TEXT, brain TEXT, llm_messages TEXT,
  cost_inr REAL DEFAULT 0, tokens_in INTEGER DEFAULT 0, tokens_out INTEGER DEFAULT 0
);
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, merchant_id TEXT, role TEXT,
  text TEXT, speak TEXT, en TEXT, kind TEXT, data TEXT, ts TEXT, voice INTEGER DEFAULT 0
);
CREATE TABLE steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, ts TEXT, kind TEXT, title TEXT,
  tool TEXT, args TEXT, result TEXT, tier TEXT, status TEXT, actor TEXT, undo TEXT
);
CREATE TABLE approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, tool TEXT, args TEXT, title TEXT,
  evidence TEXT, status TEXT, created TEXT, decided_by TEXT, decided TEXT
);
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
"""


def now():
    return datetime.now().replace(microsecond=0)


def iso(dt):
    return dt.isoformat(timespec="seconds")


class DB:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    # ---------- low level ----------
    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def x(self, sql, args=()):
        with self.lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur.lastrowid

    def meta_get(self, k, default=None):
        r = self.one("SELECT v FROM meta WHERE k=?", (k,))
        return json.loads(r["v"]) if r else default

    def meta_set(self, k, v):
        self.x("INSERT OR REPLACE INTO meta(k, v) VALUES(?, ?)", (k, json.dumps(v)))

    # ---------- reset + seed ----------
    def reset(self):
        with self.lock:
            tables = [r["name"] for r in self.q("SELECT name FROM sqlite_master WHERE type='table'")]
            for t in tables:
                if t != "sqlite_sequence":
                    self.conn.execute(f"DROP TABLE IF EXISTS {t}")
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        self.seed()

    def seed(self):
        t = now()
        today = t.replace(hour=0, minute=0, second=0)
        merchants = [
            ("M1001", "Sharma Kirana", "Ramesh Sharma", "Indore", "98260 41xxx", "Kirana store",
             "reverify_pending", "SBI ••4471", 26, json.dumps([310000, 356000, 421000]), 200000, 1, "Anil Verma", "Vijay Nagar"),
            ("M1002", "Gupta Medicals", "Sunita Gupta", "Indore", "98220 18xxx", "Pharmacy",
             "verified", "HDFC ••9012", 14, json.dumps([520000, 498000, 505000]), 0, 1, "Anil Verma", "Vijay Nagar"),
            ("M1003", "Khan Electronics", "Imran Khan", "Indore", "94150 73xxx", "Electronics",
             "verified", "ICICI ••3380", 31, json.dumps([880000, 940000, 1010000]), 500000, 1, "Anil Verma", "Vijay Nagar"),
        ]
        for m in merchants:
            self.x("INSERT INTO merchants VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", m)

        self.x("INSERT INTO devices VALUES (?,?,?,?,?,?,?)",
               ("SB-7731", "M1001", "Soundbox", "offline", iso(t - timedelta(days=1)), 82, iso(t - timedelta(hours=26))))
        self.x("INSERT INTO devices VALUES (?,?,?,?,?,?,?)",
               ("SB-2210", "M1002", "Soundbox", "online", iso(t + timedelta(days=40)), 64, iso(t)))
        self.x("INSERT INTO devices VALUES (?,?,?,?,?,?,?)",
               ("SB-5102", "M1003", "Soundbox", "online", iso(t + timedelta(days=12)), 91, iso(t)))

        # A month of realistic history for every shop: busy mornings and evenings, busier weekends, regular customers.
        # Each day's money reaches the bank the next morning at 9 am. Sharma Kirana's yesterday payout is on hold for KYC.
        for mid, prof in SHOP_PROFILES.items():
            _seed_history(self, mid, prof, t, today)

        # A real ₹1,500 payment from Neha Joshi (for the "yes, it came" check). Kept off ₹2,000, the fraud-demo amount.
        self.x("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
               ("TXN560190", "M1001", 1500, "Neha Joshi", "neha.joshi@okhdfc", iso(t - timedelta(minutes=18)),
                "success", "ORD-88390", 1))
        # A payment stuck in the middle: the customer's bank debited them but the payment never completed.
        self.x("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
               ("TXN560195", "M1001", 650, "Kavita Rao", "kavita.rao@oksbi", iso(t - timedelta(minutes=22)),
                "pending", "ORD-88401", 0))
        # The double debit: same customer, same amount, 31 seconds apart, only one order.
        d1 = t - timedelta(minutes=12)
        self.x("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
               ("TXN560201", "M1001", 4800, "Abhinandan K.", "abhinandan@okicici", iso(d1), "success", "ORD-88412", 1))
        self.x("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
               ("TXN560202", "M1001", 4800, "Abhinandan K.", "abhinandan@okicici", iso(d1 + timedelta(seconds=31)),
                "success", None, 1))
        self.meta_set("seeded_at", iso(t))
        self.meta_set("counter", 1)

    def next_id(self, prefix):
        n = (self.meta_get("counter", 1) or 1) + 1
        self.meta_set("counter", n)
        return f"{prefix}-{1000 + n}"


# ---------------------------------------------------------------- realistic dummy history
CUSTOMERS = ["Priya Sharma", "Vikas Malhotra", "Neha Joshi", "Rohit Patel", "Kavita Rao", "Arjun Tiwari", "Meena Devi",
             "Suresh Kumar", "Pooja Bansal", "Ankit Verma", "Farhan Ali", "Divya Nair", "Rakesh Yadav", "Sunita Mishra",
             "Imran Qureshi", "Geeta Choudhary", "Manoj Jain", "Ritu Agarwal", "Deepak Soni", "Anjali Gupta", "Harish Pandey",
             "Shabnam Bano", "Nitin Rathore", "Lata Thakur", "Gaurav Saxena", "Komal Sethi", "Ajay Chauhan", "Seema Kapoor",
             "Mohit Dubey", "Rekha Solanki", "Sanjay Bhatt", "Nazia Khan", "Vivek Parmar", "Swati Kulkarni", "Abhishek Rana"]
BANKS = ["okaxis", "okhdfcbank", "oksbi", "okicici", "ybl", "paytm", "ibl"]

HISTORY_DAYS = 75  # enough for 'last month' questions on any day

# amounts (₹) a shop sees, with how often each happens
SHOP_PROFILES = {
    "M1001": dict(per_day=(58, 82), weekend=1.3, rental=149, hold_yesterday=True, start_id=400000,
                  amounts=[(20, 6), (30, 7), (40, 8), (50, 9), (60, 7), (80, 7), (100, 9), (120, 6), (150, 6), (180, 4),
                           (200, 6), (250, 4), (320, 3), (400, 3), (480, 2), (560, 2), (650, 1), (780, 1), (950, 1)]),
    "M1002": dict(per_day=(28, 40), weekend=1.1, rental=149, hold_yesterday=False, start_id=600000,
                  amounts=[(45, 4), (90, 6), (140, 7), (210, 7), (320, 6), (450, 5), (620, 4), (880, 3), (1250, 2), (1700, 1)]),
    "M1003": dict(per_day=(6, 12), weekend=1.4, rental=299, hold_yesterday=False, start_id=800000,
                  amounts=[(299, 4), (499, 5), (899, 4), (1499, 3), (2499, 2), (3999, 2), (6499, 1), (12999, 1)]),
}


def inr_plain(n):
    s = str(int(n))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        s = ",".join(([head] if head else []) + parts) + "," + tail
    return "₹" + s


def _pick(rng, weighted):
    total = sum(w for _, w in weighted)
    r = rng.uniform(0, total)
    for v, w in weighted:
        r -= w
        if r <= 0:
            return v
    return weighted[-1][0]


def _second_of_day(rng):
    """Shops are busiest 8-11 am and 6-9 pm."""
    hour = _pick(rng, [(7, 3), (8, 7), (9, 9), (10, 8), (11, 6), (12, 5), (13, 4), (14, 3), (15, 3), (16, 4),
                       (17, 6), (18, 9), (19, 10), (20, 9), (21, 5)])
    return hour * 3600 + rng.randint(0, 3599)


def _seed_history(db, mid, prof, t, today):
    rng = random.Random(sum(map(ord, mid)) + 7)
    regulars = rng.sample(CUSTOMERS, 18)
    n = prof["start_id"]
    rows = []
    for back in range(HISTORY_DAYS, -1, -1):
        day = today - timedelta(days=back)
        k = rng.randint(*prof["per_day"])
        if day.weekday() >= 5:
            k = int(k * prof["weekend"])
        secs = [_second_of_day(rng) for _ in range(k)]
        if back == 0:  # today: only payments that already happened, spread from opening (7 am) to a few minutes ago
            elapsed = (t - day).total_seconds() - 300
            open_at = 7 * 3600
            if elapsed <= open_at + 600:
                secs = []
            else:
                frac = min(1, (elapsed - open_at) / (15 * 3600))
                secs = sorted(rng.randint(open_at, int(elapsed)) for _ in range(max(3, int(k * frac))))
        day_total = 0
        for sec in sorted(secs):
            amt = _pick(rng, prof["amounts"])
            name = rng.choice(regulars) if rng.random() < 0.7 else rng.choice(CUSTOMERS)
            if mid == "M1001" and back == 0 and name.startswith("Rohit"):
                name = "Ritu Agarwal"  # keep the "did Rohit pay ₹1,500?" story honest: Rohit hasn't paid today
            vpa = name.split()[0].lower() + "." + name.split()[-1].lower()[:4] + "@" + BANKS[sum(map(ord, name)) % len(BANKS)]
            n += 1
            rows.append((f"TXN{n}", mid, amt, name, vpa, iso(day + timedelta(seconds=sec)), "success", f"ORD-{n - 100000}", 1))
            day_total += amt
        if back >= 1:
            held = prof["hold_yesterday"] and back == 1
            charges = []
            if day.day == 1 or back == 2:  # monthly Soundbox rental is taken from a payout (and once more for the demo story)
                charges.append({"what": "Soundbox monthly rental (incl. GST)", "amount": prof["rental"]})
            if back % 4 == 3:  # a few customers paid with credit cards / RuPay credit on UPI, which carry a fee
                card = round(day_total * 0.12)
                charges.append({"what": f"1.5% fee on {inr_plain(card)} paid by credit card", "amount": round(card * 0.015)})
            net = day_total - sum(c["amount"] for c in charges)
            db.x("INSERT INTO settlements VALUES (?,?,?,?,?,?,?,?,?)",
                 (f"ST-{mid[-2:]}{day.strftime('%m%d')}", mid, net, day.date().isoformat(),
                  "on_hold" if held else "settled", "kyc_reverification" if held else None,
                  None if held else iso(day + timedelta(days=1, hours=9)), day_total, json.dumps(charges)))
    # Keep the 3-month figures (used for loan offers and rep briefs) in line with the last 30 days of real payments.
    month = sum(r[2] for r in rows if r[5] >= iso(today - timedelta(days=30)) and r[5] < iso(today))
    m = db.one("SELECT monthly_volume FROM merchants WHERE id=?", (mid,))
    vol = json.loads(m["monthly_volume"])
    db.x("UPDATE merchants SET monthly_volume=? WHERE id=?", (json.dumps([int(round(month * v / vol[-1], -2)) for v in vol]), mid))
    with db.lock:
        db.conn.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)", rows)
        db.conn.commit()
