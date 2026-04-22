import asyncio
import os
from datetime import datetime, timedelta
import pytz
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ========== НАЛАШТУВАННЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8641229015:AAHmaBDmCZgf7-oHfoHtBfm2aZABnmH-M2g")
CHAT_ID   = os.environ.get("CHAT_ID", "341010427")
TZ        = pytz.timezone("Europe/Warsaw")
# ==================================

bot       = Bot(token=BOT_TOKEN)
scheduler = AsyncIOScheduler(timezone=TZ)

WEEKDAYS_UK = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
MONTHS_UK   = ["", "січня", "лютого", "березня", "квітня", "травня", "червня",
               "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]

# ─────────────────────────────────────────
#  Посилання
# ─────────────────────────────────────────

LINKS = {
    "wasde":        "https://www.usda.gov/about-usda/general-information/staff-offices/office-chief-economist/commodity-markets/wasde-report",
    "crop":         "https://www.nass.usda.gov/Publications/National_Crop_Progress/",
    "eia":          "https://www.eia.gov/petroleum/supply/weekly/",
    "export_sales": "https://apps.fas.usda.gov/export-sales/esrd1.html",
    "cot":          "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
    "grain_stocks": "https://www.nass.usda.gov/Publications/Todays_Reports/",
    "acreage":      "https://www.nass.usda.gov/Publications/Todays_Reports/",
    "news":         "https://www.financialjuice.com/home",
}

# ─────────────────────────────────────────
#  Тікери (прямий і непрямий вплив)
# ─────────────────────────────────────────

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

async def send(text: str):
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML",
                           disable_web_page_preview=True)

# ─────────────────────────────────────────
#  Форматери повідомлень
# ─────────────────────────────────────────

def a(text: str, url: str) -> str:
    """Кліктабельне посилання."""
    return f'<a href="{url}">{text}</a>' if url else text


def msg_reminder(icon: str, name: str, time_str: str = "", desc: str = "",
                 direct: str = "", indirect: str = "", note: str = "",
                 link: str = "") -> str:
    now      = datetime.now(TZ)
    weekday  = WEEKDAYS_UK[now.weekday()]
    date_str = f"{weekday}, {now.day:02d}.{now.month:02d}.{now.year}"
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


def msg_release(icon: str, name: str, time_str: str, desc: str = "",
                direct: str = "", indirect: str = "", link: str = "") -> str:
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
#  Структура разових подій
# ─────────────────────────────────────────

def _wasde(dt: datetime, note: str = "") -> dict:
    t = TICKERS["wasde"]
    return dict(
        date         = dt,
        morning_hour = 8,
        icon         = "⚠️",
        name         = "USDA WASDE",
        desc         = "Найважливіший місячний звіт: світовий баланс попиту/пропозиції по всіх агрокультурах.",
        preview_time = "18:00",
        release_time = dt.replace(hour=18, minute=0, second=0),
        note         = note,
        direct       = t["direct"],
        indirect     = t["indirect"],
        link         = LINKS["wasde"],
    )


ONE_TIME = [

    # ── USDA WASDE 2026 ──
    _wasde(datetime(2026, 5, 12, tzinfo=TZ),
           note="🔥 Перший прогноз нового сезону 2026/27 — НАЙВАЖЛИВІШИЙ!"),
    _wasde(datetime(2026, 6, 11, tzinfo=TZ)),
    _wasde(datetime(2026, 7, 10, tzinfo=TZ)),
    _wasde(datetime(2026, 8, 12, tzinfo=TZ)),
    _wasde(datetime(2026, 9, 11, tzinfo=TZ)),
    _wasde(datetime(2026, 10, 9, tzinfo=TZ)),
    _wasde(datetime(2026, 11, 10, tzinfo=TZ)),
    _wasde(datetime(2026, 12, 10, tzinfo=TZ)),

    # ── Саміт Трамп–Сі ──
    dict(
        date         = datetime(2026, 5, 14, tzinfo=TZ),
        morning_hour = 8,
        icon         = "🌏",
        name         = "Саміт Трамп–Сі (день 1)",
        desc         = "Ключова геополітична подія для ринку сої.",
        preview_time = "протягом дня",
        release_time = None,
        note         = "Стеж за новинами протягом дня",
        direct       = "🫘 Soybean · Meal · Oil",
        indirect     = "",
        link         = LINKS["news"],
    ),
    dict(
        date         = datetime(2026, 5, 15, tzinfo=TZ),
        morning_hour = 8,
        icon         = "🌏",
        name         = "Саміт Трамп–Сі (день 2)",
        desc         = "Ключова геополітична подія для ринку сої.",
        preview_time = "протягом дня",
        release_time = None,
        note         = "Стеж за підсумками переговорів",
        direct       = "🫘 Soybean · Meal · Oil",
        indirect     = "",
        link         = LINKS["news"],
    ),

    # ── Grain Stocks + Acreage 30 червня ──
    dict(
        date         = datetime(2026, 6, 30, tzinfo=TZ),
        morning_hour = 8,
        icon         = "🌾",
        name         = "USDA Grain Stocks",
        desc         = "Квартальний звіт USDA про фактичні залишки зерна та олійних у сховищах США.",
        preview_time = "17:00",
        release_time = datetime(2026, 6, 30, 17, 0, tzinfo=TZ),
        note         = "⚡️ Сьогодні також виходить Acreage Report!",
        direct       = TICKERS["grain_stocks"]["direct"],
        indirect     = TICKERS["grain_stocks"]["indirect"],
        link         = LINKS["grain_stocks"],
    ),
    dict(
        date         = datetime(2026, 6, 30, tzinfo=TZ),
        morning_hour = None,
        icon         = "🌿",
        name         = "USDA Acreage Report",
        desc         = "Річний звіт USDA про засіяні площі. ⚡️ Другий великий шок року!",
        preview_time = "17:00",
        release_time = datetime(2026, 6, 30, 17, 5, tzinfo=TZ),
        note         = "",
        direct       = TICKERS["acreage"]["direct"],
        indirect     = TICKERS["acreage"]["indirect"],
        link         = LINKS["acreage"],
    ),

    # ── Grain Stocks 30 вересня ──
    dict(
        date         = datetime(2026, 9, 30, tzinfo=TZ),
        morning_hour = 8,
        icon         = "🌾",
        name         = "USDA Grain Stocks",
        desc         = "Квартальний звіт USDA про фактичні залишки зерна та олійних у сховищах США.",
        preview_time = "17:00",
        release_time = datetime(2026, 9, 30, 17, 0, tzinfo=TZ),
        note         = "",
        direct       = TICKERS["grain_stocks"]["direct"],
        indirect     = TICKERS["grain_stocks"]["indirect"],
        link         = LINKS["grain_stocks"],
    ),
]

# ─────────────────────────────────────────
#  Щотижневий огляд (субота 8:00)
# ─────────────────────────────────────────

async def weekly_preview():
    now = datetime.now(TZ)
    days_to_mon = (7 - now.weekday()) % 7
    if days_to_mon == 0:
        days_to_mon = 7
    monday = (now + timedelta(days=days_to_mon)).replace(hour=0, minute=0, second=0, microsecond=0)
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
        await send(header + "\n\nЦього тижня запланованих подій немає.")
        return

    lines = [header]
    for i in range(7):
        if i not in day_map:
            continue
        day, lst = day_map[i]
        lines.append(f"\n<b>{WEEKDAYS_UK[day.weekday()]}, {day.day:02d}.{day.month:02d}</b>")
        for time_str, icon, name, url in lst:
            lines.append(f"  {icon} {time_str} — {a(name, url)}")
    await send("\n".join(lines))

# ─────────────────────────────────────────
#  Crop Progress (квітень–листопад)
# ─────────────────────────────────────────

async def crop_progress_morning():
    if 4 <= datetime.now(TZ).month <= 11:
        t = TICKERS["crop_progress"]
        await send(msg_reminder(
            "🌱", "USDA Crop Progress", "22:00",
            desc="Щотижневий звіт USDA про стан посівів та збору врожаю по штатах США.",
            direct=t["direct"], indirect=t["indirect"],
            link=LINKS["crop"],
        ))

async def crop_progress_release():
    if 4 <= datetime.now(TZ).month <= 11:
        t = TICKERS["crop_progress"]
        await send(msg_release(
            "🌱", "USDA Crop Progress", "22:00",
            desc="Щотижневий звіт USDA про стан посівів та збору врожаю по штатах США.",
            direct=t["direct"], indirect=t["indirect"],
            link=LINKS["crop"],
        ))

# ─────────────────────────────────────────
#  Планувальник
# ─────────────────────────────────────────

def schedule_all():
    now = datetime.now(TZ)

    scheduler.add_job(weekly_preview, "cron", day_of_week="sat", hour=8, minute=0)
    scheduler.add_job(crop_progress_morning, "cron", day_of_week="mon", hour=8,  minute=0)
    scheduler.add_job(crop_progress_release, "cron", day_of_week="mon", hour=22, minute=0)

    # ── Середа: EIA ──
    t = TICKERS["eia"]
    scheduler.add_job(send, "cron", day_of_week="wed", hour=8, minute=0, args=[
        msg_reminder("🛢", "EIA Petroleum Status Report", "16:30",
                     desc="Тижневі запаси нафти/газу від Energy Information Administration.",
                     direct=t["direct"], indirect=t["indirect"],
                     note="Нафта → попит на biodiesel → соєва олія → ZM",
                     link=LINKS["eia"])
    ])
    scheduler.add_job(send, "cron", day_of_week="wed", hour=16, minute=30, args=[
        msg_release("🛢", "EIA Petroleum Status Report", "16:30",
                    desc="Тижневі запаси нафти/газу від Energy Information Administration.",
                    direct=t["direct"], indirect=t["indirect"],
                    link=LINKS["eia"])
    ])

    # ── Четвер: Export Sales ──
    t = TICKERS["export_sales"]
    scheduler.add_job(send, "cron", day_of_week="thu", hour=8, minute=0, args=[
        msg_reminder("📊", "USDA Export Sales", "14:30",
                     desc="Щотижневий звіт про фактичні експортні продажі агро-товарів США.",
                     direct=t["direct"], indirect=t["indirect"],
                     link=LINKS["export_sales"])
    ])
    scheduler.add_job(send, "cron", day_of_week="thu", hour=14, minute=30, args=[
        msg_release("📊", "USDA Export Sales", "14:30",
                    desc="Щотижневий звіт про фактичні експортні продажі агро-товарів США.",
                    direct=t["direct"], indirect=t["indirect"],
                    link=LINKS["export_sales"])
    ])

    # ── П'ятниця: COT ──
    t = TICKERS["cot"]
    scheduler.add_job(send, "cron", day_of_week="fri", hour=8, minute=0, args=[
        msg_reminder("📈", "COT Report (CFTC)", "21:30",
                     desc="Звіт CFTC про позиції трейдерів на ф'ючерсних ринках.",
                     direct=t["direct"],
                     note="Дані фіксуються у вівторок, публікуються в п'ятницю",
                     link=LINKS["cot"])
    ])
    scheduler.add_job(send, "cron", day_of_week="fri", hour=21, minute=30, args=[
        msg_release("📈", "COT Report (CFTC)", "21:30",
                    desc="Звіт CFTC про позиції трейдерів на ф'ючерсних ринках.\n"
                         "Дані фіксуються у вівторок, публікуються в п'ятницю.",
                    direct=t["direct"],
                    link=LINKS["cot"])
    ])

    # ── Разові події ──
    added, skipped = 0, 0
    for ev in ONE_TIME:
        if ev["morning_hour"] is not None:
            dt_m = ev["date"].replace(hour=ev["morning_hour"], minute=0, second=0)
            if dt_m > now:
                time_for_reminder = ev["preview_time"] if ":" in ev["preview_time"] else ""
                scheduler.add_job(send, "date", run_date=dt_m, args=[
                    msg_reminder(ev["icon"], ev["name"], time_for_reminder,
                                 desc=ev.get("desc", ""),
                                 direct=ev.get("direct", ""),
                                 indirect=ev.get("indirect", ""),
                                 note=ev.get("note", ""),
                                 link=ev.get("link", ""))
                ])
                added += 1
            else:
                skipped += 1

        dt_r = ev.get("release_time")
        if dt_r and dt_r > now:
            scheduler.add_job(send, "date", run_date=dt_r, args=[
                msg_release(ev["icon"], ev["name"], ev["preview_time"],
                            desc=ev.get("desc", ""),
                            direct=ev.get("direct", ""),
                            indirect=ev.get("indirect", ""),
                            link=ev.get("link", ""))
            ])
            added += 1

    print(f"  Разові події: додано {added}, пропущено як минулі {skipped}")

# ─────────────────────────────────────────
#  Запуск
# ─────────────────────────────────────────

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задано!")
        return

    print("🚀 Запуск Agro Calendar Bot...")
    schedule_all()
    scheduler.start()
    print("✅ Бот запущено! Зупинити: Ctrl+C")

    await send(
        "🤖 <b>Agro Calendar Bot</b> — запущено ✅\n"
        "──────────────────────\n"
        "<b>Щотижнево</b>\n"
        "📅 Сб 8:00 — огляд наступного тижня\n"
        f"🌱 Пн 8:00 + 22:00 — <a href=\"{LINKS['crop']}\">Crop Progress</a> (квіт–листоп)\n"
        f"🛢 Ср 8:00 + 16:30 — <a href=\"{LINKS['eia']}\">EIA Petroleum Status Report</a>\n"
        f"📊 Чт 8:00 + 14:30 — <a href=\"{LINKS['export_sales']}\">USDA Export Sales</a>\n"
        f"📈 Пт 8:00 + 21:30 — <a href=\"{LINKS['cot']}\">COT Report (CFTC)</a>\n\n"
        "<b>USDA WASDE 2026</b> (8:00 + 18:00)\n"
        f"⚠️ <a href=\"{LINKS['wasde']}\">12 трав · 11 черв · 10 лип · 12 серп\n"
        "   11 вер · 9 жовт · 10 лист · 10 груд</a>\n\n"
        "<b>Інші разові події</b>\n"
        f"🌏 14 трав 8:00 — <a href=\"{LINKS['news']}\">Саміт Трамп–Сі (день 1)</a>\n"
        f"🌏 15 трав 8:00 — <a href=\"{LINKS['news']}\">Саміт Трамп–Сі (день 2)</a>\n"
        f"🌾 30 черв 17:00 — <a href=\"{LINKS['grain_stocks']}\">Grain Stocks</a> + <a href=\"{LINKS['acreage']}\">Acreage</a>\n"
        f"🌾 30 вер 17:00 — <a href=\"{LINKS['grain_stocks']}\">Grain Stocks</a>"
    )

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())