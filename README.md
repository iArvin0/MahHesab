# MahHesab · ماه‌حساب

[فارسی](#fa) · [English](#en) · [Setup / راه‌اندازی](#setup) · [GitHub / iArvin0](https://github.com/iArvin0)

<a id="fa"></a>
## فارسی

ماه‌حساب بات تلگرام برای ثبت درآمد و هزینه، مدیریت ماندهٔ حساب‌ها و مرور خرج ماهانه است. با Python، `python-telegram-bot` و SQLite ساخته شده و منوی فارسی و انگلیسی دارد.

- **ثبت سریع.** «ثبت هزینه» یا «ثبت درآمد» را بزن و مبلغ یا توضیح و مبلغ را بفرست. بات تاریخ و ساعت و دستهٔ پیشنهادی را پر می‌کند. اگر فقط یک حساب داری، مستقیم پیش‌نمایش را می‌بینی. قبل از ذخیره می‌توانی همهٔ جزئیات را اصلاح کنی.
- **ثبت با پیام.** «قهوه ۱۲۰ هزار»، «حقوق ۲۵ میلیون» یا «دیروز ساعت ۸ شب، تاکسی ۸۰ هزار تومان» را مستقیم بفرست. واحد تومان است و «۸۰ تومن» به‌عنوان ۸۰ تومان ثبت می‌شود.
- **حساب‌ها و تراکنش‌ها.** حساب با موجودی اولیه بساز، بین حساب‌ها انتقال انجام بده و در تاریخچه بر اساس نوع یا متن توضیح جست‌وجو کن. تراکنش‌ها قابل ویرایش و حذف‌اند.
- **گزارش و آمار.** جمع درآمد، هزینه و خالص، بیشترین و کمترین خرج همراه با زمان، میانگین و سهم هر دسته را ببین. برای هر دسته سقف ماهانه تعیین کن و هنگام رسیدن به سقف هشدار بگیر. خروجی CSV در منو موجود است.
- **مرور خرج ماهانه.** بین ماه‌ها جابه‌جا شو، پرهزینه‌ترین روز و میانگین خرج روزانه را ببین و از گزارش وارد ریز خرج‌ها شو. ماه جاری تا امروز با روزهای متناظر ماه قبل مقایسه می‌شود.
- **تقویم.** منوی فارسی از ماه شمسی و هفته‌ای که از شنبه شروع می‌شود استفاده می‌کند. ساعت هر دو زبان بر اساس تهران است.

پایتون ۳٫۱۰ یا جدیدتر نصب کن و با دستور `/newbot` از [BotFather](https://t.me/BotFather) توکن بگیر. دستورات راه‌اندازی پایین صفحه را از پوشهٔ پروژه اجرا کن. در چت خصوصی بات `/start` را بزن، زبان را انتخاب کن و اولین حساب را بساز. `/menu` منو را باز می‌کند و `/cancel` فرم فعلی را می‌بندد. رنگ دکمه‌ها در نسخه‌های تلگرام با پشتیبانی از سبک دکمه نمایش داده می‌شود.

در نصب تازه داده‌ها در `mahhesab.sqlite3` ذخیره می‌شوند. برای اجرای محلی می‌توانی مسیر را با `MAHHESAB_DB` مشخص کنی. اگر از نسخهٔ قبلی ارتقا می‌دهی، بات همچنان پایگاه‌دادهٔ موجود را می‌خواند. Docker داده‌ها را در volume نگه می‌دارد. `docker compose down` بات را متوقف می‌کند و داده‌ها را نگه می‌دارد. گزینهٔ `-v` آن volume را حذف می‌کند.

<a id="en"></a>
## English

MahHesab is a personal finance Telegram bot for tracking income, expenses, and account balances and reviewing monthly spending. It uses Python, `python-telegram-bot`, and SQLite and offers Persian and English menus.

- **Quick entry.** Tap **Add expense** or **Add income**, then send an amount with an optional note. The bot fills in the time and suggests a category. With one account, it goes straight to the preview. You can change the details before saving.
- **Text entry.** Send `coffee 120k`, `salary 25 million`, or `yesterday 8pm taxi 80k` directly. Amounts are in toman.
- **Accounts and transactions.** Create accounts with opening balances, transfer money between them, and find transactions by type or note text. Transactions can be edited or deleted.
- **Reports and statistics.** View income, spending, net cash flow, highest and lowest expenses with their timestamps, average expense, and spending by category. Set monthly category budgets for threshold alerts and export the ledger to CSV.
- **Monthly spending review.** Browse past months, see the highest spending day and average daily spending, and open the underlying expenses. The current month through today is compared with the corresponding days of the prior month.
- **Calendar.** The English menu uses Gregorian months and weeks starting on Monday. Both languages use Tehran time.

Install Python 3.10 or newer and get a bot token with `/newbot` from [BotFather](https://t.me/BotFather). Run the setup commands below from the project directory. Open a private chat with your bot, send `/start`, choose a language, and create the first account. Use `/menu` to open the menu and `/cancel` to leave a form. Button colors appear in Telegram clients that support button styles.

New installations store data in `mahhesab.sqlite3`. Set `MAHHESAB_DB` to override the path for local runs. Upgrades continue to use the existing database. Docker stores data in a named volume. `docker compose down` stops the bot and keeps the volume. Adding `-v` removes it.

<a id="setup"></a>
## Setup · راه‌اندازی

Copy the template to `.env` and replace `YOUR_BOTFATHER_TOKEN` with your token.  
از قالب یک فایل `.env` بساز و توکن واقعی را جایگزین مقدار نمونه کن.

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

### Docker Compose

```bash
docker compose up -d --build
docker compose logs -f bot
```

### Online deployment · اجرای آنلاین

**فارسی**

1. روی یک VPS لینوکسی همیشه روشن با Docker و افزونهٔ Compose وارد شو. هاست باید اجازهٔ اجرای فرایند دائمی و اتصال خروجی HTTPS به `api.telegram.org` را بدهد. برای این بات دامنه، webhook یا پورت ورودی لازم نیست.
2. پس از انتشار این نسخه، دستورات پایین را روی سرور اجرا کن و در `.env` توکن BotFather را بگذار. برای بات عمومی، `MAHHESAB_ALLOWED_USER_IDS` را خالی بگذار. برای بات خصوصی، شناسه‌های عددی مجاز را با کاما وارد کن.
3. لاگ را بررسی کن و از چت خصوصی بات `/start` بزن. لینک `https://t.me/<bot_username>` را به کاربرها بده. هر کاربر دفتر جداگانه دارد. اگر بات را روی کامپیوتر هم اجرا کرده‌ای، قبل از روشن کردن نسخهٔ هاست آن را متوقف کن. هر توکن باید فقط یک نمونهٔ فعال داشته باشد.
4. برای به‌روزرسانی در همین پوشه `git pull` و سپس `docker compose up -d --build` را اجرا کن. volume را نگه دار و از داده‌ها نسخهٔ پشتیبان بگیر. `.env`، فایل SQLite و نسخه‌های پشتیبان را خصوصی نگه دار.

**English**

1. Use an always-on Linux VPS with Docker and the Compose plugin. The host must support a persistent process and outbound HTTPS to `api.telegram.org`. Long polling requires no domain, webhook, or inbound port.
2. Run these commands on your server after this version is published. Put your BotFather token into `.env`. Leave `MAHHESAB_ALLOWED_USER_IDS` empty for public access, or list permitted numeric Telegram user IDs separated by commas for a private bot.
3. Check the logs and send `/start` to your bot in a private chat. Share `https://t.me/<bot_username>`. Each user gets a separate ledger. Stop any local instance that uses the same token before running the hosted one.
4. To update, run `git pull` in the same directory, then `docker compose up -d --build`. Retain the volume and back up your database. Keep `.env`, the database, and backups private.

```bash
git clone https://github.com/iArvin0/MahHesab.git
cd MahHesab
cp .env.example .env
chmod 600 .env
nano .env
docker compose up -d --build
docker compose logs --tail 50 bot
```

اگر بات پاسخ نداد، `docker compose ps` و لاگ را چک کن. خطای timeout معمولاً به مسیر اتصال هاست مربوط است و خطای `Conflict` در دریافت پیام‌ها معمولاً از یک نمونهٔ دیگر با همان توکن می‌آید.

If the bot does not respond, check `docker compose ps` and the logs. Timeouts point to connectivity problems. A polling conflict usually means another process is using the same token.

### Local Python · اجرای محلی پایتون

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe bot.py
```

**Linux / macOS (Bash)**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python bot.py
```

### Offline checks · بررسی آفلاین

با اجرای محلی پایتون، بات روی کامپیوتر تو اجرا می‌شود و تا وقتی روشن و متصل باشد به پیام‌ها پاسخ می‌دهد. استفاده از خود بات در تلگرام به اینترنت نیاز دارد. برای بررسی منطق ثبت تراکنش و گزارش بدون اینترنت، پس از نصب کتابخانه‌ها دستور زیر را اجرا کن. این بررسی توکن نمی‌خواهد و از پایگاه‌دادهٔ موقت استفاده می‌کند.

Running Python locally keeps the bot on your computer. It can answer while the computer is on and connected. Chatting with the bot requires internet access. After installing the dependencies, this command checks transaction and report logic offline using a temporary database and no token.

```bash
python smoke_test.py
```

## License · مجوز

[MIT](LICENSE)

