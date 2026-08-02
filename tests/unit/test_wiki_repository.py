"""
tests/unit/test_wiki_repository.py — WikiRepository 和 Projector 测试
"""

from datetime import datetime


from company_wiki.domain import Claim, ClaimType, SourceKind
from company_wiki.wiki_repository import Projector, WikiRepository


def _make_claim(text: str, claim_type: ClaimType = ClaimType.FACT, published_at=None, **kwargs) -> Claim:
    """Helper to create Claim with required fields"""
    return Claim(
        claim_id="test-claim-001",
        entity_id="test-entity",
        source_kind=SourceKind.REGULATORY,
        claim_type=claim_type,
        text=text,
        published_at=published_at,
        **kwargs,
    )


# ── WikiRepository 测试 ──────────────────────────────

class TestWikiRepository:
    def test_write_page_atomic(self, tmp_path):
        """测试原子写入"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        # 创建目录结构
        (wiki / "companies" / "北方华创" / "wiki").mkdir(parents=True)

        repo = WikiRepository(wiki)

        # 写入页面
        before, after = repo.write_page("北方华创", "公司动态", "# 测试\n内容")

        assert before == ""  # 新文件
        assert len(after) == 16  # SHA-256 前16位

        # 验证内容
        content = (wiki / "companies" / "北方华创" / "wiki" / "公司动态.md").read_text(encoding="utf-8")
        assert "# 测试" in content

    def test_write_page_updates_hash(self, tmp_path):
        """测试写入更新 hash"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "companies" / "测试公司" / "wiki").mkdir(parents=True)

        repo = WikiRepository(wiki)

        # 第一次写入
        _, hash1 = repo.write_page("测试公司", "公司动态", "内容1")

        # 第二次写入
        before, after = repo.write_page("测试公司", "公司动态", "内容2")

        assert before == hash1  # before 是旧内容的 hash
        assert after != hash1   # after 是新内容的 hash

    def test_read_page_returns_content(self, tmp_path):
        """测试读取页面"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "companies" / "测试公司" / "wiki").mkdir(parents=True)
        (wiki / "companies" / "测试公司" / "wiki" / "公司动态.md").write_text("test content", encoding="utf-8")

        repo = WikiRepository(wiki)
        content = repo.read_page("测试公司", "公司动态")

        assert content == "test content"

    def test_read_page_returns_none_for_missing(self, tmp_path):
        """测试读取不存在的页面返回 None"""
        repo = WikiRepository(tmp_path / "wiki")
        assert repo.read_page("不存在的公司") is None

    def test_read_frontmatter(self, tmp_path):
        """测试读取 frontmatter"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "companies" / "测试公司" / "wiki").mkdir(parents=True)

        fm_content = "---\ntitle: 测试\ntype: company_topic\n---\n正文"
        (wiki / "companies" / "测试公司" / "wiki" / "公司动态.md").write_text(fm_content, encoding="utf-8")

        repo = WikiRepository(wiki)
        fm = repo.read_frontmatter("测试公司", "公司动态")

        assert fm["title"] == "测试"
        assert fm["type"] == "company_topic"

    def test_update_frontmatter(self, tmp_path):
        """测试更新 frontmatter"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "companies" / "测试公司" / "wiki").mkdir(parents=True)

        fm_content = "---\ntitle: 测试\nlast_updated: 2026-01-01\n---\n正文"
        (wiki / "companies" / "测试公司" / "wiki" / "公司动态.md").write_text(fm_content, encoding="utf-8")

        repo = WikiRepository(wiki)
        before, after = repo.update_frontmatter("测试公司", "公司动态", {"last_updated": "2026-07-10"})

        assert after != ""
        fm = repo.read_frontmatter("测试公司", "公司动态")
        assert fm["last_updated"] == "2026-07-10"

    def test_append_timeline_entry(self, tmp_path):
        """测试追加时间线条目"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "companies" / "测试公司" / "wiki").mkdir(parents=True)

        content = "---\ntitle: 测试\n---\n## 时间线\n\n### 2026-01-01 | 新闻 | 旧条目\n- 旧内容\n"
        (wiki / "companies" / "测试公司" / "wiki" / "公司动态.md").write_text(content, encoding="utf-8")

        repo = WikiRepository(wiki)

        claim = _make_claim(
            text="新条目内容",
            published_at=datetime(2026, 7, 10),
        )

        result = repo.append_timeline_entry("测试公司", "公司动态", claim, "raw/test.md")
        assert result is True

        updated = repo.read_page("测试公司", "公司动态")
        assert "2026-07-10" in updated
        assert "新条目内容" in updated

    def test_protect_annotations(self, tmp_path):
        """测试保护人工注释块"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "companies" / "测试公司" / "wiki").mkdir(parents=True)

        content = "原始内容\n<!-- ANNOTATION: user -->\n人工备注\n<!-- /ANNOTATION -->\n"
        (wiki / "companies" / "测试公司" / "wiki" / "公司动态.md").write_text(content, encoding="utf-8")

        repo = WikiRepository(wiki)
        repo.write_page("测试公司", "公司动态", "新内容", protect_annotations=True)

        updated = repo.read_page("测试公司", "公司动态")
        assert "新内容" in updated
        assert "人工备注" in updated  # 注释被保留

    def test_sector_page(self, tmp_path):
        """测试行业页面写入"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "sectors" / "半导体设备" / "wiki").mkdir(parents=True)

        repo = WikiRepository(wiki)
        before, after = repo.write_page("半导体设备", "行业概览", "行业内容")

        assert after != ""
        assert repo.read_page("半导体设备", "行业概览") == "行业内容"

    def test_update_index(self, tmp_path):
        """测试更新索引"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        repo = WikiRepository(wiki)
        repo.update_index([
            {"name": "北方华创", "description": "测试", "path": "companies/北方华创/wiki/公司动态.md"},
        ])

        index = (wiki / "index.md").read_text(encoding="utf-8")
        assert "北方华创" in index

    def test_append_log(self, tmp_path):
        """测试追加日志"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        repo = WikiRepository(wiki)
        repo.append_log("INGEST", "处理了5条新闻")

        log = (wiki / "log.md").read_text(encoding="utf-8")
        assert "INGEST" in log
        assert "处理了5条新闻" in log

    def test_atomic_write_failure_cleanup(self, tmp_path):
        """测试原子写入失败时清理临时文件"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "companies" / "测试公司" / "wiki").mkdir(parents=True)

        repo = WikiRepository(wiki)

        # 写入一个文件
        repo.write_page("测试公司", "公司动态", "原始内容")

        # 验证没有残留的临时文件
        page_dir = wiki / "companies" / "测试公司" / "wiki"
        tmp_files = list(page_dir.glob(".tmp_*"))
        assert len(tmp_files) == 0


# ── Projector 测试 ──────────────────────────────

class TestProjector:
    def test_project_company_page_basic(self, tmp_path):
        """测试基本公司页面投影"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "companies" / "测试公司" / "wiki").mkdir(parents=True)

        repo = WikiRepository(wiki)
        projector = Projector(repo)

        claims = [
            _make_claim(
                text="营收增长20%",
                published_at=datetime(2026, 7, 10),
                metric="营收增速",
                value="20",
                unit="%",
            ),
            _make_claim(
                text="市场前景乐观",
                claim_type=ClaimType.OPINION,
                published_at=datetime(2026, 6, 15),
            ),
        ]

        result = projector.project_company_page("测试公司", claims)

        assert "测试公司" in result
        assert "营收增长20%" in result
        assert "2026-07-10" in result
        assert "2026-06-15" in result
        assert "---" in result  # frontmatter

    def test_project_deterministic(self, tmp_path):
        """测试投影确定性：相同输入输出一致"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "测试公司" / "wiki").mkdir(parents=True)

        repo = WikiRepository(wiki)
        projector = Projector(repo)

        claims = [
            _make_claim(
                text="测试内容",
                published_at=datetime(2026, 7, 10),
            ),
        ]

        # 投影两次
        result1 = projector.project_company_page("测试公司", claims)
        result2 = projector.project_company_page("测试公司", claims)

        assert result1 == result2  # 确定性

    def test_project_sorted_by_date_desc(self, tmp_path):
        """测试按时间倒序排列"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        repo = WikiRepository(wiki)
        projector = Projector(repo)

        claims = [
            _make_claim(
                text="旧新闻",
                published_at=datetime(2026, 1, 1),
            ),
            _make_claim(
                text="新新闻",
                published_at=datetime(2026, 7, 10),
            ),
        ]

        result = projector.project_company_page("测试公司", claims)

        # 新闻应该在前面
        new_pos = result.find("2026-07-10")
        old_pos = result.find("2026-01-01")
        assert new_pos < old_pos

    def test_project_with_metric(self, tmp_path):
        """测试包含指标的投影"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        repo = WikiRepository(wiki)
        projector = Projector(repo)

        claims = [
            _make_claim(
                text="业绩快报",
                published_at=datetime(2026, 7, 10),
                metric="净利润",
                value="15.2",
                unit="亿元",
            ),
        ]

        result = projector.project_company_page("测试公司", claims)

        assert "净利润" in result
        assert "15.2" in result
        assert "亿元" in result

    def test_claim_type_to_label(self, tmp_path):
        """测试声明类型映射"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        repo = WikiRepository(wiki)
        projector = Projector(repo)

        test_cases = [
            (ClaimType.FACT, "财报"),
            (ClaimType.OPINION, "研报"),
            (ClaimType.PREDICTION, "预测"),
            (ClaimType.ASSESSMENT, "评估"),
        ]

        for claim_type, expected_label in test_cases:
            claims = [
                _make_claim(
                    text="测试",
                    claim_type=claim_type,
                    published_at=datetime(2026, 1, 1),
                ),
            ]
            result = projector.project_company_page("测试公司", claims)
            assert expected_label in result, f"{claim_type} should map to {expected_label}"

    def test_empty_claims(self, tmp_path):
        """测试空声明列表"""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        repo = WikiRepository(wiki)
        projector = Projector(repo)

        result = projector.project_company_page("测试公司", [])

        assert "测试公司" in result
        assert "---" in result  # frontmatter
        assert "## 时间线" in result
