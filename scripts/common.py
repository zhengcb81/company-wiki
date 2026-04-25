#!/usr/bin/env python3
"""
common.py — 公共基础设施模块

提取所有脚本共享的代码，减少重复定义。

包含：
- 路径常量（WIKI_ROOT, SCRIPTS_DIR）
- 环境初始化（sys.path, dotenv, UTF-8 修复）
- 配置加载（load_yaml_config）
- 原子写入（atomic_write）
- 日志记录（log_action）

用法：
    from common import WIKI_ROOT, get_llm_client_safe, atomic_write
"""

import os
import sys
from pathlib import Path
from typing import Optional

# ── 路径常量 ──────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

# 确保 scripts/ 在 Python 路径中
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# ── 环境初始化 ──────────────────────────────
# Windows 控制台 UTF-8 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

# 加载 .env
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# ── 配置路径 ──────────────────────────────
CONFIG_PATH = WIKI_ROOT / "config.yaml"
LOG_PATH = WIKI_ROOT / "log.md"
COMPANIES_YAML = WIKI_ROOT / "companies.yaml"
GRAPH_YAML = WIKI_ROOT / "graph.yaml"


# ── 公共函数 ──────────────────────────────
def load_yaml_config(path: Optional[Path] = None) -> dict:
    """加载 YAML 配置文件"""
    import yaml

    path = path or CONFIG_PATH
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """原子写入文件：写临时文件然后 rename，防止崩溃导致数据丢失"""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(content, encoding=encoding)
        os.replace(str(tmp_path), str(path))
    except Exception:
        # 回退到直接写入
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        path.write_text(content, encoding=encoding)


def log_action(action: str, message: str) -> None:
    """追加操作日志到 log.md"""
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{now}] {action} | {message}\n"
    if LOG_PATH.exists():
        content = LOG_PATH.read_text(encoding="utf-8")
    else:
        content = "# 知识库操作日志\n"
    content += entry
    LOG_PATH.write_text(content, encoding="utf-8")


def get_llm_client_safe():
    """安全获取 LLM 客户端（处理 API key 缺失）"""
    try:
        from llm_client import get_llm_client

        client = get_llm_client()
        if not client.available:
            print("[WARN] LLM API key not configured")
        return client
    except Exception as e:
        print(f"[WARN] Failed to initialize LLM client: {e}")
        return None


def setup_paths() -> tuple[Path, Path]:
    """返回 (SCRIPTS_DIR, WIKI_ROOT)，用于向后兼容"""
    return SCRIPTS_DIR, WIKI_ROOT


# ── 路径辅助函数（从 utils.py 合并）─────────────────
def get_company_dir(company_name: str) -> Path:
    """获取公司目录"""
    return WIKI_ROOT / "companies" / company_name


def get_raw_dir(company_name: str) -> Path:
    """获取公司 raw 目录"""
    return get_company_dir(company_name) / "raw"


def get_wiki_dir(company_name: str) -> Path:
    """获取公司 wiki 目录"""
    return get_company_dir(company_name) / "wiki"


def safe_read_file(file_path: Path, encoding: str = "utf-8") -> Optional[str]:
    """安全读取文件，失败返回 None"""
    try:
        return file_path.read_text(encoding=encoding)
    except Exception:
        return None


def safe_write_file(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """安全写入文件，返回是否成功"""
    try:
        file_path.write_text(content, encoding=encoding)
        return True
    except Exception:
        return False
