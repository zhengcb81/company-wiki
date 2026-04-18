"""
异步处理工具测试
验证异步执行器和处理器
"""
import pytest
import asyncio
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from async_utils import AsyncExecutor, TaskResult, AsyncFileScanner, AsyncProcessor


class TestAsyncExecutor:
    """测试异步执行器"""
    
    @pytest.mark.asyncio
    async def test_run_tasks(self):
        """测试运行任务"""
        executor = AsyncExecutor(max_workers=2, max_concurrent=2)
        
        def task_1():
            time.sleep(0.1)
            return "result_1"
        
        def task_2():
            time.sleep(0.1)
            return "result_2"
        
        def task_3():
            time.sleep(0.1)
            return "result_3"
        
        tasks = [task_1, task_2, task_3]
        task_ids = ["task_1", "task_2", "task_3"]
        
        results = await executor.run_tasks(tasks, task_ids)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].result == "result_1"
        assert results[1].result == "result_2"
        assert results[2].result == "result_3"
        
        executor.shutdown()
    
    @pytest.mark.asyncio
    async def test_run_tasks_with_error(self):
        """测试运行任务（有错误）"""
        executor = AsyncExecutor(max_workers=2, max_concurrent=2)
        
        def task_success():
            return "success"
        
        def task_error():
            raise ValueError("Task failed")
        
        tasks = [task_success, task_error]
        task_ids = ["success", "error"]
        
        results = await executor.run_tasks(tasks, task_ids)
        
        assert len(results) == 2
        assert results[0].success
        assert not results[1].success
        assert results[1].error == "Task failed"
        
        executor.shutdown()
    
    @pytest.mark.asyncio
    async def test_cancel(self):
        """测试取消任务"""
        executor = AsyncExecutor(max_workers=2, max_concurrent=2)
        
        def slow_task():
            time.sleep(1)
            return "done"
        
        tasks = [slow_task] * 5
        task_ids = [f"task_{i}" for i in range(5)]
        
        # 启动任务
        task = asyncio.create_task(executor.run_tasks(tasks, task_ids))
        
        # 等待一小段时间后取消
        await asyncio.sleep(0.1)
        executor.cancel()
        
        # 等待任务完成
        results = await task
        
        # 应该有一些任务被取消
        cancelled = [r for r in results if r.status == "cancelled"]
        assert len(cancelled) > 0
        
        executor.shutdown()
    
    @pytest.mark.asyncio
    async def test_progress_callback(self):
        """测试进度回调"""
        executor = AsyncExecutor(max_workers=2, max_concurrent=2)
        
        def task():
            time.sleep(0.1)
            return "done"
        
        tasks = [task] * 5
        task_ids = [f"task_{i}" for i in range(5)]
        
        progress = []
        
        def callback(completed, total):
            progress.append((completed, total))
        
        results = await executor.run_tasks(tasks, task_ids, progress_callback=callback)
        
        assert len(results) == 5
        assert len(progress) == 5
        assert progress[-1] == (5, 5)
        
        executor.shutdown()
    
    def test_get_stats(self):
        """测试获取统计信息"""
        executor = AsyncExecutor()
        
        # 手动添加一些结果
        executor._results = {
            "task_1": TaskResult("task_1", "completed", result="result_1", duration=1.0),
            "task_2": TaskResult("task_2", "completed", result="result_2", duration=2.0),
            "task_3": TaskResult("task_3", "failed", error="error"),
        }
        
        stats = executor.get_stats()
        
        assert stats["total"] == 3
        assert stats["completed"] == 2
        assert stats["failed"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["total_duration"] == 3.0
        assert stats["average_duration"] == 1.5
        
        executor.shutdown()


class TestTaskResult:
    """测试任务结果"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = TaskResult(
            task_id="test_task",
            status="completed",
            result="test_result",
            start_time=100.0,
            end_time=101.5,
        )
        
        data = result.to_dict()
        
        assert data["task_id"] == "test_task"
        assert data["status"] == "completed"
        assert data["result"] == "test_result"
        assert data["duration"] == 1.5
    
    def test_success(self):
        """测试成功属性"""
        result = TaskResult("task_1", "completed")
        assert result.success
        
        result = TaskResult("task_2", "failed")
        assert not result.success
        
        result = TaskResult("task_3", "cancelled")
        assert not result.success


@pytest.mark.asyncio
async def test_async_executor_concurrent():
    """测试并发执行"""
    executor = AsyncExecutor(max_workers=2, max_concurrent=2)
    
    execution_order = []
    
    def task_1():
        execution_order.append("task_1_start")
        time.sleep(0.2)
        execution_order.append("task_1_end")
        return "result_1"
    
    def task_2():
        execution_order.append("task_2_start")
        time.sleep(0.2)
        execution_order.append("task_2_end")
        return "result_2"
    
    def task_3():
        execution_order.append("task_3_start")
        time.sleep(0.2)
        execution_order.append("task_3_end")
        return "result_3"
    
    tasks = [task_1, task_2, task_3]
    task_ids = ["task_1", "task_2", "task_3"]
    
    start_time = time.time()
    results = await executor.run_tasks(tasks, task_ids)
    duration = time.time() - start_time
    
    # 验证结果
    assert len(results) == 3
    assert all(r.success for r in results)
    
    # 验证并发执行（应该比顺序执行快）
    # 顺序执行需要 0.6 秒，并发执行应该在 0.4 秒左右
    assert duration < 0.5
    
    # 验证执行顺序（应该有重叠）
    # task_1_start, task_2_start 应该在 task_1_end 之前
    task_1_start_idx = execution_order.index("task_1_start")
    task_2_start_idx = execution_order.index("task_2_start")
    task_1_end_idx = execution_order.index("task_1_end")
    
    assert task_1_start_idx < task_1_end_idx
    assert task_2_start_idx < task_1_end_idx
    
    executor.shutdown()


@pytest.mark.unit
def test_async_utils_module_import():
    """测试异步工具模块导入"""
    from async_utils import AsyncExecutor, TaskResult, AsyncFileScanner, AsyncProcessor
    
    assert AsyncExecutor is not None
    assert TaskResult is not None
    assert AsyncFileScanner is not None
    assert AsyncProcessor is not None
    
    print("✓ 异步工具模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])