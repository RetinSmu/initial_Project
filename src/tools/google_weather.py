import os
import requests

WEATHER_DAILY_URL = "https://weather.googleapis.com/v1/forecast/days:lookup"


def window_summaries(lat: float, lon: float, days: int = 7) -> dict:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        raise RuntimeError("Missing GOOGLE_MAPS_API_KEY in .env")

    params = {
        "key": key,
        "location.latitude": lat,
        "location.longitude": lon,
        "days": int(days),
        "languageCode": "en",
        "unitsSystem": "METRIC",
    }

    r = requests.get(WEATHER_DAILY_URL, params=params, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Weather API error {r.status_code}: {r.text}")

    data = r.json()
    forecast_days = data.get("forecastDays") or []
    summaries = []

    for d in forecast_days[:days]:
        # ---- DATE ----
        # Prefer displayDate {year,month,day}
        dd = d.get("displayDate") or {}
        if isinstance(dd, dict) and all(k in dd for k in ("year", "month", "day")):
            dt = f"{dd['year']:04d}-{dd['month']:02d}-{dd['day']:02d}"
        else:
            # fallback to interval.startTime
            interval = d.get("interval") or {}
            start = interval.get("startTime")
            dt = start.split("T")[0] if isinstance(start, str) and "T" in start else "(unknown date)"

        # ---- TEMPS ----
        max_t = d.get("maxTemperature") or {}
        min_t = d.get("minTemperature") or {}
        max_c = max_t.get("degrees") if isinstance(max_t, dict) else None
        min_c = min_t.get("degrees") if isinstance(min_t, dict) else None

        # ---- CONDITION ----
        # Use daytimeForecast.weatherCondition.description.text
        condition = "N/A"
        day_fc = d.get("daytimeForecast") or {}
        if isinstance(day_fc, dict):
            wc = day_fc.get("weatherCondition") or {}
            if isinstance(wc, dict):
                desc = wc.get("description") or {}
                if isinstance(desc, dict) and isinstance(desc.get("text"), str):
                    condition = desc["text"]

        # ---- PRECIP % ----
        precip_percent = None
        if isinstance(day_fc, dict):
            precip = day_fc.get("precipitation") or {}
            if isinstance(precip, dict):
                prob = precip.get("probability") or {}
                if isinstance(prob, dict) and isinstance(prob.get("percent"), (int, float)):
                    precip_percent = prob["percent"]

        summaries.append(
            {
                "date": dt,
                "max_c": max_c,
                "min_c": min_c,
                "precip_percent": precip_percent,
                "condition": condition,
            }
        )

    return {
        "window_note": f"Weather forecast is short-term. Showing next {len(summaries)} days from today.",
        "days": summaries,
    }
