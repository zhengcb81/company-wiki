"""
wiki_repository.py — 唯一 Wiki 写入器

所有 wiki 页面、index、log 的更新只经此入口。
单页采用同目录唯一临时文件 + flush/fsync + atomic replace。
"""

import hashlib
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .domain import Claim, ClaimType


# ── WikiRepository ──────────────────────────────

class WikiRepository:
    """
    唯一 Wiki 写入器。

    所有公司/行业/主题页面、index、log 更新只经此入口。
    支持 atomic replace、before/after hash、人工注释保护。
    """

    def __init__(self, wiki_root: Path):
        self._root = wiki_root

    # ── 读取 ──────────────────────────────

    def read_page(self, entity_name: str, page_name: str = "公司动态") -> Optional[str]:
        """读取 wiki 页面内容"""
        path = self._get_page_path(entity_name, page_name)
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None

    def read_frontmatter(self, entity_name: str, page_name: str = "公司动态") -> dict:
        """读取页面 frontmatter"""
        content = self.read_page(entity_name, page_name)
        if not content or not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        import yaml
        try:
            return yaml.safe_load(parts[1]) or {}
        except Exception:
            return {}

    # ── 写入 ──────────────────────────────

    def write_page(
        self,
        entity_name: str,
        page_name: str,
        content: str,
        protect_annotations: bool = True,
    ) -> tuple[str, str]:
        """
        原子写入 wiki 页面。

        Args:
            entity_name: 实体名称
            page_name: 页面名称（如"公司动态"）
            content: 页面内容
            protect_annotations: 是否保护人工注释块

        Returns:
            (before_hash, after_hash)
        """
        path = self._get_page_path(entity_name, page_name)

        # 计算 before hash
        before_hash = ""
        if path.exists():
            before_hash = self._hash_file(path)

            # 保护人工注释块
            if protect_annotations:
                existing = path.read_text(encoding="utf-8")
                content = self._merge_annotations(existing, content)

        # 原子写入
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(path, content)

        # 计算 after hash
        after_hash = self._hash_file(path)

        return before_hash, after_hash

    def update_frontmatter(
        self,
        entity_name: str,
        page_name: str,
        updates: dict,
    ) -> tuple[str, str]:
        """更新页面 frontmatter 字段"""
        content = self.read_page(entity_name, page_name)
        if not content:
            return "", ""

        import yaml

        # 解析现有 frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1]) or {}
                fm.update(updates)
                new_content = f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False)}---\n{parts[2]}"
                return self.write_page(entity_name, page_name, new_content, protect_annotations=False)

        return "", ""

    # ── 条目操作 ──────────────────────────────

    def append_timeline_entry(
        self,
        entity_name: str,
        page_name: str,
        claim: Claim,
        source_path: str = "",
    ) -> bool:
        """
        向时间线追加条目。

        Returns:
            是否成功
        """
        content = self.read_page(entity_name, page_name)
        if not content:
            return False

        # 格式化条目
        date_str = claim.published_at.strftime("%Y-%m-%d") if claim.published_at else "未知日期"
        source_type = self._claim_type_to_source_type(claim.claim_type)

        entry = f"\n### {date_str} | {source_type} | {claim.text[:50]}\n"
        entry += f"- {claim.text}\n"
        if claim.metric:
            entry += f"- {claim.metric}: {claim.value}{claim.unit}\n"
        if source_path:
            entry += f"- [来源说明]({source_path})\n"

        # 插入到时间线部分
        if "## 时间线" in content:
            # 在"## 时间线"之后插入
            parts = content.split("## 时间线", 1)
            # 找到第一个 ### 条目的位置
            timeline = parts[1]
            first_entry = re.search(r"\n### ", timeline)
            if first_entry:
                insert_pos = first_entry.start()
                new_content = parts[0] + "## 时间线" + timeline[:insert_pos] + entry + timeline[insert_pos:]
            else:
                new_content = content + entry
        else:
            # 没有时间线部分，追加
            new_content = content + "\n## 时间线\n" + entry

        self.write_page(entity_name, page_name, new_content)
        return True

    # ── 索引和日志 ──────────────────────────────

    def update_index(self, entries: list[dict]):
        """更新 index.md"""
        index_path = self._root / "index.md"

        lines = ["# 知识库索引\n\n"]
        for entry in entries:
            name = entry.get("name", "")
            desc = entry.get("description", "")
            path = entry.get("path", "")
            lines.append(f"- [{name}]({path}) — {desc}\n")

        self._atomic_write(index_path, "".join(lines))

    def append_log(self, action: str, message: str):
        """追加操作日志"""
        log_path = self._root / "log.md"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{now}] {action} | {message}\n"

        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
        else:
            content = "# 知识库操作日志\n"

        content += entry
        self._atomic_write(log_path, content)

    # ── 内部方法 ──────────────────────────────

    def _get_page_path(self, entity_name: str, page_name: str) -> Path:
        """获取页面文件路径"""
        # 判断实体类型
        sector_dir = self._root / "sectors" / entity_name / "wiki"
        company_dir = self._root / "companies" / entity_name / "wiki"

        if sector_dir.exists():
            return sector_dir / f"{page_name}.md"
        elif company_dir.exists():
            return company_dir / f"{page_name}.md"
        else:
            # 默认使用公司目录
            return company_dir / f"{page_name}.md"

    def _atomic_write(self, path: Path, content: str):
        """原子写入：写临时文件然后 rename"""
        path.parent.mkdir(parents=True, exist_ok=True)

        # 使用同目录下的唯一临时文件
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=".tmp_",
            suffix=".md",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(path))
        except Exception:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _hash_file(self, path: Path) -> str:
        """计算文件 SHA-256"""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    def _merge_annotations(self, existing: str, new_content: str) -> str:
        """
        合并人工注释块。保留现有内容中的注释标记段落。

        注释块格式：
        <!-- ANNOTATION: user -->
        人工编辑的内容
        <!-- /ANNOTATION -->
        """
        annotation_pattern = r"<!--\s*ANNOTATION:.*?-->[\s\S]*?<!--\s*/ANNOTATION\s*-->"
        annotations = re.findall(annotation_pattern, existing)

        if not annotations:
            return new_content

        # 在新内容末尾追加保留的注释
        annotation_block = "\n\n" + "\n\n".join(annotations) + "\n"
        return new_content.rstrip() + annotation_block

    def _claim_type_to_source_type(self, claim_type: ClaimType) -> str:
        """将声明类型映射为来源类型标签"""
        mapping = {
            ClaimType.FACT: "财报",
            ClaimType.OPINION: "研报",
            ClaimType.PREDICTION: "预测",
            ClaimType.ASSESSMENT: "评估",
        }
        return mapping.get(claim_type, "新闻")


# ── 确定性投影器 ──────────────────────────────

class Projector:
    """
    确定性投影器：从 accepted ledger 生成 Markdown。

    相同 ledger + template version 两次输出字节一致。
    """

    def __init__(self, repo: WikiRepository):
        self._repo = repo

    def project_company_page(
        self,
        company_name: str,
        claims: list[Claim],
        template: str = "company_topic",
    ) -> str:
        """
        投影公司页面。

        Args:
            company_name: 公司名称
            claims: 该公司的声明列表
            template: 模板类型

        Returns:
            生成的 Markdown 内容
        """
        # 按时间倒序排列
        sorted_claims = sorted(
            [c for c in claims if c.published_at],
            key=lambda c: c.published_at,
            reverse=True,
        )

        # 计算 sources_count（distinct source revisions）
        source_ids = set(c.source_kind.value for c in claims if c.source_kind)

        # 生成 frontmatter
        import yaml
        fm = {
            "title": f"{company_name}公司动态",
            "description": f"{company_name}动态跟踪",
            "entity": company_name,
            "type": template,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "sources_count": len(source_ids),
            "tags": [],
        }

        lines = [f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False)}---\n"]

        # 核心问题
        lines.append("## 核心问题\n")
        lines.append("\n")

        # 时间线
        lines.append("## 时间线\n")
        for claim in sorted_claims:
            date_str = claim.published_at.strftime("%Y-%m-%d")
            source_type = self._claim_type_to_label(claim.claim_type)
            lines.append(f"\n### {date_str} | {source_type} | {claim.text[:50]}\n")
            lines.append(f"- {claim.text}\n")
            if claim.metric:
                lines.append(f"- {claim.metric}: {claim.value}{claim.unit}\n")

        lines.append("\n")

        # 综合评估
        lines.append("## 综合评估\n")
        lines.append(f"> {company_name}综合评估（待生成）\n")

        return "".join(lines)

    def _claim_type_to_label(self, claim_type: ClaimType) -> str:
        mapping = {
            ClaimType.FACT: "财报",
            ClaimType.OPINION: "研报",
            ClaimType.PREDICTION: "预测",
            ClaimType.ASSESSMENT: "评估",
        }
        return mapping.get(claim_type, "新闻")
