# Gate 系统操作手册

> 配置化、可诊断、可重试的 Pipeline 质量控制框架
> 
> 版本: 1.0 | 实施日期: 2026-05-17

---

## 快速开始

### 运行带Gate检查的Pipeline

```bash
# 完整流程（所有阶段 + 自动Gate检查）
python scripts/full_pipeline.py --company 东方电缆

# 只运行特定阶段 + Gate检查
python scripts/full_pipeline.py --company 东方电缆 --stage review

# 跳过Gate检查（原始Pipeline行为）
python scripts/full_pipeline.py --company 东方电缆 --no-gates

# 预览模式（显示Gate结果但不阻断）
python scripts/full_pipeline.py --company 东方电缆 --dry-run

# 查看Gate执行日志
python scripts/full_pipeline.py --company 东方电缆 --gate-log
```

---

## 架构概览

```
PDF输入
  │
  ▼
┌──────────────────────────────┐  Gate 0: 输入校验
│ 文件完整性、格式、重复检测      │
└──────────────────────────────┘
  │
  ▼
Stage 1: PDF提取
  │
  ▼
┌──────────────────────────────┐  Gate 1: 提取质量
│ 按doc_type差异化阈值检查       │
│ quality_score, total_chars     │
│ 失败 → 诊断 → 重试/人工        │
└──────────────────────────────┘
  │
  ▼
Stage 2: 结构化提取
  │
  ▼
┌──────────────────────────────┐  Gate 2: 数据契约
│ Schema验证、必填字段、数值范围   │
│ 交叉字段公式（营收≥净利润）      │
│ 失败 → 诊断 → 重试/人工        │
└──────────────────────────────┘
  │
  ▼
Stage 3: LLM分析
  │
  ▼
┌──────────────────────────────┐  Gate 3: LLM输出检查
│ 3.1 JSON格式验证               │
│ 3.2 幻觉检测（单位感知匹配）    │
│ 3.3 逻辑一致性检查              │
│ 失败 → 诊断 → 重试/人工        │
└──────────────────────────────┘
  │
  ▼
Stage 4: 规则评分审查（保留现有）
  │
  ▼
┌──────────────────────────────┐  Gate 4.5: LLM金融分析师深度审查 ★核心
│ 投资逻辑、风险覆盖、同业对标    │
│ 数据质量、前瞻展望              │
│ 按文档类型差异化标准            │
│ 失败 → 返回修改意见 → Stage 3重试 │
│ 超限 → review_queue.md        │
└──────────────────────────────┘
  │
  ▼
Stage 5: Wiki入库
  │
  ▼
┌──────────────────────────────┐  Gate 5: Wiki完整性
│ Frontmatter、链接、重复条目    │
└──────────────────────────────┘
```

---

## Gate 清单

| Gate | 名称 | 检查内容 | 适用文档类型 |
|------|------|----------|-------------|
| Gate 1 | `gate_1_extraction_quality` | 文本长度、quality_score、扫描PDF | 全部 |
| Gate 2 | `gate_2_data_contract` | 必填字段、数值范围、交叉验证 | 全部 |
| Gate 3.1 | `gate_3_1_llm_format` | JSON格式、必填字段、时间线格式 | 全部 |
| Gate 3.2 | `gate_3_2_hallucination` | 数字幻觉检测（单位感知） | 全部 |
| Gate 3.3 | `gate_3_3_logic_consistency` | 营收利润关系、毛利率解释、情绪 | 全部 |
| **Gate 4.5** | `gate_4_5_analyst_review` | **LLM金融分析师深度审查** | 全部 |
| Gate 5 | `gate_5_wiki_integrity` | Frontmatter、链接、重复条目 | 全部 |

---

## 配置说明

### 配置文件位置

```
config/pipeline_rules.yaml
```

### 按文档类型配置

支持三种文档类型，每种有独立的规则集：

- `financial_report`: 年报/半年报/季报
- `investor_relations`: 投资者关系活动记录
- `prospectus`: 招股说明书

### 关键配置项

```yaml
pipeline_gates:
  financial_report:
    gate_1_extraction_quality:
      thresholds:
        annual_report:
          min_chars: 50000      # 年报最少字符数
          min_quality: 0.30     # 质量分阈值
      failure_action: diagnose_then_retry_or_human

    gate_4_5_analyst_review:
      enabled: true
      approval_threshold: 4.0   # 自动通过分数线（0-5）
      max_llm_retries: 2       # LLM审查最大重试次数
      mandatory_dimensions:     # 必查维度
        - revenue_analysis
        - profit_quality
        - cashflow_analysis
        - risk_factors:         # 7类必查风险
            - customer_concentration
            - supplier_concentration
            - seasonal_risk
            - subsidy_dependency
            - raw_material_exposure
            - capex_pressure
            - ar_turnover_risk
```

### 修改配置生效

配置修改后**立即生效**，无需重启或重新部署。下次运行Pipeline时自动加载新配置。

---

## Gate 4.5: LLM金融分析师审查详解

### 审查维度（5维度加权）

| 维度 | 权重 | 检查内容 |
|------|------|----------|
| 投资逻辑 | 30% | 数据→分析→结论链条完整性 |
| 风险覆盖 | **25%** | **7类风险必查清单** |
| 同业对标 | 20% | 至少2家竞争对手对比 |
| 数据质量 | 15% | 数字准确性、计算正确性 |
| 前瞻展望 | 10% | 催化剂、跟踪问题 |

### 7类必查风险清单

1. **客户集中度**（前5大客户占比 > 20%）
2. **供应商集中度**（前5大供应商占比 > 50%）
3. **季节性风险**（季度间经营现金流波动 > 30%）
4. **补贴依赖**（政府补助/净利润 > 30%）
5. **原材料敏感**（铜价等大宗商品波动）
6. **资本支出压力**（投资现金流净流出/经营现金流 > 1）
7. **应收账款风险**（应收增速 > 营收增速）

### 输出示例

```json
{
  "approval_status": "needs_revision",
  "total_score": 3.45,
  "dimensions": {
    "investment_logic": {"score": 5, "issues": []},
    "risk_coverage": {"score": 2, "issues": ["未识别5类风险"]},
    "peer_comparison": {"score": 2, "issues": ["未提及竞争对手"]},
    "data_quality": {"score": 5, "issues": []},
    "forward_outlook": {"score": 3, "issues": ["缺少具体催化剂"]}
  },
  "revision_requirements": [
    "[risk_coverage] 请补充前5大客户占比的风险分析",
    "[peer_comparison] 请对比中天科技、亨通光电的毛利率"
  ]
}
```

### 审批标准

- **>= 4.0分**: 自动通过，直接入库
- **< 4.0分**: 返回修改意见，Stage 3 重试（最多2次）
- **重试超限**: 进入 `review_queue.md` 等待人工审核

---

## 失败处理流程

### 诊断引擎（DiagnosticsEngine）

自动识别10种失败根因：

| 根因 | 自动修复 | 重试次数 | 超限处理 |
|------|---------|---------|---------|
| unit_mismatch | 单位提示重试 | 2次 | review_queue |
| fact_hallucination | 事实修正重试 | 2次 | review_queue |
| json_parse_error | JSON修复器 | 3次 | review_queue |
| missing_required_field | 字段提醒重试 | 2次 | review_queue |
| numeric_inconsistency | 数值修正重试 | 2次 | review_queue |
| logic_inconsistency | 逻辑提示重试 | 2次 | review_queue |
| extraction_too_short | 换策略重试 | 1次 | review_queue |
| quality_score_too_low | 高质量设置重试 | 1次 | review_queue |
| scanned_pdf_detected | OCR重试 | 1次 | review_queue |
| analyst_review_failed | 审查反馈重试 | 2次 | review_queue |

### 重试调度器（RetryOrchestrator）

核心原则：**搞清原因再重试，不修复就重试是浪费**

```
Gate失败
  │
  ▼
DiagnosticsEngine.analyze()
  │
  ├── fixable=True ──→ 检查重试次数 ──→ 未超限 ──→ 带fix_hint重试
  │                      │
  │                      └── 已超限 ──→ 进入 review_queue.md
  │
  └── fixable=False ──→ 直接进入 review_queue.md
```

---

## 代码结构

```
scripts/gate_system/
├── __init__.py                    # 包入口，暴露主要接口
├── base.py                        # Gate基类、GateResult、PipelineContext
├── registry.py                    # Gate注册器，从YAML加载配置
├── config_loader.py               # pipeline_rules.yaml 加载和验证
├── diagnostics.py                 # 失败诊断引擎（10种根因）
├── retry.py                       # 重试调度器
└── gates/
    ├── extraction_quality_gate.py # Gate 1: 提取质量
    ├── data_contract_gate.py      # Gate 2: 数据契约
    ├── llm_output_gates.py        # Gate 3: LLM输出（3个子Gate）
    ├── financial_analyst_gate.py  # Gate 4.5: 金融分析师审查 ★
    └── wiki_integrity_gate.py    # Gate 5: Wiki完整性
```

---

## 测试

### 运行单元测试

```bash
# 全部Gate系统测试
python -m pytest tests/unit/test_gate_system.py -v

# 具体Gate测试
python -m pytest tests/unit/test_gate_system.py::TestGateRegistry -v
```

### 手动验证Gate

```bash
# 验证特定Gate对真实数据的审查
python -c "
import sys; sys.path.insert(0, 'scripts')
from gate_system import GateRegistry, PipelineContext
registry = GateRegistry.load()
ctx = PipelineContext(company='东方电缆', doc_type='annual_report', 
                    analysis_path='companies/东方电缆/extracts/financial_reports/东方电缆：2016年年度报告.analysis.json')
result = registry.run_gate('gate_4_5_analyst_review', ctx)
print(f'Status: {result.status}, Score: {result.score}')
print(f'Issues: {result.issues}')
"
```

---

## 故障排除

### Gate系统未启用

**现象**: Pipeline运行但没有Gate检查输出

**解决**:
1. 检查 `config/pipeline_rules.yaml` 是否存在
2. 检查 `--no-gates` 是否被误用
3. 查看错误输出中是否有 "Gate系统导入失败"

### Gate检查过于严格

**现象**: 大量文档被标记为 needs_review

**解决**: 修改 `config/pipeline_rules.yaml` 中对应Gate的配置：
- 提高 `approval_threshold`（如从 4.0 改为 3.5）
- 减少 `mandatory_dimensions` 中的必查项
- 降低 `thresholds` 中的数值要求

### 审核队列积压

**现象**: `review_queue.md` 中待审条目过多

**解决**:
1. 检查DiagnosticsEngine是否正确识别根因
2. 调整 `max_retries` 增加重试次数
3. 定期检查并处理 review_queue.md

---

## 更新日志

### v1.0 (2026-05-17)

- 实现配置化Gate系统框架
- 7个Gate实现（Gate 1-5 + Gate 4.5）
- 按文档类型差异化规则（财务报告/IR/招股书）
- 诊断引擎（10种根因识别）
- 重试调度器（带fix_hint的智能重试）
- LLM金融分析师Gate（5维度审查 + 7类风险必查）
- 集成到 full_pipeline.py
- 28个单元测试全部通过
- 东方电缆年报端到端验证通过
