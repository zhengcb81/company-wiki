"""
核心功能测试
测试配置加载、基本功能
"""
import pytest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from config import Config, load_config


@pytest.fixture
def test_config_file(tmp_path):
    """创建测试配置文件"""
    config_content = """
schedule:
  news_collection: "daily"
  report_check: "weekly"

llm:
  provider: "deepseek"
  api_key: "sk-test-key-123"
  model: "deepseek-reasoner"
  base_url: "https://api.deepseek.com"

search:
  engine: "tavily"
  tavily_api_key: "tvly-test-key-456"
  results_per_query: 8
  language: "zh"

paths:
  wiki_root: "~/test-wiki"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def env_vars(monkeypatch):
    """设置环境变量"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-deepseek-key")
    monkeypatch.setenv("TAVILY_API_KEY", "env-tavily-key")


class TestConfig:
    """测试配置管理"""
    
    def test_load_from_file(self, test_config_file):
        """测试从文件加载配置"""
        config = load_config(test_config_file)
        
        assert config.llm.provider == "deepseek"
        assert config.llm.api_key == "sk-test-key-123"
        assert config.search.api_key == "tvly-test-key-456"
    
    def test_env_override(self, test_config_file, env_vars):
        """测试环境变量覆盖"""
        config = load_config(test_config_file)
        
        # 环境变量应该覆盖文件配置
        assert config.llm.api_key == "env-deepseek-key"
        assert config.search.api_key == "env-tavily-key"
    
    def test_validation(self, tmp_path, monkeypatch):
        """测试配置验证"""
        # 创建缺少 API Key 的配置
        config_content = """
llm:
  provider: "deepseek"
  api_key: ""
search:
  engine: "tavily"
  tavily_api_key: ""
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)
        
        # 移除测试环境变量，启用严格验证
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        
        # 应该抛出 ValueError
        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)
        
        assert "配置验证失败" in str(exc_info.value)
    
    def test_missing_file(self, tmp_path):
        """测试配置文件不存在"""
        config_file = tmp_path / "nonexistent.yaml"
        
        # 应该使用默认值
        config = load_config(config_file)
        
        assert config.llm.provider == "deepseek"
        assert config.search.engine == "tavily"
    
    def test_get_methods(self, test_config_file):
        """测试获取方法"""
        config = load_config(test_config_file)
        
        assert config.get_llm_api_key() == config.llm.api_key
        assert config.get_search_api_key() == config.search.api_key
        assert isinstance(config.get_wiki_root(), Path)
    
    def test_to_dict(self, test_config_file):
        """测试转换为字典"""
        config = load_config(test_config_file)
        
        data = config.to_dict()
        assert isinstance(data, dict)
        assert "llm" in data


class TestConfigDefaults:
    """测试配置默认值"""
    
    def test_default_values(self):
        """测试默认值"""
        from config import LLMConfig, SearchConfig, ScheduleConfig
        
        llm = LLMConfig()
        assert llm.provider == "deepseek"
        assert llm.max_tokens == 1024
        assert llm.temperature == 0.3
        
        search = SearchConfig()
        assert search.engine == "tavily"
        assert search.results_per_query == 8
        assert search.language == "zh"


@pytest.mark.unit
def test_config_module_import():
    """测试配置模块导入"""
    from config import Config, load_config, get_config
    
    assert Config is not None
    assert load_config is not None
    assert get_config is not None
    
    print("✅ 配置模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])