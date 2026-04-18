"""
熔断器模式
防止级联故障
"""
import asyncio
import logging
import time
from typing import Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class CircuitBreakerStats:
    """熔断器统计"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls
    
    @property
    def failure_rate(self) -> float:
        """失败率"""
        return 1.0 - self.success_rate


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        name: str = "default",
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
            half_open_max_calls: 半开状态最大调用数
            name: 熔断器名称
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.name = name
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._last_failure_time = 0.0
        self._stats = CircuitBreakerStats()
    
    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        # 检查是否应该从 OPEN 转换到 HALF_OPEN
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(f"熔断器 {self.name} 从 OPEN 转换到 HALF_OPEN")
        
        return self._state
    
    def _record_success(self) -> None:
        """记录成功"""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._stats.last_success_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            
            # 如果在半开状态成功调用足够次数，转换到 CLOSED
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"熔断器 {self.name} 从 HALF_OPEN 转换到 CLOSED")
        
        elif self._state == CircuitState.CLOSED:
            # 重置失败计数
            self._failure_count = 0
    
    def _record_failure(self) -> None:
        """记录失败"""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._stats.last_failure_time = time.time()
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            # 半开状态失败，立即转换到 OPEN
            self._state = CircuitState.OPEN
            logger.warning(f"熔断器 {self.name} 从 HALF_OPEN 转换到 OPEN")
        
        elif self._state == CircuitState.CLOSED:
            self._failure_count += 1
            
            # 检查是否达到失败阈值
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"熔断器 {self.name} 从 CLOSED 转换到 OPEN")
    
    def _record_rejection(self) -> None:
        """记录拒绝"""
        self._stats.rejected_calls += 1
    
    def can_execute(self) -> bool:
        """检查是否可以执行"""
        state = self.state
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        elif state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        
        return False
    
    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        执行函数（同步版本）
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值
            
        Raises:
            Exception: 如果熔断器打开或函数执行失败
        """
        if not self.can_execute():
            self._record_rejection()
            raise Exception(f"熔断器 {self.name} 已打开，拒绝调用")
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        
        except Exception as e:
            self._record_failure()
            raise
    
    async def execute_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        执行函数（异步版本）
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值
            
        Raises:
            Exception: 如果熔断器打开或函数执行失败
        """
        if not self.can_execute():
            self._record_rejection()
            raise Exception(f"熔断器 {self.name} 已打开，拒绝调用")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._record_success()
            return result
        
        except Exception as e:
            self._record_failure()
            raise
    
    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        装饰器模式
        
        Args:
            func: 要装饰的函数
            
        Returns:
            装饰后的函数
        """
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self.execute(func, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await self.execute_async(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    def reset(self) -> None:
        """重置熔断器"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._stats = CircuitBreakerStats()
        logger.info(f"熔断器 {self.name} 已重置")
    
    def get_stats(self) -> CircuitBreakerStats:
        """获取统计信息"""
        return self._stats
    
    def __repr__(self) -> str:
        return f"CircuitBreaker(name={self.name}, state={self.state.value}, failures={self._failure_count})"