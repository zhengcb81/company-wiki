#!/usr/bin/env python3
"""
gate_system/config_loader.py — 配置加载器

从 pipeline_rules.yaml 加载 Gate 规则配置。
与现有 config.py 集成，不冲突。
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def get_default_rules_path() -> Path:
    """获取默认规则文件路径"""
    # 尝试从项目根目录查找
    candidates = [
        Path.home() / "company-wiki" / "config" / "pipeline_rules.yaml",
        Path.home() / "company-wiki" / "pipeline_rules.yaml",
        Path(__file__).parent.parent.parent / "config" / "pipeline_rules.yaml",
        Path(__file__).parent.parent.parent / "pipeline_rules.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]  # 返回默认路径（即使不存在）


def load_pipeline_rules(path: Optional[Path] = None) -> Dict[str, Any]:
    """
    加载 Pipeline 规则配置。

    Args:
        path: 规则文件路径，None 时使用默认路径

    Returns:
        规则配置字典

    Raises:
        FileNotFoundError: 文件不存在
        yaml.YAMLError: YAML 解析错误
    """
    if path is None:
        path = get_default_rules_path()

    if not path.exists():
        raise FileNotFoundError(
            f"Pipeline 规则文件不存在: {path}\n请创建 {path} 或指定其他路径。"
        )

    with open(path, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f)

    if rules is None:
        rules = {}

    return rules


def validate_rules(rules: Dict[str, Any]) -> list:
    """
    验证规则配置的完整性。

    Returns:
        错误信息列表，空列表表示验证通过
    """
    errors = []

    if not rules:
        errors.append("规则配置为空")
        return errors

    pipeline_gates = rules.get("pipeline_gates", {})
    if not pipeline_gates:
        errors.append("缺少 pipeline_gates 根节点")

    # 检查每个文档类型配置
    for doc_type, config in pipeline_gates.items():
        if not isinstance(config, dict):
            errors.append(f"{doc_type}: 配置必须是字典")
            continue

        # 检查每个 gate 配置
        for gate_name, gate_config in config.items():
            if not isinstance(gate_config, dict):
                errors.append(f"{doc_type}.{gate_name}: 配置必须是字典")

    return errors


def save_default_rules(path: Optional[Path] = None):
    """
    生成默认规则文件（如果不存在）。
    用于首次初始化。
    """
    if path is None:
        path = get_default_rules_path()

    if path.exists():
        return False  # 已存在，不覆盖

    default_rules = {
        "pipeline_gates": {
            "financial_report": {
                "gate_1_extraction": {
                    "thresholds": {
                        "annual_report": {
                            "min_chars": 50000,
                            "min_quality": 0.30,
                            "max_scanned_pages_pct": 20,
                        },
                        "semi_annual_report": {
                            "min_chars": 25000,
                            "min_quality": 0.30,
                        },
                        "quarterly_report": {
                            "min_chars": 10000,
                            "min_quality": 0.20,
                        },
                    },
                    "failure_action": "diagnose_then_retry_or_human",
                },
                "gate_2_data_contract": {
                    "required_fields": ["revenue", "net_profit", "gross_margin"],
                    "numeric_ranges": {
                        "gross_margin": {"min": 0, "max": 100},
                        "revenue": {"min": 0},
                    },
                    "cross_validations": [
                        {
                            "formula": "revenue >= net_profit",
                            "description": "营收应大于等于净利润",
                        }
                    ],
                    "failure_action": "diagnose_then_retry_or_human",
                },
                "gate_3_llm_output": {
                    "hallucination": {
                        "unit_conversions": ["元", "万元", "亿元"],
                        "tolerance": 0.02,
                    },
                    "logic_check": {
                        "explanation_keywords": {
                            "margin": [
                                "产品结构",
                                "原材料",
                                "价格",
                                "成本",
                                "附加值",
                                "高利润",
                                "业务结构",
                            ]
                        }
                    },
                    "json_repair": {"enabled": True, "max_attempts": 3},
                    "failure_action": "diagnose_then_retry_or_human",
                },
                "gate_4_5_analyst_review": {
                    "enabled": True,
                    "approval_threshold": 4.0,
                    "max_llm_retries": 2,
                    "mandatory_dimensions": [
                        "revenue_analysis",
                        "profit_quality",
                        "cashflow_analysis",
                        {
                            "risk_factors": [
                                {"name": "customer_concentration", "threshold_pct": 20},
                                {"name": "supplier_concentration", "threshold_pct": 50},
                                {"name": "seasonal_risk", "q4_variance_threshold": 30},
                                {
                                    "name": "subsidy_dependency",
                                    "subsidy_to_netprofit_threshold": 30,
                                },
                                {"name": "raw_material_exposure"},
                                {"name": "capex_pressure"},
                                {"name": "ar_turnover_risk"},
                            ]
                        },
                        "forward_outlook",
                        "peer_comparison",
                    ],
                    "failure_action": "diagnose_then_retry_or_human",
                },
            },
            "investor_relations": {
                "gate_1_extraction": {
                    "thresholds": {"min_chars": 2000, "min_quality": 0.15}
                },
                "gate_2_data_contract": {
                    "required_fields": [],
                    "extract_indicators": [
                        "order_amount",
                        "capacity_utilization",
                        "customer_names",
                    ],
                },
                "gate_4_5_analyst_review": {
                    "enabled": True,
                    "approval_threshold": 4.0,
                    "mandatory_dimensions": [
                        "management_guidance",
                        "order_pipeline",
                        "investor_concerns",
                        "sentiment_shift_vs_history",
                    ],
                },
            },
            "prospectus": {
                "gate_1_extraction": {
                    "thresholds": {"min_chars": 80000, "min_quality": 0.30}
                },
                "gate_2_data_contract": {
                    "required_fields": [
                        "revenue",
                        "net_profit",
                        "total_assets",
                        "equity",
                    ],
                    "tag_predictions": True,
                },
                "gate_4_5_analyst_review": {
                    "enabled": True,
                    "approval_threshold": 4.0,
                    "mandatory_dimensions": [
                        "fundraising_use",
                        "profitability_trend",
                        "industry_competition",
                        "risk_factors_prospectus",
                    ],
                },
            },
        }
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            default_rules,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )

    return True


if __name__ == "__main__":
    # 测试加载
    try:
        rules = load_pipeline_rules()
        errors = validate_rules(rules)
        if errors:
            print(f"规则验证失败 ({len(errors)} 个错误):")
            for e in errors:
                print(f"  - {e}")
        else:
            print("规则验证通过")
            doc_types = list(rules.get("pipeline_gates", {}).keys())
            print(f"已配置文档类型: {doc_types}")
    except FileNotFoundError:
        print("规则文件不存在，生成默认配置...")
        saved = save_default_rules()
        if saved:
            print("默认规则已生成")
        else:
            print("规则文件已存在")
