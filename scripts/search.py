#!/usr/bin/env python3
"""
search.py -- Local TF-IDF search engine for wiki pages

Scans all wiki pages under companies/, sectors/, themes/ and builds
an inverted index with TF-IDF scoring.  Supports Chinese text via
character bigram tokenization (no jieba dependency required).

Usage:
    python scripts/search.py "刻蚀设备国产化率"
    python scripts/search.py "刻蚀设备国产化率" --max-results 10
    python scripts/search.py "刻蚀设备国产化率" --rebuild
"""

import argparse
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

WIKI_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = WIKI_ROOT / ".search_index.json"

SNIPPET_MAX_LEN = 200
SNIPPET_WINDOW = 80


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def _is_cjk(ch: str) -> bool:
    """Return True if *ch* is a CJK unified ideograph."""
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x20000 <= cp <= 0x2A6DF
        or 0x2A700 <= cp <= 0x2B73F
        or 0x2B740 <= cp <= 0x2B81F
        or 0xF900 <= cp <= 0xFAFF
    )


def tokenize(text: str) -> List[str]:
    """Tokenize *text* into a list of tokens.

    - CJK characters produce character bigrams (overlapping pairs).
    - ASCII / Latin words are lowercased and kept as-is.
    - Digits sequences are kept as single tokens.
    Punctuation and whitespace are separators.
    """
    tokens: List[str] = []

    # Buffer for consecutive CJK chars
    cjk_buf: List[str] = []
    # Buffer for non-CJK word chars (ASCII letters, digits)
    word_buf: List[str] = []

    def _flush_cjk():
        if len(cjk_buf) >= 2:
            for i in range(len(cjk_buf) - 1):
                tokens.append(cjk_buf[i] + cjk_buf[i + 1])
        elif len(cjk_buf) == 1:
            # Single CJK char -- keep it as a unigram so short queries still match
            tokens.append(cjk_buf[0])
        cjk_buf.clear()

    def _flush_word():
        if word_buf:
            tokens.append("".join(word_buf).lower())
            word_buf.clear()

    for ch in text:
        if _is_cjk(ch):
            _flush_word()
            cjk_buf.append(ch)
        elif ch.isalnum() or ch == "_":
            _flush_cjk()
            word_buf.append(ch)
        else:
            _flush_cjk()
            _flush_word()

    _flush_cjk()
    _flush_word()
    return tokens


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from *content* and return the body."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            return content[end + 3 :]
    return content


def _clean_body(body: str) -> str:
    """Strip markdown noise from *body* to produce searchable plain text.

    Removes:
      - Headings markers (#)
      - Link syntax [text](url) and [[wikilink]]
      - List markers (-)
      - Image syntax
      - Extra whitespace
    """
    # Remove image syntax ![alt](url)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
    # Remove markdown links but keep the text: [text](url) -> text
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r" \1 ", body)
    # Remove wikilinks: [[page]] -> page
    body = re.sub(r"\[\[([^\]]*)\]\]", r" \1 ", body)
    # Remove heading markers
    body = re.sub(r"^#{1,6}\s*", " ", body, flags=re.MULTILINE)
    # Remove bold/italic markers
    body = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r" \1 ", body)
    # Collapse whitespace
    body = re.sub(r"\s+", " ", body)
    return body.strip()


# ---------------------------------------------------------------------------
# WikiSearchIndex
# ---------------------------------------------------------------------------

class WikiSearchIndex:
    """Build and query a TF-IDF inverted index over wiki pages."""

    def __init__(self, wiki_root: Optional[Path] = None):
        self.wiki_root = wiki_root or WIKI_ROOT
        # page_id -> relative path (posix style, from wiki_root)
        self.pages: Dict[int, str] = {}
        # page_id -> cleaned body text (kept for snippet extraction)
        self.page_texts: Dict[int, str] = {}
        # token -> {page_id: tf}
        self.inverted: Dict[str, Dict[int, float]] = {}
        # page_id -> norm factor (pre-computed for cosine scoring)
        self.page_norms: Dict[int, float] = {}
        # Total number of indexed documents
        self.num_docs: int = 0
        # token -> document frequency
        self.doc_freq: Dict[str, int] = {}

    # -- Index building -----------------------------------------------------

    def _discover_pages(self) -> List[Path]:
        """Find all wiki markdown pages under wiki_root."""
        pages: List[Path] = []
        for pattern in [
            "companies/*/wiki/*.md",
            "sectors/*/wiki/*.md",
            "themes/*/wiki/*.md",
        ]:
            pages.extend(sorted(self.wiki_root.glob(pattern)))
        return pages

    def _index_page(self, page_id: int, path: Path) -> None:
        """Read and index a single wiki page."""
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return

        rel = path.relative_to(self.wiki_root).as_posix()
        self.pages[page_id] = rel

        body = _strip_frontmatter(raw)
        cleaned = _clean_body(body)
        self.page_texts[page_id] = cleaned

        tokens = tokenize(cleaned)
        tf_counts = Counter(tokens)
        total = len(tokens) if tokens else 1

        for token, count in tf_counts.items():
            tf = count / total
            if token not in self.inverted:
                self.inverted[token] = {}
            self.inverted[token][page_id] = tf

    def build_index(self) -> None:
        """Scan all wiki pages and build the inverted index with TF-IDF weights."""
        start = time.time()

        page_paths = self._discover_pages()
        self.num_docs = len(page_paths)

        # Reset state
        self.pages.clear()
        self.page_texts.clear()
        self.inverted.clear()
        self.page_norms.clear()
        self.doc_freq.clear()

        # Phase 1: build TF values
        for page_id, path in enumerate(page_paths):
            self._index_page(page_id, path)

        # Phase 2: compute document frequencies
        for token, postings in self.inverted.items():
            self.doc_freq[token] = len(postings)

        # Phase 3: convert TF to TF-IDF and pre-compute norms
        for token in self.inverted:
            df = self.doc_freq[token]
            idf = math.log((self.num_docs + 1) / (df + 1)) + 1  # smoothed idf
            for page_id in self.inverted[token]:
                tfidf = self.inverted[token][page_id] * idf
                self.inverted[token][page_id] = tfidf
                self.page_norms[page_id] = self.page_norms.get(page_id, 0.0) + tfidf * tfidf

        # Finalize norms (sqrt of sum of squares)
        for page_id in self.page_norms:
            self.page_norms[page_id] = math.sqrt(self.page_norms[page_id])

        elapsed = time.time() - start
        print(
            f"Indexed {self.num_docs} pages, "
            f"{len(self.inverted)} unique tokens "
            f"in {elapsed:.2f}s"
        )

    # -- Persistence --------------------------------------------------------

    def save(self, path: Optional[Path] = None) -> None:
        """Serialize the index to a JSON file for caching."""
        path = path or INDEX_PATH
        data = {
            "pages": {str(k): v for k, v in self.pages.items()},
            "page_norms": {str(k): v for k, v in self.page_norms.items()},
            "num_docs": self.num_docs,
            "doc_freq": self.doc_freq,
            "inverted": {
                token: {str(pid): score for pid, score in postings.items()}
                for token, postings in self.inverted.items()
            },
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(f"Index saved to {path} ({path.stat().st_size / 1024:.1f} KB)")

    def load(self, path: Optional[Path] = None) -> bool:
        """Load a previously saved index. Returns False if file is missing."""
        path = path or INDEX_PATH
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return False

        self.pages = {int(k): v for k, v in data["pages"].items()}
        self.page_norms = {int(k): v for k, v in data["page_norms"].items()}
        self.num_docs = data["num_docs"]
        self.doc_freq = data["doc_freq"]
        self.inverted = {
            token: {int(pid): score for pid, score in postings.items()}
            for token, postings in data["inverted"].items()
        }
        # Load page texts lazily only when we need snippets.
        # To avoid storing full text in the JSON (which would be large),
        # we re-read the actual files on demand.
        self.page_texts.clear()
        print(
            f"Loaded index: {self.num_docs} pages, "
            f"{len(self.inverted)} tokens"
        )
        return True

    def _ensure_page_text(self, page_id: int) -> str:
        """Load page text on demand for snippet extraction."""
        if page_id in self.page_texts:
            return self.page_texts[page_id]
        rel = self.pages.get(page_id)
        if not rel:
            return ""
        path = self.wiki_root / rel
        if not path.exists():
            return ""
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return ""
        body = _strip_frontmatter(raw)
        cleaned = _clean_body(body)
        self.page_texts[page_id] = cleaned
        return cleaned

    # -- Searching ----------------------------------------------------------

    def search(
        self, query: str, max_results: int = 10
    ) -> List[Tuple[str, float, str]]:
        """Search the index and return ranked results.

        Returns:
            A list of (relative_path, score, snippet) tuples sorted by
            descending score.
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Compute query TF-IDF vector
        query_tf = Counter(query_tokens)
        query_total = len(query_tokens)
        query_vec: Dict[str, float] = {}
        for token, count in query_tf.items():
            tf = count / query_total
            df = self.doc_freq.get(token, 0)
            idf = math.log((self.num_docs + 1) / (df + 1)) + 1
            query_vec[token] = tf * idf

        query_norm = math.sqrt(sum(v * v for v in query_vec.values()))
        if query_norm == 0:
            return []

        # Accumulate cosine similarity scores
        scores: Dict[int, float] = defaultdict(float)
        for token, q_weight in query_vec.items():
            postings = self.inverted.get(token)
            if not postings:
                continue
            for page_id, d_weight in postings.items():
                scores[page_id] += q_weight * d_weight

        # Normalize by page norm and query norm
        for page_id in scores:
            p_norm = self.page_norms.get(page_id, 1.0)
            if p_norm > 0:
                scores[page_id] /= p_norm * query_norm

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Build result tuples with snippets
        results: List[Tuple[str, float, str]] = []
        for page_id, score in ranked[:max_results]:
            rel_path = self.pages.get(page_id, "")
            snippet = self._extract_snippet(page_id, query_tokens)
            results.append((rel_path, round(score, 4), snippet))

        return results

    def _extract_snippet(self, page_id: int, query_tokens: List[str]) -> str:
        """Extract a short snippet from the page showing the best matching region."""
        text = self._ensure_page_text(page_id)
        if not text:
            return ""

        # Find the best window: count how many query tokens appear in each window
        # We look for clusters of matching bigrams
        best_pos = 0
        best_hits = 0

        # Simple approach: find the position with the highest concentration of
        # query token matches
        text_lower = text
        hit_positions: List[int] = []

        for qt in query_tokens:
            start = 0
            while True:
                pos = text_lower.find(qt, start)
                if pos < 0:
                    break
                hit_positions.append(pos)
                start = pos + 1

        if hit_positions:
            # Find densest cluster
            hit_positions.sort()
            best_start = hit_positions[0]
            best_count = 0
            window_end_limit = len(text)

            for i, pos in enumerate(hit_positions):
                end = pos + SNIPPET_WINDOW
                if end > window_end_limit:
                    end = window_end_limit
                count = 0
                for j in range(i, len(hit_positions)):
                    if hit_positions[j] < end:
                        count += 1
                    else:
                        break
                if count > best_count:
                    best_count = count
                    best_start = pos

            best_pos = max(0, best_start - 20)

        # Extract snippet around best_pos
        snippet_start = best_pos
        snippet_end = min(len(text), snippet_start + SNIPPET_MAX_LEN)
        snippet = text[snippet_start:snippet_end]

        # Add ellipsis indicators
        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(text):
            snippet = snippet + "..."

        return snippet.strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Local TF-IDF search engine for wiki pages"
    )
    parser.add_argument("query", help="Search query (supports Chinese)")
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of results to return (default: 10)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuilding the index instead of loading cache",
    )
    parser.add_argument(
        "--save-index",
        action="store_true",
        default=True,
        help="Save the index to disk after building (default: True)",
    )
    args = parser.parse_args()

    index = WikiSearchIndex()

    if not args.rebuild and INDEX_PATH.exists():
        loaded = index.load()
        if not loaded:
            print("Failed to load cached index, rebuilding...")
            index.build_index()
            index.save()
    else:
        index.build_index()
        if args.save_index:
            index.save()

    print()
    print(f'Searching for: "{args.query}"')
    print("-" * 60)

    start = time.time()
    results = index.search(args.query, max_results=args.max_results)
    elapsed = time.time() - start

    if not results:
        print("No results found.")
    else:
        for i, (path, score, snippet) in enumerate(results, 1):
            print(f"\n{i}. [{score}] {path}")
            if snippet:
                # Truncate snippet for display
                display = snippet
                if len(display) > 150:
                    display = display[:147] + "..."
                print(f"   {display}")

    print()
    print(f"Search completed in {elapsed * 1000:.1f}ms ({len(results)} results)")


if __name__ == "__main__":
    main()
