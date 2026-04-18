"""
告警机制
发送告警通知
"""
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警"""
    id: str
    level: AlertLevel
    title: str
    message: str
    source: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "details": self.details,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
        }
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def resolve(self) -> None:
        """解决告警"""
        self.resolved = True
        self.resolved_at = datetime.now().isoformat()


class AlertManager:
    """告警管理器"""
    
    def __init__(self, alerts_file: Optional[Path] = None):
        """
        初始化告警管理器
        
        Args:
            alerts_file: 告警文件路径
        """
        self.alerts_file = alerts_file
        self._alerts: Dict[str, Alert] = {}
        self._handlers: List[Callable[[Alert], None]] = []
        self._rules: List[Callable[[Dict[str, Any]], Optional[Alert]]] = []
    
    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        添加告警处理器
        
        Args:
            handler: 处理器函数
        """
        self._handlers.append(handler)
    
    def add_rule(self, rule: Callable[[Dict[str, Any]], Optional[Alert]]) -> None:
        """
        添加告警规则
        
        Args:
            rule: 规则函数
        """
        self._rules.append(rule)
    
    def trigger_alert(self, alert: Alert) -> None:
        """
        触发告警
        
        Args:
            alert: 告警对象
        """
        self._alerts[alert.id] = alert
        
        # 通知处理器
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器失败: {e}")
        
        logger.info(f"告警触发: {alert.level.value} - {alert.title}")
    
    def create_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        source: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """
        创建告警
        
        Args:
            level: 告警级别
            title: 标题
            message: 消息
            source: 来源
            details: 详情
            
        Returns:
            告警对象
        """
        alert_id = f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        alert = Alert(
            id=alert_id,
            level=level,
            title=title,
            message=message,
            source=source,
            details=details or {},
        )
        
        self.trigger_alert(alert)
        return alert
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        解决告警
        
        Args:
            alert_id: 告警 ID
            
        Returns:
            True 如果成功解决
        """
        if alert_id not in self._alerts:
            return False
        
        alert = self._alerts[alert_id]
        alert.resolve()
        
        logger.info(f"告警已解决: {alert_id}")
        return True
    
    def check_rules(self, context: Dict[str, Any]) -> List[Alert]:
        """
        检查告警规则
        
        Args:
            context: 上下文信息
            
        Returns:
            触发的告警列表
        """
        alerts = []
        
        for rule in self._rules:
            try:
                alert = rule(context)
                if alert:
                    self.trigger_alert(alert)
                    alerts.append(alert)
            except Exception as e:
                logger.error(f"告警规则检查失败: {e}")
        
        return alerts
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """
        获取告警
        
        Args:
            alert_id: 告警 ID
            
        Returns:
            告警对象
        """
        return self._alerts.get(alert_id)
    
    def get_all_alerts(self) -> List[Alert]:
        """获取所有告警"""
        return list(self._alerts.values())
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [a for a in self._alerts.values() if not a.resolved]
    
    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """
        根据级别获取告警
        
        Args:
            level: 告警级别
            
        Returns:
            告警列表
        """
        return [a for a in self._alerts.values() if a.level == level]
    
    def get_alerts_by_source(self, source: str) -> List[Alert]:
        """
        根据来源获取告警
        
        Args:
            source: 来源
            
        Returns:
            告警列表
        """
        return [a for a in self._alerts.values() if a.source == source]
    
    def clear_resolved(self) -> int:
        """
        清除已解决的告警
        
        Returns:
            清除的告警数量
        """
        resolved_ids = [aid for aid, a in self._alerts.items() if a.resolved]
        
        for aid in resolved_ids:
            del self._alerts[aid]
        
        logger.info(f"清除 {len(resolved_ids)} 个已解决的告警")
        return len(resolved_ids)
    
    def save(self) -> None:
        """保存告警到文件"""
        if not self.alerts_file:
            return
        
        try:
            # 确保目录存在
            self.alerts_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(self.alerts_file, "w", encoding="utf-8") as f:
                json.dump(
                    [a.to_dict() for a in self._alerts.values()],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            
            logger.info(f"告警已保存到: {self.alerts_file}")
        
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
    
    def load(self) -> None:
        """从文件加载告警"""
        if not self.alerts_file or not self.alerts_file.exists():
            return
        
        try:
            with open(self.alerts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 恢复告警
            for alert_data in data:
                alert = Alert(
                    id=alert_data["id"],
                    level=AlertLevel(alert_data["level"]),
                    title=alert_data["title"],
                    message=alert_data["message"],
                    source=alert_data.get("source", ""),
                    details=alert_data.get("details", {}),
                    timestamp=alert_data.get("timestamp"),
                    resolved=alert_data.get("resolved", False),
                    resolved_at=alert_data.get("resolved_at"),
                )
                self._alerts[alert.id] = alert
            
            logger.info(f"告警已从 {self.alerts_file} 加载")
        
        except Exception as e:
            logger.error(f"加载告警失败: {e}")


# 预定义的告警处理器
def console_handler(alert: Alert) -> None:
    """控制台告警处理器"""
    level_colors = {
        AlertLevel.INFO: "\033[94m",  # 蓝色
        AlertLevel.WARNING: "\033[93m",  # 黄色
        AlertLevel.ERROR: "\033[91m",  # 红色
        AlertLevel.CRITICAL: "\033[95m",  # 紫色
    }
    reset_color = "\033[0m"
    
    color = level_colors.get(alert.level, "")
    print(f"{color}[{alert.level.value.upper()}] {alert.title}{reset_color}")
    print(f"  {alert.message}")
    if alert.details:
        print(f"  Details: {json.dumps(alert.details, ensure_ascii=False)}")


# 预定义的告警管理器
def get_alert_manager(alerts_file: Optional[Path] = None) -> AlertManager:
    """
    获取告警管理器
    
    Args:
        alerts_file: 告警文件路径
        
    Returns:
        告警管理器
    """
    manager = AlertManager(alerts_file)
    manager.add_handler(console_handler)
    return manager


# 默认告警管理器
default_alert_manager = get_alert_manager()