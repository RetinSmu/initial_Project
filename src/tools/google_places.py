import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"


def best_place(query: str) -> Dict[str, Any]:
    """
    Returns address + lat/lon for a place query.
    query example: "CN Tower, Toronto"
    """
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        raise RuntimeError("Missing GOOGLE_MAPS_API_KEY in .env")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    payload = {"textQuery": query, "maxResultCount": 1}

    r = requests.post(PLACES_URL, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()

    places = data.get("places", []) or []
    if not places:
        return {"found": False, "query": query, "address": None, "lat": None, "lon": None}

    p = places[0]
    loc = p.get("location") or {}
    name = (p.get("displayName") or {}).get("text")

    return {
        "found": True,
        "query": query,
        "name": name,
        "address": p.get("formattedAddress"),
        "lat": loc.get("latitude"),
        "lon": loc.get("longitude"),
    }
