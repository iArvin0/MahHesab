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

در اجرای محلی، داده‌ها در `kharjban.sqlite3` ذخیره می‌شوند. برای تعیین محل فایل از `KHARJBAN_DB` استفاده کن. اجرای Docker داده‌ها را در volume نگه می‌دارد. `docker compose down` بات را متوقف می‌کند و داده‌ها را نگه می‌دارد. گزینهٔ `-v` آن volume را حذف می‌کند. برای گیت‌هاب، قالب `.env.example` را همراه سورس منتشر کن. `.env` و فایل‌های پیش‌فرض پایگاه‌داده در `.gitignore` هستند. GitHub Actions راه‌اندازی آفلاین و ساخت ایمیج Docker را بررسی می‌کند.

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

Local runs store data in `kharjban.sqlite3`. Set `KHARJBAN_DB` to use another path. Docker stores data in a named volume. `docker compose down` stops the bot and keeps the volume. Adding `-v` removes the volume. Commit `.env.example` with the project source. Git ignores `.env` and the default database files. GitHub Actions checks offline startup and builds the Docker image.

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

بعد از نصب کتابخانه‌ها، دستور زیر را با همان پایتون اجرا کن. این بررسی توکن نمی‌خواهد و از پایگاه‌دادهٔ موقت استفاده می‌کند.

After installing the dependencies, run this with the same Python interpreter. It uses a temporary database and requires no bot token.

```bash
python smoke_test.py
```

