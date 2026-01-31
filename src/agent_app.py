# src/agent_app.py
import os
from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI

from src.parser import parse_trip
from src.tools.google_places import best_place

load_dotenv()


@tool
def parse_trip_input(raw_text: str) -> dict:
    """Parse itinerary into a structured plan."""
    data = parse_trip(raw_text)

    # Normalize shape + ensure expected keys exist
    cities = data.get("cities", [])
    out_cities = []

    for c in cities:
        city_name = c.get("city", "")
        date = c.get("date", "")
        activities = c.get("activities", [])

        out_acts = []
        for a in activities:
            out_acts.append(
                {
                    "name": a.get("name", ""),
                    "time": a.get("time", ""),
                    "address": a.get("address", ""),
                    # lat/lon will be filled by resolve_place step
                    "lat": a.get("lat"),
                    "lon": a.get("lon"),
                }
            )

        out_cities.append(
            {
                "city": city_name,
                "date": date,
                "activities": out_acts,
            }
        )

    return {"cities": out_cities}


@tool
def resolve_place(place_name: str, city: str) -> dict:
    """Resolve a place name into best address + lat/lon."""
    # best_place should return something like:
    # {"name": "...", "address": "...", "lat": 43.0, "lon": -79.0}
    return best_place(f"{place_name}, {city}")


SYSTEM_PROMPT = """
You are a tool-using agent.

Return JSON ONLY with this schema:

{
  "cities":[
    {
      "city":"...",
      "date":"YYYY-MM-DD",
      "activities":[
        {"name":"...","time":"...","address":"...","lat":<float>,"lon":<float>}
      ]
    }
  ]
}

Rules:
1) Call parse_trip_input first.
2) For each activity, if address is empty OR lat/lon is missing:
   - Call resolve_place(place_name, city)
   - The tool returns fields: address, lat, lon (and maybe name).
   - Copy address/lat/lon into the activity.
   - Keep the activity time unchanged.
3) Every activity must end with non-empty address and numeric lat/lon.
4) Output valid JSON only. No markdown. No extra text.
"""



def build_agent():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY in .env")

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name, temperature=0)

    return create_agent(
        llm,
        tools=[parse_trip_input, resolve_place],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )
