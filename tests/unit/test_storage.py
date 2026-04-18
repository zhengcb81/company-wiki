"""
存储层测试
验证 SQLite 存储实现
"""
import pytest
import tempfile
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from storage import Database, CompanyRepository, SectorRepository, WikiRepository, IngestedFileRepository


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    db = Database(db_path)
    yield db
    
    # 清理
    db.close()
    db_path.unlink(missing_ok=True)


class TestDatabase:
    """测试数据库"""
    
    def test_init(self, temp_db):
        """测试初始化"""
        assert temp_db.db_path.exists()
        
        # 检查表是否存在
        tables = temp_db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t["name"] for t in tables]
        
        assert "companies" in table_names
        assert "sectors" in table_names
        assert "themes" in table_names
        assert "edges" in table_names
        assert "wiki_entries" in table_names
        assert "ingested_files" in table_names
    
    def test_execute(self, temp_db):
        """测试执行 SQL"""
        # 插入数据
        temp_db.execute(
            "INSERT INTO companies (name, ticker, exchange) VALUES (?, ?, ?)",
            ("中微公司", "688012", "SSE STAR")
        )
        
        # 查询数据
        results = temp_db.execute("SELECT * FROM companies WHERE name = ?", ("中微公司",))
        
        assert len(results) == 1
        assert results[0]["name"] == "中微公司"
        assert results[0]["ticker"] == "688012"
    
    def test_execute_one(self, temp_db):
        """测试执行单条查询"""
        # 插入数据
        temp_db.execute(
            "INSERT INTO companies (name, ticker, exchange) VALUES (?, ?, ?)",
            ("中微公司", "688012", "SSE STAR")
        )
        
        # 查询数据
        result = temp_db.execute_one("SELECT * FROM companies WHERE name = ?", ("中微公司",))
        
        assert result is not None
        assert result["name"] == "中微公司"
    
    def test_execute_insert(self, temp_db):
        """测试插入操作"""
        # 插入数据
        row_id = temp_db.execute_insert(
            "INSERT INTO companies (name, ticker, exchange) VALUES (?, ?, ?)",
            ("中微公司", "688012", "SSE STAR")
        )
        
        assert row_id > 0
    
    def test_execute_update(self, temp_db):
        """测试更新操作"""
        # 插入数据
        temp_db.execute(
            "INSERT INTO companies (name, ticker, exchange) VALUES (?, ?, ?)",
            ("中微公司", "688012", "SSE STAR")
        )
        
        # 更新数据
        affected = temp_db.execute_update(
            "UPDATE companies SET ticker = ? WHERE name = ?",
            ("002371", "中微公司")
        )
        
        assert affected == 1
        
        # 验证更新
        result = temp_db.execute_one("SELECT * FROM companies WHERE name = ?", ("中微公司",))
        assert result["ticker"] == "002371"
    
    def test_get_stats(self, temp_db):
        """测试获取统计信息"""
        # 插入数据
        temp_db.execute(
            "INSERT INTO companies (name, ticker, exchange) VALUES (?, ?, ?)",
            ("中微公司", "688012", "SSE STAR")
        )
        temp_db.execute(
            "INSERT INTO companies (name, ticker, exchange) VALUES (?, ?, ?)",
            ("北方华创", "002371", "SZSE")
        )
        
        # 获取统计
        stats = temp_db.get_stats()
        
        assert stats["companies"] == 2
        assert stats["sectors"] == 0
        assert stats["themes"] == 0


class TestCompanyRepository:
    """测试公司数据访问层"""
    
    def test_create(self, temp_db):
        """测试创建公司"""
        repo = CompanyRepository(temp_db)
        
        company = {
            "name": "中微公司",
            "ticker": "688012",
            "exchange": "SSE STAR",
            "position": "刻蚀设备龙头",
            "sectors": ["半导体设备"],
            "themes": ["AI产业链"],
            "news_queries": ["中微公司 最新消息"],
            "aliases": ["688012", "AMEC"],
        }
        
        row_id = repo.create(company)
        assert row_id > 0
        
        # 验证创建
        created = repo.get_by_name("中微公司")
        assert created is not None
        assert created["ticker"] == "688012"
        assert created["exchange"] == "SSE STAR"
        assert "半导体设备" in created["sectors"]
    
    def test_get_all(self, temp_db):
        """测试获取所有公司"""
        repo = CompanyRepository(temp_db)
        
        # 创建多个公司
        repo.create({"name": "中微公司", "ticker": "688012"})
        repo.create({"name": "北方华创", "ticker": "002371"})
        
        # 获取所有
        companies = repo.get_all()
        
        assert len(companies) == 2
        names = [c["name"] for c in companies]
        assert "中微公司" in names
        assert "北方华创" in names
    
    def test_get_by_name(self, temp_db):
        """测试根据名称获取公司"""
        repo = CompanyRepository(temp_db)
        
        repo.create({"name": "中微公司", "ticker": "688012"})
        
        # 存在的公司
        company = repo.get_by_name("中微公司")
        assert company is not None
        assert company["name"] == "中微公司"
        
        # 不存在的公司
        company = repo.get_by_name("不存在的公司")
        assert company is None
    
    def test_get_by_ticker(self, temp_db):
        """测试根据 ticker 获取公司"""
        repo = CompanyRepository(temp_db)
        
        repo.create({"name": "中微公司", "ticker": "688012"})
        
        # 存在的 ticker
        company = repo.get_by_ticker("688012")
        assert company is not None
        assert company["name"] == "中微公司"
        
        # 不存在的 ticker
        company = repo.get_by_ticker("999999")
        assert company is None
    
    def test_update(self, temp_db):
        """测试更新公司"""
        repo = CompanyRepository(temp_db)
        
        repo.create({"name": "中微公司", "ticker": "688012"})
        
        # 更新
        affected = repo.update("中微公司", {"ticker": "002371"})
        assert affected == 1
        
        # 验证更新
        company = repo.get_by_name("中微公司")
        assert company["ticker"] == "002371"
    
    def test_delete(self, temp_db):
        """测试删除公司"""
        repo = CompanyRepository(temp_db)
        
        repo.create({"name": "中微公司", "ticker": "688012"})
        
        # 删除
        affected = repo.delete("中微公司")
        assert affected == 1
        
        # 验证删除
        company = repo.get_by_name("中微公司")
        assert company is None
    
    def test_count(self, temp_db):
        """测试获取公司数量"""
        repo = CompanyRepository(temp_db)
        
        assert repo.count() == 0
        
        repo.create({"name": "中微公司", "ticker": "688012"})
        assert repo.count() == 1
        
        repo.create({"name": "北方华创", "ticker": "002371"})
        assert repo.count() == 2


class TestSectorRepository:
    """测试行业数据访问层"""
    
    def test_create(self, temp_db):
        """测试创建行业"""
        repo = SectorRepository(temp_db)
        
        sector = {
            "name": "半导体设备",
            "type": "sector",
            "description": "半导体制造设备",
            "tier": 5,
            "keywords": ["半导体设备", "芯片设备"],
            "parent_theme": ["AI产业链"],
        }
        
        row_id = repo.create(sector)
        assert row_id > 0
        
        # 验证创建
        created = repo.get_by_name("半导体设备")
        assert created is not None
        assert created["description"] == "半导体制造设备"
        assert created["tier"] == 5
        assert "半导体设备" in created["keywords"]
    
    def test_get_all(self, temp_db):
        """测试获取所有行业"""
        repo = SectorRepository(temp_db)
        
        # 创建多个行业
        repo.create({"name": "半导体设备", "type": "sector"})
        repo.create({"name": "半导体材料", "type": "sector"})
        
        # 获取所有
        sectors = repo.get_all()
        
        assert len(sectors) == 2
        names = [s["name"] for s in sectors]
        assert "半导体设备" in names
        assert "半导体材料" in names
    
    def test_get_by_type(self, temp_db):
        """测试根据类型获取行业"""
        repo = SectorRepository(temp_db)
        
        repo.create({"name": "半导体设备", "type": "sector"})
        repo.create({"name": "刻蚀设备", "type": "subsector"})
        
        # 获取 sector
        sectors = repo.get_by_type("sector")
        assert len(sectors) == 1
        assert sectors[0]["name"] == "半导体设备"
        
        # 获取 subsector
        subsectors = repo.get_by_type("subsector")
        assert len(subsectors) == 1
        assert subsectors[0]["name"] == "刻蚀设备"


class TestWikiRepository:
    """测试 Wiki 条目数据访问层"""
    
    def test_create(self, temp_db):
        """测试创建 Wiki 条目"""
        repo = WikiRepository(temp_db)
        
        entry = {
            "entity_name": "中微公司",
            "entity_type": "company",
            "topic_name": "公司动态",
            "content": "# 中微公司 — 公司动态\n\n## 时间线\n\n（暂无条目）",
            "last_updated": "2026-04-17",
            "sources_count": 0,
        }
        
        row_id = repo.create(entry)
        assert row_id > 0
        
        # 验证创建
        created = repo.get_by_topic("中微公司", "company", "公司动态")
        assert created is not None
        assert created["content"] == entry["content"]
    
    def test_upsert(self, temp_db):
        """测试创建或更新 Wiki 条目"""
        repo = WikiRepository(temp_db)
        
        entry = {
            "entity_name": "中微公司",
            "entity_type": "company",
            "topic_name": "公司动态",
            "content": "# 中微公司 — 公司动态\n\n## 时间线\n\n（暂无条目）",
            "last_updated": "2026-04-17",
            "sources_count": 0,
        }
        
        # 第一次 upsert（创建）
        repo.upsert(entry)
        
        # 第二次 upsert（更新）
        entry["content"] = "# 中微公司 — 公司动态\n\n## 时间线\n\n### 2026-04-17 | 新闻 | 测试新闻\n- 测试内容"
        entry["sources_count"] = 1
        repo.upsert(entry)
        
        # 验证更新
        updated = repo.get_by_topic("中微公司", "company", "公司动态")
        assert updated["sources_count"] == 1
        assert "测试新闻" in updated["content"]


class TestIngestedFileRepository:
    """测试已处理文件数据访问层"""
    
    def test_create_and_exists(self, temp_db):
        """测试创建和检查存在"""
        repo = IngestedFileRepository(temp_db)
        
        file_hash = "abc123def456"
        file_path = "/path/to/file.md"
        
        # 创建
        row_id = repo.create(file_hash, file_path)
        assert row_id > 0
        
        # 检查存在
        assert repo.exists(file_hash)
        assert not repo.exists("nonexistent_hash")
    
    def test_count(self, temp_db):
        """测试获取已处理文件数量"""
        repo = IngestedFileRepository(temp_db)
        
        assert repo.count() == 0
        
        repo.create("hash1", "/path/to/file1.md")
        assert repo.count() == 1
        
        repo.create("hash2", "/path/to/file2.md")
        assert repo.count() == 2


@pytest.mark.unit
def test_storage_module_import():
    """测试存储模块导入"""
    from storage import Database, CompanyRepository, SectorRepository, WikiRepository, IngestedFileRepository, DataMigrator
    
    assert Database is not None
    assert CompanyRepository is not None
    assert SectorRepository is not None
    assert WikiRepository is not None
    assert IngestedFileRepository is not None
    assert DataMigrator is not None
    
    print("✓ 存储模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])