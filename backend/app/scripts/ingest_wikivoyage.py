"""
Ingest Travel Tips from Wikivoyage into Pinecone

Fetches structured guide content for a specific destination from Wikivoyage API,
parses and maps sections to standard travel tip categories, chunks the text,
and uploads them to Pinecone.

Usage:
    python -m app.scripts.ingest_wikivoyage --destination "Delhi" --country "India"
"""

import argparse
import hashlib
import logging
import re
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Ensure the project root is on sys.path so `app.*` imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.vector_service import upsert_travel_tip, is_available

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

MAX_CHUNK_WORDS = 200


def _deterministic_id(destination: str, category: str, content: str) -> str:
    """Create a stable, reproducible vector ID from the tip content."""
    raw = f"wikivoyage:{destination}:{category}:{content[:100]}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _normalize_destination(dest: str) -> str:
    """Lowercase + strip filler words so storage keys are consistent."""
    dest = dest.lower().strip()
    dest = re.sub(r"\bcity\b", "", dest).strip()
    dest = re.sub(r"^new\s+", "", dest).strip()
    return dest


def _clean_text(text: str) -> str:
    """Clean citation markers, wiki edit markers, and excessive whitespaces."""
    # Remove wiki edit links e.g. [edit]
    text = re.sub(r"\[edit\]", "", text, flags=re.IGNORECASE)
    # Remove citations e.g. [1], [2], [citation needed]
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\[citation needed\]", "", text, flags=re.IGNORECASE)
    # Clean up double/multiple spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Remove empty lines / normalize newlines
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def _determine_category(section_name: str) -> str:
    """Map a Wikivoyage section name to standard travel tips categories."""
    name = section_name.lower().strip()
    if any(k in name for k in ["eat", "drink", "culinary", "food", "dining", "restaurant", "bar", "pub", "cafe"]):
        return "food"
    elif any(k in name for k in ["get in", "get around", "transit", "transport", "by plane", "by train", "by bus", "by car", "by taxi"]):
        return "transit"
    elif any(k in name for k in ["stay safe", "stay healthy", "safety", "health", "security", "emergency", "crime", "scam"]):
        return "safety"
    elif any(k in name for k in ["see", "do", "get out", "temple", "respect", "customs", "culture", "activities", "history", "monument", "attraction"]):
        return "customs"
    elif any(k in name for k in ["pack", "wear", "climate", "weather", "clothing"]):
        return "packing"
    return "general"


def fetch_wikivoyage_html(destination: str) -> tuple[str, str]:
    """Fetch the parsed HTML content for a destination from Wikivoyage with retry logic."""
    import time
    url = "https://en.wikivoyage.org/w/api.php"
    params = {
        "action": "parse",
        "page": destination,
        "format": "json",
        "redirects": "true",
        "prop": "text",
        "utf8": "true",
    }
    # Standard Chrome browser user agent to avoid triggering Wikimedia's bot blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"🌐 Querying Wikivoyage API for '{destination}' (attempt {attempt + 1}/{max_retries})...")
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 2))
                logger.warning(f"⚠️ Received 429 Too Many Requests. Waiting for {retry_after} seconds before retry...")
                time.sleep(retry_after)
                continue
            response.raise_for_status()
            data = response.json()
            break
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (attempt + 1) * 2
            logger.warning(f"⚠️ Request failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)

    if "error" in data:
        raise ValueError(
            f"Wikivoyage API error: {data['error'].get('info', 'Unknown error')}"
        )

    html_content = data["parse"]["text"]["*"]
    resolved_title = data["parse"]["title"]
    return html_content, resolved_title


def parse_wikivoyage_sections(html_content: str) -> dict[str, list[str]]:
    """Parse HTML into sections grouped under level 2 headings."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove edit section links so they don't pollute the text
    for edit in soup.find_all(class_="mw-editsection"):
        edit.decompose()

    container = soup.find(class_="mw-parser-output")
    if not container:
        container = soup

    def is_h2(tag):
        if tag.name == "h2":
            return True
        if tag.name == "div" and any(c in tag.get("class", []) for c in ["mw-heading2", "mw-heading-h2"]):
            return True
        return False

    def is_h3(tag):
        if tag.name == "h3":
            return True
        if tag.name == "div" and any(c in tag.get("class", []) for c in ["mw-heading3", "mw-heading-h3"]):
            return True
        return False

    def get_heading_text(tag):
        h_tag = tag.find(["h2", "h3"])
        if h_tag:
            return h_tag.get_text().strip()
        return tag.get_text().strip()

    sections = {}
    current_h2 = "Introduction"
    sections[current_h2] = []

    for child in container.find_all(recursive=False):
        if is_h2(child):
            current_h2 = get_heading_text(child)
            sections[current_h2] = []
        elif is_h3(child):
            heading_text = get_heading_text(child)
            sections[current_h2].append(f"\n### {heading_text}\n")
        elif child.name == "p":
            text = child.get_text().strip()
            if text:
                sections[current_h2].append(text)
        elif child.name in ["ul", "ol"]:
            items = []
            for li in child.find_all("li"):
                li_text = li.get_text().strip()
                if li_text:
                    items.append(f"- {li_text}")
            if items:
                sections[current_h2].append("\n".join(items))
        elif child.name == "dl":
            text = child.get_text().strip()
            if text:
                sections[current_h2].append(text)

    # Filter out empty sections or internal navigation sections
    cleaned_sections = {}
    for sec_name, blocks in sections.items():
        # Skip meta/navigation/districts sections which don't contain travel tips
        sec_lower = sec_name.lower()
        if any(k in sec_lower for k in ["districts", "go next", "references", "external links", "introduction"]):
            continue
        cleaned_blocks = [_clean_text(b) for b in blocks if b.strip()]
        if cleaned_blocks:
            cleaned_sections[sec_name] = cleaned_blocks

    return cleaned_sections


def chunk_section_content(blocks: list[str], max_words: int = MAX_CHUNK_WORDS) -> list[str]:
    """Group blocks into text chunks of at most max_words words."""
    chunks = []
    current_chunk = []
    current_word_count = 0

    for block in blocks:
        block_words = len(block.split())
        if block_words > max_words:
            # First, flush any accumulated chunk
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_word_count = 0

            # Split the giant block itself by word counts
            words = block.split()
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i : i + max_words]))
        else:
            if current_word_count + block_words > max_words and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [block]
                current_word_count = block_words
            else:
                current_chunk.append(block)
                current_word_count += block_words

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    return chunks


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Wikivoyage page sections into Pinecone vector store."
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Wikivoyage page name to ingest (e.g. 'Delhi', 'Varanasi')",
    )
    parser.add_argument(
        "--country",
        default="india",
        help="Country to associate with the destination metadata (default: 'india')",
    )
    args = parser.parse_args()

    if not is_available():
        logger.error(
            "❌ Pinecone is not configured or unreachable. "
            "Set PINECONE_API_KEY in your .env and try again."
        )
        sys.exit(1)

    try:
        html_content, resolved_title = fetch_wikivoyage_html(args.destination)
        logger.info(f"📖 Successfully fetched page '{resolved_title}' from Wikivoyage")
    except Exception as e:
        logger.error(f"❌ Failed to fetch page from Wikivoyage: {e}")
        sys.exit(1)

    sections = parse_wikivoyage_sections(html_content)
    logger.info(f"📂 Parsed {len(sections)} sections from HTML content")

    upserted = 0
    skipped = 0

    normalized_dest = _normalize_destination(resolved_title)
    country_lower = args.country.lower().strip()

    for sec_name, blocks in sections.items():
        category = _determine_category(sec_name)
        chunks = chunk_section_content(blocks, MAX_CHUNK_WORDS)

        logger.info(
            f"⚡ Processing section '{sec_name}' -> mapped to category '{category}' "
            f"({len(chunks)} chunks)"
        )

        for idx, chunk in enumerate(chunks):
            # Deterministic, unique ID for every chunk
            tip_id = _deterministic_id(normalized_dest, category, chunk)
            if idx > 0:
                tip_id = f"{tip_id}_{idx}"

            # Format the text content for premium rendering: prefix with section context
            full_content = f"[{resolved_title} Guide - {sec_name}]\n{chunk}"

            metadata = {
                "destination": normalized_dest,
                "country": country_lower,
                "category": category,
            }

            ok = upsert_travel_tip(id=tip_id, content=full_content, metadata=metadata)
            if ok:
                upserted += 1
            else:
                skipped += 1

    logger.info(
        f"🎉 Ingestion complete: {upserted} upserted, {skipped} failed for '{resolved_title}'"
    )


if __name__ == "__main__":
    main()
