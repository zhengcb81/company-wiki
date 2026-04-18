"""
异步执行器
支持并发任务执行和进度跟踪
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import List, Callable, Any, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: str  # TaskStatus 的值
    result: Any = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果提供了 start_time 和 end_time，计算 duration
        if self.start_time and self.end_time and self.duration is None:
            self.duration = self.end_time - self.start_time
    
    @property
    def success(self) -> bool:
        """是否成功"""
        return self.status == TaskStatus.COMPLETED.value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "duration": self.duration,
        }


class AsyncExecutor:
    """异步执行器"""
    
    def __init__(self, max_workers: int = 10, max_concurrent: int = 5):
        """
        初始化执行器
        
        Args:
            max_workers: 最大线程数
            max_concurrent: 最大并发数
        """
        self.max_workers = max_workers
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._results: Dict[str, TaskResult] = {}
        self._cancelled = False
    
    async def run_tasks(
        self,
        tasks: List[Callable[..., Any]],
        task_ids: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[TaskResult]:
        """
        并发运行任务
        
        Args:
            tasks: 任务列表
            task_ids: 任务 ID 列表（可选）
            progress_callback: 进度回调函数
            
        Returns:
            任务结果列表
        """
        if task_ids is None:
            task_ids = [f"task_{i}" for i in range(len(tasks))]
        
        if len(tasks) != len(task_ids):
            raise ValueError("tasks 和 task_ids 长度必须相同")
        
        self._results = {}
        self._cancelled = False
        
        # 创建异步任务
        async_tasks = []
        for task, task_id in zip(tasks, task_ids):
            async_task = asyncio.create_task(
                self._run_single_task(task, task_id)
            )
            async_tasks.append(async_task)
        
        # 等待所有任务完成
        completed = 0
        total = len(async_tasks)
        
        for coro in asyncio.as_completed(async_tasks):
            if self._cancelled:
                break
            
            try:
                result = await coro
                self._results[result.task_id] = result
            except Exception as e:
                logger.error(f"任务执行异常: {e}")
            
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
        
        # 返回结果（按原始顺序）
        return [self._results.get(task_id, TaskResult(task_id, TaskStatus.CANCELLED.value)) 
                for task_id in task_ids]
    
    async def _run_single_task(self, task: Callable[..., Any], task_id: str) -> TaskResult:
        """
        运行单个任务
        
        Args:
            task: 任务函数
            task_id: 任务 ID
            
        Returns:
            任务结果
        """
        async with self._semaphore:
            if self._cancelled:
                return TaskResult(task_id, TaskStatus.CANCELLED.value)
            
            start_time = time.time()
            result = TaskResult(task_id, TaskStatus.RUNNING.value, start_time=start_time)
            
            try:
                # 在线程池中运行任务
                loop = asyncio.get_event_loop()
                task_result = await loop.run_in_executor(self._executor, task)
                
                result.status = TaskStatus.COMPLETED.value
                result.result = task_result
                result.end_time = time.time()
                
            except Exception as e:
                result.status = TaskStatus.FAILED.value
                result.error = str(e)
                result.end_time = time.time()
                logger.error(f"任务 {task_id} 失败: {e}")
            
            return result
    
    def cancel(self) -> None:
        """取消所有任务"""
        self._cancelled = True
        logger.info("取消所有任务")
    
    def get_results(self) -> Dict[str, TaskResult]:
        """获取所有结果"""
        return self._results.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        results = list(self._results.values())
        
        completed = [r for r in results if r.status == TaskStatus.COMPLETED.value]
        failed = [r for r in results if r.status == TaskStatus.FAILED.value]
        cancelled = [r for r in results if r.status == TaskStatus.CANCELLED.value]
        
        total_duration = sum(r.duration for r in completed if r.duration)
        
        return {
            "total": len(results),
            "completed": len(completed),
            "failed": len(failed),
            "cancelled": len(cancelled),
            "success_rate": len(completed) / len(results) if results else 0,
            "total_duration": total_duration,
            "average_duration": total_duration / len(completed) if completed else 0,
        }
    
    def shutdown(self) -> None:
        """关闭执行器"""
        self._executor.shutdown(wait=True)