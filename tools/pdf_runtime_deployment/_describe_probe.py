"""Metadata-only closure/RECORD probe; runs inside a chosen interpreter.

Modes:
  source: describe the closure this interpreter resolves for a runtime config.
  verify: the same description plus isolation assertions against expectations.

No SDK import, no environment enumeration beyond the resolved closure, no
writes. This is the existing pure resolver (narrative_pdf_environment) reached
through a normal module import, not a new loader.
"""
from __future__ import annotations

from hashlib import sha256
import csv
from io import StringIO
import json
from pathlib import Path
import site
import sys


def _load_config(path: str) -> dict:
    config = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if (config.get("schema_version") != "pdf-paragraph-runtime/2"
            or config.get("environment_algorithm") != "pdf-runtime-closure/2"):
        raise SystemExit("probe requires an explicit pdf-paragraph-runtime/2 config")
    return config


def _describe(repo_src: str, config: dict) -> tuple[dict, dict]:
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(repo_src) / "src" if (Path(repo_src) / "src").is_dir() else repo_src))
    from company_wiki.source_catalog.narrative_pdf_environment import (  # noqa: E402
        configured_runtime_roots, describe_environment)
    closure = describe_environment(configured_runtime_roots(config["runtime_versions"]))
    distributions = {}
    from importlib import metadata  # noqa: E402
    for item in closure["distributions"]:
        name = item["name"]
        dist = metadata.distribution(name)
        path = Path(str(dist._path)).resolve()  # type: ignore[attr-defined]  # existing reader pattern
        record = list(csv.reader(StringIO((path / "RECORD").read_text(encoding="utf-8"))))
        distributions[name] = {
            "version": dist.version, "path": str(path),
            "record_sha256": sha256((path / "RECORD").read_bytes()).hexdigest(),
            "record": [[row[0], row[1] if len(row) > 1 else "", row[2] if len(row) > 2 else ""]
                       for row in record if row],
        }
    return closure, distributions


def main() -> None:
    arguments = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    mode = arguments.get("--mode")
    config = _load_config(arguments["--config"])
    closure, distributions = _describe(arguments["--repo-src"], config)
    payload = {"python": sys.executable, "prefix": sys.prefix, "base_prefix": sys.base_prefix,
               "closure": closure, "distributions": distributions,
               "site_packages": str(next(Path(value).resolve() for value in sys.path
                                          if value and "site-packages" in value))}
    if mode == "source":
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True))
        return
    if mode != "verify":
        raise SystemExit("probe mode must be source or verify")
    expected = json.loads(Path(arguments["--expected"]).read_text(encoding="utf-8"))
    from packaging.utils import canonicalize_name  # noqa: E402
    assert closure["environment_sha256"] == config["environment_sha256"] == expected["environment_sha256"]
    assert len(closure["distributions"]) == expected["distribution_count"]
    target_site = Path(expected["target_site"])
    third_party = set()
    from importlib import metadata  # noqa: E402
    for dist in metadata.distributions():
        name = canonicalize_name(dist.metadata["Name"])
        if name == "company-wiki":
            continue
        third_party.add(name)
        assert Path(str(dist._path)).resolve().is_relative_to(target_site), name  # type: ignore[attr-defined]  # existing reader pattern
    assert third_party == {item["name"] for item in closure["distributions"]}
    assert "pip" not in third_party
    assert site.ENABLE_USER_SITE is False
    assert not any(Path(value).resolve() == Path(sys.base_prefix) / "Lib" / "site-packages"
                   for value in sys.path if value)
    assert all(ord(char) < 128 for char in sys.prefix)
    assert not any(name in sys.modules for name in ("docling", "transformers", "torch", "dill"))
    print(json.dumps({"status": "PASS", "environment_sha256": closure["environment_sha256"],
                      "distribution_count": len(closure["distributions"]),
                      "third_party_count": len(third_party), "prefix": sys.prefix,
                      "enable_user_site": False, "sdk_imports": 0}, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
