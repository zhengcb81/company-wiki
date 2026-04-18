"""
健康检查
检查系统健康状态
"""
import time
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """健康检查"""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None
    duration_ms: float = 0.0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, health_file: Optional[Path] = None):
        """
        初始化健康检查器
        
        Args:
            health_file: 健康状态文件路径
        """
        self.health_file = health_file
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._results: Dict[str, HealthCheck] = {}
    
    def register_check(
        self,
        name: str,
        check_func: Callable[[], HealthCheck],
    ) -> None:
        """
        注册健康检查
        
        Args:
            name: 检查名称
            check_func: 检查函数
        """
        self._checks[name] = check_func
    
    def run_check(self, name: str) -> Optional[HealthCheck]:
        """
        运行单个健康检查
        
        Args:
            name: 检查名称
            
        Returns:
            健康检查结果
        """
        if name not in self._checks:
            logger.warning(f"健康检查 {name} 未注册")
            return None
        
        check_func = self._checks[name]
        
        try:
            start_time = time.time()
            result = check_func()
            duration_ms = (time.time() - start_time) * 1000
            
            result.duration_ms = duration_ms
            self._results[name] = result
            
            logger.debug(f"健康检查 {name}: {result.status.value}")
            return result
        
        except Exception as e:
            logger.error(f"健康检查 {name} 失败: {e}")
            
            result = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )
            self._results[name] = result
            return result
    
    def run_all_checks(self) -> Dict[str, HealthCheck]:
        """
        运行所有健康检查
        
        Returns:
            健康检查结果字典
        """
        results = {}
        
        for name in self._checks:
            result = self.run_check(name)
            if result:
                results[name] = result
        
        self._results = results
        return results
    
    def get_overall_status(self) -> HealthStatus:
        """
        获取整体健康状态
        
        Returns:
            整体健康状态
        """
        if not self._results:
            return HealthStatus.UNKNOWN
        
        # 检查是否有不健康的
        for result in self._results.values():
            if result.status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY
        
        # 检查是否有降级的
        for result in self._results.values():
            if result.status == HealthStatus.DEGRADED:
                return HealthStatus.DEGRADED
        
        # 所有都健康
        return HealthStatus.HEALTHY
    
    def get_check(self, name: str) -> Optional[HealthCheck]:
        """
        获取健康检查结果
        
        Args:
            name: 检查名称
            
        Returns:
            健康检查结果
        """
        return self._results.get(name)
    
    def get_all_checks(self) -> Dict[str, HealthCheck]:
        """获取所有健康检查结果"""
        return self._results.copy()
    
    def get_status_dict(self) -> Dict[str, Any]:
        """
        获取状态字典
        
        Returns:
            状态字典
        """
        overall_status = self.get_overall_status()
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {
                name: check.to_dict()
                for name, check in self._results.items()
            },
        }
    
    def save(self) -> None:
        """保存健康状态到文件"""
        if not self.health_file:
            return
        
        try:
            # 确保目录存在
            self.health_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(self.health_file, "w", encoding="utf-8") as f:
                json.dump(self.get_status_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"健康状态已保存到: {self.health_file}")
        
        except Exception as e:
            logger.error(f"保存健康状态失败: {e}")
    
    def load(self) -> None:
        """从文件加载健康状态"""
        if not self.health_file or not self.health_file.exists():
            return
        
        try:
            with open(self.health_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 恢复检查结果
            for name, check_data in data.get("checks", {}).items():
                check = HealthCheck(
                    name=name,
                    status=HealthStatus(check_data["status"]),
                    message=check_data.get("message", ""),
                    details=check_data.get("details", {}),
                    timestamp=check_data.get("timestamp"),
                    duration_ms=check_data.get("duration_ms", 0.0),
                )
                self._results[name] = check
            
            logger.info(f"健康状态已从 {self.health_file} 加载")
        
        except Exception as e:
            logger.error(f"加载健康状态失败: {e}")


# 预定义的健康检查
def get_health_checker(health_file: Optional[Path] = None) -> HealthChecker:
    """
    获取健康检查器
    
    Args:
        health_file: 健康状态文件路径
        
    Returns:
        健康检查器
    """
    return HealthChecker(health_file)


# 默认健康检查器
default_health_checker = get_health_checker()