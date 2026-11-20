from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock

from finance import Ledger, quick_entry, amount, period_range, timestamp, display_time
from telegram.error import TimedOut
from telegram.ext import ApplicationHandlerStop

from bot import FinanceBot, allowed_user_ids, build_application, callback, reject_unlisted, show_history_view

for message, kind, expected in [
    ("قهوه ۱۲۰ هزار", "expense", 120000), ("حقوق ۲۵ میلیون", "income", 25000000),
    ("دیروز ساعت ۸ شب، تاکسی ۸۰ هزار تومان", "expense", 80000),
    ("yesterday 8pm taxi 80k", "expense", 80000),
]:
    result = quick_entry(message)
    assert result[:2] == (kind, expected), result
    if "تاکسی" in message or "taxi" in message:
        assert result[-1][11:16] == "20:00", result
assert display_time(timestamp("1405/08/29 20:30").isoformat(), "en") == "2026-11-20 20:30"
assert period_range("month", "fa", timestamp("1405/08/29")) == ("2026-10-23", "2026-11-22")
assert period_range("month", "fa", timestamp("1405/01/01"), month_offset=-1)[1] == timestamp("1405/01/01").date().isoformat()
assert period_range("month", "en", timestamp("2026-01-15"), month_offset=-1) == ("2025-12-01", "2026-01-01")
assert amount("1.5m") == 1500000
assert quick_entry("Lunch at Café 120K")[3] == "Lunch at Café"


async def exercise(db):
    db.set_language(7, "en")
    db.add_account(7, "Cash", 100000)
    db.add_account(7, "Card", 200000)
    a, b = [row["id"] for row in db.accounts(7)]
    bot = FinanceBot(db, 7)
    msg = SimpleNamespace(reply_text=AsyncMock(), reply_document=AsyncMock())
    query = SimpleNamespace(edit_message_text=AsyncMock())
    update = SimpleNamespace(effective_message=msg, callback_query=query)

    async def add(kind, selections):
        ctx = SimpleNamespace(user_data={"flow": {"draft": {"kind": kind, "destination": None, "category": ""}}})
        await bot.wizard(update, ctx.user_data["flow"], "account")
        for value, button in selections:
            await bot.advance(update, ctx, value, button=button)
        assert "flow" not in ctx.user_data

    await add("expense", [(str(a), True), ("25k", False), ("food", True), ("coffee", False), ("now", True), ("save", True)])
    entry = db.entries(7)[0]
    assert entry["amount"] == 25000 and entry["note"] == "coffee"
    assert not db.entries(8)
    await add("transfer", [(str(a), True), (str(b), True), ("10k", False), ("skip", True), ("now", True), ("save", True)])
    await add("income", [(str(b), True), ("30k", False), ("salary", True), ("skip", True), ("now", True), ("save", True)])
    assert [row["balance"] for row in db.accounts(7)] == [65000, 240000]
    db.set_budget(7, "food", 50000)
    await bot.report(update, "month")
    assert "5,000 toman" in query.edit_message_text.call_args.args[0]
    await bot.report(update, "month", budgets_only=True)
    assert "Remaining 25,000 toman" in query.edit_message_text.call_args.args[0]
    await bot.monthly(update, 0)
    monthly = query.edit_message_text.call_args.args[0]
    assert "Highest spending day" in monthly and "Average daily spending" in monthly
    assert "25,000 toman (1)" in monthly and "30,000 toman" in monthly
    await bot.monthly(update, -1)
    assert "No expenses in this month." in query.edit_message_text.call_args.args[0]
    db.save(7, dict(entry, id=None, account=b, amount=500, note="tea", happened_at=timestamp("2024-01-03 09:15").isoformat()))
    await bot.statistics(update, "all")
    stats = query.edit_message_text.call_args.args[0]
    assert "Highest expense · 25,000 toman" in stats
    assert "Lowest expense · 500 toman\n2024-01-03 09:15" in stats
    assert "Average expense · 12,750 toman" in stats and "100.0%" in stats
    await bot.statistics(update, "month")
    assert "500 toman" not in query.edit_message_text.call_args.args[0]
    await FinanceBot(db, 8).statistics(update, "all")
    assert "در این بازه هزینه‌ای ثبت نشده." in query.edit_message_text.call_args.args[0]
    await bot.export(update)
    document = msg.reply_document.call_args.args[0]
    assert b"coffee" in document.input_file_content and b"amount_toman" in document.input_file_content
    ctx = SimpleNamespace(user_data={"flow": {"draft": dict(entry)}})
    await bot.wizard(update, ctx.user_data["flow"], "confirm")
    for value, button in [("amount", True), ("5k", False), ("save", True)]:
        await bot.advance(update, ctx, value, button=button)
    assert db.accounts(7)[0]["balance"] == 85000
    db.delete(7, entry["id"])
    assert db.accounts(7)[0]["balance"] == 90000
    assert build_application("123456:offline-test", db).handlers
    allowed = allowed_user_ids("7, 9")
    assert allowed == {7, 9} and not allowed_user_ids("")
    try:
        allowed_user_ids("7, invalid")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid access policy was accepted")
    restricted = build_application("123456:offline-test", db, allowed_users=allowed)
    assert -1 in restricted.handlers
    policy_context = SimpleNamespace(application=restricted)
    notice = AsyncMock(side_effect=TimedOut())
    restricted_update = SimpleNamespace(
        effective_user=SimpleNamespace(id=8), callback_query=SimpleNamespace(answer=notice),
    )
    try:
        await reject_unlisted(restricted_update, policy_context)
    except ApplicationHandlerStop:
        pass
    else:
        raise AssertionError("Restricted update was not stopped")
    restricted_update.effective_user.id = 7
    await reject_unlisted(restricted_update, policy_context)
    assert notice.await_count == 1
    assert len(db.entries(7, kind="expense", search="TEA")) == 1
    assert not db.entries(7, kind="income", search="tea")
    db.add_account(8, "Cash", 0)
    quick_bot = FinanceBot(db, 8)
    ctx = SimpleNamespace(user_data={"flow": {"fast": True, "draft": {"kind": "income", "category": "", "destination": None}}})
    await quick_bot.wizard(update, ctx.user_data["flow"], "amount")
    await quick_bot.advance(update, ctx, "۸۰ هزار", button=False)
    draft = ctx.user_data["flow"]["draft"]
    assert ctx.user_data["flow"]["step"] == "confirm"
    assert draft["kind"] == "income" and draft["category"] == "other_income"
    await quick_bot.advance(update, ctx, "save", button=True)
    assert db.accounts(8)[0]["balance"] == 80000
    await bot.send(update, "Menu", bot.menu(), home=False)
    markup = query.edit_message_text.call_args.kwargs["reply_markup"]
    assert [button.style for button in markup.inline_keyboard[0]] == ["success", "danger"]
    assert markup.inline_keyboard[2][1].style == "primary"
    for _ in range(10):
        db.save(7, dict(entry, id=None))
    ctx = SimpleNamespace(
        user_data={"history_filters": {"kind": "expense"}},
        application=SimpleNamespace(bot_data={"ledger": db}),
    )
    update.effective_user = SimpleNamespace(id=7)
    update.effective_chat = SimpleNamespace(type="private")
    query.answer = AsyncMock()
    await show_history_view(bot, update, ctx)
    first_view = ctx.user_data["history_view"]
    query.data = f"page:{first_view}:1"
    await callback(update, ctx)
    markup = query.edit_message_text.call_args.kwargs["reply_markup"]
    assert any(button.callback_data == f"page:{first_view}:0" for row in markup.inline_keyboard for button in row)
    ctx.user_data["history_filters"] = {"kind": "income"}
    await show_history_view(bot, update, ctx)
    await callback(update, ctx)
    assert "out of date" in query.edit_message_text.call_args.args[0]


with TemporaryDirectory() as folder:
    # Telegram calls are mocks and complete without yielding to an event loop.
    task = exercise(Ledger(Path(folder) / "test.sqlite3"))
    try:
        task.send(None)
    except StopIteration:
        pass
    else:
        task.close()
        raise AssertionError("Offline workflow unexpectedly needed an event loop")
print("Offline workflow checks passed")

