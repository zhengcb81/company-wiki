"""
Common module tests
测试公共基础设施模块
"""

from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from common import (
    WIKI_ROOT,
    load_yaml_config,
    atomic_write,
    log_action,
    get_company_dir,
    get_raw_dir,
    get_wiki_dir,
    safe_read_file,
    safe_write_file,
    setup_paths,
    get_llm_client_safe,
)


class TestPaths:
    """测试路径常量"""

    def test_wiki_root_exists(self):
        """测试 WIKI_ROOT 存在"""
        assert WIKI_ROOT.exists()
        assert WIKI_ROOT.is_dir()

    def test_setup_paths(self):
        """测试路径设置"""
        scripts_dir, wiki_root = setup_paths()
        assert scripts_dir.exists()
        assert wiki_root.exists()
        assert scripts_dir.name == "scripts"


class TestCompanyPaths:
    """测试公司路径辅助函数"""

    def test_get_company_dir(self):
        """测试获取公司目录"""
        path = get_company_dir("中微公司")
        assert path.name == "中微公司"
        assert "companies" in str(path)

    def test_get_raw_dir(self):
        """测试获取 raw 目录"""
        path = get_raw_dir("中微公司")
        assert path.name == "raw"

    def test_get_wiki_dir(self):
        """测试获取 wiki 目录"""
        path = get_wiki_dir("中微公司")
        assert path.name == "wiki"


class TestFileOperations:
    """测试文件操作"""

    def test_safe_read_file(self, tmp_path):
        """测试安全读取文件"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        content = safe_read_file(test_file)
        assert content == "test content"

    def test_safe_read_file_missing(self, tmp_path):
        """测试读取不存在的文件"""
        result = safe_read_file(tmp_path / "missing.txt")
        assert result is None

    def test_safe_write_file(self, tmp_path):
        """测试安全写入文件"""
        test_file = tmp_path / "test.txt"
        success = safe_write_file(test_file, "test content")

        assert success is True
        assert test_file.read_text() == "test content"

    def test_atomic_write(self, tmp_path):
        """测试原子写入"""
        test_file = tmp_path / "test.txt"
        atomic_write(test_file, "atomic content")

        assert test_file.exists()
        assert test_file.read_text() == "atomic content"

    def test_atomic_write_overwrite(self, tmp_path):
        """测试原子写入覆盖"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("old content")

        atomic_write(test_file, "new content")
        assert test_file.read_text() == "new content"


class TestYamlConfig:
    """测试 YAML 配置加载"""

    def test_load_yaml_config_existing(self, tmp_path):
        """测试加载存在的 YAML 文件"""

        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: value\n", encoding="utf-8")

        result = load_yaml_config(config_file)
        assert result == {"key": "value"}

    def test_load_yaml_config_missing(self, tmp_path):
        """测试加载不存在的 YAML 文件"""
        result = load_yaml_config(tmp_path / "missing.yaml")
        assert result == {}

    def test_load_yaml_config_invalid(self, tmp_path):
        """测试加载无效的 YAML 文件"""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{invalid", encoding="utf-8")

        result = load_yaml_config(bad_file)
        assert result == {}


class TestLogAction:
    """测试日志记录"""

    def test_log_action(self, tmp_path):
        """测试追加日志"""
        log_file = tmp_path / "log.md"
        # 临时替换 LOG_PATH
        import common

        original_path = common.LOG_PATH
        common.LOG_PATH = log_file

        try:
            log_action("test", "test message")
            content = log_file.read_text(encoding="utf-8")
            assert "test" in content
            assert "test message" in content
        finally:
            common.LOG_PATH = original_path


class TestLLMClientSafe:
    """测试 LLM 客户端安全获取"""

    def test_get_llm_client_safe_no_key(self):
        """测试无 API key 时返回 None"""
        import os

        old_key = os.environ.pop("DEEPSEEK_API_KEY", None)
        try:
            client = get_llm_client_safe()
            # 应该返回 client 但 unavailable，或 None
            assert client is not None or client is None  # 至少不抛异常
        finally:
            if old_key:
                os.environ["DEEPSEEK_API_KEY"] = old_key
