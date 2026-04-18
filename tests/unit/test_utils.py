"""
工具模块测试
测试公共工具函数
"""
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from utils import (
    log_message,
    ensure_dir,
    safe_read_file,
    safe_write_file,
    load_yaml,
    save_yaml,
    get_wiki_root,
    extract_frontmatter,
    clean_text,
    extract_keywords,
    to_bool,
    to_int,
    to_float,
    is_valid_ticker,
    is_empty_dir,
)


class TestFileOperations:
    """测试文件操作"""
    
    def test_ensure_dir(self, tmp_path):
        """测试创建目录"""
        test_dir = tmp_path / "test" / "nested" / "dir"
        result = ensure_dir(test_dir)
        
        assert result == test_dir
        assert test_dir.exists()
        assert test_dir.is_dir()
    
    def test_safe_read_file(self, tmp_path):
        """测试安全读取文件"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        content = safe_read_file(test_file)
        assert content == "test content"
    
    def test_safe_read_file_not_exists(self, tmp_path):
        """测试读取不存在的文件"""
        test_file = tmp_path / "nonexistent.txt"
        
        content = safe_read_file(test_file)
        assert content is None
    
    def test_safe_write_file(self, tmp_path):
        """测试安全写入文件"""
        test_file = tmp_path / "test.txt"
        
        result = safe_write_file(test_file, "test content")
        assert result == True
        assert test_file.read_text() == "test content"
    
    def test_safe_write_file_creates_dir(self, tmp_path):
        """测试写入文件时创建目录"""
        test_file = tmp_path / "nested" / "dir" / "test.txt"
        
        result = safe_write_file(test_file, "test content")
        assert result == True
        assert test_file.exists()


class TestYamlOperations:
    """测试 YAML 操作"""
    
    def test_load_yaml(self, tmp_path):
        """测试加载 YAML"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("""
key1: value1
key2: 123
nested:
  key3: value3
""")
        
        data = load_yaml(yaml_file)
        assert data["key1"] == "value1"
        assert data["key2"] == 123
        assert data["nested"]["key3"] == "value3"
    
    def test_load_yaml_not_exists(self, tmp_path):
        """测试加载不存在的 YAML"""
        yaml_file = tmp_path / "nonexistent.yaml"
        
        data = load_yaml(yaml_file)
        assert data == {}
    
    def test_save_yaml(self, tmp_path):
        """测试保存 YAML"""
        yaml_file = tmp_path / "test.yaml"
        data = {"key1": "value1", "key2": 123}
        
        result = save_yaml(yaml_file, data)
        assert result == True
        
        # 验证保存的内容
        loaded = load_yaml(yaml_file)
        assert loaded["key1"] == "value1"
        assert loaded["key2"] == 123


class TestPathTools:
    """测试路径工具"""
    
    def test_get_wiki_root(self):
        """测试获取 Wiki 根目录"""
        wiki_root = get_wiki_root()
        
        assert wiki_root.exists()
        assert wiki_root.is_dir()
        assert "company-wiki" in str(wiki_root)
    
    def test_get_companies_dir(self):
        """测试获取公司目录"""
        from utils import get_companies_dir
        
        companies_dir = get_companies_dir()
        assert companies_dir == get_wiki_root() / "companies"
    
    def test_get_company_dir(self):
        """测试获取指定公司目录"""
        from utils import get_company_dir
        
        company_dir = get_company_dir("中微公司")
        assert company_dir == get_wiki_root() / "companies" / "中微公司"


class TestTextProcessing:
    """测试文本处理"""
    
    def test_extract_frontmatter(self):
        """测试提取 frontmatter"""
        content = """---
title: "测试标题"
date: "2026-04-17"
---

# 内容

这是正文内容。
"""
        
        frontmatter = extract_frontmatter(content)
        assert frontmatter["title"] == "测试标题"
        assert frontmatter["date"] == "2026-04-17"
    
    def test_extract_frontmatter_no_frontmatter(self):
        """测试没有 frontmatter"""
        content = "# 标题\n\n正文内容"
        
        frontmatter = extract_frontmatter(content)
        assert frontmatter == {}
    
    def test_clean_text(self):
        """测试清理文本"""
        text = "<p>这是一段   带有HTML标签和多余空白的文本</p>"
        
        cleaned = clean_text(text)
        assert "<p>" not in cleaned
        assert "</p>" not in cleaned
        assert "  " not in cleaned
    
    def test_extract_keywords(self):
        """测试提取关键词"""
        text = "中微公司发布新一代刻蚀设备，支持5nm先进制程"
        
        keywords = extract_keywords(text)
        # 应该包含一些关键词
        assert len(keywords) > 0
        # 检查是否包含预期的词（可能是短语）
        found = any("中微" in k or "公司" in k for k in keywords)
        assert found, f"应该包含'中微'或'公司'，实际: {keywords}"
    
    def test_extract_keywords_min_length(self):
        """测试关键词最小长度"""
        text = "我你他中微公司刻蚀设备"
        
        keywords = extract_keywords(text, min_length=2)
        # 应该过滤掉单字
        assert "我" not in keywords
        assert "你" not in keywords
        assert "他" not in keywords
        
        # 应该包含2字以上的词
        assert len(keywords) > 0


class TestDataConversion:
    """测试数据转换"""
    
    def test_to_bool(self):
        """测试转换为布尔值"""
        assert to_bool("true") == True
        assert to_bool("TRUE") == True
        assert to_bool("1") == True
        assert to_bool("yes") == True
        
        assert to_bool("false") == False
        assert to_bool("FALSE") == False
        assert to_bool("0") == False
        assert to_bool("no") == False
        
        assert to_bool(True) == True
        assert to_bool(False) == False
        assert to_bool(1) == True
        assert to_bool(0) == False
    
    def test_to_int(self):
        """测试转换为整数"""
        assert to_int("123") == 123
        assert to_int(123) == 123
        assert to_int(123.45) == 123
        assert to_int("abc") == 0
        assert to_int("abc", default=99) == 99
    
    def test_to_float(self):
        """测试转换为浮点数"""
        assert to_float("3.14") == 3.14
        assert to_float(3.14) == 3.14
        assert to_float(3) == 3.0
        assert to_float("abc") == 0.0
        assert to_float("abc", default=9.9) == 9.9


class TestValidation:
    """测试验证工具"""
    
    def test_is_valid_ticker(self):
        """测试股票代码验证"""
        # A股
        assert is_valid_ticker("688012") == True
        assert is_valid_ticker("002371") == True
        
        # 美股
        assert is_valid_ticker("NVDA") == True
        assert is_valid_ticker("AMD") == True
        
        # 港股
        assert is_valid_ticker("0020.HK") == True
        
        # 无效
        assert is_valid_ticker("") == False
        assert is_valid_ticker("abc123") == False
        assert is_valid_ticker("1234567") == False  # 7位数字
    
    def test_is_empty_dir(self, tmp_path):
        """测试空目录检查"""
        # 不存在的目录
        assert is_empty_dir(tmp_path / "nonexistent") == True
        
        # 空目录
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert is_empty_dir(empty_dir) == True
        
        # 非空目录
        nonempty_dir = tmp_path / "nonempty"
        nonempty_dir.mkdir()
        (nonempty_dir / "file.txt").write_text("content")
        assert is_empty_dir(nonempty_dir) == False


@pytest.mark.unit
def test_utils_module_import():
    """测试工具模块导入"""
    from utils import (
        log_message,
        load_yaml,
        save_yaml,
        get_wiki_root,
        extract_frontmatter,
        clean_text,
        extract_keywords,
    )
    
    assert log_message is not None
    assert load_yaml is not None
    assert save_yaml is not None
    assert get_wiki_root is not None
    
    print("✅ utils 模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])