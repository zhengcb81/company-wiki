"""Bounded, opt-in public-source research; never opens the production catalog.

This probe freezes API bytes for offline construction-card tests. It is not
the production provider, does not run as part of CI, and must not be imported
by the product. Re-running requires a new empty --output directory.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
PAGE = "https://vip.stock.finance.sina.com.cn/corp/go.php/vFD_FinanceSummary/stockid/688012/displaytype/4.phtml"
JS = "https://n.sinaimg.cn/finance/2022/pc/cncw2022.js"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False, parents=True)
    calls = 0
    byte_count = 0
    observations = []

    def fetch(url: str) -> tuple[bytes, dict]:
        nonlocal calls, byte_count
        if calls >= 24:
            raise RuntimeError("research request cap")
        calls += 1
        request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": PAGE})
        with urlopen(request, timeout=20) as response:
            body = response.read(1_000_001)
            metadata = {"url": response.url, "http_status": response.status,
                        "content_type": response.headers.get("Content-Type"),
                        "server_date": response.headers.get("Date")}
        if len(body) > 1_000_000 or byte_count + len(body) > 12_000_000:
            raise RuntimeError("research response/total byte cap")
        byte_count += len(body)
        metadata.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                        retrieved_at=datetime.now(timezone.utc).isoformat())
        time.sleep(0.35)
        return body, metadata

    def api(code: str, source: str, page: int = 1, num: int = 10, report_type: int = 0) -> dict:
        params = {"paperCode": code, "source": source, "type": report_type, "page": page, "num": num}
        body, meta = fetch(BASE + "?" + urlencode(params))
        payload = json.loads(body)
        name = f"{code}-{source}-type{report_type}-page{page}-num{num}.json.gz"
        (args.output / name).write_bytes(gzip.compress(body, mtime=0))
        result = payload.get("result", {})
        data = result.get("data")
        item = {**meta, "parameters": params, "fixture": name, "result_status": result.get("status"),
                "data_type": type(data).__name__}
        if isinstance(data, dict):
            reports = data.get("report_list") or {}
            item.update(report_count=data.get("report_count"), report_dates=data.get("report_date"),
                        reports=[{"period_end_raw": date,
                                  **{k: value.get(k) for k in ("rType", "rCurrency", "data_source", "is_audit", "audit_opinion", "publish_date", "update_time")},
                                  "items": len(value.get("data", [])),
                                  "sample_items": [entry for entry in value.get("data", []) if entry.get("item_field") in
                                    {"BIZTOTINCO", "BIZINCO", "TOTASSET", "TOTAASSET", "TOTLIAB", "TOTLIABSHAREQUI", "MANANETR", "BASICEPS", "EPSBASIC"}][:8],
                                  "precision_types": sorted({str(entry.get("item_precision")) for entry in value.get("data", [])}),
                                  "blank_field_rows": sum(not entry.get("item_field") for entry in value.get("data", [])),
                                  "null_values": sum(entry.get("item_value") is None for entry in value.get("data", []))}
                                 for date, value in reports.items()])
        observations.append(item)
        (args.output / "observations.json").write_text(json.dumps(observations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return data if isinstance(data, dict) else {}

    body, page_meta = fetch(PAGE)
    try:
        html = body.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        html, encoding = body.decode("gb18030"), "gb18030"
    page_meta.update(actual_strict_encoding=encoding,
                     report_type_buttons=re.findall(r'<[^>]+data-value=[\"\x27][^>]+>[^<]*', html),
                     cncw_script_urls=re.findall(r'(?:https?:)?//[^\"\x27<>\s]*cncw2022\.js[^\"\x27<>\s]*', html))
    body, js_meta = fetch(JS)
    script = body.decode("utf-8")
    js_meta.update(endpoint_observed=BASE in script, frontend_page_size=10,
                   frontend_formats_numbers=True, frontend_may_hide_zero_by_truthiness=True)
    # Complete reported history for the user's example: page count is not a
    # constant and is independent for each statement.
    for source in ("lrb", "fzb", "llb"):
        first = api("sh688012", source)
        total = int(first["report_count"])
        seen = set(first["report_list"])
        for page in range(2, (total + 9) // 10 + 1):
            data = api("sh688012", source, page=page)
            seen.update(data.get("report_list") or {})
        if len(seen) != total:
            raise RuntimeError(f"{source}: pagination has {len(seen)} unique reports, advertised {total}")
    api("sh688012", "lrb", page=5)  # documented terminal response
    api("sh688012", "lrb", num=2, report_type=4)
    # Different layouts/markets; these are schema probes, not a claim that all
    # companies or all exchanges are covered.
    for code, source in (("sz000333", "lrb"), ("sh600036", "fzb"), ("sh601318", "lrb")):
        api(code, source, num=1)
    api("sh999999", "lrb", num=1)
    result = {"schema_version": "sina-statements-research/1", "page": page_meta, "javascript": js_meta,
              "http_requests": calls, "response_bytes": byte_count, "observations": "observations.json",
              "production_catalog_opened": False, "paid_calls": 0, "credentials_read": False,
              "fixture_bytes": sum(p.stat().st_size for p in args.output.glob("*.gz"))}
    (args.output / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
