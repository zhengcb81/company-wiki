"""
重试策略
支持指数退避和错误分类
"""
import asyncio
import logging
import time
import random
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """可重试的错误（临时性错误）"""
    pass


class PermanentError(Exception):
    """永久性错误（不应该重试）"""
    pass


class RetryStrategy(str, Enum):
    """重试策略"""
    FIXED = "fixed"  # 固定间隔
    EXPONENTIAL = "exponential"  # 指数退避
    RANDOM = "random"  # 随机间隔


class RetryPolicy:
    """重试策略"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (RetryableError, Exception),
        permanent_exceptions: Tuple[Type[Exception], ...] = (PermanentError,),
    ):
        """
        初始化重试策略
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            strategy: 重试策略
            jitter: 是否添加随机抖动
            retryable_exceptions: 可重试的异常类型
            permanent_exceptions: 永久性异常类型
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.permanent_exceptions = permanent_exceptions
    
    def get_delay(self, attempt: int) -> float:
        """
        获取延迟时间
        
        Args:
            attempt: 当前尝试次数（从 0 开始）
            
        Returns:
            延迟时间（秒）
        """
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (2 ** attempt)
        elif self.strategy == RetryStrategy.RANDOM:
            delay = self.base_delay * random.uniform(0.5, 1.5)
        else:
            delay = self.base_delay
        
        # 限制最大延迟
        delay = min(delay, self.max_delay)
        
        # 添加随机抖动
        if self.jitter:
            delay = delay * random.uniform(0.8, 1.2)
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        判断是否应该重试
        
        Args:
            exception: 异常
            attempt: 当前尝试次数
            
        Returns:
            True 如果应该重试
        """
        # 检查是否超过最大重试次数
        if attempt >= self.max_retries:
            return False
        
        # 检查是否是永久性异常
        if isinstance(exception, self.permanent_exceptions):
            return False
        
        # 检查是否是可重试异常
        if isinstance(exception, self.retryable_exceptions):
            return True
        
        # 默认不重试
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
            Exception: 最后一次异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    logger.error(f"函数 {func.__name__} 失败，不重试: {e}")
                    raise
                
                delay = self.get_delay(attempt)
                logger.warning(f"函数 {func.__name__} 失败，{delay:.2f}秒后重试 (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                time.sleep(delay)
        
        # 所有重试都失败
        logger.error(f"函数 {func.__name__} 在 {self.max_retries + 1} 次尝试后仍然失败")
        raise last_exception
    
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
            Exception: 最后一次异常
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    logger.error(f"函数 {func.__name__} 失败，不重试: {e}")
                    raise
                
                delay = self.get_delay(attempt)
                logger.warning(f"函数 {func.__name__} 失败，{delay:.2f}秒后重试 (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                await asyncio.sleep(delay)
        
        # 所有重试都失败
        logger.error(f"函数 {func.__name__} 在 {self.max_retries + 1} 次尝试后仍然失败")
        raise last_exception
    
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


# 预定义的重试策略
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    strategy=RetryStrategy.EXPONENTIAL,
    jitter=True,
)

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_retries=5,
    base_delay=0.5,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL,
    jitter=True,
)

CONSERVATIVE_RETRY_POLICY = RetryPolicy(
    max_retries=2,
    base_delay=2.0,
    max_delay=120.0,
    strategy=RetryStrategy.FIXED,
    jitter=False,
)