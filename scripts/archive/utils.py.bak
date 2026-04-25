"""
公共工具模块
提取重复代码，统一函数命名

用法：
    from utils import log_message, load_yaml, ensure_dir
"""

import os
import yaml
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


# ── 日志相关 ──────────────────────────────

def log_message(message: str, log_path: Optional[Path] = None) -> None:
    """
    记录日志消息到文件
    
    Args:
        message: 日志消息
        log_path: 日志文件路径，默认为 ~/company-wiki/log.md
    """
    if log_path is None:
        log_path = Path.home() / "company-wiki" / "log.md"
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] {message}\n"
    
    try:
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
        else:
            content = "# 知识库操作日志\n"
        
        content += entry
        log_path.write_text(content, encoding="utf-8")
    except Exception as e:
        logger.error(f"写入日志失败: {e}")


def append_log(message: str, operation: str = "operation") -> None:
    """
    追加日志（向后兼容）
    
    Args:
        message: 日志消息
        operation: 操作类型
    """
    log_message(f"{operation} | {message}")


# ── 文件操作 ──────────────────────────────

def ensure_dir(path: Path) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        目录路径
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_read_file(file_path: Path, encoding: str = "utf-8") -> Optional[str]:
    """
    安全读取文件
    
    Args:
        file_path: 文件路径
        encoding: 编码
        
    Returns:
        文件内容，失败返回 None
    """
    try:
        return file_path.read_text(encoding=encoding)
    except Exception as e:
        logger.error(f"读取文件失败 {file_path}: {e}")
        return None


def safe_write_file(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """
    安全写入文件
    
    Args:
        file_path: 文件路径
        content: 内容
        encoding: 编码
        
    Returns:
        是否成功
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=encoding)
        return True
    except Exception as e:
        logger.error(f"写入文件失败 {file_path}: {e}")
        return False


def get_file_hash(file_path: Path) -> str:
    """
    获取文件 MD5 哈希
    
    Args:
        file_path: 文件路径
        
    Returns:
        MD5 哈希值
    """
    import hashlib
    content = file_path.read_bytes()
    return hashlib.md5(content).hexdigest()


# ── 配置加载 ──────────────────────────────

def load_yaml(file_path: Path) -> Dict[str, Any]:
    """
    加载 YAML 文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        配置字典
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"加载 YAML 失败 {file_path}: {e}")
        return {}


def load_json(file_path: Path) -> Dict[str, Any]:
    """
    加载 JSON 文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        配置字典
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载 JSON 失败 {file_path}: {e}")
        return {}


def save_yaml(file_path: Path, data: Dict[str, Any]) -> bool:
    """
    保存 YAML 文件
    
    Args:
        file_path: 文件路径
        data: 数据
        
    Returns:
        是否成功
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        logger.error(f"保存 YAML 失败 {file_path}: {e}")
        return False


def save_json(file_path: Path, data: Dict[str, Any]) -> bool:
    """
    保存 JSON 文件
    
    Args:
        file_path: 文件路径
        data: 数据
        
    Returns:
        是否成功
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存 JSON 失败 {file_path}: {e}")
        return False


# ── 路径工具 ──────────────────────────────

def get_wiki_root() -> Path:
    """
    获取 Wiki 根目录
    
    Returns:
        Wiki 根目录路径
    """
    return Path(os.path.expanduser("~/company-wiki"))


def get_companies_dir() -> Path:
    """
    获取公司目录
    
    Returns:
        公司目录路径
    """
    return get_wiki_root() / "companies"


def get_company_dir(company_name: str) -> Path:
    """
    获取指定公司的目录
    
    Args:
        company_name: 公司名称
        
    Returns:
        公司目录路径
    """
    return get_companies_dir() / company_name


def get_raw_dir(company_name: str) -> Path:
    """
    获取公司的 raw 目录
    
    Args:
        company_name: 公司名称
        
    Returns:
        raw 目录路径
    """
    return get_company_dir(company_name) / "raw"


def get_wiki_dir(company_name: str) -> Path:
    """
    获取公司的 wiki 目录
    
    Args:
        company_name: 公司名称
        
    Returns:
        wiki 目录路径
    """
    return get_company_dir(company_name) / "wiki"


# ── 文本处理 ──────────────────────────────

def extract_frontmatter(content: str) -> Dict[str, str]:
    """
    提取 Markdown frontmatter
    
    Args:
        content: Markdown 内容
        
    Returns:
        frontmatter 字典
    """
    if not content.startswith("---"):
        return {}
    
    end = content.find("---", 3)
    if end < 0:
        return {}
    
    front = content[3:end]
    result = {}
    
    for line in front.strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip().strip('"').strip("'")
    
    return result


def clean_text(text: str) -> str:
    """
    清理文本
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    import re
    
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_keywords(text: str, min_length: int = 2, max_length: int = 10) -> List[str]:
    """
    提取关键词
    
    Args:
        text: 文本
        min_length: 最小长度
        max_length: 最大长度
        
    Returns:
        关键词列表
    """
    import re
    
    # 提取中文词汇（2-10个字符）
    pattern = r'[\u4e00-\u9fff]{2,10}'
    keywords = re.findall(pattern, text)
    
    # 过滤长度
    keywords = [k for k in keywords if min_length <= len(k) <= max_length]
    
    # 去重
    return list(set(keywords))


# ── 数据转换 ──────────────────────────────

def to_bool(value: Any) -> bool:
    """
    转换为布尔值
    
    Args:
        value: 任意值
        
    Returns:
        布尔值
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(value, (int, float)):
        return value != 0
    return False


def to_int(value: Any, default: int = 0) -> int:
    """
    转换为整数
    
    Args:
        value: 任意值
        default: 默认值
        
    Returns:
        整数
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    """
    转换为浮点数
    
    Args:
        value: 任意值
        default: 默认值
        
    Returns:
        浮点数
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# ── 验证工具 ──────────────────────────────

def is_valid_ticker(ticker: str) -> bool:
    """
    检查是否是有效的股票代码
    
    Args:
        ticker: 股票代码
        
    Returns:
        是否有效
    """
    if not ticker:
        return False
    
    # A股：6位数字
    if ticker.isdigit() and len(ticker) == 6:
        return True
    
    # 美股：1-5个字母
    if ticker.isalpha() and 1 <= len(ticker) <= 5:
        return True
    
    # 港股：数字.HK
    if "." in ticker and ticker.split(".")[0].isdigit():
        return True
    
    return False


def is_empty_dir(path: Path) -> bool:
    """
    检查目录是否为空
    
    Args:
        path: 目录路径
        
    Returns:
        是否为空
    """
    if not path.exists():
        return True
    if not path.is_dir():
        return False
    return not any(path.iterdir())


# ── 向后兼容 ──────────────────────────────

# 保持原有函数名的兼容性
def load_yaml_simple(path: Path) -> Dict[str, Any]:
    """向后兼容：加载 YAML"""
    return load_yaml(path)


if __name__ == "__main__":
    # 测试工具函数
    print("测试 utils 模块...")
    
    # 测试路径函数
    wiki_root = get_wiki_root()
    print(f"Wiki 根目录: {wiki_root}")
    
    # 测试文本处理
    text = "中微公司发布新一代刻蚀设备"
    keywords = extract_keywords(text)
    print(f"关键词: {keywords}")
    
    # 测试数据转换
    assert to_bool("true") == True
    assert to_bool("false") == False
    assert to_int("123") == 123
    assert to_float("3.14") == 3.14
    
    print("✅ utils 模块测试通过")