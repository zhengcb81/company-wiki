"""
监控模块
性能监控、错误监控、业务指标

用法：
    from monitor import Monitor, Metric, track_performance
"""

import time
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from functools import wraps
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """指标"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ErrorRecord:
    """错误记录"""
    error_type: str
    message: str
    module: str
    function: str
    timestamp: str = ""
    traceback: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Monitor:
    """监控器"""
    
    def __init__(self, metrics_file: Optional[Path] = None):
        """
        初始化监控器
        
        Args:
            metrics_file: 指标文件路径
        """
        self.metrics_file = metrics_file or Path.home() / "company-wiki" / "metrics.json"
        self.metrics: List[Metric] = []
        self.errors: List[ErrorRecord] = []
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # 加载历史数据
        self._load()
    
    def _load(self):
        """加载历史数据"""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, "r") as f:
                    data = json.load(f)
                    self.counters = data.get("counters", {})
                    self.gauges = data.get("gauges", {})
            except Exception as e:
                logger.warning(f"加载监控数据失败: {e}")
    
    def _save(self):
        """保存数据"""
        try:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "counters": dict(self.counters),
                "gauges": self.gauges,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.metrics_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"保存监控数据失败: {e}")
    
    def counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """
        计数器指标
        
        Args:
            name: 指标名称
            value: 增加的值
            labels: 标签
        """
        key = self._make_key(name, labels)
        self.counters[key] += value
        self.metrics.append(Metric(name, self.counters[key], labels or {}))
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        仪表盘指标
        
        Args:
            name: 指标名称
            value: 值
            labels: 标签
        """
        key = self._make_key(name, labels)
        self.gauges[key] = value
        self.metrics.append(Metric(name, value, labels or {}))
    
    def timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """
        计时器指标
        
        Args:
            name: 指标名称
            duration: 持续时间（秒）
            labels: 标签
        """
        key = self._make_key(name, labels)
        self.timers[key].append(duration)
        self.metrics.append(Metric(name, duration, labels or {}))
    
    def record_error(self, error: Exception, module: str = "", function: str = ""):
        """
        记录错误
        
        Args:
            error: 异常对象
            module: 模块名
            function: 函数名
        """
        import traceback
        
        error_record = ErrorRecord(
            error_type=type(error).__name__,
            message=str(error),
            module=module,
            function=function,
            traceback=traceback.format_exc(),
        )
        self.errors.append(error_record)
        
        # 更新错误计数
        self.counter("errors_total", labels={"type": type(error).__name__})
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """获取计数器值"""
        key = self._make_key(name, labels)
        return self.counters.get(key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """获取仪表盘值"""
        key = self._make_key(name, labels)
        return self.gauges.get(key)
    
    def get_timer_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """获取计时器统计"""
        key = self._make_key(name, labels)
        values = self.timers.get(key, [])
        
        if not values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0}
        
        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "total": sum(values),
        }
    
    def get_error_count(self, error_type: Optional[str] = None) -> int:
        """获取错误数量"""
        if error_type:
            return sum(1 for e in self.errors if e.error_type == error_type)
        return len(self.errors)
    
    def get_recent_errors(self, limit: int = 10) -> List[ErrorRecord]:
        """获取最近的错误"""
        return self.errors[-limit:]
    
    def get_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        return {
            "counters": dict(self.counters),
            "gauges": self.gauges,
            "timers": {k: self.get_timer_stats(k.split("{")[0]) for k in self.timers},
            "errors": {
                "total": len(self.errors),
                "by_type": self._count_errors_by_type(),
            },
            "metrics_count": len(self.metrics),
        }
    
    def _count_errors_by_type(self) -> Dict[str, int]:
        """按类型统计错误"""
        counts = defaultdict(int)
        for error in self.errors:
            counts[error.error_type] += 1
        return dict(counts)
    
    def save(self):
        """保存监控数据"""
        self._save()
        
        # 保存错误日志
        if self.errors:
            error_log_path = self.metrics_file.parent / "errors.json"
            try:
                with open(error_log_path, "w") as f:
                    json.dump([e.to_dict() for e in self.errors], f, indent=2)
            except Exception as e:
                logger.warning(f"保存错误日志失败: {e}")
    
    def reset(self):
        """重置监控数据"""
        self.metrics.clear()
        self.errors.clear()
        self.counters.clear()
        self.gauges.clear()
        self.timers.clear()


# 全局监控器实例
_default_monitor = None


def get_monitor() -> Monitor:
    """获取全局监控器"""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = Monitor()
    return _default_monitor


def track_performance(name: str = None):
    """
    性能追踪装饰器
    
    用法:
        @track_performance("my_function")
        def my_function():
            pass
    """
    def decorator(func):
        func_name = name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.timer(f"{func_name}_duration", duration)
                monitor.counter(f"{func_name}_calls")
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor.timer(f"{func_name}_duration", duration)
                monitor.counter(f"{func_name}_errors")
                monitor.record_error(e, module=func.__module__, function=func_name)
                raise
        
        return wrapper
    return decorator


def track_errors(func):
    """
    错误追踪装饰器
    
    用法:
        @track_errors
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        monitor = get_monitor()
        try:
            return func(*args, **kwargs)
        except Exception as e:
            monitor.record_error(e, module=func.__module__, function=func.__name__)
            raise
    return wrapper


class Timer:
    """上下文管理器计时器"""
    
    def __init__(self, name: str, monitor: Optional[Monitor] = None):
        self.name = name
        self.monitor = monitor or get_monitor()
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.monitor.timer(self.name, duration)
        
        if exc_type is not None:
            self.monitor.counter(f"{self.name}_errors")
            self.monitor.record_error(exc_val)
        
        return False


# 便捷函数
def counter(name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
    """增加计数器"""
    get_monitor().counter(name, value, labels)


def gauge(name: str, value: float, labels: Optional[Dict[str, str]] = None):
    """设置仪表盘值"""
    get_monitor().gauge(name, value, labels)


def timer(name: str, duration: float, labels: Optional[Dict[str, str]] = None):
    """记录计时"""
    get_monitor().timer(name, duration, labels)


def record_error(error: Exception, module: str = "", function: str = ""):
    """记录错误"""
    get_monitor().record_error(error, module, function)


if __name__ == "__main__":
    # 测试监控模块
    print("测试监控模块...")
    
    monitor = Monitor()
    
    # 测试计数器
    monitor.counter("test_counter", 1.0)
    monitor.counter("test_counter", 2.0)
    assert monitor.get_counter("test_counter") == 3.0
    
    # 测试仪表盘
    monitor.gauge("test_gauge", 100.0)
    assert monitor.get_gauge("test_gauge") == 100.0
    
    # 测试计时器
    monitor.timer("test_timer", 1.5)
    stats = monitor.get_timer_stats("test_timer")
    assert stats["count"] == 1
    assert stats["avg"] == 1.5
    
    # 测试错误记录
    try:
        raise ValueError("测试错误")
    except Exception as e:
        monitor.record_error(e)
    
    assert monitor.get_error_count() == 1
    
    # 测试装饰器
    @track_performance("decorated_function")
    def test_function():
        time.sleep(0.01)
        return "ok"
    
    result = test_function()
    assert result == "ok"
    
    # 测试上下文管理器
    with Timer("context_timer"):
        time.sleep(0.01)
    
    # 打印摘要
    summary = monitor.get_summary()
    print(f"\n监控摘要:")
    print(f"  计数器: {len(summary['counters'])}")
    print(f"  仪表盘: {len(summary['gauges'])}")
    print(f"  计时器: {len(summary['timers'])}")
    print(f"  错误: {summary['errors']['total']}")
    
    print("\n✅ 监控模块测试通过")