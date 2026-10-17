"""Local benchmark and resource changes follow proven consumer boundaries."""

from pathlib import Path

import pytest

from tools.changed_unit_tests import select_unit_tests


def put(root: Path, name: str, text: str = "VALUE = 1\n") -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return name


def benchmark(
    root, *, body="import subprocess\ndef run(): return subprocess.run(argv)\n"
):
    tool = put(root, "tools/document_understanding_benchmark/reader.py", body)
    test = put(
        root,
        "tests/test_benchmark.py",
        "from tools.document_understanding_benchmark import reader\ndef test_reader(): reader.run()\n",
    )
    put(
        root,
        "tests/unit/test_unrelated.py",
        "import subprocess\ndef test_other(): subprocess.run(argv)\n",
    )
    return tool, test


@pytest.mark.parametrize("suite", ["", "document_normalization/", "unit/deep/"])
def test_test_module_at_any_depth_is_itself_a_consumer(tmp_path, suite):
    case = put(
        tmp_path, "tests/" + suite + "test_example.py", "def test_example(): pass\n"
    )
    assert select_unit_tests(tmp_path, {case})[0] == [case]


def test_benchmark_dynamic_tool_follows_executing_top_level_test_and_reverse_consumers(
    tmp_path,
):
    tool, test = benchmark(tmp_path)
    consumer = put(
        tmp_path,
        "tests/unit/test_consumer.py",
        "from tests import test_benchmark\ndef test_use(): test_benchmark.test_reader()\n",
    )
    assert select_unit_tests(tmp_path, {tool})[0] == [test, consumer]


def test_benchmark_helper_change_keeps_executing_transitive_tool_consumers(tmp_path):
    tool, test = benchmark(
        tmp_path,
        body="from tools.document_understanding_benchmark import helper\ndef run(): helper.work()\n",
    )
    helper = put(
        tmp_path,
        "tools/document_understanding_benchmark/helper.py",
        "import subprocess\ndef work(): subprocess.run(argv)\n",
    )
    assert select_unit_tests(tmp_path, {helper})[0] == [test]


@pytest.mark.parametrize(
    "tool",
    ["tools/pre_push_gate.py", "tools/changed_unit_tests.py", "tools/unclassified.py"],
)
def test_unclassified_or_gate_tools_remain_global(tmp_path, tool):
    put(tmp_path, tool)
    put(
        tmp_path,
        "tests/unit/test_tool.py",
        "import tools.pre_push_gate\ndef test_tool(): pass\n",
    )
    assert select_unit_tests(tmp_path, {tool})[0] == ["tests/unit"]


def test_import_only_does_not_prove_benchmark_execution(tmp_path):
    tool, test = benchmark(tmp_path)
    put(
        tmp_path,
        test,
        "from tools.document_understanding_benchmark import reader\ndef test_unrelated(): assert True\n",
    )
    assert select_unit_tests(tmp_path, {tool})[0] == ["tests/unit"]


def test_dormant_test_helper_does_not_prove_benchmark_execution(tmp_path):
    tool, test = benchmark(tmp_path)
    put(
        tmp_path,
        test,
        "from tools.document_understanding_benchmark import reader\ndef unused(): reader.run()\ndef test_unrelated(): assert True\n",
    )
    assert select_unit_tests(tmp_path, {tool})[0] == ["tests/unit"]


def test_benchmark_worker_file_without_proven_import_call_remains_full(tmp_path):
    worker = put(
        tmp_path,
        "tools/document_understanding_benchmark/worker.py",
        "import subprocess\ndef install(): subprocess.run(argv)\n",
    )
    put(
        tmp_path,
        "tools/document_understanding_benchmark/launcher.py",
        "from tools.document_understanding_benchmark import worker\nworker.install()\n",
    )
    put(
        tmp_path,
        "tools/document_understanding_benchmark/reader.py",
        'import subprocess\ndef run(): subprocess.run(["python", "launcher.py"])\n',
    )
    put(
        tmp_path,
        "tests/test_benchmark.py",
        "from tools.document_understanding_benchmark import reader\ndef test_reader(): reader.run()\n",
    )
    assert select_unit_tests(tmp_path, {worker})[0] == ["tests/unit"]


def test_filename_comparison_is_not_a_production_execution_dependency(tmp_path):
    tool, case = benchmark(tmp_path)
    put(
        tmp_path,
        "src/pkg/policy.py",
        'def excluded(path): return path.name in {"reader.py"}\n',
    )
    assert select_unit_tests(tmp_path, {tool})[0] == [case]


def test_production_file_path_consumer_prevents_benchmark_isolation(tmp_path):
    tool, _ = benchmark(tmp_path)
    put(
        tmp_path,
        "src/pkg/runtime.py",
        'ENTRY = "tools/document_understanding_benchmark/reader.py"\n',
    )
    assert select_unit_tests(tmp_path, {tool})[0] == ["tests/unit"]


def test_benchmark_with_production_caller_is_not_test_isolated(tmp_path):
    tool, _ = benchmark(tmp_path)
    put(
        tmp_path,
        "src/pkg/runtime.py",
        "from tools.document_understanding_benchmark import reader\ndef run(): reader.run()\n",
    )
    assert select_unit_tests(tmp_path, {tool})[0] == ["tests/unit"]


def test_production_dynamic_execution_rule_is_unchanged_even_alongside_benchmark(
    tmp_path,
):
    tool, _ = benchmark(tmp_path)
    runtime = put(
        tmp_path, "src/pkg/runtime.py", "import subprocess\nsubprocess.run(argv)\n"
    )
    put(tmp_path, "tests/unit/test_runtime.py", "from pkg import runtime\n")
    assert select_unit_tests(tmp_path, {tool, runtime})[0] == ["tests/unit"]


def test_local_json_still_requires_closed_read_scope(tmp_path):
    resource = put(tmp_path, "src/pkg/profiles/catalog.json", "{}")
    put(
        tmp_path,
        "src/pkg/registry.py",
        'from pathlib import Path\nDATA = (Path(__file__).parent / "profiles" / "catalog.json").read_text()\n',
    )
    put(tmp_path, "src/pkg/reader.py", "from pkg import registry\n")
    put(tmp_path, "tests/unit/test_reader.py", "from pkg import reader\n")
    put(tmp_path, "tests/unit/test_unrelated.py")
    assert select_unit_tests(tmp_path, {resource})[0] == ["tests/unit"]


def test_referenced_fixture_does_not_prove_absence_of_other_dynamic_readers(tmp_path):
    resource = put(tmp_path, "tests/fixtures/text/catalog.json", "{}")
    put(
        tmp_path,
        "tests/test_fixture.py",
        'from pathlib import Path\ndef test_fixture(): assert Path("tests/fixtures/text/catalog.json").read_text()\n',
    )
    put(tmp_path, "tests/unit/test_unrelated.py")
    assert select_unit_tests(tmp_path, {resource})[0] == ["tests/unit"]


def test_same_basename_resource_ambiguity_retains_full_fallback(tmp_path):
    resource = put(tmp_path, "src/pkg/a/catalog.json", "{}")
    put(tmp_path, "src/pkg/b/catalog.json", "{}")
    put(tmp_path, "src/pkg/a.py", 'PATH = "a/catalog.json"\n')
    put(tmp_path, "src/pkg/b.py", 'PATH = "catalog.json"\n')
    put(tmp_path, "tests/unit/test_a.py", "from pkg import a\n")
    put(tmp_path, "tests/unit/test_b.py", "from pkg import b\n")
    assert select_unit_tests(tmp_path, {resource})[0] == ["tests/unit"]


@pytest.mark.parametrize(
    "resource", ["src/pkg/profiles/unknown.json", "tests/fixtures/unknown.json"]
)
def test_unknown_or_deleted_resource_keeps_full_fallback(tmp_path, resource):
    assert select_unit_tests(tmp_path, {resource})[0] == ["tests/unit"]
    put(tmp_path, resource, "{}")
    assert select_unit_tests(tmp_path, {resource})[0] == ["tests/unit"]


def test_unresolved_resource_filename_has_no_proven_owner(tmp_path):
    resource = put(tmp_path, "src/pkg/profiles/catalog.json", "{}")
    put(tmp_path, "src/pkg/reader.py", "DATA = Path(folder) / resource_name\n")
    put(tmp_path, "tests/unit/test_reader.py", "from pkg import reader\n")
    assert select_unit_tests(tmp_path, {resource})[0] == ["tests/unit"]


@pytest.mark.parametrize(
    "global_path",
    [
        "config/catalog.json",
        "tests/conftest.py",
        "tests/unit/shared/conftest.py",
        "setup.cfg",
        "uv.lock",
    ],
)
def test_known_reader_does_not_narrow_real_global_configuration(tmp_path, global_path):
    put(tmp_path, global_path, "{}")
    put(tmp_path, "tests/unit/test_reader.py", f'PATH = "{global_path}"\n')
    assert select_unit_tests(tmp_path, {global_path})[0] == ["tests/unit"]


def test_unknown_resource_scope_remains_global_in_mixed_push(tmp_path):
    tool, top = benchmark(tmp_path)
    resource = put(tmp_path, "src/pkg/catalog.json", "{}")
    runtime = put(tmp_path, "src/pkg/registry.py", 'PATH = "catalog.json"\n')
    put(tmp_path, "tests/unit/test_registry.py", "from pkg import registry\n")
    assert select_unit_tests(tmp_path, {tool, resource, runtime})[0] == ["tests/unit"]


def test_changed_nonmodule_test_helper_keeps_existing_computed_import_consumers(
    tmp_path,
):
    helper = put(tmp_path, "tests/support/helper.py")
    known = put(
        tmp_path, "tests/unit/test_helper.py", "from tests.support import helper\n"
    )
    dynamic = put(
        tmp_path,
        "tests/unit/test_computed.py",
        "from importlib import import_module\ndef test_plugin(): import_module(name)\n",
    )
    assert select_unit_tests(tmp_path, {helper})[0] == [dynamic, known]


def test_known_global_dynamic_fallback_does_not_build_unneeded_repository_graph(
    tmp_path, monkeypatch
):
    runtime = put(
        tmp_path, "src/pkg/runtime.py", "import subprocess\nsubprocess.run(argv)\n"
    )

    def forbidden_graph(*args, **kwargs):
        raise AssertionError(
            "already-global source change must not scan the whole repository"
        )

    monkeypatch.setattr(Path, "rglob", forbidden_graph)
    assert select_unit_tests(tmp_path, {runtime}) == (
        ["tests/unit"],
        "dynamic execution changed",
    )


@pytest.mark.parametrize("static_owner", [False, True])
def test_resource_decoy_or_static_owner_cannot_hide_dynamic_filename_reader(
    tmp_path, static_owner
):
    resource = put(tmp_path, "src/pkg/profiles/catalog.json", '{"value": 7}')
    dynamic_source = (
        "import json\nfrom pathlib import Path\n"
        "def read(filename):\n"
        "    return json.loads((Path(__file__).parent / 'profiles' / filename).read_text())\n"
    )
    reader = put(tmp_path, "src/pkg/dynamic_reader.py", dynamic_source)
    put(
        tmp_path,
        "tests/unit/test_actual_reader.py",
        "from pkg import dynamic_reader\ndef test_read(): assert dynamic_reader.read(requested_filename)['value'] == 7\n",
    )
    if static_owner:
        put(
            tmp_path,
            "src/pkg/static_reader.py",
            "from pathlib import Path\ndef read(): return (Path(__file__).parent / 'profiles' / 'catalog.json').read_text()\n",
        )
        put(
            tmp_path,
            "tests/unit/test_static_reader.py",
            "from pkg import static_reader\ndef test_read(): assert static_reader.read()\n",
        )
    else:
        put(
            tmp_path,
            "tests/unit/test_filename_policy.py",
            "def test_policy(path): assert path.name == 'catalog.json'\n",
        )
    # Prove this is a real same-subtree byte reader, not just another string.
    namespace = {"__file__": str(tmp_path / reader)}
    exec(compile(dynamic_source, str(tmp_path / reader), "exec"), namespace)
    assert namespace["read"]("catalog" + ".json") == {"value": 7}
    assert select_unit_tests(tmp_path, {resource})[0] == ["tests/unit"]


def test_printed_filename_and_unrelated_subprocess_do_not_prove_tool_execution(
    tmp_path,
):
    tool = put(
        tmp_path,
        "tools/document_understanding_benchmark/reader.py",
        "import subprocess\ndef run(): subprocess.run(argv)\n",
    )
    put(
        tmp_path,
        "tests/test_display.py",
        "import subprocess\ndef test_display():\n    print('reader.py')\n    subprocess.run(['echo', 'unrelated'])\n",
    )
    assert select_unit_tests(tmp_path, {tool}) == (
        ["tests/unit"],
        "benchmark execution or isolation unproven",
    )
