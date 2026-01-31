import json
import uuid

from src.agent_app import build_agent
from src.tools.google_weather import window_summaries
from src.tools.google_air_quality import aq_forecast, masks_needed


def _read_multiline() -> str:
    print("Paste itinerary. End with empty line:")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def _extract_text(result) -> str:
    if isinstance(result, dict) and "messages" in result and result["messages"]:
        last = result["messages"][-1]
        content = getattr(last, "content", None)
        if isinstance(content, str):
            return content
    if isinstance(result, str):
        return result
    return str(result)


def _safe_weather(lat: float, lon: float) -> dict:
    try:
        return window_summaries(lat, lon, days=7)
    except Exception as e:
        return {"window_note": f"Weather lookup failed: {e}", "days": []}


def _safe_air(lat: float, lon: float) -> dict:
    try:
        aq = aq_forecast(lat, lon)
        masks = masks_needed(aq, hours=24, threshold=100)
        return {
            "window_note": "Air quality forecast is short-term. Using next 24 hours from now.",
            "masks_24h": masks,
        }
    except Exception as e:
        return {"window_note": f"Air quality lookup failed: {e}", "masks_24h": 0}


def _format_report(data: dict) -> str:
    cities = data.get("cities") or []
    if not isinstance(cities, list):
        cities = []

    total_masks = 0
    out = []
    out.append("\n=== REPORT ===\n")

    for idx in range(len(cities)):
        c = cities[idx] if isinstance(cities[idx], dict) else {}

        city_name = c.get("city") or f"(unknown city {idx+1})"
        city_date = c.get("date") or "(unknown date)"

        out.append(f"City {idx+1}: {city_name} ({city_date})")

        acts = c.get("activities") or []
        if not isinstance(acts, list):
            acts = []

        out.append("Activities:")
        for i in range(len(acts)):
            a = acts[i] if isinstance(acts[i], dict) else {}
            out.append(f"  {i+1}. {a.get('name') or '(unknown place)'}")
            out.append(f"     Time: {a.get('time') or '(unknown time)'}")
            out.append(f"     Address: {a.get('address') or '(unknown address)'}")

        # City coords: use first activity lat/lon if exists
        lat = None
        lon = None
        if acts and isinstance(acts[0], dict):
            lat = acts[0].get("lat")
            lon = acts[0].get("lon")

        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            weather = _safe_weather(float(lat), float(lon))
            air = _safe_air(float(lat), float(lon))
        else:
            weather = {"window_note": "No lat/lon available for weather.", "days": []}
            air = {"window_note": "No lat/lon available for air quality.", "masks_24h": 0}

        out.append("")
        out.append("Weather:")
        out.append(f"  Note: {weather.get('window_note', 'N/A')}")

        # FIX 1 + FIX 2: Safe precip formatting (no "None%")
        days_list = weather.get("days") or []
        if isinstance(days_list, list):
            for d in days_list[:3]:
                if not isinstance(d, dict):
                    continue

                prec = d.get("precip_percent")
                prec_text = f"{prec}%" if isinstance(prec, (int, float)) else "N/A"

                out.append(
                    f"  - {d.get('date')}: {d.get('condition')} "
                    f"(min {d.get('min_c')}°C, max {d.get('max_c')}°C, precip {prec_text})"
                )

        out.append("")
        out.append("Air Quality:")
        out.append(f"  Note: {air.get('window_note', 'N/A')}")
        out.append(f"  Masks needed (next 24h): {air.get('masks_24h', 0)}")

        total_masks += int(air.get("masks_24h", 0) or 0)

        out.append("\n" + "-" * 40 + "\n")

    out.append(f"TOTAL masks: {total_masks}")
    out.append("")
    return "\n".join(out)


def main():
    raw_text = _read_multiline()
    agent = build_agent()

    thread_id = str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": thread_id}}

    result = agent.invoke({"messages": [("user", raw_text)]}, config=cfg)
    text = _extract_text(result)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        repair = agent.invoke(
            {"messages": [("user", "Return VALID JSON ONLY.\n\n" + text)]},
            config=cfg,
        )
        data = json.loads(_extract_text(repair))

    print(_format_report(data))


if __name__ == "__main__":
    main()
