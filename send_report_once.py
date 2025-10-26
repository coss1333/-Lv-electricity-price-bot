# -*- coding: utf-8 -*-
import os
import math
import datetime as dt
import pytz
from dotenv import load_dotenv

from elering_client import fetch_current_price, fetch_mean_price_30d
from telegram_client import send_message

TZ = pytz.timezone("Europe/Riga")

def compose_message(country: str):
    now = dt.datetime.now(TZ)
    current = fetch_current_price(country)
    mean30, n_obs = fetch_mean_price_30d(country, now=now)
    # Compute change
    change = (current.price_eur_mwh / mean30 - 1.0) * 100.0 if mean30 > 0 else float("nan")
    alert = change >= 50.0
    # Emoji marker for "красным"
    marker = "🔴 " if alert else ""
    # Format numbers
    def fmt(x):
        return f"{x:,.2f}".replace(",", " ").replace(".", ",")
    text = (
        f"{marker}<b>Цена электроэнергии (LV)</b>\n"
        f"Время: <b>{now.strftime('%Y-%m-%d %H:%M')}</b> (Europe/Riga)\n"
        f"Текущая цена: <b>{fmt(current.price_eur_mwh)}</b> €/MWh\n"
        f"Средняя за 30 дней: <b>{fmt(mean30)}</b> €/MWh\n"
        f"Отклонение: <b>{fmt(change)}%</b>\n"
        f"{'⛔ Превышение ≥ 50% от среднего' if alert else '✅ В пределах нормы (< 50% выше среднего)'}\n"
        f"\nИсточник: Elering API (Nord Pool day-ahead)\n"
    )
    return text

def main():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    country = os.getenv("COUNTRY", "LV").upper()
    if not token or not chat_id:
        raise RuntimeError("Заполните TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env")
    text = compose_message(country)
    send_message(token, chat_id, text)

if __name__ == "__main__":
    main()
