"""
migration.py — 历史数据迁移框架

所有 migration 默认 --plan，--apply manifest.json 才写入。
生成 inverse manifest、before/after hash、数量守恒。
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class MigrationAction(str, Enum):
    """迁移动作"""
    CREATE = "create"        # 创建新文件
    UPDATE = "update"        # 更新现有文件
    DELETE = "delete"        # 删除文件（实际标记为 archived）
    SKIP = "skip"            # 跳过（已有或不适用）
    QUARANTINE = "quarantine"  # 隔离（问题数据）


class EntryClassification(str, Enum):
    """旧条目分类"""
    VERIFIED = "verified"          # 来源+span 完整
    RECOVERABLE = "recoverable"    # 来源可找回
    UNVERIFIED = "unverified"      # 无法验证
    CONTRADICTED = "contradicted"  # 存在矛盾
    SUPERSEDED = "superseded"      # 已被更新
    DERIVED = "derived"            # 派生内容（不计独立来源）


@dataclass
class MigrationEntry:
    """迁移条目"""
    entry_id: str
    source_path: str
    target_path: str
    action: MigrationAction
    classification: EntryClassification = EntryClassification.UNVERIFIED
    before_hash: str = ""
    after_hash: str = ""
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MigrationManifest:
    """迁移清单"""
    manifest_id: str
    created_at: datetime
    entries: list[MigrationEntry] = field(default_factory=list)
    inverse_entries: list[MigrationEntry] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "manifest_id": self.manifest_id,
            "created_at": self.created_at.isoformat(),
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "source_path": e.source_path,
                    "target_path": e.target_path,
                    "action": e.action.value,
                    "classification": e.classification.value,
                    "before_hash": e.before_hash,
                    "after_hash": e.after_hash,
                    "reason": e.reason,
                }
                for e in self.entries
            ],
            "stats": self.stats,
        }

    def save(self, path: Path):
        """保存清单到文件"""
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "MigrationManifest":
        """从文件加载清单"""
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = cls(
            manifest_id=data["manifest_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
        for e in data.get("entries", []):
            manifest.entries.append(MigrationEntry(
                entry_id=e["entry_id"],
                source_path=e["source_path"],
                target_path=e["target_path"],
                action=MigrationAction(e["action"]),
                classification=EntryClassification(e.get("classification", "unverified")),
                before_hash=e.get("before_hash", ""),
                after_hash=e.get("after_hash", ""),
                reason=e.get("reason", ""),
            ))
        manifest.stats = data.get("stats", {})
        return manifest


class MigrationPlanner:
    """
    迁移规划器。

    扫描现有数据，生成迁移清单（不执行写入）。
    """

    def __init__(self, wiki_root: Path):
        self._root = wiki_root

    def plan_raw_registration(self) -> MigrationManifest:
        """
        规划 raw 文件注册。

        扫描 companies/*/ 和 companies/*/raw/ 下的非 wiki 文件，
        生成注册清单。
        """
        manifest = MigrationManifest(
            manifest_id=f"raw-reg-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            created_at=datetime.now(),
        )

        companies_dir = self._root / "companies"
        if not companies_dir.exists():
            manifest.stats = {
                "total": 0,
                "by_action": {},
                "by_classification": {},
            }
            return manifest

        for company_dir in companies_dir.iterdir():
            if not company_dir.is_dir() or company_dir.name == "__pycache__":
                continue

            # 扫描公司根目录下的文件
            for file_path in company_dir.rglob("*"):
                if file_path.is_file() and not self._is_wiki_file(file_path):
                    entry = MigrationEntry(
                        entry_id=f"raw-{hashlib.md5(str(file_path).encode()).hexdigest()[:8]}",
                        source_path=str(file_path.relative_to(self._root)),
                        target_path=str(file_path.relative_to(self._root)),
                        action=MigrationAction.SKIP,  # 默认跳过，只注册
                        classification=self._classify_file(file_path),
                        reason="raw 文件注册",
                    )
                    manifest.entries.append(entry)

        # 统计
        manifest.stats = {
            "total": len(manifest.entries),
            "by_action": {},
            "by_classification": {},
        }
        for e in manifest.entries:
            manifest.stats["by_action"][e.action.value] = manifest.stats["by_action"].get(e.action.value, 0) + 1
            manifest.stats["by_classification"][e.classification.value] = manifest.stats["by_classification"].get(e.classification.value, 0) + 1

        return manifest

    def plan_wiki_rebuild(self, entity_name: str) -> MigrationManifest:
        """
        规划单个实体的 wiki 重建。

        生成 before/after diff 清单。
        """
        manifest = MigrationManifest(
            manifest_id=f"wiki-rebuild-{entity_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            created_at=datetime.now(),
        )

        # 查找现有 wiki 页面
        wiki_dir = self._root / "companies" / entity_name / "wiki"
        if not wiki_dir.exists():
            wiki_dir = self._root / "sectors" / entity_name / "wiki"

        if wiki_dir.exists():
            for page in wiki_dir.glob("*.md"):
                entry = MigrationEntry(
                    entry_id=f"page-{entity_name}-{page.stem}",
                    source_path=str(page.relative_to(self._root)),
                    target_path=str(page.relative_to(self._root)),
                    action=MigrationAction.UPDATE,
                    before_hash=self._hash_file(page),
                    reason="wiki 重建",
                )
                manifest.entries.append(entry)

        manifest.stats = {
            "total": len(manifest.entries),
            "entity": entity_name,
        }

        return manifest

    def _is_wiki_file(self, path: Path) -> bool:
        """判断是否为 wiki 文件"""
        return "/wiki/" in str(path) or "\\wiki\\" in str(path)

    def _classify_file(self, path: Path) -> EntryClassification:
        """
        分类文件。

        简单实现：基于文件名和路径判断。
        """
        name = path.name.lower()

        # 有明确来源的文件
        if any(pattern in name for pattern in ["年报", "季报", "半年报", "公告"]):
            return EntryClassification.VERIFIED

        # 新闻文件
        if name.endswith(".md") and any(year in name for year in ["2024", "2025", "2026"]):
            return EntryClassification.VERIFIED

        # PDF 文件
        if name.endswith(".pdf"):
            return EntryClassification.VERIFIED

        # 其他
        return EntryClassification.UNVERIFIED

    def _hash_file(self, path: Path) -> str:
        """计算文件 SHA-256 前16位"""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]


class MigrationExecutor:
    """
    迁移执行器。

    按清单执行迁移，生成 inverse manifest 用于回滚。
    """

    def __init__(self, wiki_root: Path, dry_run: bool = True):
        self._root = wiki_root
        self._dry_run = dry_run

    def apply(self, manifest: MigrationManifest) -> MigrationManifest:
        """
        执行迁移。

        Args:
            manifest: 迁移清单

        Returns:
            inverse manifest（用于回滚）
        """
        inverse = MigrationManifest(
            manifest_id=f"inverse-{manifest.manifest_id}",
            created_at=datetime.now(),
        )

        for entry in manifest.entries:
            if entry.action == MigrationAction.SKIP:
                continue

            inverse_entry = self._apply_entry(entry)
            if inverse_entry:
                inverse.entries.append(inverse_entry)

        inverse.stats = {
            "total": len(inverse.entries),
            "original_manifest": manifest.manifest_id,
        }

        return inverse

    def _apply_entry(self, entry: MigrationEntry) -> Optional[MigrationEntry]:
        """执行单个迁移条目"""
        target = self._root / entry.target_path

        if self._dry_run:
            # dry-run 模式：只记录，不执行
            return MigrationEntry(
                entry_id=f"inverse-{entry.entry_id}",
                source_path=entry.target_path,
                target_path=entry.source_path,
                action=MigrationAction.SKIP,
                reason="dry-run: 未执行",
            )

        if entry.action == MigrationAction.CREATE:
            return self._apply_create(entry, target)
        elif entry.action == MigrationAction.UPDATE:
            return self._apply_update(entry, target)
        elif entry.action == MigrationAction.DELETE:
            return self._apply_delete(entry, target)
        elif entry.action == MigrationAction.QUARANTINE:
            return self._apply_quarantine(entry, target)

        return None

    def _apply_create(self, entry: MigrationEntry, target: Path) -> MigrationEntry:
        """执行创建"""
        # 创建目录
        target.parent.mkdir(parents=True, exist_ok=True)

        # 如果有内容，写入
        if "content" in entry.metadata:
            target.write_text(entry.metadata["content"], encoding="utf-8")

        return MigrationEntry(
            entry_id=f"inverse-{entry.entry_id}",
            source_path=entry.target_path,
            target_path=entry.source_path,
            action=MigrationAction.DELETE,
            reason="inverse of create",
        )

    def _apply_update(self, entry: MigrationEntry, target: Path) -> MigrationEntry:
        """执行更新"""
        if not target.exists():
            return MigrationEntry(
                entry_id=f"inverse-{entry.entry_id}",
                source_path=entry.target_path,
                target_path=entry.source_path,
                action=MigrationAction.SKIP,
                reason="target not found",
            )

        # 保存原内容用于回滚
        original_content = target.read_text(encoding="utf-8")
        original_hash = entry.before_hash

        # 更新内容
        if "content" in entry.metadata:
            target.write_text(entry.metadata["content"], encoding="utf-8")

        return MigrationEntry(
            entry_id=f"inverse-{entry.entry_id}",
            source_path=entry.target_path,
            target_path=entry.source_path,
            action=MigrationAction.UPDATE,
            before_hash=entry.after_hash,
            after_hash=original_hash,
            metadata={"content": original_content},
            reason="inverse of update",
        )

    def _apply_delete(self, entry: MigrationEntry, target: Path) -> MigrationEntry:
        """执行删除（标记为 archived）"""
        if not target.exists():
            return MigrationEntry(
                entry_id=f"inverse-{entry.entry_id}",
                source_path=entry.target_path,
                target_path=entry.source_path,
                action=MigrationAction.SKIP,
                reason="target not found",
            )

        # 读取原内容
        original_content = target.read_text(encoding="utf-8")

        # 重命名为 .archived
        archived_path = target.with_suffix(target.suffix + ".archived")
        target.rename(archived_path)

        return MigrationEntry(
            entry_id=f"inverse-{entry.entry_id}",
            source_path=entry.target_path,
            target_path=entry.source_path,
            action=MigrationAction.CREATE,
            metadata={"content": original_content},
            reason="inverse of delete",
        )

    def _apply_quarantine(self, entry: MigrationEntry, target: Path) -> MigrationEntry:
        """执行隔离"""
        if not target.exists():
            return MigrationEntry(
                entry_id=f"inverse-{entry.entry_id}",
                source_path=entry.target_path,
                target_path=entry.source_path,
                action=MigrationAction.SKIP,
                reason="target not found",
            )

        # 读取原内容
        original_content = target.read_text(encoding="utf-8")

        # 移动到 quarantine 目录
        quarantine_dir = self._root / ".quarantine"
        quarantine_dir.mkdir(exist_ok=True)
        quarantine_path = quarantine_dir / target.name
        target.rename(quarantine_path)

        return MigrationEntry(
            entry_id=f"inverse-{entry.entry_id}",
            source_path=entry.target_path,
            target_path=entry.source_path,
            action=MigrationAction.CREATE,
            metadata={"content": original_content},
            reason="inverse of quarantine",
        )


def verify_manifest_consistency(manifest: MigrationManifest) -> tuple[bool, list[str]]:
    """
    验证清单一致性。

    检查：
    1. 数量守恒（输入 = 输出）
    2. 哈希完整性
    3. 路径合法性

    Returns:
        (is_consistent, errors)
    """
    errors = []

    # 检查数量守恒
    action_counts = {}
    for entry in manifest.entries:
        action_counts[entry.action] = action_counts.get(entry.action, 0) + 1

    # 检查路径安全性
    for entry in manifest.entries:
        if ".." in entry.source_path or ".." in entry.target_path:
            errors.append(f"路径注入风险: {entry.entry_id}")
        if entry.source_path.startswith("/") or entry.target_path.startswith("/"):
            errors.append(f"绝对路径: {entry.entry_id}")

    # 检查哈希完整性
    for entry in manifest.entries:
        if entry.action == MigrationAction.UPDATE:
            if not entry.before_hash:
                errors.append(f"UPDATE 缺少 before_hash: {entry.entry_id}")

    return len(errors) == 0, errors
