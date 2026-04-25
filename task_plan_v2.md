# 上市公司知识库 — 改进计划 v2.1（修正版）

> 基于第一性原理深度分析 + 全面代码架构审查
> 目标：从"半自动研究助理"进化为"自我进化的闭环知识库"
> 计划日期：2026-04-25
> 关键决策：Event-Driven 彻底改造 | 完整 State Store | 仅高风险人工审核

---

## 一、架构总览：从"顺序管道"到"事件驱动闭环"

### 1.1 当前架构（问题）

```
[collect] → [ingest] → [assess] → [distill] → [detect] → [report]
     ↑________________________________________________________↓
     （没有回路！报告是终点，不被系统自身消费）
```

**核心问题**：顺序执行 + 只读报告 = 开环系统

### 1.2 目标架构（闭环）

```
┌─────────────────────────────────────────────────────────────┐
│                        Event Bus                            │
└──────┬──────────────┬──────────────┬──────────────┬─────────┘
       │              │              │              │
   [ingest]      [detect]        [lint]       [dashboard]
   completed    contradiction    data_gap     coverage_low
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                          │
                          v
                  [Repair Planner]
                          │
                          v
                   [Job Queue] (SQLite)
                          │
                          v
                   [Worker Pool]
          ┌───────────────┼───────────────┐
          v               v               v
    [collect_news]  [regenerate     [create_review
    (补充采集)       assessment]      ticket]
                     (评估更新)       (人工审核)
                          │
                          v
                   [State Store]
                   (动态状态)
```

**四个新增架构层**：
1. **Event Bus**：所有模块发布事件，不直接调用
2. **Job Queue**：持久化任务，daemon 重启不丢失
3. **Repair Planner**：质量报告 → 可执行任务的翻译器
4. **State Store**：分离动态状态 from 静态配置

---

## 二、四阶段路线图（修正版）

### Phase 1: 基础设施（2 周）

**目标**：建立闭环系统的地基。不添加新功能，只修底层。

| 任务 | 文件 | 改动 | 验收标准 |
|------|------|------|---------|
| 1.1 新增 `job_queue.py` | `scripts/job_queue.py` | SQLite 持久化队列：enqueue/dequeue/complete/fail/retry | 可存储 10,000+ 任务，daemon 重启不丢失 |
| 1.2 新增 `state.db` | `scripts/state_store.py` | 分离动态状态：最后采集时间、评估分数、错误次数、prompt 成功率 | config.yaml 只保留静态配置 |
| 1.3 新增 `event_bus.py` | `scripts/event_bus.py` | 发布/订阅模式：`publish(event_type, payload)` / `subscribe(event_type, handler)` | ingest/detect/lint 都能发布事件 |
| 1.4 修复 `validate_entries` | `scripts/ingest_v2.py` | 验证失败时 `ingested_db.mark_failed()`，不标记为已处理；失败 3 次加入黑名单 | 垃圾文件会被重试并隔离 |
| 1.5 修复 `review_queue` | `scripts/scheduler.py` | 仅 `risk_level == "low"` 时 `rq.approve()`；中高风险进入审核队列 | 高风险操作不自动写入 wiki |
| 1.6 统一 `config.py` | 所有 `scripts/*.py` | 删除所有直接 `yaml.safe_load`，统一通过 `Config.load()` | 修改 config.yaml 一处，全局生效 |
| 1.7 修复 ingest 日期 bug | `scripts/ingest_v2.py` | 从文件名提取报告期（年报=12-31，半年报=06-30），不从 frontmatter | 10 个测试 PDF 日期全部正确 |
| 1.8 清理 log spam | `scripts/query.py` | 添加查询去重（1 小时 TTL）；测试模式不写入 log | log.md 无重复条目 |
| 1.9 接入 evolve/dashboard/lint | `scripts/scheduler.py` | 默认步骤包含 evolve/dashboard/lint；lint 自动修复 broken links | scheduler 跑完全部步骤 |
| 1.10 修复 assessment 瓶颈 | `scripts/batch_assessment.py` | 统一 `is_assessment_stale()`；每次最多处理 20 个缺失评估 | 评估覆盖率 >50% |

**Phase 1 成功标准**：
- [ ] 所有脚本通过 `Config.load()` 读取配置
- [ ] `state.db` 可记录 241 家公司的动态状态
- [ ] `job_queue.db` 可存储任务并恢复
- [ ] 评估覆盖率从 1.2% 提升到 >50%
- [ ] 日志无 spam

---

### Phase 2: 降噪 + Event-Driven 改造（2 周）

**目标**：关掉噪音，建立事件驱动架构。

| 任务 | 文件 | 改动 | 验收标准 |
|------|------|------|---------|
| 2.1 重写矛盾检测 | `scripts/contradiction_detector.py` | 语义级检测：LLM 判断同一实体+90 天窗口+关键字段；废弃 O(n²) 数值匹配 | actionable 矛盾 >10% |
| 2.2 重写实体发现 | `scripts/auto_discover.py` | LLM 从新闻批量提取实体（1 次调用/周）；废弃正则 | 有效率 >50% |
| 2.3 修复交叉验证 | `scripts/cross_verify.py` | LLM 生成事件语义摘要，embedding 聚类；废弃标题字符串匹配 | 多源确认率 >30% |
| 2.4 新闻采集配额 | `scripts/collect_news.py` | 每公司每周最低 1 条；30 天无采集自动拓宽关键词 | 采集覆盖 >50% |
| 2.5 Event-Driven 改造 | `scripts/scheduler.py` | 从顺序执行改为事件驱动：步骤注册为事件处理器 | 采集 0 条时不触发 ingest |
| 2.6 `ingest_v2` 双向更新 | `scripts/ingest_v2.py` | 使用 `graph.find_related_entities()` 更新相关行业/主题 wiki | 新闻同时更新公司和行业 wiki |
| 2.7 新增 `repair_planner.py` | `scripts/repair_planner.py` | 读取 lint/dashboard 输出，生成优先级修复任务 → Job Queue | 质量报告自动转化为任务 |

**Event-Driven 注册示例**：
```python
# scripts/scheduler.py

EVENT_REGISTRY = {
    "ingest_completed": [
        ConditionalHandler("regenerate_assessment", 
                          condition=lambda e: e["entries_added"] > 0,
                          target=lambda e: e["entity"]),
        ConditionalHandler("run_cross_verify",
                          condition=lambda e: e["entries_added"] > 5),
    ],
    "assessment_stale_detected": [
        Handler("regenerate_assessment", priority=8),
    ],
    "high_confidence_contradiction": [
        Handler("create_review_ticket", priority=10),
    ],
    "company_coverage_zero": [
        Handler("broaden_search_queries", priority=5),
    ],
    "data_gap_found": [
        Handler("collect_news", priority=3),
    ],
}
```

**Phase 2 成功标准**：
- [ ] 矛盾检测 actionable >10%
- [ ] 实体发现有效率 >50%
- [ ] 采集覆盖 >50%
- [ ] scheduler 根据事件触发步骤，而非固定顺序

---

### Phase 3: 压缩 + 生命周期（2 周）

**目标**：让 wiki 页面保持在人类可读范围内。

| 任务 | 文件 | 改动 | 验收标准 |
|------|------|------|---------|
| 3.1 新增 `consolidate.py` | `scripts/consolidate.py` | wiki >500 行时触发压缩：提取关键判断+核心矛盾+投资论点；旧条目移至 `archive/` | wiki 平均 <500 行 |
| 3.2 时间衰减权重 | `scripts/batch_assessment.py` | 评估时引入指数衰减：`weight = exp(-days/90)` | 近期条目权重更高 |
| 3.3 过时信息标记 | `scripts/evolve_questions.py` | 标记陈旧判断："基于 2024-01 的信息，可能已过时" | 过时信息有明确标记 |
| 3.4 评估历史化 | `scripts/batch_assessment.py` | 保留评估变更历史+预测-验证记录 | 可追踪观点变化 |
| 3.5 预测-验证闭环 | `scripts/batch_assessment.py` | 每次评估记录预测；下次评估时验证预测偏差 | 预测偏差率可追踪 |

**压缩后的页面结构**：
```markdown
## 核心判断（自动压缩）
### 关键趋势
1. 国产替代加速：市占率 15% → 35%
2. 毛利率承压：从 45% 下滑至 38%
### 核心矛盾
- 营收增长 vs 毛利率下滑
### 投资论点
> 谨慎乐观：订单饱满但估值偏高

## 近期时间线（<90 天）
...

## 中期摘要（季度汇总）
...

[完整历史 →](../archive/公司动态_archive.md)
```

**Phase 3 成功标准**：
- [ ] wiki 平均大小 <500 行
- [ ] 评估包含历史变更记录
- [ ] 预测-验证闭环运转

---

### Phase 4: 闭环 + 自进化（2-3 周）

**目标**：系统能够自我感知、自我比较、自我纠正。

| 任务 | 文件 | 改动 | 验收标准 |
|------|------|------|---------|
| 4.1 Worker Pool | `scripts/scheduler.py` | scheduler 消费 Job Queue，而非固定步骤；支持优先级和并发控制 | 高优先级任务先执行 |
| 4.2 query 写回 wiki | `scripts/query.py` | 分析类查询结果保存为 `type: synthesis/comparison` 页面 | 查询结果可积累 |
| 4.3 Schema 自进化 | `scripts/schema_evolver.py` | 根据 parse_error 率、评估质量分自动调整 CLAUDE.md 中的 prompt 模板 | prompt 质量可追踪 |
| 4.4 Prompt Registry | `scripts/prompt_registry.py` | 版本化 prompt + A/B 测试指标；自动提升优胜版本 | prompt 成功率持续提升 |
| 4.5 投资判断 LLM 化 | `scripts/investment_judgment.py` | 从正则升级为 LLM：输入时间线+行业对比，输出估值分析 | 投资判断有分析逻辑 |
| 4.6 LLM 预算熔断 | `scripts/llm_client.py` | 日预算上限 + 熔断机制；成本超支时自动降级 | 成本可控 |
| 4.7 闭环控制面板 | `scripts/closed_loop_dashboard.py` | 显示：事件流、任务队列状态、指标偏差、补偿动作历史 | 可观测闭环运转 |

**Phase 4 成功标准**：
- [ ] 系统可根据指标偏差自动触发补偿
- [ ] query 结果写回 wiki
- [ ] schema 根据运行指标自动调整
- [ ] 投资判断有分析价值
- [ ] 每日 LLM 成本可控

---

## 三、详细依赖关系

```
Phase 1（基础设施）
  ├── 1.1 job_queue ──┐
  ├── 1.2 state_store ─┼──→ 必须先完成，是 Phase 2-4 的地基
  ├── 1.3 event_bus ───┘
  ├── 1.4-1.8 bug 修复 ──→ 可并行
  ├── 1.9 scheduler 接入 ──→ 依赖 1.1-1.3
  └── 1.10 assessment 修复 ──→ 依赖 1.2

Phase 2（降噪 + Event-Driven）
  ├── 2.1-2.4 算法重写 ──→ 依赖 Phase 1 完成
  ├── 2.5 Event-Driven ──→ 依赖 1.1-1.3
  ├── 2.6 双向更新 ──→ 依赖 2.5
  └── 2.7 repair_planner ──→ 依赖 2.1-2.4 + 1.1

Phase 3（压缩）
  ├── 3.1 consolidate ──→ 依赖 Phase 1-2
  ├── 3.2-3.5 生命周期 ──→ 依赖 1.2 + 3.1

Phase 4（闭环）
  ├── 4.1 Worker Pool ──→ 依赖 1.1 + 2.5
  ├── 4.2 query 写回 ──→ 独立
  ├── 4.3-4.4 Schema/Prompt ──→ 依赖 1.2
  ├── 4.5 投资判断 ──→ 依赖 Phase 1-3
  └── 4.6-4.7 控制面板 ──→ 依赖 4.1
```

---

## 四、关键设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| Event-Driven 范围 | **彻底改造**（方案 B） | 最小改动只是"监控+建议"，不是真正的闭环。只有 Event-Driven 才能让系统根据状态自适应 |
| state.db 范围 | **完整动态状态**（方案 B） | 仅存储 scheduler 元数据不够用。需要记录每公司/每页面/每 prompt 的状态才能做精准补偿 |
| Review Queue 阻塞 | **仅高风险**（方案 A） | 全部阻塞会让人工审核成为瓶颈，违背自动化目标。只阻塞删除条目、修改评估等不可逆操作 |
| 改造节奏 | **渐进式** | Phase 1-3 先修 bug 和基础设施，Phase 4 再做架构升级。避免一次性改动太大导致系统不可用 |
| LLM 成本控制 | **预算熔断 + 优先级队列** | 高优先级任务（投资判断、矛盾验证）优先使用 LLM；低优先级任务（实体发现）降级为规则或延迟执行 |

---

## 五、验收标准（定量 + 定性）

### 5.1 定量指标

| 指标 | 当前 | Phase 2 目标 | Phase 4 目标 |
|------|------|-------------|-------------|
| 评估覆盖率 | 1.2% | >50% | >80% |
| 新闻采集覆盖 | 0.8% | >30% | >50% |
| 矛盾 actionable | 0% | >5% | >10% |
| 实体发现有效率 | 0% | >30% | >50% |
| wiki 平均大小 | 参差不齐 | <800 行 | <500 行 |
| 交叉验证多源率 | 10.4% | >20% | >30% |
| 系统自补偿触发 | 0 次/周 | >3 次/周 | >10 次/周 |
| 每日 LLM 成本 | 无上限 | <¥50 | <¥100 |

### 5.2 定性指标

- [ ] 分析师 5 分钟内把握任意公司核心投资逻辑
- [ ] 系统每周自动触发至少 1 次有意义的自我纠正
- [ ] 查询结果自动积累，下次查询可复用
- [ ] 投资判断页面包含分析逻辑，而非数据罗列
- [ ] 系统可根据运行质量自动调整自身行为

---

## 六、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Event-Driven 改造引入新 bug | 高 | 保留原 scheduler 代码，通过 feature flag 切换；灰度测试 1 周 |
| state.db 与现有系统不兼容 | 中 | 提供迁移脚本；保留旧配置读取作为 fallback |
| consolidate 误删信息 | 高 | 压缩前生成 diff；archive 目录可恢复；前 3 次人工审核 |
| LLM 成本超预算 | 中 | 每日成本上限；超支时暂停非关键任务；成本告警 |
| 人工审核成为瓶颈 | 中 | 仅高风险阻塞；审核队列支持批量操作；7 天未审核自动降级 |

---

## 七、与已有文档对照

| 来源 | 建议 | 本计划是否采纳 |
|------|------|--------------|
| 审查意见 | 行业蒸馏 (P0) | ✅ 已存在，Phase 2 接入 scheduler + 验证 |
| 审查意见 | 问题驱动搜索 (P0) | ✅ Phase 2 采集配额 + LLM 生成搜索词 |
| 审查意见 | 评估历史化 (P1) | ✅ Phase 3.4 |
| 审查意见 | 投资判断层 (P1) | ✅ Phase 4.5，从正则升级为 LLM |
| 审查意见 | 多源交叉验证 (P2) | ✅ Phase 2.3，语义聚类替代字符串匹配 |
| 深度分析 | 修好 scheduler (P0) | ✅ 升级为 Event-Driven + Worker Pool |
| 深度分析 | 关掉噪音 (P0) | ✅ Phase 2（全部） |
| 深度分析 | 知识压缩 (P1) | ✅ Phase 3.1 |
| 深度分析 | 查询回路 (P2) | ✅ Phase 4.2 |
| **代码审查新增** | **Event Bus** | **Phase 1.3 + 2.5** |
| **代码审查新增** | **Job Queue** | **Phase 1.1 + 4.1** |
| **代码审查新增** | **State Store** | **Phase 1.2** |
| **代码审查新增** | **Repair Planner** | **Phase 2.7** |
| **代码审查新增** | **Prompt Registry** | **Phase 4.4** |
| **代码审查新增** | **预算熔断** | **Phase 4.6** |

---

**本计划已整合：**
- 设计思想.md 的原始愿景
- llm-wiki.md 的闭环理念
- 设计思想_深度分析.md 的管线诊断
- 设计思想_审查意见.md 的功能建议
- **全面代码审查揭示的架构缺陷**

**下一步：**
- 审阅本计划，提出调整意见
- 确认后开始 Phase 1 执行
