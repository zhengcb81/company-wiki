#!/usr/bin/env python3
"""
config_rules_loader.py — 统一规则配置加载器
从 config_rules.yaml 读取所有过滤、分类、质量评分规则，
供 ingest.py、extract.py、collect_news.py 等模块使用。

用法：
    from config_rules_loader import RulesConfig
    rules = RulesConfig()
    rules.get_url_blacklist()      # -> ["quote.eastmoney.com", ...]
    rules.get_title_blacklist()    # -> ["行情走势", ...]
    rules.get_noise_patterns()     # -> [regex patterns, ...]
"""

import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent
CONFIG_RULES_PATH = WIKI_ROOT / "config_rules.yaml"

# 缓存：避免重复加载
_cache = None


def _load_yaml():
    """加载 config_rules.yaml，带缓存"""
    global _cache
    if _cache is not None:
        return _cache

    import yaml
    with open(CONFIG_RULES_PATH, "r", encoding="utf-8") as f:
        _cache = yaml.safe_load(f)
    return _cache


class RulesConfig:
    """规则配置访问器 — 所有规则从 config_rules.yaml 读取，无硬编码"""

    def __init__(self, config_path=None):
        self._path = Path(config_path) if config_path else CONFIG_RULES_PATH
        import yaml
        with open(self._path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f)

    # ── 低质量来源过滤 ────────────────────────

    def get_url_blacklist(self):
        """URL 黑名单模式列表"""
        return self._data.get("low_quality_sources", {}).get("url_patterns", [])

    def get_title_blacklist(self):
        """标题黑名单模式列表"""
        return self._data.get("low_quality_sources", {}).get("title_patterns", [])

    def get_filename_blacklist(self):
        """文件名黑名单模式列表"""
        return self._data.get("low_quality_sources", {}).get("filename_patterns", [])

    # ── 噪声模式 ──────────────────────────────

    def get_noise_patterns(self):
        """噪声过滤正则模式列表"""
        return self._data.get("noise_patterns", [])

    # ── 采集质量控制 ──────────────────────────

    def get_collection_quality(self):
        """采集时质量控制参数"""
        return self._data.get("collection_quality", {
            "min_content_length": 100,
            "min_title_length": 10,
            "skip_if_title_equals_company": True,
        })

    # ── 文档分类 ──────────────────────────────

    def get_document_classification(self):
        """文档分类规则"""
        return self._data.get("document_classification", {})

    # ── 关键词映射 ────────────────────────────

    def get_question_keywords(self):
        """问题关键词映射"""
        return self._data.get("question_keywords", {})

    def get_topic_keywords(self):
        """主题发现关键词映射"""
        return self._data.get("topic_keywords", {})

    # ── 质量评分 ──────────────────────────────

    def get_quality_grading(self):
        """质量评分配置"""
        return self._data.get("quality_grading", {
            "weights": {
                "has_specific_numbers": 0.25,
                "has_action_verbs": 0.20,
                "has_entity_names": 0.15,
                "content_length": 0.15,
                "sentence_diversity": 0.10,
                "no_noise_ratio": 0.15,
            },
            "thresholds": {
                "accept": 0.5,
                "review": 0.2,
                "reject": 0.0,
            },
        })

    # ── 辅助方法 ──────────────────────────────

    def is_url_blacklisted(self, url):
        """检查 URL 是否命中黑名单"""
        url_lower = url.lower()
        for pattern in self.get_url_blacklist():
            if pattern.lower() in url_lower:
                return True
        return False

    def is_title_blacklisted(self, title):
        """检查标题是否命中黑名单"""
        title_lower = title.lower()
        for pattern in self.get_title_blacklist():
            if pattern.lower() in title_lower:
                return True
        return False

    def is_filename_blacklisted(self, filename):
        """检查文件名是否命中黑名单"""
        for pattern in self.get_filename_blacklist():
            if pattern in filename:
                return True
        return False

    def is_noise_line(self, line):
        """检查一行文本是否匹配噪声模式"""
        for pattern in self.get_noise_patterns():
            try:
                if re.search(pattern, line, re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False
