"""G3 Phase-2 evidence pass: stream-hash the nine originals and pull cover pages.

Read-only over the live company roots; every byte read is charged to the lane
read budget and the run stops as ``partial`` when the budget refuses.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from g3_source_facts.budget import ReadBudget


def _git_common_dir() -> Path:
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


REPO = Path(__file__).resolve().parents[2]
LIVE = _git_common_dir().parent
SAMPLES = REPO / "benchmarks/narrative_document_types/samples.json"
ET_ROOT = LIVE.parent / "earnings-transcripts" / "earnings-transcripts" / "transcripts"
OUT = REPO / ".planning/g3-source-facts/scratch"
PAGES = OUT / "pages"

ROOTS = {
    "company_raw": LIVE,
    "earnings_transcripts": ET_ROOT,
}


def digest(path: Path, budget: ReadBudget, chunk: int = 1 << 20) -> str:
    budget.charge(path.stat().st_size, label=f"hash:{path.name}")
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            sha.update(block)
    return sha.hexdigest()


def main() -> int:
    PAGES.mkdir(parents=True, exist_ok=True)
    budget = ReadBudget()
    register = json.loads(SAMPLES.read_text(encoding="utf-8"))
    rows = []
    status = "complete"
    for sample in register["samples"]:
        root = ROOTS[sample["root_key"]]
        path = root / sample["relative_path"]
        row = {
            "sample_id": sample["sample_id"],
            "expected_sha256": sample["sha256"],
            "expected_bytes": sample["byte_size"],
            "exists": path.exists(),
        }
        if not path.exists():
            rows.append(row)
            continue
        row["actual_bytes"] = path.stat().st_size
        row["mtime_ns"] = path.stat().st_mtime_ns
        row["actual_sha256"] = digest(path, budget)
        row["sha_match"] = row["actual_sha256"] == sample["sha256"]
        row["bytes_match"] = row["actual_bytes"] == sample["byte_size"]

        if path.suffix.lower() == ".pdf":
            budget.charge(path.stat().st_size, label=f"cover:{path.name}")
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            row["page_count"] = len(reader.pages)
            text = reader.pages[0].extract_text() or ""
            if sample["sample_id"] in {"S07", "S08"} and len(reader.pages) > 1:
                text += "\n--- page 2 ---\n" + (reader.pages[1].extract_text() or "")
            (PAGES / f"{sample['sample_id']}_cover.txt").write_text(
                text, encoding="utf-8"
            )
            row["cover_chars"] = len(text)
        else:
            budget.charge(path.stat().st_size, label=f"txt:{path.name}")
            raw = path.read_text(encoding="utf-8", errors="replace")
            (PAGES / f"{sample['sample_id']}_head.txt").write_text(
                "\n".join(raw.splitlines()[:60]), encoding="utf-8"
            )
            row["lines"] = len(raw.splitlines())
        rows.append(row)

    if budget.hit:
        status = "partial"
    summary = {
        "status": status,
        "budget": budget.summary(),
        "samples": rows,
    }
    (OUT / "hash_and_cover.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": status,
                "consumed_bytes": budget.consumed,
                "sha_all_match": all(r.get("sha_match") for r in rows),
                "rows": [
                    {
                        k: r.get(k)
                        for k in (
                            "sample_id",
                            "sha_match",
                            "bytes_match",
                            "page_count",
                            "cover_chars",
                            "lines",
                        )
                    }
                    for r in rows
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
