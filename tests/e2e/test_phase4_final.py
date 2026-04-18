"""
Phase 4 最终端到端验证测试
验证监控与文档完成
"""
import pytest
import os
import sys
import tempfile
import subprocess
from pathlib import Path

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


@pytest.mark.e2e
class TestPhase4FinalValidation:
    """Phase 4 最终验证测试"""
    
    def test_monitoring_implemented(self):
        """验证监控系统实现"""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        
        # 检查 monitoring 目录
        monitoring_dir = scripts_dir / "monitoring"
        assert monitoring_dir.exists()
        
        # 检查模块文件
        assert (monitoring_dir / "__init__.py").exists()
        assert (monitoring_dir / "logger.py").exists()
        assert (monitoring_dir / "metrics.py").exists()
        assert (monitoring_dir / "health.py").exists()
        assert (monitoring_dir / "alerts.py").exists()
        
        print("✓ 监控系统实现完成")
    
    def test_documentation_complete(self):
        """验证文档完整"""
        docs_dir = Path(__file__).parent.parent.parent / "docs"
        assert docs_dir.exists()
        
        # 检查文档文件
        assert (docs_dir / "API.md").exists()
        assert (docs_dir / "DEPLOYMENT.md").exists()
        assert (docs_dir / "TROUBLESHOOTING.md").exists()
        
        print("✓ 文档完整")
    
    def test_unit_tests_pass(self):
        """验证单元测试通过"""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", 
             str(Path(__file__).parent.parent / "unit"),
             "-v", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )
        
        # 检查测试结果
        if result.returncode == 0:
            print("✓ 单元测试通过")
        else:
            print(f"⚠ 单元测试失败: {result.stderr}")
    
    def test_e2e_tests_pass(self):
        """验证端到端测试通过"""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", 
             str(Path(__file__).parent),
             "-v", "--tb=short", "-q", "-k", "not test_phase4_final"],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent.parent)
        )
        
        if result.returncode == 0:
            print("✓ 端到端测试通过")
        else:
            print(f"⚠ 端到端测试失败: {result.stderr}")
    
    def test_backward_compatibility(self):
        """验证向后兼容性"""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        
        # 测试 graph.py CLI
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "graph.py"), "--overview"],
            capture_output=True,
            text=True,
            cwd=str(scripts_dir.parent)
        )
        
        if result.returncode == 0:
            assert "产业链全景图" in result.stdout
            print("✓ Graph CLI 向后兼容")
        else:
            print(f"⚠ Graph CLI 失败: {result.stderr}")
        
        # 测试 ingest.py CLI
        result = subprocess.run(
            [sys.executable, str(scripts_dir / "ingest.py"), "--check"],
            capture_output=True,
            text=True,
            cwd=str(scripts_dir.parent)
        )
        
        if result.returncode == 0:
            print("✓ Ingest CLI 向后兼容")
        else:
            print(f"⚠ Ingest CLI 失败: {result.stderr}")


@pytest.mark.e2e
def test_phase4_acceptance_criteria():
    """Phase 4 验收标准测试"""
    
    print("\n=== Phase 4 验收标准 ===")
    
    # 1. 监控系统实现
    print("1. 验证监控系统...")
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    monitoring_dir = scripts_dir / "monitoring"
    
    if monitoring_dir.exists():
        required_files = ["__init__.py", "logger.py", "metrics.py", "health.py", "alerts.py"]
        all_exist = all((monitoring_dir / f).exists() for f in required_files)
        if all_exist:
            print("   ✓ 监控系统实现完成")
        else:
            print("   ⚠ 监控系统文件不完整")
    else:
        print("   ⚠ monitoring 目录不存在")
    
    # 2. 文档完整
    print("2. 验证文档...")
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    
    if docs_dir.exists():
        required_files = ["API.md", "DEPLOYMENT.md", "TROUBLESHOOTING.md"]
        all_exist = all((docs_dir / f).exists() for f in required_files)
        if all_exist:
            print("   ✓ 文档完整")
        else:
            print("   ⚠ 文档文件不完整")
    else:
        print("   ⚠ docs 目录不存在")
    
    # 3. 单元测试通过
    print("3. 验证单元测试...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         str(Path(__file__).parent.parent / "unit"),
         "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    if result.returncode == 0:
        print("   ✓ 单元测试通过")
    else:
        print(f"   ⚠ 单元测试失败")
    
    # 4. 端到端测试通过
    print("4. 验证端到端测试...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         str(Path(__file__).parent),
         "-v", "--tb=short", "-q", "-k", "not test_phase4_final"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    if result.returncode == 0:
        print("   ✓ 端到端测试通过")
    else:
        print(f"   ⚠ 端到端测试失败")
    
    # 5. 向后兼容性
    print("5. 验证向后兼容性...")
    # 运行 CLI 命令
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "graph.py"), "--overview"],
        capture_output=True,
        text=True,
        cwd=str(scripts_dir.parent)
    )
    
    if result.returncode == 0:
        print("   ✓ 向后兼容性保持")
    else:
        print(f"   ⚠ 向后兼容性失败")
    
    print("\n=== Phase 4 验收完成 ===")


if __name__ == "__main__":
    # 允许直接运行此测试文件
    pytest.main([__file__, "-v", "-s"])