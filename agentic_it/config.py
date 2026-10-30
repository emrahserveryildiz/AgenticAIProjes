from __future__ import annotations

import os
import importlib.util
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "data" / "it_support_demo.sqlite3")))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = ROOT / DATABASE_PATH
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", str(ROOT / "data" / "knowledge")))
if not KNOWLEDGE_DIR.is_absolute():
    KNOWLEDGE_DIR = ROOT / KNOWLEDGE_DIR
DEMO_MODE = not bool(API_KEY) or importlib.util.find_spec("openai") is None

