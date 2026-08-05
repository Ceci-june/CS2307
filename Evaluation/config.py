"""Paths and settings shared by the Evaluation scripts."""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
GEN_DATA_DIR = REPO_ROOT / "gen_user_data" / "data"

EVENTS_FILE = GEN_DATA_DIR / "recommendation_events_v2_claude.json"
INTERACTIONS_FILE = GEN_DATA_DIR / "interactions_v2_claude.json"
USERS_FILE = GEN_DATA_DIR / "users_v2.json"
LISTINGS_FILE = GEN_DATA_DIR / "listings.json"

BACKEND_URL = os.environ.get("EVAL_BACKEND_URL", "http://localhost:8001")
SEARCH_ENDPOINT = f"{BACKEND_URL}/v1/search"

RESULTS_DIR = HERE / "results"

POSITIVE_ACTIONS = {"save", "share", "contact"}
