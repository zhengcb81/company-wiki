#!/usr/bin/env python3
"""
prompts.py — LLM Prompt 模板库

为不同类型的文档提供专门的分析 prompt。
所有 prompt 都返回一个字符串，可直接传给 llm_client.chat()。

核心设计原则：
- 把分析师的工作流编码进 prompt：读材料 → 对照问题清单 → 提取关键信息 → 判断重要性 → 发现矛盾 → 提出新问题
- LLM 输出结构化 JSON，代码只负责解析和写入 wiki
"""

from typing import Dict, List, Optional


# ── 通用分析 Prompt ──────────────────────────


def build_analysis_prompt(
    content: str,
    entity_name: str,
    source_type: str,
    published_date: str,
    core_questions: List[str],
    existing_assessment: str = "",
    related_entities: List[str] = None,
    max_content_chars: int = 25000,
) -> str:
    """
    通用分析 prompt — 适用于所有来源类型。

    Args:
        content: 文档正文（已清洗）
        entity_name: 所属实体名称（如"中微公司"）
        source_type: 来源类型（annual_report/quarterly_report/investor_relations/news/announcement）
        published_date: 发布日期 YYYY-MM-DD
        core_questions: 该实体的核心追踪问题列表
        existing_assessment: 现有 wiki 页面的综合评估（可选）
        related_entities: 相关实体列表（可选）
        max_content_chars: 内容截断长度
    """
    content = content[:max_content_chars]

    questions_text = (
        "\n".join(f"{i + 1}. {q}" for i, q in enumerate(core_questions))
        if core_questions
        else "（暂无核心问题）"
    )

    related_text = ""
    if related_entities:
        related_text = f"\n## 相关实体\n{', '.join(related_entities)}\n"

    assessment_text = ""
    if existing_assessment:
        assessment_text = f"\n## 现有知识概况\n{existing_assessment[:1000]}\n"

    source_type_desc = {
        "annual_report": "年度报告",
        "semi_annual_report": "半年度报告",
        "quarterly_report": "季度报告",
        "prospectus": "招股说明书",
        "investor_relations": "投资者关系活动记录",
        "research_report": "券商研报",
        "news": "新闻报道",
        "announcement": "公司公告",
        "unknown": "未知来源",
    }.get(source_type, source_type)

    prompt = f"""你是一名资深的上市公司研究分析师。请分析以下{source_type_desc}内容，提取对投资决策有价值的信息。

## 分析对象
实体: {entity_name}
来源类型: {source_type_desc}
日期: {published_date}

## 该实体的核心追踪问题
{questions_text}{related_text}{assessment_text}
## 待分析内容
{content}

## 分析要求
1. 提取所有与"核心追踪问题"相关的信息，判断每条信息回答了哪些问题（完全回答/部分回答/无关）
2. 提取所有具体的数字、日期、百分比、金额（营收、利润、增长率、市场份额等）
3. 识别管理层/分析师的观点和判断（不要只罗列事实，要指出"这意味着什么"）
4. 识别风险因素和负面信息（不要只报喜不报忧）
5. 如果内容中有与"现有知识概况"矛盾的地方，明确指出
6. 评估每条信息对投资决策的重要性（0-1）

## 输出格式（严格 JSON）
```json
{{
  "timeline_entries": [
    {{
      "date": "YYYY-MM-DD",
      "title": "条目标题，简洁概括事件",
      "key_points": ["要点1（含具体数字）", "要点2", "要点3"],
      "answered_questions": ["回答的核心问题编号或内容"],
      "importance": 0.0,
      "sentiment": "positive/negative/neutral",
      "source_type": "{source_type_desc}"
    }}
  ],
  "assessment_update": "是否需要更新综合评估？如果需要，给出新评估文本（100-300字）",
  "contradictions": [
    {{
      "new_claim": "新信息中的陈述",
      "existing_claim": "现有知识中的陈述",
      "explanation": "矛盾说明"
    }}
  ],
  "new_questions": ["这份内容暴露出的新问题"],
  "key_insights": ["对投资决策最关键的3-5条洞察"]
}}
```

注意：
- 只输出 JSON，不要其他内容
- 如果没有某类信息，对应字段返回空数组或空字符串
- importance 范围 0.0-1.0，0.7以上表示高重要性
- sentiment 基于信息对公司的影响判断，不是情感色彩
"""
    return prompt


# ── 财报专用 Prompt ──────────────────────────


def build_financial_report_prompt(
    content: str,
    entity_name: str,
    report_type: str,  # annual / semi_annual / quarterly
    period: str,  # 如 "2024年报" / "2025Q1"
    core_questions: List[str],
    previous_period_data: Optional[Dict] = None,
    max_content_chars: int = 25000,
) -> str:
    """
    财报专用分析 prompt。
    强调财务数据提取、季度对比、管理层讨论。
    """
    content = content[:max_content_chars]

    questions_text = (
        "\n".join(f"{i + 1}. {q}" for i, q in enumerate(core_questions))
        if core_questions
        else "（暂无核心问题）"
    )

    prev_text = ""
    if previous_period_data:
        prev_text = f"""\n## 上一期（{previous_period_data.get("period", "上期")}）关键数据
{previous_period_data.get("summary", "无")}\n"""

    prompt = f"""你是一名资深财务分析师。请深度分析以下{entity_name}的{period}{report_type}内容。

## 分析对象
实体: {entity_name}
报告类型: {report_type}
报告期: {period}

## 核心追踪问题
{questions_text}{prev_text}
## 待分析内容
{content}

## 分析要求
1. **财务数据提取**（必须包含具体数字）：
   - 营收、净利润、扣非净利润及同比增长率
   - 毛利率、净利率变化及原因
   - 分业务/分产品收入及增长
   - 研发投入金额及占营收比例
   - 经营活动现金流
   - 应收账款、存货变化

2. **管理层讨论分析**：
   - 管理层对业绩变化的解释
   - 对行业趋势的判断
   - 对竞争格局的看法

3. **风险因素**：
   - 新增或变化的风险
   - 应收账款增速是否超过营收增速
   - 存货变化是否异常

4. **未来展望**：
   - 下季度/年度指引
   - 资本开支计划
   - 研发重点方向

5. **季度对比**（如有上期数据）：
   - 环比变化趋势
   - 关键指标的加速/减速

## 输出格式（严格 JSON）
```json
{{
  "timeline_entries": [
    {{
      "date": "YYYY-MM-DD",
      "title": "条目标题",
      "key_points": ["要点1", "要点2", "要点3"],
      "answered_questions": [""],
      "importance": 0.0,
      "sentiment": "positive/negative/neutral",
      "source_type": "财报"
    }}
  ],
  "financial_highlights": {{
    "revenue": "营收及增速",
    "net_profit": "净利润及增速",
    "gross_margin": "毛利率",
    "rd_expense": "研发投入",
    "operating_cashflow": "经营现金流"
  }},
  "assessment_update": "",
  "contradictions": [],
  "new_questions": [],
  "key_insights": []
}}
```

注意：
- 只输出 JSON
- 所有数字必须准确，不要编造
- 如果某项数据在原文中未提及，标记为"未披露"
"""
    return prompt


# ── 投资者关系专用 Prompt ──────────────────────────


def build_ir_prompt(
    content: str,
    entity_name: str,
    event_date: str,
    core_questions: List[str],
    max_content_chars: int = 25000,
) -> str:
    """
    投资者关系活动记录表专用 prompt。
    强调逐对提取 QA，每对 QA 独立评估。
    """
    content = content[:max_content_chars]

    questions_text = (
        "\n".join(f"{i + 1}. {q}" for i, q in enumerate(core_questions))
        if core_questions
        else "（暂无核心问题）"
    )

    prompt = f"""你是一名资深行业研究员。以下内容是{entity_name}的投资者关系活动记录，包含机构投资者与管理层的问答对话。

## 分析对象
实体: {entity_name}
活动日期: {event_date}

## 核心追踪问题
{questions_text}

## 待分析内容
{content}

## 分析要求
1. **综合提取**（重要：一个 IR 文件只生成一个时间线条目）：
   - 将整个 IR 活动记录作为一个整体分析
   - 提取最重要的 3-5 个 QA 对的核心内容，合并为一个条目
   - 不要为每个 QA 对生成独立条目（避免时间线过度膨胀）

2. **判断回答质量**：
   - 管理层是否正面回答了关键问题？
   - 回答中是否包含具体数字/日期/事实？
   - 回答是否有回避或模糊之处？

3. **映射核心问题**：
   - 识别本次 IR 活动中回答的核心问题
   - 如果涉及新的重要话题但未在核心问题中，标记为"新问题"

4. **提取关键洞察**：
   - 管理层透露的非公开信息或前瞻判断
   - 机构投资者的关注焦点（反映市场关切）

## 输出格式（严格 JSON）
```json
{{
  "timeline_entries": [
    {{
      "date": "YYYY-MM-DD",
      "title": "IR: 活动主题概括（如'机构调研：业务进展与竞争格局'）",
      "key_points": [
        "要点1: 最重要的 QA 核心内容（含具体数据）",
        "要点2: 次重要的 QA 核心内容",
        "要点3: 管理层透露的关键洞察",
        "...最多5个要点"
      ],
      "answered_questions": ["本次IR回答的核心问题"],
      "importance": 0.0,
      "sentiment": "positive/negative/neutral",
      "source_type": "投资者关系"
    }}
  ],
  "assessment_update": "",
  "contradictions": [],
  "new_questions": ["QA中暴露的新问题"],
  "key_insights": ["对投资决策最关键的3-5条洞察"]
}}
```

注意：
- 只输出 JSON
- **一个 IR 文件只生成一个 timeline_entries 条目**（这是关键要求）
- 将多个 QA 对的核心内容合并为 3-5 个要点
- 如果管理层回避了关键问题，在 key_points 中明确指出
"""
    return prompt


# ── 综合评估生成 Prompt ──────────────────────────


def build_assessment_prompt(
    timeline_entries: List[Dict],
    entity_name: str,
    topic_name: str,
    core_questions: List[str],
) -> str:
    """
    基于时间线条目生成综合评估。
    """
    entries_text = "\n\n".join(
        f"[{e.get('date', '')}] {e.get('title', '')}\n"
        + "\n".join(f"- {p}" for p in e.get("key_points", []))
        for e in timeline_entries[-20:]  # 最近20条
    )

    questions_text = (
        "\n".join(f"{i + 1}. {q}" for i, q in enumerate(core_questions))
        if core_questions
        else "（暂无核心问题）"
    )

    prompt = f"""你是一名资深上市公司研究分析师。请基于以下时间线条目，为 {entity_name} 的「{topic_name}」主题生成一段综合评估。

## 核心追踪问题
{questions_text}

## 时间线条目（最近20条）
{entries_text}

## 要求
1. 100-300字的段落
2. 总结关键趋势和变化（不是简单罗列事实）
3. 回答核心问题的当前状态（哪些已回答、哪些尚无进展）
4. 给出核心判断和前瞻
5. 如有风险要点也要提及
6. 用引用块格式（>）输出

## 输出
直接输出综合评估文本（以 > 开头）：
"""
    return prompt


# ── 行业蒸馏 Prompt ──────────────────────────


# ── 核心问题生成 Prompt ──────────────────────────


def build_question_generation_prompt(
    entity_name: str,
    sector: str,
    position: str,
    existing_questions: List[str],
    recent_content: str,
) -> str:
    """
    基于最新信息生成/更新核心追踪问题。
    """
    existing_text = (
        "\n".join(f"- {q}" for q in existing_questions)
        if existing_questions
        else "（暂无）"
    )

    prompt = f"""你是一名上市公司研究框架设计专家。请为 {entity_name} 设计或更新核心追踪问题。

## 实体信息
名称: {entity_name}
行业: {sector}
定位: {position}

## 现有核心问题
{existing_text}

## 最新信息概况
{recent_content[:1500]}

## 要求
1. 审查现有问题：哪些问题已经过时？哪些问题需要拆分？
2. 基于最新信息，建议2-3个新问题
3. 问题要具体、可追踪、有信息增量
4. 必须结合{entity_name}的实际情况，不要产出通用问题
5. 不要出现"核心竞争优势是什么""主要增长驱动力在哪里"这类泛泛的问题

## 输出格式（严格 JSON）
```json
{{
  "archived_questions": ["建议归档的旧问题"],
  "updated_questions": [{{"old": "原问题", "new": "修改后的问题"}}],
  "new_questions": ["新问题1", "新问题2", "新问题3"]
}}
```

只输出 JSON。
"""
    return prompt


# ── 公告专用 Prompt ──────────────────────────


def build_announcement_prompt(
    content: str,
    entity_name: str,
    announcement_type: str,
    published_date: str,
    core_questions: List[str],
    max_content_chars: int = 25000,
) -> str:
    """
    重大公告专用分析 prompt。
    强调事件影响评估、对财务和股价的潜在影响。
    """
    content = content[:max_content_chars]

    questions_text = (
        "\n".join(f"{i + 1}. {q}" for i, q in enumerate(core_questions))
        if core_questions
        else "（暂无核心问题）"
    )

    prompt = f"""你是一名资深事件驱动分析师。以下{entity_name}的{announcement_type}公告可能对投资决策产生重大影响，请深度分析。

## 分析对象
实体: {entity_name}
公告类型: {announcement_type}
发布日期: {published_date}

## 核心追踪问题
{questions_text}

## 待分析内容
{content}

## 分析要求
1. **事件本质**：这笔交易/事件的实质是什么？解决了什么问题？
2. **财务影响**：
   - 涉及金额及占公司净资产/营收的比例
   - 对当期及未来3年业绩的影响
   - 资金来源
3. **战略意义**：是否符合公司长期战略？对竞争格局的影响？
4. **执行风险**：审批风险、整合风险、市场风险
5. **市场反应预判**：类似事件在历史案例中的市场反应

## 输出格式（严格 JSON）
```json
{{
  "timeline_entries": [
    {{
      "date": "YYYY-MM-DD",
      "title": "公告简要概括",
      "key_points": [
        "事件本质：...",
        "财务影响：金额XXX，占净资产X%",
        "战略意义：...",
        "主要风险：..."
      ],
      "answered_questions": [""],
      "importance": 0.0,
      "sentiment": "positive/negative/neutral",
      "source_type": "公告"
    }}
  ],
  "assessment_update": "",
  "contradictions": [],
  "new_questions": ["事件后续需要追踪的问题"],
  "key_insights": ["对投资决策最关键的2-3条洞察"]
}}
```

注意：
- 只输出 JSON
- 如果某项数据未披露，标记为"未披露"
- importance 对于重大公告应 ≥ 0.8
"""
    return prompt


# ── 招股书专用 Prompt ──────────────────────────


def build_prospectus_prompt(
    content: str,
    entity_name: str,
    published_date: str,
    core_questions: List[str],
    max_content_chars: int = 25000,
) -> str:
    """
    招股说明书专用分析 prompt。
    强调商业模式、竞争优势、募投项目、风险因素。
    """
    content = content[:max_content_chars]

    questions_text = (
        "\n".join(f"{i + 1}. {q}" for i, q in enumerate(core_questions))
        if core_questions
        else "（暂无核心问题）"
    )

    prompt = f"""你是一名资深IPO分析师。请深度分析{entity_name}的招股说明书，提取对打新/投资决策最关键的信息。

## 分析对象
实体: {entity_name}
文档类型: 招股说明书
日期: {published_date}

## 核心追踪问题
{questions_text}

## 待分析内容
{content}

## 分析要求
1. **商业模式**：公司如何赚钱？收入来源、客户结构、定价模式
2. **核心竞争优势**：技术壁垒、客户粘性、成本优势、牌照壁垒
3. **募投项目**：募资金额及用途、预期回报、与现有业务协同性
4. **财务健康度**：增长趋势、毛利率同行对比、现金流质量
5. **风险因素**：客户集中度、技术迭代、政策监管、关联交易
6. **可比公司估值**：同行业PE、PB、PS估值水平

## 输出格式（严格 JSON）
```json
{{
  "timeline_entries": [
    {{
      "date": "YYYY-MM-DD",
      "title": "招股书关键发现",
      "key_points": [
        "商业模式：...",
        "竞争优势：...",
        "募投项目：...",
        "主要风险：..."
      ],
      "answered_questions": [""],
      "importance": 0.0,
      "sentiment": "positive/negative/neutral",
      "source_type": "招股说明书"
    }}
  ],
  "assessment_update": "",
  "contradictions": [],
  "new_questions": ["IPO后需要持续追踪的问题"],
  "key_insights": ["对打新/投资决策最关键的3-5条洞察"]
}}
```

注意：
- 只输出 JSON
- 所有数字必须准确，不要编造
- 风险因素要具体，不要泛泛而谈
"""
    return prompt


# ── 行业蒸馏 Prompt ──────────────────────────


def build_distillation_prompt(
    sector_name: str,
    company_entries: dict,
    core_questions: list,
    existing_assessment: str = "",
) -> str:
    """
    行业蒸馏 prompt — 从多家公司的时间线条目中提取行业级洞察。

    Args:
        sector_name: 行业名称（如"半导体设备"）
        company_entries: {公司名: [条目dict]} 的字典
        core_questions: 该行业的核心追踪问题
        existing_assessment: 行业 wiki 现有综合评估（可选）
    """
    questions_text = (
        "\n".join(f"{i + 1}. {q}" for i, q in enumerate(core_questions))
        if core_questions
        else "（暂无核心问题）"
    )

    # 构建公司条目文本
    companies_text = ""
    for cname, entries in company_entries.items():
        if not entries:
            continue
        entry_lines = []
        for e in entries:
            date = e.get("date", "")
            title = e.get("title", "")
            points = e.get("key_points") or e.get("points") or []
            points_text = "\n".join(f"    - {p[:100]}" for p in points[:5])
            entry_lines.append(f"  [{date}] {title}\n{points_text}")
        companies_text += f"\n### {cname}\n" + "\n".join(entry_lines) + "\n"

    assessment_text = ""
    if existing_assessment:
        assessment_text = f"\n## 现有行业评估\n{existing_assessment[:800]}\n"

    prompt = f"""你是一名资深行业研究分析师。请分析以下{len(company_entries)}家在「{sector_name}」行业的公司的最新动态，从中提取行业层面的洞察。

## 行业
{sector_name}

## 该行业核心追踪问题
{questions_text}{assessment_text}
## 各公司近期动态
{companies_text}

## 分析要求
1. **跨公司模式识别**：哪些趋势/变化在多家公司同时出现？（这是行业层面信号的最强证据）
2. **市场信号**：需求变化、价格趋势、产能扩张/收缩、库存周期
3. **竞争格局**：市场份额变化、新进入者、退出者、竞争加剧/缓和
4. **技术趋势**：技术路线变化、新产品/新工艺、研发方向
5. **供应链动态**：上游供应变化、下游客户需求、国产化进展
6. **政策/监管**：行业政策变化、监管动态、国际贸易影响
7. **只提取真正的行业级洞察**：一条信息如果只影响一家公司（如该公司独特的财务结果），不应纳入行业条目
8. **对比现有评估**：如果新信息与"现有行业评估"矛盾或显著更新，在 assessment_update 中说明

## 输出格式（严格 JSON）
```json
{{
  "industry_insights": [
    {{
      "date": "YYYY-MM-DD",
      "title": "洞察标题（简洁概括）",
      "key_points": [
        "要点1：具体趋势描述",
        "要点2：支撑证据（哪家公司提到）",
        "影响：对行业的影响判断"
      ],
      "source_companies": ["提及此趋势的公司列表"],
      "importance": 0.0
    }}
  ],
  "assessment_update": "是否需要更新行业综合评估？如需，给出新评估文本（100-200字）。如无需更新，留空。",
  "new_questions": ["新发现的需追踪的行业问题"],
  "no_insights_reason": "如果没有提取到行业级洞察，简要说明原因。如有洞察，留空。"
}}
```

注意：
- 只输出 JSON
- 每个 insight 必须来自至少 1 家公司的时间线，且最好是跨公司的模式
- date 使用该趋势最相关的日期（最近公司提及的日期）
- importance 范围 0.0-1.0，0.7 以上表示高重要性（跨公司确认的趋势）
- 不要编造数据，只基于提供的条目
- 如果没有行业级洞察，将 industry_insights 设为空数组，并在 no_insights_reason 中说明
"""
    return prompt
