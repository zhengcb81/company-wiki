"""Idempotent, recoverable ASCII-path deployment of the selected PDF runtime.

The tool only ever projects an already-authorized source deployment: it freezes
the closure resolved by the existing ``pdf-runtime-closure/2`` resolver, links
every selected file by same-volume NTFS hardlink (zero SDK/model byte copies),
emits a ``pdf-paragraph-runtime/2`` config whose only changes are the ASCII
``python``/``artifacts`` paths, and verifies the real production entry. No
approval gates, no license chain, no implicit environment discovery.
"""
from __future__ import annotations

import base64
from hashlib import new as new_hash, sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable

TOOL_NAME = "pdf_runtime_deployment"
DEPLOYMENT_SCHEMA = "pdf-runtime-deployment/1"
PLAN_SCHEMA = "pdf-runtime-deployment-plan/1"
RECEIPT_NAME = "deployment.json"
CONFIG_NAME = "paragraph-runtime.config.json"
ENV_DIRNAME = "env"
ARTIFACTS_DIRNAME = "artifacts"
SUPPORTED_SOURCE_SCHEMA = "pdf-paragraph-runtime/2"

VENV_TIMEOUT_SECONDS = 300
PROBE_TIMEOUT_SECONDS = 300
CONSTRUCTOR_DEADLINE_SECONDS = 30

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]


class DeploymentError(RuntimeError):
    """Explicit, actionable deployment failure."""


class TargetConflict(DeploymentError):
    """The target holds content this tool does not own; nothing was modified."""


class SourceChanged(DeploymentError):
    """A selected source byte changed after its snapshot; nothing was linked."""


def implementation_sha256() -> str:
    return sha256((_HERE / "deployment.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def require_ascii(path: Path) -> None:
    """The deployment fix is a real ASCII resource tree; aliases do not count."""
    if any(ord(char) > 127 for char in str(path)):
        raise DeploymentError(f"deployment target must be pure ASCII: {path!s}")


def require_base_python(expected_base_prefix: str, *, prefix: str, base_prefix: str) -> None:
    """The venv module must run from the same base interpreter as the source."""
    if os.path.normcase(prefix) != os.path.normcase(base_prefix) or (
        os.path.normcase(base_prefix) != os.path.normcase(expected_base_prefix)
    ):
        raise DeploymentError(
            f"run this command with the base interpreter {expected_base_prefix!s} "
            f"(got prefix={prefix!s}, base={base_prefix!s})")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _rel_posix(relative: str) -> PurePosixPath:
    return PurePosixPath(relative.replace("\\", "/"))


def _safe_relative(relative: str) -> bool:
    pure = _rel_posix(relative)
    return (bool(relative) and "\x00" not in relative and not pure.is_absolute()
            and ".." not in pure.parts and ":" not in relative)


def _declared_hash_matches(path: Path, declared: str) -> bool | None:
    """RECORD digest check; None when the declared algorithm is unknown here."""
    algorithm, _, encoded = declared.partition("=")
    try:
        if algorithm == "sha256":
            observed = bytes.fromhex(_sha256_file(path))
        else:
            hasher = new_hash(algorithm)
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    hasher.update(block)
            observed = hasher.digest()
    except (ValueError, OSError):
        return None
    expected = base64.urlsafe_b64encode(observed).rstrip(b"=").decode()
    return expected == encoded.rstrip("=")


def plan_digest(plan: dict[str, Any]) -> str:
    """Frozen integrity digest over everything except the digest itself."""
    return sha256(_canonical({key: value for key, value in plan.items()
                              if key != "plan_sha256"})).hexdigest()


def build_plan(target: Path, source_profile: dict[str, Any], probe: dict[str, Any], *,
               source_config_sha256: str | None = None) -> dict[str, Any]:
    """Freeze the projection plan from a describe-probe result. Read-only."""
    target = Path(target)
    require_ascii(target)
    if source_profile.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise DeploymentError(f"source config must be {SUPPORTED_SOURCE_SCHEMA}")
    if source_profile.get("environment_algorithm") != probe["closure"].get("environment_algorithm"):
        raise DeploymentError("source config and probe disagree on the environment algorithm")
    if os.path.normcase(source_profile["python"]) != os.path.normcase(probe["python"]):
        raise DeploymentError("source config python and probe python disagree")
    site = Path(probe["site_packages"])
    if not site.is_dir():
        raise DeploymentError(f"source site-packages is missing: {site!s}")
    if os.path.normcase(Path(target).drive) != os.path.normcase(site.drive):
        raise DeploymentError("hardlink projection requires the target on the same NTFS volume "
                              f"as {site!s}; refusing a silent copy")
    artifacts_source = Path(source_profile["artifacts"])
    if not artifacts_source.is_dir():
        raise DeploymentError(f"source model artifacts are missing: {artifacts_source!s}")
    if os.path.normcase(artifacts_source.drive) != os.path.normcase(Path(target).drive):
        raise DeploymentError("model hardlink projection requires the target on the same "
                              f"NTFS volume as {artifacts_source!s}; refusing a silent copy")

    env_rows: dict[str, dict[str, Any]] = {}
    owners: dict[str, list[str]] = {}
    deviations: list[dict[str, Any]] = []
    blocking: list[dict[str, Any]] = []
    hooks: list[dict[str, Any]] = []
    site_hooks: list[str] = []
    missing_unhashed_bytecode = 0
    distributions_summary = []
    for item in probe["closure"]["distributions"]:
        name = item["name"]
        entry = probe["distributions"].get(name)
        if entry is None:
            blocking.append({"kind": "probe_missing_distribution", "distribution": name})
            continue
        record_path = Path(entry["path"]) / "RECORD"
        if _sha256_file(record_path) != entry["record_sha256"]:
            blocking.append({"kind": "record_changed_since_probe", "distribution": name})
        distributions_summary.append({"name": name, "version": entry["version"],
                                      "record_sha256": entry["record_sha256"],
                                      "record_entries": len(entry["record"])})
        for relative, declared, declared_size in entry["record"]:
            if not _safe_relative(relative):
                blocking.append({"kind": "invalid_record_path", "distribution": name, "path": relative})
                continue
            pure = _rel_posix(relative)
            source = site.joinpath(*pure.parts).resolve()
            if not source.is_relative_to(site.resolve()):
                blocking.append({"kind": "escaping_record_path", "distribution": name, "path": relative})
                continue
            target_relative = "env/Lib/site-packages/" + pure.as_posix()
            if not source.is_file():
                if source.suffix.lower() in {".pyc", ".pyo"} and not declared and not declared_size:
                    missing_unhashed_bytecode += 1
                    continue
                blocking.append({"kind": "missing_record_source", "distribution": name, "path": relative})
                continue
            if declared_size and source.stat().st_size != int(declared_size):
                deviations.append({"kind": "record_size_mismatch", "distribution": name,
                                   "path": relative, "declared": int(declared_size),
                                   "actual": source.stat().st_size})
            if declared and _declared_hash_matches(source, declared) is False:
                deviations.append({"kind": "record_hash_mismatch", "distribution": name, "path": relative})
            key = target_relative.lower()
            row = {"target": target_relative, "source": str(source),
                   "sha256": _sha256_file(source), "bytes": source.stat().st_size, "owner": name}
            if key in env_rows:
                if (env_rows[key]["sha256"] != row["sha256"]
                        or os.path.normcase(env_rows[key]["source"]) != os.path.normcase(row["source"])):
                    blocking.append({"kind": "selected_record_conflict", "path": target_relative,
                                     "owners": owners[key] + [name]})
                owners[key].append(name)
                continue
            env_rows[key], owners[key] = row, [name]
            if pure.suffix.lower() == ".pth":
                lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
                if any(line.strip() and not line.lstrip().startswith("#") for line in lines):
                    hooks.append({"path": target_relative, "lines": lines})
            if pure.name in {"sitecustomize.py", "usercustomize.py"}:
                site_hooks.append(target_relative)

    artifact_rows = []
    for path in sorted(artifacts_source.rglob("*")):
        if path.is_file():
            artifact_rows.append({"target": f"{ARTIFACTS_DIRNAME}/" + path.relative_to(artifacts_source).as_posix(),
                                  "source": str(path), "sha256": _sha256_file(path),
                                  "bytes": path.stat().st_size})
    weights = artifacts_source / "model.safetensors"
    config_json = artifacts_source / "config.json"
    if _sha256_file(weights) != source_profile["model_sha256"] or (
        _sha256_file(config_json) != source_profile["model_config_sha256"]
    ):
        raise DeploymentError("source profile model SHAs do not describe the actual artifacts")

    plan = {
        "schema_version": PLAN_SCHEMA,
        "tool": {"name": TOOL_NAME, "implementation_sha256": implementation_sha256()},
        "target": str(target),
        "source": {"config_sha256": source_config_sha256, "python": probe["python"],
                   "prefix": probe["prefix"], "base_prefix": probe["base_prefix"],
                   "site_packages": str(site), "artifacts": str(artifacts_source)},
        "closure": probe["closure"],
        "environment_sha256": probe["closure"]["environment_sha256"],
        "distribution_summary": sorted(distributions_summary, key=lambda row: str(row["name"])),
        "env_rows": sorted(env_rows.values(), key=lambda row: str(row["target"])),
        "artifact_rows": sorted(artifact_rows, key=lambda row: str(row["target"])),
        "diagnostics": {"record_deviations": sorted(deviations, key=lambda row: (str(row["kind"]), str(row["path"]))),
                        "missing_unhashed_bytecode": missing_unhashed_bytecode,
                        "active_pth_hooks": sorted(hooks, key=lambda row: str(row["path"])),
                        "site_hooks": sorted(site_hooks)},
        "blocking_errors": sorted(blocking, key=lambda row: (str(row["kind"]), str(row.get("path", "")))),
        "source_profile": source_profile,
        "output_config": {"config_name": CONFIG_NAME, "path": str(target / CONFIG_NAME)},
        "same_volume": True,
    }
    plan["plan_sha256"] = plan_digest(plan)
    return plan


def load_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate a plan dict, including its frozen integrity digest."""
    if plan.get("schema_version") != PLAN_SCHEMA:
        raise DeploymentError(f"plan schema must be {PLAN_SCHEMA}")
    if plan.get("plan_sha256") != plan_digest(plan):
        raise DeploymentError("plan integrity digest mismatch")
    for row in (*plan["env_rows"], *plan["artifact_rows"]):
        if not _safe_relative(row["target"]):
            raise DeploymentError(f"unsafe plan row target: {row['target']!s}")
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) or type(row["bytes"]) is not int:
            raise DeploymentError(f"invalid plan row digest: {row['target']!s}")
        if not Path(row["source"]).is_absolute():
            raise DeploymentError(f"plan row source must be absolute: {row['target']!s}")
    return plan


def tool_identity() -> dict[str, str]:
    return {"name": TOOL_NAME, "implementation_sha256": implementation_sha256()}


def receipt_stub(plan: dict[str, Any], status: str) -> dict[str, Any]:
    return {"schema_version": DEPLOYMENT_SCHEMA, "tool": tool_identity(),
            "plan_sha256": plan["plan_sha256"], "status": status, "target": plan["target"],
            "environment_sha256": plan["environment_sha256"],
            "distribution_count": len(plan["distribution_summary"]),
            "source_config_sha256": plan["source"]["config_sha256"]}


def write_receipt(target: Path, receipt: dict[str, Any]) -> None:
    """Atomic-enough marker write inside the owned tree only."""
    destination = target / RECEIPT_NAME
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target,
                                         prefix="receipt-", suffix=".tmp", delete=False)
    try:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.close()
        os.replace(handle.name, destination)
    except BaseException:
        handle.close()
        Path(handle.name).unlink(missing_ok=True)
        raise


def _read_receipt(target: Path) -> dict[str, Any] | None:
    path = target / RECEIPT_NAME
    if not path.is_file():
        return None
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (not isinstance(receipt, dict) or receipt.get("schema_version") != DEPLOYMENT_SCHEMA
            or receipt.get("tool", {}).get("name") != TOOL_NAME):
        return None
    return receipt


def classify_target(target: Path, plan_sha256: str) -> str:
    """ABSENT/EMPTY/OWNED_COMPLETE/OWNED_INCOMPLETE/FOREIGN; never guesses."""
    if not target.exists():
        return "ABSENT"
    if target.is_dir() and not any(target.iterdir()):
        return "EMPTY"
    receipt = _read_receipt(target)
    if receipt is None or receipt.get("plan_sha256") != plan_sha256:
        return "FOREIGN"
    return "OWNED_COMPLETE" if receipt.get("status") == "COMPLETE" else "OWNED_INCOMPLETE"


def snapshot_tree(root: Path) -> dict[str, Any]:
    """Count/bytes/mtime summary proving zero writes across a light recheck."""
    digest = sha256()
    files = total = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            info = path.stat()
            files += 1
            total += info.st_size
            digest.update(json.dumps([path.relative_to(root).as_posix(), info.st_size,
                                      info.st_mtime_ns], separators=(",", ":")).encode())
    return {"files": files, "bytes": total, "state_sha256": digest.hexdigest()}


def _default_venv_runner(host_python: str, env_path: Path) -> None:
    created = subprocess.run([host_python, "-B", "-I", "-m", "venv", "--without-pip",
                              "--copies", str(env_path)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=VENV_TIMEOUT_SECONDS)
    if created.returncode != 0:
        raise DeploymentError("venv creation failed: "
                              + created.stderr.decode("utf-8", "replace")[-2000:])


def _default_link(source: Path, destination: Path) -> None:
    os.link(source, destination)
    if not os.path.samefile(source, destination):
        raise DeploymentError(f"projected file is not a hardlink of its source: {destination!s}")


def _scaffold_bytes(env_path: Path, plan: dict[str, Any]) -> int:
    planned = {row["target"][len(ENV_DIRNAME) + 1:].lower() for row in plan["env_rows"]}
    prefix = env_path.as_posix().lower().rstrip("/") + "/"
    return sum(path.stat().st_size for path in env_path.rglob("*") if path.is_file()
               and path.as_posix().lower()[len(prefix):] not in planned)


def _expected_config_bytes(plan: dict[str, Any], python: str) -> bytes:
    emitted = {**plan["source_profile"], "python": python,
               "artifacts": str(Path(plan["target"]) / ARTIFACTS_DIRNAME)}
    return (json.dumps(emitted, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _reconcile(plan: dict[str, Any], *, link: Callable[[Path, Path], None],
               created: dict[str, int]) -> None:
    """Link missing rows; keep byte-identical owned files; never overwrite."""
    target = Path(plan["target"])
    for row in (*plan["env_rows"], *plan["artifact_rows"]):
        source, destination = Path(row["source"]), target.joinpath(*_rel_posix(row["target"]).parts)
        if not source.is_file() or _sha256_file(source) != row["sha256"] or (
            source.stat().st_size != row["bytes"]
        ):
            raise SourceChanged(f"selected source changed after its snapshot: {row['target']}")
        if destination.exists():
            if _sha256_file(destination) == row["sha256"]:
                created["reused"] += 1
                continue
            raise TargetConflict(f"owned path holds different content: {row['target']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            link(source, destination)
        except DeploymentError:
            raise
        except BaseException as failure:
            raise DeploymentError(f"linking failed at {row['target']}: {failure}") from failure
        if not destination.is_file() or _sha256_file(destination) != row["sha256"]:
            raise DeploymentError(f"projected file content mismatch: {row['target']}")
        created["made"] += 1


def deploy(plan: dict[str, Any], *, host_python: str,
           venv_runner: Callable[[str, Path], None] | None = None,
           link: Callable[[Path, Path], None] | None = None) -> dict[str, Any]:
    """Create/recover/reuse one owned ASCII deployment. Never touches sources."""
    plan = load_plan(plan)
    venv_runner = venv_runner or _default_venv_runner
    link = link or _default_link
    target = Path(plan["target"])
    require_ascii(target)
    started = time.monotonic()
    classification = classify_target(target, plan["plan_sha256"])
    if classification == "FOREIGN":
        raise TargetConflict(
            f"target exists and is not this tool's deployment for plan {plan['plan_sha256']}: {target!s}; "
            "choose another explicitly owned ASCII target")
    if classification == "ABSENT":
        target.mkdir(parents=True)
        classification = "EMPTY"
    counters = {"made": 0, "reused": 0}
    receipt: dict[str, Any]
    try:
        if classification == "OWNED_COMPLETE" and _reconcile_fully_consistent(plan):
            receipt = {**receipt_stub(plan, "REUSED"),
                       "created_links": 0,
                       "reused_links": len(plan["env_rows"]) + len(plan["artifact_rows"]),
                       "sdk_bytes_copied": 0, "model_bytes_copied": 0,
                       "seconds": round(time.monotonic() - started, 3)}
            return receipt
        env_path = target / ENV_DIRNAME
        python_exe = env_path / "Scripts" / "python.exe"
        venv_created = False
        if not (python_exe.is_file() and (env_path / "pyvenv.cfg").is_file()):
            try:
                venv_runner(host_python, env_path)
            except DeploymentError:
                raise
            except BaseException as failure:
                raise DeploymentError(f"venv creation failed: {failure}") from failure
            venv_created = True
        pyvenv = (env_path / "pyvenv.cfg").read_text(encoding="utf-8")
        if "include-system-site-packages = false" not in pyvenv:
            raise DeploymentError("deployed venv must not include system site-packages")
        scaffold = _scaffold_bytes(env_path, plan)
        _reconcile(plan, link=link, created=counters)
        config_path = Path(plan["output_config"]["path"])
        expected_config = _expected_config_bytes(plan, str(python_exe))
        if config_path.exists() and config_path.read_bytes() != expected_config:
            raise TargetConflict("owned config content was modified externally")
        if not config_path.exists():
            config_path.write_bytes(expected_config)
        receipt = {**receipt_stub(plan, "COMPLETE"),
                   "created_links": counters["made"], "reused_links": counters["reused"],
                   "venv_created": venv_created,
                   "new_scaffold_file_bytes": scaffold,
                   "logical_shared_bytes": sum(row["bytes"] for row in
                                               (*plan["env_rows"], *plan["artifact_rows"])),
                   "sdk_bytes_copied": 0, "model_bytes_copied": 0,
                   "output_config_sha256": sha256(expected_config).hexdigest(),
                   "diagnostic_counts": {
                       "record_deviations": len(plan["diagnostics"]["record_deviations"]),
                       "missing_unhashed_bytecode": plan["diagnostics"]["missing_unhashed_bytecode"],
                       "active_pth_hooks": len(plan["diagnostics"]["active_pth_hooks"]),
                       "site_hooks": len(plan["diagnostics"]["site_hooks"])},
                   "seconds": round(time.monotonic() - started, 3)}
    except BaseException as failure:
        failure_receipt = {**receipt_stub(plan, "INCOMPLETE"),
                           "error_type": type(failure).__name__, "error": str(failure)[:2000],
                           "created_links": counters["made"], "reused_links": counters["reused"],
                           "seconds": round(time.monotonic() - started, 3)}
        try:
            write_receipt(target, failure_receipt)
        except OSError:
            pass
        raise
    write_receipt(target, receipt)
    return receipt


def _reconcile_fully_consistent(plan: dict[str, Any]) -> bool:
    """Zero-write reuse check: every owned file exactly where the plan put it."""
    target = Path(plan["target"])
    for row in (*plan["env_rows"], *plan["artifact_rows"]):
        destination = target.joinpath(*_rel_posix(row["target"]).parts)
        if not destination.is_file() or _sha256_file(destination) != row["sha256"]:
            return False
    config_path = Path(plan["output_config"]["path"])
    python_exe = target / ENV_DIRNAME / "Scripts" / "python.exe"
    if not config_path.is_file() or config_path.read_bytes() != _expected_config_bytes(plan, str(python_exe)):
        return False
    return True


_PROBE_ENV_NAMES = ("APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "PATH",
                    "PATHEXT", "PROGRAMDATA", "SYSTEMDRIVE", "SYSTEMROOT", "USERNAME",
                    "USERPROFILE", "WINDIR")


def _probe_env(**updates: str) -> dict[str, str]:
    # Probe-only sanitized environment. The production child environment stays
    # owned by narrative_pdf_enhancement.child_environment.
    env = {name: os.environ[name] for name in _PROBE_ENV_NAMES if name in os.environ}
    env.update(PYTHONNOUSERSITE="1", PYTHONUTF8="1", **updates)
    return env


def _run_probe(python: str, arguments: list[str], *, timeout: float) -> dict[str, Any]:
    completed = subprocess.run([python, "-B", "-I", str(_HERE / "_describe_probe.py"), *arguments],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_probe_env(),
                               timeout=timeout)
    if completed.returncode != 0:
        raise DeploymentError("describe probe failed: "
                              + completed.stderr.decode("utf-8", "replace")[-2000:])
    return json.loads(completed.stdout.decode("utf-8"))


def describe_source(source_config: Path, *, repo_src: Path,
                    timeout: float = PROBE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Run the metadata-only closure probe inside the source interpreter."""
    config = json.loads(Path(source_config).read_text(encoding="utf-8-sig"))
    return _run_probe(config["python"], ["--mode", "source", "--repo-src", str(repo_src),
                                         "--config", str(source_config)], timeout=timeout)


def verify_light(config_path: Path, *, repo_src: Path,
                 timeout: float = PROBE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Fresh deployed interpreter: closure identity + isolation + zero SDK."""
    config_path = Path(config_path)
    target = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    receipt = _read_receipt(target)
    if receipt is None:
        raise DeploymentError("verify requires this tool's deployment receipt in the target")
    site_packages = target / ENV_DIRNAME / "Lib" / "site-packages"
    expected = {"environment_sha256": config["environment_sha256"],
                "distribution_count": receipt["distribution_count"],
                "target_site": str(site_packages)}
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
    try:
        json.dump(expected, handle)
        handle.close()
        observation = _run_probe(config["python"],
                                 ["--mode", "verify", "--repo-src", str(repo_src),
                                  "--config", str(config_path), "--expected", handle.name],
                                 timeout=timeout)
    finally:
        Path(handle.name).unlink(missing_ok=True)
    if observation["environment_sha256"] != receipt["environment_sha256"]:
        raise DeploymentError("deployed environment digest differs from the deployment receipt")
    return observation


_CONFIG_LOAD_SCRIPT = (
    "import json, os, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "os.environ['COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG'] = sys.argv[2]\n"
    "from company_wiki.source_catalog.narrative_pdf_enhancement import configured_paragraph_runtime\n"
    "selected = configured_paragraph_runtime()\n"
    "assert selected is not None, 'explicit config must select'\n"
    "bound = selected.config\n"
    "print(json.dumps({'status': 'PASS', 'python': bound.python, 'artifacts': bound.artifacts,\n"
    "    'environment_algorithm': bound.environment_algorithm,\n"
    "    'environment_sha256': bound.environment_sha256,\n"
    "    'docling_version': bound.docling_version, 'max_seconds': bound.max_seconds,\n"
    "    'max_pages': bound.max_pages, 'model_sha256': bound.model_sha256}))\n"
)


def verify_config_load(config_path: Path, *, repo_src: Path, python: str | None = None,
                       timeout: float = 120) -> dict[str, Any]:
    """Production ``configured_paragraph_runtime`` loads the emitted config."""
    config_path = Path(config_path)
    raw = json.loads(config_path.read_text(encoding="utf-8-sig"))
    completed = subprocess.run([python or sys.executable, "-B", "-I", "-c", _CONFIG_LOAD_SCRIPT,
                                str(repo_src), str(config_path)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=_probe_env(COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG=str(config_path)),
                               timeout=timeout)
    if completed.returncode != 0:
        raise DeploymentError("production config load failed: "
                              + completed.stderr.decode("utf-8", "replace")[-2000:])
    observation = json.loads(completed.stdout.decode("utf-8"))
    if (observation["environment_sha256"] != raw["environment_sha256"]
            or observation["python"] != raw["python"] or observation["artifacts"] != raw["artifacts"]):
        raise DeploymentError("production config load does not match the emitted config")
    return observation


def constructor_probe(python: str, artifacts: str, *,
                      timeout: float = CONSTRUCTOR_DEADLINE_SECONDS) -> dict[str, Any]:
    """No-document SDK constructor through the deployed interpreter, capped."""
    completed = subprocess.run([python, "-I", "-X", "utf8",
                                str(_HERE / "_constructor_probe.py"), artifacts],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=_probe_env(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1"),
                               timeout=timeout)
    if completed.returncode != 0:
        raise DeploymentError("no-document constructor failed: "
                              + completed.stderr.decode("utf-8", "replace")[-4000:])
    return json.loads(completed.stdout.decode("utf-8"))
