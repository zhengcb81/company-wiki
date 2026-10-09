"""Reproducible, opt-in major-node regression against frozen real companies.

Run from repo root: python -B -m tools.cross_market_suite.runner --help
No production writes; neither network nor project LLM calls in replay mode.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
from collections import Counter
import shutil
import subprocess
import sys
import time
import zipfile

from .runtime_evidence import runtime_properties

from .core import arithmetic_checks, compare_reports, domain_checks, isolated_directory, load, safe_child, sha, summarize, write_new

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "benchmarks/cross_market_rf/cases.json"
POINTS = REPO / "benchmarks/cross_market_rf/checkpoints.json"
sys.path.insert(0, str(REPO / "src"))


def acquisition_command(command, *, interface, origin, wiki):
    """Map CWP-owned code/state to test export; retain provider interpreter.

    The external venv is read-only and not archived. SDK imports use the
    archived provider cwd, not the editable install's original checkout.
    """
    values = []
    for value in command:
        isolated = interface == "dayu_sdk_bounded_v1" and value.startswith("${PROJECT_ROOT}/") \
            and not value.startswith("${PROJECT_ROOT}/../")
        values.append(value.replace("${PROJECT_ROOT}", str(wiki if isolated else origin))
                      .replace("${PYTHON_EXECUTABLE}", sys.executable))
    return values


class Suite:
    def __init__(self, args, root):
        self.args, self.root = args, root
        self.spec, self.points = load(SPEC), load(POINTS)
        self.checks = {(c["case"], key): {"case": c["case"], "id": key, "status": "NOT_RUN", "detail": "not executed"}
                       for c in self.spec["cases"] for key in self.points["per_company"]}
        self.checks.update({("ALL", key): {"case": "ALL", "id": key, "status": "NOT_RUN", "detail": "not executed"}
                            for key in self.points["shared"]})
        self.commands, self.protected = [], {}
        self.process_log = root / "processes"
        self.process_log.mkdir()
        self.env = dict(os.environ)
        if args.mode == "replay":
            self.env = {key: value for key, value in self.env.items()
                        if not any(t in key.upper() for t in ("KEY", "TOKEN", "SECRET", "PASSWORD"))}
        for key in ("HOME", "USERPROFILE", "TMP", "TEMP", "XDG_CACHE_HOME"):
            path = root / "profile" / key.lower()
            path.mkdir(parents=True)
            self.env[key] = str(path)
        self.env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1",
                        PYTHONHASHSEED="0",
                        CMRF_OFFLINE="1" if args.mode == "replay" else "0",
                        CMRF_PROCESS_LOG=str(self.process_log),
                        REVENUE_PUBLICATION_REGISTRY=str(root / "registry.jsonl"))
        self.env["PYTHONPATH"] = os.pathsep.join((str(REPO / "tools/cross_market_suite/replay_hook"), str(REPO / "src")))

    def set(self, case, key, status, detail, **evidence):
        if (case, key) not in self.checks:
            raise ValueError("undefined checkpoint")
        self.checks[case, key] = dict(case=case, id=key, status=status, detail=detail, **evidence)

    def protect(self, path):
        path = Path(path).resolve()
        self.protected[path] = (sha(path), path.stat().st_size, path.stat().st_mtime_ns) if path.is_file() else None

    def command(self, argv, *, cwd=None, payload=None, timeout=90, expected=0, binary=False, env_override=None):
        index, started = len(self.commands), time.monotonic()
        log = dict(index=index, argv=[str(a) for a in argv], cwd=str(cwd or self.root))
        self.commands.append(log)
        # Streams go to bounded test-local files, not the source/research archive.
        out, err = self.root / f"stdout-{index}", self.root / f"stderr-{index}"
        with out.open("wb") as stdout, err.open("wb") as stderr:
            process = subprocess.Popen(log["argv"], cwd=cwd or self.root, env={**self.env, **(env_override or {})},
                                       stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                       start_new_session=os.name != "nt",
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
            try:
                process.communicate(json.dumps(payload).encode("utf-8") if payload is not None else None,
                                    timeout=timeout)
            except BaseException:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=15)
                else:
                    import signal
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=15)
                log.update(returncode=process.returncode, interrupted=True)
                raise
            finally:
                log["seconds"] = round(time.monotonic() - started, 3)
        log.update(returncode=process.returncode, stdout_sha256=sha(out), stdout_bytes=out.stat().st_size,
                   stderr_sha256=sha(err), stderr_bytes=err.stat().st_size)
        if out.stat().st_size > 32 * 1024 * 1024 or err.stat().st_size > 1024 * 1024:
            raise AssertionError("command exceeded test output cap")
        stdout, stderr = out.read_bytes(), err.read_bytes()
        # Never keep raw binaries, large reports, credentials or complete research text in engineering logs.
        detail = stderr.decode("utf-8", errors="replace")[:3000]
        for key, value in {**os.environ, **self.env}.items():
            if value and any(t in key.upper() for t in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
                detail = detail.replace(value, "<redacted>")
        log["stderr_excerpt"] = detail
        out.unlink()
        err.unlink()
        if expected is not None:
            assert process.returncode == expected, f"command {index} returned {process.returncode}: {detail} {stdout[:400] if not binary else ''}"
        return stdout, stderr, process.returncode

    def export(self, source, name, parts):
        head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True, timeout=20).strip()
        data = subprocess.check_output(["git", "-C", str(source), "archive", "--format=zip", head, *parts], timeout=30)
        target = self.root / name
        target.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                path = safe_child(target, entry.filename)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(entry))
        return target, head

    def raw(self, source):
        portable = self.args.delivery_root / "objects" / source["sha256"][:2] / source["sha256"]
        if source.get("object_relative") or portable.exists():
            path = portable
            self.protect(path)
            data = path.read_bytes()
        else:
            if not self.args.source_catalog_config.is_file():
                raise FileNotFoundError(2, "frozen raw absent and production reader config unavailable", str(self.args.source_catalog_config))
            assert source.get("source_ref"), "raw source unavailable; supply the frozen delivery/cwp catalog"
            ref = source["source_ref"]
            argv = [sys.executable, "-B", "-m", "company_wiki.source_catalog.source_reader_cli",
                    "--config", str(self.args.source_catalog_config), "--document-id", ref["document_id"],
                    "--source-id", ref["source_id"], "--content-sha256", ref["content_sha256"],
                    "--purpose", source.get("read_purpose", "filing_reuse")]
            # Only this zero-write production read resolves the user's configured Dropbox roots.
            # All writes/caches/worker profiles remain isolated; consumers still receive SourceRef.
            data, receipt, _ = self.command(argv, binary=True,
                env_override={"USERPROFILE": os.environ.get("USERPROFILE", str(Path.home()))})
            assert json.loads(receipt)["status"] == "ok"
        assert hashlib.sha256(data).hexdigest() == source["sha256"], "raw source SHA mismatch"
        return data

    def setup(self):
        self.rf, rf_head = self.export(self.args.rf_root, "rf", ["scripts", "config", "references", "SKILL.md"])
        self.ff, ff_head = self.export(self.args.ff_root, "ff", ["scripts", "config"])
        # Replay parser capabilities are fixture-declared, never inherited from host OCR.
        parts = ["src", "scripts", "tools/dayu_sdk_bridge.py"]
        if self.args.mode == "live":
            parts.insert(2, "config")
        self.wiki, cwp_head = self.export(REPO, "wiki", parts)
        self.versions = dict(rf=rf_head, ff=ff_head, cwp=cwp_head, python=sys.version)
        if self.args.et_root:
            self.et, et_head = self.export(self.args.et_root, "et", ["."])
            self.versions["et"] = et_head
            self.env["EARNINGS_TRANSCRIPTS_TOOL"] = str(self.et / "transcript_tool.py")
            key_file = self.args.ff_root / "config/FMP_API_KEY.txt"
            if self.args.mode == "live" and not self.env.get("FMP_API_KEY") and key_file.is_file():
                self.env["FMP_API_KEY"] = key_file.read_text(encoding="utf-8-sig").strip()
        self.env["PYTHONPATH"] = os.pathsep.join((str(REPO / "tools/cross_market_suite/replay_hook"), str(self.wiki / "src")))
        config_dir = self.wiki / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.catalog_config = config_dir / "source_catalog.yaml"
        self.catalog_config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": str(self.wiki / ".source_catalog"),
            "roots": [{"root_id": "company_raw", "kind": "company_raw", "path": str(self.wiki / "companies"), "read_only": False}]}), encoding="utf-8")
        self.ff_config = self.root / "ff-cwp.json"
        write_new(self.ff_config, {"schema_version": "1.0", "company_wiki_root": str(self.wiki)})
        security = self.wiki / ".source_catalog/security_master"
        security.mkdir(parents=True)
        for market in ("cn", "hk", "us"):
            shutil.copyfile(REPO / f"benchmarks/cross_market_rf/identity_{market}.json", security / (market + ".json"))
        # Live acquisition config is an explicit copy, never this repo's default or a provider permission override.
        if self.args.mode == "live":
            import yaml
            config = yaml.safe_load(self.args.acquisition_config.read_text(encoding="utf-8"))
            assert config["staging_root"] == "${PROJECT_ROOT}/.source_catalog/staging", "live staging_root must use the isolated PROJECT_ROOT token"
            origin = self.args.acquisition_config.parent.parent
            for market, adapter in config["adapters"].items():
                # Configuration is copied; provider code is exported at HEAD, never owner WIP.
                def expand(value):
                    if isinstance(value, str):
                        return value.replace("${PROJECT_ROOT}", str(origin)).replace("${PYTHON_EXECUTABLE}", sys.executable)
                    return value
                source = Path(expand(adapter["project_root"])).resolve()
                exported, head = self.export(source, "provider-" + market, ["."])
                self.versions["provider-" + market] = head
                adapter["project_root"] = str(exported)
                adapter["command"] = acquisition_command(adapter["command"],
                    interface=adapter["interface"], origin=origin, wiki=self.wiki)
                if adapter.get("config_root"):
                    original_config = Path(expand(adapter["config_root"])).resolve()
                    copied = self.root / ("provider-config-" + market)
                    copied.mkdir()
                    for path in original_config.glob("*.yaml"):
                        shutil.copyfile(path, copied / path.name)
                    adapter["config_root"] = str(copied)
            (config_dir / "source_acquisition.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
        else:
            (config_dir / "source_acquisition.yaml").write_text("schema_version: '1.1'\nstaging_root: '${PROJECT_ROOT}/.source_catalog/staging'\ntimeout_seconds: 10\nadapters: {}\n", encoding="utf-8")
        self.protect(self.args.source_catalog_config)
        self.protect(self.args.source_catalog_config.parent.parent / ".source_catalog/catalog.sqlite3")
        from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization, PPTX_MIME
        ocr_path = config_dir / "local_ocr.json"
        port = NarrativeNormalization.from_project(self.wiki, enabled=True)
        self.normalization_policy = {
            "profile": "offline_fixture_no_ocr" if self.args.mode == "replay" else "configured_head_snapshot",
            "cwp_head": cwp_head,
            "local_ocr_sha256": sha(ocr_path) if ocr_path.is_file() else None,
            "pptx_parser_version": port.identity(PPTX_MIME)["parser_version"],
        }
        if self.args.mode == "replay":
            assert port.config is None, "replay fixture unexpectedly inherited OCR config"
        self.context = {"root": str(self.root), "wiki": str(self.wiki), "rf": str(self.rf), "cases": [],
                        "normalization_policy": self.normalization_policy}

    def case(self, spec):
        case = spec["case"]
        directory = self.root / case
        directory.mkdir()
        try:
            for name, digest in spec["frozen_artifacts"].items():
                path = safe_child(self.args.delivery_root, case + "/" + name)
                self.protect(path)
                assert sha(path) == digest, f"fixed {name} SHA mismatch"
                shutil.copyfile(path, directory / name)
            review = REPO / spec["review_relative"]
            self.protect(review)
            assert sha(review) == spec["review_sha256"]
            sources = [(s, self.raw(s)) for s in spec["sources"]]
            self.set(case, "frozen_bytes", "PASS", "all referenced raw bytes and independent reviewed inputs opened", raw_count=len(sources))
            self.catalog_case(spec, directory, sources)
            self.forecast_case(spec, directory)
        except FileNotFoundError as exc:
            self.set(case, "frozen_bytes", "BLOCKED", "required frozen data bundle not available: " + str(exc.filename or exc))
        except (AssertionError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            self.set(case, "frozen_bytes" if self.checks[case, "frozen_bytes"]["status"] != "PASS" else "formal_forecast",
                     "FAIL", str(exc)[:2000])
        self.set(case, "future_backtest", "NOT_APPLICABLE", "future actuals absent in frozen as-of; no fabricated evaluation")
        self.set(case, "skill_coverage", "NOT_RUN", "fresh skill 0–11 research is not proven by replay; sealed independent review retained",
                 historical_review=spec["review_relative"], historical_review_sha256=spec["review_sha256"])
        self.set(case, "narrative_forecast_consumption", "NOT_RUN", "frozen accepted model inputs; new worker output is not silently substituted into research evidence")
        self.set(case, "correct_provider_download", "NOT_RUN", "offline replay does not contact real market providers")
        self.set(case, "transcript_live", "NOT_RUN", "offline contract is separate from real ET entitlement/acquisition")
        self.set(case, "official_provenance", "BLOCKED" if spec["market"] == "HK" else "NOT_RUN",
                 "HK archived-byte identity is known, fresh official authentication/publication day remains unproved" if spec["market"] == "HK" else "fresh official provenance must be established in live mode")
        if case != "US-MSFT":
            for key in ("format_html", "format_pptx"):
                self.set(case, key, "NOT_APPLICABLE", "format sample belongs to Microsoft case")

    def catalog_case(self, spec, directory, sources):
        from company_wiki.source_catalog.config import load_catalog_config
        from company_wiki.source_catalog.service import SourceCatalog
        from company_wiki.source_catalog.source_reader import SourceVersionReader
        case, primary = spec["case"], sources[0]
        source, data = primary
        destination = self.wiki / "companies" / spec["company_name"] / "raw" / source["filename"]
        destination.parent.mkdir(parents=True)
        destination.write_bytes(data)
        meta = dict(source["metadata"])
        meta.update(source_title=source["title"], company_name=spec["company_name"], market=spec["market"],
                    security_id=spec["security_id"], document_kind="annual_report", fiscal_year=2025,
                    language="en" if spec["market"] == "US" else "zh", content_sha256=source["sha256"])
        meta.setdefault("published_date", source["published_date"])
        meta["source_url"] = source["url"]
        destination.with_name(destination.name + ".source.json").write_text(json.dumps(meta), encoding="utf-8")
        config = load_catalog_config(self.catalog_config, project_root=self.wiki)
        catalog = SourceCatalog(config)
        try:
            relative = destination.relative_to(self.wiki / "companies").as_posix()
            assert catalog.register_sources(root_id="company_raw", relative_paths={relative}).errors == 0
            count = catalog.reader.fetchone("SELECT count(*) AS n FROM documents")["n"]
            assert catalog.register_sources(root_id="company_raw", relative_paths={relative}).errors == 0
            assert catalog.reader.fetchone("SELECT count(*) AS n FROM documents")["n"] == count
            row = catalog.reader.fetchone("SELECT document_id,primary_source_id FROM documents WHERE document_id=?",
                                        ("urn:company-wiki:document:sha256:" + source["sha256"],))
            assert row, "source not registered"
            reader = SourceVersionReader(catalog)
            ref = reader.query_ref(row["document_id"], row["primary_source_id"], source["sha256"])
            assert reader.open_version(ref, purpose="filing_reuse").data == data
            manifest = reader.describe_version(ref)
            assert (manifest["market"], manifest["security_id"], manifest["fiscal_year"]) == (spec["market"], spec["security_id"], 2025)
            self.set(case, "identity_period", "PASS", "copied source declarations, not fresh official authenticity proof",
                     published_date=manifest["published_date"], availability_semantics=source.get("publication_date_semantics"))
            self.set(case, "raw_replay", "PASS", "registration idempotent; verified original byte open", source_ref=asdict(ref))
            argv = [sys.executable, "-B", "-m", "company_wiki.source_catalog.source_reader_cli", "--config", str(self.catalog_config),
                    "--document-id", ref.document_id, "--source-id", ref.source_id, "--content-sha256", "0" * 64]
            out, _, rc = self.command(argv, expected=None, binary=True)
            assert rc != 0 and not out
            self.set(case, "wrong_hash", "PASS", "wrong SHA refused with zero original bytes")
            # Relocate only an owned copy, keep same logical root/id and source reference.
            moved = destination.with_name("moved-" + destination.name)
            destination.rename(moved)
            destination.with_name(destination.name + ".source.json").rename(moved.with_name(moved.name + ".source.json"))
            assert catalog.register_sources(root_id="company_raw", relative_paths={moved.relative_to(self.wiki / "companies").as_posix()}).errors == 0
            assert reader.open_version(ref, purpose="filing_reuse").data == data
            self.set(case, "virtual_move", "PASS", "old SourceRef opens bytes after isolated physical rename")
            self.context["cases"].append({"case": case, "config": str(self.catalog_config), "source_ref": asdict(ref),
                                           "raw_path": str(moved), "metadata": manifest})
            if case == "US-MSFT":
                old = load(REPO / "docs/plans/cross-market-rf-e2e-2026-10-08/existing_narrative_current_vs_asof.json")
                txt_ref = old["checks"][0]["request"]["narrative_ref"]["source_ref"]
                txt_spec = {"source_ref": txt_ref, "sha256": txt_ref["content_sha256"], "read_purpose": "narrative_derivation"}
                txt = self.raw(txt_spec)
                path = moved.parent / "call-FY2026Q4.txt"
                path.write_bytes(txt)
                path.with_name(path.name + ".source.json").write_text(json.dumps({
                    "company_name": spec["company_name"], "source_title": "Microsoft FY2026 Q4 earnings call transcript",
                    "market": "US", "security_id": "MSFT", "document_kind": "investor_call_transcript",
                    "fiscal_year": 2026, "fiscal_period": "Q4", "language": "en", "published_date": None,
                    "content_sha256": txt_ref["content_sha256"], "provenance_status": "legacy_unverified"}), encoding="utf-8")
                assert catalog.register_sources(root_id="company_raw", relative_paths={path.relative_to(self.wiki / "companies").as_posix()}).errors == 0
                opened_ref = reader.query_ref(txt_ref["document_id"], txt_ref["source_id"], txt_ref["content_sha256"])
                self.context["cases"][-1]["worker_source_ref"] = asdict(opened_ref)
                ppt_spec, ppt_data = next((s, body) for s, body in sources if s["filename"].endswith(".pptx"))
                ppt_path = moved.parent / ppt_spec["filename"]
                ppt_path.write_bytes(ppt_data)
                ppt_path.with_name(ppt_path.name + ".source.json").write_text(json.dumps({
                    "company_name": spec["company_name"], "source_title": ppt_spec["title"], "market": "US",
                    "security_id": "MSFT", "document_kind": "investor_presentation", "fiscal_year": 2027,
                    "language": "en", "published_date": ppt_spec["published_date"], "source_url": ppt_spec["url"],
                    "content_sha256": ppt_spec["sha256"]}), encoding="utf-8")
                assert catalog.register_sources(root_id="company_raw", relative_paths={ppt_path.relative_to(self.wiki / "companies").as_posix()}).errors == 0
                ppt_ref = reader.query_ref("urn:company-wiki:document:sha256:" + ppt_spec["sha256"],
                                          "urn:company-wiki:source:sha256:" + ppt_spec["sha256"], ppt_spec["sha256"])
                self.context["cases"][-1]["ppt_source_ref"] = asdict(ppt_ref)
        finally:
            catalog.close()
        request = {"schema_version": "2.0", "company_query": spec["security_id"], "market": spec["market"],
                   "document_kind": "annual_report", "fiscal_year": 2025, "mode": "exact", "as_of_date": self.spec["as_of_date"], "filing_intent": "reuse_only"}
        argv = [sys.executable, "-B", str(self.rf / "scripts/source_preparation.py"), "--company-wiki-config", str(self.ff_config),
                "--company-wiki-catalog-config", str(self.catalog_config), "--filing-fetch-root", str(self.ff), "--timeout-seconds", "45"]
        out, stderr, rc = self.command(argv, payload=request, expected=None, timeout=60)
        if rc != 0:
            self.set(case, "rf_ff_reuse", "BLOCKED", "real source preparation refused; no fixture success substituted", error=stderr.decode(errors="replace")[:1000])
        else:
            record = json.loads(out)
            assert record["reuse_receipt"]["download_calls"] == 0
            assert record["capture"]["snapshot_sha256"] == source["sha256"]
            trace = [json.loads(line) for p in self.process_log.glob("*.jsonl") for line in p.read_text(encoding="utf-8").splitlines()]
            assert any(any("fetch_filing.py" in str(a) for a in t["argv"]) for t in trace), "FF was not launched"
            self.set(case, "rf_ff_reuse", "PASS", "real RF/FF/CWP subprocesses; SourceRef v2; download_calls=0")

    def forecast_case(self, spec, directory):
        case, data = spec["case"], load(directory / "input.json")
        domain_checks(data, spec["expected"])
        self.set(case, "domain_boundaries", "PASS", "independently reviewed facts, targets, peer and pp boundaries")
        base = [sys.executable, "-B", str(self.rf / "scripts/revenue_forecast.py"), str(directory / "input.json")]
        self.command(base + ["--validate-only", "--verbose"])
        self.command(base + ["--output", str(directory / "new_forecast.json"), "--markdown", str(directory / "new_forecast.md")])
        result, old = load(directory / "new_forecast.json"), load(directory / "forecast.json")
        # Compare economic paths, not timestamp/registration signatures. Not a claim of predictive accuracy.
        assert result["consolidated_forecast"] == old["consolidated_forecast"], "economic paths changed"
        assert (directory / "new_forecast.md").stat().st_size > 1000
        self.set(case, "formal_forecast", "PASS", "validator + formal engine + generated Markdown; all scenario/year paths unchanged")
        arithmetic_checks(data, result)
        self.set(case, "arithmetic", "PASS", "independent segment bridge and sensitivity request recomputation")
        self.command([sys.executable, "-B", str(self.rf / "scripts/revenue_backtest.py"), "create", str(directory / "input.json"),
                      "--version", data["forecast_version"], "--output", str(directory / "new_snapshot.json")])
        self.command([sys.executable, "-B", str(REPO / "tools/cross_market_suite/rf_checks.py"),
                      "--runtime", str(self.rf), "--case-dir", str(directory)])
        again = self.command([sys.executable, "-B", str(self.rf / "scripts/revenue_backtest.py"), "create", str(directory / "input.json"),
                              "--version", data["forecast_version"], "--output", str(directory / "new_snapshot.json")], expected=None)
        assert again[2] != 0, "immutable snapshot overwritten"
        self.set(case, "snapshot_registry", "PASS", "new frozen snapshot, registered-artifact audit, tuple validation, overwrite rejected")
        # Deliberately vary Python hash seed: claims/floats must remain valid across processes.
        stable = True
        for seed in ("1", "2"):
            _, _, rc = self.command([sys.executable, "-B", str(REPO / "tools/cross_market_suite/rf_checks.py"),
                                     "--runtime", str(self.rf), "--case-dir", str(directory)],
                                    expected=None, env_override={"PYTHONHASHSEED": seed})
            stable = stable and rc == 0
        self.set(case, "process_seed_stability", "PASS" if stable else "FAIL",
                 "strong validation of the same artifact under hash seeds 0/1/2; no changed expectations")
        assert all(sha(directory / name) == digest for name, digest in spec["frozen_artifacts"].items())
        self.set(case, "old_snapshot_immutable", "PASS", "original input/forecast/snapshot bytes unchanged")

    def full(self):
        if self.args.suite != "full":
            return
        if self.args.et_root:
            self.command([sys.executable, "-B", str(REPO / "tests/e2e/run_ff_et_cwp_offline_acceptance.py"),
                          "--ff-root", str(self.ff), "--et-root", str(self.et)], timeout=120)
            self.set("ALL", "ff_et_cwp_contract", "PASS", "actual ET CLI/workers; HTTP-only fixture; untranslated text, dedup, timeout cleanup")
        context = self.root / "context.json"
        write_new(context, self.context)
        self.env["CWP_CMRF_CONTEXT"] = str(context)
        self.command([sys.executable, "-B", "-m", "pytest", str(REPO / "tests/e2e/test_cross_market_rf_pipeline.py"),
                      "-q", "-p", "no:cacheprovider", "--basetemp", str(self.root / "pytest"),
                      "--junitxml", str(self.root / "worker.xml"), "-o", "junit_family=legacy"], cwd=REPO, timeout=240, expected=None)
        import xml.etree.ElementTree as ET
        tree = ET.parse(self.root / "worker.xml")
        for test in tree.iter("testcase"):
            properties = {p.attrib["name"]: p.attrib.get("value") for p in test.findall("properties/property")}
            if "cmrf_case" not in properties:
                continue
            case = properties["cmrf_case"]
            evidence = runtime_properties(properties)
            format_key = properties.get("cmrf_format")
            if format_key:
                status = "FAIL" if test.find("failure") is not None or test.find("error") is not None else properties["cmrf_format_status"]
                self.set(case, format_key, status, properties.get("cmrf_format_detail", "format probe failed"), **evidence)
                continue
            if test.find("failure") is not None or test.find("error") is not None:
                self.set(case, "canonical_worker", "FAIL", "isolated real-byte Worker failed", test=test.attrib["name"], **evidence)
            elif test.find("skipped") is not None:
                self.set(case, "canonical_worker", "BLOCKED", "source format/capability not supported", test=test.attrib["name"], **evidence)
            else:
                receipt = json.loads(properties["cmrf_receipt"])
                self.set(case, "canonical_worker", "PASS", "real finite spawned Worker, loopback model only; selected business content, no translation, idempotent resume", **receipt, **evidence)
                self.set(case, "narrative_virtual_read", "PASS", "CWP/RF current NarrativeRef contents match and exact evidence lookup")
            self.set(case, "format_support", self.checks[case, "canonical_worker"]["status"],
                     "PDF tested" if case != "US-MSFT" else "TXT tested; HTML/PPTX are separate actual probes")

    def live(self):
        if self.args.mode != "live":
            return
        plan = REPO / "docs/plans/cross-market-rf-e2e-2026-10-08/executions"
        names = {"CN-688012": "requests/half2026_fetch.json", "HK-00700": "request_interim_2026_no_language.json", "US-MSFT": "request_fy2026_fetch.json"}
        for case, name in names.items():
            request = load(plan / case / name)
            # Live fees stay zero; entitled/subscribed providers must not bypass their budget contract.
            out, _, rc = self.command([sys.executable, "-B", str(self.ff / "scripts/fetch_filing.py"),
                                       "--config", str(self.ff_config), "--timeout-seconds", "180"], payload=request, timeout=195, expected=None)
            payload = json.loads(out)
            filing = payload.get("filing", {})
            if rc == 0 and filing.get("status") == "source_candidate":
                downloads = payload.get("downloads")
                assert downloads and downloads > 0, "missing source did not produce a real download"
                ref = filing["source_ref"]
                data, receipt, _ = self.command([sys.executable, "-B", "-m", "company_wiki.source_catalog.source_reader_cli",
                    "--config", str(self.catalog_config), "--document-id", ref["document_id"], "--source-id", ref["source_id"],
                    "--content-sha256", ref["content_sha256"]], binary=True)
                manifest = json.loads(receipt)["manifest"]
                assert hashlib.sha256(data).hexdigest() == ref["content_sha256"] and len(data) == ref["byte_size"]
                assert (manifest["market"], manifest["security_id"], manifest["fiscal_year"]) == (request["market"], request["company_query"], request["fiscal_year"])
                if request.get("fiscal_period"):
                    assert manifest["fiscal_period"] == request["fiscal_period"]
                second, _, rc2 = self.command([sys.executable, "-B", str(self.ff / "scripts/fetch_filing.py"), "--config", str(self.ff_config), "--timeout-seconds", "180"], payload=request, timeout=195, expected=None)
                repeated = json.loads(second)
                assert rc2 == 0 and repeated["filing"]["source_ref"] == filing["source_ref"]
                assert repeated.get("downloads") == 0
                self.set(case, "correct_provider_download", "PASS", "actual configured market adapter, verified new bytes/identity/year, second request zero download", envelope=payload)
                prepared, _, _ = self.command([sys.executable, "-B", str(self.rf / "scripts/source_preparation.py"),
                    "--company-wiki-config", str(self.ff_config), "--company-wiki-catalog-config", str(self.catalog_config),
                    "--filing-fetch-root", str(self.ff), "--timeout-seconds", "45"], payload=request, timeout=60)
                assert json.loads(prepared)["capture"]["snapshot_sha256"] == ref["content_sha256"]
            else:
                self.set(case, "correct_provider_download", "BLOCKED", "real configured provider did not complete; no manual bypass", envelope=payload)
            transcript = payload.get("transcript", {})
            if "companion_transcript" not in request:
                self.set(case, "transcript_live", "NOT_APPLICABLE", "this CN filing request has no earnings-call companion")
                continue
            # A missing filing must not hide the independent transcript capability.
            # Existing annual reuse triggers the REAL FF companion with the same exact call quarter.
            call_request = dict(request, fiscal_year=2025, fiscal_period=None, document_kind="annual_report", filing_intent="reuse_only")
            call_request.pop("acquisition_limits", None)
            call_request["companion_transcript"] = dict(request["companion_transcript"])
            call_request["companion_transcript"].update(intent="fetch_if_missing", provider="fmp",
                acquisition_limits={"max_bytes": 5 * 1024 * 1024, "timeout_seconds": 60, "max_cost_usd": "0.00"})
            before_pids = {json.loads(line)["pid"] for path in self.process_log.glob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()}
            call_out, _, _ = self.command([sys.executable, "-B", str(self.ff / "scripts/fetch_filing.py"), "--config", str(self.ff_config),
                                          "--timeout-seconds", "90"], payload=call_request, timeout=105, expected=None)
            transcript = json.loads(call_out).get("transcript", {})
            traces = [json.loads(line) for path in self.process_log.glob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()]
            tool_started = any(row["pid"] not in before_pids and any("transcript_tool.py" in str(arg) for arg in row["argv"]) for row in traces)
            if transcript.get("status") == "source_candidate":
                ref = transcript["source_ref"]
                data, _, _ = self.command([sys.executable, "-B", "-m", "company_wiki.source_catalog.source_reader_cli",
                    "--config", str(self.catalog_config), "--document-id", ref["document_id"], "--source-id", ref["source_id"],
                    "--content-sha256", ref["content_sha256"], "--purpose", "narrative_derivation"], binary=True)
                assert hashlib.sha256(data).hexdigest() == ref["content_sha256"]
                status = "PASS"
            else:
                status = "BLOCKED" if tool_started else "NOT_RUN"
            self.set(case, "transcript_live", status, "actual FF companion; tool start/provider calls/reason separate from filing outcome",
                     transcript=transcript, et_tool_started=tool_started)

    def result(self):
        for path, before in self.protected.items():
            assert ((sha(path), path.stat().st_size, path.stat().st_mtime_ns) if path.is_file() else None) == before, f"read-only input changed: {path.name}"
        final_bytes = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())
        assert final_bytes <= 256 * 1024 * 1024, "test storage exceeds 256 MiB budget"
        return {"schema_version": "cross-market-report/1", "mode": self.args.mode, "suite": self.args.suite,
                "spec_sha256": sha(SPEC), "checkpoints_sha256": sha(POINTS), "versions": self.versions,
                "normalization_policy": self.normalization_policy,
                "checks": list(self.checks.values()), "commands": self.commands,
                "subprocesses": [json.loads(line) for path in self.process_log.glob("*.jsonl")
                                 for line in path.read_text(encoding="utf-8").splitlines()],
                "test_tree_final_bytes_before_cleanup": final_bytes,
                "external_model_calls": 0, "project_llm_cost_usd": 0, "replay_python_hashseed": "0",
                "semantic_review": "frozen independent review; fresh model outputs not independently researched"}


def markdown(report):
    lines = ["# 三市場固定回归", "", f"模式：{report['mode']} / {report['suite']}；总体：{report['status']}", "",
             "| 公司 | 检查点 | 状态 | 说明 |", "|---|---|---|---|"]
    lines.extend(f"| {r['case']} | {r['id']} | {r['status']} | {r['detail'].replace('|', '/').replace(chr(10), ' ')} |" for r in report["checks"])
    lines += ["", "离线 HTTP 回放不能证明真实供应商可用；固定模型重放不能证明新一轮研究和预测准确。"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("--before", type=Path, required=True)
    compare.add_argument("--after", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    run = sub.add_parser("run")
    pack = sub.add_parser("pack", help="explicit one-copy portable frozen data bundle, never added to Git")
    for name in ("rf-root", "ff-root", "delivery-root", "output"):
        run.add_argument("--" + name, type=Path, required=True)
    run.add_argument("--source-catalog-config", type=Path, default=REPO / "config/source_catalog.yaml")
    pack.add_argument("--delivery-root", type=Path, required=True)
    pack.add_argument("--source-catalog-config", type=Path, default=REPO / "config/source_catalog.yaml")
    pack.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--et-root", type=Path)
    run.add_argument("--mode", choices=("replay", "live"), default="replay")
    run.add_argument("--suite", choices=("core", "full"), default="full")
    run.add_argument("--acquisition-config", type=Path)
    args = parser.parse_args()
    if args.command == "compare":
        result = compare_reports(load(args.before), load(args.after))
        write_new(args.output, result)
        print(json.dumps({"comparable": result["comparable"], "changes": dict(Counter(r["change"] for r in result["changes"])),
                          "output": str(args.output.resolve())}, ensure_ascii=False))
        return 0 if result["comparable"] and not any(r["change"] in {"regressed", "missing"} for r in result["changes"]) else 1
    if args.command == "pack":
        args.delivery_root, args.source_catalog_config = args.delivery_root.resolve(), args.source_catalog_config.resolve()
        target = args.output_dir.resolve()
        if target.exists():
            parser.error("portable bundle destination must be absent")
        # Data copies are explicit and hash-addressed once; source DB/credentials are not copied.
        args.mode, args.suite = "replay", "core"
        with isolated_directory() as root:
            suite = Suite(args, root)
            target.mkdir(parents=True)
            try:
                for case in suite.spec["cases"]:
                    for name, digest in case["frozen_artifacts"].items():
                        source = safe_child(args.delivery_root, case["case"] + "/" + name)
                        assert sha(source) == digest
                        dest = safe_child(target, case["case"] + "/" + name)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, dest)
                    for source in case["sources"]:
                        data = suite.raw(source)
                        dest = target / "objects" / source["sha256"][:2] / source["sha256"]
                        if not dest.exists():
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(data)
                old = load(REPO / "docs/plans/cross-market-rf-e2e-2026-10-08/existing_narrative_current_vs_asof.json")
                ref = old["checks"][0]["request"]["narrative_ref"]["source_ref"]
                data = suite.raw({"source_ref": ref, "sha256": ref["content_sha256"], "read_purpose": "narrative_derivation"})
                dest = target / "objects" / ref["content_sha256"][:2] / ref["content_sha256"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                files = {p.relative_to(target).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size}
                         for p in target.rglob("*") if p.is_file()}
                write_new(target / "bundle.json", {"schema_version": "cross-market-data/1", "spec_sha256": sha(SPEC), "files": files})
            except BaseException:
                # This exact new target contains only copies; no preexisting path can be deleted.
                assert target == args.output_dir.resolve() and not target.is_symlink()
                shutil.rmtree(target)
                raise
        print(json.dumps({"bundle": str(target), "files": len(files), "bytes": sum(p["bytes"] for p in files.values())}))
        return 0
    for name in ("rf_root", "ff_root", "delivery_root", "source_catalog_config", "output", "et_root", "acquisition_config"):
        if getattr(args, name, None) is not None:
            setattr(args, name, getattr(args, name).resolve())
    if args.output.exists() or args.output.with_suffix(".md").exists():
        parser.error("output exists; choose a fresh immutable run name")
    if args.mode == "live" and not args.acquisition_config:
        parser.error("live requires an explicit copied acquisition config; no default production downloads")
    if args.suite == "full" and not args.et_root:
        parser.error("full requires --et-root for cross-repository contract")
    report, suite, root = {}, None, None
    started = time.monotonic()
    try:
        with isolated_directory() as root:
            assert not args.output.is_relative_to(root), "report must survive scratch cleanup"
            suite = Suite(args, root)
            suite.setup()
            for case in suite.spec["cases"]:
                suite.case(case)
            suite.full()
            suite.live()
            report = suite.result()
    except Exception as exc:
        report = {"schema_version": "cross-market-report/1", "mode": args.mode, "suite": args.suite,
                  "spec_sha256": sha(SPEC), "checkpoints_sha256": sha(POINTS),
                  "checks": list(suite.checks.values()) if suite else [],
                  "commands": suite.commands if suite else [], "harness_error": str(exc)[:2000]}
    clean = root is not None and not root.exists()
    checks = report["checks"]
    isolation = next((r for r in checks if r["case"] == "ALL" and r["id"] == "isolation_cleanup"), None)
    if isolation is not None:
        isolation.update(status="PASS" if clean and "harness_error" not in report else "FAIL",
                         detail="owned temporary tree removed and protected input hashes unchanged" if clean else "cleanup incomplete")
    report.update(test_root_restored_absent=clean, seconds=round(time.monotonic() - started, 3))
    report["status"] = "FAIL" if "harness_error" in report else summarize(checks)
    write_new(args.output, report)
    args.output.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(args.output.resolve()), "seconds": report["seconds"], "cleanup": clean}))
    return 1 if report["status"] == "FAIL" else 2 if report["status"] == "PARTIAL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
