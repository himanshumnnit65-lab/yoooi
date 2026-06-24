"""
Pinecone Vector Service for TBuddy RAG

Provides semantic search over curated travel tips using Pinecone cloud
and the all-MiniLM-L6-v2 sentence-transformer for local embeddings.
"""

from typing import List, Dict, Any, Optional
import asyncio
import logging
import re

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons ──────────────────────────────────────────
_embedding_model = None
_pinecone_index = None


def _get_embedding_model():
    """Lazy-load SentenceTransformer (downloads ~90 MB on first call)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("✅ SentenceTransformer 'all-MiniLM-L6-v2' loaded")
    return _embedding_model


from pathlib import Path
import math

class MockPineconeIndex:
    """Mock local vector store using cosine similarity over local JSON storage."""
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.data = {}
        self._load()

    def _load(self):
        if self.filepath.exists():
            try:
                import json
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info(f"💾 Loaded {len(self.data)} travel tips from local Mock Pinecone DB")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load local Mock Pinecone DB: {e}")
                self.data = {}

    def _save(self):
        try:
            import json
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save local Mock Pinecone DB: {e}")

    def upsert(self, vectors: list):
        for id_, vec, meta in vectors:
            self.data[id_] = {
                "vector": vec,
                "metadata": meta
            }
        self._save()

    def query(self, vector: list[float], top_k: int, filter: dict = None, **kwargs):
        def dot_product(v1, v2):
            return sum(x*y for x, y in zip(v1, v2))
        
        def magnitude(v):
            return math.sqrt(sum(x*x for x in v))

        results = []
        for id_, item in self.data.items():
            meta = item.get("metadata", {})
            if filter:
                matched = True
                for field, condition in filter.items():
                    val = meta.get(field)
                    target = condition["$eq"] if isinstance(condition, dict) and "$eq" in condition else condition
                    if val != target:
                        matched = False
                        break
                if not matched:
                    continue

            v_stored = item.get("vector", [])
            if not v_stored or len(v_stored) != len(vector):
                continue
            
            mag_stored = magnitude(v_stored)
            mag_query = magnitude(vector)
            if mag_stored == 0 or mag_query == 0:
                similarity = 0.0
            else:
                similarity = dot_product(vector, v_stored) / (mag_stored * mag_query)
            
            results.append({
                "id": id_,
                "score": similarity,
                "metadata": meta
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return {"matches": results[:top_k]}


def _get_pinecone_index():
    """Lazy-load Pinecone index connection (or local Mock database fallback)."""
    global _pinecone_index
    if _pinecone_index is None:
        api_key = settings.pinecone_api_key
        if not api_key:
            db_path = Path(__file__).resolve().parent.parent / "scripts" / "data" / "mock_pinecone_db.json"
            logger.warning(
                f"ℹ️ PINECONE_API_KEY not configured. "
                f"Falling back to local Mock Pinecone store: {db_path}"
            )
            _pinecone_index = MockPineconeIndex(db_path)
        else:
            from pinecone import Pinecone
            pc = Pinecone(api_key=api_key)
            _pinecone_index = pc.Index(settings.pinecone_index_name)
            logger.info(
                f"✅ Connected to Pinecone index '{settings.pinecone_index_name}'"
            )
    return _pinecone_index


# ── Destination normalization ───────────────────────────────────────

def _normalize_destination(dest: str) -> str:
    """
    Normalize destination for consistent Pinecone matching.

    Strips filler words like 'city', 'new' prefix, and lowercases.
    Examples:
        'New Delhi' -> 'delhi'
        'Jaipur City' -> 'jaipur'
        '  GOA  ' -> 'goa'
    """
    dest = dest.lower().strip()
    dest = re.sub(r"\bcity\b", "", dest).strip()
    dest = re.sub(r"^new\s+", "", dest).strip()
    return dest


# ── Public helpers ──────────────────────────────────────────────────

def embed_text(text: str) -> List[float]:
    """Convert text to a 384-dim float vector using the local model."""
    model = _get_embedding_model()
    vector = model.encode(text).tolist()
    return vector


async def embed_text_async(text: str) -> List[float]:
    """Non-blocking embedding for use in async route handlers."""
    return await asyncio.to_thread(embed_text, text)


def search_travel_tips(
    query: str,
    destination: str,
    category: Optional[str] = None,
    top_k: int = 3,
) -> List[str]:
    """
    Semantic search for travel tips matching *query* filtered by destination.

    Uses a two-pass strategy:
    1. First search with exact (normalized) destination filter.
    2. If zero results, retry with country-level filter only.

    Returns a list of plain-text tip strings (up to *top_k*).
    Returns an empty list gracefully on any failure.
    """
    try:
        index = _get_pinecone_index()
        query_vector = embed_text(query)
        normalized_dest = _normalize_destination(destination)

        # ── Pass 1: exact destination match ──────────────────────────
        metadata_filter: Dict[str, Any] = {
            "destination": {"$eq": normalized_dest}
        }
        if category:
            metadata_filter["category"] = {"$eq": category.lower()}

        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter,
        )

        tips = _extract_tips(results)

        # ── Pass 2: broaden to country if nothing found ──────────────
        if not tips:
            logger.info(
                f"🔍 No exact match for '{normalized_dest}', "
                f"retrying with country filter"
            )
            country_filter: Dict[str, Any] = {
                "country": {"$eq": "india"}
            }
            if category:
                country_filter["category"] = {"$eq": category.lower()}

            results = index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                filter=country_filter,
            )
            tips = _extract_tips(results)

        logger.info(
            f"🔍 RAG search for '{query}' in '{destination}': "
            f"{len(tips)} tips found"
        )
        return tips

    except Exception as e:
        logger.warning(f"⚠️ RAG search failed (non-fatal): {e}")
        return []


async def search_travel_tips_async(
    query: str,
    destination: str,
    category: Optional[str] = None,
    top_k: int = 3,
) -> List[str]:
    """Non-blocking wrapper around search_travel_tips for async handlers."""
    return await asyncio.to_thread(
        search_travel_tips, query, destination, category, top_k
    )


def _extract_tips(results) -> List[str]:
    """Pull content strings from a Pinecone query response."""
    tips = []
    for match in results.get("matches", []):
        content = match.get("metadata", {}).get("content", "")
        if content:
            tips.append(content)
    return tips


def upsert_travel_tip(
    id: str,
    content: str,
    metadata: Dict[str, Any],
) -> bool:
    """
    Embed *content* and upsert into Pinecone with the given metadata.

    Metadata should contain at least: destination, country, category.
    """
    try:
        index = _get_pinecone_index()
        vector = embed_text(content)

        # Ensure content is also in metadata for retrieval
        metadata["content"] = content

        index.upsert(vectors=[(id, vector, metadata)])
        logger.info(f"✅ Upserted travel tip '{id}' to Pinecone")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to upsert travel tip '{id}': {e}")
        return False


def is_available() -> bool:
    """Check if RAG/Pinecone is configured and reachable (always True for local fallback)."""
    return True
