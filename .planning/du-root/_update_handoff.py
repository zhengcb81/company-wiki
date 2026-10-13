"""Add the merge-phase integration findings to the ROOT handoff.

The handoff was written before the lane-merge pass finished, so it does not record the
three defects that only appear once the lanes are composed into one chain.
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / ".planning" / "du-root" / "handoff.json"

MERGE_FINDINGS = [
    {
        "defect": "routing-was-a-no-op-in-the-orchestrator",
        "symptom": (
            "build_dependency_packages read route['section_priorities'], but that key lives "
            "on the profile returned by get_profile(route['profile_id']); route_document does "
            "not return it. Every document therefore received the same generic priority order "
            "and routing had no effect on reading order. Nothing failed."
        ),
        "fix": (
            "build_dependency_packages accepts profile= and _role_priority prefers the profile "
            "while still accepting a route; locked by tests/unit/document_understanding_root/"
            "test_du_root_lane_seam.py."
        ),
    },
    {
        "defect": "lane-fixture-module-name-collision-breaks-combined-collection",
        "symptom": (
            "The structure lane prepended its fixture directory to sys.path and imported a bare "
            "module named 'fixtures'. The repository also has tests/fixtures on sys.path, so "
            "running the DU suites in ONE pytest invocation (which is what CI does) failed at "
            "collection: ImportError: cannot import name 'available_inputs' from 'fixtures'. "
            "Each lane passed when run alone."
        ),
        "fix": (
            "Renamed the module to the unique tests/fixtures/document_understanding_structure/"
            "du_structure_fixtures.py and import it by that name."
        ),
    },
    {
        "defect": "repo-root-path-wrong-in-four-test-modules",
        "symptom": (
            "tests/unit/<lane>/test_*.py computed REPO as Path(__file__).parents[2], which is "
            "<repo>/tests and not <repo>. The bindings file was therefore never found and the "
            "real-original node reported 10 SKIPPED instead of running -- an honest but "
            "misleading green."
        ),
        "fix": (
            "Changed to parents[3] in the four ROOT modules. The real-original node now runs "
            "and passes (10 passed, plus the legacy-vs-new comparison). NOTE: the structure "
            "lane's own FIXTURE_ROOT uses parents[2]/'fixtures'/... at the same depth and is "
            "CORRECT; it must not be changed."
        ),
    },
]

TESTS_NOT_RUN_ADDITION = (
    "Paid model summary fidelity and cross-company G4/G5 acceptance (parent plan scope; the "
    "layer is not wired into the production parse/select entry point)."
)


def main() -> int:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    data["merge_phase_findings"] = MERGE_FINDINGS
    data["tests_not_run"] = list(data.get("tests_not_run", [])) + [TESTS_NOT_RUN_ADDITION]
    data["combined_invocation"] = (
        "pytest tests/unit/document_understanding_profiles tests/unit/document_understanding_"
        "structure tests/unit/document_understanding_root tools/document_understanding_"
        "benchmark/tests -q  ->  331 passed, 5 skipped (one invocation, as CI runs it)"
    )
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated {PATH.name}: {len(data)} keys, {len(MERGE_FINDINGS)} merge findings added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
