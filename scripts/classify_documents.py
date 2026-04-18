#!/usr/bin/env python3
"""
classify_documents.py — 文档分类脚本
根据文件名和内容自动将文档分类到对应的子目录

用法：
    python3 scripts/classify_documents.py                    # 分类所有公司
    python3 scripts/classify_documents.py --company 中微公司  # 只分类指定公司
    python3 scripts/classify_documents.py --dry-run           # 只分析不执行
    python3 scripts/classify_documents.py --verify            # 验证分类结果
"""

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent


class DocumentType(str, Enum):
    """文档类型"""
    ANNUAL_REPORT = "annual_report"           # 年报
    SEMI_ANNUAL_REPORT = "semi_annual_report" # 半年报
    QUARTERLY_REPORT = "quarterly_report"     # 季报
    PROSPECTUS = "prospectus"                 # 招股说明书
    ANNOUNCEMENT = "announcement"             # 公告
    INVESTOR_RELATIONS = "investor_relations" # 投资者关系
    RESEARCH = "research"                     # 券商研报
    NEWS = "news"                             # 新闻
    UNKNOWN = "unknown"                       # 未知


# 文档类型到目录的映射
TYPE_TO_DIR = {
    DocumentType.ANNUAL_REPORT: "financial_reports/annual",
    DocumentType.SEMI_ANNUAL_REPORT: "financial_reports/semi_annual",
    DocumentType.QUARTERLY_REPORT: "financial_reports/quarterly",
    DocumentType.PROSPECTUS: "prospectus",
    DocumentType.ANNOUNCEMENT: "announcements",
    DocumentType.INVESTOR_RELATIONS: "investor_relations",
    DocumentType.RESEARCH: "research",
    DocumentType.NEWS: "news",
    DocumentType.UNKNOWN: "other",
}


@dataclass
class FileClassification:
    """文件分类结果"""
    file_path: Path
    document_type: DocumentType
    confidence: float
    reason: str
    target_dir: str
    target_path: Path


def load_classification_rules() -> Dict[str, Any]:
    """
    加载分类规则配置
    
    Returns:
        分类规则字典
    """
    config_path = WIKI_ROOT / "config_rules.yaml"
    
    if not config_path.exists():
        # 返回默认规则
        return get_default_classification_rules()
    
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("document_classification", get_default_classification_rules())
    except Exception as e:
        print(f"Warning: Failed to load config_rules.yaml: {e}")
        return get_default_classification_rules()


def get_default_classification_rules() -> Dict[str, Any]:
    """
    获取默认分类规则
    
    Returns:
        默认规则字典
    """
    return {
        "annual_report": {
            "patterns": ["年年度报告", "年年报"],
            "confidence": 0.95,
            "target_dir": "financial_reports/annual"
        },
        "semi_annual_report": {
            "patterns": ["半年度报告", "半年报"],
            "confidence": 0.95,
            "target_dir": "financial_reports/semi_annual"
        },
        "quarterly_report": {
            "patterns": ["第[一二三四]季度报告", "季报", "一季度报告", "二季度报告", "三季度报告", "四季度报告"],
            "confidence": 0.95,
            "target_dir": "financial_reports/quarterly"
        },
        "prospectus": {
            "patterns": ["招股说明书", "招股意向书"],
            "confidence": 0.95,
            "target_dir": "prospectus"
        },
        "investor_relations": {
            "patterns": ["投资者关系", "投资者交流", "投资者问答"],
            "confidence": 0.90,
            "target_dir": "investor_relations"
        },
        "announcement": {
            "patterns": ["公告", "决议", "通知", "提示"],
            "confidence": 0.80,
            "target_dir": "announcements"
        },
        "research": {
            "patterns": ["研报", "深度报告", "点评报告", "跟踪报告"],
            "confidence": 0.85,
            "target_dir": "research"
        },
        "news": {
            "file_extensions": [".md"],
            "confidence": 0.70,
            "target_dir": "news"
        }
    }


# 全局变量：分类规则
CLASSIFICATION_RULES = load_classification_rules()


def classify_by_filename(filename: str) -> Tuple[DocumentType, float, str]:
    """
    根据文件名分类文档
    
    Args:
        filename: 文件名
        
    Returns:
        (文档类型, 置信度, 原因)
    """
    # 类型映射
    type_mapping = {
        "annual_report": DocumentType.ANNUAL_REPORT,
        "semi_annual_report": DocumentType.SEMI_ANNUAL_REPORT,
        "quarterly_report": DocumentType.QUARTERLY_REPORT,
        "prospectus": DocumentType.PROSPECTUS,
        "investor_relations": DocumentType.INVESTOR_RELATIONS,
        "announcement": DocumentType.ANNOUNCEMENT,
        "research": DocumentType.RESEARCH,
        "news": DocumentType.NEWS,
    }
    
    # 遍历规则
    for rule_name, rule_config in CLASSIFICATION_RULES.items():
        patterns = rule_config.get("patterns", [])
        file_extensions = rule_config.get("file_extensions", [])
        confidence = rule_config.get("confidence", 0.5)
        target_dir = rule_config.get("target_dir", "other")
        
        # 检查文件扩展名
        if file_extensions:
            for ext in file_extensions:
                if filename.endswith(ext):
                    doc_type = type_mapping.get(rule_name, DocumentType.UNKNOWN)
                    return doc_type, confidence, f"文件扩展名匹配 {ext}"
        
        # 检查模式
        for pattern in patterns:
            if re.search(pattern, filename):
                doc_type = type_mapping.get(rule_name, DocumentType.UNKNOWN)
                return doc_type, confidence, f"文件名匹配模式 '{pattern}'"
    
    return DocumentType.UNKNOWN, 0.0, "无法根据文件名判断"


def classify_by_path(file_path: Path) -> Tuple[DocumentType, float, str]:
    """
    根据文件路径分类文档
    
    Args:
        file_path: 文件路径
        
    Returns:
        (文档类型, 置信度, 原因)
    """
    path_str = str(file_path)
    
    # 已经在分类目录中
    if "/news/" in path_str or "\\news\\" in path_str:
        return DocumentType.NEWS, 0.95, "文件已在 news 目录"
    
    if "/research/" in path_str or "\\research\\" in path_str:
        return DocumentType.RESEARCH, 0.90, "文件已在 research 目录"
    
    if "/reports/" in path_str or "\\reports\\" in path_str:
        # 需要进一步分析
        return DocumentType.UNKNOWN, 0.5, "文件在 reports 目录，需进一步分析"
    
    return DocumentType.UNKNOWN, 0.0, "无法根据路径判断"


def classify_document(file_path: Path) -> FileClassification:
    """
    分类单个文档
    
    Args:
        file_path: 文件路径
        
    Returns:
        分类结果
    """
    filename = file_path.name
    
    # 根据文件名分类
    type_by_name, conf_by_name, reason_by_name = classify_by_filename(filename)
    
    # 根据路径分类
    type_by_path, conf_by_path, reason_by_path = classify_by_path(file_path)
    
    # 选择置信度更高的分类
    if conf_by_name >= conf_by_path:
        doc_type = type_by_name
        confidence = conf_by_name
        reason = reason_by_name
    else:
        doc_type = type_by_path
        confidence = conf_by_path
        reason = reason_by_path
    
    # 如果还是未知，尝试其他方法
    if doc_type == DocumentType.UNKNOWN:
        # PDF 文件默认为研报或报告
        if filename.endswith('.pdf'):
            doc_type = DocumentType.RESEARCH
            confidence = 0.5
            reason = "PDF 文件默认分类为研报"
        # Markdown 文件默认为新闻
        elif filename.endswith('.md'):
            doc_type = DocumentType.NEWS
            confidence = 0.6
            reason = "Markdown 文件默认分类为新闻"
    
    # 计算目标目录
    target_dir = TYPE_TO_DIR.get(doc_type, "other")
    
    # 计算目标路径
    # 从 companies/{公司名}/raw/... 开始
    parts = file_path.parts
    try:
        raw_idx = parts.index("raw")
        company_idx = parts.index("companies") + 1
        company_name = parts[company_idx]
        
        # 目标路径：companies/{公司名}/raw/{target_dir}/{filename}
        target_path = WIKI_ROOT / "companies" / company_name / "raw" / target_dir / filename
    except (ValueError, IndexError):
        target_path = file_path.parent / target_dir / filename
    
    return FileClassification(
        file_path=file_path,
        document_type=doc_type,
        confidence=confidence,
        reason=reason,
        target_dir=target_dir,
        target_path=target_path,
    )


def scan_company_documents(company_name: str) -> List[FileClassification]:
    """
    扫描公司的所有文档
    
    Args:
        company_name: 公司名称
        
    Returns:
        分类结果列表
    """
    company_dir = WIKI_ROOT / "companies" / company_name
    raw_dir = company_dir / "raw"
    
    if not raw_dir.exists():
        return []
    
    classifications = []
    
    # 扫描 raw 目录下的所有文件
    for file_path in raw_dir.rglob("*"):
        if file_path.is_file():
            # 跳过已经在正确目录中的文件
            if is_correctly_classified(file_path):
                continue
            
            classification = classify_document(file_path)
            classifications.append(classification)
    
    return classifications


def is_correctly_classified(file_path: Path) -> bool:
    """
    检查文件是否已经正确分类
    
    Args:
        file_path: 文件路径
        
    Returns:
        True 如果已正确分类
    """
    path_str = str(file_path)
    
    # 检查是否在正确的子目录中
    correct_dirs = [
        "financial_reports/annual",
        "financial_reports/semi_annual",
        "financial_reports/quarterly",
        "prospectus",
        "announcements",
        "investor_relations",
        "research",
        "news",
    ]
    
    for correct_dir in correct_dirs:
        if f"/{correct_dir}/" in path_str or f"\\{correct_dir}\\" in path_str:
            return True
    
    return False


def create_target_directories(classifications: List[FileClassification]) -> None:
    """
    创建目标目录
    
    Args:
        classifications: 分类结果列表
    """
    dirs_to_create = set()
    
    for c in classifications:
        dirs_to_create.add(c.target_path.parent)
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)


def move_files(classifications: List[FileClassification], dry_run: bool = False) -> Dict[str, int]:
    """
    移动文件到目标目录
    
    Args:
        classifications: 分类结果列表
        dry_run: 只分析不执行
        
    Returns:
        统计信息
    """
    stats = {
        "total": len(classifications),
        "moved": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    for c in classifications:
        if dry_run:
            print(f"  [DRY] {c.file_path.name} -> {c.target_dir}/ ({c.document_type.value}, {c.confidence:.0%})")
            continue
        
        try:
            # 检查目标文件是否已存在
            if c.target_path.exists():
                print(f"  SKIP (exists): {c.file_path.name}")
                stats["skipped"] += 1
                continue
            
            # 移动文件
            shutil.move(str(c.file_path), str(c.target_path))
            print(f"  MOVE: {c.file_path.name} -> {c.target_dir}/")
            stats["moved"] += 1
            
        except Exception as e:
            print(f"  ERROR: {c.file_path.name} - {e}")
            stats["errors"] += 1
    
    return stats


def cleanup_empty_dirs(raw_dir: Path) -> None:
    """
    清理空目录
    
    Args:
        raw_dir: raw 目录
    """
    for dir_path in sorted(raw_dir.rglob("*"), reverse=True):
        if dir_path.is_dir() and dir_path != raw_dir:
            try:
                if not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    print(f"  CLEANUP: Removed empty directory {dir_path.name}/")
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="文档分类")
    parser.add_argument("--company", type=str, help="只分类指定公司")
    parser.add_argument("--dry-run", action="store_true", help="只分析不执行")
    parser.add_argument("--verify", action="store_true", help="验证分类结果")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  上市公司知识库 — 文档分类")
    print("=" * 50)
    
    # 获取公司列表
    companies_dir = WIKI_ROOT / "companies"
    if args.company:
        companies = [args.company]
    else:
        companies = [d.name for d in companies_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    
    total_stats = {
        "companies": 0,
        "files_analyzed": 0,
        "files_moved": 0,
        "files_skipped": 0,
        "errors": 0,
    }
    
    for company in companies:
        print(f"\n[{company}]")
        
        # 扫描文档
        classifications = scan_company_documents(company)
        
        if not classifications:
            print("  No files to classify")
            continue
        
        total_stats["companies"] += 1
        total_stats["files_analyzed"] += len(classifications)
        
        # 按类型统计
        type_counts = {}
        for c in classifications:
            type_counts[c.document_type.value] = type_counts.get(c.document_type.value, 0) + 1
        
        print(f"  Found {len(classifications)} files to classify:")
        for doc_type, count in sorted(type_counts.items()):
            print(f"    - {doc_type}: {count}")
        
        if args.verify:
            # 验证模式：只显示分类结果
            for c in classifications:
                print(f"    {c.file_path.name}")
                print(f"      Type: {c.document_type.value} ({c.confidence:.0%})")
                print(f"      Reason: {c.reason}")
                print(f"      Target: {c.target_dir}/")
            continue
        
        # 创建目标目录
        if not args.dry_run:
            create_target_directories(classifications)
        
        # 移动文件
        stats = move_files(classifications, args.dry_run)
        
        total_stats["files_moved"] += stats["moved"]
        total_stats["files_skipped"] += stats["skipped"]
        total_stats["errors"] += stats["errors"]
        
        # 清理空目录
        if not args.dry_run:
            raw_dir = companies_dir / company / "raw"
            if raw_dir.exists():
                cleanup_empty_dirs(raw_dir)
    
    # 打印总结
    print(f"\n{'=' * 50}")
    print("  Summary")
    print(f"{'=' * 50}")
    print(f"  Companies processed: {total_stats['companies']}")
    print(f"  Files analyzed: {total_stats['files_analyzed']}")
    print(f"  Files moved: {total_stats['files_moved']}")
    print(f"  Files skipped: {total_stats['files_skipped']}")
    print(f"  Errors: {total_stats['errors']}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()