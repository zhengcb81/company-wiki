"""
死信队列
记录失败的任务
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class DeadLetterMessage:
    """死信消息"""
    id: str
    task_type: str
    task_data: Dict[str, Any]
    error: str
    created_at: str
    retry_count: int = 0
    last_retry_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeadLetterMessage':
        """从字典创建"""
        return cls(**data)


class DeadLetterQueue:
    """死信队列"""
    
    def __init__(self, queue_path: Optional[Path] = None):
        """
        初始化死信队列
        
        Args:
            queue_path: 队列文件路径
        """
        if queue_path is None:
            queue_path = Path.home() / "company-wiki" / "data" / "dead_letter.json"
        
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载现有消息
        self._messages: List[DeadLetterMessage] = self._load()
    
    def _load(self) -> List[DeadLetterMessage]:
        """加载消息"""
        if not self.queue_path.exists():
            return []
        
        try:
            with open(self.queue_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return [DeadLetterMessage.from_dict(msg) for msg in data]
        
        except Exception as e:
            logger.error(f"加载死信队列失败: {e}")
            return []
    
    def _save(self) -> None:
        """保存消息"""
        try:
            with open(self.queue_path, "w", encoding="utf-8") as f:
                json.dump(
                    [msg.to_dict() for msg in self._messages],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        
        except Exception as e:
            logger.error(f"保存死信队列失败: {e}")
    
    def add(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        error: str,
    ) -> DeadLetterMessage:
        """
        添加死信消息
        
        Args:
            task_type: 任务类型
            task_data: 任务数据
            error: 错误信息
            
        Returns:
            死信消息
        """
        message = DeadLetterMessage(
            id=f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            task_type=task_type,
            task_data=task_data,
            error=error,
            created_at=datetime.now().isoformat(),
        )
        
        self._messages.append(message)
        self._save()
        
        logger.info(f"添加死信消息: {message.id}")
        return message
    
    def get_all(self) -> List[DeadLetterMessage]:
        """获取所有消息"""
        return self._messages.copy()
    
    def get_by_type(self, task_type: str) -> List[DeadLetterMessage]:
        """根据类型获取消息"""
        return [msg for msg in self._messages if msg.task_type == task_type]
    
    def get_by_id(self, message_id: str) -> Optional[DeadLetterMessage]:
        """根据 ID 获取消息"""
        for msg in self._messages:
            if msg.id == message_id:
                return msg
        return None
    
    def remove(self, message_id: str) -> bool:
        """
        移除消息
        
        Args:
            message_id: 消息 ID
            
        Returns:
            True 如果成功移除
        """
        for i, msg in enumerate(self._messages):
            if msg.id == message_id:
                self._messages.pop(i)
                self._save()
                logger.info(f"移除死信消息: {message_id}")
                return True
        
        return False
    
    def retry(self, message_id: str) -> Optional[DeadLetterMessage]:
        """
        标记消息为重试
        
        Args:
            message_id: 消息 ID
            
        Returns:
            更新后的消息
        """
        message = self.get_by_id(message_id)
        if not message:
            return None
        
        message.retry_count += 1
        message.last_retry_at = datetime.now().isoformat()
        self._save()
        
        logger.info(f"标记死信消息为重试: {message_id} (retry_count={message.retry_count})")
        return message
    
    def clear(self) -> int:
        """
        清空队列
        
        Returns:
            清除的消息数量
        """
        count = len(self._messages)
        self._messages.clear()
        self._save()
        
        logger.info(f"清空死信队列: {count} 条消息")
        return count
    
    def count(self) -> int:
        """获取消息数量"""
        return len(self._messages)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._messages:
            return {
                "total": 0,
                "by_type": {},
                "oldest": None,
                "newest": None,
            }
        
        by_type = {}
        for msg in self._messages:
            by_type[msg.task_type] = by_type.get(msg.task_type, 0) + 1
        
        sorted_messages = sorted(self._messages, key=lambda m: m.created_at)
        
        return {
            "total": len(self._messages),
            "by_type": by_type,
            "oldest": sorted_messages[0].created_at,
            "newest": sorted_messages[-1].created_at,
        }