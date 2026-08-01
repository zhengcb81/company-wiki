"""
tests/contract/test_gold_corpus.py — 金标语料验证测试

验证系统输出与人工标注的 ground truth 一致。
"""

import hashlib
import json
from pathlib import Path


# ── 路径 ──────────────────────────────

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "gold_corpus"
ANNOTATIONS_DIR = FIXTURES_DIR / "annotations"
EXPECTED_DIR = FIXTURES_DIR / "expected"
SOURCES_DIR = FIXTURES_DIR / "sources"


# ── 辅助函数 ──────────────────────────────


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── 标注完整性测试 ──────────────────────────────


class TestAnnotationCompleteness:
    """验证标注文件结构完整"""

    def test_evidence_spans_file_exists(self):
        """证据标注文件存在"""
        assert (ANNOTATIONS_DIR / "evidence_spans.json").exists()

    def test_material_claims_file_exists(self):
        """声明标注文件存在"""
        assert (ANNOTATIONS_DIR / "material_claims.json").exists()

    def test_routing_targets_file_exists(self):
        """路由标注文件存在"""
        assert (ANNOTATIONS_DIR / "routing_targets.json").exists()

    def test_contradictions_file_exists(self):
        """矛盾标注文件存在"""
        assert (ANNOTATIONS_DIR / "contradictions.json").exists()

    def test_expected_wiki_page_exists(self):
        """预期 wiki 页面存在"""
        assert (EXPECTED_DIR / "wiki_pages" / "北方华创_公司动态.md").exists()

    def test_quality_metrics_exists(self):
        """质量指标文件存在"""
        assert (EXPECTED_DIR / "quality_metrics.json").exists()


# ── 标注一致性测试 ──────────────────────────────


class TestAnnotationConsistency:
    """验证标注之间的一致性"""

    def test_evidence_spans_referenced_by_claims(self):
        """声明引用的 evidence span 都存在"""
        spans = load_json(ANNOTATIONS_DIR / "evidence_spans.json")
        claims = load_json(ANNOTATIONS_DIR / "material_claims.json")

        # 收集所有 span_id
        all_span_ids = set()
        for source_spans in spans["spans"].values():
            for span in source_spans:
                all_span_ids.add(span["span_id"])

        # 检查 claim 引用的 span
        for claim in claims["claims"]:
            for span_id in claim.get("evidence_spans", []):
                assert span_id in all_span_ids, (
                    f"Claim {claim['claim_id']} 引用了不存在的 span {span_id}"
                )

    def test_claims_have_required_fields(self):
        """声明包含所有必需字段"""
        claims = load_json(ANNOTATIONS_DIR / "material_claims.json")

        required_fields = [
            "claim_id",
            "source_id",
            "claim_type",
            "text",
            "entity_id",
            "materiality",
        ]
        for claim in claims["claims"]:
            for field in required_fields:
                assert field in claim, (
                    f"Claim {claim.get('claim_id', '?')} 缺少字段 {field}"
                )

    def test_claim_types_valid(self):
        """声明类型有效"""
        claims = load_json(ANNOTATIONS_DIR / "material_claims.json")
        valid_types = ["fact", "opinion", "prediction"]

        for claim in claims["claims"]:
            assert claim["claim_type"] in valid_types, (
                f"Claim {claim['claim_id']} 类型无效: {claim['claim_type']}"
            )

    def test_materiality_levels_valid(self):
        """重要性级别有效"""
        claims = load_json(ANNOTATIONS_DIR / "material_claims.json")
        valid_levels = ["high", "medium", "low"]

        for claim in claims["claims"]:
            assert claim["materiality"] in valid_levels, (
                f"Claim {claim['claim_id']} 重要性无效: {claim['materiality']}"
            )

    def test_routing_confidence_valid(self):
        """路由置信度有效"""
        routing = load_json(ANNOTATIONS_DIR / "routing_targets.json")
        valid_confidences = ["high", "medium", "low", "ambiguous"]

        for route in routing["routing"]:
            for target in route["expected_targets"]:
                assert target["confidence"] in valid_confidences, (
                    f"Route {route['source_id']} target {target['entity_id']} 置信度无效: {target['confidence']}"
                )


# ── 数值准确性测试 ──────────────────────────────


class TestNumericAccuracy:
    """验证数值标注准确性"""

    def test_numeric_values_have_required_fields(self):
        """数值包含所有必需字段"""
        claims = load_json(ANNOTATIONS_DIR / "material_claims.json")
        required_fields = ["metric", "value", "unit", "currency", "period"]

        for claim in claims["claims"]:
            if claim.get("numeric"):
                for field in required_fields:
                    assert field in claim["numeric"], (
                        f"Claim {claim['claim_id']} numeric 缺少字段 {field}"
                    )

    def test_numeric_values_are_numbers(self):
        """数值是数字类型"""
        claims = load_json(ANNOTATIONS_DIR / "material_claims.json")

        for claim in claims["claims"]:
            if claim.get("numeric"):
                assert isinstance(claim["numeric"]["value"], (int, float)), (
                    f"Claim {claim['claim_id']} value 不是数字: {claim['numeric']['value']}"
                )

    def test_currency_valid(self):
        """货币代码有效"""
        claims = load_json(ANNOTATIONS_DIR / "material_claims.json")
        valid_currencies = ["CNY", "USD", "HKD"]

        for claim in claims["claims"]:
            if claim.get("numeric"):
                assert claim["numeric"]["currency"] in valid_currencies, (
                    f"Claim {claim['claim_id']} 货币无效: {claim['numeric']['currency']}"
                )


# ── 路由准确性测试 ──────────────────────────────


class TestRoutingAccuracy:
    """验证路由标注准确性"""

    def test_primary_entity_always_high_confidence(self):
        """主实体总是高置信度"""
        routing = load_json(ANNOTATIONS_DIR / "routing_targets.json")

        for route in routing["routing"]:
            primary = route["source_entity"]
            targets = route["expected_targets"]

            # 主实体应该在目标中
            primary_target = next(
                (t for t in targets if t["entity_id"] == primary), None
            )
            if primary_target and not route.get("has_ambiguity"):
                assert primary_target["confidence"] == "high", (
                    f"Route {route['source_id']} 主实体 {primary} 置信度不是 high"
                )

    def test_ambiguity_flag_consistent(self):
        """歧义标记一致"""
        routing = load_json(ANNOTATIONS_DIR / "routing_targets.json")

        for route in routing["routing"]:
            if route.get("has_ambiguity"):
                # 有歧义标记时，应该有 disambiguation_needed
                assert "disambiguation_needed" in route, (
                    f"Route {route['source_id']} 有歧义但无 disambiguation_needed"
                )

    def test_irrelevant_not_expected(self):
        """无关新闻不应出现在目标中"""
        routing = load_json(ANNOTATIONS_DIR / "routing_targets.json")

        for route in routing["routing"]:
            if route.get("is_irrelevant"):
                assert "not_expected" in route, (
                    f"Route {route['source_id']} 标记为无关但无 not_expected"
                )


# ── 矛盾处理测试 ──────────────────────────────


class TestContradictionHandling:
    """验证矛盾标注准确性"""

    def test_contradictions_have_resolution(self):
        """矛盾都有解决方案"""
        contradictions = load_json(ANNOTATIONS_DIR / "contradictions.json")

        for c in contradictions["contradictions"]:
            assert "resolution" in c, f"Contradiction {c['id']} 缺少 resolution"
            assert "effective_date" in c, f"Contradiction {c['id']} 缺少 effective_date"

    def test_corrections_reference_original(self):
        """更正引用原始来源"""
        contradictions = load_json(ANNOTATIONS_DIR / "contradictions.json")

        for correction in contradictions["corrections"]:
            assert "original_source" in correction
            assert "correcting_source" in correction
            assert "affected_claims" in correction

    def test_supersedes_has_dates(self):
        """替代关系有日期"""
        contradictions = load_json(ANNOTATIONS_DIR / "contradictions.json")

        for s in contradictions.get("supersedes", []):
            assert "effective_date" in s, "Supersedes 缺少 effective_date"


# ── 质量指标测试 ──────────────────────────────

FROZEN_GOLD_THRESHOLDS = {
    "material_claim_recall": (">=", 0.90, True),
    "material_claim_precision": (">=", 0.90, True),
    "evidence_exactness": (">=", 0.95, True),
    "provenance_coverage": (">=", 1.00, True),
    "numeric_exactness": (">=", 1.00, True),
    "claim_type_accuracy": (">=", 1.00, True),
    "routing_micro_precision": (">=", 0.90, True),
    "routing_micro_recall": (">=", 0.90, True),
    "routing_macro_f1": (">=", 0.85, False),
    "irrelevant_rejection": (">=", 1.00, True),
    "ambiguity_detection_recall": (">=", 1.00, True),
    "correction_supersedes_accuracy": (">=", 1.00, True),
    "as_of_leakage_rate": ("<=", 0.00, True),
    "aggregation_dedup_accuracy": (">=", 1.00, True),
}


class TestQualityMetrics:
    """验证 reviewer-owned 阈值定义；actual/status 只能出现在 evaluator receipt。"""

    def test_all_critical_metrics_present(self):
        """所有关键指标都存在"""
        metrics = load_json(EXPECTED_DIR / "quality_metrics.json")
        thresholds = metrics["thresholds"]
        for metric in FROZEN_GOLD_THRESHOLDS:
            assert metric in thresholds, f"缺少冻结指标: {metric}"

    def test_metrics_have_required_fields(self):
        """指标包含必需字段"""
        metrics = load_json(EXPECTED_DIR / "quality_metrics.json")

        for name, threshold in metrics["thresholds"].items():
            assert threshold.get("operator") in {">=", "<="}, (
                f"指标 {name} operator 无效"
            )
            assert isinstance(threshold.get("value"), (int, float)), (
                f"指标 {name} value 无效"
            )
            assert isinstance(threshold.get("critical"), bool), (
                f"指标 {name} critical 无效"
            )

    def test_critical_metrics_pass(self):
        """冻结阈值不得被实施模型在失败后放宽。"""
        metrics = load_json(EXPECTED_DIR / "quality_metrics.json")
        thresholds = metrics["thresholds"]
        for name, (operator, value, critical) in FROZEN_GOLD_THRESHOLDS.items():
            actual = thresholds[name]
            assert actual["operator"] == operator, f"{name} operator 漂移"
            assert actual["value"] == value, f"{name} 阈值被改动"
            assert actual["critical"] is critical, f"{name} critical 属性漂移"


# ── 来源文件测试 ──────────────────────────────


class TestSourceFiles:
    """验证来源文件结构"""

    def test_source_files_have_frontmatter(self):
        """来源文件有 frontmatter"""
        for source_file in SOURCES_DIR.rglob("*.md"):
            content = source_file.read_text(encoding="utf-8")
            assert content.startswith("---"), (
                f"来源文件 {source_file.name} 缺少 frontmatter"
            )

    def test_source_files_have_required_metadata(self):
        """来源文件包含必需元数据"""
        required_fields = ["source_id", "source_kind", "published_at", "entity_hints"]

        for source_file in SOURCES_DIR.rglob("*.md"):
            content = source_file.read_text(encoding="utf-8")
            # 简单检查 frontmatter 中是否包含字段名
            for field in required_fields:
                assert field in content, f"来源文件 {source_file.name} 缺少字段 {field}"


# ═══════════════════════════════════════════════════════════════════════
# RR-12.2d-1：Corpus 结构契约（红测）
#
# 本节为 RR-12.2d-1 的 inventory + manifest 红测。当前 corpus 仅 1 份 source、
# 无 manifest、存在外键缺失 / orphan span / offset 失准 / README 漂移 / 手填
# quality 指标等问题，因此下列新测试在旧 corpus 上**预期失败**。失败回执保存于
# artifacts/gates/rr-12.2d-1-red.json，作为进入 d-2（schema 正规化与样本修复）
# 与 d-3（扩展至 30 revision）的前置证据。
#
# 本节为纯只读：仅读取 fixture 文件与磁盘，不写入、不调用 LLM、不联网。
# ═══════════════════════════════════════════════════════════════════════

MANIFEST_PATH = FIXTURES_DIR / "corpus_manifest.json"

# RR-12.2d 施工包 §4：30-revision 最低覆盖矩阵
MIN_REVISIONS = 30
REQUIRED_SOURCE_KINDS = {
    "regulatory": 6,
    "company_announcement": 5,
    "ir": 5,
    "broker_research": 5,
    "original_news": 5,
    "aggregated_news": 4,
}
MANIFEST_REVISION_FIELDS = [
    "source_id",
    "revision_id",
    "logical_document_id",
    "path",
    "source_kind",
    "publisher",
    "entity_hints",
    "published_at",
    "observed_at",
    "effective_period",
    "scenario_tags",
    "content_sha256",
    "synthetic",
    "review_status",
]


# ── 只读 inventory helper ──────────────────────────────


def _parse_frontmatter(text: str):
    """简易 frontmatter 解析：返回 (fm_dict, body_str)。

    fm 行形如 `key: value`；不依赖 PyYAML，保持 contract 测试纯 stdlib。
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm_block, body = parts[1], parts[2]
    fm = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm, body


def _all_source_files():
    return sorted(SOURCES_DIR.rglob("*.md"))


def _disk_source_index():
    """source_id -> dict(path, body, fm, text) for each source file on disk."""
    index = {}
    for path in _all_source_files():
        text = path.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        sid = fm.get("source_id")
        if sid:
            index[sid] = {"path": path, "body": body, "fm": fm, "text": text}
    return index


def _spans_by_source():
    return load_json(ANNOTATIONS_DIR / "evidence_spans.json").get("spans", {})


def _all_claims():
    return load_json(ANNOTATIONS_DIR / "material_claims.json").get("claims", [])


def _all_routes():
    return load_json(ANNOTATIONS_DIR / "routing_targets.json").get("routing", [])


def _contradictions_doc():
    return load_json(ANNOTATIONS_DIR / "contradictions.json")


def _referenced_source_ids():
    """所有 annotation 中引用到的 source_id 集合。"""
    ids = set()
    ids.update(_spans_by_source().keys())
    for claim in _all_claims():
        sid = claim.get("source_id")
        if sid:
            ids.add(sid)
    for route in _all_routes():
        sid = route.get("source_id")
        if sid:
            ids.add(sid)
        # 更正关系
        for key in ("correction_of",):
            if route.get(key):
                ids.add(route[key])
    doc = _contradictions_doc()
    for c in doc.get("contradictions", []):
        for node_key in ("original_claim", "correcting_claim"):
            node = c.get(node_key, {})
            if node.get("source_id"):
                ids.add(node["source_id"])
    for corr in doc.get("corrections", []):
        for key in ("original_source", "correcting_source"):
            if corr.get(key):
                ids.add(corr[key])
    return ids


def _referenced_claim_ids():
    """contradictions/corrections/supersedes 中引用到的 claim_id 集合。"""
    ids = set()
    doc = _contradictions_doc()
    for c in doc.get("contradictions", []):
        for node_key in ("original_claim", "correcting_claim"):
            node = c.get(node_key, {})
            if node.get("claim_id"):
                ids.add(node["claim_id"])
    for corr in doc.get("corrections", []):
        ids.update(corr.get("affected_claims", []))
    for s in doc.get("supersedes", []):
        for key in ("newer_claim", "supersedes"):
            if s.get(key):
                ids.add(s[key])
    return ids


def _orphan_span_ids():
    """被任何 claim 的 evidence_spans 都未引用的 span_id。"""
    referenced = set()
    for claim in _all_claims():
        referenced.update(claim.get("evidence_spans", []))
    orphans = []
    for span_list in _spans_by_source().values():
        for span in span_list:
            if span.get("span_id") not in referenced:
                orphans.append(span.get("span_id"))
    return orphans


def _spans_referencing_missing_claim():
    """span.claim_id 指向不存在 claim 的 (span_id, claim_id)。"""
    claim_ids = {c.get("claim_id") for c in _all_claims()}
    missing = []
    for span_list in _spans_by_source().values():
        for span in span_list:
            cid = span.get("claim_id")
            if cid and cid not in claim_ids:
                missing.append((span.get("span_id"), cid))
    return missing


def _offset_mismatches():
    """span 的 [start:end] 与 source 正文不匹配的 (span_id, reason)。"""
    disk = _disk_source_index()
    mismatches = []
    for sid, span_list in _spans_by_source().items():
        body = disk.get(sid, {}).get("body", "")
        for span in span_list:
            span_id = span.get("span_id")
            start, end, text = span.get("start"), span.get("end"), span.get("text", "")
            if start is None or end is None:
                mismatches.append((span_id, "missing offsets"))
                continue
            if not (
                isinstance(start, int) and isinstance(end, int) and 0 <= start < end
            ):
                mismatches.append((span_id, f"invalid offsets [{start}:{end}]"))
                continue
            if end > len(body):
                mismatches.append((span_id, f"end {end} > body len {len(body)}"))
                continue
            if body[start:end] != text:
                mismatches.append((span_id, "body[start:end] != text"))
    return mismatches


# ── 1. Corpus manifest 契约 ──────────────────────────────


class TestCorpusManifest:
    """RR-12.2d 施工包 §3：corpus_manifest.json 是 fixture 唯一目录索引。"""

    def test_manifest_file_exists(self):
        assert MANIFEST_PATH.exists(), (
            f"缺少 corpus_manifest.json（{MANIFEST_PATH}）；当前 corpus 没有唯一目录索引"
        )

    def test_manifest_top_level_fields(self):
        manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else None
        assert manifest is not None
        for field in (
            "schema_version",
            "corpus_version",
            "annotation_policy_version",
            "synthetic_only",
            "revisions",
        ):
            assert field in manifest, f"manifest 缺少顶层字段 {field}"

    def test_manifest_synthetic_only(self):
        manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else None
        assert manifest is not None
        assert manifest.get("synthetic_only") is True, "金标 corpus 必须全部 synthetic"

    def test_manifest_revisions_have_required_fields(self):
        manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else None
        assert manifest is not None
        revisions = manifest.get("revisions", [])
        assert revisions, "manifest.revisions 不得为空"
        for rev in revisions:
            missing = [f for f in MANIFEST_REVISION_FIELDS if f not in rev]
            assert not missing, f"revision {rev.get('source_id')} 缺少字段 {missing}"

    def test_manifest_ids_are_layered(self):
        """source_id / revision_id / logical_document_id 三层不可混用。"""
        manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else None
        assert manifest is not None
        for rev in manifest.get("revisions", []):
            sid, rid, lid = (
                rev.get("source_id"),
                rev.get("revision_id"),
                rev.get("logical_document_id"),
            )
            assert sid and rid and lid, f"revision 缺少三层 ID: {rev}"
            assert len({sid, rid, lid}) == 3, (
                f"revision {sid} 的 source/revision/logical ID 不应相同"
            )

    def test_manifest_paths_resolve_to_real_files(self):
        manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else None
        assert manifest is not None
        for rev in manifest.get("revisions", []):
            p = rev.get("path", "")
            assert p and ".." not in p, (
                f"revision {rev.get('source_id')} path 非法: {p}"
            )
            assert (FIXTURES_DIR / p).is_file(), (
                f"revision {rev.get('source_id')} path {p} 不对应磁盘文件"
            )

    def test_manifest_content_sha256_matches_disk(self):
        manifest = load_json(MANIFEST_PATH) if MANIFEST_PATH.exists() else None
        assert manifest is not None
        for rev in manifest.get("revisions", []):
            p = rev.get("path")
            declared = rev.get("content_sha256")
            if not p or not declared:
                continue
            text = (FIXTURES_DIR / p).read_text(encoding="utf-8")
            _, body = _parse_frontmatter(text)
            actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
            assert actual == declared, (
                f"revision {rev.get('source_id')} content_sha256 与磁盘 body 不符（§3：正文 bytes）"
            )


# ── 2. 引用完整性 ──────────────────────────────


class TestReferentialIntegrity:
    """RR-12.2d 施工包 §5：所有外键必须指向真实存在的 source/claim。"""

    def test_no_missing_sources_referenced(self):
        disk = set(_disk_source_index().keys())
        referenced = _referenced_source_ids()
        missing = sorted(referenced - disk)
        assert not missing, (
            f"annotation 引用了 {len(missing)} 个不存在的 source: {missing}"
        )

    def test_no_orphan_spans(self):
        orphans = _orphan_span_ids()
        assert not orphans, f"{len(orphans)} 个 span 未被任何 claim 引用: {orphans}"

    def test_spans_claim_refs_exist(self):
        missing = _spans_referencing_missing_claim()
        assert not missing, (
            f"{len(missing)} 个 span 的 claim_id 指向不存在的 claim: {missing}"
        )

    def test_contradiction_claim_refs_exist(self):
        claim_ids = {c.get("claim_id") for c in _all_claims()}
        missing = sorted(cid for cid in _referenced_claim_ids() if cid not in claim_ids)
        assert not missing, (
            f"contradictions 引用了 {len(missing)} 个不存在的 claim: {missing}"
        )

    def test_global_id_uniqueness(self):
        """source/span/claim/route ID 在各自域内全局唯一。"""
        source_ids = [
            fm.get("source_id")
            for fm in (v["fm"] for v in _disk_source_index().values())
        ]
        span_ids = [
            span.get("span_id")
            for span_list in _spans_by_source().values()
            for span in span_list
        ]
        claim_ids = [c.get("claim_id") for c in _all_claims()]
        for label, ids in (
            ("source", source_ids),
            ("span", span_ids),
            ("claim", claim_ids),
        ):
            dupes = {i for i in ids if ids.count(i) > 1}
            assert not dupes, f"{label} ID 重复: {dupes}"


# ── 3. Evidence 精确性 ──────────────────────────────


class TestEvidenceExactness:
    """RR-12.2d 施工包 §5.1：span 的 [start:end] 必须与 source 正文精确相等。"""

    def test_span_offsets_match_source_body(self):
        mismatches = _offset_mismatches()
        assert not mismatches, (
            f"{len(mismatches)} 个 span 的 offset 与正文不符: {mismatches}"
        )


# ── 4. README 与磁盘一致 ──────────────────────────────


class TestReadmeConsistency:
    """RR-12.2d 施工包 §6(d-2)：README 须从 manifest/磁盘生成，不得手写虚构目录。"""

    def test_readme_documents_all_disk_source_dirs(self):
        # §6(d-2)：README 须从 manifest/磁盘生成；每个磁盘来源目录都应在 README 记录
        readme = (FIXTURES_DIR / "README.md").read_text(encoding="utf-8")
        disk_dirs = {p.name for p in SOURCES_DIR.iterdir() if p.is_dir()}
        for d in sorted(disk_dirs):
            assert d in readme, f"README 未记录磁盘存在的来源目录 sources/{d}/"

    def test_readme_documents_all_disk_annotation_files(self):
        # §6(d-2)：每个磁盘标注文件都应在 README 记录（numeric 内嵌于 material_claims）
        readme = (FIXTURES_DIR / "README.md").read_text(encoding="utf-8")
        for j in sorted(ANNOTATIONS_DIR.glob("*.json")):
            assert j.stem in readme, f"README 未记录磁盘存在的标注文件 {j.name}"

    def test_readme_mentions_manifest(self):
        readme = (FIXTURES_DIR / "README.md").read_text(encoding="utf-8")
        assert "corpus_manifest.json" in readme, (
            "README 未提及 corpus_manifest.json（唯一目录索引）"
        )


# ── 5. 规模与覆盖门槛 ──────────────────────────────


class TestCoverageGates:
    """RR-12.2d 施工包 §4：至少 30 revision、6 类来源、多实体覆盖。"""

    def test_revision_count_at_least_30(self):
        # d-1：以磁盘 source 文件数作为 revision 代理；d-2 后改读 manifest.revisions
        count = len(_all_source_files())
        assert count >= MIN_REVISIONS, (
            f"corpus 仅 {count} 个 source revision，低于门槛 {MIN_REVISIONS}"
        )

    def test_source_kind_coverage(self):
        from collections import Counter

        counter = Counter()
        for v in _disk_source_index().values():
            counter[v["fm"].get("source_kind", "").lower()] += 1
        under = {
            k: (counter.get(k, 0), need)
            for k, need in REQUIRED_SOURCE_KINDS.items()
            if counter.get(k, 0) < need
        }
        assert not under, f"source kind 覆盖不足: {under}"

    def test_company_coverage_at_least_3(self):
        companies = set()
        for v in _disk_source_index().values():
            for hint in v["fm"].get("entity_hints", []):
                # entity_hints 在 frontmatter 中为字符串，简单按逗号/括号拆分
                pass
        # frontmatter entity_hints 形如 "[北方华创, 002371]"，已解析为字符串
        for v in _disk_source_index().values():
            raw = v["fm"].get("entity_hints", "")
            for token in raw.strip("[]").split(","):
                token = token.strip()
                if token and not token.isdigit():
                    companies.add(token)
        assert len(companies) >= 3, (
            f"corpus 仅覆盖 {len(companies)} 家公司 {companies}，低于门槛 3"
        )

    def test_primary_entity_share_at_most_40_percent(self):
        """锚定公司不得支配 gold；口径为 routing.source_entity。"""
        from collections import Counter

        routes = _all_routes()
        counter = Counter(route.get("source_entity") for route in routes)
        entity, count = counter.most_common(1)[0]
        assert count * 100 <= len(routes) * 40, (
            f"primary entity 过度集中: {entity}={count}/{len(routes)} "
            f"({count / len(routes):.1%})，上限 40%"
        )

    def test_ambiguity_cases_at_least_4(self):
        count = sum(route.get("has_ambiguity") is True for route in _all_routes())
        assert count >= 4, f"ambiguity 场景仅 {count}，低于门槛 4"

    def test_irrelevant_cases_at_least_4(self):
        count = sum(route.get("is_irrelevant") is True for route in _all_routes())
        assert count >= 4, f"irrelevant 场景仅 {count}，低于门槛 4"

    def test_as_of_cases_at_least_4(self):
        manifest = load_json(MANIFEST_PATH)
        count = sum(
            "as_of" in revision.get("scenario_tags", [])
            for revision in manifest.get("revisions", [])
        )
        assert count >= 4, f"as_of 反前视场景仅 {count}，低于门槛 4"

    def test_correction_or_supersedes_claims_at_least_4(self):
        count = sum(
            bool(claim.get("corrects") or claim.get("supersedes"))
            for claim in _all_claims()
        )
        assert count >= 4, f"correction/supersedes claim 仅 {count}，低于门槛 4"


# ── 6. quality_metrics 反作弊 ──────────────────────────────


class TestQualityMetricsConsistency:
    """RR-12.2d §8(14)：质量文件只能定义阈值，不能伪造运行结果。"""

    def test_total_sources_matches_disk(self):
        metrics = load_json(EXPECTED_DIR / "quality_metrics.json")
        serialized = json.dumps(metrics, ensure_ascii=False)
        assert "total_sources" not in serialized
        assert "verified_sources" not in serialized

    def test_total_material_claims_matches_annotations(self):
        metrics = load_json(EXPECTED_DIR / "quality_metrics.json")
        serialized = json.dumps(metrics, ensure_ascii=False)
        assert "total_material_claims" not in serialized
        assert '"actual"' not in serialized
        assert '"status"' not in serialized

    def test_below_threshold_implies_not_canary_ready(self):
        """阈值文件不得嵌入 canary/overall 结论；结论只能由 receipt 产生。"""
        metrics = load_json(EXPECTED_DIR / "quality_metrics.json")
        serialized = json.dumps(metrics, ensure_ascii=False)
        assert "overall_assessment" not in metrics
        assert "all_critical_metrics_pass" not in serialized
        assert "ready_for_canary" not in serialized
