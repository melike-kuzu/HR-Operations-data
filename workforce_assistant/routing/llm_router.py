from __future__ import annotations

import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()
from typing import Any

from openai import AzureOpenAI

from workforce_assistant.domain.models import (
    RouteDecision,
    RouteType,
)


logger = logging.getLogger(__name__)


ROUTER_SYSTEM_PROMPT = """
You are the routing component of an HR workforce assistant.

Your task is to identify which internal data source should answer
the user's question and extract any relevant filters.

Available routes:

- bench:
  Questions asking who is currently on bench or unassigned.

- consultant_tracker:
  Questions about consultant availability, future availability,
  allocation, booking status, leave, capacity, or when someone
  becomes free.

- project_tracker:
  Questions about projects, clients, project assignments,
  project status, project dates, or project ownership.

- utilisation:
  Questions asking for aggregate utilisation information.

- utilisation_detailed:
  Questions asking for detailed consultant-level utilisation.

- partial_assignments:
  Questions about consultants who are partially allocated,
  partly booked, or assigned below full capacity.

- skill_lookup:
  Questions asking which consultants know a technology,
  tool, platform, methodology, industry, or skill.

- profile_search:
  Questions asking about consultant profiles, CVs,
  experience, employment history, project history,
  background, certifications, or combined searches involving
  skills plus structured workforce filters.

- document_search:
  Questions asking about policies, procedures, handbooks,
  documents, PDFs, or internal guidance.

- general_chat:
  Greetings or general conversational questions that do not
  require workforce data.

- unknown:
  Only when the request genuinely cannot be understood.

Extract filters when relevant:

- skill_query: string or null
- availability:
    - "today"
    - "next_week"
    - "next_month"
    - "specific_date"
    - "soon"
    - "bench"
    - null
- availability_date: ISO date string or null
- consultant_name: string or null
- group: string or null
- client: string or null
- industry: string or null
- location: string or null
- active_projects:
    {
      "operator": "eq" | "lt" | "lte" | "gt" | "gte",
      "value": integer
    }
  or null

Important routing rules:

1. A pure skill question should use skill_lookup.
2. A pure availability question should use consultant_tracker.
3. A question combining skills with availability, group,
   active projects, client, industry, or location should use
   profile_search.
4. Interpret the meaning of the question, not exact keywords.
5. Support different wording, spelling mistakes, English,
   and Turkish.
6. Never choose unknown merely because the wording does not
   match an example.
"""


ROUTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "route": {
            "type": "string",
            "enum": [
                route.value
                for route in RouteType
            ],
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
        "filters": {
            "type": "object",
            "properties": {
                "skill_query": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "availability": {
                    "type": [
                        "string",
                        "null",
                    ],
                    "enum": [
                        "today",
                        "next_week",
                        "next_month",
                        "specific_date",
                        "soon",
                        "bench",
                        None,
                    ],
                },
                "availability_date": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "consultant_name": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "group": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "client": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "industry": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "location": {
                    "type": [
                        "string",
                        "null",
                    ],
                },
                "active_projects": {
                    "anyOf": [
                        {
                            "type": "object",
                            "properties": {
                                "operator": {
                                    "type": "string",
                                    "enum": [
                                        "eq",
                                        "lt",
                                        "lte",
                                        "gt",
                                        "gte",
                                    ],
                                },
                                "value": {
                                    "type": "integer",
                                },
                            },
                            "required": [
                                "operator",
                                "value",
                            ],
                            "additionalProperties": False,
                        },
                        {
                            "type": "null",
                        },
                    ],
                },
            },
            "required": [
                "skill_query",
                "availability",
                "availability_date",
                "consultant_name",
                "group",
                "client",
                "industry",
                "location",
                "active_projects",
            ],
            "additionalProperties": False,
        },
    },
    "required": [
        "route",
        "confidence",
        "filters",
    ],
    "additionalProperties": False,
}


def _get_client() -> AzureOpenAI:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    api_version = os.getenv(
        "AZURE_OPENAI_API_VERSION",
        "2024-10-21",
    )

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )


def _remove_empty_filters(
    filters: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in filters.items()
        if value is not None
        and value != ""
        and value != {}
    }


def route_question_with_llm(
    question: str,
) -> RouteDecision:
    client = _get_client()

    deployment = os.environ[
        "AZURE_OPENAI_CHAT_DEPLOYMENT"
    ]

    completion = client.chat.completions.create(
        model=deployment,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": ROUTER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "workforce_route_decision",
                "strict": True,
                "schema": ROUTER_SCHEMA,
            },
        },
    )

    content = completion.choices[0].message.content

    if not content:
        raise RuntimeError(
            "The router model returned an empty response."
        )

    parsed = json.loads(content)

    route = RouteType(
        parsed["route"]
    )

    confidence = float(
        parsed["confidence"]
    )

    filters = _remove_empty_filters(
        parsed.get(
            "filters",
            {},
        )
    )

    logger.info(
        "LLM router decision completed",
        extra={
            "event_type": "llm_router_completed",
            "route": route.value,
            "confidence": confidence,
            "filters": filters,
        },
    )

    return RouteDecision(
        route_type=route,
        confidence=confidence,
        extracted_filters=filters,
    )