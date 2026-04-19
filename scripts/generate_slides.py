#!/usr/bin/env python3
"""
generate_slides.py -- Generate Marp-format slide decks from wiki content.

Reads wiki page(s) for a specified entity (company, sector, or theme),
extracts timeline entries and comprehensive assessments, and produces
a Marp markdown file that can be converted to PDF/PPTX with marp-cli.

Usage:
    python scripts/generate_slides.py --company 中微公司
    python scripts/generate_slides.py --sector 半导体设备
    python scripts/generate_slides.py --theme AI产业链

The output file is saved as {entity}_slides.md in the entity's wiki directory.
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import yaml


WIKI_ROOT = Path(__file__).resolve().parent.parent

MAX_TIMELINE_ENTRIES = 10


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TimelineEntry:
    """One timeline entry parsed from a wiki page."""
    date: str
    source_type: str
    title: str
    points: List[str] = field(default_factory=list)

    def display_title(self) -> str:
        return f"{self.source_type} | {self.title}"


@dataclass
class WikiPage:
    """Parsed content of a single wiki markdown file."""
    path: Path
    title: str = ""
    entity: str = ""
    page_type: str = ""
    last_updated: str = ""
    core_questions: List[str] = field(default_factory=list)
    timeline: List[TimelineEntry] = field(default_factory=list)
    assessment: str = ""
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(content: str) -> Tuple[dict, str]:
    """Return (frontmatter_dict, body_text)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end < 0:
        return {}, content
    fm_text = content[3:end]
    body = content[end + 3:]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def _parse_core_questions(body: str) -> List[str]:
    """Extract bullet points under the '## 核心问题' section."""
    questions: List[str] = []
    in_section = False
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped.lstrip("# ").strip()
            in_section = "核心问题" in heading
            continue
        if in_section:
            if stripped.startswith("## "):
                break
            if stripped.startswith("- "):
                text = stripped[2:].strip()
                if text:
                    questions.append(text)
    return questions


def _parse_assessment(body: str) -> str:
    """Extract the blockquote content under '## 综合评估'."""
    capturing = False
    parts: List[str] = []
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## ") and "综合评估" in stripped:
            capturing = True
            continue
        if capturing:
            if stripped.startswith("## "):
                break
            # Collect lines that are part of the blockquote
            if stripped.startswith(">"):
                parts.append(stripped.lstrip("> ").strip())
            elif stripped == "":
                if parts and parts[-1] != "":
                    parts.append("")
            else:
                # Some assessments have plain text lines too
                parts.append(stripped)
    return " ".join(p for p in parts if p != "").strip()


def _parse_timeline(body: str) -> List[TimelineEntry]:
    """Parse all timeline entries (### YYYY-MM-DD | type | title ...)."""
    entries: List[TimelineEntry] = []
    current: Optional[TimelineEntry] = None

    # Pattern for the heading: ### 2026-04-17 | 产品 | Some title
    heading_re = re.compile(
        r"^###\s+(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*(.+)$"
    )

    for line in body.split("\n"):
        m = heading_re.match(line.strip())
        if m:
            if current is not None:
                entries.append(current)
            current = TimelineEntry(
                date=m.group(1),
                source_type=m.group(2).strip(),
                title=m.group(3).strip(),
            )
            continue

        if current is not None:
            stripped = line.strip()
            # Stop at next ### or ## heading
            if stripped.startswith("### ") or stripped.startswith("## "):
                entries.append(current)
                current = None
                # Check if this is another timeline entry heading
                m2 = heading_re.match(stripped)
                if m2:
                    current = TimelineEntry(
                        date=m2.group(1),
                        source_type=m2.group(2).strip(),
                        title=m2.group(3).strip(),
                    )
                continue
            # Collect bullet points (key takeaways)
            if stripped.startswith("- ") and not stripped.startswith("- [来源"):
                point = stripped[2:].strip()
                if point:
                    current.points.append(point)

    if current is not None:
        entries.append(current)

    return entries


def parse_wiki_file(filepath: Path) -> WikiPage:
    """Parse a wiki markdown file into a WikiPage."""
    content = filepath.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(content)

    page = WikiPage(
        path=filepath,
        title=fm.get("title", filepath.stem),
        entity=fm.get("entity", ""),
        page_type=fm.get("type", ""),
        last_updated=str(fm.get("last_updated", "")),
        tags=fm.get("tags", []),
    )
    page.core_questions = _parse_core_questions(body)
    page.timeline = _parse_timeline(body)
    page.assessment = _parse_assessment(body)

    return page


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------

def _resolve_company(name: str) -> List[Path]:
    """Return all wiki/*.md files under companies/{name}/wiki/."""
    wiki_dir = WIKI_ROOT / "companies" / name / "wiki"
    if not wiki_dir.is_dir():
        print(f"Error: company wiki directory not found: {wiki_dir}", file=sys.stderr)
        sys.exit(1)
    files = sorted(wiki_dir.glob("*.md"))
    if not files:
        print(f"Error: no wiki files found for company '{name}'", file=sys.stderr)
        sys.exit(1)
    return files


def _resolve_sector(name: str) -> List[Path]:
    """Return all wiki/*.md files under sectors/{name}/wiki/."""
    wiki_dir = WIKI_ROOT / "sectors" / name / "wiki"
    if not wiki_dir.is_dir():
        print(f"Error: sector wiki directory not found: {wiki_dir}", file=sys.stderr)
        sys.exit(1)
    files = sorted(wiki_dir.glob("*.md"))
    if not files:
        print(f"Error: no wiki files found for sector '{name}'", file=sys.stderr)
        sys.exit(1)
    return files


def _resolve_theme(name: str) -> List[Path]:
    """Return all wiki/*.md files under themes/{name}/wiki/."""
    wiki_dir = WIKI_ROOT / "themes" / name / "wiki"
    if not wiki_dir.is_dir():
        print(f"Error: theme wiki directory not found: {wiki_dir}", file=sys.stderr)
        sys.exit(1)
    files = sorted(wiki_dir.glob("*.md"))
    if not files:
        print(f"Error: no wiki files found for theme '{name}'", file=sys.stderr)
        sys.exit(1)
    return files


def resolve_entity(args: argparse.Namespace) -> Tuple[str, List[Path]]:
    """Determine entity name and wiki file paths from CLI args."""
    if args.company:
        return args.company, _resolve_company(args.company)
    if args.sector:
        return args.sector, _resolve_sector(args.sector)
    if args.theme:
        return args.theme, _resolve_theme(args.theme)
    print("Error: specify one of --company, --sector, or --theme", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Slide generation
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Remove wikilinks markup [[...]] for clean slide display."""
    # Replace [[target|display]] with display
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    # Replace [[target]] with target
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return text


def _generate_title_slide(entity: str, page: WikiPage) -> List[str]:
    """Generate the opening title slide."""
    lines = [
        "<!-- _class: lead -->",
        "",
        f"# {entity}",
        "",
    ]
    topic = page.title if page.title and page.title != entity else ""
    if topic:
        lines.append(f"## {topic}")
        lines.append("")
    if page.last_updated:
        lines.append(f"Updated: {page.last_updated}")
        lines.append("")
    return lines


def _generate_overview_slide(pages: List[WikiPage]) -> List[str]:
    """Generate the overview/assessment slide."""
    # Collect all assessments from all pages
    assessments = []
    for page in pages:
        if page.assessment:
            assessments.append((page.title, page.assessment))

    if not assessments:
        return []

    lines = [
        "# 综合评估",
        "",
    ]

    for page_title, assessment in assessments:
        if len(assessments) > 1:
            lines.append(f"### {page_title}")
            lines.append("")

        # Clean and truncate assessment for slide readability
        clean = _clean_text(assessment)
        # Remove bold markers for plain readability, but keep emphasis
        clean = clean.replace("**", "")
        # Split into sentences and display as bullet points if long
        sentences = re.split(r"(?<=[。；！？])", clean)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 3:
            for s in sentences:
                lines.append(f"- {s}")
        else:
            # Show first 5 key sentences
            for s in sentences[:5]:
                lines.append(f"- {s}")
            if len(sentences) > 5:
                lines.append(f"- ... (共 {len(sentences)} 个要点)")
        lines.append("")

    return lines


def _generate_timeline_slide(entry: TimelineEntry) -> List[str]:
    """Generate a single slide for one timeline entry."""
    lines = [
        f"### {entry.date} | {entry.source_type}",
        "",
        f"**{_clean_text(entry.title)}**",
        "",
    ]

    points = entry.points[:5]  # Max 5 bullet points per slide
    for p in points:
        clean_p = _clean_text(p)
        # Truncate overly long points
        if len(clean_p) > 120:
            clean_p = clean_p[:117] + "..."
        lines.append(f"- {clean_p}")

    if not points:
        lines.append("(无详细要点)")

    lines.append("")
    return lines


def _generate_questions_slide(pages: List[WikiPage]) -> List[str]:
    """Generate a slide showing core questions being tracked."""
    all_questions = []
    for page in pages:
        for q in page.core_questions:
            all_questions.append(_clean_text(q))

    if not all_questions:
        return []

    lines = [
        "# 核心跟踪问题",
        "",
    ]
    for i, q in enumerate(all_questions[:6], 1):
        if len(q) > 100:
            q = q[:97] + "..."
        lines.append(f"{i}. {q}")
    lines.append("")
    return lines


def _generate_summary_slide(entity: str, pages: List[WikiPage]) -> List[str]:
    """Generate a closing summary slide with stats."""
    total_entries = sum(len(p.timeline) for p in pages)
    total_sources = 0
    for page in pages:
        # Try to get sources_count from frontmatter
        try:
            content = page.path.read_text(encoding="utf-8")
            fm, _ = _parse_frontmatter(content)
            total_sources += int(fm.get("sources_count", 0))
        except Exception:
            pass

    lines = [
        "<!-- _class: lead -->",
        "",
        "# Summary",
        "",
        f"- Entity: **{entity}**",
        f"- Wiki pages: **{len(pages)}**",
        f"- Timeline entries: **{total_entries}**",
        f"- Total sources: **{total_sources}**",
        "",
        "> Generated by company-wiki slide generator",
        "",
    ]
    return lines


def generate_slides(entity: str, wiki_files: List[Path]) -> str:
    """Build the complete Marp markdown content from wiki files."""
    # Parse all wiki pages
    pages = [parse_wiki_file(f) for f in wiki_files]

    # Use the first page as the primary page for metadata
    primary = pages[0]

    slides: List[str] = []

    # Marp frontmatter
    slides.append("---")
    slides.append("marp: true")
    slides.append("theme: default")
    slides.append("paginate: true")
    slides.append("")

    # Slide 1: Title
    slides.extend(_generate_title_slide(entity, primary))

    # Slide 2: Core questions (if any)
    questions_slide = _generate_questions_slide(pages)
    if questions_slide:
        slides.append("---")
        slides.append("")
        slides.extend(questions_slide)

    # Slide 3: Overview / Assessment
    overview_slide = _generate_overview_slide(pages)
    if overview_slide:
        slides.append("---")
        slides.append("")
        slides.extend(overview_slide)

    # Timeline slides: merge entries from all pages, sort by date descending,
    # take the most recent MAX_TIMELINE_ENTRIES
    all_entries: List[TimelineEntry] = []
    for page in pages:
        all_entries.extend(page.timeline)
    # Sort by date descending
    all_entries.sort(key=lambda e: e.date, reverse=True)
    # Take the most recent entries
    selected = all_entries[:MAX_TIMELINE_ENTRIES]

    for entry in selected:
        slides.append("---")
        slides.append("")
        slides.extend(_generate_timeline_slide(entry))

    # Final slide: Summary
    slides.append("---")
    slides.append("")
    slides.extend(_generate_summary_slide(entity, pages))

    return "\n".join(slides)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def get_output_path(entity: str, args: argparse.Namespace) -> Path:
    """Determine where to write the slides file."""
    if args.company:
        return WIKI_ROOT / "companies" / entity / "wiki" / f"{entity}_slides.md"
    if args.sector:
        return WIKI_ROOT / "sectors" / entity / "wiki" / f"{entity}_slides.md"
    if args.theme:
        return WIKI_ROOT / "themes" / entity / "wiki" / f"{entity}_slides.md"
    raise ValueError("No entity type specified")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Marp slide decks from wiki content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
    python scripts/generate_slides.py --company 中微公司
    python scripts/generate_slides.py --sector 半导体设备
    python scripts/generate_slides.py --theme AI产业链
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--company",
        help="Company name (directory under companies/)",
    )
    group.add_argument(
        "--sector",
        help="Sector name (directory under sectors/)",
    )
    group.add_argument(
        "--theme",
        help="Theme name (directory under themes/)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: {entity}_slides.md in wiki dir)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    entity, wiki_files = resolve_entity(args)
    print(f"Generating slides for '{entity}' from {len(wiki_files)} wiki page(s)...")

    content = generate_slides(entity, wiki_files)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = get_output_path(entity, args)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(content, encoding="utf-8")
    print(f"Slides written to: {output_path}")

    # Report stats
    slide_count = content.count("---") - 1  # First --- is frontmatter
    print(f"  Total slides: {slide_count}")


if __name__ == "__main__":
    main()
