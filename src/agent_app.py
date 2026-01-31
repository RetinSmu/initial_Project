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
    plans = parse_trip(raw_text)
    return {
        "cities": [
            {
                "city": p.city,
                "date": p.day.isoformat(),
                "activities": [
                    {"name": a.name, "time": a.time_range, "address": a.address}
                    for a in p.activities
                ],
            }
            for p in plans
        ]
    }


@tool
def resolve_place(place_name: str, city: str) -> dict:
    """Resolve a place name into best address + lat/lon."""
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
- Call parse_trip_input.
- For each activity:
  - If address missing OR lat/lon missing, call resolve_place.
  - Fill address, lat, lon for every activity.
- Output valid JSON only. No markdown. No extra text.
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
