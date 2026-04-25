# 审查发现

> 记录实施过程中的关键发现和问题

## 2026-04-22 资深分析师审查

### 发现8：内容质量参差不齐
- 宁德时代（5/5）是最佳范例，英伟达（2/5）是最差
- 行业页面被污染：半导体设备混入机器人/工业软件/建筑 IT 研报
- 主题页面偏离：半导体国产替代变成个股新闻聚合器
- 多数新闻条目是原始网页抓取碎片，缺乏提炼

### 发现9：6 个系统性机制缺陷
1. Ingest 无相关性门控 → 内容污染
2. Ingest 无提炼环节 → 垃圾条目
3. 综合评估无持续更新机制 → 评估过时
4. 无定时执行机制 → config.yaml 的 daily/weekly 调度从未被执行
5. Lint 无反馈闭环 → 2637 broken links 持续存在
6. 问题清单不进化 → 450 个 unanswered questions

### 发现10：覆盖率低
- 238 家公司中只有 53 家有 wiki（22%）
- 53 个行业中只有 26 个有 wiki（49%）

---

## 2026-04-20 初始审查

## 2026-04-24 自进化体系改造

### 发现21：auto_discover.py 产生100%垃圾输出
- suggestions.json 中的所有 50 条"公司发现"都是财务报告 boilerplate 碎片
- 示例："该指标侧面反映出一家公司"（置信度 1.0）
- 示例："市净率是公司"（置信度 1.0）
- **根本原因**：正则提取无法区分"公司名称"和"包含'公司'一词的财务术语"
- **零有效发现**

### 发现22：contradiction_detector 仅使用正则，未调用 LLM
- `llm_client.py:906` 有 `detect_contradictions()` 方法但从未被调用
- 当前 4 种检测方法全部是正则
- 正则无法区分正常时间序列变化和真正矛盾

### 发现23：配置系统名存实亡
- `config.py` 有精致的 `Config`/`LLMConfig` dataclass
- `scheduler.py` 硬编码: model="deepseek-v4-flash", max_tokens=4096
- `ingest_v2.py` 硬编码: model="deepseek-v4-flash", max_tokens=4096
- `batch_assessment.py` 硬编码: model="deepseek-v4-flash", max_tokens=2048
- 改 config.yaml 对实际运行 zero effect

### 发现24：query.py --auto-file 已实现但需手动触发
- `AnswerQualityJudge` + `AnswerSaver` 均已完整实现
- 但需要手动传 `--auto-file` 参数
- 交互式确认阻止了自动化调度

---
### 发现1：1,284份PDF从未被ingest
- 总PDF: 4,597份
- 已ingest: 3,213份（有.hash标记）
- **未ingest: 1,284份**
- 这些文档躺在磁盘上，从未被wiki系统读取

### 发现2：已ingest的PDF处理极浅
- pdf_extract.py只读前60页的几个章节
- 200页年报只读约30%
- 提取后截断到10,000字符
- 交给extract.py做规则打分（初中生水平理解）
- 一份年报在wiki里只留3句话

### 发现3：LLM能力被严重闲置
- llm_client.py有完整的业务方法（analyze_content/synthesize_assessment/detect_contradictions等）
- 但主流程ingest.py完全不调用LLM
- 只有"备用入口"ingest_with_llm.py使用了LLM
- synthesize_assessment()等关键方法没有任何调用方

### 发现4：新闻采集只有摘要
- Tavily search_depth="basic", include_raw_content=false
- 拿到的只是Tavily自己编的100-300字摘要
- 没有任何环节获取原文
- 输入是摘要，输出只能是"摘要的摘要"

### 发现5：API Key未配置
- DEEPSEEK_API_KEY环境变量未设置
- llm_client.available = False
- LLM驱动改进无法进行

## 2026-04-20 交叉污染调研

### 背景
- 现象：sectors/光模块 有 450 条条目，而 companies/北方华创/公司动态 仅 3 条
- 目标：定位污染根源，验证 v2 是否规避，给出处理建议

### 污染根源：graph.py 的  find_related_entities 级联逻辑

问题出在 scripts/graph.py 第 262—341 行的  find_related_entities() 函数。

**Signal 1: company_hint 级联（第 274—291 行）**

当传入 company_hint 时，函数会：
1. 给该公司自身打分 1.0
2. **自动级联到该公司所属的所有 sector 和 theme**，打分 _w_sector_cascade = 0.5
3. 再级联到竞争者的"相关动态"，打分 .3

关键配置：
- _w_sector_cascade = 0.5
- _min_score_threshold = 0.3

这意味着：**只要一个文件带有 company_hint，它所属的每个行业都会被路由到，且分数 0.5 > 阈值 0.3，一定会入库。**

举例：太辰光属于 光模块 行业。当太辰光的一份原始文件被处理时， find_related_entities 会返回：
- ('太辰光', 'company', '公司动态') —— 正确
- ('光模块', 'sector', '光模块') —— **污染**
- ('AI产业链', 'theme', 'AI产业链') —— **污染**

然后 ingest.py / ingest/stages.py 会把同一条内容写入公司 wiki 和行业 wiki。

### 典型案例验证

**案例 1：光模块行业页面**

sectors/光模块/wiki/光模块.md 前 20 条条目（按文件顺序）：
- **20/20 条全部是关于 太辰光 的具体公司信息**（新闻、财报、公告、投资者关系）
- 全文 462 条中，至少 77 条含有"太辰光"
- 这些内容是典型的公司层面信息，如"太辰光：120.78 -5.42%"、"太辰光 2025 年归母净利润 2.99 亿元"，不属于行业层面

**案例 2：北方华创公司页面**

companies/北方华创/wiki/公司动态.md：
- 仅 3 条条目（新闻、财报、股吧讨论）
- 但 companies/北方华创/raw/ 目录下有 **209 个原始文件**

**案例 3：太辰光公司页面**

companies/太辰光/wiki/公司动态.md：
- 仅 4 条条目
- 但 companies/太辰光/raw/ 目录下有 **89 个原始文件**

这说明大量原始文件被路由到了行业页面，而公司自己的页面反而被"饥荒"。

### v2 是否避免了污染？是的，完全避免

scripts/ingest_v2.py 的核心差异：

1. **不调用  find_related_entities()**
   - v2 的 process_file() 直接接收 entity_name 和 entity_type 参数（第 345 行）
   - 只写入该 entity 自己的 wiki 页面，不查找其他相关实体

2. **扫描逻辑更严格**
   - scan_pending_files() 中，公司文件只绑定到自身 company entity，sector 文件只绑定到自身 sector entity（第 74—102 行）
   - 没有级联扩展

3. **LLM 负责内容理解**
   - v2 让 LLM 来判断内容的关键要点，而不是用简单的关键词匹配和级联
   - prompt 中明确指定 entity_name，LLM 会围绕该实体提取时间线

**结论：ingest_v2.py 完全避免了交叉污染问题。**

### 建议：如何处理已有污染数据

已有数据的污染程度很深，手工清理成本极高。建议：

1. **切换到 v2 主流程**
   - 确认 ingest_v2.py 的 LLM 负载和成本可接受
   - 将 v2 作为主 ingest 入口

2. **重建比清理更可靠**
   - 行业 wiki 页面（如 sectors/光模块/wiki/光模块.md）中的 450 条大部分是公司级碎片
   - 手动逐条删除不现实，且无法保证完整性
   - 建议备份后重建：
     - 备份现有 sectors/<name>/wiki/*.md
     - 清空或重置行业 wiki 的时间线部分（只保留核心问题和综合评估框架）
     - 使用 v2 重新处理未 ingest 的文件（主要是行业层面的研报/行业数据）

3. **重新处理历史文件**
   - 当前 .ingested/ 下有超过 3000 个标记文件，很多是由旧 ingest 打上的
   - 若要让 v2 重新处理历史公司文件，需要：
     - 删除对应公司的 .ingested/*.hash 标记（或重置全部标记）
     - 重新运行 v2，让公司文件正确写入各公司的 wiki
     - 注意：v2 的标记机制与 v1 共用同一个 .ingested/ 目录，重复运行不会重复写入（有去重逻辑）

4. **对于行业 wiki 的定位**
   - 行业 wiki 应该只收录：行业政策、市场规模、技术路线、供应链变化等行业级信息
   - 不应该收录：某个具体公司的财报、公告、新闻
   - v2 的 LLM prompt 需要在行业处理时强调这一区分

### 小结

| 指标 | 数值 |
|------|------|
| 光模块行业 wiki 条目 | 450 |
| 其中太辰光相关 | 77+ |
| 太辰光公司 wiki 条目 | 4 |
| 太辰光 raw 文件 | 89 |
| 北方华创公司 wiki 条目 | 3 |
| 北方华创 raw 文件 | 209 |

**根本原因：** graph.find_related_entities 中 company_hint → sector 的无条件级联，导致每份公司文件都会同时写入行业 wiki。v2 已完全解耦这一逻辑。

---

## 2026-04-23 P0 修复执行记录

### 发现21：内容质量修复记录
1. **半导体设备.md 已清理**：从 17 条时间线（含 5 组重复）降为 7 条唯一条目；5 个冗余的矛盾警告合并为 3 个清晰的分类警告（数据来源/数据矛盾/时效性）。
2. **主题子页面内容重复（系统性问题）**：`设备国产化.md`、`市场与需求.md`、`资本投入.md` 三个主题页面具有完全相同的 17 条时间线条目。这是因为 ingest 系统将同一批新闻（珂玛科技+中微公司）同时路由到三个页面，而三个页面的综合评估各不相同且质量较高。此为 ingest 管线的系统性问题，非手动修复可解决，需要 v2 的 LLM 路由增强来按主题相关性分配条目。
3. **北方华创/公司动态.md 澄清**：早前探索 agent 误报为"9 行空页面"，实际文件有 2578 行、322 个来源，内容充实。从清理列表中移除。
4. **安集科技数据缺口**：raw/ 目录下仅有 6 份 2019 年研究 PDF，无新闻文件（`collect_news.py` 从未为其采集），2020-2026 年完全空白。需要将安集科技加入 `config.yaml` 的新闻采集列表并运行 `collect_news.py` 以补全数据。
5. **标签系统失活**：几乎全部页面的 `tags: []`。此为 ingest 管线缺陷——ingest 时未生成标签。

### 发现22：废弃脚本清理完成
- 创建 `scripts/archive/` 目录，21 个脚本已移入
- 归档分类：
  - **v1 脚本（4个）**：extract.py、ingest.py、ingest_with_llm.py、pdf_extract.py（均有 v2 替代）
  - **一次性工具（17个）**：编码修复、数据回填、历史清理、框架导入等
- 活动脚本从 63 减少到 42 个
- 详见 `scripts/archive/README.md`

## 2026-04-23 设计思想独立审查

### 编号说明
以下发现编号接续 findings.md 已有编号（发现1-15），从发现16开始。

### 发现16：审查意见遗漏了代码层面的严重 Bug
审查意见（设计思想_审查意见.md）是一份高质量的产品设计审查，但完全未涉及代码质量。实际代码中存在多处可复现的 bug：

- **lint.py LLMResponse 类型混淆**：`check_semantic_contradictions()` 等处将 `LLMResponse` 对象当字符串使用（`if "无矛盾" not in response` 而非 `response.content`）。影响语义矛盾检测、缺失概念发现、声明新鲜度检查的全部可信度。
- **auto_discover.py 时间戳错误**：`save_suggestions()` 使用 `Path(__file__).stat().st_mtime`（脚本文件修改时间）而非当前时间，语义错误。
- **auto_discover.py 正则召回率极低**：`extract_company_names()` 使用 `[\u4e00-\u9fff]{2,}(?:公司|集团|...)` 模式，无法匹配英文名（AMD、NVIDIA）和无后缀中文名（字节跳动）。
- **batch_assessment.py regex 替换潜在 Bug**：`content.replace(f"## 综合评估\n{match.group(2)}", ...)` 在有多余换行时可能找不到精确匹配。
- **scheduler.py 违反 DRY**：重新实现了 `batch_assessment.py` 的扫描+评估逻辑，而非直接调用。
- **llm_client.py 与 prompts.py 功能重叠**：`synthesize_assessment()` 与 `build_assessment_prompt()` 两套不一致。

### 发现17：审查意见遗漏了内容质量的关键问题
审查意见对行业蒸馏、问题驱动搜索等机制层面分析到位，但没有深入检查实际 wiki 页面的内容质量：

- **主题子页面内容完全重复（严重）**：`半导体国产替代/设备国产化.md`、`市场与需求.md`、`资本投入.md` 三个主题不同的页面包含完全相同的 17 条时间线条目（全是珂玛科技+中微公司新闻）。最严重的内容质量问题。
- **行业页面来源全部缺失**：`半导体设备.md` 全部 17 条时间线条目标注"未知来源"，关键数据（如"2025年国产设备营收突破1000亿元"）无法验证。
- **公司覆盖极度不均**：中微公司/华特气体（数百条丰富条目）vs 安集科技（全部数据止于2019年，7年空白）vs 北方华创/公司动态.md（仅9行 frontmatter，内容为空）。
- **标签系统全面失活**：几乎所有页面 `tags: []`。

### 发现18：审查意见的评分过于乐观
审查意见综合评分 6.75，各项维度 4-9 分。我的修正评分：

| 维度 | 审查评分 | 修正评分 | 原因 |
|------|---------|---------|------|
| 数据存储架构 | 9 | 8 | graph.yaml 3200行单体化；.ingested/ 数千小文件效率低 |
| 数据采集能力 | 7 | 6 | 财报采集依赖外部工具且集成度低；无成本控制 |
| 数据整理质量 | 8 | 7 | lint.py 类型 bug 影响质量检查可信度；内容重复未清理 |
| 自动化程度 | 8 | 7 | scheduler 重复代码；守护模式 last_run 不持久化 |
| 自我进化能力 | 7 | 5 | 发现缺陷但不修复不执行，不构成闭环 |
| 投资判断支持 | 4 | 3 | 信息层优秀、判断层缺失，一致但更严格 |
| 人机协作设计 | 5 | 3 | 无审核机制；lint/auto_discover 都存在未修复 bug |
| 质量度量体系 | 6 | 4 | lint.py bug 导致 LLM 驱动检查不可信 |
| **代码质量** | 未评估 | 5 | 60+ 脚本、v1/v2 共存、多处 bug、DRY 违反 |
| **综合评分** | **6.75** | **5.3** | 差距来自代码质量和技术债务 |

### 发现19：审查意见优先级排序需要修正
审查意见的 P0 是"行业蒸馏"和"问题驱动搜索"（功能新增）。我认为在引入新功能前应先修复现有 bug 和内容问题：

- P0a：修复 lint.py 的 LLMResponse 类型混淆 bug
- P0b：修复 auto_discover.py 的时间戳 bug 和正则缺陷
- P0c：修复 batch_assessment.py 的 regex 替换 bug
- P0d：清理已发现的内容质量问题（主题页面去重、安集科技重新 ingest、行业页面补来源）
- P0e：清理废弃脚本（v1 归档、one-off 工具）
- **然后再做 P1（行业蒸馏、问题驱动搜索、评估历史化）**

### 发现20：设计思想本身存在根本性盲区
1. **缺少"代码质量治理"要求**：只强调知识进化，未涉及代码维护。"自我进化的知识库"不应只进化知识，还应进化代码本身。
2. **"自我进化"的边界未定义**：发现问题后谁来执行？人类还是 AI？当前现状是"发现问题但不解决问题"——auto_discover 建议存 JSON 但需手动 --apply，evolve_questions 标记陈旧但不修复。
3. **缺少成本意识**：LLM API 调用成本（每次 ingest 25K tokens 输入），无成本追踪机制。
4. **缺少质量闭环**：lint 只报告不修复（虽有 --fix 但仅限 broken links）；没有"发现→修复→验证→更新状态"的完整回路。
5. **人机协作设想过于乐观**：实际执行中大量人工配置（公司列表、问题设定、关键词权重）不可或缺。

## 2026-04-21 孤儿公司分析

### 发现6：189 家公司有文件但未被跟踪

- 磁盘上有 240 个公司目录，但 graph.yaml 只跟踪 45 家
- 189 家"孤儿公司"拥有 2,685 个文件（PDF、docx、md 等）
- 从 PDF 文件名自动提取 174 个股票代码，手动补充 15 个
- 按行业分类：半导体相关(31)、AI/科技(7)、互联网/媒体(9)、军工(16)、金融(4)、医药(17)、化工(11)、消费(25)、工业(16)、能源(10)、其他(38)
- **处理方案**：全部纳入 graph.yaml 跟踪，53 家映射到现有行业
- 跟踪公司数：45 → 234

### 发现7：行业 Wiki 高度依赖外部信息采集

- 25 个核心行业中 19 个 wiki 完全为空
- 行业层面原始文件几乎为零（sectors/*/raw/ 下无文件）
- 公司文件不应写入行业 wiki（v2 已避免交叉污染）
- 行业信息需要独立的采集渠道（网络搜索、行业研报）
- **处理方案**：通过 Web 搜索批量采集 19 个行业的市场规模/竞争格局/技术趋势等信息
- 结果：25/25 核心行业全部有内容，249 条时间线条目

## 2026-04-22 Phase 8 Scheduler 运行

### 发现11：collect_news.py 不加载 dotenv
- **问题**：collect_news.py 读取 `config.yaml` 中的 `tavily_api_key` 字段，但 config.yaml 只在注释中提到 env var
- **影响**：所有公司的新闻采集全部失败，返回 "No Tavily API key in config.yaml"
- **修复**：新增 `from dotenv import load_dotenv` + `load_dotenv(WIKI_ROOT / ".env")` + env var fallback
- **根本原因**：scheduler.py 有 dotenv 加载，但 collect_news.py 没有

### 发现12：行业分析文件被重复发现
- **问题**：Phase 7 中生成的 `sectors/{行业}/raw/行业分析_2026-04-21.md` 文件被 `scan_pending_files` 扫描为每个关联公司的待处理文件
- **影响**：每个公司处理时都包含了 15-20 个行业分析文件，浪费 LLM API 调用
- **表现**：北方华创 57 文件中有 28 个 `行业分析_2026-04-21.md`（49%），全部返回 0 条目
- **待修复**：scan_pending_files 应根据 entity_type 区分，sector 文件不应出现在 company 的 pending 列表中

### 发现13：已标记文件仍被扫描但无新条目
- **现象**：大量文件显示 `-> OK | entries:0`
- **原因**：.hash 标记文件生效（文件已处理），但 scan_pending_files 仍然将它们列入待处理
- **影响**：每次运行 scheduler 都会重新扫描这些文件，浪费 LLM API 调用和运行时间
- **根因**：scan_pending_files 的过滤逻辑可能有缺陷——标记存在但仍被返回

### 发现14：并发 API 调用效率问题
- 15 个并行 DeepSeek API 调用导致：
  - 单公司处理时间从之前的 ~5 分钟增长到 23-40 分钟
  - parse_error 率可能与并发导致 API 超时有关
- **建议**：scheduler 并行度限制在 3-5 个公司

## 2026-04-22 关键 Bug 发现

### 发现15：validate_entries 字段名不匹配（所有 Ingest 返回 0 条目的根因）

**问题**：`ingest_v2.py` 的 `validate_entries()` 函数使用 `entry.get("points", [])` 获取条目要点，
但 LLM prompt 输出的是 `"key_points"` 字段。字段名不匹配导致所有通过 `validate_entries` 的
时间线条目被**静默过滤**，返回 0 条目。

**影响范围**：
- 所有经过 `validate_entries` 的 ingest 操作均受影响（约 430+ 个文件）
- Phase 8 scheduler 运行的 15 家核心公司全部返回 0 条目
- 早期 batch 处理的首批孤儿公司也返回 0 条目
- `add_timeline_entries` 也使用了 `entry.get("key_points", [])`，与 `validate_entries`
  的 `entry["points"]` 不一致

**修复（已应用）**：
1. `validate_entries`: `entry.get("points") or entry.get("key_points") or []` + 统一为 `entry["points"]`
2. `add_timeline_entries`: `entry.get("key_points") or entry.get("points") or []`
3. `scan_pending_files` + `batch_ingest.py`: 增加 `行业分析/行业研究/行业报告` 模式过滤

**修复效果验证**（11 家半导体/科技孤儿公司，共 74 个文件）：

| 公司 | 文件 | 条目 | 评估 | 错误 |
|------|------|------|------|------|
| 安集科技 | 5 | 13 | 5 | 0 |
| 菲利华 | 15 | 20 | 6 | 0 |
| 石英股份 | 15 | 50 | 13 | 0 |
| 三环集团 | 15 | 26 | 14 | 0 |
| 鼎龙股份 | 6 | 14 | 6 | 0 |
| 雅克科技 | 2 | 6 | 2 | 0 |
| 至纯科技 | 10 | 37 | 10 | 0 |
| 兆易创新 | 4 | 6 | 4 | 0 |
| 卓胜微 | 1 | 1 | 1 | 0 |
| 华卓精科 | 1 | 1 | 1 | 0 |
| **合计** | **74** | **174** | **62** | **0** |

**后续影响**：
- 重新运行 `batch_ingest.py --reset` 后可恢复所有被静默过滤的条目
- 需要批处理 15 家核心公司 + 剩余的 170+ 孤儿公司
- 建议优先处理半导体/AI 高价值公司

## 2026-04-24 全面代码审查（3 个并行 Review Agent）

### 发现23：contradiction_detector.py 的 `continue` bug 导致大型实体被完全跳过
- **位置**：`scripts/contradiction_detector.py:132-134`
- **问题**：当某个实体的 numeric statements 超过 200 条时，代码截断列表后执行 `continue`，跳到外层循环的下一个实体。结果是超过 200 条声明的实体（可能是核心公司）的矛盾检测被完全跳过。
- **修复**：移除 `continue` 即可。

### 发现24：scheduler.py 在 Windows 上因 SIGTERM 崩溃
- **位置**：`scripts/scheduler.py:128-129`
- **问题**：Windows 没有 `signal.SIGTERM`，守护模式启动时抛出 `AttributeError` 直接崩溃。
- **修复**：用 `getattr(signal, 'SIGTERM', None)` 守卫。

### 发现25：lint.py 的 check_config_consistency 是空操作
- **位置**：`scripts/lint.py:174-193`
- **问题**：函数读取 `config.yaml` 的 `companies`/`sectors`/`themes` 字段做一致性检查，但这些业务数据已拆分到 `companies.yaml` 和 `sectors.yaml`。`config.yaml` 中不存在这些字段，所有检查都被静默跳过。
- **修复**：改读 `companies.yaml` 和 `sectors.yaml`，或删除此函数。

### 发现26：graph.yaml 内联公司数据被 companies.yaml 静默覆盖
- **位置**：`scripts/graph.py:76-79`
- **问题**：加载器先读 `graph.yaml` 的内联公司数据，然后检查 `companies.yaml` 是否存在——如果存在，直接替换全部公司数据。`graph.yaml` 中 2700+ 行的公司定义是死数据。
- **影响**：两个文件可能不同步，用户编辑 `graph.yaml` 中的公司数据不会生效。
- **修复**：清理 `graph.yaml` 中的内联公司数据，仅保留 `companies.yaml` 为唯一数据源。

### 发现27：graph.yaml 包含虚假公司实体
- **位置**：`graph.yaml:1748-1755`
- **问题**：`十论"复苏牛"` 是一篇研报标题，不是公司。作为公司实体存在会触发无意义的新闻采集和污染公司列表。
- **修复**：从 `companies.yaml`（或 `graph.yaml`）中删除此条目。

### 发现28：LLM client 非线程安全
- **位置**：`scripts/llm_client.py:274-287`（generate 方法）、`:946-951`（单例创建）
- **问题**：`generate()` 临时修改实例的 `_max_tokens` 和 `_temperature`，并发调用会互相覆盖。全局单例无锁保护。
- **影响**：守护模式并行处理时可能导致参数混乱。
- **建议**：将参数直接传入底层调用，而非修改实例状态；或文档说明仅限单线程。

### 发现29：wiki 文件非原子读写
- **位置**：`scripts/ingest_v2.py:225-299`、`scripts/review_queue.py:147-173`
- **问题**：所有 wiki 文件操作采用 read → modify → write 模式，无文件锁、无临时文件+rename。进程崩溃或并发写入会导致数据丢失或文件损坏。
- **修复**：使用 write-to-temp + os.replace 模式。

### 发现30：cross_verify.py 跨年日期比较失败
- **位置**：`scripts/cross_verify.py:235`
- **问题**：`abs(int("202512") - int("202601")) = 89 > 1`，导致 12 月-1 月的相邻事件从不被比较。同样 `abs(int("202509") - int("202511")) = 2 > 1`，隔月事件也被跳过。
- **修复**：用 `datetime` 计算月份差，而非字符串整数减法。

### 发现31：Graph._build_indices 不索引 aliases
- **位置**：`scripts/graph.py:90-96`
- **问题**：只按 `name` 和 `ticker` 索引公司，不索引 `aliases` 字段（如 "NVIDIA"、"NVDA"、"超微半导体"）。而 `models/graph_queries.py:58-59` 正确索引了 aliases。
- **影响**：使用 `Graph` 类的脚本（auto_discover、batch_ingest）无法通过别名查找公司。
- **修复**：在 `_build_indices` 中增加 alias 索引，或统一使用 `models/` 实现。

### 发现32：ingested_db.py 两次 read_bytes 无错误处理
- **位置**：`scripts/ingested_db.py:60, 74, 79`
- **问题**：`mark_ingested` 和 `is_ingested` 都调用 `Path(file_path).read_bytes()` 无 try/except。如果文件在扫描和标记之间被删除，抛出 `FileNotFoundError` 导致整个批处理中止。
- **修复**：添加 try/except FileNotFoundError。

### 发现33：batch_ingest.py 将整个文件读入内存
- **位置**：`scripts/batch_ingest.py:62`
- **问题**：循环中 `f.read_bytes()` 将每个文件全部读入内存计算 MD5。大型 PDF 研报（50-200MB）导致内存峰值。且每次扫描都重复计算。
- **修复**：使用分块流式哈希；或缓存文件路径→hash 映射。

### 发现34：sources_count 更新可能损坏
- **位置**：`scripts/ingest_v2.py:289-295`
- **问题**：`wiki_text.replace(f"sources_count: {old_count}", f"sources_count: {old_count + added}")` 使用字符串替换。如果 `sources_count` 值在正文某处出现（如示例文本中），会被错误替换。
- **修复**：使用正则仅替换 frontmatter 中的值。

### 发现35：双重 DB 单例
- **位置**：`scripts/ingest_v2.py:61-68` vs `scripts/ingested_db.py:125-133`
- **问题**：两处各自维护全局单例 `_INGESTED_DB` 和 `_default_db`，可能创建两个独立的 SQLite 连接指向同一数据库。
- **修复**：合并为单一入口。

### 发现36：is_ingested 性能瓶颈
- **位置**：`scripts/ingested_db.py:70-81`
- **问题**：每次调用 `is_ingested` 都重新读取文件计算 MD5。`scan_pending_files` 对 234 家公司的每个文件调用一次，导致大量冗余 I/O。
- **修复**：批量预计算 hash 集合，或缓存文件路径→hash。

### 发现37：日志系统不统一
- **位置**：`scripts/collect_news.py:408-419` vs `scripts/log_writer.py`
- **问题**：`collect_news.py` 有自己的 `append_log()` 直接写 `log.md`，绕过统一的 `log_writer.py`。格式不一致。
- **修复**：统一使用 `log_writer.py`。

### 发现38：配置加载不统一
- **位置**：`scripts/collect_news.py`、`scripts/scheduler.py:95-97`
- **问题**：多处直接 `yaml.safe_load()` 读取 `config.yaml`，绕过 `config.py` 的统一加载器。环境变量覆盖和 `.env` 加载被跳过。
- **修复**：所有脚本统一通过 `config.py` 加载配置。

---

## 2026-04-24 Phase 13 测试修复

### 发现39：graph_loader.py save() 使用 self._data 而非 data 参数
- **位置**：`scripts/models/graph_loader.py:95-117`
- **问题**：`save(data)` 方法中，第 85-86 行将 `data` 赋值后，后续所有引用仍使用 `self._data`。当传入的 `data` 参数与 `self._data` 不同时，写入的是错误的数据。
- **触发场景**：测试 `test_save_to_file` 创建一个独立的 `GraphData` 对象并传入 `loader.save(data)`，此时 `self._data` 为 None，导致 `AttributeError: 'NoneType' object has no attribute 'nodes'`。
- **修复**：将所有 `self._data` 引用改为 `data`。

### 发现40：test_ingest_pipeline.py 依赖已归档的 v1 extract 模块
- **位置**：`tests/unit/test_ingest_pipeline.py:17`
- **问题**：测试从 `scripts/ingest/` 导入，而该包依赖 `extract` 模块（已在 P0e 中归档）。导致 193 个测试全部无法收集（1 error）。
- **修复**：将 `scripts/ingest/` 包（6 个文件）归档到 `scripts/archive/ingest/`，将测试文件重命名并移到 `tests/archive/`。

### 发现41：conftest.py mkdir() 缺少 exist_ok 导致 E2E 测试 setup 失败
- **位置**：`tests/conftest.py:109, 122`
- **问题**：`temp_wiki_structure` fixture 使用 `mkdir()` 而非 `mkdir(exist_ok=True)`。当多个测试复用同一个 `wiki_root` fixture 时，目录已存在导致 `FileExistsError`。
- **修复**：所有 mkdir() 调用统一加上 `exist_ok=True`。

### 发现42：E2E config 测试未适配新 API
- **位置**：`tests/e2e/test_config_loading.py`
- **问题**：6 处与 Phase 10/12 代码变更不匹配：
  1. `config.wiki_root` → 改为 `config.paths.wiki_root`（3 处）
  2. 缺少文件的配置不再抛 `FileNotFoundError`，改为返回默认值
  3. 测试模式下 `validate(strict=False)` 不会验证必需字段
  4. `load_yaml_simple` 不再发射 `DeprecationWarning`
  5. 空配置/不完整配置在测试模式不抛异常
  6. `write_text()` 在 Windows 上默认用 GBK 编码，含中文的配置内容导致 `UnicodeDecodeError`
- **修复**：更新测试预期行为匹配当前代码。

