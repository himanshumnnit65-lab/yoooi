"""
Ingest Travel Tips into Pinecone

One-time script to populate the Pinecone vector index with curated travel
guidelines.  Safe to re-run — uses deterministic IDs so duplicates are
silently overwritten rather than duplicated.

Usage:
    python -m app.scripts.ingest_travel_data
"""

import json
import hashlib
import logging
import sys
import os
from pathlib import Path

# Ensure the project root is on sys.path so `app.*` imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.vector_service import upsert_travel_tip, is_available

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────────────────────────────────

DATA_FILE = Path(__file__).parent / "data" / "travel_tips.json"
MAX_CHUNK_WORDS = 200  # split long tips into chunks of this size


def _deterministic_id(destination: str, category: str, content: str) -> str:
    """Create a stable, reproducible vector ID from the tip content."""
    raw = f"{destination}:{category}:{content[:100]}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _chunk_text(text: str, max_words: int = MAX_CHUNK_WORDS) -> list[str]:
    """Split *text* into segments of at most *max_words* words."""
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words])
        chunks.append(chunk)
    return chunks


def _normalize_destination(dest: str) -> str:
    """Lowercase + strip filler words so storage keys are consistent."""
    import re
    dest = dest.lower().strip()
    dest = re.sub(r"\bcity\b", "", dest).strip()
    dest = re.sub(r"^new\s+", "", dest).strip()
    return dest


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    if not is_available():
        logger.error(
            "❌ Pinecone is not configured or unreachable. "
            "Set PINECONE_API_KEY in your .env and try again."
        )
        sys.exit(1)

    if not DATA_FILE.exists():
        logger.error(f"❌ Data file not found: {DATA_FILE}")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        tips = json.load(f)

    logger.info(f"📂 Loaded {len(tips)} tips from {DATA_FILE.name}")

    upserted = 0
    skipped = 0

    for tip in tips:
        destination = _normalize_destination(tip["destination"])
        country = tip.get("country", "india").lower()
        category = tip.get("category", "general").lower()
        content = tip["content"]

        chunks = _chunk_text(content)

        for idx, chunk in enumerate(chunks):
            tip_id = _deterministic_id(destination, category, chunk)
            if idx > 0:
                # Append chunk index to ID so multi-chunk tips don't collide
                tip_id = f"{tip_id}_{idx}"

            metadata = {
                "destination": destination,
                "country": country,
                "category": category,
            }

            ok = upsert_travel_tip(id=tip_id, content=chunk, metadata=metadata)
            if ok:
                upserted += 1
            else:
                skipped += 1

    logger.info(
        f"✅ Ingestion complete: {upserted} upserted, {skipped} failed"
    )


if __name__ == "__main__":
    main()
