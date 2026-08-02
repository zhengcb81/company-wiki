"""
tests/unit/test_migration.py — 迁移框架测试
"""

from datetime import datetime
from pathlib import Path


from company_wiki.migration import (
    EntryClassification,
    MigrationAction,
    MigrationEntry,
    MigrationExecutor,
    MigrationManifest,
    MigrationPlanner,
    verify_manifest_consistency,
)


# ── MigrationManifest 测试 ──────────────────────────────

class TestMigrationManifest:
    def test_manifest_creation(self):
        """测试清单创建"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
        )
        assert manifest.manifest_id == "test-001"
        assert len(manifest.entries) == 0

    def test_manifest_to_dict(self):
        """测试清单序列化"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime(2026, 7, 10),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="companies/test/raw/data.md",
                    target_path="companies/test/raw/data.md",
                    action=MigrationAction.SKIP,
                ),
            ],
        )

        d = manifest.to_dict()
        assert d["manifest_id"] == "test-001"
        assert len(d["entries"]) == 1
        assert d["entries"][0]["action"] == "skip"

    def test_manifest_save_load(self, tmp_path):
        """测试清单保存和加载"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime(2026, 7, 10),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.UPDATE,
                    before_hash="abc123",
                ),
            ],
            stats={"total": 1},
        )

        # 保存
        path = tmp_path / "manifest.json"
        manifest.save(path)

        # 加载
        loaded = MigrationManifest.load(path)
        assert loaded.manifest_id == "test-001"
        assert len(loaded.entries) == 1
        assert loaded.entries[0].before_hash == "abc123"


# ── MigrationPlanner 测试 ──────────────────────────────

class TestMigrationPlanner:
    def test_plan_raw_registration_empty(self, tmp_path):
        """测试空目录的 raw 注册规划"""
        planner = MigrationPlanner(tmp_path)
        manifest = planner.plan_raw_registration()

        assert manifest.stats["total"] == 0

    def test_plan_raw_registration_with_files(self, tmp_path):
        """测试有文件的 raw 注册规划"""
        # 创建测试文件
        company_dir = tmp_path / "companies" / "北方华创"
        company_dir.mkdir(parents=True)
        (company_dir / "年报.md").write_text("年报内容", encoding="utf-8")
        (company_dir / "公告.pdf").write_bytes(b"pdf content")

        planner = MigrationPlanner(tmp_path)
        manifest = planner.plan_raw_registration()

        assert manifest.stats["total"] == 2
        assert manifest.entries[0].classification == EntryClassification.VERIFIED

    def test_plan_raw_registration_skips_wiki(self, tmp_path):
        """测试跳过 wiki 文件"""
        # 创建 wiki 文件
        wiki_dir = tmp_path / "companies" / "北方华创" / "wiki"
        wiki_dir.mkdir(parents=True)
        (wiki_dir / "公司动态.md").write_text("wiki内容", encoding="utf-8")

        # 创建 raw 文件
        raw_dir = tmp_path / "companies" / "北方华创" / "raw"
        raw_dir.mkdir(parents=True)
        (raw_dir / "新闻.md").write_text("新闻内容", encoding="utf-8")

        planner = MigrationPlanner(tmp_path)
        manifest = planner.plan_raw_registration()

        # 只有 raw 文件，没有 wiki 文件
        paths = [e.source_path for e in manifest.entries]
        assert any("raw" in p for p in paths)
        assert not any("wiki" in p for p in paths)

    def test_plan_wiki_rebuild(self, tmp_path):
        """测试 wiki 重建规划"""
        # 创建 wiki 文件
        wiki_dir = tmp_path / "companies" / "北方华创" / "wiki"
        wiki_dir.mkdir(parents=True)
        (wiki_dir / "公司动态.md").write_text("内容", encoding="utf-8")

        planner = MigrationPlanner(tmp_path)
        manifest = planner.plan_wiki_rebuild("北方华创")

        assert manifest.stats["total"] == 1
        assert manifest.entries[0].action == MigrationAction.UPDATE
        assert manifest.entries[0].before_hash != ""

    def test_classify_file(self, tmp_path):
        """测试文件分类"""
        planner = MigrationPlanner(tmp_path)

        # 年报 -> VERIFIED
        assert planner._classify_file(Path("test_年报.md")) == EntryClassification.VERIFIED

        # PDF -> VERIFIED
        assert planner._classify_file(Path("test.pdf")) == EntryClassification.VERIFIED

        # 其他 -> UNVERIFIED
        assert planner._classify_file(Path("unknown.txt")) == EntryClassification.UNVERIFIED


# ── MigrationExecutor 测试 ──────────────────────────────

class TestMigrationExecutor:
    def test_apply_dry_run(self, tmp_path):
        """测试 dry-run 模式"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.CREATE,
                ),
            ],
        )

        executor = MigrationExecutor(tmp_path, dry_run=True)
        inverse = executor.apply(manifest)

        # dry-run 不应该创建文件
        assert not (tmp_path / "test.md").exists()
        # 应该生成 inverse
        assert len(inverse.entries) == 1
        assert inverse.entries[0].action == MigrationAction.SKIP

    def test_apply_create(self, tmp_path):
        """测试创建操作"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.CREATE,
                    metadata={"content": "新内容"},
                ),
            ],
        )

        executor = MigrationExecutor(tmp_path, dry_run=False)
        inverse = executor.apply(manifest)

        # 文件应该被创建
        assert (tmp_path / "test.md").exists()
        assert (tmp_path / "test.md").read_text(encoding="utf-8") == "新内容"

        # inverse 应该是 DELETE
        assert inverse.entries[0].action == MigrationAction.DELETE

    def test_apply_update(self, tmp_path):
        """测试更新操作"""
        # 创建原文件
        (tmp_path / "test.md").write_text("原内容", encoding="utf-8")

        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.UPDATE,
                    before_hash="abc",
                    metadata={"content": "新内容"},
                ),
            ],
        )

        executor = MigrationExecutor(tmp_path, dry_run=False)
        inverse = executor.apply(manifest)

        # 文件应该被更新
        assert (tmp_path / "test.md").read_text(encoding="utf-8") == "新内容"

        # inverse 应该包含原内容
        assert inverse.entries[0].metadata["content"] == "原内容"

    def test_apply_delete(self, tmp_path):
        """测试删除操作"""
        # 创建原文件
        (tmp_path / "test.md").write_text("原内容", encoding="utf-8")

        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.DELETE,
                ),
            ],
        )

        executor = MigrationExecutor(tmp_path, dry_run=False)
        inverse = executor.apply(manifest)

        # 文件应该被重命名为 .archived
        assert not (tmp_path / "test.md").exists()
        assert (tmp_path / "test.md.archived").exists()

        # inverse 应该是 CREATE
        assert inverse.entries[0].action == MigrationAction.CREATE

    def test_apply_quarantine(self, tmp_path):
        """测试隔离操作"""
        # 创建原文件
        (tmp_path / "test.md").write_text("问题内容", encoding="utf-8")

        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.QUARANTINE,
                ),
            ],
        )

        executor = MigrationExecutor(tmp_path, dry_run=False)
        executor.apply(manifest)

        # 文件应该被移动到 quarantine
        assert not (tmp_path / "test.md").exists()
        assert (tmp_path / ".quarantine" / "test.md").exists()

    def test_apply_skip(self, tmp_path):
        """测试跳过操作"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.SKIP,
                ),
            ],
        )

        executor = MigrationExecutor(tmp_path, dry_run=False)
        inverse = executor.apply(manifest)

        # 跳过的条目不生成 inverse
        assert len(inverse.entries) == 0


# ── verify_manifest_consistency 测试 ──────────────────────────────

class TestVerifyManifestConsistency:
    def test_consistent_manifest(self):
        """测试一致的清单"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.UPDATE,
                    before_hash="abc",
                ),
            ],
        )

        is_consistent, errors = verify_manifest_consistency(manifest)
        assert is_consistent is True
        assert len(errors) == 0

    def test_path_injection(self):
        """测试路径注入检测"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="../etc/passwd",
                    target_path="test.md",
                    action=MigrationAction.UPDATE,
                ),
            ],
        )

        is_consistent, errors = verify_manifest_consistency(manifest)
        assert is_consistent is False
        assert any("路径注入" in e for e in errors)

    def test_absolute_path(self):
        """测试绝对路径检测"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="/etc/passwd",
                    target_path="test.md",
                    action=MigrationAction.UPDATE,
                ),
            ],
        )

        is_consistent, errors = verify_manifest_consistency(manifest)
        assert is_consistent is False
        assert any("绝对路径" in e for e in errors)

    def test_missing_hash_for_update(self):
        """测试 UPDATE 缺少 hash"""
        manifest = MigrationManifest(
            manifest_id="test-001",
            created_at=datetime.now(),
            entries=[
                MigrationEntry(
                    entry_id="e1",
                    source_path="test.md",
                    target_path="test.md",
                    action=MigrationAction.UPDATE,
                    # 缺少 before_hash
                ),
            ],
        )

        is_consistent, errors = verify_manifest_consistency(manifest)
        assert is_consistent is False
        assert any("before_hash" in e for e in errors)
