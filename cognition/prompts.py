"""Prompt builders and structured-output schemas for every cognition call.

Every prompt carries a machine-readable CONTEXT_JSON block (sorted keys):
real models get clean structured context, and the deterministic fake model
(cognition/fake_model.py) parses the same block. Output shapes are enforced
through the gateway's validation wall.
"""
from __future__ import annotations

import json

CONTEXT_MARKER = "CONTEXT_JSON:"


def with_context(instruction: str, ctx: dict) -> list[dict]:
    body = f"{instruction}\n\n{CONTEXT_MARKER}\n{json.dumps(ctx, sort_keys=True)}"
    return [{"role": "user", "content": body}]


def parse_context(prompt: str) -> dict:
    _, _, tail = prompt.partition(CONTEXT_MARKER)
    return json.loads(tail.strip())


HHMM = {"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"}

IMPORTANCE_SCHEMA = {
    "title": "importance",
    "type": "object",
    "required": ["score"],
    "additionalProperties": False,
    "properties": {"score": {"type": "integer", "minimum": 1, "maximum": 10}},
}

AGENDA_SCHEMA = {
    "title": "daily_agenda",
    "type": "object",
    "required": ["agenda"],
    "additionalProperties": False,
    "properties": {
        "agenda": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["start", "end", "activity", "location"],
                "additionalProperties": False,
                "properties": {
                    "start": HHMM,
                    "end": HHMM,
                    "activity": {"type": "string", "minLength": 1},
                    "location": {"type": "string", "pattern": "^[a-z0-9_]+$"},
                },
            },
        }
    },
}

STEPS_SCHEMA = {
    "title": "action_steps",
    "type": "object",
    "required": ["steps"],
    "additionalProperties": False,
    "properties": {
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["minutes", "kind"],
                "additionalProperties": False,
                "properties": {
                    "minutes": {"type": "integer", "minimum": 1},
                    "kind": {"enum": ["move_to", "use_object", "idle", "sleep"]},
                    "destination": {"type": "string", "pattern": "^[a-z0-9_]+$"},
                    "object_id": {"type": "string", "pattern": "^[a-z0-9_]+$"},
                    "interaction": {"type": "string", "pattern": "^[a-z0-9_]+$"},
                },
            },
        }
    },
}

REACTION_SCHEMA = {
    "title": "reaction",
    "type": "object",
    "required": ["action"],
    "additionalProperties": False,
    "properties": {
        "action": {"enum": ["continue", "start_conversation"]},
        "partner": {"type": "string", "pattern": "^[a-z0-9_]+$"},
    },
}

QUESTIONS_SCHEMA = {
    "title": "reflection_questions",
    "type": "object",
    "required": ["questions"],
    "additionalProperties": False,
    "properties": {
        "questions": {"type": "array", "minItems": 1, "maxItems": 3,
                      "items": {"type": "string", "minLength": 1}},
    },
}

INSIGHTS_SCHEMA = {
    "title": "reflection_insights",
    "type": "object",
    "required": ["insights"],
    "additionalProperties": False,
    "properties": {
        "insights": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "required": ["text", "evidence"],
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string", "minLength": 1},
                    "evidence": {"description": "indices into the provided memories list",
                                 "type": "array", "minItems": 1,
                                 "items": {"type": "integer", "minimum": 0}},
                },
            },
        }
    },
}

SUMMARY_SCHEMA = {
    "title": "conversation_summary",
    "type": "object",
    "required": ["summary"],
    "additionalProperties": False,
    "properties": {"summary": {"type": "string", "minLength": 1}},
}


def importance_prompt(agent: dict, text: str) -> list[dict]:
    return with_context(
        "On a scale of 1 (mundane) to 10 (life-changing), rate the importance "
        "of this observation to this person. Respond with JSON {\"score\": n}.",
        {"role": "importance", "agent": agent["id"], "observation": text},
    )


def daily_plan_prompt(agent: dict, day: int, yesterday_summary: list[str]) -> list[dict]:
    return with_context(
        "Draft this person's agenda for the day as ordered blocks from wake "
        "to sleep, grounded in their anchors, occupation, home and workplace.",
        {
            "role": "daily_planning",
            "agent": agent["id"],
            "occupation": agent["occupation"],
            "traits": agent["traits"],
            "home": agent["home"],
            "workplace": agent["workplace"],
            "anchors": agent["daily_anchors"],
            "day": day,
            "yesterday": yesterday_summary,
        },
    )


def decompose_prompt(agent: dict, block: dict, location_objects: list[dict]) -> list[dict]:
    return with_context(
        "Decompose this agenda block into concrete action steps. Steps must "
        "only use the listed intent kinds; use_object steps must reference a "
        "listed object id and one of its allowed interactions.",
        {
            "role": "decomposition",
            "agent": agent["id"],
            "block": block,
            "home": agent["home"],
            "objects": location_objects,
        },
    )


def reaction_prompt(agent: dict, observation: str, candidates: list[str]) -> list[dict]:
    return with_context(
        "Given this salient observation, decide whether to continue the "
        "current plan or start a conversation with a nearby person.",
        {"role": "action_selection", "agent": agent["id"],
         "observation": observation, "nearby": candidates},
    )


def dialogue_turn_prompt(agent: dict, partner_id: str, turn: int,
                         retrieved: list[str], history: list[str]) -> list[dict]:
    return with_context(
        "Produce this person's next utterance in the conversation, grounded "
        "in what they remember about their interlocutor. If the conversation "
        "has run its course, end the utterance with [DONE].",
        {"role": "dialogue", "agent": agent["id"], "partner": partner_id,
         "turn": turn, "memories": retrieved, "history": history},
    )


def summary_prompt(agent: dict, partner_id: str, history: list[str]) -> list[dict]:
    return with_context(
        "Summarize this conversation from this person's point of view in one "
        "or two sentences, keeping any concrete facts exchanged.",
        {"role": "dialogue", "agent": agent["id"], "partner": partner_id,
         "history": history},
    )


def questions_prompt(agent: dict, recent_texts: list[str]) -> list[dict]:
    return with_context(
        "Given these recent memories, what are the most salient high-level "
        "questions this person could reflect on?",
        {"role": "reflection", "agent": agent["id"], "memories": recent_texts},
    )


def insights_prompt(agent: dict, question: str, evidence_texts: list[str]) -> list[dict]:
    return with_context(
        "Answer the question by synthesizing insights from the numbered "
        "memories. Each insight must cite the memory indices it rests on.",
        {"role": "reflection", "agent": agent["id"], "question": question,
         "memories": evidence_texts},
    )
