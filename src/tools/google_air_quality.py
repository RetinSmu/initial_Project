import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union

import requests

AQ_FORECAST_URL = "https://airquality.googleapis.com/v1/forecast:lookup"


def _to_rfc3339_z(dt: datetime) -> str:
    """Return RFC3339 UTC Z format like 2026-01-31T12:00:00Z."""
    dt_utc = dt.astimezone(timezone.utc).replace(microsecond=0)
    return dt_utc.isoformat().replace("+00:00", "Z")


def _next_hour_utc() -> datetime:
    """Round up to the next exact hour in UTC."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return now + timedelta(hours=1)


def aq_forecast(
    lat: float,
    lon: float,
    dt: Optional[Union[str, datetime]] = None,
    hours: int = 24,
    page_size: int = 24,
) -> Dict[str, Any]:
    """
    Calls Google Air Quality forecast endpoint.
    Uses either:
      - dateTime (single hour) if dt is provided
      - or a period starting next hour for `hours` hours (recommended)
    """
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        raise RuntimeError("Missing GOOGLE_MAPS_API_KEY in .env")

    if hours < 1:
        hours = 1
    if hours > 96:
        hours = 96

    body: Dict[str, Any] = {
        "location": {"latitude": float(lat), "longitude": float(lon)},
        "languageCode": "en",
        "universalAqi": True,
        "pageSize": int(page_size),
    }

    if dt is not None:
        if isinstance(dt, datetime):
            body["dateTime"] = _to_rfc3339_z(dt)
        elif isinstance(dt, str):
            body["dateTime"] = dt
        else:
            raise TypeError("dt must be a datetime, RFC3339 string, or None")
    else:
        start = _next_hour_utc()
        end = start + timedelta(hours=int(hours) - 1)  # inclusive end hour
        body["period"] = {"startTime": _to_rfc3339_z(start), "endTime": _to_rfc3339_z(end)}

    r = requests.post(
        f"{AQ_FORECAST_URL}?key={key}",
        json=body,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if not r.ok:
        raise RuntimeError(f"AQ API error {r.status_code}: {r.text}")

    return r.json()


def _extract_aqi_from_hour(hour_obj: Dict[str, Any], code: str = "uaqi") -> Optional[int]:
    """
    hour_obj has 'indexes': [{code, aqi, ...}, ...]
    We try to find matching index code (default uaqi).
    """
    indexes = hour_obj.get("indexes") or []
    if not isinstance(indexes, list):
        return None

    # Try preferred code first
    for idx in indexes:
        if isinstance(idx, dict) and idx.get("code") == code and isinstance(idx.get("aqi"), (int, float)):
            return int(idx["aqi"])

    # Fallback: first available aqi
    for idx in indexes:
        if isinstance(idx, dict) and isinstance(idx.get("aqi"), (int, float)):
            return int(idx["aqi"])

    return None


def masks_needed(
    forecast_json: Dict[str, Any],
    hours: int = 24,
    threshold: int = 100,
    aqi_code: str = "uaqi",
) -> int:
    """
    Simple rule:
    Count how many forecast hours have AQI >= threshold.
    Return that count as "masks needed".
    """
    hourly = forecast_json.get("hourlyForecasts") or []
    if not isinstance(hourly, list):
        return 0

    n = min(int(hours), len(hourly))
    masks = 0

    for i in range(n):
        hour_obj = hourly[i]
        if not isinstance(hour_obj, dict):
            continue
        aqi = _extract_aqi_from_hour(hour_obj, code=aqi_code)
        if aqi is not None and aqi >= threshold:
            masks += 1

    return masks
