# -*- coding: utf-8 -*-
import os
import logging
import datetime as dt
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from elering_client import fetch_current_price, fetch_mean_price_30d
from telegram_client import send_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lv_price_bot")

TZ = pytz.timezone("Europe/Riga")

def build_and_send(token: str, chat_id: str, country: str):
    now = dt.datetime.now(TZ)
    try:
        current = fetch_current_price(country)
        mean30, n_obs = fetch_mean_price_30d(country, now=now)
        change = (current.price_eur_mwh / mean30 - 1.0) * 100.0 if mean30 > 0 else float("nan")
        marker = "🔴 " if change >= 50.0 else ""
        fmt = lambda x: f"{x:,.2f}".replace(",", " ").replace(".", ",")
        text = (
            f"{marker}<b>Цена электроэнергии (LV)</b>\n"
            f"Время: <b>{now.strftime('%Y-%m-%d %H:%M')}</b> (Europe/Riga)\n"
            f"Текущая цена: <b>{fmt(current.price_eur_mwh)}</b> €/MWh\n"
            f"Средняя за 30 дней: <b>{fmt(mean30)}</b> €/MWh\n"
            f"Отклонение: <b>{fmt(change)}%</b>\n"
            f"{'⛔ Превышение ≥ 50% от среднего' if change >= 50.0 else '✅ В пределах нормы (< 50% выше среднего)'}\n"
            f"\nИсточник: Elering API (Nord Pool day-ahead)\n"
        )
        send_message(token, chat_id, text)
        log.info("Report sent")
    except Exception as e:
        log.exception("Failed to send report: %s", e)

def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    country = os.getenv("COUNTRY", "LV").upper()
    if not token or not chat_id:
        raise RuntimeError("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env")
    # Plan: send at every top of the hour Riga time
    scheduler = BlockingScheduler(timezone=TZ)
    scheduler.add_job(lambda: build_and_send(token, chat_id, country),
                      CronTrigger(minute=0))
    # Send immediately on start
    build_and_send(token, chat_id, country)
    log.info("Scheduler started: every hour at minute=0 (Europe/Riga)")
    scheduler.start()

if __name__ == "__main__":
    main()
