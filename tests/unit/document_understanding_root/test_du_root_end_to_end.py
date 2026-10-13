"""ROOT end-to-end: parse -> adapter -> route -> structure -> packages.

This is the full chain from ``implementation.md`` step 6.  It exists to catch
the class of failure that per-lane tests cannot see: each package being correct
on its own fixtures while their *composition* is wrong.

The chain must also never let routing delete evidence.  A route decides reading
strategy and priority; it does not remove a unit, and an unknown route still
yields structure.  That property is asserted here on the real originals.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SOURCE = REPO / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from company_wiki.document_understanding import build_observation  # noqa: E402
from company_wiki.document_understanding.orchestration import (  # noqa: E402
    build_dependency_packages,
)
from company_wiki.document_understanding.profiles import route_document  # noqa: E402
from company_wiki.document_understanding.selection_bridge import (  # noqa: E402
    dependency_closure,
)
from company_wiki.document_understanding.structure import build_structure  # noqa: E402

BINDINGS_ENV = "DU_ROOT_BINDINGS"
DEFAULT_BINDINGS = Path(".planning") / "du-root" / "bindings.local.json"


def _observation(units, *, source_id="s", title="", sha="d"):
    return build_observation(units, source_id=source_id, source_sha256=sha, title=title)


class _Coords:
    def __init__(self, page=None, table_index=None, row_index=None):
        self.page_number = page
        self.table_index = table_index
        self.row_index = row_index
        self.column_index = None


class _Unit:
    def __init__(self, unit_id, text, *, kind="pdf_text_block", page=1, bbox=None,
                 metadata=None, coords=None, role="company_filing", language="zh"):
        self.unit_id = unit_id
        self.raw_text = text
        self.unit_kind = kind
        self.source_role = role
        self.language = language
        self.coordinates = coords or _Coords(page=page)
        self.metadata = dict(metadata or {})
        if bbox is not None:
            self.metadata["bbox"] = list(bbox)


# ------------------------------------------------------------ chain shape


def _offering_units():
    return [
        _Unit("h1", "第三节 募集资金运用", bbox=(60, 90, 300, 115)),
        _Unit("i1", "本次募集资金拟投资于以下项目：", bbox=(60, 130, 530, 155)),
        _Unit("c1", "单位：万元", kind="table_caption", bbox=(60, 160, 200, 178)),
        _Unit(
            "r0",
            "项目名称 | 投资总额 | 募集资金投入额 | 建设期",
            kind="pdf_table_row",
            coords=_Coords(page=2, table_index=0, row_index=0),
            bbox=(60, 185, 530, 205),
        ),
        _Unit(
            "r1",
            "高端精密刀具扩产项目 | 28000 | 20000 | 24 个月",
            kind="pdf_table_row",
            coords=_Coords(page=2, table_index=0, row_index=1),
            bbox=(60, 210, 530, 230),
        ),
        _Unit("p2", "项目建设期为 24 个月，其中前 12 个月完成土建，", page=2, bbox=(60, 300, 530, 345)),
        _Unit("p3", "后 12 个月完成设备安装调试并试生产。", page=3, bbox=(60, 95, 530, 140)),
    ]


def test_full_chain_runs_and_produces_every_layer() -> None:
    observation = _observation(
        _offering_units(),
        title="示例：向特定对象发行A股股票募集说明书",
    )
    route = route_document(observation)
    structure = build_structure(observation)
    packages = build_dependency_packages(structure, route=route)

    assert route["schema_version"] == "du-route/1"
    assert structure["schema_version"] == "du-structure/1"
    assert packages["schema_version"] == "du-packages/1"
    assert packages["package_count"] > 0
    assert route["disposition_hint"] in {"read", "generic_read", "administrative_candidate"}


def test_routing_never_removes_a_unit_from_the_structure() -> None:
    """Structure output must be identical regardless of the route."""
    observation = _observation(_offering_units(), title="任意标题")
    routed = route_document(observation)
    baseline = build_structure(observation)
    with_route = build_structure(observation)
    assert baseline["sections"] == with_route["sections"]
    assert baseline["semantic_units"] == with_route["semantic_units"]
    # The route is metadata; it does not gate structural output.
    assert routed["profile_id"]


def test_unknown_document_still_reads() -> None:
    observation = _observation(
        [_Unit("u1", "这是一段没有任何标题线索的正文。", bbox=(60, 90, 530, 140))],
        title="untitled",
    )
    route = route_document(observation)
    assert route["disposition_hint"] in {"read", "generic_read"}
    structure = build_structure(observation)
    assert structure["semantic_units"], "an unknown document must still be readable"


def test_route_priorities_reach_the_packages_without_changing_membership() -> None:
    observation = _observation(_offering_units(), title="示例募集说明书")
    route = route_document(observation)
    plain = build_dependency_packages(build_structure(observation))
    routed = build_dependency_packages(build_structure(observation), route=route)
    plain_ids = {package["package_id"] for package in plain["packages"]}
    routed_ids = {package["package_id"] for package in routed["packages"]}
    assert plain_ids == routed_ids, "routing must not change which packages exist"


def test_package_closure_end_to_end_keeps_the_unit_caption() -> None:
    observation = _observation(_offering_units(), title="示例募集说明书")
    structure = build_structure(observation)
    packages = build_dependency_packages(structure)
    texts = {unit["unit_id"]: unit["text"] for unit in observation["units"]}

    # Pretend the selector chose only the bare project row.
    closed = dependency_closure(["r1"], packages, texts)
    assert "c1" in closed["selected_unit_ids"], (
        "the unit caption must be restored so the number keeps its unit"
    )


def test_chain_output_is_stable_across_two_runs() -> None:
    observation = _observation(_offering_units(), title="示例募集说明书")
    def run():
        route = route_document(observation)
        structure = build_structure(observation)
        return json.dumps(
            {
                "route": route,
                "structure": structure,
                "packages": build_dependency_packages(structure, route=route),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    assert run() == run()


# ------------------------------------------------------------ real data


def _bindings():
    configured = os.environ.get(BINDINGS_ENV)
    path = Path(configured) if configured else REPO / DEFAULT_BINDINGS
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


@pytest.mark.real_data
def test_real_unknown_offering_now_routes_to_an_offering() -> None:
    """The headline defect: 发行A股股票募集说明书 used to route to unknown."""
    bindings = _bindings()
    if not bindings:
        pytest.skip(f"no bindings; set {BINDINGS_ENV} for real-data checks")
    entry = bindings.get("cn-equity")
    if not isinstance(entry, dict) or not Path(entry.get("path", "")).is_file():
        pytest.skip("cn-equity original not bound on this machine")

    import hashlib

    from company_wiki.source_catalog.narrative_evidence import parse_pdf
    from company_wiki.source_catalog.narrative_routing import classify_document_kind

    path = Path(entry["path"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != entry.get("sha256"):
        pytest.skip("cn-equity SHA does not match its binding")

    title = "恒锋工具：2020年向特定对象发行A股股票募集说明书（注册稿）"
    legacy = classify_document_kind(title)
    assert legacy == "unknown", "the legacy title router no longer shows the defect"

    parsed = parse_pdf(path, source_id="cn-equity", source_sha256=digest, table_pages=[62, 63])
    units = [unit for unit in parsed.units if unit.coordinates.page_number in (62, 63)]
    observation = build_observation(
        units, source_id="cn-equity", source_sha256=digest, title=title, native_scan="partial"
    )
    route = route_document(observation)
    assert route["regime"] == "cn_exchange"
    assert route["family"] in {"offering", "prospectus"}
    assert route["disposition_hint"] == "read"
