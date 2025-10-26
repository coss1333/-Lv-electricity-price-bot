# -*- coding: utf-8 -*-
import os
import requests

def send_message(token: str, chat_id: str, text: str, parse_mode: str = "HTML", disable_web_page_preview: bool = True):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    r = requests.post(url, data=data, timeout=20)
    r.raise_for_status()
    return r.json()
