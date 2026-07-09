"""AI opportunity ranking.

Uses Claude (claude-opus-4-8) with structured outputs when credentials are
available; otherwise a deterministic keyword heuristic keeps the pipeline
functional. The composite score is always computed in code so it stays
tunable and comparable across scorers.
"""

from __future__ import annotations

import json
import sqlite3

from .config import load_profile, profile_summary
from .db import category_weights, save_score, unranked
from .models import Score

MODEL = "claude-opus-4-8"
BATCH_SIZE = 15

ELIGIBILITY_FACTOR = {"eligible": 1.0, "likely": 0.8, "unlikely": 0.3, "no": 0.0}
URGENCY_BOOST = {"critical": 1.3, "high": 1.15, "medium": 1.0, "low": 0.9}
REGION_BOOST = {"mumbai": 1.2, "maharashtra": 1.15, "india": 1.1, "global": 1.0, "other": 0.7}

BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "relevance": {"type": "number"},
                    "legitimacy": {"type": "number"},
                    "confidence": {"type": "number"},
                    "est_value_inr": {"type": "number"},
                    "effort_hours": {"type": "number"},
                    "eligibility": {"type": "string", "enum": ["eligible", "likely", "unlikely", "no"]},
                    "region_scope": {"type": "string", "enum": ["global", "india", "maharashtra", "mumbai", "other"]},
                    "urgency": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "reasoning": {"type": "string"},
                },
                "required": ["index", "relevance", "legitimacy", "confidence",
                             "est_value_inr", "effort_hours", "eligibility",
                             "region_scope", "urgency", "reasoning"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

RUBRIC = """You evaluate internet opportunities (deals, hackathons, credits, scholarships,
beta programs, courses) for the user profiled above. For each numbered item, estimate:
- relevance (0-1): fit to the user's interests, stack, and anti-interests
- legitimacy (0-1): 1.0 = clearly real; low for scammy/vague/marketing-noise items
- confidence (0-1): your certainty in this assessment given the limited text
- est_value_inr: realistic expected value to THIS user in Indian Rupees
  (savings, credits, prize expectation adjusted for win probability, career value)
- effort_hours: hours the user must invest to capture that value
- eligibility: can this user (engineering student in Navi Mumbai, India) realistically claim it?
- region_scope: narrowest region where it is available
- urgency: critical = expires within days; low = evergreen
- reasoning: ONE short sentence.
Items that are just news/articles with nothing to claim get relevance <= 0.2."""


def composite(s: dict, weight: float) -> float:
    value_density = min(1.0, s["est_value_inr"] / (1500.0 * max(0.25, s["effort_hours"])))
    return round(
        s["relevance"]
        * s["legitimacy"]
        * (0.4 + 0.6 * value_density)
        * ELIGIBILITY_FACTOR[s["eligibility"]]
        * URGENCY_BOOST[s["urgency"]]
        * REGION_BOOST[s["region_scope"]]
        * weight,
        4,
    )


def _format_items(rows: list[sqlite3.Row]) -> str:
    lines = []
    for i, r in enumerate(rows):
        lines.append(
            f"[{i}] title: {r['title']}\n    source: {r['source']} | category hint: "
            f"{r['category']} | region hint: {r['region_hint']}\n"
            f"    description: {(r['description'] or '')[:300]}"
        )
    return "\n".join(lines)


def _claude_client():
    """Return an Anthropic client, or None when no credentials resolve."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        return client
    except Exception:
        return None


def _rank_batch_claude(client, profile_text: str, weights: dict, rows: list[sqlite3.Row]) -> list[Score] | None:
    import anthropic

    learned = ""
    if weights:
        learned = "\nLearned preferences (category: weight, >1 favored, <1 disfavored): " + \
            ", ".join(f"{k}: {v:.2f}" for k, v in sorted(weights.items()))
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=[{
                "type": "text",
                "text": f"USER PROFILE:\n{profile_text}\n\n{RUBRIC}",
                "cache_control": {"type": "ephemeral"},
            }],
            output_config={"format": {"type": "json_schema", "schema": BATCH_SCHEMA}},
            messages=[{
                "role": "user",
                "content": f"Evaluate these {len(rows)} opportunities:{learned}\n\n{_format_items(rows)}",
            }],
        )
    except (anthropic.AuthenticationError, TypeError):
        # TypeError: SDK raises it at request time when no credential source
        # (API key, auth token, or ant profile) resolves.
        return None
    except anthropic.APIError as e:
        print(f"  Claude API error, falling back to heuristic for this batch: {e}")
        return None

    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        return None
    items = {it["index"]: it for it in json.loads(text)["items"]}
    scores: list[Score] = []
    for i, row in enumerate(rows):
        it = items.get(i)
        if it is None:
            scores.append(_heuristic_score(row, weights))
            continue
        w = weights.get(row["category"], 1.0)
        scores.append(Score(
            scorer=MODEL,
            relevance=it["relevance"], legitimacy=it["legitimacy"],
            confidence=it["confidence"], est_value_inr=it["est_value_inr"],
            effort_hours=it["effort_hours"], eligibility=it["eligibility"],
            region_scope=it["region_scope"], urgency=it["urgency"],
            composite=composite(it, w), reasoning=it["reasoning"],
        ))
    return scores


HEURISTIC_KEYWORDS = {
    # keyword fragments -> relevance bump
    "free": 0.15, "credit": 0.25, "student": 0.3, "hackathon": 0.3, "scholarship": 0.3,
    "grant": 0.25, "beta": 0.15, "discount": 0.15, "voucher": 0.2, "fellowship": 0.25,
    "internship": 0.2, "api": 0.15, "cloud": 0.15, "github": 0.2, "ai": 0.15,
    "open source": 0.15, "india": 0.2, "deadline": 0.1, "apply": 0.1,
}


def _heuristic_score(row: sqlite3.Row, weights: dict) -> Score:
    text = f"{row['title']} {row['description'] or ''}".lower()
    relevance = min(1.0, 0.1 + sum(v for k, v in HEURISTIC_KEYWORDS.items() if k in text))
    region = row["region_hint"] if row["region_hint"] in REGION_BOOST else "global"
    est = {
        "relevance": relevance, "legitimacy": 0.6, "confidence": 0.3,
        "est_value_inr": 1000.0 * relevance, "effort_hours": 1.0,
        "eligibility": "likely", "region_scope": region, "urgency": "medium",
    }
    w = weights.get(row["category"], 1.0)
    return Score(
        scorer="heuristic",
        relevance=est["relevance"], legitimacy=est["legitimacy"],
        confidence=est["confidence"], est_value_inr=est["est_value_inr"],
        effort_hours=est["effort_hours"], eligibility=est["eligibility"],
        region_scope=est["region_scope"], urgency=est["urgency"],
        composite=composite(est, w), reasoning="keyword heuristic (no AI credentials)",
    )


def rank_all(con: sqlite3.Connection) -> tuple[int, str]:
    """Score every unranked opportunity. Returns (count, scorer_used)."""
    rows = unranked(con)
    if not rows:
        return 0, "none"

    profile_text = profile_summary(load_profile())
    weights = category_weights(con)
    client = _claude_client()
    scorer_used = "heuristic"

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        scores = None
        if client is not None:
            scores = _rank_batch_claude(client, profile_text, weights, batch)
            if scores is not None:
                scorer_used = MODEL
            else:
                client = None  # credentials/API dead — stop retrying per batch
        if scores is None:
            scores = [_heuristic_score(r, weights) for r in batch]
        for row, score in zip(batch, scores):
            save_score(con, row["id"], score)
        print(f"  ranked {min(start + BATCH_SIZE, len(rows))}/{len(rows)}")
    return len(rows), scorer_used
