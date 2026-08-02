#!/usr/bin/env python3
"""
valuation_engine.py — 投资估值引擎

基于LLM生成投资级分析。

用法：
    python scripts/valuation_engine.py --company 中微公司 --dry-run   # 预览估值
    python scripts/valuation_engine.py --company 中微公司 --run       # 运行估值
"""

import argparse
import json
import re
from datetime import datetime

from common import WIKI_ROOT
from llm_client import LLMClient

VALUATION_PROMPT_TEMPLATE = """你是一名资深股票分析师。请基于以下公司信息，生成投资估值分析。

## 公司: {company}
## 行业: {sector}

## 最近财务数据
{financial_data}

## 最近时间线（最近10条）
{recent_timeline}

## 分析框架

请从以下维度进行分析：

1. **估值区间**
   - PE估值（基于行业平均PE）
   - PB估值（基于净资产）
   - DCF估值（基于未来现金流折现）
   - 综合估值区间

2. **同行对比**
   - 主要竞争对手
   - 估值对比（PE/PB）
   - 竞争优势对比

3. **催化剂**
   - 短期催化剂（3-6个月）
   - 中期催化剂（6-12个月）
   - 长期催化剂（1-3年）

4. **风险因素**
   - 主要风险
   - 风险等级（高/中/低）

5. **投资建议**
   - 看多/看空/中性
   - 目标价
   - 投资逻辑

## 输出格式
```json
{{
  "valuation": {{
    "pe_estimate": "PE估值区间",
    "pb_estimate": "PB估值区间",
    "dcf_estimate": "DCF估值",
    "comprehensive_range": "综合估值区间"
  }},
  "peer_comparison": {{
    "competitors": ["竞争对手1", "竞争对手2"],
    "valuation_comparison": "估值对比分析",
    "competitive_advantage": "竞争优势"
  }},
  "catalysts": {{
    "short_term": ["催化剂1", "催化剂2"],
    "medium_term": ["催化剂1", "催化剂2"],
    "long_term": ["催化剂1", "催化剂2"]
  }},
  "risks": {{
    "main_risks": ["风险1", "风险2"],
    "risk_level": "高/中/低"
  }},
  "recommendation": {{
    "stance": "bullish/bearish/neutral",
    "target_price": "目标价",
    "logic": "投资逻辑"
  }}
}}
```
"""


def get_company_info(company: str) -> dict:
    """获取公司信息"""
    import yaml

    companies_path = WIKI_ROOT / "companies.yaml"
    if not companies_path.exists():
        return {}

    data = yaml.safe_load(companies_path.read_text(encoding="utf-8"))
    companies = data.get("companies", {})

    return companies.get(company, {})


def get_financial_data(company: str) -> str:
    """获取最近财务数据"""
    extracts_dir = WIKI_ROOT / "companies" / company / "extracts"
    if not extracts_dir.exists():
        return "无财务数据"

    # 找到最新的年报分析文件
    annual_files = list(extracts_dir.glob("financial_reports/annual/*.analysis.json"))
    if not annual_files:
        return "无年报分析"

    # 按修改时间排序，取最新的
    latest_file = max(annual_files, key=lambda f: f.stat().st_mtime)

    try:
        data = json.loads(latest_file.read_text(encoding="utf-8"))
        llm_output = data.get("llm_output", "")

        # 提取财务数据
        if llm_output:
            parsed = json.loads(llm_output)
            financial_highlights = parsed.get("financial_highlights", {})
            dimensions = parsed.get("dimensions", {})

            return json.dumps(
                {
                    "financial_highlights": financial_highlights,
                    "dimensions": dimensions,
                },
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass

    return "财务数据解析失败"


def get_recent_timeline(company: str, max_entries: int = 10) -> str:
    """获取最近时间线"""
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    timeline_file = wiki_dir / "公司动态.md"

    if not timeline_file.exists():
        return "无时间线"

    content = timeline_file.read_text(encoding="utf-8")

    # 提取时间线条目
    entries = []
    current_entry = []

    for line in content.split("\n"):
        if line.startswith("### "):
            if current_entry:
                entries.append("\n".join(current_entry))
            current_entry = [line]
        elif current_entry:
            current_entry.append(line)

    if current_entry:
        entries.append("\n".join(current_entry))

    # 只取最近的条目
    recent = entries[-max_entries:]
    return "\n\n".join(recent)


def run_valuation(company: str, dry_run: bool = False) -> dict:
    """运行估值分析"""
    # 获取公司信息
    company_info = get_company_info(company)
    sector = ", ".join(company_info.get("sectors", []))

    # 获取财务数据
    financial_data = get_financial_data(company)

    # 获取最近时间线
    recent_timeline = get_recent_timeline(company)

    # 构建prompt
    prompt = VALUATION_PROMPT_TEMPLATE.format(
        company=company,
        sector=sector,
        financial_data=financial_data[:10000],
        recent_timeline=recent_timeline[:10000],
    )

    if dry_run:
        print("=" * 60)
        print("  预览估值分析")
        print("=" * 60)
        print(f"\n公司: {company}")
        print(f"行业: {sector}")
        print(f"\nPrompt长度: {len(prompt)} 字符")
        return {"success": True, "dry_run": True}

    # 调用LLM
    try:
        client = LLMClient()
        response = client.generate(prompt)
        result_text = response.content
    except Exception as e:
        return {"success": False, "error": str(e)}

    # 解析结果
    try:
        # 提取JSON
        json_match = re.search(r"```json\s*\n?(.*?)\n?```", result_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            result = json.loads(result_text)
    except Exception:
        result = {"raw_text": result_text}

    # 保存估值结果
    wiki_dir = WIKI_ROOT / "companies" / company / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    valuation_file = wiki_dir / "投资估值.md"
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # 构建页面内容
    content = f"""---
title: {company} 投资估值
description: 基于LLM的投资估值分析
entity: {company}
type: overview
last_updated: {timestamp}
source: valuation_engine
---

# {company} 投资估值

**生成时间**: {timestamp}
**生成方式**: 投资估值引擎

---

## 估值区间

"""

    valuation = result.get("valuation", {})
    content += f"- **PE估值**: {valuation.get('pe_estimate', '待分析')}\n"
    content += f"- **PB估值**: {valuation.get('pb_estimate', '待分析')}\n"
    content += f"- **DCF估值**: {valuation.get('dcf_estimate', '待分析')}\n"
    content += f"- **综合估值**: {valuation.get('comprehensive_range', '待分析')}\n"

    content += "\n## 同行对比\n\n"

    peer = result.get("peer_comparison", {})
    content += f"**竞争对手**: {', '.join(peer.get('competitors', []))}\n\n"
    content += f"**估值对比**: {peer.get('valuation_comparison', '待分析')}\n\n"
    content += f"**竞争优势**: {peer.get('competitive_advantage', '待分析')}\n"

    content += "\n## 催化剂\n\n"

    catalysts = result.get("catalysts", {})
    content += "### 短期（3-6个月）\n"
    for c in catalysts.get("short_term", []):
        content += f"- {c}\n"
    content += "\n### 中期（6-12个月）\n"
    for c in catalysts.get("medium_term", []):
        content += f"- {c}\n"
    content += "\n### 长期（1-3年）\n"
    for c in catalysts.get("long_term", []):
        content += f"- {c}\n"

    content += "\n## 风险因素\n\n"

    risks = result.get("risks", {})
    content += f"**风险等级**: {risks.get('risk_level', '待评估')}\n\n"
    for r in risks.get("main_risks", []):
        content += f"- {r}\n"

    content += "\n## 投资建议\n\n"

    rec = result.get("recommendation", {})
    stance_map = {"bullish": "看多", "bearish": "看空", "neutral": "中性"}
    content += f"**评级**: {stance_map.get(rec.get('stance', ''), '待定')}\n"
    content += f"**目标价**: {rec.get('target_price', '待定')}\n\n"
    content += f"**投资逻辑**:\n{rec.get('logic', '待分析')}\n"

    content += "\n---\n\n*此估值由 valuation_engine.py 自动生成，仅供参考。*\n"

    valuation_file.write_text(content, encoding="utf-8")

    return {
        "success": True,
        "company": company,
        "output_file": str(valuation_file),
        "result": result,
    }


def main():
    parser = argparse.ArgumentParser(description="投资估值引擎")
    parser.add_argument("--company", required=True, help="公司名称")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--run", action="store_true", help="运行估值")
    args = parser.parse_args()

    if args.dry_run:
        result = run_valuation(args.company, dry_run=True)
    elif args.run:
        result = run_valuation(args.company)
        if result.get("success"):
            print(f"\n估值分析已生成: {result.get('output_file')}")
        else:
            print(f"\n错误: {result.get('error')}")
    else:
        # 默认预览
        result = run_valuation(args.company, dry_run=True)


from writer_policy import enforce_direct_cli as _enforce_legacy_writer_freeze

_enforce_legacy_writer_freeze(__name__, __file__)


if __name__ == "__main__":
    main()
