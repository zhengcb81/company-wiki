#!/usr/bin/env python3
"""
gate_system/gates/financial_analyst_gate.py — Gate 4.5: LLM金融分析师深度审查

核心质量控制关卡：
- 投资逻辑完整性
- 风险覆盖度（7类风险必查清单）
- 同业对标
- 数据质量
- 前瞻展望

按文档类型差异化审查标准：
- financial_report: 营收/盈利/现金流/风险/对标/展望
- investor_relations: 管理层指引/订单/投资者关切/情绪变化
- prospectus: 募资用途/盈利趋势/行业竞争/风险

输入：Stage 3 LLM分析结果 + 原始文本片段
输出：结构化审查报告（approval_status, dimensions, mandatory_checks, revision_requirements）
"""

import json
import re
from pathlib import Path
from typing import Dict, List

from gate_system.base import (
    Gate,
    GateResult,
    PipelineContext,
    create_passed_result,
    create_failed_result,
    create_needs_review_result,
)


class FinancialAnalystGate(Gate):
    """
    Gate 4.5: LLM金融分析师深度审查。

    用LLM审查LLM输出，实现"分析师审分析师"。
    """

    name = "gate_4_5_analyst_review"
    doc_types = [
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "prospectus",
    ]
    description = "LLM金融分析师对整理好的文档内容进行深度审查"

    def run(self, context: PipelineContext) -> GateResult:
        # 1. 读取分析结果
        analysis_path = context.analysis_path
        if not analysis_path or not Path(analysis_path).exists():
            return create_failed_result(
                issues=["分析结果不存在，无法审查"],
                diagnosis={"root_cause": "execution_error", "fixable": False},
            )

        try:
            data = json.loads(Path(analysis_path).read_text(encoding="utf-8"))
            llm_output = data.get("llm_output", "")
            parsed = json.loads(llm_output) if llm_output else data
            metadata = data.get("metadata", {})
        except Exception as e:
            return create_failed_result(
                issues=[f"读取分析结果失败: {e}"],
                diagnosis={"root_cause": "execution_error", "fixable": False},
            )

        # 2. 检查是否启用
        if not self.config.get("enabled", True):
            return create_passed_result(score=5.0, issues=["Gate 4.5 已禁用"])

        # 3. 获取审查配置
        mandatory_dims = self.config.get("mandatory_dimensions", [])
        approval_threshold = self.config.get("approval_threshold", 4.0)

        # 4. 构建审查prompt
        self._build_review_prompt(parsed, metadata, context, mandatory_dims)

        # 5. 调用LLM审查（简化版本：先使用规则检查作为fallback）
        # 注：实际运行时通过 llm_client 调用，这里先做规则预检查
        review_result = self._rule_based_review(
            parsed, metadata, context, mandatory_dims
        )

        # 6. 判断是否通过
        total_score = review_result.get("total_score", 0)

        if total_score >= approval_threshold:
            return create_passed_result(
                score=total_score,
                issues=[],
            )
        else:
            return create_needs_review_result(
                score=total_score,
                issues=review_result.get("revision_requirements", []),
                diagnosis={
                    "root_cause": "analyst_review_failed",
                    "fixable": True,
                    "fix_method": "re_analyze_with_reviewer_feedback",
                    "max_retries": self.config.get("max_llm_retries", 2),
                    "fix_hint": self._build_fix_hint(review_result),
                    "review_details": review_result,
                },
            )

    def _build_review_prompt(
        self,
        parsed: Dict,
        metadata: Dict,
        context: PipelineContext,
        mandatory_dims: List,
    ) -> str:
        """
        构建LLM审查prompt（按文档类型差异化）。
        """
        company = metadata.get("company", context.company)
        doc_type = metadata.get("doc_type", context.doc_type)
        period = metadata.get("period", context.period)

        # 文档类型描述
        type_desc = {
            "annual_report": "年度报告",
            "semi_annual_report": "半年度报告",
            "quarterly_report": "季度报告",
            "investor_relations": "投资者关系活动记录",
            "prospectus": "招股说明书",
        }.get(doc_type, doc_type)

        # 基础prompt框架
        prompt = f"""你是一名资深投资研究总监，正在审查下属分析师整理的{type_desc}分析文档。

## 审查对象
公司: {company}
报告期: {period}
文档类型: {type_desc}

## 下属分析师的输出
```json
{json.dumps(parsed, ensure_ascii=False, indent=2)[:8000]}
```

## 审查标准

请从以下维度进行审查，每项1-5分：

### 1. 投资逻辑完整性（权重30%）
- 数据 → 分析 → 结论 链条是否完整？
- 营收变动原因是否解释（价格/销量/产品结构）？
- 利润与扣非利润差异是否分析？

### 2. 风险覆盖度（权重25%）★必查项
"""

        # 按文档类型添加差异化风险清单
        if doc_type in ["annual_report", "semi_annual_report", "quarterly_report"]:
            prompt += self._build_financial_risk_checklist()
        elif doc_type == "investor_relations":
            prompt += self._build_ir_risk_checklist()
        elif doc_type == "prospectus":
            prompt += self._build_prospectus_risk_checklist()

        prompt += """
### 3. 同业对标（权重20%）
- 是否提及至少2家主要竞争对手？
- 是否进行关键指标对比（毛利率、增速、市场份额）？

### 4. 数据质量（权重15%）
- 数字是否与原始文档一致？
- 同比/环比计算是否正确？
- 单位是否统一？

### 5. 前瞻展望（权重10%）
- 未来催化剂是否明确？
- 跟踪问题是否有价值？

## 输出要求（严格JSON）
{
  "approval_status": "approved | needs_revision | rejected",
  "total_score": 4.5,
  "dimensions": {
    "investment_logic": {"score": 5, "issues": [], "suggestions": []},
    "risk_coverage": {"score": 3, "issues": [], "suggestions": []},
    "peer_comparison": {"score": 4, "issues": [], "suggestions": []},
    "data_quality": {"score": 5, "issues": [], "suggestions": []},
    "forward_outlook": {"score": 4, "issues": [], "suggestions": []}
  },
  "mandatory_checks": {
    "revenue_analysis": {"passed": true},
    "risk_factors": {"passed": false, "missing": ["customer_concentration"]}
  },
  "revision_requirements": ["具体修改意见1", "具体修改意见2"],
  "action": "revise_content"
}
"""

        return prompt

    def _build_financial_risk_checklist(self) -> str:
        """财务报告风险清单"""
        return """
必须逐项检查以下风险，未识别则扣分：
- [ ] 客户集中度风险（前5大客户占比 > 20%）
- [ ] 供应商集中度风险（前5大供应商占比 > 50%）
- [ ] 季节性/周期性风险（季度间经营现金流波动 > 30%）
- [ ] 补贴依赖风险（政府补助/净利润 > 30%）
- [ ] 原材料价格敏感风险（铜价等大宗商品波动）
- [ ] 资本支出压力风险（投资现金流净流出/经营现金流 > 1）
- [ ] 应收账款风险（应收账款增速 > 营收增速）
"""

    def _build_ir_risk_checklist(self) -> str:
        """投资者关系风险清单"""
        return """
必须检查：
- [ ] 管理层是否给出具体数字目标（营收/利润/订单）
- [ ] 订单pipeline是否可量化
- [ ] 投资者关切问题是否被充分回应
- [ ] 与历史IR记录对比，管理层态度/指引是否有显著变化
"""

    def _build_prospectus_risk_checklist(self) -> str:
        """招股说明书风险清单"""
        return """
必须检查：
- [ ] 募集资金用途是否具体、可验证
- [ ] 报告期盈利能力趋势分析是否客观（避免过度乐观）
- [ ] 行业竞争格局分析是否包含具体竞争对手
- [ ] 招股说明书风险章节是否被充分引用到分析中
"""

    def _rule_based_review(
        self,
        parsed: Dict,
        metadata: Dict,
        context: PipelineContext,
        mandatory_dims: List,
    ) -> Dict:
        """
        基于规则的预审查（作为LLM审查的fallback和补充）。
        实际生产环境应调用LLM进行深度审查。
        """
        dimensions = {
            "investment_logic": {"score": 0, "issues": [], "suggestions": []},
            "risk_coverage": {"score": 0, "issues": [], "suggestions": []},
            "peer_comparison": {"score": 0, "issues": [], "suggestions": []},
            "data_quality": {"score": 0, "issues": [], "suggestions": []},
            "forward_outlook": {"score": 0, "issues": [], "suggestions": []},
        }
        mandatory_checks = {}
        revision_requirements = []

        highlights = parsed.get("financial_highlights", {})
        entries = parsed.get("timeline_entries", [])
        all_text = " ".join(str(p) for e in entries for p in e.get("key_points", []))
        assessment = parsed.get("assessment_update", "")
        key_insights = parsed.get("key_insights", [])
        all_content = all_text + " " + assessment + " " + " ".join(key_insights)

        # 1. 投资逻辑检查
        il_score = 5
        il_issues = []

        # 营收分析完整性
        revenue_text = str(highlights.get("revenue", ""))
        if revenue_text and (
            "原因" in all_content or "由于" in all_content or "主要" in all_content
        ):
            pass
        elif revenue_text:
            il_issues.append("营收变动缺少原因分析")
            il_score -= 1

        # 利润质量分析
        profit_text = str(highlights.get("net_profit", ""))
        if (
            "扣非" in all_content
            or "非经常性" in all_content
            or "政府补助" in all_content
        ):
            pass
        elif profit_text:
            il_issues.append("未分析扣非净利润vs归母净利润差异")
            il_score -= 1

        # 现金流分析
        cashflow_text = str(highlights.get("operating_cashflow", ""))
        if cashflow_text and ("现金流" in all_content or "经营" in all_content):
            pass
        elif cashflow_text:
            il_issues.append("缺少现金流分析")
            il_score -= 1

        dimensions["investment_logic"] = {
            "score": max(1, il_score),
            "issues": il_issues,
            "suggestions": [],
        }
        mandatory_checks["revenue_analysis"] = {"passed": il_score >= 4}

        # 2. 风险覆盖度检查
        risk_score = 5
        risk_issues = []
        risk_missing = []

        # 定义风险检测规则
        risk_rules = {
            "customer_concentration": {
                "keywords": ["客户集中", "前五大客户", "大客户", "集中度"],
                "threshold_desc": "前5大客户占比 > 20%",
            },
            "supplier_concentration": {
                "keywords": ["供应商集中", "前五大供应商", "依赖"],
                "threshold_desc": "前5大供应商占比 > 50%",
            },
            "seasonal_risk": {
                "keywords": ["季度", "季节性", "Q4", "回款", "账期"],
                "threshold_desc": "季度间波动 > 30%",
            },
            "subsidy_dependency": {
                "keywords": ["补贴", "政府补助", "非经常性", "税收优惠"],
                "threshold_desc": "补助/净利润 > 30%",
            },
            "raw_material_exposure": {
                "keywords": ["原材料", "铜价", "价格波动", "成本上升"],
                "threshold_desc": "原材料价格敏感",
            },
            "capex_pressure": {
                "keywords": ["资本支出", "投资活动", "在建工程", "扩产"],
                "threshold_desc": "资本支出压力",
            },
            "ar_turnover_risk": {
                "keywords": ["应收账款", "回款", "账期", "信用政策"],
                "threshold_desc": "应收增速 > 营收增速",
            },
        }

        for risk_name, rule in risk_rules.items():
            found = any(kw in all_content for kw in rule["keywords"])
            if not found:
                risk_missing.append(risk_name)
                risk_score -= 0.5

        if risk_missing:
            risk_issues.append(f"未识别风险: {', '.join(risk_missing[:3])}")
            if len(risk_missing) > 3:
                risk_issues.append(f"等共{len(risk_missing)}类风险")

        dimensions["risk_coverage"] = {
            "score": max(1, int(risk_score)),
            "issues": risk_issues,
            "suggestions": [
                f"请补充{risk_rules[r]['threshold_desc']}分析" for r in risk_missing[:3]
            ],
        }
        mandatory_checks["risk_factors"] = {
            "passed": len(risk_missing) == 0,
            "missing": risk_missing,
        }

        # 3. 同业对标检查
        peer_score = 5
        peer_issues = []

        # 通用关键词（不硬编码公司名）
        competitor_keywords = [
            "竞争对手",
            "竞争格局",
            "同业",
            "同行",
            "对标",
            "市场份额",
            "市占率",
            "行业龙头",
            "主要厂商",
            "可比公司",
            "可比上市公司",
            "对比分析",
        ]
        has_peer = any(kw in all_content for kw in competitor_keywords)

        if not has_peer and context.doc_type in [
            "annual_report",
            "semi_annual_report",
            "quarterly_report",
        ]:
            peer_issues.append("未提及竞争对手或同业对比")
            peer_score = 2
        elif not has_peer:
            peer_score = 3

        dimensions["peer_comparison"] = {
            "score": peer_score,
            "issues": peer_issues,
            "suggestions": [],
        }

        # 4. 数据质量检查
        dq_score = 5
        dq_issues = []

        # 检查是否有数字支撑
        has_numbers = bool(re.search(r"\d+", all_content))
        if not has_numbers:
            dq_issues.append("分析缺少具体数字支撑")
            dq_score = 2

        # 检查财务亮点是否有数字
        for key, value in highlights.items():
            if value and not re.search(r"\d+", str(value)):
                dq_issues.append(f"{key} 缺少具体数字")
                dq_score -= 0.5

        dimensions["data_quality"] = {
            "score": max(1, int(dq_score)),
            "issues": dq_issues,
            "suggestions": [],
        }

        # 5. 前瞻展望检查
        fo_score = 5
        fo_issues = []

        future_keywords = ["未来", "预计", "展望", "催化剂", "跟踪", "关注"]
        has_future = any(kw in all_content for kw in future_keywords)

        if not has_future:
            fo_issues.append("缺少前瞻性展望和跟踪问题")
            fo_score = 2
        elif "催化剂" not in all_content and "跟踪" not in all_content:
            fo_issues.append("有展望但缺少具体催化剂或跟踪问题")
            fo_score = 3

        dimensions["forward_outlook"] = {
            "score": fo_score,
            "issues": fo_issues,
            "suggestions": [],
        }

        # 计算总分（加权）
        weights = {
            "investment_logic": 0.30,
            "risk_coverage": 0.25,
            "peer_comparison": 0.20,
            "data_quality": 0.15,
            "forward_outlook": 0.10,
        }

        total = sum(dimensions[d]["score"] * weights[d] for d in dimensions)

        # 生成修改意见
        for dim_name, dim_data in dimensions.items():
            if dim_data["score"] < 4:
                for issue in dim_data["issues"][:2]:
                    revision_requirements.append(f"[{dim_name}] {issue}")
                for suggestion in dim_data.get("suggestions", [])[:1]:
                    revision_requirements.append(f"[{dim_name}] {suggestion}")

        # 风险因子特别处理
        if risk_missing:
            for r in risk_missing[:3]:
                rule = risk_rules[r]
                revision_requirements.append(
                    f"[风险覆盖] 请补充{rule['threshold_desc']}的风险分析"
                )

        return {
            "approval_status": "approved"
            if total >= self.config.get("approval_threshold", 4.0)
            else "needs_revision",
            "total_score": round(total, 2),
            "dimensions": dimensions,
            "mandatory_checks": mandatory_checks,
            "revision_requirements": revision_requirements[:8],  # 最多8条
            "action": "revise_content"
            if total < self.config.get("approval_threshold", 4.0)
            else "approve",
        }

    def _build_fix_hint(self, review_result: Dict) -> str:
        """根据审查结果构建修复提示"""
        requirements = review_result.get("revision_requirements", [])
        if not requirements:
            return ""

        hint = "审查未通过，请按以下意见修改：\n"
        for i, req in enumerate(requirements[:5], 1):
            hint += f"{i}. {req}\n"

        return hint

    def get_review_prompt_template(self, doc_type: str) -> str:
        """获取指定文档类型的审查prompt模板"""
        # 可以扩展为从外部文件加载
        templates = {
            "annual_report": self._build_financial_risk_checklist(),
            "investor_relations": self._build_ir_risk_checklist(),
            "prospectus": self._build_prospectus_risk_checklist(),
        }
        return templates.get(doc_type, templates.get("annual_report", ""))
