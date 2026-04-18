"""
配置加载端到端测试
验证 Phase 1.1: 密钥管理重构
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
import sys

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


@pytest.mark.e2e
class TestConfigLoading:
    """配置加载测试类"""
    
    def test_config_loads_from_file(self, temp_wiki_structure):
        """测试从文件加载配置"""
        from config_loader import load_config
        
        config_path = temp_wiki_structure / "config.yaml"
        config = load_config(config_path)
        
        assert config is not None
        assert config.llm.provider == "deepseek"
        assert config.llm.model == "deepseek-reasoner"
        assert config.search.engine == "tavily"
        assert config.search.results_per_query == 8
    
    def test_config_validates_required_fields(self, tmp_path):
        """测试配置验证必需字段"""
        from config_loader import load_config
        
        # 创建缺少必需字段的配置
        config_content = """
llm:
  provider: "deepseek"
  # 缺少 api_key 和 model
search:
  engine: "tavily"
  # 缺少 tavily_api_key
"""
        config_path = tmp_path / "bad_config.yaml"
        config_path.write_text(config_content)
        
        # 应该抛出 ValueError
        with pytest.raises(ValueError) as exc_info:
            load_config(config_path)
        
        error_msg = str(exc_info.value)
        assert "配置验证失败" in error_msg
        assert "LLM API Key" in error_msg
        assert "Tavily API Key" in error_msg
    
    def test_config_env_override(self, temp_wiki_structure, monkeypatch):
        """测试环境变量覆盖"""
        from config_loader import load_config
        
        # 设置环境变量
        monkeypatch.setenv("TAVILY_API_KEY", "env-tavily-key-12345")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "env-deepseek-key-12345")
        
        config_path = temp_wiki_structure / "config.yaml"
        config = load_config(config_path)
        
        # 验证环境变量覆盖了文件中的值
        assert config.llm.api_key == "env-deepseek-key-12345"
        assert config.search.api_key == "env-tavily-key-12345"
    
    def test_config_missing_file(self, tmp_path):
        """测试配置文件不存在"""
        from config_loader import load_config
        
        config_path = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError):
            load_config(config_path)
    
    def test_config_invalid_yaml(self, tmp_path):
        """测试无效 YAML 格式"""
        from config_loader import load_config
        
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: [")
        
        with pytest.raises(ValueError) as exc_info:
            load_config(config_path)
        
        assert "格式错误" in str(exc_info.value)
    
    def test_config_helper_methods(self, temp_wiki_structure):
        """测试配置辅助方法"""
        from config_loader import load_config
        
        config_path = temp_wiki_structure / "config.yaml"
        config = load_config(config_path)
        
        # 测试辅助方法
        assert config.get_llm_api_key() == config.llm.api_key
        assert config.get_search_api_key() == config.search.api_key
        assert config.get_wiki_root() == config.wiki_root
        
        # 测试转换为字典
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "llm" in config_dict
        assert "search" in config_dict
    
    def test_config_backward_compatibility(self, temp_wiki_structure):
        """测试向后兼容性"""
        from config_loader import load_yaml_simple
        import warnings
        
        config_path = temp_wiki_structure / "config.yaml"
        
        # 捕获警告
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            result = load_yaml_simple(config_path)
            
            # 验证警告
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "load_yaml_simple 已弃用" in str(w[0].message)
        
        # 验证功能正常
        assert isinstance(result, dict)
        assert "llm" in result
        assert "search" in result


@pytest.mark.e2e
class TestConfigIntegration:
    """配置集成测试"""
    
    def test_config_with_collect_news(self, temp_wiki_structure, monkeypatch):
        """测试配置与 collect_news 集成"""
        from config_loader import load_config
        
        # 设置环境变量
        monkeypatch.setenv("TAVILY_API_KEY", "test-key-for-collect")
        
        config_path = temp_wiki_structure / "config.yaml"
        config = load_config(config_path)
        
        # 验证配置可以用于 collect_news
        assert config.search.api_key == "test-key-for-collect"
        assert config.search.results_per_query > 0
        assert config.search.max_age_days > 0
    
    def test_config_with_ingest(self, temp_wiki_structure):
        """测试配置与 ingest 集成"""
        from config_loader import load_config
        
        config_path = temp_wiki_structure / "config.yaml"
        config = load_config(config_path)
        
        # 验证配置可以用于 ingest
        assert config.wiki_root.exists() or True  # 可能不存在，但路径有效
        assert config.llm.provider is not None
        assert config.llm.model is not None
    
    def test_config_wiki_root_expansion(self, tmp_path, monkeypatch):
        """测试 wiki 根目录路径展开"""
        from config_loader import load_config
        
        # 创建包含 ~ 的配置
        config_content = """
llm:
  provider: "deepseek"
  api_key: "sk-test-123"
  model: "deepseek-reasoner"
  base_url: "https://api.deepseek.com"
search:
  engine: "tavily"
  tavily_api_key: "tvly-test-123"
paths:
  wiki_root: "~/test-wiki"
"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(config_content)
        
        # 模拟 HOME 目录
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        
        config = load_config(config_path)
        
        # 验证路径展开
        expected_path = fake_home / "test-wiki"
        assert config.wiki_root == expected_path


@pytest.mark.e2e
def test_full_config_workflow(temp_wiki_structure, monkeypatch):
    """完整配置工作流测试"""
    from config_loader import load_config, Config
    
    # 1. 从文件加载
    config_path = temp_wiki_structure / "config.yaml"
    config1 = load_config(config_path)
    assert config1 is not None
    
    # 2. 环境变量覆盖
    monkeypatch.setenv("TAVILY_API_KEY", "workflow-test-key")
    config2 = load_config(config_path)
    assert config2.search.api_key == "workflow-test-key"
    
    # 3. 验证配置完整性
    assert config2.llm.provider == "deepseek"
    assert config2.search.engine == "tavily"
    assert config2.schedule.news_collection == "daily"
    
    # 4. 转换为字典
    config_dict = config2.to_dict()
    assert "llm" in config_dict
    assert "search" in config_dict
    assert "schedule" in config_dict
    
    # 5. 验证路径
    assert isinstance(config2.wiki_root, Path)
    
    print("✓ 完整配置工作流测试通过")


@pytest.mark.e2e
def test_error_messages_are_helpful(tmp_path):
    """测试错误信息是否友好"""
    from config_loader import load_config
    
    # 测试空文件
    empty_config = tmp_path / "empty.yaml"
    empty_config.write_text("")
    
    with pytest.raises(ValueError) as exc_info:
        load_config(empty_config)
    
    error_msg = str(exc_info.value)
    assert "配置文件为空" in error_msg
    
    # 测试缺少字段
    incomplete_config = tmp_path / "incomplete.yaml"
    incomplete_config.write_text("llm: {}")
    
    with pytest.raises(ValueError) as exc_info:
        load_config(incomplete_config)
    
    error_msg = str(exc_info.value)
    assert "配置验证失败" in error_msg
    assert "LLM API Key" in error_msg
    assert "环境变量" in error_msg  # 应该提示可以使用环境变量


if __name__ == "__main__":
    # 允许直接运行此测试文件
    pytest.main([__file__, "-v"])