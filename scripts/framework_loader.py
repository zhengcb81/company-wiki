#!/usr/bin/env python3
"""
framework_loader.py — 分析框架加载器

动态从config/目录加载分析框架和Prompt模板。
支持：
- 默认框架加载
- 公司特定配置覆盖
- 框架继承（如半年报继承年报）
- 章节类型匹配
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional

# 配置目录路径
CONFIG_DIR = Path(__file__).parent.parent / "config"


class FrameworkLoader:
    """分析框架加载器"""

    def __init__(self, config_dir: Path = CONFIG_DIR):
        self.config_dir = config_dir
        self._cache = {}  # 缓存已加载的配置

    def load_framework(self, doc_type: str, company: str = None) -> Dict:
        """
        加载指定文档类型的分析框架。

        Args:
            doc_type: 文档类型（prospectus/annual_report/...）
            company: 公司名（可选，用于加载公司特定配置）

        Returns:
            框架配置字典
        """
        # 1. 加载主框架配置
        frameworks = self._load_yaml("analysis_frameworks.yaml")

        # 2. 获取文档类型框架
        framework = frameworks.get("frameworks", {}).get(doc_type)
        if not framework:
            # 返回默认框架
            return self._get_default_framework(doc_type)

        # 3. 处理继承（如半年报继承年报）
        if "inherit" in framework:
            parent = frameworks["frameworks"].get(framework["inherit"], {})
            framework = self._merge_frameworks(parent, framework)

        # 4. 加载公司特定配置覆盖（如果有）
        if company:
            company_config = self._load_company_config(company)
            if company_config:
                framework = self._apply_company_overrides(framework, company_config)

        return framework

    def load_prompt_template(self, doc_type: str) -> Dict:
        """
        加载Prompt模板。

        Args:
            doc_type: 文档类型

        Returns:
            模板配置字典 {"template": "...", "output_schema": "..."}
        """
        template_path = self.config_dir / "prompts" / f"{doc_type}.yaml"
        if not template_path.exists():
            return self._get_default_prompt_template(doc_type)
        return self._load_yaml(template_path)

    def build_framework_description(self, framework: Dict) -> str:
        """
        构建框架描述文本（用于Prompt）。

        Args:
            framework: 框架配置

        Returns:
            格式化的框架描述文本
        """
        desc = ""
        for dim in framework.get("dimensions", []):
            desc += f"\n### {dim['name']}\n"
            if dim.get("required"):
                desc += "（必填）\n"
            for aspect in dim.get("aspects", []):
                desc += f"- {aspect}\n"
        return desc

    def build_source_sections_description(
        self, framework: Dict, discovered_sections: List[Dict]
    ) -> str:
        """
        构建来源章节描述（用于Prompt）。

        Args:
            framework: 框架配置
            discovered_sections: 从文档中发现的章节列表

        Returns:
            格式化的章节描述文本
        """
        section_types = framework.get("section_types", {})
        if not section_types:
            return "（请从全文提取）"

        desc = ""
        matched_types = set()

        for dim in framework.get("dimensions", []):
            section_type = dim.get("section_type")
            if section_type and section_type not in matched_types:
                # 从discovered_sections中找到匹配的章节
                matched = []
                for sec in discovered_sections:
                    if (
                        self._match_section_type(sec["title"], section_types)
                        == section_type
                    ):
                        matched.append(sec)

                if matched:
                    desc += f"\n### {dim['name']}\n"
                    for sec in matched:
                        desc += f"- 第{sec['number']}节 {sec['title']}\n"
                    matched_types.add(section_type)

        return desc if desc else "（请从全文提取）"

    def build_output_schema(self, framework: Dict) -> str:
        """
        构建输出Schema（用于Prompt）。

        Args:
            framework: 框架配置

        Returns:
            JSON格式的Schema描述
        """
        schema = {
            "document_type": framework.get("name", ""),
            "timeline_entries": [
                {
                    "date": "YYYY-MM-DD",
                    "title": "事件标题",
                    "key_points": ["要点1", "要点2"],
                    "source_type": "来源类型",
                    "importance": 0.0,
                    "sentiment": "positive/negative/neutral",
                }
            ],
            "dimensions": {},
            "assessment": "总体评估（100字内）",
            "key_insights": ["洞察1", "洞察2"],
            "new_questions": ["新问题1"],
        }

        # 根据框架构建dimensions示例
        for dim in framework.get("dimensions", []):
            dim_example = {
                "name": dim["name"],
                "source_section": "来源章节名称",
                "items": [
                    {
                        "aspect": dim["aspects"][0] if dim.get("aspects") else "方面",
                        "finding": "你的发现",
                        "evidence": "原文依据",
                    }
                ],
            }
            schema["dimensions"][dim["id"]] = dim_example

        return json.dumps(schema, ensure_ascii=False, indent=2)

    def _load_yaml(self, filename: str) -> Dict:
        """
        加载YAML文件（带缓存）。
        """
        if filename in self._cache:
            return self._cache[filename]

        filepath = self.config_dir / filename
        if not filepath.exists():
            return {}

        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._cache[filename] = data
        return data

    def _load_company_config(self, company: str) -> Optional[Dict]:
        """
        加载公司特定配置。
        """
        company_config_path = (
            Path(__file__).parent.parent / "companies" / company / "config.yaml"
        )
        if not company_config_path.exists():
            return None
        return self._load_yaml(company_config_path)

    def _get_default_framework(self, doc_type: str) -> Dict:
        """
        获取默认框架（当配置文件不存在时）。
        """
        return {
            "name": doc_type,
            "description": "默认分析框架",
            "section_types": {},
            "dimensions": [
                {
                    "id": "general",
                    "name": "通用分析",
                    "required": True,
                    "aspects": ["关键信息提取", "风险识别", "趋势判断"],
                }
            ],
        }

    def _get_default_prompt_template(self, doc_type: str) -> Dict:
        """
        获取默认Prompt模板。
        """
        return {
            "template": "请分析以下内容，提取关键信息并按JSON格式输出。",
            "output_schema": '{"timeline_entries": [...], "dimensions": {...}}',
        }

    def _merge_frameworks(self, parent: Dict, child: Dict) -> Dict:
        """
        合并框架（子框架覆盖父框架）。
        """
        merged = parent.copy()
        merged.update(child)

        # 合并dimensions（子框架的dimensions覆盖父框架同id的dimension）
        if "dimensions" in child:
            parent_dims = {d["id"]: d for d in parent.get("dimensions", [])}
            parent_dims.update({d["id"]: d for d in child["dimensions"]})
            merged["dimensions"] = list(parent_dims.values())

        return merged

    def _apply_company_overrides(self, framework: Dict, company_config: Dict) -> Dict:
        """
        应用公司特定配置覆盖。
        """
        # 公司配置可以添加额外的维度或关注点
        extra_dims = company_config.get("extra_dimensions", [])
        if extra_dims:
            framework["dimensions"].extend(extra_dims)
        return framework

    def _match_section_type(
        self, section_title: str, section_types: Dict
    ) -> Optional[str]:
        """
        匹配章节类型。
        """
        for section_type, config in section_types.items():
            patterns = config.get("patterns", [])
            for pattern in patterns:
                if pattern in section_title:
                    return section_type
        return None


# 测试代码
if __name__ == "__main__":
    print("测试框架加载器")
    print("=" * 60)

    loader = FrameworkLoader()

    # 测试加载各种框架
    for doc_type in [
        "prospectus",
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
    ]:
        framework = loader.load_framework(doc_type)
        print(f"\n{doc_type}:")
        print(f"  名称: {framework.get('name')}")
        print(f"  维度数: {len(framework.get('dimensions', []))}")
        print(f"  章节类型: {list(framework.get('section_types', {}).keys())}")

    # 测试构建框架描述
    print("\n" + "=" * 60)
    print("招股书框架描述:")
    framework = loader.load_framework("prospectus")
    desc = loader.build_framework_description(framework)
    print(desc[:500])

    # 测试构建输出Schema
    print("\n" + "=" * 60)
    print("招股书输出Schema:")
    schema = loader.build_output_schema(framework)
    print(schema[:500])
