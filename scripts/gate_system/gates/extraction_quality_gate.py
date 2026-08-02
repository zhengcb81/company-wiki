#!/usr/bin/env python3
"""
gate_system/gates/extraction_quality_gate.py — Gate 1: 提取质量

检查PDF提取结果的质量：
- 文本长度是否达到文档类型对应的阈值
- quality_score 是否达标
- 扫描PDF检测
"""

import re
from pathlib import Path
from typing import Any, Dict

from gate_system.base import (
    Gate,
    GateResult,
    PipelineContext,
    create_passed_result,
    create_failed_result,
)


class ExtractionQualityGate(Gate):
    """
    Gate 1: 提取质量检查。

    验证 Stage 1 (PDF提取) 的输出质量。
    """

    name = "gate_1_extraction_quality"
    doc_types = [
        "annual_report",
        "semi_annual_report",
        "quarterly_report",
        "investor_relations",
        "prospectus",
    ]
    description = "检查PDF提取的文本长度和质量分是否达标"

    def run(self, context: PipelineContext) -> GateResult:
        # 1. 读取提取文件
        extract_path = context.extract_path
        if not extract_path or not Path(extract_path).exists():
            return create_failed_result(
                issues=["提取文件不存在"],
                diagnosis={
                    "root_cause": "extraction_too_short",
                    "fixable": True,
                    "fix_method": "retry_with_different_strategy",
                    "max_retries": 1,
                },
            )

        content = Path(extract_path).read_text(encoding="utf-8")

        # 2. 解析 frontmatter 提取元数据
        metadata = self._parse_frontmatter(content)
        total_chars = metadata.get("total_chars", 0)
        quality_score = metadata.get("quality_score", 0)
        doc_type = metadata.get("doc_type", context.doc_type)
        pages = metadata.get("pages", 0)

        # 3. 获取阈值配置
        thresholds = self._get_thresholds(doc_type)

        issues = []

        # 4. 检查文本长度
        min_chars = thresholds.get("min_chars", 10000)
        if total_chars < min_chars:
            issues.append(f"文本长度不足: {total_chars} < 阈值 {min_chars}")

        # 5. 检查质量分
        min_quality = thresholds.get("min_quality", 0.20)
        if quality_score < min_quality:
            issues.append(f"质量分过低: {quality_score:.3f} < 阈值 {min_quality}")

        # 6. 扫描PDF检测
        max_scanned_pct = thresholds.get("max_scanned_pages_pct")
        if max_scanned_pct and pages > 0:
            scanned_ratio = self._detect_scanned_ratio(content, pages)
            if scanned_ratio > max_scanned_pct / 100:
                issues.append(
                    f"扫描PDF占比过高: {scanned_ratio:.1%} > 阈值 {max_scanned_pct}%"
                )

        if not issues:
            return create_passed_result(
                score=min(5.0, 3.0 + quality_score * 2),
            )

        # 7. 诊断根因
        root_cause = self._determine_root_cause(
            issues, total_chars, min_chars, quality_score, min_quality
        )
        diagnosis = {
            "root_cause": root_cause,
            "fixable": True,
            "fix_hint": f"文本长度={total_chars}, 质量分={quality_score:.3f}. "
            + "; ".join(issues),
            "metadata": {
                "total_chars": total_chars,
                "quality_score": quality_score,
                "pages": pages,
            },
        }

        if root_cause == "extraction_too_short":
            diagnosis.update(
                {
                    "fix_method": "retry_with_different_strategy",
                    "max_retries": 1,
                }
            )
        elif root_cause == "quality_score_too_low":
            diagnosis.update(
                {
                    "fix_method": "retry_with_higher_quality_settings",
                    "max_retries": 1,
                }
            )
        elif root_cause == "scanned_pdf_detected":
            diagnosis.update(
                {
                    "fix_method": "retry_with_ocr",
                    "max_retries": 1,
                }
            )
        else:
            diagnosis.update(
                {
                    "fix_method": "retry_with_different_strategy",
                    "max_retries": 1,
                }
            )

        return create_failed_result(issues=issues, diagnosis=diagnosis)

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """从Markdown frontmatter提取元数据"""
        metadata = {}
        fm_match = re.match(r"---\n(.*?)\n---\n", content, re.DOTALL)
        if fm_match:
            for line in fm_match.group(1).split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # 尝试转换为数值
                    try:
                        if "." in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass
                    metadata[key] = value
        return metadata

    def _get_thresholds(self, doc_type: str) -> Dict[str, Any]:
        """从配置获取文档类型对应的阈值"""
        config = self.config.get("thresholds", {})
        # 直接按 doc_type 查找
        if doc_type in config:
            return config[doc_type]
        # fallback: 通用配置
        return config.get("default", {"min_chars": 10000, "min_quality": 0.20})

    def _detect_scanned_ratio(self, content: str, pages: int) -> float:
        """
        估算扫描PDF占比。
        简单启发式：文本密度极低（<100 chars/page）视为扫描页。
        """
        body = re.sub(r"---\n.*?\n---\n", "", content, flags=re.DOTALL)
        chars_per_page = len(body) / max(pages, 1)
        # 正常PDF: 500+ chars/page, 扫描PDF: <200 chars/page
        if chars_per_page < 150:
            return 1.0  # 全部扫描
        elif chars_per_page < 300:
            return 0.5  # 部分扫描
        return 0.0

    def _determine_root_cause(
        self, issues, total_chars, min_chars, quality_score, min_quality
    ):
        """根据issue判断根因"""
        for issue in issues:
            if "扫描PDF" in issue:
                return "scanned_pdf_detected"
            if "质量分" in issue:
                return "quality_score_too_low"
            if "长度不足" in issue:
                return "extraction_too_short"
        return "extraction_too_short"
