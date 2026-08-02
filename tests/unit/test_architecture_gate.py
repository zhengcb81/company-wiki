
from architecture_gate import evaluate_architecture


def rule(rule_id, kind, glob, regex, **extra):
    return {"id": rule_id, "kind": kind, "glob": glob, "regex": regex, **extra}


def test_required_regex_rejects_missing_canonical_import(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "scheduler.py").write_text("from legacy import run\n", encoding="utf-8")
    config = {
        "schema_version": 1,
        "rules": [
            rule("canonical", "required_regex", "scripts/scheduler.py", r"import company_wiki")
        ],
    }
    result = evaluate_architecture(tmp_path, config)
    assert result["result"] == "fail"
    assert result["violations"][0]["id"] == "canonical"


def test_forbidden_regex_rejects_constant_success_drill(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "deployment.py").write_text(
        "def _drill_interrupt_recovery(self):\n    return True\n", encoding="utf-8"
    )
    config = {
        "schema_version": 1,
        "rules": [rule("drill", "forbidden_regex", "src/deployment.py", r"return\s+True")],
    }
    result = evaluate_architecture(tmp_path, config)
    assert result["result"] == "fail"
    assert result["violations"][0]["matches"][0]["line"] == 2


def test_max_matches_enforces_direct_writer_budget(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "writer.py").write_text("path.write_text('x')\n", encoding="utf-8")
    config = {
        "schema_version": 1,
        "rules": [
            rule(
                "writers",
                "max_regex_matches",
                "scripts/**/*.py",
                r"\.write_text\(",
                max_matches=0,
            )
        ],
    }
    result = evaluate_architecture(tmp_path, config)
    assert result["result"] == "fail"
    assert result["violations"][0]["actual"] == 1


def test_excluded_tool_writer_does_not_fail_rule(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "gate.py").write_text("path.write_text('receipt')\n", encoding="utf-8")
    config = {
        "schema_version": 1,
        "rules": [
            rule(
                "writers",
                "max_regex_matches",
                "scripts/**/*.py",
                r"\.write_text\(",
                max_matches=0,
                exclude=["scripts/gate.py"],
            )
        ],
    }
    result = evaluate_architecture(tmp_path, config)
    assert result["result"] == "pass"
