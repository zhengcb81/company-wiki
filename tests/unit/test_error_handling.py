"""
错误处理模块测试
验证重试策略、熔断器、死信队列
"""
import pytest
import asyncio
import tempfile
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from error_handling import RetryPolicy, RetryableError, PermanentError, CircuitBreaker, DeadLetterQueue


class TestRetryPolicy:
    """测试重试策略"""
    
    def test_execute_success(self):
        """测试成功执行"""
        policy = RetryPolicy(max_retries=3)
        
        def success_func():
            return "success"
        
        result = policy.execute(success_func)
        assert result == "success"
    
    def test_execute_with_retry(self):
        """测试重试"""
        policy = RetryPolicy(max_retries=3, base_delay=0.1)
        
        call_count = 0
        
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Temporary failure")
            return "success"
        
        result = policy.execute(flaky_func)
        assert result == "success"
        assert call_count == 3
    
    def test_execute_permanent_error(self):
        """测试永久性错误"""
        policy = RetryPolicy(max_retries=3)
        
        call_count = 0
        
        def permanent_fail():
            nonlocal call_count
            call_count += 1
            raise PermanentError("Permanent failure")
        
        with pytest.raises(PermanentError):
            policy.execute(permanent_fail)
        
        assert call_count == 1  # 不应该重试
    
    def test_execute_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        policy = RetryPolicy(max_retries=2, base_delay=0.1)
        
        call_count = 0
        
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise RetryableError("Always fails")
        
        with pytest.raises(RetryableError):
            policy.execute(always_fail)
        
        assert call_count == 3  # 初始调用 + 2 次重试
    
    def test_get_delay_fixed(self):
        """测试固定延迟"""
        from error_handling.retry import RetryStrategy
        
        policy = RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            strategy=RetryStrategy.FIXED,
            jitter=False,
        )
        
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 1.0
    
    def test_get_delay_exponential(self):
        """测试指数退避"""
        from error_handling.retry import RetryStrategy
        
        policy = RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False,
        )
        
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
    
    def test_should_retry(self):
        """测试是否应该重试"""
        policy = RetryPolicy(max_retries=3)
        
        # 可重试异常
        assert policy.should_retry(RetryableError("test"), 0)
        assert policy.should_retry(RetryableError("test"), 2)
        assert not policy.should_retry(RetryableError("test"), 3)  # 超过最大次数
        
        # 永久性异常
        assert not policy.should_retry(PermanentError("test"), 0)
    
    @pytest.mark.asyncio
    async def test_execute_async(self):
        """测试异步执行"""
        policy = RetryPolicy(max_retries=3, base_delay=0.1)
        
        call_count = 0
        
        async def async_flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Temporary failure")
            return "success"
        
        result = await policy.execute_async(async_flaky_func)
        assert result == "success"
        assert call_count == 3


class TestCircuitBreaker:
    """测试熔断器"""
    
    def test_initial_state(self):
        """测试初始状态"""
        breaker = CircuitBreaker(name="test")
        assert breaker.state.value == "closed"
    
    def test_record_success(self):
        """测试记录成功"""
        breaker = CircuitBreaker(name="test")
        
        def success_func():
            return "success"
        
        result = breaker.execute(success_func)
        assert result == "success"
        assert breaker.state.value == "closed"
    
    def test_record_failure(self):
        """测试记录失败"""
        breaker = CircuitBreaker(failure_threshold=3, name="test")
        
        def fail_func():
            raise Exception("Failure")
        
        def success_func():
            return "success"
        
        # 失败 3 次
        for _ in range(3):
            with pytest.raises(Exception):
                breaker.execute(fail_func)
        
        # 应该打开熔断器
        assert breaker.state.value == "open"
        
        # 应该拒绝调用
        with pytest.raises(Exception) as exc_info:
            breaker.execute(success_func)
        
        assert "已打开" in str(exc_info.value)
    
    def test_half_open_state(self):
        """测试半开状态"""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=2,
            name="test",
        )
        
        def fail_func():
            raise Exception("Failure")
        
        # 失败 2 次，打开熔断器
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.execute(fail_func)
        
        assert breaker.state.value == "open"
        
        # 等待恢复超时
        time.sleep(0.2)
        
        # 应该转换到半开状态
        assert breaker.state.value == "half_open"
        
        # 在半开状态成功调用 2 次
        def success_func():
            return "success"
        
        breaker.execute(success_func)
        breaker.execute(success_func)
        
        # 应该转换到关闭状态
        assert breaker.state.value == "closed"
    
    def test_reset(self):
        """测试重置"""
        breaker = CircuitBreaker(failure_threshold=2, name="test")
        
        def fail_func():
            raise Exception("Failure")
        
        # 失败 2 次
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.execute(fail_func)
        
        assert breaker.state.value == "open"
        
        # 重置
        breaker.reset()
        assert breaker.state.value == "closed"
    
    def test_get_stats(self):
        """测试获取统计信息"""
        breaker = CircuitBreaker(name="test")
        
        def success_func():
            return "success"
        
        def fail_func():
            raise Exception("Failure")
        
        # 成功 3 次
        for _ in range(3):
            breaker.execute(success_func)
        
        # 失败 2 次
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.execute(fail_func)
        
        stats = breaker.get_stats()
        assert stats.total_calls == 5
        assert stats.successful_calls == 3
        assert stats.failed_calls == 2
        assert stats.success_rate == 0.6


class TestDeadLetterQueue:
    """测试死信队列"""
    
    def test_add_and_get(self, tmp_path):
        """测试添加和获取"""
        queue_path = tmp_path / "dead_letter.json"
        queue = DeadLetterQueue(queue_path)
        
        # 添加消息
        msg = queue.add(
            task_type="test",
            task_data={"key": "value"},
            error="Test error",
        )
        
        assert msg.id is not None
        assert msg.task_type == "test"
        assert msg.error == "Test error"
        
        # 获取消息
        messages = queue.get_all()
        assert len(messages) == 1
        assert messages[0].id == msg.id
    
    def test_get_by_type(self, tmp_path):
        """测试根据类型获取"""
        queue_path = tmp_path / "dead_letter.json"
        queue = DeadLetterQueue(queue_path)
        
        # 添加不同类型的消息
        queue.add("type1", {"key": "value1"}, "Error 1")
        queue.add("type2", {"key": "value2"}, "Error 2")
        queue.add("type1", {"key": "value3"}, "Error 3")
        
        # 获取 type1
        messages = queue.get_by_type("type1")
        assert len(messages) == 2
    
    def test_remove(self, tmp_path):
        """测试移除"""
        queue_path = tmp_path / "dead_letter.json"
        queue = DeadLetterQueue(queue_path)
        
        # 添加消息
        msg = queue.add("test", {"key": "value"}, "Error")
        
        # 移除
        assert queue.remove(msg.id)
        assert queue.count() == 0
    
    def test_retry(self, tmp_path):
        """测试重试"""
        queue_path = tmp_path / "dead_letter.json"
        queue = DeadLetterQueue(queue_path)
        
        # 添加消息
        msg = queue.add("test", {"key": "value"}, "Error")
        
        # 标记重试
        updated = queue.retry(msg.id)
        assert updated.retry_count == 1
        assert updated.last_retry_at is not None
    
    def test_clear(self, tmp_path):
        """测试清空"""
        queue_path = tmp_path / "dead_letter.json"
        queue = DeadLetterQueue(queue_path)
        
        # 添加消息
        queue.add("test1", {"key": "value1"}, "Error 1")
        queue.add("test2", {"key": "value2"}, "Error 2")
        
        # 清空
        count = queue.clear()
        assert count == 2
        assert queue.count() == 0
    
    def test_get_stats(self, tmp_path):
        """测试获取统计信息"""
        queue_path = tmp_path / "dead_letter.json"
        queue = DeadLetterQueue(queue_path)
        
        # 添加消息
        queue.add("type1", {"key": "value1"}, "Error 1")
        queue.add("type2", {"key": "value2"}, "Error 2")
        queue.add("type1", {"key": "value3"}, "Error 3")
        
        stats = queue.get_stats()
        assert stats["total"] == 3
        assert stats["by_type"]["type1"] == 2
        assert stats["by_type"]["type2"] == 1


@pytest.mark.unit
def test_error_handling_module_import():
    """测试错误处理模块导入"""
    from error_handling import RetryPolicy, RetryableError, PermanentError, CircuitBreaker, DeadLetterQueue
    
    assert RetryPolicy is not None
    assert RetryableError is not None
    assert PermanentError is not None
    assert CircuitBreaker is not None
    assert DeadLetterQueue is not None
    
    print("✓ 错误处理模块导入成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])