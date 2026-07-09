from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("HERMES_DB", ROOT / "hermes.db"))
PROFILE_PATH = Path(os.environ.get("HERMES_PROFILE", ROOT / "profile.yaml"))


def load_profile() -> dict:
    with open(PROFILE_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def profile_summary(profile: dict) -> str:
    """Compact, stable text rendering of the profile for the ranking prompt.

    Deterministic output matters: this is the cached prefix of every ranking call.
    """
    ident = profile.get("identity", {})
    loc = ident.get("location", {})
    lines = [
        f"Role: {ident.get('role', 'software developer')}",
        f"Location: {loc.get('city', '')}, {loc.get('state', '')}, {loc.get('country', 'India')}",
        "Interests: " + "; ".join(profile.get("interests", [])),
        "Not interested in: " + "; ".join(profile.get("anti_interests", [])),
        "Tools/brands used: " + "; ".join(profile.get("stack", [])),
        f"Student: {profile.get('student', {}).get('is_student', False)}"
        f" (GitHub Student Pack: {profile.get('student', {}).get('has_github_student_pack', False)})",
    ]
    return "\n".join(lines)
