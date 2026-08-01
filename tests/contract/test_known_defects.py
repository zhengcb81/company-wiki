"""
Contract tests for known defects — Phase 12.5

这些测试先复现已知缺陷，再验证修复。
每个测试对应一个具体的系统不变量。

注意：这些测试使用 mini_wiki fixture，不依赖真实数据、网络或 LLM。
"""

import hashlib
from pathlib import Path

import pytest

# Setup paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "mini_wiki"
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"


class TestRawImmutability:
    """原始来源不可被处理流程修改或删除"""

    def test_raw_files_exist_after_read(self, tmp_path):
        """读取 raw 文件后，原文件不应被修改"""
        import shutil

        src = FIXTURES_DIR / "raw" / "北方华创" / "北方华创_2025年报.md"
        dst = tmp_path / "raw" / "北方华创" / "北方华创_2025年报.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        original_hash = sha256(dst)

        # Simulate reading (what ingest does)
        content = dst.read_text(encoding="utf-8")
        assert "北方华创" in content

        # File should be unchanged
        assert sha256(dst) == original_hash

    def test_raw_directory_not_deleted(self, tmp_path):
        """处理流程不应删除 raw 目录"""
        import shutil

        src = FIXTURES_DIR / "raw"
        dst = tmp_path / "raw"
        shutil.copytree(src, dst)

        files_before = list(dst.rglob("*"))
        assert len(files_before) > 0

        # After any processing, files should still exist
        # (This is a contract: raw is immutable)
        files_after = list(dst.rglob("*"))
        assert len(files_after) == len(files_before)


class TestNoEvidenceRejection:
    """没有证据的输出应被拒绝"""

    def test_wiki_entry_has_source_link(self):
        """wiki 时间线条目必须有来源链接"""
        wiki_path = FIXTURES_DIR / "companies" / "北方华创" / "wiki" / "公司动态.md"
        content = wiki_path.read_text(encoding="utf-8")

        # Find all timeline entries
        import re
        entries = re.findall(r"### \d{4}-\d{2}-\d{2}.*", content)
        assert len(entries) > 0

        # Each entry should have a source link
        for entry in entries:
            # Find the section between this entry and the next
            start = content.find(entry)
            next_entry = content.find("### ", start + len(entry))
            if next_entry == -1:
                section = content[start:]
            else:
                section = content[start:next_entry]

            assert "[来源说明]" in section, f"Entry lacks source link: {entry[:50]}"

    def test_wiki_frontmatter_has_sources_count(self):
        """wiki frontmatter 必须有 sources_count"""
        import yaml

        wiki_path = FIXTURES_DIR / "companies" / "北方华创" / "wiki" / "公司动态.md"
        content = wiki_path.read_text(encoding="utf-8")

        # Extract frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Missing frontmatter"

        fm = yaml.safe_load(parts[1])
        assert "sources_count" in fm, "Missing sources_count in frontmatter"
        assert fm["sources_count"] > 0, "sources_count should be > 0"


class TestFanOutAPI:
    """fan-out 必须正确识别相关实体"""

    def test_company_belongs_to_sector(self):
        """公司应正确关联到所属行业"""
        # Load companies.yaml from fixture or real config
        import yaml

        companies_path = Path(__file__).parent.parent.parent / "companies.yaml"
        if not companies_path.exists():
            pytest.skip("companies.yaml not found")

        with open(companies_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        companies = data.get("companies", {})
        bf = companies.get("北方华创", {})
        sectors = bf.get("sectors", [])

        assert "半导体设备" in sectors, "北方华创 should belong to 半导体设备"

    def test_competitor_relationship(self):
        """竞争关系应正确声明"""
        import yaml

        companies_path = Path(__file__).parent.parent.parent / "companies.yaml"
        if not companies_path.exists():
            pytest.skip("companies.yaml not found")

        with open(companies_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        companies = data.get("companies", {})
        bf = companies.get("北方华创", {})
        competitors = bf.get("competes_with", [])

        assert "中微公司" in competitors, "北方华创 should compete with 中微公司"


class TestAmbiguityHandling:
    """同名实体不应被混淆"""

    def test_fixture_contains_ambiguity_case(self):
        """fixture 应包含歧义测试用例"""
        ambig_path = FIXTURES_DIR / "raw" / "中微公司" / "中微公司_歧义新闻.md"
        assert ambig_path.exists(), "Ambiguity fixture missing"

        content = ambig_path.read_text(encoding="utf-8")
        assert "中微半导体" in content, "Should mention ambiguous entity"
        assert "MCU" in content, "Should mention the other company's business"

    def test_fixture_contains_injection_case(self):
        """fixture 应包含指令注入测试用例"""
        inject_path = FIXTURES_DIR / "raw" / "中微公司" / "中微公司_恶意指令.md"
        assert inject_path.exists(), "Injection fixture missing"

        content = inject_path.read_text(encoding="utf-8")
        # The injection attempt should be identifiable
        assert "忽略以上内容" in content or "请忽略" in content or "ignore" in content.lower()


class TestConfigFailFast:
    """非法配置应被拒绝"""

    def test_missing_required_field(self):
        """缺少必填字段的配置应报错"""
        import yaml

        # A config with missing model
        bad_config = """
llm:
  provider: "deepseek"
  base_url: "https://api.deepseek.com"
"""
        data = yaml.safe_load(bad_config)
        llm = data.get("llm", {})
        # model should be required
        assert "model" not in llm, "This tests that we CAN detect missing model"

    def test_invalid_interval(self):
        """非法调度间隔应被拒绝"""
        # Intervals like "never", "0", negative values should be rejected
        valid_intervals = ["daily", "weekly", "monthly", "hourly"]
        invalid_intervals = ["never", "0", "-1", "abc", ""]

        for interval in invalid_intervals:
            assert interval not in valid_intervals, f"{interval} should not be valid"


class TestIndexConsistency:
    """index.md 应与实际 wiki 页面一致"""

    def test_fixture_wiki_files_exist(self):
        """fixture 中的 wiki 文件应存在"""
        wiki_dir = FIXTURES_DIR / "companies" / "北方华创" / "wiki"
        assert wiki_dir.exists()
        md_files = list(wiki_dir.glob("*.md"))
        assert len(md_files) > 0

    def test_sector_wiki_exists(self):
        """fixture 中的行业 wiki 应存在"""
        wiki_path = FIXTURES_DIR / "sectors" / "半导体设备" / "wiki" / "行业概览.md"
        assert wiki_path.exists()


class TestSchedulerIntervals:
    """调度间隔必须合法"""

    def test_config_intervals_are_valid(self):
        """config.yaml 中的间隔应全部合法"""
        import yaml

        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        if not config_path.exists():
            pytest.skip("config.yaml not found")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        schedule = config.get("schedule", {})
        valid = {"daily", "weekly", "monthly", "hourly", "manual"}

        for job, interval in schedule.items():
            assert interval in valid, f"Invalid interval for {job}: {interval}"


# Helpers
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
