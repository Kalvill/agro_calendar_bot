import asyncio
import os
from datetime import datetime, timedelta
import pytz
from telegram import Bot, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ========== НАЛАШТУВАННЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID   = os.environ.get("CHAT_ID", "341010427")
TZ        = pytz.timezone("Europe/Warsaw")
# ==================================

scheduler = AsyncIOScheduler(timezone=TZ)

WEEKDAYS_UK = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
MONTHS_UK   = ["", "січня", "лютого", "березня", "квітня", "травня", "червня",
               "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]

LINKS = {
    "wasde":        "https://www.usda.gov/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report",
    "crop":         "https://www.nass.usda.gov/Publications/National_Crop_Progress/",
    "eia":          "https://www.eia.gov/petroleum/supply/weekly/",
    "export_sales": "https://apps.fas.usda.gov/export-sales/esrd1.html",
    "cot":          "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
    "grain_stocks": "https://www.nass.usda.gov/Publications/Todays_Reports/",
    "acreage":      "https://www.nass.usda.gov/Publications/Todays_Reports/",
    "news":         "https://www.financialjuice.com/home",
    "oilseeds":     "https://apps.fas.usda.gov/psdonline/circulars/oilseeds.pdf",
}

TICKERS = {
    "crop_progress": {
        "direct":   "☕ Coffee · 🍫 Cocoa · 🌿 Cotton · 🍬 Sugar · 🍊 OJ · 🌾 Wheat · 🫘 Soybean · Meal · Oil",
        "indirect": "🍚 Rice · 🪵 Lumber",
    },
    "eia": {
        "direct":   "🛢 Brent · 🛢 WTI Crude · ⛽ Nat Gas",
        "indirect": "💵 CAD · DXY · 🥇 Gold · 🥈 Silver · 🟤 Copper · 📈 S&P500 · VIX · 🪵 Lumber · 🍚 Rice",
    },
    "export_sales": {
        "direct":   "🌾 Wheat · 🫘 Soybean · Meal · Oil · 🌿 Cotton · 🍚 Rice",
        "indirect": "☕ Coffee · 🍫 Cocoa · 🍬 Sugar",
    },
    "cot": {
        "direct":   "Всі ф'ючерсні ринки — валюти, метали, енергетика, агро",
        "indirect": "",
    },
    "wasde": {
        "direct":   "🌾 Wheat · 🫘 Soybean · Meal · Oil · ☕ Coffee · 🍫 Cocoa · 🌿 Cotton · 🍬 Sugar · 🍚 Rice · 📈 S&P500 · VIX",
        "indirect": "🍊 OJ · 🪵 Lumber",
    },
    "grain_stocks": {
        "direct":   "🌾 Wheat · 🫘 Soybean · Meal · Oil · 🌿 Cotton",
        "indirect": "🍚 Rice · 🪵 Lumber",
    },
    "acreage": {
        "direct":   "🌾 Wheat · 🫘 Soybean · Meal · Oil · ☕ Coffee · 🌿 Cotton · 🍬 Sugar · 🍚 Rice",
        "indirect": "",
    },
}

# ─────────────────────────────────────────
#  Базова функція відправки
# ─────────────────────────────────────────

async def send(bot: Bot, text: str, chat_id: str = None):
    await bot.send_message(
        chat_id=chat_id or CHAT_ID,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ─────────────────────────────────────────
#  Форматери повідомлень
# ─────────────────────────────────────────

def a(text: str, url: str) -> str:
    return f'<a href="{url}">{text}</a>' if url else text

def msg_reminder(icon, name, time_str="", desc="", direct="", indirect="", note="", link="") -> str:
    now      = datetime.now(TZ)
    date_str = f"{WEEKDAYS_UK[now.weekday()]}, {now.day:02d}.{now.month:02d}.{now.year}"
    parts = [f"🔔 <b>{date_str} · Нагадування</b>", ""]
    parts.append(f"{icon} <b>{a(name, link)}</b>")
    if desc:
        parts.append(f"<i>{desc}</i>")
    if time_str:
        parts.append(f"🕐 Сьогодні о <b>{time_str}</b>")
    if note:
        parts.append(f"💬 {note}")
    if direct:
        parts.extend(["", f"🟢 {direct}"])
    if indirect:
        parts.append(f"🟡 {indirect}")
    return "\n".join(parts)

def msg_release(icon, name, time_str, desc="", direct="", indirect="", link="") -> str:
    now      = datetime.now(TZ)
    date_str = f"{now.day:02d}.{now.month:02d}.{now.year}"
    parts = [f"{icon} · <b>{a(name, link)}</b> ·"]
    parts.append(f"🕐 · {time_str} · {date_str}")
    if desc:
        parts.extend(["", desc])
    if direct:
        parts.extend(["", f"🟢 {direct}"])
    if indirect:
        parts.append(f"🟡 {indirect}")
    return "\n".join(parts)

# ─────────────────────────────────────────
#  Разові події
# ─────────────────────────────────────────

def _wasde(dt: datetime, note: str = "") -> dict:
    t = TICKERS["wasde"]
    return dict(
        date=dt, morning_hour=8, icon="⚠️", name="USDA WASDE",
        desc="Найважливіший місячний звіт: світовий баланс попиту/пропозиції по всіх агрокультурах.",
        preview_time="18:00", release_time=dt.replace(hour=18, minute=0, second=0),
        note=note, direct=t["direct"], indirect=t["indirect"], link=LINKS["wasde"],
    )

def _oilseeds(dt: datetime) -> dict:
    return dict(
        date=dt, morning_hour=8, icon="🫘", name="USDA Oilseeds: World Markets & Trade",
        desc="Щомісячний звіт FAS USDA про світовий баланс олійних культур.",
        preview_time="18:15", release_time=dt.replace(hour=18, minute=15, second=0),
        note="Виходить одночасно з WASDE",
        direct="🫘 Soybean · Meal · Oil · 🌿 Cotton · 🌴 Palm Oil",
        indirect="🌾 Wheat · ☕ Coffee", link=LINKS["oilseeds"],
    )

ONE_TIME = [
    _wasde(datetime(2026, 5, 12, tzinfo=TZ), note="🔥 Перший прогноз нового сезону 2026/27 — НАЙВАЖЛИВІШИЙ!"),
    _oilseeds(datetime(2026, 5, 12, tzinfo=TZ)),
    _wasde(datetime(2026, 6, 11, tzinfo=TZ)),
    _oilseeds(datetime(2026, 6, 11, tzinfo=TZ)),
    _wasde(datetime(2026, 7, 10, tzinfo=TZ)),
    _oilseeds(datetime(2026, 7, 10, tzinfo=TZ)),
    _wasde(datetime(2026, 8, 12, tzinfo=TZ)),
    _oilseeds(datetime(2026, 8, 12, tzinfo=TZ)),
    _wasde(datetime(2026, 9, 11, tzinfo=TZ)),
    _oilseeds(datetime(2026, 9, 11, tzinfo=TZ)),
    _wasde(datetime(2026, 10, 9, tzinfo=TZ)),
    _oilseeds(datetime(2026, 10, 9, tzinfo=TZ)),
    _wasde(datetime(2026, 11, 10, tzinfo=TZ)),
    _oilseeds(datetime(2026, 11, 10, tzinfo=TZ)),
    _wasde(datetime(2026, 12, 10, tzinfo=TZ)),
    _oilseeds(datetime(2026, 12, 10, tzinfo=TZ)),
    dict(
        date=datetime(2026, 5, 14, tzinfo=TZ), morning_hour=8,
        icon="🌏", name="Саміт Трамп–Сі (день 1)",
        desc="Ключова геополітична подія для ринку сої.",
        preview_time="протягом дня", release_time=None,
        note="Стеж за новинами протягом дня",
        direct="🫘 Soybean · Meal · Oil", indirect="", link=LINKS["news"],
    ),
    dict(
        date=datetime(2026, 5, 15, tzinfo=TZ), morning_hour=8,
        icon="🌏", name="Саміт Трамп–Сі (день 2)",
        desc="Ключова геополітична подія для ринку сої.",
        preview_time="протягом дня", release_time=None,
        note="Стеж за підсумками переговорів",
        direct="🫘 Soybean · Meal · Oil", indirect="", link=LINKS["news"],
    ),
    dict(
        date=datetime(2026, 6, 30, tzinfo=TZ), morning_hour=8,
        icon="🌾", name="USDA Grain Stocks",
        desc="Квартальний звіт USDA про фактичні залишки зерна та олійних у сховищах США.",
        preview_time="17:00", release_time=datetime(2026, 6, 30, 17, 0, tzinfo=TZ),
        note="⚡️ Сьогодні також виходить Acreage Report!",
        direct=TICKERS["grain_stocks"]["direct"], indirect=TICKERS["grain_stocks"]["indirect"],
        link=LINKS["grain_stocks"],
    ),
    dict(
        date=datetime(2026, 6, 30, tzinfo=TZ), morning_hour=None,
        icon="🌿", name="USDA Acreage Report",
        desc="Річний звіт USDA про засіяні площі. ⚡️ Другий великий шок року!",
        preview_time="17:00", release_time=datetime(2026, 6, 30, 17, 5, tzinfo=TZ),
        note="", direct=TICKERS["acreage"]["direct"], indirect=TICKERS["acreage"]["indirect"],
        link=LINKS["acreage"],
    ),
    dict(
        date=datetime(2026, 9, 30, tzinfo=TZ), morning_hour=8,
        icon="🌾", name="USDA Grain Stocks",
        desc="Квартальний звіт USDA про фактичні залишки зерна та олійних у сховищах США.",
        preview_time="17:00", release_time=datetime(2026, 9, 30, 17, 0, tzinfo=TZ),
        note="", direct=TICKERS["grain_stocks"]["direct"], indirect=TICKERS["grain_stocks"]["indirect"],
        link=LINKS["grain_stocks"],
    ),
]

# ─────────────────────────────────────────
#  Щотижневий огляд
# ─────────────────────────────────────────

def get_active_monday(now: datetime, week_change_day: int = 5) -> datetime:
    """
    Повертає понеділок «активного» тижня.
    week_change_day: день тижня коли тиждень перемикається (0=Пн … 6=Нд, за замовч. 5=Сб)
    - До цього дня (включно з пн–пт якщо зміна в сб) → поточний тиждень
    - Починаючи з цього дня → наступний тиждень
    """
    this_monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    if now.weekday() >= week_change_day:
        return this_monday + timedelta(weeks=1)
    return this_monday


async def weekly_preview(bot: Bot, chat_id: str = None, week_change_day: int = 5):
    now    = datetime.now(TZ)
    monday = get_active_monday(now, week_change_day)
    sunday = monday + timedelta(days=6)

    def date_label(dt):
        return f"{dt.day} {MONTHS_UK[dt.month]}"

    day_map = {}
    for i in range(7):
        day = monday + timedelta(days=i)
        wd, m = day.weekday(), day.month
        lst = []
        if wd == 0 and 4 <= m <= 11:
            lst.append(("22:00", "🌱", "USDA Crop Progress", LINKS["crop"]))
        if wd == 2:
            lst.append(("16:30", "🛢", "EIA Petroleum Status Report", LINKS["eia"]))
        if wd == 3:
            lst.append(("14:30", "📊", "USDA Export Sales", LINKS["export_sales"]))
        if wd == 4:
            lst.append(("21:30", "📈", "COT Report (CFTC)", LINKS["cot"]))
        for ev in ONE_TIME:
            if ev["date"].date() == day.date():
                lst.append((ev["preview_time"], ev["icon"], ev["name"], ev.get("link", "")))
        if lst:
            day_map[i] = (day, lst)

    header = (f"📅 <b>Розклад на тиждень</b>\n"
              f"{date_label(monday)} — {date_label(sunday)} {sunday.year}\n"
              f"──────────────────────")

    if not day_map:
        await send(bot, header + "\n\nЦього тижня запланованих подій немає.", chat_id)
        return

    lines = [header]
    for i in range(7):
        if i not in day_map:
            continue
        day, lst = day_map[i]
        lines.append(f"\n<b>{WEEKDAYS_UK[day.weekday()]}, {day.day:02d}.{day.month:02d}</b>")
        for time_str, icon, name, url in lst:
            lines.append(f"  {icon} {time_str} — {a(name, url)}")
    await send(bot, "\n".join(lines), chat_id)

# ─────────────────────────────────────────
#  Крон-задачі (обгортки для scheduler)
# ─────────────────────────────────────────

def make_cron_jobs(bot: Bot):
    async def job_crop_morning():
        if 4 <= datetime.now(TZ).month <= 11:
            t = TICKERS["crop_progress"]
            await send(bot, msg_reminder("🌱", "USDA Crop Progress", "22:00",
                desc="Щотижневий звіт USDA про стан посівів та збору врожаю по штатах США.",
                direct=t["direct"], indirect=t["indirect"], link=LINKS["crop"]))

    async def job_crop_release():
        if 4 <= datetime.now(TZ).month <= 11:
            t = TICKERS["crop_progress"]
            await send(bot, msg_release("🌱", "USDA Crop Progress", "22:00",
                desc="Щотижневий звіт USDA про стан посівів та збору врожаю по штатах США.",
                direct=t["direct"], indirect=t["indirect"], link=LINKS["crop"]))

    async def job_eia_morning():
        t = TICKERS["eia"]
        await send(bot, msg_reminder("🛢", "EIA Petroleum Status Report", "16:30",
            desc="Тижневі запаси нафти/газу від Energy Information Administration.",
            direct=t["direct"], indirect=t["indirect"],
            note="Нафта → попит на biodiesel → соєва олія → ZM", link=LINKS["eia"]))

    async def job_eia_release():
        t = TICKERS["eia"]
        await send(bot, msg_release("🛢", "EIA Petroleum Status Report", "16:30",
            desc="Тижневі запаси нафти/газу від Energy Information Administration.",
            direct=t["direct"], indirect=t["indirect"], link=LINKS["eia"]))

    async def job_export_morning():
        t = TICKERS["export_sales"]
        await send(bot, msg_reminder("📊", "USDA Export Sales", "14:30",
            desc="Щотижневий звіт про фактичні експортні продажі агро-товарів США.",
            direct=t["direct"], indirect=t["indirect"], link=LINKS["export_sales"]))

    async def job_export_release():
        t = TICKERS["export_sales"]
        await send(bot, msg_release("📊", "USDA Export Sales", "14:30",
            desc="Щотижневий звіт про фактичні експортні продажі агро-товарів США.",
            direct=t["direct"], indirect=t["indirect"], link=LINKS["export_sales"]))

    async def job_cot_morning():
        t = TICKERS["cot"]
        await send(bot, msg_reminder("📈", "COT Report (CFTC)", "21:30",
            desc="Звіт CFTC про позиції трейдерів на ф'ючерсних ринках.",
            direct=t["direct"],
            note="Дані фіксуються у вівторок, публікуються в п'ятницю", link=LINKS["cot"]))

    async def job_cot_release():
        t = TICKERS["cot"]
        await send(bot, msg_release("📈", "COT Report (CFTC)", "21:30",
            desc="Звіт CFTC про позиції трейдерів на ф'ючерсних ринках.\n"
                 "Дані фіксуються у вівторок, публікуються в п'ятницю.",
            direct=t["direct"], link=LINKS["cot"]))

    async def job_weekly():
        await weekly_preview(bot)

    return (job_crop_morning, job_crop_release, job_eia_morning, job_eia_release,
            job_export_morning, job_export_release, job_cot_morning, job_cot_release,
            job_weekly)

# ─────────────────────────────────────────
#  ════════ КОМАНДИ МЕНЮ ════════
# ─────────────────────────────────────────

async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Зведення подій на сьогодні"""
    now = datetime.now(TZ)
    lines = [f"📋 <b>Події на сьогодні</b>  {WEEKDAYS_UK[now.weekday()]}, {now.day:02d}.{now.month:02d}.{now.year}",
             "──────────────────────"]
    found = False

    wd, m = now.weekday(), now.month
    if wd == 0 and 4 <= m <= 11:
        lines.append(f"🌱 22:00 — {a('USDA Crop Progress', LINKS['crop'])}")
        found = True
    if wd == 2:
        lines.append(f"🛢 16:30 — {a('EIA Petroleum Status Report', LINKS['eia'])}")
        found = True
    if wd == 3:
        lines.append(f"📊 14:30 — {a('USDA Export Sales', LINKS['export_sales'])}")
        found = True
    if wd == 4:
        lines.append(f"📈 21:30 — {a('COT Report (CFTC)', LINKS['cot'])}")
        found = True
    for ev in ONE_TIME:
        if ev["date"].date() == now.date():
            lines.append(f"{ev['icon']} {ev['preview_time']} — {a(ev['name'], ev.get('link',''))}")
            found = True

    if not found:
        lines.append("Сьогодні запланованих звітів немає.")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML",
                                    disable_web_page_preview=True)

async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📅 Розклад на тиждень"""
    wcd = context.bot_data.get("week_change_day", 5)
    await weekly_preview(context.bot, str(update.effective_chat.id), week_change_day=wcd)

async def cmd_actuals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚡️ Активні нагадування"""
    now = datetime.now(TZ)
    upcoming = []
    for ev in ONE_TIME:
        if ev["date"] >= now.replace(hour=0, minute=0, second=0, microsecond=0):
            upcoming.append(ev)

    upcoming.sort(key=lambda x: x["date"])
    lines = ["⚡️ <b>Активні разові події</b>", "──────────────────────"]
    for ev in upcoming[:10]:
        d = ev["date"]
        lines.append(f"{ev['icon']} <b>{d.day:02d}.{d.month:02d}</b> {ev['preview_time']} — "
                     f"{a(ev['name'], ev.get('link',''))}")
        if ev.get("note"):
            lines.append(f"   💬 {ev['note']}")

    if len(upcoming) > 10:
        lines.append(f"\n...і ще {len(upcoming)-10} подій")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML",
                                    disable_web_page_preview=True)

async def cmd_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Всі регулярні звіти"""
    text = (
        "📊 <b>Регулярні звіти</b>\n"
        "──────────────────────\n"
        f"🌱 <b>USDA Crop Progress</b> — {a('посилання', LINKS['crop'])}\n"
        "   Щопонеділка 22:00 (квіт–листоп)\n"
        f"   🟢 {TICKERS['crop_progress']['direct']}\n\n"
        f"🛢 <b>EIA Petroleum Status</b> — {a('посилання', LINKS['eia'])}\n"
        "   Щосереди 16:30\n"
        f"   🟢 {TICKERS['eia']['direct']}\n\n"
        f"📊 <b>USDA Export Sales</b> — {a('посилання', LINKS['export_sales'])}\n"
        "   Щочетверга 14:30\n"
        f"   🟢 {TICKERS['export_sales']['direct']}\n\n"
        f"📈 <b>COT Report (CFTC)</b> — {a('посилання', LINKS['cot'])}\n"
        "   Щоп'ятниці 21:30\n"
        f"   🟢 {TICKERS['cot']['direct']}\n\n"
        f"⚠️ <b>USDA WASDE</b> — {a('посилання', LINKS['wasde'])}\n"
        "   Щомісяця, ~12-е число, 18:00\n"
        f"   🟢 {TICKERS['wasde']['direct']}\n\n"
        f"🫘 <b>USDA Oilseeds</b> — {a('посилання', LINKS['oilseeds'])}\n"
        "   Одночасно з WASDE, 18:15"
    )
    await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ Налаштування бота"""
    current_tz  = context.bot_data.get("timezone", "Europe/Warsaw")
    wcd         = context.bot_data.get("week_change_day", 5)
    now_local   = datetime.now(pytz.timezone(current_tz))

    WCD_NAMES = {0:"Пн", 1:"Вт", 2:"Ср", 3:"Чт", 4:"Пт", 5:"Сб", 6:"Нд"}

    tz_keyboard = [
        [InlineKeyboardButton("🌍 UTC+0  London",         callback_data="tz_UTC+0")],
        [
            InlineKeyboardButton("🇵🇱 UTC+1  Warsaw/Paris", callback_data="tz_UTC+1"),
            InlineKeyboardButton("🇺🇦 UTC+2  Kyiv",         callback_data="tz_UTC+2"),
        ],
        [
            InlineKeyboardButton("🇹🇷 UTC+3  Istanbul",     callback_data="tz_UTC+3"),
            InlineKeyboardButton("🇺🇸 UTC-5  New York",     callback_data="tz_UTC-5"),
        ],
    ]

    wcd_keyboard = [
        [
            InlineKeyboardButton(f"{'✅ ' if wcd==4 else ''}Пт", callback_data="wcd_4"),
            InlineKeyboardButton(f"{'✅ ' if wcd==5 else ''}Сб", callback_data="wcd_5"),
            InlineKeyboardButton(f"{'✅ ' if wcd==6 else ''}Нд", callback_data="wcd_6"),
        ]
    ]
    done_keyboard = [[InlineKeyboardButton("✅  Готово", callback_data="settings_done")]]

    reply_markup = InlineKeyboardMarkup(tz_keyboard + wcd_keyboard + done_keyboard)
    tz_label_map  = {v[0]: v[1] for v in TZ_MAP.values()}
    tz_display    = tz_label_map.get(current_tz, current_tz)

    text = (
        "⚙️ <b>Налаштування</b>\n"
        "──────────────────────\n"
        f"🕐 Часовий пояс: <b>{tz_display}</b>\n"
        f"🕐 Час зараз: <b>{now_local.strftime('%H:%M')}</b>\n\n"
        f"📅 Тиждень оновлюється: <b>{WCD_NAMES[wcd]}</b>\n"
        "<i>(у цей день /week переключається на наступний тиждень)</i>\n\n"
        "<b>Оберіть часовий пояс:</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """❓ Допомога по командах"""
    text = (
        "ℹ️ <b>Допомога по командах</b>\n"
        "──────────────────────\n"
        "📋 /daily — події на сьогодні\n"
        "📅 /week — розклад на активний тиждень\n"
        "⚡️ /actuals — активні разові події\n"
        "📊 /reports — всі регулярні звіти з описом\n"
        "⚙️ /settings — налаштування (часовий пояс)\n"
        "❓ /help — ця підказка\n\n"
        "<i>Бот автоматично надсилає нагадування о 8:00 перед кожним звітом "
        "та повідомлення в момент виходу звіту.</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

# ─────────────────────────────────────────
#  Обробка вибору часового поясу
# ─────────────────────────────────────────

TZ_MAP = {
    "tz_UTC+0": ("UTC",              "🌍 UTC+0 — London, Lisbon"),
    "tz_UTC+1": ("Europe/Warsaw",    "🇵🇱 UTC+1 — Warsaw, Paris, Berlin"),
    "tz_UTC+2": ("Europe/Kyiv",      "🇺🇦 UTC+2 — Kyiv, Helsinki"),
    "tz_UTC+3": ("Europe/Istanbul",  "🇹🇷 UTC+3 — Istanbul, Dubai"),
    "tz_UTC-5": ("America/New_York", "🇺🇸 UTC-5 — New York, Toronto"),
}

WCD_NAMES = {0:"Понеділок", 1:"Вівторок", 2:"Середа", 3:"Четвер", 4:"П'ятниця", 5:"Субота", 6:"Неділя"}

def build_settings_markup(wcd: int) -> InlineKeyboardMarkup:
    tz_keyboard = [
        [InlineKeyboardButton("🌍 UTC+0  London",         callback_data="tz_UTC+0")],
        [
            InlineKeyboardButton("🇵🇱 UTC+1  Warsaw/Paris", callback_data="tz_UTC+1"),
            InlineKeyboardButton("🇺🇦 UTC+2  Kyiv",         callback_data="tz_UTC+2"),
        ],
        [
            InlineKeyboardButton("🇹🇷 UTC+3  Istanbul",     callback_data="tz_UTC+3"),
            InlineKeyboardButton("🇺🇸 UTC-5  New York",     callback_data="tz_UTC-5"),
        ],
    ]
    wcd_keyboard = [[
        InlineKeyboardButton(f"{'✅ ' if wcd==4 else ''}Пт", callback_data="wcd_4"),
        InlineKeyboardButton(f"{'✅ ' if wcd==5 else ''}Сб", callback_data="wcd_5"),
        InlineKeyboardButton(f"{'✅ ' if wcd==6 else ''}Нд", callback_data="wcd_6"),
    ]]
    done_keyboard = [[InlineKeyboardButton("✅  Готово", callback_data="settings_done")]]
    return InlineKeyboardMarkup(tz_keyboard + wcd_keyboard + done_keyboard)


def build_settings_text(current_tz: str, wcd: int) -> str:
    tz_label_map = {v[0]: v[1] for v in TZ_MAP.values()}
    tz_display   = tz_label_map.get(current_tz, current_tz)
    now_local    = datetime.now(pytz.timezone(current_tz))
    return (
        "⚙️ <b>Налаштування</b>\n"
        "──────────────────────\n"
        f"🕐 Часовий пояс: <b>{tz_display}</b>\n"
        f"🕐 Час зараз: <b>{now_local.strftime('%H:%M')}</b>\n\n"
        f"📅 Тиждень оновлюється: <b>{WCD_NAMES[wcd]}</b>\n"
        "<i>(у цей день /week переключається на наступний тиждень)</i>\n\n"
        "<b>Оберіть часовий пояс:</b>"
    )


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── Закрити налаштування ──
    if data == "settings_done":
        await query.delete_message()
        return

    # ── Часовий пояс ──
    if data in TZ_MAP:
        tz_name, _ = TZ_MAP[data]
        context.bot_data["timezone"] = tz_name
        wcd = context.bot_data.get("week_change_day", 5)
        await query.edit_message_text(
            build_settings_text(tz_name, wcd),
            parse_mode="HTML",
            reply_markup=build_settings_markup(wcd),
        )
        return

    # ── День оновлення тижня ──
    if data.startswith("wcd_"):
        wcd = int(data.split("_")[1])
        context.bot_data["week_change_day"] = wcd
        current_tz = context.bot_data.get("timezone", "Europe/Warsaw")
        await query.edit_message_text(
            build_settings_text(current_tz, wcd),
            parse_mode="HTML",
            reply_markup=build_settings_markup(wcd),
        )
        return

# ─────────────────────────────────────────
#  Реєстрація команд у меню Telegram
# ─────────────────────────────────────────

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand("daily",   "📋 Зведення подій на сьогодні"),
        BotCommand("week",    "📅 Розклад на активний тиждень"),
        BotCommand("actuals", "⚡️ Активні разові події"),
        BotCommand("reports", "📊 Всі регулярні звіти"),
        BotCommand("settings","⚙️ Налаштування"),
        BotCommand("help",    "❓ Допомога"),
    ]
    await bot.set_my_commands(commands)

    # Опис бота — відображається в профілі (кнопки Bot Help / Bot Settings з'являються
    # автоматично в Telegram коли зареєстровані команди /help і /settings)
    await bot.set_my_description(
        "📊 Agro Calendar Bot\n\n"
        "Автоматичні нагадування про виходи ключових агро-звітів:\n"
        "USDA WASDE · Crop Progress · EIA · Export Sales · COT\n\n"
        "Використовуй /help для списку команд або /settings для налаштувань."
    )
    await bot.set_my_short_description("📊 Нагадування про агро-звіти USDA, EIA, CFTC")
    print("✅ Команди меню та опис бота зареєстровано")

# ─────────────────────────────────────────
#  Планувальник
# ─────────────────────────────────────────

def schedule_all(bot: Bot):
    now = datetime.now(TZ)
    (crop_m, crop_r, eia_m, eia_r,
     exp_m, exp_r, cot_m, cot_r, weekly) = make_cron_jobs(bot)

    scheduler.add_job(weekly,  "cron", day_of_week="sat", hour=8,  minute=0)
    scheduler.add_job(crop_m,  "cron", day_of_week="mon", hour=8,  minute=0)
    scheduler.add_job(crop_r,  "cron", day_of_week="mon", hour=22, minute=0)
    scheduler.add_job(eia_m,   "cron", day_of_week="wed", hour=8,  minute=0)
    scheduler.add_job(eia_r,   "cron", day_of_week="wed", hour=16, minute=30)
    scheduler.add_job(exp_m,   "cron", day_of_week="thu", hour=8,  minute=0)
    scheduler.add_job(exp_r,   "cron", day_of_week="thu", hour=14, minute=30)
    scheduler.add_job(cot_m,   "cron", day_of_week="fri", hour=8,  minute=0)
    scheduler.add_job(cot_r,   "cron", day_of_week="fri", hour=21, minute=30)

    added, skipped = 0, 0
    for ev in ONE_TIME:
        if ev["morning_hour"] is not None:
            dt_m = ev["date"].replace(hour=ev["morning_hour"], minute=0, second=0)
            if dt_m > now:
                scheduler.add_job(
                    lambda e=ev: send(bot, msg_reminder(
                        e["icon"], e["name"],
                        e["preview_time"] if ":" in e["preview_time"] else "",
                        desc=e.get("desc",""), direct=e.get("direct",""),
                        indirect=e.get("indirect",""), note=e.get("note",""),
                        link=e.get("link","")
                    )),
                    "date", run_date=dt_m
                )
                added += 1
            else:
                skipped += 1

        dt_r = ev.get("release_time")
        if dt_r and dt_r > now:
            scheduler.add_job(
                lambda e=ev: send(bot, msg_release(
                    e["icon"], e["name"], e["preview_time"],
                    desc=e.get("desc",""), direct=e.get("direct",""),
                    indirect=e.get("indirect",""), link=e.get("link","")
                )),
                "date", run_date=dt_r
            )
            added += 1

    print(f"  Разові події: додано {added}, пропущено як минулі {skipped}")

# ─────────────────────────────────────────
#  Запуск
# ─────────────────────────────────────────

async def post_init(application: Application):
    """Викликається після ініціалізації application"""
    bot = application.bot
    await set_bot_commands(bot)
    schedule_all(bot)
    scheduler.start()

    await send(bot,
        "🤖 <b>Agro Calendar Bot</b> — запущено ✅\n"
        "──────────────────────\n"
        "Використовуй меню або команди:\n"
        "📋 /daily · 📅 /week · ⚡️ /actuals\n"
        "📊 /reports · ⚙️ /settings · ❓ /help\n"
        "──────────────────────\n"
        "<b>Щотижнево</b>\n"
        "📅 Сб 8:00 — огляд наступного тижня\n"
        f"🌱 Пн 8:00 + 22:00 — <a href=\"{LINKS['crop']}\">Crop Progress</a> (квіт–листоп)\n"
        f"🛢 Ср 8:00 + 16:30 — <a href=\"{LINKS['eia']}\">EIA Petroleum Status Report</a>\n"
        f"📊 Чт 8:00 + 14:30 — <a href=\"{LINKS['export_sales']}\">USDA Export Sales</a>\n"
        f"📈 Пт 8:00 + 21:30 — <a href=\"{LINKS['cot']}\">COT Report (CFTC)</a>"
    )


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задано!")
        return

    print("🚀 Запуск Agro Calendar Bot...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ── Реєстрація обробників команд ──
    app.add_handler(CommandHandler("daily",    cmd_daily))
    app.add_handler(CommandHandler("week",     cmd_week))
    app.add_handler(CommandHandler("actuals",  cmd_actuals))
    app.add_handler(CommandHandler("reports",  cmd_reports))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("help",     cmd_help))

    # ── Обробник кнопок (часовий пояс) ──
    app.add_handler(CallbackQueryHandler(handle_settings_callback, pattern="^(tz_|wcd_)"))

    print("✅ Бот запущено! Зупинити: Ctrl+C")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()