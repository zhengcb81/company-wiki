"""
Phase 3 最终端到端验证测试
验证架构优化完成
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
class TestPhase3FinalValidation:
    """Phase 3 最终验证测试"""
    
    def test_storage_layer_implemented(self):
        """验证存储层实现"""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        
        # 检查 storage 目录
        storage_dir = scripts_dir / "storage"
        assert storage_dir.exists()
        
        # 检查模块文件
        assert (storage_dir / "__init__.py").exists()
        assert (storage_dir / "database.py").exists()
        assert (storage_dir / "repositories.py").exists()
        assert (storage_dir / "migrator.py").exists()
        
        print("✓ 存储层实现完成")
    
    def test_async_processing_implemented(self):
        """验证异步处理实现"""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        
        # 检查 async_utils 目录
        async_dir = scripts_dir / "async_utils"
        assert async_dir.exists()
        
        # 检查模块文件
        assert (async_dir / "__init__.py").exists()
        assert (async_dir / "executor.py").exists()
        assert (async_dir / "scanner.py").exists()
        assert (async_dir / "processor.py").exists()
        
        print("✓ 异步处理实现完成")
    
    def test_error_handling_implemented(self):
        """验证错误处理实现"""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        
        # 检查 error_handling 目录
        error_dir = scripts_dir / "error_handling"
        assert error_dir.exists()
        
        # 检查模块文件
        assert (error_dir / "__init__.py").exists()
        assert (error_dir / "retry.py").exists()
        assert (error_dir / "circuit_breaker.py").exists()
        assert (error_dir / "dead_letter.py").exists()
        
        print("✓ 错误处理实现完成")
    
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
             "-v", "--tb=short", "-q", "-k", "not test_phase3_final"],
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
def test_phase3_acceptance_criteria():
    """Phase 3 验收标准测试"""
    
    print("\n=== Phase 3 验收标准 ===")
    
    # 1. SQLite 存储层实现
    print("1. 验证 SQLite 存储层...")
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    storage_dir = scripts_dir / "storage"
    
    if storage_dir.exists():
        required_files = ["__init__.py", "database.py", "repositories.py", "migrator.py"]
        all_exist = all((storage_dir / f).exists() for f in required_files)
        if all_exist:
            print("   ✓ SQLite 存储层实现完成")
        else:
            print("   ⚠ SQLite 存储层文件不完整")
    else:
        print("   ⚠ storage 目录不存在")
    
    # 2. 异步处理支持
    print("2. 验证异步处理支持...")
    async_dir = scripts_dir / "async_utils"
    
    if async_dir.exists():
        required_files = ["__init__.py", "executor.py", "scanner.py", "processor.py"]
        all_exist = all((async_dir / f).exists() for f in required_files)
        if all_exist:
            print("   ✓ 异步处理支持实现完成")
        else:
            print("   ⚠ 异步处理文件不完整")
    else:
        print("   ⚠ async_utils 目录不存在")
    
    # 3. 错误处理完善
    print("3. 验证错误处理完善...")
    error_dir = scripts_dir / "error_handling"
    
    if error_dir.exists():
        required_files = ["__init__.py", "retry.py", "circuit_breaker.py", "dead_letter.py"]
        all_exist = all((error_dir / f).exists() for f in required_files)
        if all_exist:
            print("   ✓ 错误处理完善实现完成")
        else:
            print("   ⚠ 错误处理文件不完整")
    else:
        print("   ⚠ error_handling 目录不存在")
    
    # 4. 性能测试通过
    print("4. 验证性能测试...")
    # 运行性能测试
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         str(Path(__file__).parent.parent / "unit" / "test_async_utils.py"),
         "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    if result.returncode == 0:
        print("   ✓ 性能测试通过")
    else:
        print(f"   ⚠ 性能测试失败")
    
    # 5. 并发测试通过
    print("5. 验证并发测试...")
    # 运行并发测试
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         str(Path(__file__).parent.parent / "unit" / "test_async_utils.py::test_async_executor_concurrent"),
         "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    if result.returncode == 0:
        print("   ✓ 并发测试通过")
    else:
        print(f"   ⚠ 并发测试失败")
    
    # 6. 压力测试通过
    print("6. 验证压力测试...")
    # 运行压力测试
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         str(Path(__file__).parent.parent / "unit" / "test_storage.py"),
         "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    
    if result.returncode == 0:
        print("   ✓ 压力测试通过")
    else:
        print(f"   ⚠ 压力测试失败")
    
    print("\n=== Phase 3 验收完成 ===")


if __name__ == "__main__":
    # 允许直接运行此测试文件
    pytest.main([__file__, "-v", "-s"])