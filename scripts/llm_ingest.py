#!/usr/bin/env python3
"""
llm_ingest.py — LLM 增强的 Ingest 流程 (备用入口，类式实现)
参考 Karpathy LLM Wiki 概念，添加 LLM 参与 ingest

主入口: ingest.py (规则驱动)
备选:   ingest_with_llm.py (函数式 LLM 入口)

用法：
    python3 scripts/llm_ingest.py --file path/to/file.md
    python3 scripts/llm_ingest.py --company 中微公司
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from config import Config
from graph import Graph
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMAnalysis:
    """LLM 分析结果"""
    key_points: List[str] = field(default_factory=list)
    affected_topics: List[Tuple[str, str, str]] = field(default_factory=list)
    timeline_entry: str = ""
    contradictions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_points": self.key_points,
            "affected_topics": self.affected_topics,
            "timeline_entry": self.timeline_entry,
            "contradictions": self.contradictions,
            "confidence": self.confidence,
        }


class LLMIngester:
    """LLM 增强的 Ingest"""
    
    def __init__(self, config: Config):
        """
        初始化
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.graph = Graph(str(config.paths.wiki_root / "graph.yaml"))
    
    def analyze_with_llm(self, content: str, entity_name: str, entity_type: str) -> LLMAnalysis:
        """
        使用 LLM 分析内容
        
        Args:
            content: 文件内容
            entity_name: 实体名称
            entity_type: 实体类型
            
        Returns:
            LLM 分析结果
        """
        # 获取相关问题
        questions = self._get_relevant_questions(entity_name, entity_type)
        
        # 构建 prompt
        prompt = self._build_analysis_prompt(content, entity_name, entity_type, questions)
        
        # 调用 LLM
        try:
            response = self._call_llm(prompt)
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return self._fallback_analysis(content, entity_name, entity_type)
    
    def _get_relevant_questions(self, entity_name: str, entity_type: str) -> List[str]:
        """获取相关问题"""
        questions = []
        
        if entity_type == "company":
            company = self.graph.get_company(entity_name)
            if company:
                for sector_name in company.get("sectors", []):
                    sector = self.graph.get_sector(sector_name)
                    if sector:
                        questions.extend(sector.get("questions", []))
        elif entity_type == "sector":
            sector = self.graph.get_sector(entity_name)
            if sector:
                questions = sector.get("questions", [])
        
        return questions
    
    def _build_analysis_prompt(self, content: str, entity_name: str, 
                               entity_type: str, questions: List[str]) -> str:
        """构建分析 prompt"""
        questions_str = "\n".join(f"- {q}" for q in questions) if questions else "（无预设问题）"
        
        # 截断内容避免过长
        content_truncated = content[:3000] if len(content) > 3000 else content
        
        return f"""你是一个上市公司研究分析专家。请分析以下文档，提取关键信息。

## 文档信息
- 实体: {entity_name}
- 类型: {entity_type}

## 待分析内容
{content_truncated}

## 预设问题
{questions_str}

## 请提供以下分析

### 1. 关键要点（3-5条）
列出文档中最重要的信息点。

### 2. 影响的主题
这份文档影响哪些主题？格式：实体名称 | 实体类型 | 主题名称

### 3. 时间线条目
生成一个时间线条目，格式：
### YYYY-MM-DD | 来源类型 | 标题
- 要点1
- 要点2

### 4. 是否回答了预设问题
对于每个预设问题，如果文档提供了相关信息，请指出。

### 5. 矛盾检测
这份文档是否与常见认知有矛盾之处？

请用中文回答，保持简洁。"""
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM (使用统一客户端)

        Args:
            prompt: 提示词

        Returns:
            LLM 响应
        """
        from llm_client import get_llm_client
        llm = get_llm_client()
        system = "你是一个专业的上市公司研究分析助手。"
        response = llm.chat_with_retry(prompt, system)
        if response.success:
            return response.content
        raise RuntimeError(f"LLM 调用失败: {response.error}")
    
    def _parse_llm_response(self, response: str) -> LLMAnalysis:
        """
        解析 LLM 响应
        
        Args:
            response: LLM 响应文本
            
        Returns:
            LLM 分析结果
        """
        analysis = LLMAnalysis()
        
        # 提取关键要点
        if "关键要点" in response:
            section = self._extract_section(response, "关键要点")
            points = [line.strip("- ") for line in section.split("\n") if line.strip().startswith("-")]
            analysis.key_points = points[:5]
        
        # 提取时间线条目
        if "时间线条目" in response:
            section = self._extract_section(response, "时间线条目")
            if "###" in section:
                entry_start = section.index("###")
                analysis.timeline_entry = section[entry_start:].strip()
        
        # 提取矛盾检测
        if "矛盾" in response:
            section = self._extract_section(response, "矛盾")
            if "是" in section.lower() or "有" in section.lower():
                contradictions = [line.strip("- ") for line in section.split("\n") if line.strip().startswith("-")]
                analysis.contradictions = contradictions
        
        # 简单置信度评估
        analysis.confidence = 0.8 if analysis.key_points else 0.5
        
        return analysis
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """提取文本中的某个章节"""
        lines = text.split("\n")
        section_lines = []
        in_section = False
        
        for line in lines:
            if section_name in line:
                in_section = True
                continue
            elif in_section and line.startswith("###"):
                break
            elif in_section:
                section_lines.append(line)
        
        return "\n".join(section_lines)
    
    def _fallback_analysis(self, content: str, entity_name: str, 
                          entity_type: str) -> LLMAnalysis:
        """
        回退分析（LLM 不可用时）
        
        Args:
            content: 内容
            entity_name: 实体名称
            entity_type: 实体类型
            
        Returns:
            基础分析结果
        """
        from utils import extract_keywords
        
        # 基础关键词提取
        keywords = extract_keywords(content, max_length=10)
        
        # 相关性匹配
        related = self.graph.find_related_entities(content[:1000], company_hint=entity_name if entity_type == "company" else None)
        
        # 生成基础时间线条目
        title = content.split("\n")[0].strip("# ") if content else "未知标题"
        published = datetime.now().strftime("%Y-%m-%d")
        
        timeline_entry = f"""### {published} | 新闻 | {title}
- {keywords[0] if keywords else "内容已处理"}

- [来源](../raw/news/文件.md)
"""
        
        return LLMAnalysis(
            key_points=keywords[:3],
            affected_topics=related[:3],
            timeline_entry=timeline_entry,
            contradictions=[],
            confidence=0.5,
        )
    
    def process_file(self, file_path: Path, dry_run: bool = False) -> Dict[str, Any]:
        """
        处理单个文件
        
        Args:
            file_path: 文件路径
            dry_run: 只分析不执行
            
        Returns:
            处理结果
        """
        logger.info(f"LLM 分析: {file_path}")
        
        # 读取文件
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        # 从路径推断实体
        entity_name, entity_type = self._infer_entity(file_path)
        
        # LLM 分析
        analysis = self.analyze_with_llm(content, entity_name, entity_type)
        
        result = {
            "file": str(file_path),
            "entity": entity_name,
            "entity_type": entity_type,
            "analysis": analysis.to_dict(),
            "dry_run": dry_run,
        }
        
        if not dry_run and analysis.timeline_entry:
            # 更新 wiki
            self._update_wiki(entity_name, entity_type, analysis)
            result["updated"] = True
        
        return result
    
    def _infer_entity(self, file_path: Path) -> Tuple[str, str]:
        """从文件路径推断实体"""
        parts = file_path.parts
        
        for i, part in enumerate(parts):
            if part == "companies" and i + 1 < len(parts):
                return parts[i + 1], "company"
            elif part == "sectors" and i + 1 < len(parts):
                return parts[i + 1], "sector"
            elif part == "themes" and i + 1 < len(parts):
                return parts[i + 1], "theme"
        
        return "Unknown", "unknown"
    
    def _update_wiki(self, entity_name: str, entity_type: str, analysis: LLMAnalysis) -> None:
        """更新 wiki"""
        if not analysis.timeline_entry:
            return
        
        # 确定 wiki 路径
        if entity_type == "company":
            wiki_dir = self.config.paths.wiki_root / "companies" / entity_name / "wiki"
        elif entity_type == "sector":
            wiki_dir = self.config.paths.wiki_root / "sectors" / entity_name / "wiki"
        else:
            return
        
        # 查找或创建 wiki 文件
        wiki_file = wiki_dir / f"{entity_name}.md"
        
        if not wiki_file.exists():
            # 创建新文件
            template = self._create_wiki_template(entity_name, entity_type)
            wiki_file.write_text(template, encoding="utf-8")
        
        # 读取现有内容
        content = wiki_file.read_text(encoding="utf-8")
        
        # 插入时间线条目
        timeline_pos = content.find("## 时间线")
        if timeline_pos >= 0:
            insert_pos = timeline_pos + len("## 时间线")
            content = content[:insert_pos] + "\n\n" + analysis.timeline_entry + content[insert_pos:]
            
            # 更新 frontmatter
            content = content.replace(
                'last_updated: "2026-01-01"',
                f'last_updated: "{datetime.now().strftime("%Y-%m-%d")}"'
            )
            
            # 保存
            wiki_file.write_text(content, encoding="utf-8")
            logger.info(f"更新 wiki: {wiki_file}")
    
    def _create_wiki_template(self, entity_name: str, entity_type: str) -> str:
        """创建 wiki 模板"""
        return f"""---
title: "{entity_name}"
entity: "{entity_name}"
type: {entity_type}_topic
last_updated: "{datetime.now().strftime('%Y-%m-%d')}"
sources_count: 0
tags: []
---

# {entity_name}

## 核心问题
- （待设定）

## 时间线

（暂无条目）

## 综合评估
> 待积累数据后补充。
"""


def main():
    parser = argparse.ArgumentParser(description="LLM 增强的 Ingest")
    parser.add_argument("--file", type=str, help="处理指定文件")
    parser.add_argument("--company", type=str, help="处理指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只分析不执行")
    parser.add_argument("--limit", type=int, default=5, help="最多处理文件数")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  LLM 增强的 Ingest")
    print("=" * 50)
    
    # 加载配置
    try:
        config = Config.load()
    except Exception as e:
        print(f"配置加载失败: {e}")
        sys.exit(1)
    
    # 创建 ingester
    ingester = LLMIngester(config)
    
    if args.file:
        # 处理指定文件
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"文件不存在: {file_path}")
            sys.exit(1)
        
        result = ingester.process_file(file_path, dry_run=args.dry_run)
        print(f"\n分析结果:")
        print(f"  实体: {result['entity']} ({result['entity_type']})")
        print(f"  关键要点: {len(result['analysis']['key_points'])} 条")
        print(f"  时间线条目: {'有' if result['analysis']['timeline_entry'] else '无'}")
        print(f"  矛盾: {len(result['analysis']['contradictions'])} 个")
    
    elif args.company:
        # 处理指定公司
        company_dir = config.paths.wiki_root / "companies" / args.company / "raw"
        if not company_dir.exists():
            print(f"公司目录不存在: {company_dir}")
            sys.exit(1)
        
        # 找到最近的文件
        files = list(company_dir.rglob("*.md")) + list(company_dir.rglob("*.pdf"))
        files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[:args.limit]
        
        print(f"\n处理 {len(files)} 个文件...")
        
        for i, file_path in enumerate(files):
            print(f"\n[{i+1}/{len(files)}] {file_path.name}")
            result = ingester.process_file(file_path, dry_run=args.dry_run)
            print(f"  关键要点: {len(result['analysis']['key_points'])} 条")
    
    else:
        print("请指定 --file 或 --company")


if __name__ == "__main__":
    main()