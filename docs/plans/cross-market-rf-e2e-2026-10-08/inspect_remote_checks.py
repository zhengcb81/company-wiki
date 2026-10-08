"""Read public GitHub Actions status for the exact repaired commits."""
import datetime
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

targets = [
    ("revenue-forecast", "08673cf87b8a58fc25982b695a9d14e28c6818d3"),
    ("StockInfoDownloader", "c0f07e12d4ba3e232d712bb6e5e491832023b0a0"),
]
record = {"read_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "runs": []}
for repo, sha in targets:
    url = f"https://api.github.com/repos/zhengcb81/{repo}/actions/runs?head_sha={sha}&per_page=10"
    row = {"repository": repo, "commit": sha}
    try:
        request = Request(url, headers={"User-Agent": "company-wiki-cross-market-audit", "Accept": "application/vnd.github+json"})
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
        row["workflow_runs"] = [{key: item.get(key) for key in
            ("id", "name", "head_branch", "head_sha", "status", "conclusion", "html_url", "created_at", "updated_at")}
            for item in payload.get("workflow_runs", [])]
    except (HTTPError, URLError, TimeoutError) as exc:
        row.update(status="unavailable", error=str(exc))
    record["runs"].append(row)
destination = Path(__file__).resolve().parent / "remote_ci_status.json"
destination.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record, ensure_ascii=False))
