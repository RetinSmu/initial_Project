#for parsing input for hard mode 
#used by agent and main (enforces JSON format)
# src/parser.py
# src/parser.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


_CITY_RE = re.compile(
    r"^\s*City\s*(\d+)\s*:?\s*(.+?)\s+(\d{4}-\d{2}-\d{2})\s*$",
    re.IGNORECASE,
)


def parse_trip(text: str) -> Dict[str, Any]:
    """
    Backward-compatible name.
    Your agent_app.py expects parse_trip().
    """
    return parse_itinerary(text)


def parse_itinerary(text: str) -> Dict[str, Any]:
    """
    Supported city headers:
      City1: Toronto 2026-01-31
      City1 Toronto 2026-01-31
      City3 Los Angeles 2026-02-02

    Supported activity lines:
      Place;Time
      Place;Address;Time
    """
    cities: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # City header
        m = _CITY_RE.match(line)
        if m:
            city_name = m.group(2).strip()
            date_str = m.group(3).strip()
            current = {"city": city_name, "date": date_str, "activities": []}
            cities.append(current)
            continue

        # If user forgot a city header
        if current is None:
            current = {"city": "(unknown city)", "date": "(unknown date)", "activities": []}
            cities.append(current)

        activity = _parse_activity_line(line)
        if activity:
            current["activities"].append(activity)
        else:
            current["activities"].append({"name": line, "time": "", "address": ""})

    return {"cities": cities}


def _parse_activity_line(line: str) -> Optional[Dict[str, str]]:
    if ";" not in line:
        return None

    parts = [p.strip() for p in line.split(";")]
    parts = [p for p in parts if p != ""]
    if len(parts) < 2:
        return None

    # Place;Time
    if len(parts) == 2:
        return {"name": parts[0], "address": "", "time": parts[1]}

    # Place;Address;Time  (or more parts => join middle as address)
    name = parts[0]
    time = parts[-1]
    address = "; ".join(parts[1:-1])
    return {"name": name, "address": address, "time": time}
