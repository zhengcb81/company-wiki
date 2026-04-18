"""
下载功能测试
测试文件下载和分类
"""
import pytest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


@pytest.fixture
def test_wiki_structure(tmp_path):
    """创建测试 wiki 结构"""
    wiki_root = tmp_path / "wiki"
    wiki_root.mkdir()
    
    # 创建公司目录
    company_dir = wiki_root / "companies" / "中微公司"
    company_dir.mkdir(parents=True)
    
    # 创建子目录
    (company_dir / "raw").mkdir()
    (company_dir / "raw" / "financial_reports").mkdir()
    (company_dir / "raw" / "financial_reports" / "annual").mkdir()
    (company_dir / "raw" / "financial_reports" / "quarterly").mkdir()
    (company_dir / "raw" / "prospectus").mkdir()
    (company_dir / "raw" / "investor_relations").mkdir()
    (company_dir / "raw" / "research").mkdir()
    (company_dir / "raw" / "announcements").mkdir()
    (company_dir / "raw" / "news").mkdir()
    
    return wiki_root


class TestFileClassification:
    """测试文件分类"""
    
    def test_classify_annual_report(self):
        """测试年报分类"""
        from classify_documents import classify_by_filename
        
        # 测试年报
        type_by_name, conf, reason = classify_by_filename("中微公司：2025年年度报告.pdf")
        assert type_by_name.value == "annual_report"
        assert conf >= 0.9
    
    def test_classify_quarterly_report(self):
        """测试季报分类"""
        from classify_documents import classify_by_filename
        
        # 测试季报
        type_by_name, conf, reason = classify_by_filename("中微公司：2025年一季度报告.pdf")
        assert type_by_name.value == "quarterly_report"
        assert conf >= 0.9
    
    def test_classify_prospectus(self):
        """测试招股说明书分类"""
        from classify_documents import classify_by_filename
        
        # 测试招股说明书
        type_by_name, conf, reason = classify_by_filename("中微公司：招股说明书.pdf")
        assert type_by_name.value == "prospectus"
        assert conf >= 0.9
    
    def test_classify_investor_relations(self):
        """测试投资者关系分类"""
        from classify_documents import classify_by_filename
        
        # 测试投资者关系
        type_by_name, conf, reason = classify_by_filename("中微公司：投资者关系活动记录表.pdf")
        assert type_by_name.value == "investor_relations"
        assert conf >= 0.9


class TestFileOrganization:
    """测试文件组织"""
    
    def test_get_target_directory(self, test_wiki_structure):
        """测试获取目标目录"""
        from classify_documents import classify_by_filename, TYPE_TO_DIR
        
        # 测试年报
        doc_type, conf, reason = classify_by_filename("中微公司：2025年年度报告.pdf")
        target_dir = TYPE_TO_DIR.get(doc_type)
        
        assert target_dir == "financial_reports/annual"
    
    def test_create_target_directories(self, test_wiki_structure):
        """测试创建目标目录"""
        from pathlib import Path
        
        # 模拟文件分类结果
        classifications = [
            {
                "file_path": Path("test.pdf"),
                "document_type": "annual_report",
                "target_dir": "financial_reports/annual",
                "target_path": test_wiki_structure / "companies" / "中微公司" / "raw" / "financial_reports" / "annual" / "test.pdf",
            }
        ]
        
        # 创建目录
        for c in classifications:
            c["target_path"].parent.mkdir(parents=True, exist_ok=True)
        
        # 验证目录存在
        assert (test_wiki_structure / "companies" / "中微公司" / "raw" / "financial_reports" / "annual").exists()


class TestDownloadVerification:
    """测试下载验证"""
    
    def test_verify_file_exists(self, test_wiki_structure):
        """测试验证文件存在"""
        # 创建测试文件
        test_file = test_wiki_structure / "companies" / "中微公司" / "raw" / "financial_reports" / "annual" / "test.pdf"
        test_file.write_text("test content")
        
        # 验证文件存在
        assert test_file.exists()
        assert test_file.stat().st_size > 0
    
    def test_verify_file_location(self, test_wiki_structure):
        """测试验证文件位置"""
        # 创建测试文件
        test_file = test_wiki_structure / "companies" / "中微公司" / "raw" / "financial_reports" / "annual" / "test.pdf"
        test_file.write_text("test content")
        
        # 验证文件在正确位置
        expected_path = test_wiki_structure / "companies" / "中微公司" / "raw" / "financial_reports" / "annual" / "test.pdf"
        assert test_file == expected_path


@pytest.mark.unit
def test_download_module_import():
    """测试下载模块导入"""
    from classify_documents import classify_by_filename, TYPE_TO_DIR
    
    assert classify_by_filename is not None
    assert TYPE_TO_DIR is not None
    
    print("✅ 下载模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])