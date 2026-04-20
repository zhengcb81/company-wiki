# 知识库升级 — 后续行动清单

> 基于 2026-04-20 的质量报告和代码审计生成
>
> **已完成：四轮清洗 + LLM 富化 + 根因修复 + 维护管道**：
> 1. 交叉污染清洗：移除 3,886 条跨行业条目
> 2. 编码乱码清洗：移除 113 条含 mojibake 的条目
> 3. 标题复制清洗：移除 1,024 条无信息增量的条目
> 4. 财报标题清洗：移除 15 条纯标题条目
> 5. 累计清理：5,038 条垃圾条目，从 15,674 降至 10,642
> 6. LLM 富化：21 页生成了综合评估（缺评估从 31 降至 ~10）
> 7. 根因修复：ingest 管道已禁止写入标题填充条目
> 8. 维护管道：`maintenance.py` 系统化所有清理+富化步骤

---

## 一键维护（推荐定期执行）

所有清理和富化步骤已固化为统一管道：

```bash
# 完整维护（清理 + LLM 富化 + 质量报告）
python scripts/maintenance.py --all

# 只运行清理步骤（规则驱动，不需要 API）
python scripts/maintenance.py --clean

# 只运行 LLM 富化（需要 DeepSeek API）
python scripts/maintenance.py --enrich

# 只生成质量报告
python scripts/maintenance.py --report

# 清理预览模式（不实际修改文件）
python scripts/maintenance.py --clean --dry-run
```

管道步骤：

| Phase | 步骤 | 脚本 | 需要 LLM |
|-------|------|------|---------|
| 清理 | 1.1 交叉污染 | cleanup_contamination.py | 否 |
| 清理 | 1.2 编码乱码 | fix_wiki_encoding.py | 否 |
| 清理 | 1.3 标题复制 | remove_title_dumps.py | 否 |
| 清理 | 1.4 财报标题 | remove_report_titles.py | 否 |
| 清理 | 1.5 重处理校验 | reprocess.py | 否 |
| 富化 | 2.1 核心问题 | enrich_wiki.py --questions | 是 |
| 富化 | 2.2 综合评估 | enrich_wiki.py --assessments | 是 |
| 报告 | 3.1 质量仪表盘 | quality_dashboard.py | 否 |

建议频率：每周一次 `python scripts/maintenance.py --all`（config.yaml 已配置 schedule.maintenance: "weekly"）

---

## P1：需要人工审核的操作

### 审核清洗掉的条目

交叉污染清洗移出了 3,886 条记录到 `docs/contaminated_entries_review.md`。
建议人工快速浏览，恢复其中有价值的条目。

### 补充竞争关系（剩余 30 家公司）

当前 15/45 家公司有 competes_with。缺少的关键竞争组：

| 公司 | 建议添加竞争者 |
|------|--------------|
| 华虹半导体 | 中芯国际（特色工艺 vs 标准工艺）|
| 甬矽电子 | 长电科技、通富微电 |
| 天孚通信 | 中际旭创（光器件 vs 光模块）|
| 光迅科技 | 中际旭创、新易盛 |
| 盛美上海 | 北方华创（清洗设备）|
| 华海清科 | 北方华创（CMP）|
| 华大九天 | Synopsys/Cadence（国际对手）|
| 精测电子 | 中科飞测（量检测）|

编辑 `graph.yaml` 对应公司条目，添加 `competes_with` 字段即可。

---

## P2：持续迭代优化

### 补充数据稀缺页面（35个公司条目<10）

以下公司页面的"公司动态"条目不足10条，需要更多数据采集：

**最急需（条目<=4）：**
| 公司 | 条目数 | 建议 |
|------|--------|------|
| 拓荆科技 | 3 | 添加更多搜索词，关注 CVD/PVD 领域 |
| 商汤科技 | 3 | AI 应用公司，应有很多新闻 |
| 珂玛科技 | 3 | 半导体陶瓷零部件 |
| 精测电子 | 3 | 缺综合评估 |
| 华特气体 | 3 | 电子特气龙头 |
| 太辰光 | 4 | 光通信 |
| 景嘉微 | 4 | 国产 GPU |
| 盛美上海 | 4 | 半导体清洗 |

**建议操作**：运行新闻采集补充数据：
```bash
# 为特定公司重新采集
python scripts/collect_news.py --company 拓荆科技
python scripts/collect_news.py --company 商汤科技
# 采集后重新 ingest
python scripts/ingest.py --company 拓荆科技
```

### 定期运行 lint

```bash
# 检查矛盾、孤儿页面、过时信息
python scripts/lint.py
```

### 关键词特异性调优

当前 `graph.yaml` 的 `keyword_meta.specificity_overrides` 已配置 60+ 关键词。
如果后续发现新的误分类案例，只需编辑 `graph.yaml` 增加条目：

```yaml
keyword_meta:
  specificity_overrides:
    新发现的泛词: 0.1    # 太泛，过滤
    新发现的专业词: 0.9  # 高度特异
```

### 质量评分阈值调优

当前 `config_rules.yaml` 的质量评分阈值：
- S 级 >= 0.8
- A 级 >= 0.5
- B 级 >= 0.2
- C 级 < 0.2（拒绝）

如果发现过多误杀或漏杀，调整 `quality_grading.thresholds`：

```yaml
quality_grading:
  thresholds:
    accept: 0.4     # 降低接受门槛
    review: 0.15    # 降低审查门槛
```

---

## 当前质量快照（2026-04-20 清洗+富化后）

| 指标 | 数值 |
|------|------|
| 总 wiki 页面 | 119 |
| 总时间线条目 | ~10,642 |
| 交叉污染条目 | 0 |
| 编码乱码条目 | 0 |
| 标题复制条目 | 0 |
| 缺评估页面 | ~10 (8%) |
| 条目<5的公司页 | 9 |
| 条目<10的公司页 | 35 |
| 有竞争关系 | 15/45 (33%) |
| 测试覆盖 | 159/159 通过 |

## 清洗前后对比

| 指标 | 清洗前 | 清洗后 | 变化 |
|------|--------|--------|------|
| 总条目 | 15,674 | ~10,642 | **-32%** |
| 液冷条目 | 510 | 353 | -31% |
| 光模块条目 | 542 | 451 | -17% |
| 半导体设备条目 | 900 | 347 | -61% |
| 封测条目 | 630 | 244 | -61% |
| AI产业链条目 | 539 | 379 | -30% |
| 编码乱码文件 | 126 | 0 | -100% |
| 标题复制文件 | 99 | 0 | -100% |
| 缺评估页面 | 31 (26%) | ~10 (8%) | -68% |
