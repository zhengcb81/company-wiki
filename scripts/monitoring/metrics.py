"""
指标收集
收集和报告系统指标
"""
import time
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """指标类型"""
    COUNTER = "counter"  # 计数器（只增不减）
    GAUGE = "gauge"  # 仪表盘（可增可减）
    HISTOGRAM = "histogram"  # 直方图（分布）
    SUMMARY = "summary"  # 摘要（分位数）


@dataclass
class Metric:
    """指标"""
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: Optional[str] = None
    help: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp,
            "help": self.help,
        }
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, metrics_file: Optional[Path] = None):
        """
        初始化指标收集器
        
        Args:
            metrics_file: 指标文件路径
        """
        self.metrics_file = metrics_file
        self._metrics: Dict[str, Metric] = {}
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._callbacks: List[Callable[[Metric], None]] = []
    
    def counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
        help: str = "",
    ) -> None:
        """
        增加计数器
        
        Args:
            name: 指标名称
            value: 增加的值
            labels: 标签
            help: 帮助信息
        """
        key = self._make_key(name, labels)
        self._counters[key] += value
        
        metric = Metric(
            name=name,
            type=MetricType.COUNTER,
            value=self._counters[key],
            labels=labels or {},
            help=help,
        )
        
        self._metrics[key] = metric
        self._notify(metric)
    
    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help: str = "",
    ) -> None:
        """
        设置仪表盘值
        
        Args:
            name: 指标名称
            value: 值
            labels: 标签
            help: 帮助信息
        """
        key = self._make_key(name, labels)
        self._gauges[key] = value
        
        metric = Metric(
            name=name,
            type=MetricType.GAUGE,
            value=value,
            labels=labels or {},
            help=help,
        )
        
        self._metrics[key] = metric
        self._notify(metric)
    
    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        help: str = "",
    ) -> None:
        """
        记录直方图值
        
        Args:
            name: 指标名称
            value: 值
            labels: 标签
            help: 帮助信息
        """
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        
        metric = Metric(
            name=name,
            type=MetricType.HISTOGRAM,
            value=value,
            labels=labels or {},
            help=help,
        )
        
        self._metrics[key] = metric
        self._notify(metric)
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """生成指标键"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _notify(self, metric: Metric) -> None:
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"指标回调失败: {e}")
    
    def register_callback(self, callback: Callable[[Metric], None]) -> None:
        """
        注册回调函数
        
        Args:
            callback: 回调函数
        """
        self._callbacks.append(callback)
    
    def get_metric(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[Metric]:
        """
        获取指标
        
        Args:
            name: 指标名称
            labels: 标签
            
        Returns:
            指标对象
        """
        key = self._make_key(name, labels)
        return self._metrics.get(key)
    
    def get_all_metrics(self) -> List[Metric]:
        """获取所有指标"""
        return list(self._metrics.values())
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """
        获取计数器值
        
        Args:
            name: 指标名称
            labels: 标签
            
        Returns:
            计数器值
        """
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """
        获取仪表盘值
        
        Args:
            name: 指标名称
            labels: 标签
            
        Returns:
            仪表盘值
        """
        key = self._make_key(name, labels)
        return self._gauges.get(key)
    
    def get_histogram(self, name: str, labels: Optional[Dict[str, str]] = None) -> List[float]:
        """
        获取直方图值
        
        Args:
            name: 指标名称
            labels: 标签
            
        Returns:
            直方图值列表
        """
        key = self._make_key(name, labels)
        return self._histograms.get(key, [])
    
    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """
        获取直方图统计信息
        
        Args:
            name: 指标名称
            labels: 标签
            
        Returns:
            统计信息字典
        """
        values = self.get_histogram(name, labels)
        
        if not values:
            return {
                "count": 0,
                "sum": 0.0,
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
            }
        
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
        }
    
    def reset(self) -> None:
        """重置所有指标"""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
    
    def save(self) -> None:
        """保存指标到文件"""
        if not self.metrics_file:
            return
        
        try:
            # 确保目录存在
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备数据
            data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": [m.to_dict() for m in self._metrics.values()],
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: list(v) for k, v in self._histograms.items()},
            }
            
            # 写入文件
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"指标已保存到: {self.metrics_file}")
        
        except Exception as e:
            logger.error(f"保存指标失败: {e}")
    
    def load(self) -> None:
        """从文件加载指标"""
        if not self.metrics_file or not self.metrics_file.exists():
            return
        
        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 恢复计数器
            for key, value in data.get("counters", {}).items():
                self._counters[key] = value
            
            # 恢复仪表盘
            for key, value in data.get("gauges", {}).items():
                self._gauges[key] = value
            
            # 恢复直方图
            for key, values in data.get("histograms", {}).items():
                self._histograms[key] = list(values)
            
            # 恢复指标
            for metric_data in data.get("metrics", []):
                metric = Metric(
                    name=metric_data["name"],
                    type=MetricType(metric_data["type"]),
                    value=metric_data["value"],
                    labels=metric_data.get("labels", {}),
                    timestamp=metric_data.get("timestamp"),
                    help=metric_data.get("help", ""),
                )
                key = self._make_key(metric.name, metric.labels)
                self._metrics[key] = metric
            
            logger.info(f"指标已从 {self.metrics_file} 加载")
        
        except Exception as e:
            logger.error(f"加载指标失败: {e}")
    
    def export_prometheus(self) -> str:
        """
        导出为 Prometheus 格式
        
        Returns:
            Prometheus 格式的指标字符串
        """
        lines = []
        
        for metric in self._metrics.values():
            # 添加 HELP
            if metric.help:
                lines.append(f"# HELP {metric.name} {metric.help}")
            
            # 添加 TYPE
            lines.append(f"# TYPE {metric.name} {metric.type.value}")
            
            # 添加指标
            if metric.labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(metric.labels.items()))
                lines.append(f"{metric.name}{{{label_str}}} {metric.value}")
            else:
                lines.append(f"{metric.name} {metric.value}")
        
        return "\n".join(lines)


# 预定义的指标收集器
def get_metrics_collector(metrics_file: Optional[Path] = None) -> MetricsCollector:
    """
    获取指标收集器
    
    Args:
        metrics_file: 指标文件路径
        
    Returns:
        指标收集器
    """
    return MetricsCollector(metrics_file)


# 默认指标收集器
default_metrics = get_metrics_collector()