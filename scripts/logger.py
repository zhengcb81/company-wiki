"""
统一日志模块
所有脚本使用此模块进行日志记录

用法：
    from logger import get_logger
    logger = get_logger(__name__)
    logger.info("处理完成")
    logger.error("发生错误", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = True,
) -> None:
    """
    设置全局日志配置
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径
        console: 是否输出到控制台
    """
    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 创建格式器
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器
    
    Args:
        name: 日志器名称，通常使用 __name__
        
    Returns:
        日志器对象
    """
    return logging.getLogger(name)


class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, logger: logging.Logger, message: str):
        self.logger = logger
        self.message = message
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"开始: {self.message}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        if exc_type is None:
            self.logger.info(f"完成: {self.message} ({duration:.2f}s)")
        else:
            self.logger.error(f"失败: {self.message} ({duration:.2f}s): {exc_val}")
        return False


def log_function_call(logger: logging.Logger):
    """
    函数调用日志装饰器
    
    用法：
        @log_function_call(logger)
        def my_function():
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"调用: {func_name}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"完成: {func_name}")
                return result
            except Exception as e:
                logger.error(f"异常: {func_name}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


# 便捷函数
def log_info(message: str, logger_name: str = "app") -> None:
    """记录 INFO 日志"""
    logging.getLogger(logger_name).info(message)


def log_error(message: str, logger_name: str = "app", exc_info: bool = False) -> None:
    """记录 ERROR 日志"""
    logging.getLogger(logger_name).error(message, exc_info=exc_info)


def log_warning(message: str, logger_name: str = "app") -> None:
    """记录 WARNING 日志"""
    logging.getLogger(logger_name).warning(message)


def log_debug(message: str, logger_name: str = "app") -> None:
    """记录 DEBUG 日志"""
    logging.getLogger(logger_name).debug(message)


# 初始化默认日志配置
def init_default_logging():
    """初始化默认日志配置"""
    log_dir = Path.home() / "company-wiki" / "logs"
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    setup_logging(level="INFO", log_file=log_file, console=True)


# 如果直接导入，自动初始化
if __name__ != "__main__":
    # 只设置基本的控制台日志
    if not logging.getLogger().handlers:
        setup_logging(level="INFO", console=True)


if __name__ == "__main__":
    # 测试日志模块
    setup_logging(level="DEBUG")
    logger = get_logger(__name__)
    
    logger.debug("这是 DEBUG 消息")
    logger.info("这是 INFO 消息")
    logger.warning("这是 WARNING 消息")
    logger.error("这是 ERROR 消息")
    
    # 测试上下文管理器
    with LogContext(logger, "测试操作"):
        import time
        time.sleep(0.1)
    
    print("\n✅ 日志模块测试通过")