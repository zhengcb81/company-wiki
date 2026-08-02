"""Frozen legacy research compiler retained only for compatibility tests."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .domain import (
    SourceRecord, Claim, ClaimType, KnowledgePatch,
)
from .source_registry import SourceRegistry
from .run_store import RunStore


# ── 内容规范化 ──────────────────────────────

class ContentNormalizer:
    """将不同来源格式统一为标准化文本"""

    def normalize(self, source: SourceRecord) -> str:
        """
        读取并规范化来源内容。

        Returns:
            标准化文本内容
        """
        path = Path(source.path)
        if not path.exists():
            return ""

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = path.read_text(encoding="gbk")
            except Exception:
                return ""

        # 移除 YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        return content

    def extract_metadata(self, source: SourceRecord) -> dict:
        """从文件中提取元数据"""
        path = Path(source.path)
        if not path.exists():
            return {}

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return {}

        # 提取 YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    return yaml.safe_load(parts[1]) or {}
                except Exception:
                    pass

        return {}


# ── LLM 分析器 ──────────────────────────────

class ContentAnalyzer:
    """使用 LLM 分析内容，产出结构化声明"""

    # 分析 prompt
    ANALYSIS_PROMPT = """分析以下文档内容，提取关键信息。

文档来源：{source_kind}
关联公司/实体：{entity_hints}

要求：
1. 提取关键事实声明（Claim），每个声明包含：
   - text: 声明文本
   - claim_type: fact/opinion/prediction/assessment
   - metric: 涉及的指标名（如有）
   - value: 指标值（如有）
   - unit: 单位（如有）
2. 识别关联实体和问题
3. 区分事实、观点和预测
4. 注意识别数值和时间段

以 JSON 格式输出：
{{
  "claims": [
    {{
      "text": "声明文本",
      "claim_type": "fact",
      "metric": "营收",
      "value": "185.6",
      "unit": "亿元",
      "entity_hint": "北方华创",
      "confidence": 0.9
    }}
  ],
  "entity_mentions": ["北方华创", "半导体设备"],
  "question_relevance": ["Q001", "Q004"]
}}

文档内容：
{content}"""

    def __init__(self, llm_client=None):
        self._llm = llm_client

    def analyze(self, content: str, source: SourceRecord) -> dict:
        """
        分析内容，返回结构化结果。

        Returns:
            {"claims": [...], "entity_mentions": [...], "question_relevance": [...]}
        """
        if not self._llm:
            return self._fallback_extract(content, source)

        prompt = self.ANALYSIS_PROMPT.format(
            source_kind=source.source_kind.value,
            entity_hints=", ".join(source.entity_hints) or "未知",
            content=content[:8000],  # 限制长度
        )

        try:
            response = self._llm.generate(prompt)
            return self._parse_response(response)
        except Exception:
            return self._fallback_extract(content, source)

    def _parse_response(self, response: str) -> dict:
        """解析 LLM 响应"""
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return {
                    "claims": data.get("claims", []),
                    "entity_mentions": data.get("entity_mentions", []),
                    "question_relevance": data.get("question_relevance", []),
                }
            except json.JSONDecodeError:
                pass

        return {"claims": [], "entity_mentions": [], "question_relevance": []}

    def _fallback_extract(self, content: str, source: SourceRecord) -> dict:
        """无 LLM 时的降级提取"""
        claims = []
        entities = set(source.entity_hints)

        # 简单数值提取
        for match in re.finditer(r'(\d+\.?\d*)\s*(亿元|万元|%|倍)', content):
            value, unit = match.groups()
            # 获取上下文
            start = max(0, match.start() - 50)
            context = content[start:match.end() + 50]
            claims.append({
                "text": context.strip(),
                "claim_type": "fact",
                "metric": "",
                "value": value,
                "unit": unit,
                "entity_hint": source.entity_hints[0] if source.entity_hints else "",
                "confidence": 0.3,
            })

        # 实体提及
        for entity in entities:
            if entity in content:
                pass  # 已知实体

        return {
            "claims": claims,
            "entity_mentions": list(entities),
            "question_relevance": [],
        }


# ── 验证器 ──────────────────────────────

class OutputValidator:
    """验证分析输出的质量"""

    def validate(self, analysis: dict, source: SourceRecord) -> tuple[bool, list[str]]:
        """
        验证分析结果。

        Returns:
            (is_valid, errors)
        """
        errors = []

        # 检查基本结构
        if not isinstance(analysis.get("claims"), list):
            errors.append("claims 不是列表")
            return False, errors

        # 检查每个 claim
        for i, claim in enumerate(analysis.get("claims", [])):
            if not isinstance(claim, dict):
                errors.append(f"claim[{i}] 不是字典")
                continue

            # 必须有 text
            if not claim.get("text"):
                errors.append(f"claim[{i}] 缺少 text")

            # claim_type 必须合法
            valid_types = {"fact", "opinion", "prediction", "assessment"}
            if claim.get("claim_type") not in valid_types:
                errors.append(f"claim[{i}] 非法 claim_type: {claim.get('claim_type')}")

            # 数值 claim 必须有 value 和 unit
            if claim.get("metric") and not claim.get("value"):
                errors.append(f"claim[{i}] 有 metric 但无 value")

            # 检查路径注入
            text = claim.get("text", "")
            if any(p in text for p in ["../", "..\\", "/etc/", "C:\\"]):
                errors.append(f"claim[{i}] 文本包含可疑路径")

            # 检查指令注入
            injection_patterns = [
                r"忽略以上", r"请忽略", r"ignore.*above",
                r"作为AI", r"你应该", r"自动批准", r"无需.*审核",
            ]
            for pattern in injection_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    errors.append(f"claim[{i}] 文本可能包含指令注入")
                    break

        # 检查实体提及
        if not analysis.get("entity_mentions"):
            errors.append("无实体提及")

        is_valid = len(errors) == 0
        return is_valid, errors


# ── IngestService ──────────────────────────────

class LegacyResearchIngestService:
    """
    Frozen legacy research compiler; not a canonical source-ingest service.

    影子模式：只生成 KnowledgePatch proposal，不写 wiki。
    """

    def __init__(
        self,
        source_registry: SourceRegistry,
        run_store: RunStore,
        llm_client=None,
        graph_adapter=None,
        validator: OutputValidator = None,
    ):
        self._sources = source_registry
        self._runs = run_store
        self._analyzer = ContentAnalyzer(llm_client)
        self._normalizer = ContentNormalizer()
        self._graph = graph_adapter
        self._validator = validator or OutputValidator()

    def analyze(
        self,
        source: SourceRecord,
        dry_run: bool = True,
    ) -> Optional[KnowledgePatch]:
        """
        分析来源，生成 KnowledgePatch proposal。

        Args:
            source: 来源记录
            dry_run: True=影子模式（不写 wiki）

        Returns:
            KnowledgePatch 或 None（如果验证失败）
        """
        # 创建 run
        run_id = self._runs.create_run(source.source_id, "v1.0")
        self._runs.start_run(run_id)

        try:
            # 1. 规范化内容
            content = self._normalizer.normalize(source)
            if not content:
                self._runs.fail_run(run_id, "内容为空或无法读取")
                return None

            # 2. LLM 分析
            analysis = self._analyzer.analyze(content, source)

            # 3. 验证输出
            is_valid, errors = self._validator.validate(analysis, source)
            if not is_valid:
                self._runs.fail_run(run_id, f"验证失败: {'; '.join(errors[:3])}")
                return None

            # 4. 生成 Claims
            claims = []
            for claim_data in analysis.get("claims", []):
                claim = Claim(
                    claim_id=f"{source.source_id[:8]}:{len(claims)}",
                    claim_type=ClaimType(claim_data.get("claim_type", "fact")),
                    text=claim_data.get("text", ""),
                    entity_id=claim_data.get("entity_hint", ""),
                    metric=claim_data.get("metric", ""),
                    value=str(claim_data.get("value", "")),
                    unit=claim_data.get("unit", ""),
                    confidence=claim_data.get("confidence", 0.5),
                    published_at=source.published_at,
                    observed_at=datetime.now(),
                    source_kind=source.source_kind,
                )
                claims.append(claim)

            # 5. 解析目标
            targets = self._resolve_targets(source, analysis)

            # 6. 创建 patch
            patch = KnowledgePatch(
                patch_id=f"patch-{run_id}",
                source_id=source.source_id,
                claims=claims,
                targets=targets,
                routing_reason=f"来源类型: {source.source_kind.value}",
                risk_level=self._assess_risk(claims, targets),
                validation_result="passed" if is_valid else "failed",
                model_version="v1.0",
            )

            # 7. 完成 run
            output_hash = hashlib.sha256(
                json.dumps([c.text for c in claims]).encode()
            ).hexdigest()[:16]
            self._runs.complete_run(run_id, output_hash)

            return patch

        except Exception as e:
            self._runs.fail_run(run_id, str(e))
            return None

    def _resolve_targets(self, source: SourceRecord, analysis: dict) -> list[str]:
        """解析目标实体"""
        targets = set()

        # 从来源的 entity_hints
        targets.update(source.entity_hints)

        # 从分析结果的 entity_mentions
        for entity in analysis.get("entity_mentions", []):
            targets.add(entity)

        # 如果有 graph_adapter，用关系匹配扩展
        if self._graph and source.entity_hints:
            for hint in source.entity_hints[:2]:  # 只取前两个
                related = self._graph.resolve_targets(hint, max_targets=3)
                for r in related:
                    if r.relevance_score >= 0.7:
                        targets.add(r.entity_name)

        return list(targets)

    def _assess_risk(self, claims: list[Claim], targets: list[str]) -> str:
        """评估风险等级"""
        # 高风险：目标多于 5 个
        if len(targets) > 5:
            return "high"

        # 中风险：有预测类声明
        if any(c.claim_type == ClaimType.PREDICTION for c in claims):
            return "medium"

        # 低风险：只有事实
        return "low"
