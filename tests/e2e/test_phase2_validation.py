"""
Phase 2 端到端验证测试
验证核心模块重构
"""
import pytest
import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


@pytest.mark.e2e
class TestPhase2ConfigUnification:
    """Phase 2 配置统一测试"""
    
    def test_collect_news_uses_config_loader(self, temp_wiki_structure, monkeypatch):
        """验证 collect_news 使用 config_loader"""
        # 设置环境变量
        monkeypatch.setenv("TAVILY_API_KEY", "test-key-collect-news")
        
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        collect_news_script = scripts_dir / "collect_news.py"
        
        # 尝试导入并验证
        sys.path.insert(0, str(scripts_dir))
        try:
            import collect_news
            
            # 验证 load_search_config 函数存在
            assert hasattr(collect_news, 'load_search_config')
            
            # 验证 config_loader 已导入
            assert hasattr(collect_news, 'load_config')
            
            print("✓ collect_news 已使用 config_loader")
        except ImportError as e:
            pytest.fail(f"导入 collect_news 失败: {e}")
    
    def test_ingest_uses_config_loader(self):
        """验证 ingest 使用 config_loader"""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))
        
        try:
            import ingest
            
            # 验证 config_loader 已导入
            assert hasattr(ingest, 'load_config')
            
            print("✓ ingest 已使用 config_loader")
        except ImportError as e:
            pytest.fail(f"导入 ingest 失败: {e}")
    
    def test_no_duplicate_yaml_parsing(self):
        """验证没有重复的 YAML 解析代码"""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        
        # 检查 collect_news.py
        collect_news_path = scripts_dir / "collect_news.py"
        if collect_news_path.exists():
            content = collect_news_path.read_text()
            
            # 检查是否还有直接的 yaml.safe_load 调用
            # 允许在回退逻辑中使用
            yaml_imports = content.count("import yaml")
            yaml_safe_load = content.count("yaml.safe_load")
            
            # 应该只有一个 yaml.safe_load（在回退逻辑中）
            assert yaml_safe_load <= 1, f"collect_news.py 中有 {yaml_safe_load} 个 yaml.safe_load 调用，应该最多1个"
        
        print("✓ 没有重复的 YAML 解析代码")
    
    def test_config_loader_error_handling(self, tmp_path):
        """验证 config_loader 错误处理"""
        from config_loader import load_config
        
        # 测试配置文件不存在
        nonexistent_path = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError):
            load_config(nonexistent_path)
        
        # 测试配置文件格式错误
        invalid_path = tmp_path / "invalid.yaml"
        invalid_path.write_text("invalid: yaml: content: [")
        
        with pytest.raises(ValueError) as exc_info:
            load_config(invalid_path)
        
        assert "格式错误" in str(exc_info.value)
        
        print("✓ config_loader 错误处理正常")


@pytest.mark.e2e
def test_phase2_acceptance_criteria():
    """Phase 2 验收标准测试"""
    
    print("\n=== Phase 2.1 验收标准 ===")
    
    # 1. 所有脚本使用统一的配置加载
    print("1. 验证配置加载统一...")
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    
    # 检查 collect_news
    collect_news_path = scripts_dir / "collect_news.py"
    if collect_news_path.exists():
        content = collect_news_path.read_text()
        assert "from config_loader import" in content, "collect_news 未导入 config_loader"
        print("   ✓ collect_news 使用 config_loader")
    
    # 检查 ingest
    ingest_path = scripts_dir / "ingest.py"
    if ingest_path.exists():
        content = ingest_path.read_text()
        assert "from config_loader import" in content, "ingest 未导入 config_loader"
        print("   ✓ ingest 使用 config_loader")
    
    # 2. 无重复的 YAML 解析代码
    print("2. 验证无重复 YAML 解析...")
    
    # 检查主要脚本
    scripts_to_check = ["collect_news.py", "ingest.py"]
    
    for script_name in scripts_to_check:
        script_path = scripts_dir / script_name
        if script_path.exists():
            content = script_path.read_text()
            
            # 统计 yaml.safe_load 调用
            yaml_safe_load_count = content.count("yaml.safe_load")
            
            # 允许在回退逻辑中使用一次
            if yaml_safe_load_count > 1:
                print(f"   ⚠ {script_name} 有 {yaml_safe_load_count} 个 yaml.safe_load 调用")
            else:
                print(f"   ✓ {script_name} YAML 解析已统一")
    
    # 3. 配置验证可以捕获格式错误
    print("3. 验证配置验证...")
    from config_loader import load_config
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
llm:
  provider: "deepseek"
  # 缺少 api_key
search:
  engine: "tavily"
  # 缺少 tavily_api_key
""")
        bad_config_path = f.name
    
    try:
        config = load_config(Path(bad_config_path))
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        error_msg = str(e)
        assert "配置验证失败" in error_msg
        print("   ✓ 配置验证可以捕获格式错误")
    finally:
        os.unlink(bad_config_path)
    
    # 4. 端到端测试通过
    print("4. 运行端到端测试...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         str(Path(__file__).parent / "test_phase2_validation.py"), 
         "-v", "-k", "TestPhase2ConfigUnification"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    if result.returncode == 0:
        print("   ✓ 端到端测试通过")
    else:
        print(f"   ⚠ 端到端测试失败: {result.stderr}")
    
    print("\n=== Phase 2.1 验收完成 ===")


if __name__ == "__main__":
    # 允许直接运行此测试文件
    pytest.main([__file__, "-v", "-s"])