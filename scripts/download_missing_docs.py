#!/usr/bin/env python3
"""
download_missing_docs.py — 下载缺失文档脚本
检查并下载缺失的财报、招股说明书、投资者关系文档

用法：
    python3 scripts/download_missing_docs.py                    # 检查并下载所有缺失文档
    python3 scripts/download_missing_docs.py --check            # 只检查不下载
    python3 scripts/download_missing_docs.py --company 中微公司  # 只处理指定公司
    python3 scripts/download_missing_docs.py --type annual       # 只下载年报
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 路径
SCRIPTS_DIR = Path(__file__).resolve().parent
WIKI_ROOT = SCRIPTS_DIR.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from graph import Graph


@dataclass
class MissingDoc:
    """缺失文档"""
    company_name: str
    ticker: str
    doc_type: str  # annual, semi_annual, quarterly, prospectus, investor_relations
    doc_name: str


def check_missing_documents(company_name: Optional[str] = None) -> List[MissingDoc]:
    """
    检查缺失文档
    
    Args:
        company_name: 只检查指定公司
        
    Returns:
        缺失文档列表
    """
    graph = Graph()
    companies = graph.get_all_companies()
    
    if company_name:
        companies = [c for c in companies if c['name'] == company_name]
    
    missing = []
    
    # 文档类型配置
    doc_configs = [
        {
            'type': 'annual',
            'name': '年报',
            'dir': 'financial_reports/annual',
            'check': lambda path: path.exists() and len(list(path.glob('*.pdf'))) > 0,
        },
        {
            'type': 'semi_annual',
            'name': '半年报',
            'dir': 'financial_reports/semi_annual',
            'check': lambda path: path.exists() and len(list(path.glob('*.pdf'))) > 0,
        },
        {
            'type': 'quarterly',
            'name': '季报',
            'dir': 'financial_reports/quarterly',
            'check': lambda path: path.exists() and len(list(path.glob('*.pdf'))) > 0,
        },
        {
            'type': 'prospectus',
            'name': '招股说明书',
            'dir': 'prospectus',
            'check': lambda path: path.exists() and len(list(path.glob('*.pdf'))) > 0,
        },
        {
            'type': 'investor_relations',
            'name': '投资者关系',
            'dir': 'investor_relations',
            'check': lambda path: path.exists() and len(list(path.glob('*.pdf'))) > 0,
        },
    ]
    
    for company in companies:
        name = company['name']
        ticker = company.get('ticker', '')
        exchange = company.get('exchange', '')
        
        # 只检查A股公司（有股票代码的）
        if not ticker or ticker == '':
            continue
        
        # 跳过非A股公司（美股、港股等）
        if exchange in ['NASDAQ', 'NYSE', 'HKEX']:
            continue
        
        company_dir = WIKI_ROOT / 'companies' / name / 'raw'
        
        for doc_config in doc_configs:
            doc_path = company_dir / doc_config['dir']
            
            if not doc_config['check'](doc_path):
                missing.append(MissingDoc(
                    company_name=name,
                    ticker=ticker,
                    doc_type=doc_config['type'],
                    doc_name=doc_config['name'],
                ))
    
    return missing


def download_documents(missing_docs: List[MissingDoc], doc_type: Optional[str] = None) -> Dict[str, Any]:
    """
    下载文档
    
    Args:
        missing_docs: 缺失文档列表
        doc_type: 只下载指定类型
        
    Returns:
        下载结果统计
    """
    stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'skipped': 0,
    }
    
    # 过滤文档类型
    if doc_type:
        missing_docs = [d for d in missing_docs if d.doc_type == doc_type]
    
    # 按公司分组
    by_company: Dict[str, List[MissingDoc]] = {}
    for doc in missing_docs:
        if doc.company_name not in by_company:
            by_company[doc.company_name] = []
        by_company[doc.company_name].append(doc)
    
    print(f'准备下载 {len(missing_docs)} 个文档，涉及 {len(by_company)} 家公司\\n')
    
    for company_name, docs in by_company.items():
        print(f'[{company_name}]')
        
        # 获取公司信息
        graph = Graph()
        company = graph.get_company(company_name)
        if not company:
            print(f'  ERROR: 公司信息不存在')
            continue
        
        ticker = company.get('ticker', '')
        
        for doc in docs:
            stats['total'] += 1
            
            # 使用 collect_reports.py 调用 StockInfoDownloader 下载
            cmd = [
                sys.executable,
                str(SCRIPTS_DIR / 'collect_reports.py'),
                '--company', company_name,
            ]
            
            print(f'  下载 {doc.doc_name}...')
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5分钟超时
                    cwd=str(WIKI_ROOT),
                )
                
                if result.returncode == 0:
                    print(f'    ✓ 成功')
                    stats['success'] += 1
                else:
                    print(f'    ✗ 失败: {result.stderr[:100]}')
                    stats['failed'] += 1
            
            except subprocess.TimeoutExpired:
                print(f'    ✗ 超时')
                stats['failed'] += 1
            except Exception as e:
                print(f'    ✗ 错误: {e}')
                stats['failed'] += 1
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="下载缺失文档")
    parser.add_argument("--check", action="store_true", help="只检查不下载")
    parser.add_argument("--company", type=str, help="只处理指定公司")
    parser.add_argument("--type", type=str, choices=['annual', 'semi_annual', 'quarterly', 'prospectus', 'investor_relations'], help="只下载指定类型")
    parser.add_argument("--download", action="store_true", help="执行下载")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  上市公司知识库 — 缺失文档检查")
    print("=" * 60)
    
    # 检查缺失文档
    print("\n检查缺失文档...")
    missing = check_missing_documents(args.company)
    
    # 按类型统计
    by_type: Dict[str, List[MissingDoc]] = {}
    for doc in missing:
        if doc.doc_type not in by_type:
            by_type[doc.doc_type] = []
        by_type[doc.doc_type].append(doc)
    
    print(f"\n发现 {len(missing)} 个缺失文档:")
    for doc_type, docs in by_type.items():
        print(f"\n{docs[0].doc_name} ({len(docs)}个):")
        # 按公司名排序
        docs_sorted = sorted(docs, key=lambda d: d.company_name)
        for doc in docs_sorted[:10]:
            print(f"  - {doc.company_name} ({doc.ticker})")
        if len(docs) > 10:
            print(f"  ... 还有 {len(docs) - 10} 个")
    
    if args.check:
        print("\n检查完成，未执行下载")
        return
    
    if args.download or not args.check:
        # 执行下载
        print("\n" + "=" * 60)
        print("  开始下载")
        print("=" * 60)
        
        stats = download_documents(missing, args.type)
        
        print("\n" + "=" * 60)
        print("  下载完成")
        print("=" * 60)
        print(f"总计: {stats['total']}")
        print(f"成功: {stats['success']}")
        print(f"失败: {stats['failed']}")
        print(f"跳过: {stats['skipped']}")


if __name__ == "__main__":
    main()