import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from persiantools.jdatetime import JalaliDate

TEHRAN = ZoneInfo("Asia/Tehran")
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩يك", "01234567890123456789یک")
MONEY = r"(?:[0-9]+(?:[,٬][0-9]{3})*(?:[.٫][0-9]+)?)\s*(?:میلیون|هزار|million\b|thousand\b|[km]\b)?\s*(?:تومان|تومن|tomans?\b)?"
CATEGORIES = {
    "expense": {
        "food": ("خوراک", "Food", "قهوه غذا نان رستوران coffee food lunch groceries"),
        "transport": ("حمل‌ونقل", "Transport", "تاکسی اسنپ مترو بنزین taxi fuel bus"),
        "home": ("خانه و قبض", "Housing & bills", "اجاره قبض برق rent bill"),
        "health": ("سلامت", "Health", "دارو پزشک pharmacy doctor"),
        "shopping": ("خرید", "Shopping", "لباس پوشاک clothes shopping"),
        "fun": ("تفریح", "Entertainment", "سینما بازی cinema movie game"),
        "other_expense": ("سایر هزینه‌ها", "Other expenses", ""),
    },
    "income": {
        "salary": ("حقوق", "Salary", "حقوق salary paycheck"),
        "freelance": ("درآمد پروژه", "Freelance", "پروژه freelance"),
        "gift": ("هدیه", "Gift", "هدیه عیدی gift"),
        "other_income": ("سایر درآمدها", "Other income", "درآمد واریز income deposit"),
    },
}


def now():
    return datetime.now(TEHRAN).replace(microsecond=0)


def normalize(text):
    return text.translate(DIGITS).strip()


def amount(text, *, allow_zero=False):
    cleaned = normalize(text).lower()
    if not re.fullmatch(MONEY, cleaned):
        raise ValueError("Invalid amount")
    number = re.search(r"[0-9,٬.٫]+", cleaned)[0]
    scale = 1
    if re.search(r"میلیون|million|m\b", cleaned.replace("toman", "")):
        scale = 1_000_000
    elif re.search(r"هزار|thousand|k\b", cleaned):
        scale = 1_000
    result = Decimal(number.replace(",", "").replace("٬", "").replace("٫", ".")) * scale
    if result != result.to_integral_value() or not (int(not allow_zero) <= result <= 10**12):
        raise ValueError("Amount out of range")
    return int(result)


def timestamp(text, reference=None):
    reference = reference or now()
    text = normalize(text).lower()
    if text in ("now", "الان", "اکنون"):
        return reference
    date_text, _, time_text = text.partition(" ")
    if date_text in ("today", "امروز", "yesterday", "دیروز"):
        day = reference.date() - timedelta(days=date_text in ("yesterday", "دیروز"))
    else:
        match = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", date_text)
        if not match:
            raise ValueError("Invalid date")
        year, month, day_number = map(int, match.groups())
        day = (JalaliDate(year, month, day_number).to_gregorian() if year < 1700
               else datetime(year, month, day_number).date())
    if not time_text:
        return datetime.combine(day, reference.timetz())
    match = re.fullmatch(r"(?:ساعت\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|صبح|شب|عصر)?", time_text.strip())
    if not match:
        raise ValueError("Invalid time")
    hour, minute, period = match.groups()
    hour = int(hour)
    if period:
        if not 1 <= hour <= 12:
            raise ValueError("Invalid hour")
        hour = hour % 12 + (12 if period in ("pm", "شب", "عصر") else 0)
    return datetime(day.year, day.month, day.day, hour, int(minute or 0), tzinfo=TEHRAN)


def display_time(value, language):
    dt = datetime.fromisoformat(value).astimezone(TEHRAN)
    day = str(JalaliDate.to_jalali(dt.date())) if language == "fa" else dt.date().isoformat()
    return f"{day} {dt:%H:%M}"


def quick_entry(text):
    text = text.strip()
    date = re.search(r"(?<!\w)(?:دیروز|امروز|yesterday|today|\d{4}[-/]\d{1,2}[-/]\d{1,2})(?!\w)(?:\s+(?:ساعت\s+\d{1,2}(?::\d{2})?|\d{1,2}:\d{2}|\d{1,2}(?=\s*(?:am|pm)\b))(?:\s*(?:صبح|شب|عصر|am\b|pm\b))?)?", normalize(text), re.IGNORECASE)
    date_time = timestamp(date[0]) if date else now()
    if date:
        text = text[:date.start()] + " " + text[date.end():]
    text = text.strip().rstrip(".,،")
    normalized = normalize(text)
    matches = list(re.finditer(r"(?<![\w.,٬٫+\-−])" + MONEY + r"(?![\w.,٬٫])", normalized, re.IGNORECASE))
    if len(matches) != 1 or re.search(r"[+−-]\s*\d", normalized):
        raise ValueError("Expected one amount")
    value = amount(matches[0][0])
    note = (text[:matches[0].start()] + " " + text[matches[0].end():]).strip(" ،,:")
    words = set(re.findall(r"\w+", normalize(note).casefold()))
    for kind in ("income", "expense"):
        for category, (_, _, aliases) in CATEGORIES[kind].items():
            if words.intersection(aliases.split()):
                return kind, value, category, note, date_time.isoformat()
    return "expense", value, "other_expense", note, date_time.isoformat()


def period_range(period, language, reference=None, *, month_offset=0):
    reference = reference or now()
    day = reference.date()
    if period == "week":
        start = day - timedelta(days=(day.weekday() - (5 if language == "fa" else 0)) % 7)
        end = start + timedelta(days=7)
    elif language == "fa":
        jalali = JalaliDate.to_jalali(day)
        year, month = divmod(jalali.year * 12 + jalali.month - 1 + month_offset, 12)
        start = JalaliDate(year, month + 1, 1).to_gregorian()
        end = JalaliDate(year + (month == 11), (month + 1) % 12 + 1, 1).to_gregorian()
    else:
        year, month = divmod(day.year * 12 + day.month - 1 + month_offset, 12)
        start = day.replace(year=year, month=month + 1, day=1)
        end = (start + timedelta(days=32)).replace(day=1)
    return start.isoformat(), end.isoformat()


class Ledger:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY, language TEXT NOT NULL DEFAULT 'fa'
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
                    opening INTEGER NOT NULL, UNIQUE(user_id, name), UNIQUE(user_id, id)
                );
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('income','expense','transfer')),
                    amount INTEGER NOT NULL CHECK(amount > 0), account INTEGER NOT NULL,
                    destination INTEGER, category TEXT NOT NULL, note TEXT NOT NULL,
                    happened_at TEXT NOT NULL,
                    FOREIGN KEY(user_id, account) REFERENCES accounts(user_id, id),
                    FOREIGN KEY(user_id, destination) REFERENCES accounts(user_id, id),
                    CHECK((kind = 'transfer' AND destination IS NOT NULL AND destination != account)
                       OR (kind != 'transfer' AND destination IS NULL))
                );
                CREATE INDEX IF NOT EXISTS entry_date ON entries(user_id, happened_at, id);
                CREATE INDEX IF NOT EXISTS entry_account ON entries(user_id, account);
                CREATE INDEX IF NOT EXISTS entry_destination ON entries(user_id, destination);
                CREATE TABLE IF NOT EXISTS budgets (
                    user_id INTEGER NOT NULL, category TEXT NOT NULL, amount INTEGER NOT NULL,
                    PRIMARY KEY(user_id, category)
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def language(self, user):
        with self.connect() as db:
            row = db.execute("SELECT language FROM users WHERE id=?", (user,)).fetchone()
        return row["language"] if row else "fa"

    def set_language(self, user, language):
        with self.connect() as db:
            db.execute("INSERT INTO users VALUES (?,?) ON CONFLICT(id) DO UPDATE SET language=excluded.language",
                       (user, language))

    def accounts(self, user):
        with self.connect() as db:
            return db.execute("""
                SELECT a.*, a.opening + COALESCE((
                    SELECT SUM(CASE WHEN e.destination=a.id OR e.kind='income' THEN e.amount ELSE -e.amount END)
                    FROM entries e WHERE e.user_id=a.user_id AND (e.account=a.id OR e.destination=a.id)
                ), 0) AS balance FROM accounts a WHERE a.user_id=? ORDER BY a.id
            """, (user,)).fetchall()

    def add_account(self, user, name, opening):
        with self.connect() as db:
            db.execute("INSERT INTO accounts(user_id,name,opening) VALUES (?,?,?)", (user, name, opening))

    def save(self, user, draft):
        keys = ("kind", "amount", "account", "destination", "category", "note", "happened_at")
        values = tuple(draft.get(key) for key in keys)
        with self.connect() as db:
            if entry_id := draft.get("id"):
                result = db.execute("""
                    UPDATE entries SET kind=?,amount=?,account=?,destination=?,category=?,note=?,happened_at=?
                    WHERE id=? AND user_id=?
                """, (*values, entry_id, user))
                if not result.rowcount:
                    raise ValueError("Missing transaction")
                return entry_id
            return db.execute("""
                INSERT INTO entries(kind,amount,account,destination,category,note,happened_at,user_id)
                VALUES (?,?,?,?,?,?,?,?)
            """, (*values, user)).lastrowid

    def entry(self, user, entry_id):
        with self.connect() as db:
            return db.execute("SELECT * FROM entries WHERE user_id=? AND id=?", (user, entry_id)).fetchone()

    def delete(self, user, entry_id):
        with self.connect() as db:
            db.execute("DELETE FROM entries WHERE user_id=? AND id=?", (user, entry_id))

    def entries(self, user, dates=None, *, page=None, kind=None, search=None):
        query = "SELECT * FROM entries WHERE user_id=?"
        args = [user]
        if dates:
            query += " AND happened_at>=? AND happened_at<?"
            args.extend(dates)
        if kind:
            query += " AND kind=?"
            args.append(kind)
        if search:
            query += " AND instr(search_text(note), ?) > 0"
            args.append(normalize(search).casefold())
        query += " ORDER BY happened_at DESC,id DESC"
        if page is not None:
            query += " LIMIT 9 OFFSET ?"
            args.append(page * 8)
        with self.connect() as db:
            if search:
                db.create_function("search_text", 1, lambda value: normalize(value).casefold())
            return db.execute(query, args).fetchall()

    def spending(self, user, category, dates):
        with self.connect() as db:
            return db.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM entries
                WHERE user_id=? AND kind='expense' AND category=? AND happened_at>=? AND happened_at<?
            """, (user, category, *dates)).fetchone()[0]

    def set_budget(self, user, category, value):
        with self.connect() as db:
            if value:
                db.execute("INSERT INTO budgets VALUES (?,?,?) ON CONFLICT(user_id,category) DO UPDATE SET amount=excluded.amount",
                           (user, category, value))
            else:
                db.execute("DELETE FROM budgets WHERE user_id=? AND category=?", (user, category))

    def budgets(self, user):
        with self.connect() as db:
            return dict(db.execute("SELECT category,amount FROM budgets WHERE user_id=?", (user,)).fetchall())
