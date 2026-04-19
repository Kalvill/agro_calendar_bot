import asyncio
import os
from datetime import datetime, timedelta
import pytz
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ========== НАЛАШТУВАННЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8641229015:AAHF6NmgYJM7ABHraR8MTib_FDXCWxESZuM")
CHAT_ID   = os.environ.get("CHAT_ID", "341010427")
TZ        = pytz.timezone("Europe/Warsaw")
# ==================================

bot       = Bot(token=BOT_TOKEN)
scheduler = AsyncIOScheduler(timezone=TZ)

WEEKDAYS_UK = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
MONTHS_UK   = ["", "січня", "лютого", "березня", "квітня", "травня", "червня",
               "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]


# ─────────────────────────────────────────
#  Базова функція відправки
# ─────────────────────────────────────────

async def send(text: str):
    await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")


# ─────────────────────────────────────────
#  Форматери повідомлень
# ─────────────────────────────────────────

def msg_reminder(icon: str, name: str, time_str: str = "",
                 tickers: str = "", note: str = "") -> str:
    parts = ["🔔 <b>Нагадування</b>", ""]
    parts.append(f"{icon} <b>{name}</b>")
    if time_str:
        parts.append(f"🕐 Сьогодні о <b>{time_str}</b> за Варшавою")
    if note:
        parts.append(f"💬 <i>{note}</i>")
    if tickers:
        parts.extend(["", tickers])
    return "\n".join(parts)


def msg_release(icon: str, name: str, time_str: str,
                desc: str = "", tickers: str = "", link: str = "") -> str:
    parts = [f"{icon} <b>{name}</b>", f"🕐 <b>{time_str}</b> · Варшава"]
    if desc:
        parts.extend(["", desc])
    if tickers:
        parts.extend(["", tickers])
    if link:
        parts.extend(["", f"🔗 {link}"])
    return "\n".join(parts)


# ─────────────────────────────────────────
#  Структура разових подій
# ─────────────────────────────────────────

def _wasde(dt: datetime, note: str = "") -> dict:
    return dict(
        date         = dt,
        morning_hour = 8,
        icon         = "⚠️",
        name         = "USDA WASDE",
        preview_time = "18:00",
        release_time = dt.replace(hour=18, minute=0, second=0),
        note         = note,
        desc         = "Прогнози попиту, пропозиції, запасів і середніх цін",
        tickers      = "🌽 Corn · 🌾 Wheat · 🫘 Soybean/Meal/Oil · Rice · Cotton · Sugar",
        link         = "usda.gov/wasde",
    )


ONE_TIME = [

    # ── USDA WASDE 2026 (конкретні дати) ──
    _wasde(datetime(2026, 5, 12, tzinfo=TZ),
           note="🔥 Перший прогноз нового сезону 2026/27 — НАЙВАЖЛИВІШИЙ!"),
    _wasde(datetime(2026, 6, 11, tzinfo=TZ)),
    _wasde(datetime(2026, 7, 10, tzinfo=TZ)),
    _wasde(datetime(2026, 8, 12, tzinfo=TZ)),
    _wasde(datetime(2026, 9, 11, tzinfo=TZ)),
    _wasde(datetime(2026, 10, 9, tzinfo=TZ)),
    _wasde(datetime(2026, 11, 10, tzinfo=TZ)),
    _wasde(datetime(2026, 12, 10, tzinfo=TZ)),

    # ── Саміт Трамп–Сі (8:00 обидва дні, тільки нагадування) ──
    dict(
        date         = datetime(2026, 5, 14, tzinfo=TZ),
        morning_hour = 8,
        icon         = "🌏",
        name         = "Саміт Трамп–Сі (день 1)",
        preview_time = "протягом дня",
        release_time = None,
        note         = "Ключова подія для ринку сої!",
        desc         = "Стеж за новинами протягом дня",
        tickers      = "🫘 Soybean",
        link         = "",
    ),
    dict(
        date         = datetime(2026, 5, 15, tzinfo=TZ),
        morning_hour = 8,
        icon         = "🌏",
        name         = "Саміт Трамп–Сі (день 2)",
        preview_time = "протягом дня",
        release_time = None,
        note         = "Стеж за підсумками переговорів",
        desc         = "Підсумки переговорів — ключово для ринку сої",
        tickers      = "🫘 Soybean",
        link         = "",
    ),

    # ── Grain Stocks + Acreage 30 червня ──
    dict(
        date         = datetime(2026, 6, 30, tzinfo=TZ),
        morning_hour = 8,
        icon         = "🌾",
        name         = "USDA Grain Stocks",
        preview_time = "17:00",
        release_time = datetime(2026, 6, 30, 17, 0, tzinfo=TZ),
        note         = "⚡️ Сьогодні також виходить Acreage Report!",
        desc         = "Фактичні запаси зерна в США",
        tickers      = "🌽 Corn · 🌾 Wheat · 🫘 Soybean",
        link         = "usda.gov/nass",
    ),
    dict(
        date         = datetime(2026, 6, 30, tzinfo=TZ),
        morning_hour = None,
        icon         = "🌿",
        name         = "USDA Acreage Report",
        preview_time = "17:00",
        release_time = datetime(2026, 6, 30, 17, 5, tzinfo=TZ),
        note         = "",
        desc         = "Фактично засіяні площі — підтвердження березневих намірів\n⚡️ Другий великий шок року!",
        tickers      = "🌽 Corn · 🫘 Soybean · 🌾 Wheat · Cotton",
        link         = "usda.gov/nass",
    ),

    # ── Grain Stocks 30 вересня ──
    dict(
        date         = datetime(2026, 9, 30, tzinfo=TZ),
        morning_hour = 8,
        icon         = "🌾",
        name         = "USDA Grain Stocks",
        preview_time = "17:00",
        release_time = datetime(2026, 9, 30, 17, 0, tzinfo=TZ),
        note         = "",
        desc         = "Фактичні запаси зерна в США",
        tickers      = "🌽 Corn · 🌾 Wheat · 🫘 Soybean",
        link         = "usda.gov/nass",
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
    monday = (now + timedelta(days=days_to_mon)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6)

    def date_label(dt):
        return f"{dt.day} {MONTHS_UK[dt.month]}"

    day_map = {}

    for i in range(7):
        day = monday + timedelta(days=i)
        wd  = day.weekday()
        m   = day.month
        lst = []

        if wd == 0 and 4 <= m <= 11:
            lst.append(("22:00", "🌱", "USDA Crop Progress"))
        if wd == 2:  # середа
            lst.append(("16:30", "🛢", "EIA Petroleum Status Report"))
        if wd == 3:
            lst.append(("14:30", "📊", "USDA Export Sales"))
        if wd == 4:
            lst.append(("21:30", "📈", "COT Report (CFTC)"))

        for ev in ONE_TIME:
            if ev["date"].date() == day.date():
                lst.append((ev["preview_time"], ev["icon"], ev["name"]))

        if lst:
            day_map[i] = (day, lst)

    header = (
        f"📅 <b>Розклад на тиждень</b>\n"
        f"{date_label(monday)} — {date_label(sunday)} {sunday.year}\n"
        f"──────────────────────"
    )

    if not day_map:
        await send(header + "\n\nЦього тижня запланованих подій немає.")
        return

    lines = [header]
    for i in range(7):
        if i not in day_map:
            continue
        day, lst = day_map[i]
        wd_name = WEEKDAYS_UK[day.weekday()]
        lines.append(f"\n<b>{wd_name}, {day.day:02d}.{day.month:02d}</b>")
        for time_str, icon, name in lst:
            lines.append(f"  {icon} {time_str} — {name}")

    await send("\n".join(lines))


# ─────────────────────────────────────────
#  Crop Progress (тільки квітень–листопад)
# ─────────────────────────────────────────

async def crop_progress_morning():
    if 4 <= datetime.now(TZ).month <= 11:
        await send(msg_reminder(
            "🌱", "USDA Crop Progress", "22:00",
            tickers="🌽 Corn · 🫘 Soybean · 🌾 Wheat · Cotton",
        ))

async def crop_progress_release():
    if 4 <= datetime.now(TZ).month <= 11:
        await send(msg_release(
            "🌱", "USDA Crop Progress", "22:00",
            desc="Стан посівів та збору врожаю по штатах США",
            tickers="🌽 Corn · 🫘 Soybean · 🌾 Wheat · Cotton",
            link="usda.gov/nass",
        ))


# ─────────────────────────────────────────
#  Планувальник
# ─────────────────────────────────────────

def schedule_all():
    now = datetime.now(TZ)

    # ── Субота: тижневий огляд ──
    scheduler.add_job(weekly_preview, "cron", day_of_week="sat", hour=8, minute=0)

    # ── Понеділок: Crop Progress ──
    scheduler.add_job(crop_progress_morning, "cron", day_of_week="mon", hour=8,  minute=0)
    scheduler.add_job(crop_progress_release, "cron", day_of_week="mon", hour=22, minute=0)

    # ── Середа: EIA Petroleum ──
    scheduler.add_job(send, "cron", day_of_week="wed", hour=8, minute=0, args=[
        msg_reminder("🛢", "EIA Petroleum Status Report", "16:30",
                     tickers="🛢 Нафта · 🌱 Biodiesel · ZM",
                     note="Запаси нафти впливають на попит biodiesel → соєва олія → ZM")
    ])
    scheduler.add_job(send, "cron", day_of_week="wed", hour=16, minute=30, args=[
        msg_release("🛢", "EIA Petroleum Status Report", "16:30",
                    desc="Тижневі запаси нафти та нафтопродуктів США\n"
                         "Впливає на попит biodiesel → соєва олія → ZM",
                    tickers="🛢 Нафта · 🌱 Biodiesel · ZM",
                    link="eia.gov")
    ])

    # ── Четвер: USDA Export Sales ──
    scheduler.add_job(send, "cron", day_of_week="thu", hour=8, minute=0, args=[
        msg_reminder("📊", "USDA Export Sales", "14:30",
                     tickers="🌽 Corn · 🫘 Soybean · Meal · 🌾 Wheat · Cotton · Rice")
    ])
    scheduler.add_job(send, "cron", day_of_week="thu", hour=14, minute=30, args=[
        msg_release("📊", "USDA Export Sales", "14:30",
                    desc="Тижневий попит імпортерів на агро-товари США",
                    tickers="🌽 Corn · 🫘 Soybean · Meal · 🌾 Wheat · Cotton · Rice",
                    link="fas.usda.gov")
    ])

    # ── П'ятниця: COT Report ──
    scheduler.add_job(send, "cron", day_of_week="fri", hour=8, minute=0, args=[
        msg_reminder("📈", "COT Report (CFTC)", "21:30",
                     tickers="ZM · ZS · ZC · ZW · KC · CC · CT · SB")
    ])
    scheduler.add_job(send, "cron", day_of_week="fri", hour=21, minute=30, args=[
        msg_release("📈", "COT Report (CFTC)", "21:30",
                    desc="Позиції Large Specs, Commercials, Small Specs\n"
                         "Дані фіксуються у вівторок, публікуються в п'ятницю",
                    tickers="ZM · ZS · ZC · ZW · KC · CC · CT · SB",
                    link="cftc.gov")
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
                                 tickers=ev.get("tickers", ""),
                                 note=ev.get("note", ""))
                ])
                added += 1
            else:
                skipped += 1

        dt_r = ev.get("release_time")
        if dt_r and dt_r > now:
            scheduler.add_job(send, "date", run_date=dt_r, args=[
                msg_release(ev["icon"], ev["name"], ev["preview_time"],
                            desc=ev.get("desc", ""),
                            tickers=ev.get("tickers", ""),
                            link=ev.get("link", ""))
            ])
            added += 1

    print(f"  Разові події: додано {added}, пропущено як минулі {skipped}")


# ─────────────────────────────────────────
#  Запуск
# ─────────────────────────────────────────

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не задано! Впиши токен або встанови змінну середовища.")
        return

    print("🚀 Запуск Agro Calendar Bot...")
    schedule_all()
    scheduler.start()
    print("✅ Бот запущено! Всі нагадування активні.")
    print("   Часовий пояс: Europe/Warsaw")
    print("   Зупинити: Ctrl+C")

    await send(
        "🤖 <b>Agro Calendar Bot</b> — запущено ✅\n"
        "──────────────────────\n"
        "<b>Щотижнево</b>\n"
        "📅 Сб 8:00 — огляд наступного тижня\n"
        "🌱 Пн 8:00 + 22:00 — Crop Progress (квіт–листоп)\n"
        "🛢 Ср 8:00 + 16:30 — EIA Petroleum Status Report\n"
        "📊 Чт 8:00 + 14:30 — USDA Export Sales\n"
        "📈 Пт 8:00 + 21:30 — COT Report (CFTC)\n\n"
        "<b>USDA WASDE 2026</b> (8:00 + 18:00)\n"
        "🔥 12 трав · 11 черв · 10 лип · 12 серп\n"
        "   11 вер · 9 жовт · 10 лист · 10 груд\n\n"
        "<b>Інші разові події</b>\n"
        "🌏 14 трав 8:00 — Саміт Трамп–Сі (день 1)\n"
        "🌏 15 трав 8:00 — Саміт Трамп–Сі (день 2)\n"
        "🌾 30 черв 17:00 — Grain Stocks + Acreage\n"
        "🌾 30 вер 17:00 — Grain Stocks"
    )

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())