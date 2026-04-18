"""
结构化日志
支持 JSON 格式输出
"""
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: str
    level: str
    message: str
    logger_name: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class StructuredLogger:
    """结构化日志"""
    
    def __init__(
        self,
        name: str,
        log_file: Optional[Path] = None,
        log_level: LogLevel = LogLevel.INFO,
        json_format: bool = True,
    ):
        """
        初始化结构化日志
        
        Args:
            name: 日志器名称
            log_file: 日志文件路径
            log_level: 日志级别
            json_format: 是否使用 JSON 格式
        """
        self.name = name
        self.log_file = log_file
        self.log_level = log_level
        self.json_format = json_format
        
        # 创建日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.value))
        
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 添加控制台处理器
        self._add_console_handler()
        
        # 添加文件处理器
        if log_file:
            self._add_file_handler(log_file)
    
    def _add_console_handler(self) -> None:
        """添加控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        
        if self.json_format:
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        self.logger.addHandler(handler)
    
    def _add_file_handler(self, log_file: Path) -> None:
        """添加文件处理器"""
        # 确保目录存在
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(str(log_file), encoding="utf-8")
        
        if self.json_format:
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
        
        self.logger.addHandler(handler)
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> None:
        """
        记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外信息
            exc_info: 是否包含异常信息
        """
        # 获取调用信息
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller = frame.f_back.f_back
            module = caller.f_globals.get('__name__', '')
            function = caller.f_code.co_name
            line_number = caller.f_lineno
        else:
            module = None
            function = None
            line_number = None
        
        # 创建日志条目
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level.value,
            message=message,
            logger_name=self.name,
            module=module,
            function=function,
            line_number=line_number,
            extra=extra or {},
        )
        
        # 记录日志
        log_level = getattr(logging, level.value)
        self.logger.log(log_level, entry.to_json(), exc_info=exc_info)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录 DEBUG 日志"""
        self._log(LogLevel.DEBUG, message, extra)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录 INFO 日志"""
        self._log(LogLevel.INFO, message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录 WARNING 日志"""
        self._log(LogLevel.WARNING, message, extra)
    
    def error(
        self,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> None:
        """记录 ERROR 日志"""
        self._log(LogLevel.ERROR, message, extra, exc_info)
    
    def critical(
        self,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ) -> None:
        """记录 CRITICAL 日志"""
        self._log(LogLevel.CRITICAL, message, extra, exc_info)
    
    def set_level(self, level: LogLevel) -> None:
        """设置日志级别"""
        self.log_level = level
        self.logger.setLevel(getattr(logging, level.value))
    
    def add_context(self, **kwargs: Any) -> 'StructuredLogger':
        """
        添加上下文信息
        
        Args:
            **kwargs: 上下文信息
            
        Returns:
            新的日志器实例
        """
        # 创建新的日志器，带有上下文
        new_logger = StructuredLogger(
            name=self.name,
            log_file=self.log_file,
            log_level=self.log_level,
            json_format=self.json_format,
        )
        
        # 添加上下文到额外信息
        original_log = new_logger._log
        
        def log_with_context(
            level: LogLevel,
            message: str,
            extra: Optional[Dict[str, Any]] = None,
            exc_info: bool = False,
        ) -> None:
            merged_extra = {**kwargs, **(extra or {})}
            original_log(level, message, merged_extra, exc_info)
        
        new_logger._log = log_with_context
        
        return new_logger


class JsonFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            格式化后的字符串
        """
        try:
            # 尝试解析为 JSON
            return record.getMessage()
        except (json.JSONDecodeError, TypeError):
            # 如果不是 JSON，创建新的日志条目
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created).isoformat(),
                level=record.levelname,
                message=record.getMessage(),
                logger_name=record.name,
                module=record.module,
                function=record.funcName,
                line_number=record.lineno,
            )
            return entry.to_json()


# 预定义的日志器
def get_logger(
    name: str,
    log_file: Optional[Path] = None,
    log_level: LogLevel = LogLevel.INFO,
) -> StructuredLogger:
    """
    获取日志器
    
    Args:
        name: 日志器名称
        log_file: 日志文件路径
        log_level: 日志级别
        
    Returns:
        结构化日志器
    """
    return StructuredLogger(name, log_file, log_level)


# 默认日志器
default_logger = get_logger("company-wiki")