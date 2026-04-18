#!/usr/bin/env python3
"""
contradiction_detector.py — 矛盾检测模块
检测不同页面之间的矛盾陈述

用法：
    python3 scripts/contradiction_detector.py                    # 检测所有矛盾
    python3 scripts/contradiction_detector.py --company 中微公司  # 检测指定公司
    python3 scripts/contradiction_detector.py --report           # 生成报告
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


@dataclass
class Contradiction:
    """矛盾"""
    entity1: str
    entity1_type: str
    page1: str
    statement1: str
    
    entity2: str
    entity2_type: str
    page2: str
    statement2: str
    
    contradiction_type: str  # numeric, temporal, categorical
    confidence: str  # high, medium, low
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entity1": self.entity1,
            "entity1_type": self.entity1_type,
            "page1": self.page1,
            "statement1": self.statement1,
            "entity2": self.entity2,
            "entity2_type": self.entity2_type,
            "page2": self.page2,
            "statement2": self.statement2,
            "contradiction_type": self.contradiction_type,
            "confidence": self.confidence,
            "description": self.description,
        }


class ContradictionDetector:
    """矛盾检测器"""
    
    def __init__(self, wiki_root: Path):
        """
        初始化检测器
        
        Args:
            wiki_root: Wiki 根目录
        """
        self.wiki_root = wiki_root
        self.graph = Graph(str(wiki_root / "graph.yaml"))
    
    def detect_all(self) -> List[Contradiction]:
        """
        检测所有矛盾
        
        Returns:
            矛盾列表
        """
        contradictions = []
        
        # 1. 检测数值矛盾
        contradictions.extend(self._detect_numeric_contradictions())
        
        # 2. 检测时间矛盾
        contradictions.extend(self._detect_temporal_contradictions())
        
        # 3. 检测分类矛盾
        contradictions.extend(self._detect_categorical_contradictions())
        
        # 4. 检测跨页面不一致
        contradictions.extend(self._detect_cross_page_inconsistencies())
        
        return contradictions
    
    def _detect_numeric_contradictions(self) -> List[Contradiction]:
        """
        检测数值矛盾
        
        Returns:
            矛盾列表
        """
        contradictions = []
        
        # 收集所有数值陈述
        numeric_statements = self._collect_numeric_statements()
        
        # 按实体分组
        by_entity: Dict[str, List[Dict[str, Any]]] = {}
        for stmt in numeric_statements:
            entity = stmt["entity"]
            if entity not in by_entity:
                by_entity[entity] = []
            by_entity[entity].append(stmt)
        
        # 检查同一实体的不同数值
        for entity, statements in by_entity.items():
            if len(statements) < 2:
                continue
            
            # 按指标分组
            by_metric: Dict[str, List[Dict[str, Any]]] = {}
            for stmt in statements:
                metric = stmt["metric"]
                if metric not in by_metric:
                    by_metric[metric] = []
                by_metric[metric].append(stmt)
            
            # 检查同一指标的不同数值
            for metric, metric_stmts in by_metric.items():
                if len(metric_stmts) < 2:
                    continue
                
                # 比较数值
                for i in range(len(metric_stmts)):
                    for j in range(i + 1, len(metric_stmts)):
                        stmt1 = metric_stmts[i]
                        stmt2 = metric_stmts[j]
                        
                        # 跳过同一页面内的比较
                        if stmt1["page"] == stmt2["page"]:
                            continue
                        
                        # 检查是否矛盾
                        if self._is_numeric_contradiction(stmt1, stmt2):
                            contradictions.append(Contradiction(
                                entity1=entity,
                                entity1_type=stmt1["entity_type"],
                                page1=stmt1["page"],
                                statement1=stmt1["statement"],
                                entity2=entity,
                                entity2_type=stmt2["entity_type"],
                                page2=stmt2["page"],
                                statement2=stmt2["statement"],
                                contradiction_type="numeric",
                                confidence="medium",
                                description=f"数值矛盾: {metric} 在不同页面有不同值",
                            ))
        
        return contradictions
    
    def _collect_numeric_statements(self) -> List[Dict[str, Any]]:
        """
        收集数值陈述
        
        Returns:
            数值陈述列表
        """
        statements = []
        
        # 扫描所有 wiki 页面
        for wiki_file in self.wiki_root.rglob("*/wiki/*.md"):
            try:
                content = wiki_file.read_text(encoding="utf-8")
                
                # 提取实体信息
                entity_name = self._extract_entity_name(content, wiki_file)
                entity_type = self._extract_entity_type(wiki_file)
                
                # 提取数值陈述
                # 模式：数字 + 单位 + 指标
                patterns = [
                    (r'(\d+\.?\d*)\s*%', '百分比'),
                    (r'(\d+\.?\d*)\s*亿', '金额（亿）'),
                    (r'(\d+\.?\d*)\s*万', '金额（万）'),
                    (r'(\d+)\s*倍', '倍数'),
                    (r'(\d+)\s*台', '数量（台）'),
                    (r'(\d+)\s*片', '数量（片）'),
                ]
                
                for pattern, metric_type in patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # 提取上下文
                        start = max(0, match.start() - 30)
                        end = min(len(content), match.end() + 30)
                        context = content[start:end].replace('\n', ' ')
                        
                        statements.append({
                            "entity": entity_name,
                            "entity_type": entity_type,
                            "page": str(wiki_file.relative_to(self.wiki_root)),
                            "value": float(match.group(1)),
                            "metric": metric_type,
                            "statement": context,
                        })
            
            except Exception as e:
                continue
        
        return statements
    
    def _is_numeric_contradiction(self, stmt1: Dict[str, Any], stmt2: Dict[str, Any]) -> bool:
        """
        判断是否数值矛盾
        
        Args:
            stmt1: 陈述1
            stmt2: 陈述2
            
        Returns:
            True 如果矛盾
        """
        val1 = stmt1["value"]
        val2 = stmt2["value"]
        
        # 如果数值相同，不矛盾
        if val1 == val2:
            return False
        
        # 只检查同一实体、同一指标、同一实体类型的矛盾
        if stmt1["entity"] != stmt2["entity"]:
            return False
        
        if stmt1["entity_type"] != stmt2["entity_type"]:
            return False
        
        if stmt1["metric"] != stmt2["metric"]:
            return False
        
        # 检查上下文是否相关
        # 如果上下文中包含不同的公司/产品，可能不是矛盾
        context1 = stmt1.get("statement", "")
        context2 = stmt2.get("statement", "")
        
        # 提取上下文中的公司/产品名称
        companies1 = set(re.findall(r'[\u4e00-\u9fff]{2,}(?:公司|集团|股份|科技|电子|半导体)', context1))
        companies2 = set(re.findall(r'[\u4e00-\u9fff]{2,}(?:公司|集团|股份|科技|电子|半导体)', context2))
        
        # 如果上下文中提到不同的公司，可能不是矛盾
        if companies1 and companies2 and companies1 != companies2:
            return False
        
        # 如果数值差异超过 30%，可能是矛盾
        if val1 > 0 and val2 > 0:
            diff_ratio = abs(val1 - val2) / max(val1, val2)
            if diff_ratio > 0.3:
                return True
        
        return False
    
    def _detect_temporal_contradictions(self) -> List[Contradiction]:
        """
        检测时间矛盾
        
        Returns:
            矛盾列表
        """
        contradictions = []
        
        # 收集时间相关陈述
        temporal_statements = self._collect_temporal_statements()
        
        # 按实体分组
        by_entity: Dict[str, List[Dict[str, Any]]] = {}
        for stmt in temporal_statements:
            entity = stmt["entity"]
            if entity not in by_entity:
                by_entity[entity] = []
            by_entity[entity].append(stmt)
        
        # 检查时间顺序
        for entity, statements in by_entity.items():
            # 按日期排序
            sorted_stmts = sorted(statements, key=lambda s: s["date"])
            
            # 检查是否有时间倒流
            for i in range(len(sorted_stmts) - 1):
                stmt1 = sorted_stmts[i]
                stmt2 = sorted_stmts[i + 1]
                
                # 如果同一事件在不同时间出现
                if self._is_same_event(stmt1, stmt2) and stmt1["date"] != stmt2["date"]:
                    contradictions.append(Contradiction(
                        entity1=entity,
                        entity1_type=stmt1["entity_type"],
                        page1=stmt1["page"],
                        statement1=stmt1["statement"],
                        entity2=entity,
                        entity2_type=stmt2["entity_type"],
                        page2=stmt2["page"],
                        statement2=stmt2["statement"],
                        contradiction_type="temporal",
                        confidence="medium",
                        description=f"时间矛盾: 同一事件在不同时间出现",
                    ))
        
        return contradictions
    
    def _collect_temporal_statements(self) -> List[Dict[str, Any]]:
        """
        收集时间相关陈述
        
        Returns:
            时间陈述列表
        """
        statements = []
        
        # 扫描所有 wiki 页面
        for wiki_file in self.wiki_root.rglob("*/wiki/*.md"):
            try:
                content = wiki_file.read_text(encoding="utf-8")
                
                # 提取实体信息
                entity_name = self._extract_entity_name(content, wiki_file)
                entity_type = self._extract_entity_type(wiki_file)
                
                # 提取时间线条目
                timeline_entries = re.findall(r'### (\d{4}-\d{2}-\d{2}) \| (.+?) \| (.+)', content)
                
                for date, source_type, title in timeline_entries:
                    statements.append({
                        "entity": entity_name,
                        "entity_type": entity_type,
                        "page": str(wiki_file.relative_to(self.wiki_root)),
                        "date": date,
                        "title": title,
                        "statement": f"{date} | {source_type} | {title}",
                    })
            
            except Exception as e:
                continue
        
        return statements
    
    def _is_same_event(self, stmt1: Dict[str, Any], stmt2: Dict[str, Any]) -> bool:
        """
        判断是否同一事件
        
        Args:
            stmt1: 陈述1
            stmt2: 陈述2
            
        Returns:
            True 如果是同一事件
        """
        title1 = stmt1.get("title", "").lower()
        title2 = stmt2.get("title", "").lower()
        
        # 简单的相似度检查
        # 如果标题有超过 50% 的重叠，认为是同一事件
        words1 = set(re.findall(r'[\u4e00-\u9fff]{2,}', title1))
        words2 = set(re.findall(r'[\u4e00-\u9fff]{2,}', title2))
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1 & words2)
        min_len = min(len(words1), len(words2))
        
        return overlap / min_len > 0.5
    
    def _detect_categorical_contradictions(self) -> List[Contradiction]:
        """
        检测分类矛盾
        
        Returns:
            矛盾列表
        """
        contradictions = []
        
        # 收集分类相关陈述
        categorical_statements = self._collect_categorical_statements()
        
        # 按实体分组
        by_entity: Dict[str, List[Dict[str, Any]]] = {}
        for stmt in categorical_statements:
            entity = stmt["entity"]
            if entity not in by_entity:
                by_entity[entity] = []
            by_entity[entity].append(stmt)
        
        # 检查分类冲突
        for entity, statements in by_entity.items():
            # 按属性分组
            by_attribute: Dict[str, List[Dict[str, Any]]] = {}
            for stmt in statements:
                attr = stmt["attribute"]
                if attr not in by_attribute:
                    by_attribute[attr] = []
                by_attribute[attr].append(stmt)
            
            # 检查同一属性的不同值
            for attr, attr_stmts in by_attribute.items():
                if len(attr_stmts) < 2:
                    continue
                
                # 提取所有值
                values = [stmt["value"] for stmt in attr_stmts]
                unique_values = list(set(values))
                
                if len(unique_values) > 1:
                    # 有冲突的值
                    for i in range(len(attr_stmts)):
                        for j in range(i + 1, len(attr_stmts)):
                            stmt1 = attr_stmts[i]
                            stmt2 = attr_stmts[j]
                            
                            if stmt1["value"] != stmt2["value"]:
                                contradictions.append(Contradiction(
                                    entity1=entity,
                                    entity1_type=stmt1["entity_type"],
                                    page1=stmt1["page"],
                                    statement1=stmt1["statement"],
                                    entity2=entity,
                                    entity2_type=stmt2["entity_type"],
                                    page2=stmt2["page"],
                                    statement2=stmt2["statement"],
                                    contradiction_type="categorical",
                                    confidence="low",
                                    description=f"分类矛盾: {attr} 有不同值",
                                ))
        
        return contradictions
    
    def _collect_categorical_statements(self) -> List[Dict[str, Any]]:
        """
        收集分类相关陈述
        
        Returns:
            分类陈述列表
        """
        statements = []
        
        # 分类属性模式
        attribute_patterns = [
            (r'行业[：:]\s*(.+)', '行业'),
            (r'领域[：:]\s*(.+)', '领域'),
            (r'类型[：:]\s*(.+)', '类型'),
            (r'地位[：:]\s*(.+)', '地位'),
            (r'定位[：:]\s*(.+)', '定位'),
        ]
        
        # 扫描所有 wiki 页面
        for wiki_file in self.wiki_root.rglob("*/wiki/*.md"):
            try:
                content = wiki_file.read_text(encoding="utf-8")
                
                # 提取实体信息
                entity_name = self._extract_entity_name(content, wiki_file)
                entity_type = self._extract_entity_type(wiki_file)
                
                # 提取分类陈述
                for pattern, attribute in attribute_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        value = match.group(1).strip()
                        
                        statements.append({
                            "entity": entity_name,
                            "entity_type": entity_type,
                            "page": str(wiki_file.relative_to(self.wiki_root)),
                            "attribute": attribute,
                            "value": value,
                            "statement": match.group(0),
                        })
            
            except Exception as e:
                continue
        
        return statements
    
    def _detect_cross_page_inconsistencies(self) -> List[Contradiction]:
        """
        检测跨页面不一致
        
        Returns:
            矛盾列表
        """
        contradictions = []
        
        # 检查公司和行业的关系
        companies = self.graph.get_all_companies()
        
        for company in companies:
            company_name = company["name"]
            company_sectors = company.get("sectors", [])
            
            # 检查公司 wiki 页面中提到的行业
            company_wiki_dir = self.wiki_root / "companies" / company_name / "wiki"
            if not company_wiki_dir.exists():
                continue
            
            for wiki_file in company_wiki_dir.glob("*.md"):
                try:
                    content = wiki_file.read_text(encoding="utf-8")
                    
                    # 提取页面中提到的行业
                    mentioned_sectors = []
                    for sector in company_sectors:
                        if sector in content:
                            mentioned_sectors.append(sector)
                    
                    # 检查是否所有行业都被提及
                    if len(mentioned_sectors) < len(company_sectors):
                        # 可能有遗漏，但这不是矛盾
                        pass
                
                except Exception as e:
                    continue
        
        return contradictions
    
    def _extract_entity_name(self, content: str, file_path: Path) -> str:
        """
        提取实体名称
        
        Args:
            content: 页面内容
            file_path: 文件路径
            
        Returns:
            实体名称
        """
        # 从 frontmatter 提取
        match = re.search(r'entity:\s*"?([^"\n]+)"?', content)
        if match:
            return match.group(1).strip()
        
        # 从文件路径推断
        parts = file_path.parts
        for i, part in enumerate(parts):
            if part in ("companies", "sectors", "themes") and i + 1 < len(parts):
                # 使用完整的路径作为实体标识
                entity_name = parts[i + 1]
                # 如果有 wiki 文件名，也加上
                if i + 3 < len(parts) and parts[i + 2] == "wiki":
                    wiki_file = parts[i + 3].replace(".md", "")
                    return f"{entity_name}/{wiki_file}"
                return entity_name
        
        return "Unknown"
    
    def _extract_entity_type(self, file_path: Path) -> str:
        """
        提取实体类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            实体类型
        """
        parts = file_path.parts
        for part in parts:
            if part == "companies":
                return "company"
            elif part == "sectors":
                return "sector"
            elif part == "themes":
                return "theme"
        
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="矛盾检测")
    parser.add_argument("--company", type=str, help="检测指定公司")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument("--output", type=str, help="输出文件路径")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  上市公司知识库 — 矛盾检测")
    print("=" * 50)
    
    # 初始化检测器
    detector = ContradictionDetector(WIKI_ROOT)
    
    # 检测矛盾
    print("\n检测矛盾...")
    contradictions = detector.detect_all()
    
    print(f"\n发现 {len(contradictions)} 个潜在矛盾:")
    
    # 按类型分组
    by_type: Dict[str, List[Contradiction]] = {}
    for c in contradictions:
        if c.contradiction_type not in by_type:
            by_type[c.contradiction_type] = []
        by_type[c.contradiction_type].append(c)
    
    for ctype, clist in by_type.items():
        print(f"\n{ctype} 矛盾 ({len(clist)}个):")
        for c in clist[:5]:  # 只显示前5个
            print(f"  - {c.description}")
            print(f"    页面1: {c.page1}")
            print(f"    页面2: {c.page2}")
    
    if args.report:
        # 生成报告
        report_path = args.output or str(WIKI_ROOT / "contradiction_report.md")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 矛盾检测报告\n\n")
            f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"## 概述\n\n")
            f.write(f"发现 {len(contradictions)} 个潜在矛盾\n\n")
            
            for ctype, clist in by_type.items():
                f.write(f"## {ctype} 矛盾 ({len(clist)}个)\n\n")
                for c in clist:
                    f.write(f"### {c.description}\n\n")
                    f.write(f"- **页面1**: {c.page1}\n")
                    f.write(f"- **陈述1**: {c.statement1}\n")
                    f.write(f"- **页面2**: {c.page2}\n")
                    f.write(f"- **陈述2**: {c.statement2}\n")
                    f.write(f"- **置信度**: {c.confidence}\n\n")
        
        print(f"\n报告已保存到: {report_path}")


if __name__ == "__main__":
    main()