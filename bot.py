import csv
import io
import logging
import os
import secrets
import sqlite3
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.error import BadRequest, InvalidToken, NetworkError
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from finance import CATEGORIES, Ledger, amount, display_time, now, period_range, quick_entry, timestamp

LABELS = {
    "income": ("ثبت درآمد", "Add income"), "expense": ("ثبت هزینه", "Add expense"),
    "transfer": ("انتقال وجه", "Transfer"), "history": ("تراکنش‌ها", "Transactions"),
    "reports": ("گزارش‌ها", "Reports"), "accounts": ("حساب‌ها", "Accounts"),
    "budgets": ("بودجه‌ها", "Budgets"), "csv": ("خروجی CSV", "Export CSV"),
    "help": ("راهنما", "Help"), "language": ("زبان", "Language"),
    "home": ("منوی اصلی", "Main menu"), "save": ("تأیید و ذخیره", "Confirm and save"),
    "edit": ("ویرایش", "Edit"), "delete": ("حذف", "Delete"),
    "week": ("این هفته", "This week"), "month": ("این ماه", "This month"),
    "stats": ("آمار", "Statistics"), "all": ("کل دوره", "All time"),
}


def button_style(data):
    action = data.rsplit(":", 1)[-1] if data.startswith("w:") else data.split(":", 1)[0]
    if action in {"save", "income", "new_account", "new_budget"}:
        return "success"
    if action in {"expense", "delete", "remove"}:
        return "danger"
    return "primary"


class FinanceBot:
    def __init__(self, ledger, user):
        self.ledger = ledger
        self.user = user
        self.language = ledger.language(user)

    def tr(self, fa, en):
        return fa if self.language == "fa" else en

    def label(self, key):
        return self.tr(*LABELS[key])

    def category(self, key):
        for categories in CATEGORIES.values():
            if key in categories:
                fa, en, _ = categories[key]
                return self.tr(fa, en)
        return "—"

    def money(self, value):
        return self.tr(f"{value:,} تومان", f"{value:,} toman")

    def kind(self, key):
        return {
            "income": self.tr("درآمد", "Income"),
            "expense": self.tr("هزینه", "Expense"),
            "transfer": self.label("transfer"),
        }[key]

    async def send(self, update, text, rows=(), *, home=True):
        buttons = [list(row) for row in rows]
        if home:
            buttons.append([(self.label("home"), "home")])
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data=data, style=button_style(data)) for label, data in row]
            for row in buttons
        ]) if buttons else None
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=markup)
            except BadRequest as error:
                if "message is not modified" not in str(error).lower():
                    raise
        else:
            await update.effective_message.reply_text(text, reply_markup=markup)

    def menu(self):
        return [
            [(self.label(key), key) for key in keys]
            for keys in (
                ("income", "expense"), ("transfer", "accounts"), ("history", "reports"),
                ("stats", "budgets"), ("csv", "language"), ("help",),
            )
        ]

    def entry_text(self, entry):
        accounts = {row["id"]: row["name"] for row in self.ledger.accounts(self.user)}
        account = accounts[entry["account"]]
        if entry["destination"]:
            account += " → " + accounts[entry["destination"]]
        return "\n".join(filter(None, [
            f"{self.kind(entry['kind'])} · {self.money(entry['amount'])}",
            f"{self.label('accounts')} · {account}",
            self.category(entry["category"]) if entry["category"] else "",
            display_time(entry["happened_at"], self.language),
            entry["note"],
        ]))

    async def guide(self, update):
        await self.send(update, self.tr(
            "برای ثبت سریع، «ثبت درآمد» یا «ثبت هزینه» را بزن و مبلغ را بفرست. "
            "می‌توانی یک پیام مثل این‌ها هم مستقیم بفرستی:\n\n"
            "قهوه ۱۲۰ هزار\nحقوق ۲۵ میلیون\nدیروز ساعت ۸ شب، تاکسی ۸۰ هزار تومان\n\n"
            "مبلغ بدون واحد به تومان است. «۸۰ تومن» یعنی ۸۰ تومان. زمان بر اساس تهران است. "
            "گزارش ماهانه و سقف بودجه در منوی فارسی بر اساس ماه شمسی محاسبه می‌شود.",
            "Tap Add income or Add expense and send an amount. "
            "You can also send one of these messages directly:\n\n"
            "coffee 120k\nsalary 25 million\nyesterday 8pm taxi 80k\n\n"
            "Amounts are in toman. Times use Tehran time. Monthly reports and budget limits "
            "in the English menu use Gregorian months.",
        ))

    async def show_history(self, update, page, filters=None, *, view=None):
        filters = filters or {}
        entries = self.ledger.entries(self.user, page=page, **filters)
        rows = [[(
            f"#{entry['id']} · {self.kind(entry['kind'])} · {self.money(entry['amount'])} · "
            f"{display_time(entry['happened_at'], self.language)}",
            f"entry:{entry['id']}",
        )] for entry in entries[:8]]
        navigation = []
        if page and view:
            navigation.append((self.tr("قبلی", "Previous"), f"page:{view}:{page - 1}"))
        if len(entries) > 8 and view:
            navigation.append((self.tr("بعدی", "Next"), f"page:{view}:{page + 1}"))
        if navigation:
            rows.append(navigation)
        rows.extend([
            [(self.kind(key), f"history_kind:{key}") for key in ("income", "expense", "transfer")],
            [(self.tr("جست‌وجوی توضیح", "Search notes"), "history_search"),
             (self.tr("نمایش همه", "Show all"), "history")],
        ])
        lines = [self.label("history")]
        if filters.get("kind"):
            lines.append(self.kind(filters["kind"]))
        if filters.get("search"):
            lines.append(f"«{filters['search']}»")
        if dates := filters.get("dates"):
            lines.append(self.range_text(dates))
        if not entries:
            lines.append(self.tr("تراکنشی پیدا نشد.", "No matching transactions."))
        await self.send(update, "\n".join(lines), rows)

    def range_text(self, dates):
        start, end = map(date.fromisoformat, dates)
        first = display_time(start.isoformat() + "T00:00:00+03:30", self.language).split()[0]
        last = display_time((end - timedelta(days=1)).isoformat() + "T00:00:00+03:30", self.language).split()[0]
        return f"{first} – {last}"

    async def monthly(self, update, offset):
        reference = now()
        dates = period_range("month", self.language, reference, month_offset=offset)
        previous = period_range("month", self.language, reference, month_offset=offset - 1)
        # Compare equal elapsed portions when the selected month is still open.
        compare_dates = previous
        if offset == 0:
            elapsed = (reference.date() - date.fromisoformat(dates[0])).days + 1
            cutoff = date.fromisoformat(previous[0]) + timedelta(days=elapsed)
            compare_dates = (previous[0], min(previous[1], cutoff.isoformat()))
            dates = (dates[0], (reference.date() + timedelta(days=1)).isoformat())
        expenses = self.ledger.entries(self.user, dates, kind="expense")
        earlier = self.ledger.entries(self.user, compare_dates, kind="expense")
        income = sum(e["amount"] for e in self.ledger.entries(self.user, dates, kind="income"))
        by_category, by_day = Counter(), Counter()
        for entry in expenses:
            by_category[entry["category"]] += entry["amount"]
            by_day[entry["happened_at"][:10]] += entry["amount"]
        total, before = sum(by_category.values()), sum(e["amount"] for e in earlier)
        change = total - before
        change_text = self.money(change)
        if change > 0:
            change_text = "+" + change_text
        if before:
            change_text += f" ({change / before:+.1%})"
        lines = [
            self.tr("گزارش ماهانه", "Monthly report"), self.range_text(dates), "",
            f"{self.kind('income')} · {self.money(income)}",
            f"{self.kind('expense')} · {self.money(total)} ({len(expenses)})",
            f"{self.tr('خالص', 'Net')} · {self.money(income - total)}",
            f"{self.tr('هزینهٔ بازهٔ مقایسه', 'Comparison spending')} · {self.money(before)}",
            f"{self.tr('تفاوت با ماه قبل', 'Change from prior month')} · {change_text}",
            self.range_text(compare_dates),
        ]
        if by_day:
            peak_day, peak_total = by_day.most_common(1)[0]
            peak_date = display_time(peak_day + "T00:00:00+03:30", self.language).split()[0]
            lines.append(f"{self.tr('پرهزینه‌ترین روز', 'Highest spending day')} · {peak_date} · {self.money(peak_total)}")
            days = (date.fromisoformat(dates[1]) - date.fromisoformat(dates[0])).days
            lines.append(f"{self.tr('میانگین خرج روزانه', 'Average daily spending')} · {self.money((total + days // 2) // days)}")
            lines.append("\n" + self.tr("هزینه به تفکیک دسته", "Expenses by category"))
            lines.extend(
                f"{self.category(key)} · {self.money(value)} · {value / total:.1%}"
                for key, value in by_category.most_common()
            )
        else:
            lines.append(self.tr("\nدر این ماه هزینه‌ای ثبت نشده.", "\nNo expenses in this month."))
        navigation = []
        if offset > -120:
            navigation.append((self.tr("ماه قبل", "Previous month"), f"month_at:{offset - 1}"))
        if offset:
            navigation.extend([
                (self.label("month"), "month"),
                (self.tr("ماه بعد", "Next month"), f"month_at:{offset + 1}"),
            ])
        rows = [navigation, [(self.tr("ریز خرج‌های این ماه", "View monthly expenses"), f"month_expenses:{offset}")]]
        if offset == 0:
            rows.append([(self.label("budgets"), "budgets"), (self.label("stats"), "stats")])
        await self.send(update, "\n".join(lines), rows)

    async def report(self, update, period, *, budgets_only=False):
        dates = period_range(period, self.language)
        entries = self.ledger.entries(self.user, dates)
        totals = Counter()
        expenses = Counter()
        for entry in entries:
            totals[entry["kind"]] += entry["amount"]
            if entry["kind"] == "expense":
                expenses[entry["category"]] += entry["amount"]
        if budgets_only:
            lines = [self.tr("بودجهٔ این ماه", "This month's budgets")]
            for category, limit in self.ledger.budgets(self.user).items():
                left = limit - expenses[category]
                lines.append(
                    f"{self.category(category)} · {self.money(expenses[category])} / {self.money(limit)}"
                    f" · {self.tr('مانده', 'Remaining')} {self.money(left)}"
                )
            if len(lines) == 1:
                lines.append(self.tr("هنوز بودجه‌ای تعیین نشده.", "No budgets yet."))
            rows = [[(self.tr("تعیین بودجه", "Set budget"), "new_budget")]]
        else:
            lines = [
                self.label(period),
                f"{self.kind('income')} · {self.money(totals['income'])}",
                f"{self.kind('expense')} · {self.money(totals['expense'])}",
                f"{self.tr('خالص', 'Net')} · {self.money(totals['income'] - totals['expense'])}",
            ]
            for category, value in expenses.most_common():
                lines.append(f"{self.category(category)} · {self.money(value)}")
            rows = [[(self.label("reports"), "reports"), (self.label("history"), "history")]]
        await self.send(update, "\n".join(lines), rows)

    async def statistics(self, update, period):
        dates = None if period == "all" else period_range(period, self.language)
        entries = self.ledger.entries(self.user, dates)
        expenses = [e for e in entries if e["kind"] == "expense"]
        incomes = [e for e in entries if e["kind"] == "income"]
        transfers = [e for e in entries if e["kind"] == "transfer"]
        total_out = sum(e["amount"] for e in expenses)
        total_in = sum(e["amount"] for e in incomes)
        lines = [
            f"{self.label('stats')} · {self.label(period)}",
            f"{self.kind('income')} · {self.money(total_in)} ({len(incomes)})",
            f"{self.kind('expense')} · {self.money(total_out)} ({len(expenses)})",
            f"{self.tr('خالص', 'Net')} · {self.money(total_in - total_out)}",
            f"{self.tr('تعداد تراکنش‌ها', 'Transactions')} · {len(entries)}",
            f"{self.tr('انتقال‌ها', 'Transfers')} · {len(transfers)} ({self.money(sum(e['amount'] for e in transfers))})",
        ]
        rows = []
        if expenses:
            average = (total_out + len(expenses) // 2) // len(expenses)
            lines.append(f"{self.tr('میانگین هر خرج', 'Average expense')} · {self.money(average)}")
            for title, entry in [
                (self.tr("بیشترین خرج", "Highest expense"), max(expenses, key=lambda e: e["amount"])),
                (self.tr("کمترین خرج", "Lowest expense"), min(expenses, key=lambda e: e["amount"])),
            ]:
                lines.append(
                    f"\n{title} · {self.money(entry['amount'])}\n"
                    f"{display_time(entry['happened_at'], self.language)} · "
                    f"{self.category(entry['category'])}\n{entry['note']}".rstrip()
                )
                rows.append([(title, f"entry:{entry['id']}")])
            by_category = Counter()
            for entry in expenses:
                by_category[entry["category"]] += entry["amount"]
            lines.append("\n" + self.tr("سهم دسته‌ها از کل خرج", "Share of spending by category"))
            lines.extend(
                f"{self.category(category)} · {self.money(value)} · {value / total_out:.1%}"
                for category, value in by_category.most_common()
            )
        else:
            lines.append(self.tr("در این بازه هزینه‌ای ثبت نشده.", "No expenses in this period."))
        rows.append([(self.label(key), f"stats_period:{key}") for key in ("week", "month", "all")])
        await self.send(update, "\n".join(lines), rows)

    async def export(self, update):
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["id", "type", "amount_toman", "account", "destination", "category", "note", "tehran_iso8601"])
        names = {row["id"]: row["name"] for row in self.ledger.accounts(self.user)}
        for e in self.ledger.entries(self.user):
            writer.writerow([
                e["id"], e["kind"], e["amount"], csv_text(names[e["account"]]),
                csv_text(names.get(e["destination"], "")), e["category"], csv_text(e["note"]), e["happened_at"],
            ])
        await update.effective_message.reply_document(
            InputFile(buffer.getvalue().encode("utf-8-sig"), filename="mahhesab-transactions.csv"),
            caption=self.tr("فهرست تراکنش‌ها به‌صورت CSV", "Your transaction history as a CSV file"),
        )

    async def wizard(self, update, state, step, error=""):
        state["step"] = step
        state["nonce"] = secrets.token_hex(5)
        draft = state["draft"]
        rows = []

        def choice(label, value):
            return [(label, f"w:{state['nonce']}:{value}")]

        if step in ("account", "destination"):
            accounts = self.ledger.accounts(self.user)
            if not accounts:
                await self.send(update, self.tr("اول یک حساب بساز.", "Create an account first."),
                                [[(self.label("accounts"), "accounts")]])
                return
            if step == "destination":
                accounts = [a for a in accounts if a["id"] != draft["account"]]
            prompt = self.tr("حساب مقصد را انتخاب کن.", "Choose the destination account.") if step == "destination" else self.tr("حساب را انتخاب کن.", "Choose an account.")
            rows = [choice(account["name"], account["id"]) for account in accounts]
        elif step in ("category", "budget_category"):
            prompt = self.tr("دسته را انتخاب کن.", "Choose a category.")
            categories = CATEGORIES["expense" if step == "budget_category" else draft["kind"]]
            rows = [choice(self.category(category), category) for category in categories]
        elif step == "amount":
            prompt = self.tr("مبلغ را به تومان بفرست. مثلاً ۱۲۰ هزار.", "Send an amount in toman, e.g. 120k.")
            if state.get("fast") and not state.get("return_to"):
                prompt = self.tr(
                    f"{self.label(draft['kind'])}\n\nمبلغ را به تومان بفرست. می‌توانی توضیح را هم در همان پیام بنویسی.",
                    f"{self.label(draft['kind'])}\n\nSend the amount in toman. You can include a note in the same message.",
                ) + "\n" + (
                    self.tr("مثلاً «حقوق ۲۵ میلیون»", "Example: “salary 25 million”") if draft["kind"] == "income"
                    else self.tr("مثلاً «قهوه ۱۲۰ هزار»", "Example: “coffee 120k”")
                )
        elif step == "note":
            prompt = self.tr("توضیح تراکنش را بفرست.", "Send a transaction note.")
            rows = [choice(self.tr("بدون توضیح", "Skip note"), "skip")]
        elif step == "date":
            prompt = self.tr(
                "تاریخ و ساعت را بفرست. مثلاً ۱۴۰۵/۰۸/۲۹ ۲۰:۳۰ یا «دیروز ساعت ۸ شب».",
                "Send the date and time, e.g. 2026-11-20 20:30 or yesterday 8pm.",
            )
            rows = [choice(self.tr("همین حالا", "Now"), "now")]
        elif step == "confirm":
            heading = self.tr("پیش‌نمایش تراکنش", "Review transaction")
            prompt = f"{heading}\n\n{self.entry_text(draft)}"
            rows = [choice(self.label("save"), "save")]
            rows += [choice(self.tr("تغییر دسته", "Change category"), "category")] if draft["kind"] != "transfer" else []
            rows += [choice(self.tr("تغییر حساب", "Change account"), "account"),
                     choice(self.tr("تغییر مبلغ", "Change amount"), "amount"),
                     choice(self.tr("تغییر زمان", "Change time"), "date"),
                     choice(self.tr("تغییر توضیح", "Change note"), "note")]
        elif step == "account_name":
            prompt = self.tr("نام حساب را بفرست. مثلاً نقد یا کارت.", "Send an account name, e.g. Cash or Card.")
        elif step == "opening":
            prompt = self.tr("موجودی اولیه را به تومان بفرست. صفر هم مجاز است.", "Send the opening balance in toman. Zero is allowed.")
        elif step == "budget_amount":
            prompt = self.tr("سقف ماهانه را به تومان بفرست. صفر بودجه را حذف می‌کند.", "Send the monthly limit in toman. Zero removes the budget.")
        elif step == "history_search":
            prompt = self.tr("بخشی از توضیح تراکنش را بفرست.", "Send part of the transaction note.")
        else:
            raise ValueError(step)
        await self.send(update, f"{error}\n\n{prompt}" if error else prompt, rows)

    async def advance(self, update, context, value, *, button=False):
        state = context.user_data.get("flow")
        if not state:
            return
        step, draft = state["step"], state["draft"]
        button_steps = {"account", "destination", "category", "budget_category", "confirm"}
        if not button and step in button_steps:
            await self.wizard(update, state, step, self.tr("یکی از دکمه‌ها را بزن.", "Choose a button."))
            return
        try:
            if step in ("account", "destination"):
                selected = int(value)
                if selected not in {a["id"] for a in self.ledger.accounts(self.user)}:
                    raise ValueError("Invalid account")
                draft[step] = selected
                if step == "account" and draft["kind"] == "transfer":
                    draft.pop("destination", None)
                    next_step = "destination"
                else:
                    next_step = state.pop("return_to", None) or ("confirm" if state.get("quick") or state.get("fast") else "amount")
            elif step == "amount":
                if state.get("fast") and not state.get("return_to"):
                    kind, value, category, note, happened_at = quick_entry(value)
                    if len(note) > 240:
                        raise ValueError("Note too long")
                    fallback = "other_income" if draft["kind"] == "income" else "other_expense"
                    draft.update(amount=value, category=category if kind == draft["kind"] else fallback,
                                 note=note, happened_at=happened_at)
                    accounts = self.ledger.accounts(self.user)
                    if len(accounts) == 1:
                        draft["account"] = accounts[0]["id"]
                    next_step = "confirm" if len(accounts) == 1 else "account"
                else:
                    draft["amount"] = amount(value)
                    next_step = state.pop("return_to", None) or ("note" if draft["kind"] == "transfer" else "category")
            elif step == "category":
                if value not in CATEGORIES[draft["kind"]]:
                    raise ValueError("Invalid category")
                draft["category"] = value
                next_step = state.pop("return_to", None) or "note"
            elif step == "note":
                note = "" if button else value.strip()
                if len(note) > 240:
                    raise ValueError("Note too long")
                draft["note"] = note
                next_step = state.pop("return_to", None) or "date"
            elif step == "date":
                draft["happened_at"] = timestamp(value).isoformat()
                next_step = state.pop("return_to", None) or "confirm"
            elif step == "confirm":
                if value != "save":
                    state["return_to"] = "confirm"
                    await self.wizard(update, state, value)
                    return
                category = draft["category"]
                dates = period_range("month", self.language)
                in_month = dates[0] <= draft["happened_at"][:10] < dates[1]
                limit = self.ledger.budgets(self.user).get(category) if draft["kind"] == "expense" and in_month else None
                before = self.ledger.spending(self.user, category, dates) if limit else 0
                entry_id = self.ledger.save(self.user, draft)
                context.user_data.pop("flow", None)
                message = self.tr("✓ تراکنش ذخیره شد.", "✓ Transaction saved.") + "\n\n" + self.entry_text(draft)
                if limit and before < limit <= self.ledger.spending(self.user, category, dates):
                    message += "\n" + self.tr("به سقف بودجهٔ این دسته رسیده‌ای.", "You reached this category's budget limit.")
                await self.send(update, message, [
                    [(self.label("income"), "income"), (self.label("expense"), "expense")],
                    [(self.tr("جزئیات تراکنش", "Transaction details"), f"entry:{entry_id}"),
                     (self.tr("گزارش ماهانه", "Monthly report"), "month")],
                ])
                return
            elif step == "account_name":
                name = value.strip()
                if not 1 <= len(name) <= 40 or "\n" in name or any(a["name"] == name for a in self.ledger.accounts(self.user)):
                    raise ValueError("Invalid account name")
                draft["name"] = name
                next_step = "opening"
            elif step == "opening":
                self.ledger.add_account(self.user, draft["name"], amount(value, allow_zero=True))
                context.user_data.pop("flow", None)
                await self.show_accounts(update)
                return
            elif step == "budget_category":
                draft["category"] = value
                next_step = "budget_amount"
            elif step == "budget_amount":
                self.ledger.set_budget(self.user, draft["category"], amount(value, allow_zero=True))
                context.user_data.pop("flow", None)
                await self.report(update, "month", budgets_only=True)
                return
            elif step == "history_search":
                if not 1 <= len(value.strip()) <= 80:
                    raise ValueError("Invalid search")
                filters = context.user_data.setdefault("history_filters", {})
                filters["search"] = value.strip()
                context.user_data.pop("flow", None)
                await show_history_view(self, update, context)
                return
        except (ValueError, sqlite3.IntegrityError):
            await self.wizard(update, state, step, self.tr(
                "ورودی معتبر نیست. دوباره با نمونهٔ زیر امتحان کن.",
                "That input is invalid. Try again using the prompt below.",
            ))
            return
        await self.wizard(update, state, next_step)

    async def show_accounts(self, update):
        accounts = self.ledger.accounts(self.user)
        lines = [self.label("accounts")]
        lines += [f"{a['name']} · {self.money(a['balance'])}" for a in accounts]
        lines.append(f"{self.tr('مجموع موجودی', 'Total balance')} · {self.money(sum(a['balance'] for a in accounts))}")
        rows = [[(self.tr("ساخت حساب", "Create account"), "new_account")]]
        if accounts:
            rows.insert(0, [(self.label("income"), "income"), (self.label("expense"), "expense")])
        await self.send(update, "\n".join(lines), rows)


def csv_text(value):
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


def bot_for(update, context):
    return FinanceBot(context.application.bot_data["ledger"], update.effective_user.id)


async def show_history_view(bot, update, context, page=0):
    if page == 0:
        context.user_data["history_view"] = secrets.token_hex(5)
    await bot.show_history(update, page, context.user_data.get("history_filters"),
                           view=context.user_data["history_view"])


async def home(update, context):
    context.user_data.pop("flow", None)
    bot = bot_for(update, context)
    if not bot.ledger.accounts(bot.user):
        await bot.send(update, bot.tr(
            "به ماه‌حساب خوش آمدی. برای شروع، یک حساب مثل «نقد» یا «کارت» بساز.",
            "Welcome to MahHesab. To get started, create an account such as Cash or Card.",
        ), [[(bot.tr("ساخت اولین حساب", "Create your first account"), "new_account")],
            [(bot.label("language"), "language"), (bot.label("help"), "help")]], home=False)
        return
    await bot.send(update, bot.tr(
        "ماه‌حساب\n\nیک گزینه انتخاب کن یا تراکنش را مستقیم بفرست، مثل «قهوه ۱۲۰ هزار».",
        "MahHesab\n\nChoose an action or send a transaction directly, like “coffee 120k”.",
    ), bot.menu(), home=False)


async def start(update, context):
    bot = bot_for(update, context)
    if not bot.ledger.accounts(bot.user):
        await bot.send(update, "ماه‌حساب · MahHesab\n\nزبان بات را انتخاب کن.\nChoose your language.",
                       [[("فارسی", "lang:fa"), ("English", "lang:en")]], home=False)
    else:
        await home(update, context)


async def help_command(update, context):
    context.user_data.pop("flow", None)
    await bot_for(update, context).guide(update)


async def text_received(update, context):
    bot = bot_for(update, context)
    value = update.effective_message.text
    if "flow" in context.user_data:
        await bot.advance(update, context, value)
        return
    if not bot.ledger.accounts(bot.user):
        await bot.send(update, bot.tr("برای ثبت تراکنش، اول یک حساب بساز.", "Create an account before adding transactions."),
                       [[(bot.tr("ساخت حساب", "Create account"), "new_account")]])
        return
    try:
        kind, value, category, note, happened_at = quick_entry(value)
        if len(note) > 240:
            raise ValueError("Note too long")
    except ValueError:
        await bot.guide(update)
        return
    state = {"draft": dict(kind=kind, amount=value, category=category, note=note, happened_at=happened_at, destination=None), "quick": True}
    context.user_data["flow"] = state
    accounts = bot.ledger.accounts(bot.user)
    if len(accounts) == 1:
        state["draft"]["account"] = accounts[0]["id"]
        await bot.wizard(update, state, "confirm")
    else:
        await bot.wizard(update, state, "account")


async def callback(update, context):
    query = update.callback_query
    if not update.effective_chat or update.effective_chat.type != "private":
        await query.answer()
        return
    bot = bot_for(update, context)
    action, _, value = query.data.partition(":")
    if action == "w":
        state = context.user_data.get("flow", {})
        nonce, _, selection = value.partition(":")
        if nonce != state.get("nonce"):
            await query.answer(bot.tr("این مرحله دیگر فعال نیست.", "This step is no longer active."), show_alert=True)
            return
        await query.answer()
        await bot.advance(update, context, selection, button=True)
        return
    await query.answer()
    context.user_data.pop("flow", None)
    if action == "home":
        await home(update, context)
    elif action == "language":
        await bot.send(update, "زبان را انتخاب کن · Choose a language", [[("فارسی", "lang:fa"), ("English", "lang:en")]])
    elif action == "lang" and value in ("fa", "en"):
        bot.ledger.set_language(bot.user, value)
        await home(update, context)
    elif action == "help":
        await bot.guide(update)
    elif action == "accounts":
        await bot.show_accounts(update)
    elif action in ("new_account", "new_budget"):
        state = {"draft": {}}
        context.user_data["flow"] = state
        await bot.wizard(update, state, "account_name" if action == "new_account" else "budget_category")
    elif action in ("income", "expense", "transfer"):
        account_count = len(bot.ledger.accounts(bot.user))
        if account_count < (2 if action == "transfer" else 1):
            await bot.send(update, bot.tr(
                "برای انتقال دو حساب لازم است." if action == "transfer" else "اول یک حساب بساز.",
                "Transfers require two accounts." if action == "transfer" else "Create an account first.",
            ), [[(bot.tr("ساخت حساب", "Create account"), "new_account")]])
            return
        state = {"draft": {"kind": action, "category": "", "destination": None}, "fast": action != "transfer"}
        context.user_data["flow"] = state
        await bot.wizard(update, state, "amount" if state["fast"] else "account")
    elif action == "page":
        view, _, page = value.partition(":")
        if view == context.user_data.get("history_view") and page.isdecimal():
            await show_history_view(bot, update, context, int(page))
        else:
            await bot.send(update, bot.tr(
                "این صفحه قدیمی است. تاریخچه را دوباره باز کن.",
                "This page is out of date. Reopen your transactions.",
            ), [[(bot.label("history"), "history")]])
    elif action in ("history", "history_kind"):
        filters = context.user_data.setdefault("history_filters", {})
        if action == "history":
            filters.clear()
        elif action == "history_kind":
            filters["kind"] = value
        await show_history_view(bot, update, context)
    elif action == "history_search":
        state = {"draft": {}}
        context.user_data["flow"] = state
        await bot.wizard(update, state, "history_search")
    elif action in ("entry", "edit", "delete", "remove"):
        entry_id = int(value)
        entry = bot.ledger.entry(bot.user, entry_id)
        if entry is None:
            await bot.send(update, bot.tr("این تراکنش پیدا نشد.", "Transaction not found."))
        elif action == "entry":
            await bot.send(update, bot.entry_text(entry), [
                [(bot.label("edit"), f"edit:{entry_id}"), (bot.label("delete"), f"delete:{entry_id}")],
                [(bot.label("history"), "history")],
            ])
        elif action == "edit":
            state = {"draft": dict(entry)}
            context.user_data["flow"] = state
            await bot.wizard(update, state, "confirm")
        elif action == "delete":
            await bot.send(update, bot.tr("این تراکنش حذف شود؟", "Delete this transaction?"), [
                [(bot.label("delete"), f"remove:{entry_id}"), (bot.tr("انصراف", "Cancel"), f"entry:{entry_id}")],
            ])
        else:
            bot.ledger.delete(bot.user, entry_id)
            await show_history_view(bot, update, context)
    elif action == "reports":
        await bot.send(update, bot.label("reports"), [[(bot.label("week"), "week"), (bot.label("month"), "month")]])
    elif action == "stats":
        await bot.statistics(update, "month")
    elif action == "stats_period" and value in ("week", "month", "all"):
        await bot.statistics(update, value)
    elif action in ("month", "month_at", "month_expenses"):
        offset = int(value) if value else 0
        if -120 <= offset <= 0:
            if action == "month_expenses":
                reference = now()
                dates = period_range("month", bot.language, reference, month_offset=offset)
                if offset == 0:
                    dates = (dates[0], (reference.date() + timedelta(days=1)).isoformat())
                filters = {"kind": "expense", "dates": dates}
                context.user_data["history_filters"] = filters
                await show_history_view(bot, update, context)
            else:
                await bot.monthly(update, offset)
    elif action in ("week", "budgets"):
        await bot.report(update, "month" if action == "budgets" else action, budgets_only=action == "budgets")
    elif action == "csv":
        await bot.export(update)


async def error_handler(update, context):
    logging.getLogger(__name__).error("Update failed (%s)", type(context.error).__name__)
    if isinstance(context.error, NetworkError) and not isinstance(context.error, BadRequest):
        return
    if isinstance(update, Update) and update.effective_message and update.effective_chat and update.effective_chat.type == "private":
        bot = bot_for(update, context)
        try:
            await update.effective_message.reply_text(bot.tr(
                "خطایی پیش آمد. برای بازگشت به منو /menu را بزن.",
                "Something went wrong. Use /menu to return to the menu.",
            ))
        except NetworkError:
            logging.getLogger(__name__).warning("Could not deliver the error message")


def build_application(token, ledger):
    app = (
        Application.builder().token(token).concurrent_updates(False)
        .connect_timeout(20).read_timeout(20)
        .get_updates_connect_timeout(20).build()
    )
    app.bot_data["ledger"] = ledger
    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", start, filters=private))
    app.add_handler(CommandHandler(["menu", "cancel"], home, filters=private))
    app.add_handler(CommandHandler("help", help_command, filters=private))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(private & filters.TEXT & ~filters.COMMAND, text_received))
    app.add_error_handler(error_handler)
    return app


def main():
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "YOUR_BOTFATHER_TOKEN":
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env or in the environment before starting.")
    path = Path(os.environ.get("KHARJBAN_DB") or "kharjban.sqlite3")
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext._utils.networkloop").addFilter(
        lambda record: not (record.exc_info and isinstance(record.exc_info[1], InvalidToken))
    )
    try:
        build_application(token, Ledger(path)).run_polling(
            allowed_updates=["message", "callback_query"], bootstrap_retries=2,
        )
    except InvalidToken:
        raise SystemExit("Telegram rejected the bot token. Check TELEGRAM_BOT_TOKEN in .env.") from None
    except NetworkError:
        raise SystemExit("Could not reach the Telegram Bot API. Check the network or proxy and try again.") from None


if __name__ == "__main__":
    main()
