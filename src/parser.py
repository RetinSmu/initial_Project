#for parsing input for hard mode 

import re
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class Activity:
    name: str
    time_range: Optional[str] = None
    address: Optional[str] = None


@dataclass
class CityPlan:
    city: str
    day: date
    activities: List[Activity]


_CITY_RE = re.compile(r"^City\s*\d*\s*:\s*(.+?)\s+(\d{4}-\d{2}-\d{2})\s*$", re.IGNORECASE)


def parse_trip(text: str) -> List[CityPlan]:
    """
    Input example:
    City1: Toronto 2025-01-31
    CN Tower;8am-9am
    Royal Ontario Museum;10am-11am

    Also supports address line:
    Royal Ontario Museum;100 Queen's Park, Toronto, ON;10am-11am
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    plans: List[CityPlan] = []

    current_city: Optional[str] = None
    current_day: Optional[date] = None
    current_acts: List[Activity] = []

    def flush():
        nonlocal current_city, current_day, current_acts
        if current_city and current_day:
            plans.append(CityPlan(city=current_city, day=current_day, activities=current_acts))
        current_city, current_day, current_acts = None, None, []

    for ln in lines:
        m = _CITY_RE.match(ln)
        if m:
            flush()
            current_city = m.group(1).strip()
            y, mo, d = [int(x) for x in m.group(2).split("-")]
            current_day = date(y, mo, d)
            continue

        parts = [p.strip() for p in ln.split(";") if p.strip()]
        if not parts:
            continue

        if len(parts) == 1:
            current_acts.append(Activity(name=parts[0]))
        elif len(parts) == 2:
            current_acts.append(Activity(name=parts[0], time_range=parts[1]))
        else:
            current_acts.append(Activity(name=parts[0], address=parts[1], time_range=parts[2]))

    flush()
    return plans
