# -*- coding: utf-8 -*-
import datetime as dt
import io
import os
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd
import pytz
import requests

ELERING_BASE = "https://dashboard.elering.ee/api/nps/price"

TZ = pytz.timezone("Europe/Riga")

@dataclass
class PricePoint:
    timestamp: dt.datetime  # timezone-aware
    price_eur_mwh: float

def _to_iso(ts: dt.datetime) -> str:
    # Ensure UTC for API
    if ts.tzinfo is None:
        ts = TZ.localize(ts)
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def fetch_current_price(country: str = "LV", timeout: int = 20) -> PricePoint:
    """
    Uses /api/nps/price/<country>/current to get current hour (or current interval) price.
    """
    url = f"{ELERING_BASE}/{country.upper()}/current"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    # Expected shape: {"data": {"price": 123.45, "timestamp": 1714074000000, ...}} or flat
    # Handle both potential shapes defensively
    if isinstance(data, dict) and "data" in data:
        payload = data["data"]
    else:
        payload = data
    # timestamp might be epoch ms or ISO
    ts = payload.get("timestamp")
    if isinstance(ts, (int, float)):
        ts_dt = dt.datetime.fromtimestamp(float(ts)/1000.0, tz=dt.timezone.utc).astimezone(TZ)
    else:
        ts_dt = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(TZ)
    price = float(payload.get("price"))
    return PricePoint(timestamp=ts_dt, price_eur_mwh=price)

def fetch_mean_price_30d(country: str = "LV", now: Optional[dt.datetime] = None, timeout: int = 30) -> Tuple[float, int]:
    """
    Uses /api/nps/price/csv to download last 30 days price series and compute mean.
    Returns (mean_price_eur_mwh, observations_count)
    """
    if now is None:
        now = dt.datetime.now(TZ)
    start = now - dt.timedelta(days=30)
    # Build CSV URL
    params = {
        "start": _to_iso(start),
        "end": _to_iso(now),
        "country": country.upper(),
    }
    url = f"{ELERING_BASE}/csv"
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    csv_bytes = r.content
    # Load CSV into pandas
    df = pd.read_csv(io.BytesIO(csv_bytes))
    # Expect columns like: timestamp (UTC/ISO) and price
    # Try to auto-detect column names
    # Common patterns seen: "timestamp", "price", or localized headers
    cols = {c.lower(): c for c in df.columns}
    # Try multiple options
    ts_col = None
    price_col = None
    for cand in ["timestamp", "time", "date", "datetime"]:
        if cand in cols:
            ts_col = cols[cand]
            break
    for cand in ["price", "value", "eur_mwh"]:
        if cand in cols:
            price_col = cols[cand]
            break
    if ts_col is None or price_col is None:
        # Fallback heuristic: first column is time, last column is price
        ts_col = df.columns[0]
        price_col = df.columns[-1]
    # Parse timestamps
    df[ts_col] = pd.to_datetime(df[ts_col], utc=True).dt.tz_convert(TZ)
    # If 15-minute resolution is in use, aggregate to hourly average for fairness
    # We will compute the mean over the whole period regardless of frequency.
    prices = pd.to_numeric(df[price_col], errors="coerce").dropna()
    mean_val = float(prices.mean())
    return mean_val, int(prices.shape[0])
